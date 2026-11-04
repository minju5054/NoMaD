"""Shared persistent-component and forward/approach progress rules."""
import inspect,textwrap,time
import numpy as np
from scipy.ndimage import label,find_objects
from nomad_phase20f.history import CellHistory,HistoryMap,HistorySnapshot,CONNECTIVITY,MIN_CELLS
from nomad_phase20f.direction import component_direction,inside_rectangle
from nomad_phase20c.trigger import NoProgress

_source=textwrap.dedent(inspect.getsource(CellHistory.update));_age='&(int(tick)-self.first_occupied_tick<=WINDOW_TICKS)'
assert _source.count(_age)==1
_globals=dict(CellHistory.update.__globals__);exec(_source.replace(_age,''),_globals)
class PersistentCellHistory(CellHistory):update=_globals['update']
class PersistentMap(HistoryMap):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.history=PersistentCellHistory(self.values.shape)

def component_sets(snapshot):
    mask=snapshot.occupied&snapshot.observed&(snapshot.new_component_ids>0);labels,_=label(mask,CONNECTIVITY);sizes=np.bincount(labels.ravel());result={}
    for k,region in enumerate(find_objects(labels),1):
        if region is None or sizes[k]<MIN_CELLS:continue
        yy,xx=np.nonzero(labels[region]==k);yy+=region[0].start;xx+=region[1].start
        for identity in np.unique(snapshot.new_component_ids[yy,xx]):
            chosen=snapshot.new_component_ids[yy,xx]==identity
            if identity>0:result.setdefault(int(identity),[]).append(np.c_[xx[chosen],yy[chosen]])
    return {i:snapshot.origin+np.concatenate(v)*snapshot.h for i,v in result.items()}

def passed(points,pose,u,radius=.09,h=.01):
    # Whole circular footprint clears the farthest observed square cell.
    cell_extent=.5*h*float(np.abs(u).sum())
    return bool(np.asarray(pose)[:2]@u-radius>np.max(np.asarray(points)@u)+cell_extent)

def approach_progress(points,old_pose,new_pose):
    points=np.asarray(points);a=float(np.linalg.norm(points-np.asarray(old_pose)[:2],axis=1).min());b=float(np.linalg.norm(points-np.asarray(new_pose)[:2],axis=1).min())
    return a-b,a,b

def choose_ahead(snapshot,poses,tick,cache):
    sets=component_sets(snapshot);candidates=[];active=0
    for identity,points in sets.items():
        birth=snapshot.component_births[identity]
        if identity not in cache:cache[identity]=component_direction(poses,birth)
        u,detail=cache[identity]
        if passed(points,poses[tick],u,snapshot.radius,snapshot.h):continue
        active+=1;inside=inside_rectangle(points,poses[tick],u)
        if inside.any():candidates.append(dict(component_id=identity,t_new_tick=birth,u_ref=u.tolist(),direction=detail,cells_total=len(points),cells_ahead=int(inside.sum())))
    chosen=min(candidates,key=lambda c:(c['t_new_tick'],c['component_id'])) if candidates else None
    return chosen,dict(active_component_count=active,ahead_component_count=len(candidates),occupied_component_count=len(sets),snapshot=dict(snapshot.metadata))

def no_new_obstacle_ahead(snapshot,pose,tick,u):
    u=np.asarray(u)
    return not any(not passed(points,pose,u,snapshot.radius,snapshot.h) and inside_rectangle(points,pose,u).any() for points in component_sets(snapshot).values())

class PersistentNoProgress(NoProgress):
    def __init__(self,owner):super().__init__();self.owner=owner;self.last_gate=None;self.direction_cache={}
    def check(self,poses,tick,old_u,blocked=False):
        if tick<216 or self.busy or tick/72<self.cooldown_until-1e-12 or blocked:return super().check(poses,tick,old_u,blocked)
        field=self.owner.depth_maps.snapshot();chosen,info=choose_ahead(field,poses,tick,self.direction_cache);u=np.array(chosen['u_ref']) if chosen else np.asarray(old_u)
        forward=float((np.asarray(poses[tick])[:2]-np.asarray(poses[tick-216])[:2])@u);drop=a=b=None
        if chosen:
            points=component_sets(field)[chosen['component_id']];drop,a,b=approach_progress(points,poses[tick-216],poses[tick])
        forward_stalled=forward<.2;approach_stalled=drop is not None and drop<.1
        fire=bool(chosen and (forward_stalled or approach_stalled));reason='NO_PROGRESS' if fire else 'NO_NEW_OBSTACLE_AHEAD' if chosen is None else 'PROGRESS'
        self.last_gate=dict(new_obstacle_ahead=chosen is not None,component=chosen,forward_stalled=forward_stalled,approach_stalled=approach_stalled,
            component_distance_drop_m=drop,component_distance_old_pose_m=a,component_distance_now_m=b,**info)
        if (forward_stalled or approach_stalled) and tick!=self.owner.suppress_trigger_tick:
            self.owner.drecord('NEW_OBSTACLE_CONDITION',tick=tick,simulation_time_s=tick/72,pose=np.asarray(poses[tick]).tolist(),u_ref=u.tolist(),evaluated_monotonic_ns=time.monotonic_ns(),progress_3s_m=forward,reason=reason,**self.last_gate)
        return fire,forward,reason
