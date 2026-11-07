"""Phase33 opt-in serialization only. Live map update/EDT code is untouched."""
import json,os
from pathlib import Path
from types import MappingProxyType
import numpy as np
from nomad_storage_sdf.loader import load_npz

HISTORY_ARRAYS=('last_free_tick','first_free_tick','first_occupied_tick','new_component_ids')

def snapshot_arrays(snapshot):
    data={name:np.asarray(getattr(snapshot,name)) for name in ('values','occupied','observed','origin','h','radius')}
    for name in HISTORY_ARRAYS:
        if hasattr(snapshot,name):data[name]=np.asarray(getattr(snapshot,name))
    if hasattr(snapshot,'component_births'):data['component_births']=np.asarray(json.dumps(dict(snapshot.component_births)))
    data['metadata']=np.asarray(json.dumps(dict(snapshot.metadata)))
    return data

def save_snapshot(snapshot,path,compressed=True):
    """Always compressed, including callers that formerly requested raw NPZ.

    No runtime EDT is added here. Empty-map distance is preserved in metadata;
    component identity arrays are retained because the frozen trigger needs them.
    """
    data=snapshot_arrays(snapshot);values=data.pop('values');original=str(data['metadata']);meta=json.loads(original)
    empty=not bool(data['occupied'].any())
    if empty and not np.all(values==values.flat[0]):raise ValueError('Nonconstant empty SDF cannot use storage v2')
    meta['_sdf_storage_v2']=dict(version=2,original_metadata_json=original,metadata_dtype=data['metadata'].dtype.str,
        values_dtype=values.dtype.str,values_order='F' if values.flags.f_contiguous and not values.flags.c_contiguous else 'C',
        empty_distance_m=float(values.flat[0]) if empty else None)
    data['metadata']=np.asarray(json.dumps(meta));path=Path(path);tmp=path.with_name(path.name+'.v2.tmp')
    with tmp.open('wb') as f:
        np.savez_compressed(f,**data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def load_snapshot(cls,path):
    data=load_npz(path);obj=object.__new__(cls)
    for name in ('values','occupied','observed','origin',*HISTORY_ARRAYS):
        if name in data:
            a=data[name].copy();a.flags.writeable=False;setattr(obj,name,a)
    obj.h=float(data['h']);obj.radius=float(data['radius']);obj.error_bound=obj.h/np.sqrt(2)
    obj.metadata=MappingProxyType(json.loads(str(data['metadata'])))
    if 'component_births' in data:obj.component_births=MappingProxyType({int(k):int(v) for k,v in json.loads(str(data['component_births'])).items()})
    return obj

def install():
    from nomad_phase15b.depth import Snapshot
    from nomad_phase20d.recent import RecentSnapshot
    from nomad_phase20f.history import HistorySnapshot
    for cls in (Snapshot,RecentSnapshot,HistorySnapshot):
        cls.save=save_snapshot;cls.load=classmethod(load_snapshot)
