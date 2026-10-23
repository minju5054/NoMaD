"""72Hz angular plant; unchanged 9Hz translational acceleration convention."""
import json
import math
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase4.execution import command_policy as curv_policy


def alpha_value(label):
    return math.inf if str(label)=='inf' else float(label)


def limited_omega(previous,command,alpha,dt=1/72):
    return float(command) if math.isinf(alpha) else float(np.clip(command,previous-alpha*dt,previous+alpha*dt))


def control_command(method,kappa,previous_v,actual_w,alpha):
    base,flags=curv_policy('CURV-SPEED',kappa,previous_v)
    flags={**flags,'base_v_target_m_s':flags['v_target_m_s'],'angular_reach_limited':False,
        'omega_reach_rad_s':None,'reachable_lower_rad_s':None,'reachable_upper_rad_s':None}
    if method!='CURV+ACC' or math.isinf(alpha):return base,flags
    low=max(-.4,actual_w-alpha/9);high=min(.4,actual_w+alpha/9)
    needed=base[0]*kappa;reach=float(np.clip(needed,low,high))
    flags.update(omega_reach_rad_s=reach,reachable_lower_rad_s=low,reachable_upper_rad_s=high)
    if low<=needed<=high:return base,flags
    if abs(kappa)<=1e-12:
        flags['zero_curvature_unreachable']=True;return base,flags
    target=float(np.clip(abs(reach)/abs(kappa),.05,flags['base_v_target_m_s']))
    # The existing linear acceleration cap takes precedence over instant deceleration.
    v=float(np.clip(target,max(.05,previous_v-.5/9),min(.3,previous_v+.5/9)))
    w=float(np.clip(v*kappa,-.4,.4))
    flags.update(v_target_m_s=target,angular_reach_limited=True,ACCEL_LIMITED=abs(v-target)>1e-12,
        OMEGA_CLIPPED=abs(w-v*kappa)>1e-12,temporal_acceleration_exceeds_limit=abs(v-previous_v)>.5/9+1e-12,
        reachable_sign_matches_curvature=reach*kappa>=0)
    return (v,w),flags


class AngularPlant:
    def __init__(self,alpha,out=None):
        self.alpha=alpha_value(alpha);self.actual_w=0.;self.last_tick=0
        self.log=(out/'plant.jsonl').open('x') if out is not None else None
        if self.log:self.record({'tick':0,'simulation_time_s':0.,'commanded_v_m_s':0.,'commanded_w_rad_s':0.,'actual_v_m_s':0.,'actual_w_rad_s':0.,'omega_tracking_error_rad_s':0.})

    def record(self,row):
        if self.log:self.log.write(json.dumps(row)+'\n');self.log.flush()

    def integrate(self,core,tick):
        assert tick==self.last_tick+1
        previous=self.actual_w
        self.actual_w=limited_omega(previous,core.w,self.alpha)
        core.pose=integrate_se2(core.pose,core.v,self.actual_w,1/72)
        self.last_tick=tick
        self.record({'tick':tick,'simulation_time_s':tick/72,'commanded_v_m_s':core.v,
            'commanded_w_rad_s':core.w,'actual_v_m_s':core.v,'actual_w_rad_s':self.actual_w,
            'previous_actual_w_rad_s':previous,'omega_tracking_error_rad_s':core.w-self.actual_w,
            'angular_rate_limited':abs(core.w-self.actual_w)>1e-12})
        return core.v,self.actual_w

    def close(self):
        if self.log:self.log.close()
