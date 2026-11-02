"""Eight policy plus available side seeds; a shared500ms anytime budget."""
import time
import numpy as np
from nomad_phase15b.depth import Snapshot
from nomad_phase0.pure_pursuit import XYPath
from .graph import prepare_candidates,side_initializations
from .optimized import solve_start

_key=None;_field=None

def warm_suffix(previous,B):
    """Only a previous accepted U solution; no baseline or oracle initialization."""
    q=np.asarray(previous['poses'],dtype=float);dt=np.asarray(previous['dt'],dtype=float)
    lengths=np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1);s=np.r_[0.,np.cumsum(lengths)]
    if s[-1]<=1e-10:return None
    projected=XYPath(q[:,:2]).project(np.asarray(B)[:2])[0]
    if s[-1]-projected<=1e-8:return None
    if projected<=1e-8:
        q=q.copy();q[0]=B;return dict(poses=q.tolist(),dt=dt.tolist())
    # Keep the last heading/time at duplicate arclengths (completed rotations).
    keep=np.r_[np.diff(s)>1e-10,True];ss=s[keep];qq=q[keep];tt=np.r_[0.,np.cumsum(dt)][keep]
    positions=np.linspace(projected,s[-1],11);heading=np.unwrap(qq[:,2])
    out=np.c_[np.interp(positions,ss,qq[:,0]),np.interp(positions,ss,qq[:,1]),np.interp(positions,ss,heading)]
    out[0]=B;times=np.interp(positions,ss,tt)
    return dict(poses=out.tolist(),dt=np.clip(np.diff(times),.05,1.).tolist())

def worker(args):
    global _key,_field
    index,case,candidates,sigma,path,weights,deadline,nh,warm=args
    key=(case['snapshot_file'],deadline)
    if key!=_key:_field=Snapshot.load(case['snapshot_file']);_key=key
    r=solve_start(case['B'],case['previous_vw'][0],np.asarray(candidates),sigma,_field,weights,np.asarray(path),deadline,nh,warm_state=warm)
    return dict(index=index,**r)

def plan(pool,case,weights,policy,previous=None):
    from .anytime import collect
    from .prediction import prefix
    field=Snapshot.load(case['snapshot_file']);started=time.monotonic_ns();deadline=started+500_000_000
    mode=policy.get('prediction_mode')
    if mode is None:raise ValueError('Register the current-path prediction model before execution')
    motion=prefix(case,.5,mode);B=motion['B_pred'];v0=motion['previous_vw'][0]
    candidates,sigma,flags=prepare_candidates(case['samples_world'],B,case.get('old_path'),policy['short_policy'])
    lateral,component=side_initializations(candidates,B,field);starts=list(candidates)+lateral
    payloads=[dict(index=i,B=B,v0=v0,candidates=candidates,sigma=sigma,path=path,weights=weights,deadline_ns=deadline,snapshot_file=case['snapshot_file']) for i,path in enumerate(starts)]
    delivery=collect(pool,payloads,deadline);ended=time.monotonic_ns();selected=delivery['selected']
    attempts=[]
    for i in range(len(starts)):
        data=delivery['latest'].get(i,{})
        attempts.append(dict(index=i,completed_before_cutoff=data.get('kind')=='DONE',iteration=data.get('iteration'),iteration_limit=data.get('iteration_limit'),
            active_obstacle=data.get('active_obstacle'),active_kinematic=data.get('active_kinematic'),violated_obstacle=data.get('violated_obstacle'),violated_kinematic=data.get('violated_kinematic'),
            mixture_switches=data.get('mixture_switches',0),started_before_cutoff=bool(data)))
    return dict(accepted=selected is not None,disposition='FEASIBLE_ANYTIME' if selected else 'NO_FEASIBLE_BEFORE_DEADLINE',selected=selected,
        path=selected['path'] if selected else None,poses=selected['poses'] if selected else None,dt=selected['dt'] if selected else None,
        B_pred=B,application_previous_vw=motion['previous_vw'],prediction=motion,application_delay_s=.5,source_B=case['B'],
        sigma_policy_m=sigma,candidate_flags=flags,component=component,initialization_count=len(starts),attempts=attempts,
        compute_s=(ended-started)/1e9,deadline_s=.5,deadline_overrun=ended>deadline,dispatch_ns=started,deadline_ns=deadline,returned_ns=ended,
        active_candidate=selected.get('active_candidate') if selected else None,selected_initialization=selected.get('index') if selected else None,
        pending_at_cutoff=delivery['pending_at_cutoff'],anytime_messages=delivery['messages'],late_results_used=False,
        warm_start_available=False,warm_start_used=False,warm_start_selected=False,active_switches=sum(r['mixture_switches'] for r in attempts),iterate_count=sum(r.get('iteration') or 0 for r in attempts))

class Replanner:
    """Arrival-driven interface: nominal4Hz. No synthetic arrivals or online hooks."""
    period_s=.25
    def __init__(self,pool,weights,policy):self.pool=pool;self.weights=weights;self.policy=policy;self.previous={}
    def key(self,case):return (case['split'],case['run'])
    def remember(self,case,result):
        if result['accepted']:self.previous[self.key(case)]=dict(plan=result,case_id=case['case_id'],tick=case['tick'])
    def on_candidates(self,case):
        prior=self.previous.get(self.key(case));usable=prior is not None and prior['tick']<case['tick']
        result=plan(self.pool,case,self.weights,self.policy,previous=prior['plan'] if usable else None)
        result.update(nominal_candidate_period_s=self.period_s,warm_source_case_id=prior['case_id'] if usable else None,
            warm_source_gap_s=(case['tick']-prior['tick'])/72 if usable else None)
        self.remember(case,result);return result
