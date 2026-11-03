"""Computation-window prefixes from the existing rollout, not a motion proxy."""
from types import FunctionType
import math
import numpy as np
from nomad_isaac.common import integrate_se2
from .rollout import baseline_simulate,unified_simulate,stop_rollout
from nomad_phase20.execution import SPAlignment


def bounded_existing(function,args,duration_s,old_state=None):
    """Reuse the original function bytecode/controller with an additional time stop.

    Its72Hz steps and9Hz control decisions are untouched. For a non-grid deadline,
    keep the original command and use the existing exact SE(2) integrator for the
    last partial tick. No extra speed model or heading rule is introduced.
    """
    if duration_s<=0:return None
    ticks=int(math.ceil(duration_s*72-1e-10));original=function.__globals__['stop_reason']
    def stop(*values):
        return 'COMPUTATION_WINDOW' if values[4]>=ticks/72-1e-12 else original(*values)
    namespace=dict(function.__globals__,stop_reason=stop)
    if function is baseline_simulate and old_state is not None:
        class ContinuingSP(SPAlignment):
            def replace_path(self,xy,B,actual_v):
                super().replace_path(xy,B,actual_v)
                # OLD is already installed: do not invent a new start-alignment
                # trigger because an old waypoint now lies behind the robot.
                self.mode=old_state['mode'];self.target_yaw=old_state.get('target_yaw');self.trigger_S=self.mode in ('BRAKE','ROTATE')
                self.follower.progress=self.follower.path.project(np.asarray(B)[:2])[0]
        namespace['SPAlignment']=ContinuingSP
    bounded=FunctionType(function.__code__,namespace,function.__name__,function.__defaults__,function.__closure__)
    return bounded(*args)


def prefix(case,duration_s,mode='existing_rollout'):
    if mode!='existing_rollout':raise ValueError('Only the registered existing-rollout prediction is allowed')
    if not np.isfinite(duration_s) or duration_s<0:raise ValueError('Invalid computation duration')
    pose=np.asarray(case['B'],dtype=float).copy();v,w=map(float,case['previous_vw'])
    path=case.get('executing_path',case.get('baseline_old_path',case.get('old_path')))
    graph=case.get('executing_graph');poses=[pose.copy()];vs=[];ws=[];dts=[];commands=[];elapsed=0.
    def append(trace):
        nonlocal pose,elapsed,v,w
        origin=elapsed;offset=len(vs)
        for command in trace.get('commands',[]):
            t=origin+command['tick']/72
            if t<duration_s-1e-12:commands.append(dict(command,tick=offset+command['tick'],time_s=t,phase='COMPUTATION_OLD_PATH'))
        for i,(vv,ww) in enumerate(zip(trace['speeds'],trace['omegas'])):
            remaining=duration_s-elapsed
            if remaining<=1e-12:break
            dt=min(1/72,remaining);v,w=float(vv),float(ww)
            pose=np.asarray(trace['poses'][i+1]).copy() if dt>=1/72-1e-12 else integrate_se2(pose,v,w,dt)
            poses.append(pose.copy());vs.append(v);ws.append(w);dts.append(dt);elapsed+=dt
    if duration_s>0:
        if graph is not None:
            trace=bounded_existing(unified_simulate,(case,graph,dict(rotation_policy='graph_rotation')),duration_s);executor='PP_GRAPH_SPEED'
        elif path is not None:
            trace=bounded_existing(baseline_simulate,(case['B'],path,v),duration_s,case.get('executing_state',dict(mode='GO')));executor='FROZEN_PP_SP_ALIGNMENT'
        else:trace=stop_rollout(pose,v);executor='NO_ACTIVE_PATH_BRAKE'
        append(trace)
        if elapsed<duration_s-1e-12:
            # The original endpoint/timeout stopped OLD, so use its existing
            # bounded braking rule, then hold. Do not extend OLD beyond its end.
            append(stop_rollout(pose,v))
        while elapsed<duration_s-1e-12:
            dt=min(1/72,duration_s-elapsed);v=w=0.;poses.append(pose.copy());vs.append(0.);ws.append(0.);dts.append(dt);elapsed+=dt
    else:executor='ZERO_DELAY'
    return dict(poses=np.array(poses),speeds=vs,omegas=ws,step_dt_s=dts,duration_s=duration_s,distance_m=float(np.sum(np.abs(vs)*dts)),
        B_pred=pose.tolist(),previous_vw=[v,w],mode=mode,executor=executor,path_available=path is not None or graph is not None,
        oracle_used=False,future_log_used=False,commands=commands,controller_code_reused=True)


def concatenate(waiting,result):
    n=len(waiting['speeds']);dts=result.get('step_dt_s',[1/72]*len(result['speeds']));duration=waiting['duration_s']+result['duration_s']
    if not np.allclose(waiting['poses'][-1],result['poses'][0],rtol=0,atol=1e-12):raise ValueError('Application pose differs from the computation rollout endpoint')
    commands=list(waiting.get('commands',[]))+[dict(c,tick=c['tick']+n,time_s=waiting['duration_s']+c.get('time_s',c['tick']/72)) for c in result.get('commands',[])]
    return dict(result,poses=np.vstack([waiting['poses'][:-1],result['poses']]),speeds=waiting['speeds']+list(result['speeds']),omegas=waiting['omegas']+list(result['omegas']),commands=commands,
        step_dt_s=waiting['step_dt_s']+list(dts),duration_s=duration,completion_time_s=duration if result['completed'] else None,distance_m=waiting['distance_m']+result['distance_m'],
        computation_prefix_ticks=n,computation_prefix_s=waiting['duration_s'],computation_prefix_distance_m=waiting['distance_m'],
        tick_cap=n+result.get('tick_cap',len(result['speeds'])),
        omega_saturation_fraction=float(np.mean(np.abs(waiting['omegas']+list(result['omegas']))>=.399)) if duration else 0.)
