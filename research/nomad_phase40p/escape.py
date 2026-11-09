"""Time-local EC thresholds over the frozen NA rollout and exact arc sweep."""
import time
from types import FunctionType
import numpy as np
from nomad_phase32o.exec_cert import rollout,swept_clearance
from nomad_phase32.policy import continuation_certificate
from nomad_isaac.common import integrate_se2
from nomad_phase0.pure_pursuit import XYPath


def fixed_anchor(job_id,installed_s,pose,field,t_escape):
    """Called at first actual installation only; callers keep it by job id."""
    xy=np.asarray(pose,float)[:2]
    exact=float(field.exact_clearance(np.array([xy,xy])))
    if not np.isfinite(t_escape) or t_escape<0:raise ValueError('Finite t_esc required')
    return dict(job_id=int(job_id),installed_s=float(installed_s),c0=exact-.005,
                initial_base_exact_m=exact,t_escape_s=float(t_escape),escape_deadline_sim_s=float(installed_s+t_escape))


def installation_anchor(job_id,cB,installed_s,pose,vw,path,field,cap=None):
    """First72Hz projected-arclength crossing; endpoint shortcut or2s cap.

    The projection is onto the job's installed path (whose arclength origin
    is its predicted B), not integrated travel distance or time at nominal v.
    """
    assert cB<.025
    trace=rollout(pose,vw,path,cap)
    curve=XYPath(path);s_escape=(.03-float(cB))/.5
    projected=np.array([curve.project(q[:2])[0] for q in trace['poses']])
    hits=np.flatnonzero(projected>=s_escape)
    if len(hits):t_escape=float(hits[0]/72);reason='PROJECTED_S_ESCAPE'
    elif curve.s[-1]<s_escape and trace['endpoint_reached']:
        t_escape=float(trace['duration_s']);reason='ENDPOINT_BEFORE_S_ESCAPE'
    else:t_escape=2.;reason='TWO_SECOND_CAP'
    result=fixed_anchor(job_id,installed_s,pose,field,t_escape)
    result.update(cB=float(cB),s_escape_m=s_escape,time_reason=reason,cap_applied=reason=='TWO_SECOND_CAP',
                  projected_s_at_install_m=float(projected[0]),path_length_m=float(curve.s[-1]))
    return result,trace


def continuation_trace(controller,pose,vw,field,tick):
    # Reuse the exact frozen integration function, exposing its trace instead
    # of applying its constant threshold. No controller equations are copied.
    fn=continuation_certificate
    collector=lambda field,poses,commands:dict(poses=poses,commands=commands)
    trace=FunctionType(fn.__code__,dict(fn.__globals__,swept_clearance=collector),fn.__name__,fn.__defaults__,fn.__closure__)(controller,pose,vw,field,tick)
    trace['poses']=np.asarray(trace['poses']);trace['commands']=np.asarray(trace['commands']).reshape(-1,2)
    return trace


def slice_trace(trace,start,end):
    """Sub-tick cuts retain exact arcs; scaled commands keep frozen72Hz API."""
    poses=np.asarray(trace['poses']);cmd=np.asarray(trace['commands']).reshape(-1,2)
    start=max(0.,start);end=min(len(cmd)/72,end)
    if end<start:raise ValueError('Reversed trace interval')
    def pose_at(t):
        i=min(int(np.floor(t*72+1e-12)),len(cmd))
        return poses[-1].copy() if i==len(cmd) else integrate_se2(poses[i],*cmd[i],max(0.,t-i/72))
    qs=[pose_at(start)];vs=[]
    for i in range(max(0,int(np.floor(start*72))),min(len(cmd),int(np.ceil(end*72)))):
        lo=max(start,i/72);hi=min(end,(i+1)/72)
        if hi<=lo+1e-14:continue
        fraction=(hi-lo)*72
        vs.append((cmd[i]*fraction).tolist());qs.append(pose_at(hi))
    return np.asarray(qs),np.asarray(vs).reshape(-1,2)


def check_trace(field,trace,c0,t_escape,elapsed):
    duration=len(trace['commands'])/72
    remaining=t_escape-elapsed
    if remaining<=0:
        result=swept_clearance(field,trace['poses'],trace['commands'])
        return dict(result,escape_active=False,escape_remaining_s=0.,thresholds=[.025])
    intervals=[(0.,min(duration,remaining),c0)]
    # At the2s cap the entire initial2s rollout uses c0, including its end.
    # The strict segment exists only when some rollout time follows deadline.
    if duration>remaining+1e-12:intervals.append((remaining,duration,.025))
    parts=[]
    for lo,hi,threshold in intervals:
        poses,commands=slice_trace(trace,lo,hi)
        cert=swept_clearance(field,poses,commands)
        passed=cert.get('clearance_m') is not None and cert['clearance_m']>=threshold
        parts.append(dict(start_s=lo,end_s=hi,threshold_m=threshold,clearance_m=cert.get('clearance_m'),passed=bool(passed)))
    passed=all(p['passed'] for p in parts)
    values=[p['clearance_m'] for p in parts if p['clearance_m'] is not None]
    return dict(passed=passed,reason='PASS' if passed else 'DEPTH_SWEEP_UNSAFE',clearance_m=min(values) if values else None,
                escape_active=True,escape_remaining_s=remaining,thresholds=[p['threshold_m'] for p in parts],segments=parts)


def certify_escape(pose,vw,path,field,anchor,now_s,cap=None,controller=None,trace=None):
    start=time.perf_counter()
    if trace is None:
        trace=continuation_trace(controller,pose,vw,field,round(now_s*72)) if controller is not None else rollout(pose,vw,path,cap)
    after=time.perf_counter()
    cert=check_trace(field,trace,anchor['c0'],anchor['escape_deadline_sim_s'],now_s)
    return dict(cert,compute_s=time.perf_counter()-start,rollout_s=after-start,duration_s=trace['duration_s'],
                endpoint_reached=trace['endpoint_reached'],escape_job_id=anchor['job_id'],
                escape_initial_threshold_m=anchor['c0'],escape_deadline_sim_s=anchor['escape_deadline_sim_s'])
