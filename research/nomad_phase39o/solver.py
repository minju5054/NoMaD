"""Fixed-cost SLSQP with L1 SDF slack and the registered escape schedule."""
import time
import numpy as np
from scipy.optimize import Bounds,minimize
from nomad_phase0.graph_v4 import norm,menger
from nomad_phase19r.repair import initialize
from nomad_phase20.repair import RepairGraphR2,solve_sample as frozen_r2
from nomad_phase20c.detour_known import KnownDetourGraph,solve_initialization as frozen_r3

RHO=1000.;SLACK_TOL=1e-6;TOL=1e-7
VARIANTS=('V0','V1','V2','V3')

def arc_data(graph,x):
    p=graph.points(x);delta=np.diff(p,axis=0);length=norm(delta);n=len(length);jl=np.zeros((n,len(x)))
    for i in range(n):
        if i:jl[i,2*(i-1):2*i]-=delta[i]/length[i]
        jl[i,2*i:2*i+2]+=delta[i]/length[i]
    fractions=np.linspace(0,1,9)
    starts=np.r_[0.,np.cumsum(length)[:-1]];jstarts=np.vstack([np.zeros(len(x)),np.cumsum(jl,axis=0)[:-1]])
    s=(starts[:,None]+length[:,None]*fractions).ravel()
    js=(jstarts[:,None,:]+fractions[None,:,None]*jl[:,None,:]).reshape(n*9,len(x))
    return s,js

def escape_threshold(cB,s):
    s=np.asarray(s);return np.where(s<=.3,np.minimum(.025,cB-.005+.5*s),.025)

def certificate(graph,path,escape):
    if not escape:return graph.certificate(path)
    # Keep exact segment-to-occupied-site geometry; only compare each closed
    # segment (split at .3m) to the threshold at its conservative far endpoint.
    p=np.asarray(path,float);length=norm(np.diff(p,axis=0));starts=np.r_[0.,np.cumsum(length)]
    details=[];base=getattr(graph,'base_field',graph.field);strict=getattr(graph,'strict_field',base)
    for i,(a,b) in enumerate(zip(p[:-1],p[1:])):
        cuts=[starts[i]]
        if starts[i]<.3<starts[i+1]:cuts.append(.3)
        cuts.append(starts[i+1])
        for lo,hi in zip(cuts[:-1],cuts[1:]):
            q=np.array([a+(lo-starts[i])/length[i]*(b-a),a+(hi-starts[i])/length[i]*(b-a)])
            far=lo>=.3;field=strict if far else base;threshold=.025 if far else float(escape_threshold(graph.cB,hi))
            gap=float(field.exact_clearance(q));details.append(dict(s_a=float(lo),s_b=float(hi),threshold_m=threshold,exact_clearance_m=gap,strict_field=far))
    return dict(certificate_pass=all(r['exact_clearance_m']>=r['threshold_m'] for r in details),
        depth_clearance_m=min(r['exact_clearance_m'] for r in details),certificate_segments=details,escape_certificate=True)

