"""EC-only choices; no decision trigger, map, solver or oracle changes."""
import copy,time
import numpy as np
from nomad_phase28.alignment import NoAlignment
from nomad_phase32o.exec_cert import certify,swept_clearance
from nomad_isaac.common import integrate_se2
from nomad_phase28.telemetry import builtin

PERIOD_TICKS=36
CONTROL_TICKS=8

class CappedNA(NoAlignment):
    def __init__(self):super().__init__();self.speed_cap=None
    def control(self,pose,actual_v):
        (v,w),diag=super().control(pose,actual_v)
        if self.speed_cap is not None and diag.get('mode')=='GO' and not diag['completed']:
            v=max(float(actual_v)-.5/9,min(v,.1));w=float(np.clip(v*diag['kappa'],-.4,.4))
        return (float(v),float(w)),builtin(dict(diag,ec_speed_cap_m_s=self.speed_cap))


def continuation_certificate(controller,pose,vw,field,tick):
    """Continue the actual frozen follower state and9Hz clock, not a reinstall.

    Inspection at tick36 holds the current command for4 integration ticks,
    then uses the same control function. Rotation target/progress/cap persist.
    """
    begin=time.perf_counter();ctl=copy.deepcopy(controller);q=np.asarray(pose,dtype=float).copy();v,w=map(float,vw);poses=[q.copy()];commands=[];completed=False
    for step in range(144):
        if (tick+step)%8==0:
            (v,w),diag=ctl.control(q,v)
            if diag['completed']:completed=True;break
        q=integrate_se2(q,v,w,1/72);poses.append(q.copy());commands.append([v,w])
    end=time.perf_counter();r=swept_clearance(field,np.asarray(poses),np.asarray(commands).reshape(-1,2))
    return builtin(dict(r,compute_s=time.perf_counter()-begin,rollout_s=end-begin,duration_s=len(commands)/72,endpoint_reached=completed,continuation=True,control_phase_tick=tick%8))


def normal_choice(primary,options,check,retained_cap=None,primary_rejected=False):
    """Primary then other SAFE in FRESHEST order; all SAFE at.1, then STOP.

    options carries the same candidate path at both speeds (including G18's
    candidate when it is the primary). No new Graph solve for alternates.
    """
    tested=set();primary_key=primary['key']
    if retained_cap is None:
        for item in [primary,*options]:
            if item['key'] in tested or (primary_rejected and item['key']==primary_key):continue
            tested.add(item['key'])
            if check(item,None)['passed']:
                return dict(item=item,cap=None,route='PRIMARY_FULL' if item['key']==primary_key else 'NEXT_SAFE_FULL')
    else:
        if not primary_rejected and check(primary,.1)['passed']:return dict(item=primary,cap=.1,route='PRIMARY_RETAINED_SLOW')
    for item in options:
        if retained_cap is not None and item['key']==primary_key:continue
        if check(item,.1)['passed']:return dict(item=item,cap=.1,route='SAFE_SLOW')
    return dict(item=None,cap=None,route='STOP_WAIT')
