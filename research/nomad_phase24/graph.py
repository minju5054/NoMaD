"""One normal/detour graph, analytic factors, frozen500ms output policy."""
import time,types
import numpy as np
from nomad_phase23.graph import UnifiedGraph,prepare_candidates,resample
from nomad_phase23.optimized import OptimizedGraph
from nomad_phase23.prediction import prefix
from nomad_phase15b.depth import Snapshot,evaluate_samples
from nomad_phase15.evaluate import suffix
from nomad_phase20c.detour import ANGLES
from nomad_phase23o3 import graph as output_policy

class GraphG(OptimizedGraph):
    def __init__(self,B,v0,candidates,sigma,field,weights,deadline_ns,kinematic_sigma=.03):
        self.mode=weights['mode'];assert self.mode in ('NORMAL','DETOUR')
        reference=np.asarray(candidates)[0] if self.mode=='NORMAL' else np.repeat(np.asarray(B)[None,:2],11,axis=0)
        super().__init__(B,v0,reference[None],sigma if self.mode=='NORMAL' else 1.,field,dict(time=1.,goal=1. if self.mode=='NORMAL' else 0.,curvature=.01),deadline_ns,kinematic_sigma)
        self.u=np.asarray(weights['u_ref'])@self.R if self.mode=='DETOUR' else None
        if self.u is not None:np.testing.assert_allclose(np.linalg.norm(self.u),1.,atol=1e-12)
        self.full_constraint_cache=None
    def active(self,p):
        value=float(np.sum((p[1:]-self.candidates[0,1:])**2)/self.sigma**2) if self.mode=='NORMAL' else 0.
        return 0,np.array([value])
    def full_constraints(self,x):
        self.check()
        if self.full_constraint_cache is None or not np.array_equal(x,self.full_constraint_cache[0]):
            self.constraint_kernel_calls+=1;self.full_constraint_cache=(np.array(x,copy=True),UnifiedGraph.constraints(self,x))
        return self.full_constraint_cache[1]
    def constraints(self,x):
        h,j=self.full_constraints(x);self.constraint_cache=(np.array(x,copy=True),(h[:-20],j[:-20]));return self.constraint_cache[1]
    def objective(self,x):
        self.check()
        if self.objective_cache is not None and np.array_equal(x,self.objective_cache[0]):return self.objective_cache[1]
        value,grad=self._objective_kernel(x);p,_,_=self.unpack(x)
        if self.mode=='DETOUR':
            # The reused kernel's placeholder F1 value is zero; remove its
            # quadratic gradient too. No reference or endpoint prior remains.
            grad-=2*np.einsum('qi,qij->j',p[1:],self.jp[1:])
            r=max(0.,1.2-float((p[-1]-p[0])@self.u))/.10;value+=r*r;grad+=-2*r/.10*self.u@(self.jp[-1]-self.jp[0])
        h,j=self.full_constraints(x);acc=.5-h[-20:-10];jac=-j[-20:-10];r=np.maximum(0,np.abs(acc)-.5)/.05
        value+=float(r@r);grad+=(2*r*np.sign(acc)/.05)@jac
        self.objective_cache=(np.array(x,copy=True),(value,grad));return self.objective_cache[1]

# Reuse the registered FEASIBLE -> tolerated-last-iterate -> STOP solver.
_kernel=types.FunctionType(output_policy.worker.__code__,dict(output_policy.worker.__globals__,U3Graph=GraphG),argdefs=output_policy.worker.__defaults__)
def worker(payload,channel):return _kernel(payload,channel)


