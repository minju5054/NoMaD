"""Non-search seeds plus an optional prior-U warm start; one250ms/four-worker budget."""
import time
import numpy as np
from nomad_phase15b.depth import Snapshot
from nomad_phase0.pure_pursuit import XYPath
from .graph import prepare_candidates,side_initializations,solve_start

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
    field=Snapshot.load(case['snapshot_file']);started=time.monotonic_ns();deadline=started+250_000_000
    candidates,sigma,flags=prepare_candidates(case['samples_world'],case['B'],case.get('old_path'),policy['short_policy'])
    lateral,component=side_initializations(candidates,case['B'],field);starts=[(i,path,None) for i,path in enumerate(list(candidates)+lateral)]
    warm=warm_suffix(previous,case['B']) if previous is not None else None
    if warm is not None:starts.insert(0,(-1,np.asarray(warm['poses'])[:,:2],warm))
    args=[(i,{k:case[k] for k in ('snapshot_file','B','previous_vw')},candidates,sigma,path,weights,deadline,policy['kinematic_sigma'],initial) for i,path,initial in starts]
    results=list(pool.map(worker,args));ended=time.monotonic_ns();overrun=ended>deadline
    feasible=[r for r in results if r['accepted'] and r['ready_ns']<=deadline]
    best=min(feasible,key=lambda r:(r['cost'],r['index'])) if feasible else None
    selected=best if not overrun else None  # Late output must brake, not execute a late plan.
    return dict(accepted=selected is not None,disposition='TIMEOUT' if overrun else 'FEASIBLE' if selected else 'NO_FEASIBLE_BEFORE_DEADLINE',selected=selected,
        path=selected['path'] if selected else None,poses=selected['poses'] if selected else None,dt=selected['dt'] if selected else None,
        sigma_policy_m=sigma,candidate_flags=flags,component=component,initialization_count=len(starts),attempts=results,
        compute_s=(ended-started)/1e9,deadline_s=.25,deadline_overrun=overrun,active_candidate=selected.get('active_candidate') if selected else None,
        warm_start_available=previous is not None,warm_start_used=warm is not None,warm_start_selected=selected is not None and selected['index']==-1,
        feasible_before_deadline_but_discarded=overrun and best is not None,
        active_switches=sum(r['active_switches'] for r in results),iterate_count=sum(r['iterate_count'] for r in results))

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
