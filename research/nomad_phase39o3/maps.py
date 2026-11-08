"""Explicit R3 map views; immutable original occupancy/observed history."""
import time
from types import MappingProxyType
import numpy as np
from scipy.ndimage import distance_transform_edt
from nomad_phase20d.recent import CachedField

VARIANTS=('VN','VU')

def policy_map(base,B,variant):
    assert variant in VARIANTS
    start=time.perf_counter()
    field=object.__new__(CachedField)
    for key in ('origin','h','radius','error_bound','observed'):setattr(field,key,getattr(base,key))
    if variant=='VU':mask=base.occupied.copy()
    else:
        yy,xx=np.ogrid[:base.occupied.shape[0],:base.occupied.shape[1]]
        near=(base.origin[0]+xx*base.h-B[0])**2+(base.origin[1]+yy*base.h-B[1])**2<=.6**2+1e-12
        mask=base.occupied|((~base.observed)&near)
    field.occupied=np.asarray(mask).copy();field.occupied.flags.writeable=False
    if np.array_equal(mask,base.occupied):field.values=base.values if not base.values.flags.writeable else base.values.copy()
    else:field.values=distance_transform_edt(~mask,sampling=base.h)-base.radius if mask.any() else base.values.copy()
    field.values.flags.writeable=False
    field.metadata=MappingProxyType(dict(map_variant=variant,source_frame=base.metadata.get('frame_id'),unknown_radius_m=.6 if variant=='VN' else None,recency_blocking=False))
    return field,dict(variant=variant,blocked_cells=int(mask.sum()),original_occupied_cells=int(base.occupied.sum()),
        added_unknown_cells=int(np.count_nonzero(mask&~base.occupied)),map_build_s=time.perf_counter()-start)

class EverywhereField:
    """Adapter accepted by KnownDetourGraph with one field for all segments."""
    def __init__(self,field):self.field=field;self.error_bound=field.error_bound
    def configure(self,p):pass
    def query(self,q):return self.field.query(q)
    def unknown_fraction(self,q):return self.field.unknown_fraction(q)
