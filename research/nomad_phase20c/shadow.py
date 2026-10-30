"""One authorized map change: forget negative evidence in 0.5m occlusion tails."""
import ctypes,subprocess,tempfile
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from nomad_phase15.occupancy import LogOddsSDF
from nomad_phase15b.depth import Snapshot

_kernel=None
_build=None

def shadow_kernel():
    global _kernel,_build
    if _kernel is None:
        _build=tempfile.TemporaryDirectory(prefix='nomad20c_shadow_');target=Path(_build.name)/'shadow.so'
        subprocess.run(['/usr/bin/cc','-O3','-std=c99','-shared','-fPIC',str(Path(__file__).with_name('shadow_rays.c')),'-o',str(target)],check=True,capture_output=True)
        fn=ctypes.CDLL(str(target)).shadow_rays
        ints=np.ctypeslib.ndpointer(dtype=np.int32,ndim=2,flags='C_CONTIGUOUS');mask=np.ctypeslib.ndpointer(dtype=np.uint8,flags='C_CONTIGUOUS')
        fn.argtypes=[ints,ints,ctypes.c_int,ctypes.c_int,ctypes.c_int,mask];fn.restype=None;_kernel=fn
    return _kernel


class ShadowSDF(LogOddsSDF):
    def __init__(self,bounds,resolution=.01,radius=.09):
        super().__init__(bounds,'V1',resolution,radius);self.shadow_mask=np.zeros(self.values.shape,dtype=np.uint8);self.shadow_fn=shadow_kernel()

    def accumulate(self,points,ranges,origin,max_range=3.):
        info=super().accumulate(points,ranges,origin,max_range)
        hit=(points[:,2]>.03)&(points[:,2]<=.6)&(ranges<=max_range)
        endpoints=points[hit,:2];direction=endpoints-np.asarray(origin)[:2];length=np.linalg.norm(direction,axis=1)
        endpoints=endpoints[length>1e-12];direction=direction[length>1e-12]/length[length>1e-12,None]
        starts,inside=self.cells(endpoints);ends,_=self.cells(endpoints+.5*direction)
        # Same grid convention as V1. Duplicate rays have identical union effect.
        pairs=np.unique(np.c_[starts[inside],ends[inside]],axis=0)
        a=np.ascontiguousarray(pairs[:,:2],dtype=np.int32);b=np.ascontiguousarray(pairs[:,2:],dtype=np.int32)
        self.shadow_mask.fill(0);self.shadow_fn(a,b,len(a),self.values.shape[1],self.values.shape[0],self.shadow_mask)
        reset=self.shadow_mask.astype(bool)&(self.log_odds_hundredths<0)
        positive=self.shadow_mask.astype(bool)&(self.log_odds_hundredths>0)
        self.log_odds_hundredths[reset]=0;self.observed[reset]=False
        # Negative->zero cannot change current occupied cells; original >85 rule remains.
        info.update(shadow_rays=len(a),shadow_cells=int(self.shadow_mask.sum()),shadow_reset_cells=int(reset.sum()),
                    shadow_positive_preserved_cells=int(positive.sum()),unknown_fraction=float((~self.observed).mean()))
        return info


def strict_snapshot(base,metadata=None):
    """R3-only map view. Selection/R2/fallback keep the original base occupancy."""
    strict=object.__new__(Snapshot)
    for key in ('h','radius','error_bound','origin','observed'):setattr(strict,key,getattr(base,key))
    strict.occupied=np.asarray(base.occupied|~base.observed).copy();strict.occupied.flags.writeable=False
    strict.values=(distance_transform_edt(~strict.occupied,sampling=base.h)-base.radius) if strict.occupied.any() else base.values.copy()
    strict.values.flags.writeable=False
    from types import MappingProxyType
    strict.metadata=MappingProxyType(dict(base.metadata) if metadata is None else dict(metadata))
    return strict
