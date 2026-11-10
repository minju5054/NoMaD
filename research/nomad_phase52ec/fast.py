"""Compiled arithmetic mirror, used only inside offline optimization."""
import ctypes,hashlib,subprocess,tempfile
from pathlib import Path
import numpy as np

_library=None

def library():
    global _library
    if _library is None:
        source=Path(__file__).with_name('kernel.cpp');digest=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
        target=Path(tempfile.gettempdir())/f'nomad_ec_tail_{digest}.so'
        if not target.exists():
            temp=target.with_suffix(f'.{__import__("os").getpid()}.so')
            subprocess.run(['/usr/bin/c++','-O3','-std=c++17','-ffp-contract=off','-shared','-fPIC',str(source),'-o',str(temp)],check=True,capture_output=True)
            temp.replace(target)
        lib=ctypes.CDLL(str(target));D=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');U=np.ctypeslib.ndpointer(dtype=np.uint8,flags='C_CONTIGUOUS')
        lib.tail_rollout.argtypes=[D,ctypes.c_int,D,D,ctypes.c_double,D,D,D];lib.tail_rollout.restype=ctypes.c_int
        lib.tail_clearance.argtypes=[D,D,ctypes.c_int,U,ctypes.c_int,ctypes.c_int,D,ctypes.c_double];lib.tail_clearance.restype=ctypes.c_double
        _library=lib
    return _library

def trace(path,B,vw,cap=None):
    p=np.ascontiguousarray(path,float);q=np.ascontiguousarray(B,float);u=np.ascontiguousarray(vw,float)
    poses=np.empty((217,3));commands=np.empty((216,2));meta=np.empty(6)
    n=library().tail_rollout(p,len(p),q,u,-1. if cap is None else float(cap),poses,commands,meta)
    if n<0:return None
    return dict(poses=poses[:n+1].copy(),commands=commands[:n].copy(),endpoint_reached=bool(meta[0]),brake_request_s=float(meta[1]),
        brake_start_s=float(meta[2]),duration_s=float(meta[3]),terminal_vw=meta[4:6].tolist())

def clearance(trajectory,field):
    if trajectory is None:return -1.
    return float(library().tail_clearance(trajectory['poses'],trajectory['commands'],len(trajectory['commands']),
        np.ascontiguousarray(field.occupied,dtype=np.uint8),*field.occupied.shape,np.ascontiguousarray(field.origin,float),field.h))
