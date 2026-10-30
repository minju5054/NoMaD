"""Timestamped free evidence and one EDT cache per immutable R3 evaluation snapshot."""
import json,time
from types import MappingProxyType
import numpy as np
from scipy.ndimage import distance_transform_edt
from nomad_phase15b.depth import Snapshot
from nomad_phase20c.shadow import ShadowSDF


class RecentMap(ShadowSDF):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw);self.last_free_tick=np.full(self.values.shape,-1,dtype=np.int32);self.frame_tick=-1
    def update(self,depth,k,transform,noise=False,rng=None,max_range=3.,frame_tick=None):
        assert frame_tick is not None;self.frame_tick=int(frame_tick)
        return super().update(depth,k,transform,noise,rng,max_range)
    def accumulate(self,*a,**kw):
        info=super().accumulate(*a,**kw)
        free=self._free.astype(bool)&~self._hits.astype(bool)
        # Timestamp is evidence history. Shadow-reset cells stay blocked by unknown;
        # no additional occupancy/forgetting rule is introduced here.
        self.last_free_tick[free]=self.frame_tick
        info['free_timestamp_cells']=int(free.sum());return info


class RecentSnapshot(Snapshot):
    def __init__(self,field,metadata):
        super().__init__(field,metadata);self.last_free_tick=field.last_free_tick.copy();self.last_free_tick.flags.writeable=False
    def save(self,path,compressed=True):
        fn=np.savez_compressed if compressed else np.savez
        fn(path,values=self.values,occupied=self.occupied,observed=self.observed,origin=self.origin,h=self.h,radius=self.radius,
           last_free_tick=self.last_free_tick,metadata=json.dumps(dict(self.metadata)))
    @classmethod
    def load(cls,path):
        base=Snapshot.load(path);obj=object.__new__(cls);obj.__dict__.update(base.__dict__)
        with np.load(path) as z:obj.last_free_tick=z['last_free_tick'].copy()
        obj.last_free_tick.flags.writeable=False;return obj
    def blocked(self,tick):
        stale=(self.last_free_tick<0)|(int(tick)-self.last_free_tick>144)
        return self.occupied|~self.observed|stale


class CachedField(Snapshot):
    """Exact segment-to-site distance with an EDT-derived search bound.

    The minimum vertex distance plus h/sqrt(2) upper-bounds the path minimum.
    Every improving occupied site lies in a segment AABB expanded by that bound.
    Distances inside those boxes are the original exact projection formula.
    No sampled-polyline clearance is substituted for the exact certificate.
    """
    def exact_clearance(self,xy):
        xy=np.asarray(xy);upper=max(0.,float(self.query(xy)[0].min())+self.error_bound+self.radius)+1e-12
        best=float('inf');shape=np.array(self.occupied.shape[::-1])
        for a,b in zip(xy[:-1],xy[1:]):
            bound=min(upper,best)
            low=np.maximum(0,np.floor((np.minimum(a,b)-bound-self.origin)/self.h).astype(int)-1)
            high=np.minimum(shape,np.ceil((np.maximum(a,b)+bound-self.origin)/self.h).astype(int)+2)
            if np.any(high<=low):continue
            iy,ix=np.nonzero(self.occupied[low[1]:high[1],low[0]:high[0]])
            if not len(ix):continue
            q=self.origin+np.c_[ix+low[0],iy+low[1]]*self.h;delta=b-a;den=float(delta@delta)
            f=np.clip((q-a)@delta/den,0,1) if den>1e-24 else np.zeros(len(q))
            best=min(best,float(np.linalg.norm(q-(a+f[:,None]*delta),axis=1).min()))
        if not np.isfinite(best):return Snapshot.exact_clearance(self,xy)
        return best-self.radius


def build_cache(base,tick):
    start=time.perf_counter();blocked=base.blocked(tick);field=object.__new__(CachedField)
    for name in ('h','radius','error_bound','origin','observed'):setattr(field,name,getattr(base,name))
    field.occupied=blocked;field.occupied.flags.writeable=False
    field.values=distance_transform_edt(~blocked,sampling=base.h)-base.radius if blocked.any() else base.values.copy();field.values.flags.writeable=False
    field.metadata=MappingProxyType(dict(source_frame=base.metadata.get('frame_id'),evaluation_tick=int(tick),max_free_age_s=2.))
    return field,dict(edt_computations=1,build_s=time.perf_counter()-start,blocked_cells=int(blocked.sum()),evaluation_tick=int(tick))


def save_cache(base,field,path):
    np.savez(path,base_values=base.values,base_occupied=base.occupied,base_observed=base.observed,
             values=field.values,occupied=field.occupied,origin=base.origin,h=base.h,radius=base.radius,metadata=json.dumps(dict(field.metadata)))


def load_cache(path):
    with np.load(path) as z:
        base=object.__new__(Snapshot);strict=object.__new__(CachedField)
        for obj in (base,strict):
            obj.origin=z['origin'].copy();obj.h=float(z['h']);obj.radius=float(z['radius']);obj.error_bound=obj.h/np.sqrt(2)
            obj.observed=z['base_observed'].copy();obj.metadata=MappingProxyType(json.loads(str(z['metadata'])))
        base.values=z['base_values'].copy();base.occupied=z['base_occupied'].copy()
        strict.values=z['values'].copy();strict.occupied=z['occupied'].copy()
    for obj in (base,strict):
        for name in ('origin','observed','values','occupied'):getattr(obj,name).flags.writeable=False
    return base,strict


def local_certificate(snapshot,path,tick,threshold,strict):
    """Exact threshold check against the current map/time without another EDT.

    Only cells within radius+threshold of a segment can violate the certificate.
    A pass supplies a lower bound, not an invented numerical minimum clearance.
    """
    xy=np.asarray(path);extent=snapshot.radius+threshold;shape=np.array(snapshot.occupied.shape[::-1])
    cell=np.floor((xy-snapshot.origin)/snapshot.h).astype(int)
    if np.any(cell<0) or np.any(cell>=shape-1):return False
    for a,b in zip(xy[:-1],xy[1:]):
        lo=np.maximum(0,np.floor((np.minimum(a,b)-extent-snapshot.origin)/snapshot.h).astype(int)-1)
        hi=np.minimum(shape,np.ceil((np.maximum(a,b)+extent-snapshot.origin)/snapshot.h).astype(int)+2)
        if np.any(hi<=lo):return False
        region=np.s_[lo[1]:hi[1],lo[0]:hi[0]];mask=snapshot.occupied[region].copy()
        if strict:mask|=~snapshot.observed[region]|(snapshot.last_free_tick[region]<0)|(int(tick)-snapshot.last_free_tick[region]>144)
        iy,ix=np.nonzero(mask)
        if not len(ix):continue
        q=snapshot.origin+np.c_[ix+lo[0],iy+lo[1]]*snapshot.h;delta=b-a;den=float(delta@delta)
        f=np.clip((q-a)@delta/den,0,1) if den>1e-24 else np.zeros(len(q))
        if float(np.linalg.norm(q-(a+f[:,None]*delta),axis=1).min())-snapshot.radius<threshold:return False
    return True
