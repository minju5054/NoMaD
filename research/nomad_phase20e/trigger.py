"""Only the extra occupied-cell predicate; no oracle, age or unknown inflation."""
import time
import numpy as np
from nomad_phase20c.trigger import NoProgress

LENGTH=1.0
HALF_WIDTH=.20


def obstacle_ahead(field,B,u_ref):
    b=np.asarray(B,dtype=float)[:2];u=np.asarray(u_ref,dtype=float);u=u/np.linalg.norm(u);left=np.array([-u[1],u[0]])
    corners=np.array([b+side*HALF_WIDTH*left+ahead*LENGTH*u for ahead in (0,1) for side in (-1,1)])
    shape=np.array(field.occupied.shape[::-1]);lo=np.maximum(0,np.floor((corners.min(axis=0)-field.origin)/field.h).astype(int)-1)
    hi=np.minimum(shape,np.ceil((corners.max(axis=0)-field.origin)/field.h).astype(int)+2)
    forward=np.array([])
    if np.all(hi>lo):
        iy,ix=np.nonzero(field.occupied[lo[1]:hi[1],lo[0]:hi[0]])
        delta=field.origin+np.c_[ix+lo[0],iy+lo[1]]*field.h-b
        along=delta@u;cross=delta@left
        forward=along[(along>=-1e-12)&(along<=LENGTH+1e-12)&(np.abs(cross)<=HALF_WIDTH+1e-12)]
    return dict(obstacle_ahead=bool(len(forward)),occupied_cells=int(len(forward)),nearest_forward_m=float(forward.min()) if len(forward) else None,
        rectangle_world=corners.tolist(),snapshot=dict(field.metadata))


class ConditionalNoProgress(NoProgress):
    def __init__(self,owner):super().__init__();self.owner=owner;self.last_gate=None
    def check(self,poses,tick,u_ref,blocked=False):
        fire,progress,reason=super().check(poses,tick,u_ref,blocked)
        if not fire or tick==self.owner.suppress_trigger_tick:return fire,progress,reason
        field=self.owner.depth_maps.snapshot();self.last_gate=obstacle_ahead(field,poses[tick],u_ref)
        self.owner.drecord('OBSTACLE_CONDITION',tick=tick,simulation_time_s=tick/72,pose=np.asarray(poses[tick]).tolist(),u_ref=np.asarray(u_ref).tolist(),
            evaluated_monotonic_ns=time.monotonic_ns(),progress_3s_m=progress,reason='OBSTACLE_AHEAD' if self.last_gate['obstacle_ahead'] else 'NO_OBSTACLE_AHEAD',**self.last_gate)
        return (True,progress,reason) if self.last_gate['obstacle_ahead'] else (False,progress,'NO_OBSTACLE_AHEAD')