class SlackGraph:
    def __init__(self,graph,variant):
        assert variant in ('V1','V2','V3');self.graph=graph;self.variant=variant;self.n=len(graph.initial)
        self.m=(len(graph.points(graph.initial))-1)*9;self.escape=variant in ('V2','V3') and graph.cB<.025
        g,_=self.physical_constraints(graph.initial);self.initial=np.r_[graph.initial,np.maximum(0.,-g[:self.m])]
        self.bounds=Bounds(np.r_[graph.bounds.lb,np.zeros(self.m)],np.r_[graph.bounds.ub,np.full(self.m,np.inf)])
    def physical_constraints(self,x):
        g,j=self.graph.constraints(x);g=g.copy();j=j.copy()
        if self.escape:
            s,js=arc_data(self.graph,x);old=np.where(s<=.3,self.graph.near_threshold,.025);new=escape_threshold(self.graph.cB,s)
            g[:self.m]+=old-new
            active=(s<=.3)&(self.graph.cB-.005+.5*s<.025);j[:self.m]-=.5*active[:,None]*js
        return g,j
    def objective(self,z):
        cost,j=self.graph.objective(z[:self.n]);return float(cost+RHO*z[self.n:].sum()),np.r_[j,np.full(self.m,RHO)]
    def constraints(self,z):
        g,j=self.physical_constraints(z[:self.n]);g[:self.m]+=z[self.n:]
        slack_j=np.zeros((len(g),self.m));slack_j[:self.m]=np.eye(self.m)
        return g,np.c_[j,slack_j]
    def solve(self):
        start=time.perf_counter();graph=self.graph
        if graph.cB<0 and not self.escape:return dict(accepted=False,disposition='NEGATIVE_DEPTH_AT_B',path=None,solver_started=False,cB=graph.cB,attempt_wall_s=time.perf_counter()-start)
        result=minimize(lambda z:self.objective(z)[0],self.initial,jac=lambda z:self.objective(z)[1],method='SLSQP',bounds=self.bounds,
            constraints=[dict(type='ineq',fun=lambda z:self.constraints(z)[0],jac=lambda z:self.constraints(z)[1])],options=dict(maxiter=100,ftol=1e-8,disp=False))
        solver_s=time.perf_counter()-start;x=result.x[:self.n];slack=result.x[self.n:];path=graph.points(x);g,_=self.physical_constraints(x)
        violation=max(0.,float(-g.min()),float(np.max(graph.bounds.lb-x)),float(np.max(x-graph.bounds.ub)),float(-slack.min()))
        cert=certificate(graph,path,self.escape);r3=hasattr(graph,'u');progress=float((path[-1]-graph.B[:2])@graph.u) if r3 else None
        accepted=bool(result.success and violation<=TOL and float(slack.max())<=SLACK_TOL and cert['certificate_pass'] and (not r3 or progress>=.5))
        disposition='ACCEPTED' if accepted else 'NONCONVERGED' if not result.success else 'CONSTRAINT_FAILED' if violation>TOL else 'SLACK_REJECTED' if slack.max()>SLACK_TOL else 'CERTIFICATE_REJECTED' if not cert['certificate_pass'] else 'INSUFFICIENT_PROGRESS'
        return dict(accepted=accepted,disposition=disposition,path=path.tolist(),solver_started=True,solver_success=bool(result.success),solver_status=int(result.status),message=str(result.message),
            iterations=int(result.nit),objective=float(result.fun),original_objective=float(graph.objective(x)[0]),slack_l1_cost=float(RHO*slack.sum()),xi_max=float(slack.max()),xi=slack.tolist(),
            constraint_violation=violation,augmented_constraint_violation=max(0.,float(-self.constraints(result.x)[0].min())),**cert,
            progress_m=progress,length_m=float(norm(np.diff(path,axis=0)).sum()),maximum_abs_curvature_m_inv=float(np.abs(menger(path)[0]).max()),
            cB=graph.cB,escape_schedule=self.escape,escape_negative_B=bool(graph.cB<0),
            fixed_B_constraint_m=float(g[0]),fixed_B_escape_upper_m=float(.005-norm(path[1:2]-path[:1])[0]/16) if self.escape else None,
            solver_wall_s=solver_s,attempt_wall_s=time.perf_counter()-start)

def solve(kind,index,job,base,strict):
    variant=job['variant'];start=time.perf_counter()
    from nomad_phase20c.detour import ANGLES
    if variant=='V0':return frozen_r2(job['samples_world'][index],job['B'],base) if kind=='R2' else frozen_r3(job['B'],job['u_ref'],base,strict,ANGLES[index])
    if kind=='R2':
        cB=float(base.query(np.asarray(job['B'])[None,:2])[0][0])-base.error_bound
        if variant=='V1' and cB<0:return dict(accepted=False,disposition='NEGATIVE_DEPTH_AT_B',path=None,solver_started=False,cB=cB)
        reference,init=initialize(job['samples_world'][index],job['B'])
        if reference is None:return dict(init,accepted=False,path=None,solver_started=False)
        graph=RepairGraphR2(reference,job['B'],base)
    else:
        graph=KnownDetourGraph(job['B'],job['u_ref'],base,strict,ANGLES[index] if index<7 else 0)
        if index>=7:
            graph.initial_path=np.asarray(job['extra_initializations'][index-7]['path']);graph.initial=graph.initial_path[1:].ravel().copy()
        if variant=='V1' and graph.cB<0:
            return dict(accepted=False,disposition='NEGATIVE_DEPTH_AT_B',path=None,initial_path=graph.initial_path.tolist(),
                solver_started=False,cB=graph.cB,total_attempt_s=time.perf_counter()-start)
    try:
        r=SlackGraph(graph,variant).solve()
        if kind=='R2' and r.get('path') is not None:
            edits=norm(np.asarray(r['path'])-reference);r.update(mean_edit_m=float(edits.mean()),max_edit_m=float(edits.max()),reference=reference.tolist())
        if kind=='R3':r['initial_path']=graph.initial_path.tolist()
        r['total_attempt_s']=time.perf_counter()-start;return r
    except ValueError as exc:return dict(accepted=False,disposition='SDF_OR_NUMERICAL_ERROR',path=None,solver_started=True,error=str(exc),total_attempt_s=time.perf_counter()-start)
