"""Depth-history-only NO_PROGRESS predicate; immutable direction per component."""
import time
import numpy as np
from nomad_phase20c.trigger import NoProgress
from .history import active_components
from .direction import component_direction,inside_rectangle


def choose_ahead(snapshot,poses,tick,cache):
    components=active_components(snapshot,tick);candidates=[]
    for identity,points in components.items():
        birth=snapshot.component_births[identity]
        if identity not in cache:cache[identity]=component_direction(poses,birth)
        u,detail=cache[identity];inside=inside_rectangle(points,poses[tick],u)
        if inside.any():candidates.append(dict(component_id=identity,t_new_tick=birth,u_ref=u.tolist(),direction=detail,cells_total=len(points),cells_ahead=int(inside.sum())))
    chosen=min(candidates,key=lambda c:(c['t_new_tick'],c['component_id'])) if candidates else None
    return chosen,dict(active_component_count=len(components),ahead_component_count=len(candidates),snapshot=dict(snapshot.metadata))


class NewObstacleNoProgress(NoProgress):
    def __init__(self,owner):super().__init__();self.owner=owner;self.last_gate=None;self.direction_cache={}
    def check(self,poses,tick,old_u,blocked=False):
        if tick<216 or self.busy or tick/72<self.cooldown_until-1e-12 or blocked:
            return super().check(poses,tick,old_u,blocked)
        field=self.owner.depth_maps.snapshot();chosen,info=choose_ahead(field,poses,tick,self.direction_cache)
        # With no new obstacle there is no associated u_ref. The old direction is
        # used only to count denied checks, never to trigger or guide a detour.
        u=np.array(chosen['u_ref']) if chosen else old_u
        fire,progress,reason=super().check(poses,tick,u,blocked)
        if not fire or tick==self.owner.suppress_trigger_tick:return fire,progress,reason
        self.last_gate=dict(new_obstacle_ahead=chosen is not None,component=chosen,**info)
        self.owner.drecord('NEW_OBSTACLE_CONDITION',tick=tick,simulation_time_s=tick/72,pose=np.asarray(poses[tick]).tolist(),u_ref=np.asarray(u).tolist(),
            evaluated_monotonic_ns=time.monotonic_ns(),progress_3s_m=progress,reason='NEW_OBSTACLE_AHEAD' if chosen else 'NO_NEW_OBSTACLE_AHEAD',**self.last_gate)
        return (True,progress,reason) if chosen else (False,progress,'NO_NEW_OBSTACLE_AHEAD')


def no_new_obstacle_ahead(snapshot,pose,tick,u):
    return not any(inside_rectangle(points,pose,np.asarray(u)).any() for points in active_components(snapshot,tick).values())
