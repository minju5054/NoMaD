"""Publication-time provenance only; occupancy and SDF calculations unchanged."""
from types import FunctionType
import numpy as np
from nomad_phase24r.trigger import PersistentMap
from nomad_phase20f.history import HistorySnapshot
from nomad_phase24r.depth import DepthMapThread as OriginalPublisher
from nomad_phase24.retention import full_frames
from nomad_phase33p import storage


class PublishedFree:
    def __init__(self,shape):
        self.first_confirmed_free_tick=np.full(shape,-1,np.int32)
        self.last_frame_tick=-1;self.updates=0

    def update(self,observed,occupied,last_free_tick,first_occupied_tick,frame_tick):
        tick=int(frame_tick);assert tick>=self.last_frame_tick
        shape=self.first_confirmed_free_tick.shape
        assert all(np.shape(x)==shape for x in (observed,occupied,last_free_tick,first_occupied_tick))
        before_first=(np.asarray(first_occupied_tick)<0)|(tick<np.asarray(first_occupied_tick))
        witness=(np.asarray(last_free_tick)==tick)&np.asarray(observed)&~np.asarray(occupied)&before_first
        new=witness&(self.first_confirmed_free_tick<0)
        self.first_confirmed_free_tick[new]=tick;self.last_frame_tick=tick;self.updates+=1
        return dict(prov_frame_tick=tick,prov_new_confirmed_cells=int(new.sum()),
            prov_witness_cells=int(witness.sum()),prov_confirmed_free_cells=int(np.count_nonzero(self.first_confirmed_free_tick>=0)))


class ProvenMap(PersistentMap):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw);self.prov=PublishedFree(self.values.shape)


def archive_arrays(snapshot):
    data=storage.snapshot_arrays(snapshot)
    data.update(prov_confirmed_free=np.asarray(snapshot.prov_confirmed_free),
                prov_first_confirmed_free_tick=np.asarray(snapshot.prov_first_confirmed_free_tick))
    return data


_save=FunctionType(storage.save_snapshot.__code__,dict(storage.save_snapshot.__globals__,snapshot_arrays=archive_arrays),
    storage.save_snapshot.__name__,storage.save_snapshot.__defaults__,storage.save_snapshot.__closure__)
_load=FunctionType(storage.load_snapshot.__code__,dict(storage.load_snapshot.__globals__,
    HISTORY_ARRAYS=storage.HISTORY_ARRAYS+('prov_confirmed_free','prov_first_confirmed_free_tick')),
    storage.load_snapshot.__name__,storage.load_snapshot.__defaults__,storage.load_snapshot.__closure__)


class ProvenSnapshot(HistorySnapshot):
    def __init__(self,field,metadata):
        # Called by the original map-publisher immediately after the full
        # V1/shadow/history update, immediately before publication under lock.
        # Never called by the control-loop snapshot() getter.
        if metadata.get('frame_id',-1)>=0:
            info=field.prov.update(field.observed,field.occupied,field.last_free_tick,
                                   field.history.first_occupied_tick,round(metadata['sim_s']*72))
            metadata.update(info)
        metadata['prov_schema_version']=1
        super().__init__(field,metadata)
        self.prov_first_confirmed_free_tick=field.prov.first_confirmed_free_tick.copy()
        self.prov_confirmed_free=self.prov_first_confirmed_free_tick>=0
        self.prov_first_confirmed_free_tick.flags.writeable=False;self.prov_confirmed_free.flags.writeable=False

    @property
    def provenance_mask(self):return self.prov_confirmed_free

    save=_save
    load=classmethod(_load)


def clone(function,**bindings):
    return FunctionType(function.__code__,dict(function.__globals__,**bindings),function.__name__,function.__defaults__,function.__closure__)


class ProvenPublisher(OriginalPublisher):
    _initialize=clone(OriginalPublisher._initialize,RecentMap=ProvenMap,RecentSnapshot=ProvenSnapshot)
    run=clone(OriginalPublisher.run,RecentSnapshot=ProvenSnapshot)
    def __init__(self,*a,**kw):self.full_frames=full_frames();self._initialize(*a,**kw)
