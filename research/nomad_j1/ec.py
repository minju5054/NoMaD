"""Unmodified Phase52 braking tail/certificate, driven by Phase18 PP/CURV."""
import copy
import time
import numpy as np
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.chunk_execution import protocol
from nomad_phase4c.plant import control_command
from nomad_phase52ec.rollout import certify as frozen_certificate
from nomad_phase28.telemetry import builtin

class CurvController:
    trigger_S=False
    def __init__(self,path=None,follower=None,latched=False):
        self.follower=copy.deepcopy(follower) if follower is not None else PurePursuit(path,protocol()['follower'])
        self.latched=latched
    def control(self,pose,actual_v):
        _,diag=self.follower.control(pose)
        completed=bool(self.latched or diag['endpoint_stop']);self.latched=completed
        if completed:return (0.,0.),dict(completed=True)
        x,y=diag['target_local_x_m'],diag['target_local_y_m'];k=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
        vw,_=control_command('CURV',k,actual_v,0.,float('inf'))
        return vw,dict(completed=False)

def certify(pose,vw,path,field,tick,follower=None,latched=False):
    begin=time.perf_counter();ctl=CurvController(path,follower,latched)
    result=frozen_certificate(pose,vw,path,field,controller=ctl,start_tick=tick)
    return builtin(dict(result,compute_s=time.perf_counter()-begin,controller='PHASE18_PP_CURV',tail='PHASE52_FROZEN'))
