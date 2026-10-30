"""Observation history only; leaves20D occupancy/SDF values unchanged."""
import json
from types import MappingProxyType
import numpy as np
from scipy.ndimage import label,find_objects,generate_binary_structure
from nomad_phase20d.recent import RecentMap,RecentSnapshot

WINDOW_TICKS=720
MIN_CELLS=5
CONNECTIVITY=generate_binary_structure(2,1)  # Four-neighbour, fixed before replay.


class CellHistory:
    def __init__(self,shape):
        self.first_free_tick=np.full(shape,-1,np.int32);self.first_occupied_tick=np.full(shape,-1,np.int32)
        self.ids=np.zeros(shape,np.int32);self.births={};self.next_id=1;self.new_component_ids=np.zeros(shape,np.int32)
    def update(self,last_free,occupied,tick):
        newly=(self.first_free_tick<0)&(last_free>=0);self.first_free_tick[newly]=last_free[newly]
        newly=(self.first_occupied_tick<0)&occupied;self.first_occupied_tick[newly]=int(tick)
        candidate=occupied&(self.first_free_tick>=0)&(self.first_occupied_tick>self.first_free_tick)&(int(tick)-self.first_occupied_tick<=WINDOW_TICKS)
        labels,n=label(candidate,CONNECTIVITY);sizes=np.bincount(labels.ravel());self.new_component_ids.fill(0)
        for k,region in enumerate(find_objects(labels),1):
            if region is None or sizes[k]<MIN_CELLS:continue
            mask=labels[region]==k;known=np.unique(self.ids[region][mask]);known=known[known>0]
            if len(known):identity=min((int(i) for i in known),key=lambda i:(self.births[i],i))
            else:
                identity=self.next_id;self.next_id+=1;self.births[identity]=int(self.first_occupied_tick[region][mask].min())
            self.ids[region][mask]=identity;self.new_component_ids[region][mask]=identity
        return dict(new_obstacle_cells=int(np.count_nonzero(self.new_component_ids)),new_components=len(np.unique(self.new_component_ids[self.new_component_ids>0])))


class HistoryMap(RecentMap):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.history=CellHistory(self.values.shape)
    def accumulate(self,*a,**kw):
        first_id=self.history.next_id;info=super().accumulate(*a,**kw);info.update(self.history.update(self.last_free_tick,self.occupied,self.frame_tick))
        records=[]
        for identity in range(first_id,self.history.next_id):
            iy,ix=np.nonzero(self.history.new_component_ids==identity)
            records.append(dict(component_id=identity,t_new_tick=self.history.births[identity],recognized_tick=self.frame_tick,cells_world=(self.origin+np.c_[ix,iy]*self.h).tolist()))
        info['new_component_records']=records;return info


class HistorySnapshot(RecentSnapshot):
    def __init__(self,field,metadata):
        super().__init__(field,metadata)
        for name in ('first_free_tick','first_occupied_tick','new_component_ids'):
            a=getattr(field.history,name).copy();a.flags.writeable=False;setattr(self,name,a)
        self.component_births=MappingProxyType(field.history.births.copy())
    def save(self,path,compressed=True):
        fn=np.savez_compressed if compressed else np.savez
        fn(path,values=self.values,occupied=self.occupied,observed=self.observed,origin=self.origin,h=self.h,radius=self.radius,last_free_tick=self.last_free_tick,
            first_free_tick=self.first_free_tick,first_occupied_tick=self.first_occupied_tick,new_component_ids=self.new_component_ids,
            component_births=json.dumps(dict(self.component_births)),metadata=json.dumps(dict(self.metadata)))
    @classmethod
    def load(cls,path):
        obj=object.__new__(cls);obj.__dict__.update(RecentSnapshot.load(path).__dict__)
        with np.load(path) as z:
            for name in ('first_free_tick','first_occupied_tick','new_component_ids'):
                a=z[name].copy();a.flags.writeable=False;setattr(obj,name,a)
            obj.component_births=MappingProxyType({int(k):int(v) for k,v in json.loads(str(z['component_births'])).items()})
        return obj


def active_components(snapshot,tick):
    """Reapply the10s window at query time even if the latest map is old."""
    mask=snapshot.occupied&(snapshot.new_component_ids>0)&(int(tick)-snapshot.first_occupied_tick<=WINDOW_TICKS)
    labels,n=label(mask,CONNECTIVITY);sizes=np.bincount(labels.ravel());result={}
    for k,region in enumerate(find_objects(labels),1):
        if region is None or sizes[k]<MIN_CELLS:continue
        yy,xx=np.nonzero(labels[region]==k);yy+=region[0].start;xx+=region[1].start
        for identity in np.unique(snapshot.new_component_ids[yy,xx]):
            chosen=snapshot.new_component_ids[yy,xx]==identity
            if identity>0:result.setdefault(int(identity),[]).append(np.c_[xx[chosen],yy[chosen]])
    return {i:snapshot.origin+np.concatenate(parts)*snapshot.h for i,parts in result.items()}
