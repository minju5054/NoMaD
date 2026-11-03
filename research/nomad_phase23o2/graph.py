"""U2: soft acceleration, robust max-mixture, aged observed candidate sets."""
import time,types
import numpy as np
from nomad_phase23.graph import UnifiedGraph,prepare_candidates,side_initializations
from nomad_phase23.optimized import OptimizedGraph
from nomad_phase23 import anytime
from nomad_phase23.prediction import prefix
from nomad_phase15b.depth import Snapshot

FIXED_WEIGHTS=dict(time=1.,goal=1.,curvature=.01)

class U2Graph(OptimizedGraph):
    def __init__(self,B,v0,candidates,sigma,field,weights,deadline_ns,kinematic_sigma=.03):
        config=weights['u2'];self.cauchy_c=float(config['c']);self.memory_T=float(config['T_m']);self.ages=np.asarray(config['ages_s'],float)
        assert len(self.ages)==len(candidates) and np.all(self.ages>=0)
        self.component_sigma=sigma*(1+self.ages/self.memory_T);self.age_cost=self.ages/self.memory_T;self.full_constraint_cache=None
        super().__init__(B,v0,candidates,sigma,field,FIXED_WEIGHTS,deadline_ns,kinematic_sigma)
    def active(self,p):
        delta=self.candidates[:,1:]-p[None,1:];r2=np.sum(delta*delta,axis=2)/self.component_sigma[:,None]**2;c2=self.cauchy_c**2
        costs=np.sum(c2*np.log1p(r2/c2),axis=1)+self.age_cost
        return int(np.argmin(costs)),costs
    def full_constraints(self,x):
        self.check()
        if self.full_constraint_cache is None or not np.array_equal(x,self.full_constraint_cache[0]):
            self.constraint_kernel_calls+=1;self.full_constraint_cache=(np.array(x,copy=True),UnifiedGraph.constraints(self,x))
        return self.full_constraint_cache[1]
    def constraints(self,x):
        h,j=self.full_constraints(x)
        # Last20rows are the ten acceleration upper/lower bounds, including
        # acceleration from actual initial speed. Everything else stays hard.
        self.constraint_cache=(np.array(x,copy=True),(h[:-20],j[:-20]));return self.constraint_cache[1]
    def objective(self,x):
        self.check()
        if self.objective_cache is not None and np.array_equal(x,self.objective_cache[0]):return self.objective_cache[1]
        # Reuse all frozen F2-F6 code. Its F1 value already calls our active();
        # replace only its quadratic F1 gradient by the matching Cauchy gradient.
        value,gradient=self._objective_kernel(x);p,_,_=self.unpack(x);active,_=self.active(p);delta=p[1:]-self.candidates[active,1:]
        gradient-=2*np.einsum('qi,qij->j',delta,self.jp[1:])/self.sigma**2
        sigma=self.component_sigma[active];den=sigma*sigma+np.sum(delta*delta,axis=1)/self.cauchy_c**2
        gradient+=np.einsum('qi,qij->j',2*delta/den[:,None],self.jp[1:])
        h,j=self.full_constraints(x);acc=.5-h[-20:-10];ja=-j[-20:-10];residual=np.maximum(0,np.abs(acc)-.5)/.05
        value+=float(residual@residual);gradient+=(2*residual*np.sign(acc)/.05)@ja
        self.objective_cache=(np.array(x,copy=True),(value,gradient));return self.objective_cache[1]

# The500ms streaming SLSQP worker is identical except its graph class binding.
_kernel=types.FunctionType(anytime.worker.__code__,dict(anytime.worker.__globals__,OptimizedGraph=U2Graph),argdefs=anytime.worker.__defaults__)
def worker(payload,channel):return _kernel(payload,channel)


