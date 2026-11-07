"""Wall-time instrumentation for the unchanged lossless file operation.

No external backup is created. Original SHA and all array fingerprints are
captured from the original bytes before a verified atomic replacement.
"""
import hashlib,io,os,time,zipfile
from contextlib import contextmanager
from pathlib import Path
import numpy as np
from . import bulk as b,loader

STAGES=('read_decompress','sdf_recompute','bit_validation','compress_save','atomic_replace','one_touch_backup','manifest','guard','lock_wait','other')
class Timer:
    def __init__(self):self.seconds={k:0. for k in STAGES};self.stack=[]
    @contextmanager
    def stage(self,name):
        entry=[name,time.monotonic(),0.];self.stack.append(entry)
        try:yield
        finally:
            elapsed=time.monotonic()-entry[1];self.stack.pop();self.seconds[name]+=elapsed-entry[2]
            if self.stack:self.stack[-1][2]+=elapsed

def restored(path,timer):
    original=loader.reconstruct
    def measured(data):
        with timer.stage('sdf_recompute'):return original(data)
    loader.reconstruct=measured
    try:
        with timer.stage('read_decompress'):return loader.load_npz(path)
    finally:loader.reconstruct=original

def prepare(path,version,prior,timer):
    path=Path(path)
    with timer.stage('read_decompress'):
        st=path.stat();raw=path.read_bytes();original_sha=hashlib.sha256(raw).hexdigest()
        row=dict(path=str(path),runtime_version_id=version['version_id'],original_sha256=original_sha,new_sha256=original_sha,
                 before_bytes=st.st_size,after_bytes=st.st_size,backup_tar=None,backup_member=None,backup_policy='DISABLED_BY_USER',
                 values_bit_equal=None,restored_arrays_bit_equal=None,array_count=None,mtime_ns=st.st_mtime_ns,mode=b.stat.S_IMODE(st.st_mode))
        with b.ORIGINAL_LOAD(io.BytesIO(raw),allow_pickle=False) as z:
            keys=set(z.files)
            compact='values' not in keys
            if not compact:
                if not b.MIN_KEYS.issubset(keys) or not keys.issubset(b.KNOWN_KEYS):row.update(status='SKIPPED_DIFFERENT_FORMAT',keys=sorted(keys));return row
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    for key in z.files:
                        with archive.open(key+'.npy') as stream:
                            version_number=np.lib.format.read_magic(stream)
                            if version_number not in ((1,0),(2,0)):row.update(status='SKIPPED_DIFFERENT_FORMAT',reason='unsupported NPY header');return row
                            _,_,dtype=(np.lib.format.read_array_header_1_0(stream) if version_number==(1,0) else np.lib.format.read_array_header_2_0(stream))
                            if dtype.hasobject:row.update(status='SKIPPED_DIFFERENT_FORMAT',reason='object array');return row
                data={k:z[k] for k in z.files}
    if compact:
        if prior is None or original_sha!=prior['new_sha256']:raise RuntimeError('Compact file without matching original manifest: '+str(path))
        data=restored(path,timer)
        with timer.stage('bit_validation'):
            digest=b.arrays_digest(data)
            if digest!=b.known_digest(prior):raise RuntimeError('Prior compact restored arrays mismatch')
        row.update(status='ALREADY_COMPACT',original_sha256=prior['original_sha256'],arrays_sha256=digest,array_count=len(data),values_bit_equal=True,restored_arrays_bit_equal=True,
                   backup_tar=prior.get('backup_tar'),backup_member=prior.get('backup_member'),prior_manifest='research/results/storage_retrofit/manifest.json')
        return row
    with timer.stage('bit_validation'):
        for key,a in data.items():
            if a.dtype.hasobject:raise RuntimeError('Unexpected object array')
            if a.dtype.kind in 'fc' and not np.isfinite(a).all():raise RuntimeError('Nonfinite original array '+str(path)+':'+key)
        if data['occupied'].dtype!=np.bool_ or data['occupied'].ndim!=2 or data['values'].shape!=data['occupied'].shape:
            row.update(status='SKIPPED_DIFFERENT_FORMAT',reason='unsupported grid dtype/dimensions');return row
    with timer.stage('sdf_recompute'):computed=b.reconstruct(data)
    with timer.stage('bit_validation'):
        row.update(values_bit_equal=b.bit_equal(data['values'],computed),arrays_sha256=b.arrays_digest(data),array_count=len(data))
        if not row['values_bit_equal']:
            row.update(status='SKIPPED_SDF_MISMATCH',max_abs_difference=float(np.max(np.abs(computed-data['values']))));return row
    tmp=path.with_name('.'+path.name+'.sdf-strip.tmp')
    if tmp.exists():raise FileExistsError('Unreconciled temporary: '+str(tmp))
    with timer.stage('compress_save'):
        with tmp.open('xb') as f:
            np.savez_compressed(f,**{k:v for k,v in data.items() if k!='values'});f.flush();os.fsync(f.fileno())
        os.chmod(tmp,row['mode']);os.utime(tmp,ns=(st.st_atime_ns,st.st_mtime_ns))
    output=restored(tmp,timer)
    with timer.stage('bit_validation'):
        if set(output)!=set(data) or not all(b.bit_equal(v,output[k]) for k,v in data.items()):raise RuntimeError('Restored temporary differs from original')
        newsha=b.sha(tmp)
    row.update(status='VERIFIED_TEMP',temp_path=str(tmp),new_sha256=newsha,after_bytes=tmp.stat().st_size,restored_arrays_bit_equal=True)
    return row

def commit(row,guard,root,record,timer):
    if row['status']!='VERIFIED_TEMP':record(row);return row
    path=Path(row['path']);tmp=Path(row['temp_path'])
    with timer.stage('guard'):guard.assert_clear(root)
    with timer.stage('bit_validation'):
        if b.sha(path)!=row['original_sha256']:raise RuntimeError('Original changed before atomic replace')
        if b.sha(tmp)!=row['new_sha256']:raise RuntimeError('Temporary changed before atomic replace')
    record(dict(row,status='PREPARED'))
    with timer.stage('atomic_replace'):
        os.replace(tmp,path);fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    with timer.stage('bit_validation'):
        if b.sha(path)!=row['new_sha256']:raise RuntimeError('Atomic replacement SHA failure')
    result=dict(row,status='CONVERTED');result.pop('temp_path',None);record(result);return result
