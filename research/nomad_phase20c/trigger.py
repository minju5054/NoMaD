"""Pose/sample-only NO_PROGRESS detection, explicit busy and end-time cooldown."""
import numpy as np


def reference_direction(poses,tick,samples_world):
    b=np.asarray(poses[tick])[:2];delta=None
    if tick>=8*72:delta=np.asarray(poses[tick-3*72])[:2]-np.asarray(poses[tick-8*72])[:2]
    if delta is not None and np.linalg.norm(delta)>=.3:
        return delta/np.linalg.norm(delta),dict(source='HISTORY_8_TO_3',history_displacement_m=float(np.linalg.norm(delta)))
    if samples_world is None:return None,dict(source='NO_AVAILABLE_SAMPLE',history_displacement_m=float(np.linalg.norm(delta)) if delta is not None else None)
    direction=np.mean(np.asarray(samples_world)[:,-1,:],axis=0)-b;n=float(np.linalg.norm(direction))
    if n<=1e-12:return None,dict(source='UNDEFINED_MEAN_ENDPOINT',mean_endpoint_distance_m=n)
    return direction/n,dict(source='MEAN_ENDPOINT_INCOMPLETE_HISTORY' if delta is None else 'MEAN_ENDPOINT_SHORT_DISPLACEMENT',
                           history_displacement_m=float(np.linalg.norm(delta)) if delta is not None else None,mean_endpoint_distance_m=n)


class NoProgress:
    def __init__(self):self.busy=False;self.cooldown_until=-float('inf')
    def started(self):self.busy=True
    def ended(self,time_s):self.busy=False;self.cooldown_until=float(time_s)+3.
    def check(self,poses,tick,u_ref,blocked=False):
        if tick<3*72 or u_ref is None:return False,None,'INSUFFICIENT_HISTORY_OR_DIRECTION'
        forward=float((np.asarray(poses[tick])[:2]-np.asarray(poses[tick-3*72])[:2])@u_ref)
        if self.busy:return False,forward,'DETOUR_BUSY'
        if tick/72<self.cooldown_until-1e-12:return False,forward,'COOLDOWN'
        if blocked:return False,forward,'ROTATION_ALIGNMENT_OR_REPAIR_WAIT'
        return forward<.20,forward,'NO_PROGRESS' if forward<.20 else 'PROGRESS'
