"""Ephemeral map bundle, preserving separate cost and certificate views."""
import json
from types import MappingProxyType
import numpy as np
from nomad_phase15b.depth import Snapshot
from nomad_phase20d.recent import CachedField

def save_bundle(base,cost,planning,path,variant):
    ref='base' if planning.values is base.values and np.array_equal(planning.occupied,base.occupied) else 'cost' if planning is cost else 'separate'
    data=dict(base_values=base.values,base_occupied=base.occupied,observed=base.observed,cost_values=cost.values,cost_occupied=cost.occupied,
        origin=base.origin,h=base.h,radius=base.radius,planning_reference=ref,metadata=json.dumps(dict(variant=variant,source_frame=base.metadata.get('frame_id'))))
    if ref=='separate':data.update(planning_values=planning.values,planning_occupied=planning.occupied)
    np.savez(path,**data)

def load_bundle(path):
    with np.load(path,allow_pickle=False) as z:
        def make(prefix,cls):
            f=object.__new__(cls);f.h=float(z['h']);f.radius=float(z['radius']);f.error_bound=f.h/np.sqrt(2)
            for name in ('origin','observed'):setattr(f,name,z[name].copy());getattr(f,name).flags.writeable=False
            f.values=z[prefix+'_values'].copy();f.occupied=z[prefix+'_occupied'].copy()
            f.values.flags.writeable=False;f.occupied.flags.writeable=False;f.metadata=MappingProxyType(json.loads(str(z['metadata'])))
            return f
        base=make('base',Snapshot);cost=make('cost',CachedField);ref=str(z['planning_reference'])
        if ref=='base':
            planning=object.__new__(CachedField);planning.__dict__.update(base.__dict__)
        else:planning=cost if ref=='cost' else make('planning',CachedField)
    return base,cost,planning
