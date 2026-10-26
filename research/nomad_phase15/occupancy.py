"""V0 unchanged; V1--V4 frame-wise log-odds evidence and Bresenham clearing.

All sensor transformation, filters, distance field and query conventions match
Phase15-A. A small serial C kernel only traces integer Bresenham rays; compile
once before update timing, without installing a dependency or touching raw data.
"""
import ctypes
import hashlib
from pathlib import Path
import subprocess
import tempfile
import time
import numpy as np
from scipy.ndimage import distance_transform_edt
from .depth_sdf import DepthSDF, backproject

_KERNEL=None
_BUILD=None


def ray_kernel():
    global _KERNEL, _BUILD
    if _KERNEL is None:
        source=Path(__file__).with_name('occupancy_rays.c')
        _BUILD=tempfile.TemporaryDirectory(prefix='nomad15a2_bresenham_')
        target=Path(_BUILD.name)/'rays.so'
        subprocess.run(['/usr/bin/cc','-O3','-std=c99','-shared','-fPIC',str(source),'-o',str(target)],
                       check=True,capture_output=True)
        lib=ctypes.CDLL(str(target));fn=lib.trace_rays
        ip=np.ctypeslib.ndpointer(dtype=np.int32,ndim=2,flags='C_CONTIGUOUS')
        bp=np.ctypeslib.ndpointer(dtype=np.uint8,flags='C_CONTIGUOUS')
        fn.argtypes=[ctypes.c_int,ctypes.c_int,ip,bp,ctypes.c_int,ctypes.c_int,ctypes.c_int,bp,bp,bp]
        fn.restype=None;_KERNEL=fn
    return _KERNEL


def kernel_provenance():
    source=Path(__file__).with_name('occupancy_rays.c')
    return dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                compiler=subprocess.check_output(['/usr/bin/cc','--version'],text=True).splitlines()[0],
                flags=['-O3','-std=c99','-shared','-fPIC'],threads=1,
                startup_compilation_excluded_from_per_observation_update=True)


class LogOddsSDF(DepthSDF):
    def __init__(self,bounds,variant,resolution=.01,radius=.09):
        if variant not in ('V1','V2','V3','V4'):raise ValueError(variant)
        super().__init__(bounds,resolution,radius)
        self.variant=variant
        self.occ_range=2. if variant in ('V3','V4') else 3.
        self.minimum_observations=3 if variant in ('V2','V4') else 0
        # Exact integer hundredths of log-odds avoid 0.85 threshold drift.
        self.log_odds_hundredths=np.zeros(self.values.shape,dtype=np.int16)
        self.occupied_observations=np.zeros(self.values.shape,dtype=np.uint32)
        self._free=np.zeros(self.values.shape,dtype=np.uint8)
        self._hits=self._free.copy();self._seen=self._free.copy()
        self._kernel=ray_kernel()

    def accumulate(self,points,ranges,origin,max_range=3.):
        """One occupied or free update per cell per frame, hit wins ties."""
        near=ranges<=max_range
        height=(points[:,2]>.03)&(points[:,2]<=.6)
        floor=points[:,2]<=.03
        self.mark(self.height_rejected,points[~height & near,:2])
        self.mark(self.range_rejected,points[height & ~near,:2])
        valid=near&(height|floor)
        hits=height[valid] & (ranges[valid]<=self.occ_range)
        kinds=np.where(floor[valid],0,np.where(hits,1,2)).astype(np.int32)
        endpoints,_=self.cells(points[valid,:2])
        # Duplicate endpoint/kind rays are identical integer rays. The union
        # below is exactly equivalent to tracing every pixel once in C.
        if len(endpoints):
            low=endpoints.min(axis=0);span_y=int(np.ptp(endpoints[:,1]))+1
            code=((endpoints[:,0]-low[0])*span_y+endpoints[:,1]-low[1])*3+kinds
            _,indices=np.unique(code,return_index=True)
            endpoints=endpoints[indices];kinds=kinds[indices]
        endpoints=np.ascontiguousarray(endpoints,dtype=np.int32)
        kinds=np.ascontiguousarray(kinds,dtype=np.uint8)
        start,_=self.cells(np.asarray(origin)[None,:2]);ox,oy=map(int,start[0])
        self._free.fill(0);self._hits.fill(0);self._seen.fill(0)
        self._kernel(ox,oy,endpoints,kinds,len(endpoints),self.values.shape[1],self.values.shape[0],
                     self._free,self._hits,self._seen)
        hit=self._hits.astype(bool);free=self._free.astype(bool)&~hit
        self.observed |= self._seen.astype(bool)
        self.log_odds_hundredths[free]-=40
        self.log_odds_hundredths[hit]+=85
        np.clip(self.log_odds_hundredths,-200,350,out=self.log_odds_hundredths)
        self.occupied_observations[hit]+=1
        self.occupied=(self.log_odds_hundredths>85)&(self.occupied_observations>=self.minimum_observations)
        return dict(points=len(points),obstacle_points=int(hits.sum()),ray_count=len(endpoints),
                    occupied_update_cells=int(hit.sum()),free_update_cells=int(free.sum()),
                    occupied_cells=int(self.occupied.sum()),unknown_fraction=float((~self.observed).mean()))

    def update(self,depth,k,transform,noise=False,rng=None,max_range=3.):
        t0=time.perf_counter()
        points,ranges,_=backproject(depth,k,transform,noise,rng)
        t1=time.perf_counter()
        result=self.accumulate(points,ranges,transform[:3,3],max_range)
        t2=time.perf_counter()
        if result['occupied_cells']:
            self.values=distance_transform_edt(~self.occupied,sampling=self.h)-self.radius
        else:
            self.values.fill(self.empty_distance)
        t3=time.perf_counter();self.build_wall_s=t3-t0
        result.update(pointcloud_ms=(t1-t0)*1000,accumulate_ms=(t2-t1)*1000,sdf_ms=(t3-t2)*1000,update_ms=(t3-t0)*1000)
        return result


def make_field(bounds,variant):
    if variant=='V0':return DepthSDF(bounds)
    return LogOddsSDF(bounds,variant)