def normal_inputs(case,B,field):
    samples=np.asarray(case['samples_world']);_,detail=evaluate_samples(samples,B,field)
    ranked=sorted(detail['candidates'],key=lambda r:(-r['remaining_length_m'],r['index']));safe=[r for r in ranked if r['safe']]
    selected=(safe or ranked)[0]['index'];old=None if case.get('U_old_withheld_ASTAR') else case.get('old_path')
    prepared,sigma,flags=prepare_candidates(samples,B,old,'retain');reference=prepared[selected];starts=[reference];names=['REFERENCE']
    old_reason='NO_OLD'
    if old is not None:
        tail,length=suffix(old,B)
        if length>1e-9:starts.append(resample(np.vstack([np.asarray(B)[:2],tail])));names.append('OLD_REMAINDER');old_reason='USED'
        else:old_reason='NO_REMAINING_ARCLENGTH'
    elif case.get('U_old_withheld_ASTAR'):old_reason='ASTAR_OLD_EXCLUDED'
    extra=[r['index'] for r in safe if r['index']!=selected][:2]
    for i in extra:starts.append(prepared[i]);names.append('SAFE_'+str(i))
    return dict(reference=reference,sigma=sigma,starts=starts,names=names,selected_sample=selected,all_unsafe=not bool(safe),safe_count=len(safe),old_reason=old_reason,details=detail,candidate_flags=flags)

def fan_paths(B,u_ref):
    yaw=float(np.arctan2(u_ref[1],u_ref[0]));return [np.asarray(B)[:2]+np.linspace(0.,1.5,11)[:,None]*np.array([np.cos(yaw+np.deg2rad(a)),np.sin(yaw+np.deg2rad(a))]) for a in ANGLES]

def plan(pool,case,mode,u_ref,policy):
    field=Snapshot.load(case['snapshot_file']);start=time.monotonic_ns();deadline=start+500_000_000;motion=prefix(case,.5,policy['prediction_mode']);B=motion['B_pred']
    if mode=='NORMAL':
        selection=normal_inputs(case,B,field);reference=selection['reference'];sigma=selection['sigma'];starts=selection['starts'];names=selection['names']
    else:
        assert mode=='DETOUR' and u_ref is not None;reference=None;sigma=1.;starts=fan_paths(B,u_ref);names=['FAN_'+str(a) for a in ANGLES];selection=None
    placeholder=np.repeat(np.asarray(B)[None,:2],11,axis=0);candidates=np.asarray([reference if reference is not None else placeholder])
    weights=dict(mode=mode,u_ref=u_ref)
    payloads=[dict(index=i,B=B,v0=motion['previous_vw'][0],candidates=candidates,sigma=sigma,path=path,weights=weights,deadline_ns=deadline,snapshot_file=case['snapshot_file']) for i,path in enumerate(starts)]
    delivery=output_policy.Collector.collect(pool,payloads,deadline,task=worker);ended=time.monotonic_ns();chosen=delivery['selected'];attempts=[]
    for i,name in enumerate(names):
        d=delivery['latest'].get(i,{})
        attempts.append(dict(index=i,name=name,iteration=d.get('iteration'),iteration_limit=d.get('iteration_limit'),completed_before_cutoff=d.get('kind')=='DONE',active_obstacle=d.get('active_obstacle'),active_kinematic=d.get('active_kinematic'),active_dt_bound=d.get('active_dt_bound')))
    return dict(accepted=chosen is not None,output_type=chosen['output_type'] if chosen else 'STOP',disposition=chosen['output_type'] if chosen else 'STOP',selected=chosen,
        path=chosen['path'] if chosen else None,poses=chosen['poses'] if chosen else None,dt=chosen['dt'] if chosen else None,
        mode=mode,reference=reference.tolist() if reference is not None else None,u_ref=u_ref,sigma_reference=sigma,selection=selection,
        B_pred=B,application_previous_vw=motion['previous_vw'],prediction=motion,application_delay_s=.5,source_B=case['B'],
        compute_s=(ended-start)/1e9,deadline_s=.5,deadline_overrun=ended>deadline,selected_initialization=names[chosen['index']] if chosen else None,
        initializations=[dict(name=n,path=np.asarray(q).tolist()) for n,q in zip(names,starts)],attempts=attempts,anytime_messages=delivery['messages'],pending_at_cutoff=delivery['pending_at_cutoff'],late_results_used=False)
