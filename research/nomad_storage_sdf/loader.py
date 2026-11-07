"""Restore omitted SDF values using the original runtime EDT implementation."""
from contextlib import contextmanager
from collections.abc import Mapping
import hashlib,json
from pathlib import Path
import numpy as np
from nomad_phase15.occupancy import distance_transform_edt
from nomad_phase15.depth_sdf import DepthSDF

ORIGINAL_LOAD=np.load
REQUIRED={'occupied','origin','h','radius'}


def array_fingerprint(a):
    a=np.asarray(a)
    if a.dtype.hasobject:raise ValueError('Object arrays are not allowed')
    return dict(dtype=a.dtype.str,shape=list(a.shape),fortran_only=bool(a.flags.f_contiguous and not a.flags.c_contiguous),
                sha256=hashlib.sha256(a.tobytes(order='C')).hexdigest(),nbytes=a.nbytes)


def bit_equal(a,b):
    a=np.asarray(a);b=np.asarray(b)
    return (a.dtype==b.dtype and a.shape==b.shape
            and bool(a.flags.f_contiguous and not a.flags.c_contiguous)==bool(b.flags.f_contiguous and not b.flags.c_contiguous)
            and a.tobytes(order='C')==b.tobytes(order='C'))


def reconstruct(data):
    occ=np.asarray(data['occupied']);origin=np.asarray(data['origin']);h=float(data['h']);radius=float(data['radius'])
    if occ.ndim!=2 or occ.dtype!=np.bool_ or origin.shape!=(2,) or not np.isfinite(origin).all() or not np.isfinite(h) or h<=0 or not np.isfinite(radius):raise ValueError('Invalid SDF grid metadata')
    if occ.any():
        # Identical primitive/expression to LogOddsSDF.update, not a new EDT.
        return distance_transform_edt(~occ,sampling=h)-radius
    # Original bounds are not stored. Reconstruct grid extent; if floating
    # rounding or non-grid bounds differ, conversion's exact check SKIPS it.
    upper=origin+(np.array(occ.shape[::-1])-1)*h
    empty=DepthSDF([*origin,*upper],resolution=h,radius=radius).empty_distance
    return np.full(occ.shape,empty)


def load_npz(path,expected_arrays=None):
    with ORIGINAL_LOAD(path,allow_pickle=False) as z:data={k:z[k] for k in z.files}
    if 'values' not in data:
        if not REQUIRED.issubset(data):raise ValueError('Not a compact SDF archive')
        data={'values':reconstruct(data),**data}
    if expected_arrays is not None:
        if set(data)!=set(expected_arrays):raise ValueError('Restored key mismatch')
        for k,a in data.items():
            if array_fingerprint(a)!=expected_arrays[k]:raise ValueError('Restored array mismatch: '+k)
    return data


class RestoredArchive(Mapping):
    """The NpzFile read/context interface used by existing analysis loaders."""
    def __init__(self,data):self.data=data;self.files=list(data)
    def __getitem__(self,key):return self.data[key]
    def __iter__(self):return iter(self.data)
    def __len__(self):return len(self.data)
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def close(self):pass


@contextmanager
def restoring_numpy_load():
    """Explicit process-local opt-in. Never alters a frozen file on disk.

    Only compact SDF NPZs get an adapter. Other np.load calls are untouched.
    This context is for single-threaded offline tools, never online execution.
    """
    previous=np.load
    def patched(file,*args,**kwargs):
        z=ORIGINAL_LOAD(file,*args,**kwargs)
        if isinstance(z,np.lib.npyio.NpzFile) and 'values' not in z.files and REQUIRED.issubset(z.files):
            try:data={k:z[k] for k in z.files};data={'values':reconstruct(data),**data}
            finally:z.close()
            return RestoredArchive(data)
        return z
    np.load=patched
    try:yield
    finally:np.load=previous


def manifest_index(path):
    rows=json.loads(Path(path).read_text())
    return {str(Path(r['path']).resolve()):r for r in rows}


def resolve_original_hash(path,expected_sha,manifest):
    path=Path(path).resolve();current=hashlib.sha256(path.read_bytes()).hexdigest()
    if current==expected_sha:return dict(status='ORIGINAL_BYTES',current_sha256=current)
    row=manifest_index(manifest).get(str(path))
    if row is None or row['original_sha256']!=expected_sha or row['new_sha256']!=current or row['status']!='CONVERTED':raise ValueError('No verified original-hash lineage: '+str(path))
    load_npz(path,row['original_arrays'])
    return dict(status='LOSSLESS_RETROFIT',original_sha256=expected_sha,current_sha256=current,
                original_tar=row['backup_tar'],original_tar_member=row['backup_member'])
