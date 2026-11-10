"""Reduced SE(2) execution factor graph: fixed PP states eliminated exactly."""
import time
import numpy as np
from scipy.optimize import minimize,Bounds
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase15.evaluate import suffix
from nomad_phase32o.exec_cert import swept_clearance
from . import fast
from .rollout import certify

FD_STEP=1e-6;MAXITER=100;FTOL=1e-8;TRUST=.75

def reference(native,B):
    tail,_=suffix(np.asarray(native,float),B)
    try:
        path=XYPath(np.vstack([np.asarray(B)[:2],tail]));q=np.array([path.at(s) for s in np.linspace(0,path.s[-1],8)]);q[0]=B[:2]
        return q
    except ValueError:return None

class ExecutionGraph:
    def __init__(self,q,B,vw,field):
        self.q=q;self.B=np.asarray(B,float);self.vw=np.asarray(vw,float);self.field=field
        self.x0=q[1:].ravel().copy();self.bounds=Bounds(self.x0-TRUST,self.x0+TRUST);self.cache=None;self.evaluations=0
    def points(self,x):return np.vstack([self.B[:2],np.asarray(x).reshape(7,2)])
    def objective(self,x):
        delta=x-self.x0;return float(delta@delta),2*delta
    def constraint(self,x):
        if self.cache is None or not np.array_equal(self.cache[0],x):
            self.evaluations+=1;trajectory=fast.trace(self.points(x),self.B,self.vw)
            value=fast.clearance(trajectory,self.field)-.025
            self.cache=(x.copy(),float(value))
        return self.cache[1]

def solve_candidate(native,B,vw,field,index):
    start=time.perf_counter();q=reference(native,B)
    base=dict(sample=index,accepted=False,gradient='objective analytic;execution min-clearance 2-point finite difference eps=1e-6m',fd_step_m=FD_STEP)
    if q is None:return dict(base,solver_status=None,solver_message='DEGENERATE_SUFFIX',solver_started=False,wall_s=time.perf_counter()-start)
    g=ExecutionGraph(q,B,vw,field)
    r=minimize(lambda x:g.objective(x)[0],g.x0,jac=lambda x:g.objective(x)[1],method='SLSQP',bounds=g.bounds,
        constraints=[dict(type='ineq',fun=g.constraint)],options=dict(maxiter=MAXITER,ftol=FTOL,eps=FD_STEP,disp=False))
    numerical_s=time.perf_counter()-start;violation=max(0.,-g.constraint(r.x),float(np.max(g.bounds.lb-r.x)),float(np.max(r.x-g.bounds.ub)))
    path=g.points(r.x);checked=None
    if r.success and violation<=1e-7:
        checked=certify(B,vw,path,field,return_trace=True)
    accepted=bool(checked is not None and checked['passed'] and checked['stopped'] and checked['terminal_vw']==[0.,0.])
    edits=np.linalg.norm(path-q,axis=1)
    result=dict(base,accepted=accepted,solver_started=True,solver_success=bool(r.success),solver_status=int(r.status),solver_message=str(r.message),
        iterations=int(r.nit),function_evaluations=int(r.nfev),constraint_evaluations=g.evaluations,objective=float(r.fun),
        constraint_violation_m=violation,independent_ec_pass=checked['passed'] if checked else None,
        independent_clearance_m=checked.get('clearance_m') if checked else None,numerical_s=numerical_s,wall_s=time.perf_counter()-start,
        mean_displacement_m=float(edits.mean()),max_displacement_m=float(edits.max()),path=path.tolist(),reference=q.tolist())
    if accepted:
        trace=checked.pop('trace');result.update(verification=checked,trajectory=trace['poses'].tolist(),commands=trace['commands'].tolist(),
            displacement_from_B_m=float(np.linalg.norm(trace['poses'][-1,:2]-np.asarray(B)[:2])),
            travel_m=float(np.linalg.norm(np.diff(trace['poses'][:,:2],axis=0),axis=1).sum()))
    return result

def solve_event(job,field):
    started=time.perf_counter();B=job['pose'];vw=job['vw'];original=[]
    for p in job['candidates']:
        try:r=certify(B,vw,p,field);original.append(dict(passed=r['passed'],clearance_m=r.get('clearance_m')))
        except ValueError as e:original.append(dict(passed=False,error=str(e)))
    initial=swept_clearance(field,np.asarray([B]),np.empty((0,2)))
    if not initial['passed']:
        candidates=[dict(sample=i,accepted=False,solver_started=False,solver_status=None,solver_message='INFEASIBLE_FIXED_INITIAL_STATE',wall_s=0.) for i in range(8)]
    else:candidates=[solve_candidate(p,B,vw,field,i) for i,p in enumerate(job['candidates'])]
    accepted=[i for i,c in enumerate(candidates) if c['accepted']]
    selected=min(accepted,key=lambda i:(candidates[i]['objective'],i)) if accepted else None
    return dict(event_id=job['event_id'],phase=job['phase'],scene=job['scene'],method=job['method'],seed=job['seed'],time_s=job['time_s'],
        selected=selected,found=selected is not None,results=candidates,original_candidates=original,
        original_any_tail_pass=any(c['passed'] for c in original),all_original_reject=not any(c['passed'] for c in original),
        independent_ec_used=True,initial_state_pass=initial['passed'],initial_clearance_m=initial.get('clearance_m'),
        eight_start_s=time.perf_counter()-started)