def mixture(case,B):
    current,sigma,flags=prepare_candidates(case['samples_world'],B,case.get('old_path'),'retain')
    age0=float(case.get('current_input_age_s',0.));candidates=list(current);ages=[age0]*8;metadata=[dict(set_index=0,sample=i,age_s=age0,fresh_id=case['fresh_id'],**{k:v for k,v in flags[i].items() if k!='sample'}) for i in range(8)]
    sets=case.get('memory_sets',[])
    assert len(sets)<=7
    for k,item in enumerate(sets,1):
        assert item['kind']=='NATIVE_NOMAD','A*-derived OLD is not a mixture component'
        age=float(item['age_s']);assert 0<=age<=2.+1e-9
        # History is native geometry only: no applied OLD/A* supplementation.
        q,_,ff=prepare_candidates(item['samples_world'],B,None,'retain')
        candidates.extend(q);ages.extend([age]*8)
        metadata.extend(dict(set_index=k,sample=i,age_s=age,fresh_id=item['fresh_id'],**{a:v for a,v in ff[i].items() if a!='sample'}) for i in range(8))
    return np.asarray(candidates),sigma,np.asarray(ages),metadata,current


def plan(pool,case,settings,policy):
    field=Snapshot.load(case['snapshot_file']);start=time.monotonic_ns();deadline=start+500_000_000
    motion=prefix(case,.5,policy['prediction_mode']);B=motion['B_pred'];candidates,sigma,ages,metadata,current=mixture(case,B)
    sides,component=side_initializations(current,B,field);starts=list(current)+sides
    weights=dict(FIXED_WEIGHTS,u2=dict(settings,ages_s=ages.tolist()))
    payloads=[dict(index=i,B=B,v0=motion['previous_vw'][0],candidates=candidates,sigma=sigma,path=path,weights=weights,deadline_ns=deadline,snapshot_file=case['snapshot_file']) for i,path in enumerate(starts)]
    delivery=anytime.collect(pool,payloads,deadline,task=worker);end=time.monotonic_ns();selected=delivery['selected'];attempts=[]
    for i in range(len(starts)):
        d=delivery['latest'].get(i,{})
        attempts.append(dict(index=i,completed_before_cutoff=d.get('kind')=='DONE',iteration=d.get('iteration'),iteration_limit=d.get('iteration_limit'),
            active_obstacle=d.get('active_obstacle'),active_kinematic=d.get('active_kinematic'),active_dt_bound=d.get('active_dt_bound'),violated_obstacle=d.get('violated_obstacle'),violated_kinematic=d.get('violated_kinematic'),mixture_switches=d.get('mixture_switches',0)))
    chosen=metadata[selected['active_candidate']] if selected else None;deviation=None
    if selected:deviation=np.linalg.norm(np.asarray(selected['path'])[1:]-candidates[selected['active_candidate'],1:],axis=1)
    return dict(accepted=selected is not None,disposition='FEASIBLE_ANYTIME' if selected else 'NO_FEASIBLE_BEFORE_DEADLINE',selected=selected,
        path=selected['path'] if selected else None,poses=selected['poses'] if selected else None,dt=selected['dt'] if selected else None,
        B_pred=B,application_previous_vw=motion['previous_vw'],prediction=motion,application_delay_s=.5,source_B=case['B'],
        sigma_policy_m=sigma,candidate_flags=metadata,component=component,initialization_count=len(starts),attempts=attempts,
        compute_s=(end-start)/1e9,deadline_s=.5,deadline_overrun=end>deadline,dispatch_ns=start,deadline_ns=deadline,returned_ns=end,
        active_candidate=selected.get('active_candidate') if selected else None,selected_initialization=selected.get('index') if selected else None,
        active_component=chosen,prior_deviation_max_m=float(deviation.max()) if deviation is not None else None,prior_deviation_mean_m=float(deviation.mean()) if deviation is not None else None,
        pending_at_cutoff=delivery['pending_at_cutoff'],anytime_messages=delivery['messages'],late_results_used=False,
        warm_start_available=False,warm_start_used=False,warm_start_selected=False,active_switches=sum(r['mixture_switches'] for r in attempts),iterate_count=sum(r.get('iteration') or 0 for r in attempts))
