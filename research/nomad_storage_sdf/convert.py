"""Per-file bit audit, deterministic compression and atomic replacement."""
import hashlib,io,json,os,stat
from pathlib import Path
import numpy as np
from .loader import ORIGINAL_LOAD,array_fingerprint,bit_equal,reconstruct,load_npz


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def inspect_file(path):
    path=Path(path);st=path.stat();before=sha(path)
    if path.is_symlink():raise ValueError('Symlink targets are not converted')
    with ORIGINAL_LOAD(path,allow_pickle=False) as z:data={k:z[k] for k in z.files}
    original={k:array_fingerprint(v) for k,v in data.items()}
    if 'values' not in data:raise ValueError('Already compact or not an SDF')
    computed=reconstruct(data);match=bit_equal(data['values'],computed)
    base=dict(path=str(path.resolve()),original_sha256=before,original_arrays=original,values_bit_equal=match,
              original_bytes=st.st_size,original_allocated_bytes=st.st_blocks*512,original_mtime_ns=st.st_mtime_ns,original_atime_ns=st.st_atime_ns,original_mode=stat.S_IMODE(st.st_mode),
              computed_values=array_fingerprint(computed),max_abs_difference=float(np.max(np.abs(computed-data['values']))))
    payload=None
    if match:
        buf=io.BytesIO();np.savez_compressed(buf,**{k:v for k,v in data.items() if k!='values'});payload=buf.getvalue()
        with ORIGINAL_LOAD(io.BytesIO(payload),allow_pickle=False) as z:
            assert set(z.files)==set(data)-{'values'}
            assert all(bit_equal(z[k],data[k]) for k in z.files)
            restored={'values':reconstruct({k:z[k] for k in z.files}),**{k:z[k] for k in z.files}}
            assert all(bit_equal(v,restored[k]) for k,v in data.items())
        base.update(proposed_sha256=hashlib.sha256(payload).hexdigest(),proposed_bytes=len(payload),other_arrays_bit_equal=True)
    else:base.update(proposed_sha256=before,proposed_bytes=st.st_size,other_arrays_bit_equal=True)
    if sha(path)!=before:raise RuntimeError('Source changed during inspection')
    return base,payload


def compact_one(path,expected,backup_tar,backup_member,journal):
    path=Path(path);current=sha(path)
    if current!=expected['original_sha256']:raise RuntimeError('Source differs from dry-run: '+str(path))
    row,payload=inspect_file(path)
    assert row['values_bit_equal']==expected['values_bit_equal'] and row['proposed_sha256']==expected['proposed_sha256']
    row.update(backup_tar=str(backup_tar),backup_member=backup_member,new_sha256=row['original_sha256'],new_bytes=row['original_bytes'])
    if payload is None:
        row.update(status='SKIPPED_VALUES_MISMATCH',new_allocated_bytes=path.stat().st_blocks*512,restored_arrays_bit_equal=True);journal(row);return row
    tmp=path.with_name('.'+path.name+'.sdf-strip.tmp')
    if tmp.exists():raise FileExistsError(tmp)
    try:
        with tmp.open('xb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        assert sha(tmp)==row['proposed_sha256'];load_npz(tmp,row['original_arrays'])
        os.chmod(tmp,row['original_mode']);os.utime(tmp,ns=(row['original_atime_ns'],row['original_mtime_ns']))
        row.update(new_sha256=row['proposed_sha256'],new_bytes=len(payload),status='PREPARED',restored_arrays_bit_equal=True)
        journal(row)  # Durable old/new lineage before atomic replacement.
        if sha(path)!=row['original_sha256']:raise RuntimeError('Source changed before replace')
        os.replace(tmp,path);fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
        load_npz(path,row['original_arrays']);assert sha(path)==row['new_sha256']
        row.update(status='CONVERTED',new_allocated_bytes=path.stat().st_blocks*512);journal(row);return row
    finally:
        if tmp.exists():tmp.unlink()
