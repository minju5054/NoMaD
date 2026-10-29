"""14-variable, fixed-B SLSQP repair with explicit analytic derivatives."""
import time
import numpy as np
from scipy.optimize import Bounds,minimize
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase0.graph_v4 import norm,menger
from nomad_phase15.evaluate import suffix

SIGMA_P=.10
SIGMA_S=.02
SIGMA_H=np.pi/6
SAFETY=.025
TOL=1e-7


def initialize(native,B):
    """Retain the suffix in world coordinates; explicitly connect B to its projection."""
    tail,remaining=suffix(np.asarray(native),B)
    if remaining<.25:return None,dict(disposition='SHORT_REMAINING',remaining_m=remaining)
    path=XYPath(np.vstack([np.asarray(B)[:2],tail]))
    reference=np.array([path.at(s) for s in np.linspace(0,path.s[-1],8)])
    reference[0]=np.asarray(B)[:2]
    lengths=np.linalg.norm(np.diff(reference,axis=0),axis=1)
    if np.any(lengths<=1e-10):return None,dict(disposition='DEGENERATE_INITIALIZATION',remaining_m=remaining)
    return reference,dict(remaining_m=remaining,connector_m=float(np.linalg.norm(tail[0]-np.asarray(B)[:2])),
        resampled_length_m=float(lengths.sum()),initial_segment_lengths_m=lengths.tolist())


class RepairGraph:
    def __init__(self,reference,B,field):
        self.q=np.asarray(reference,dtype=float);self.B=np.asarray(B,dtype=float);self.field=field
        assert self.q.shape==(8,2) and np.isfinite(self.q).all()
        np.testing.assert_array_equal(self.q[0],self.B[:2])
        self.initial=self.q[1:].ravel().copy();self.lengths=norm(np.diff(self.q,axis=0))
        self.bounds=Bounds(self.initial-.75,self.initial+.75)
        D=np.zeros((6,8))
        for i in range(6):D[i,i:i+3]=[1.,-2.,1.]
        self.D=D;self.smooth_j=np.kron(D[:,1:],np.eye(2))/SIGMA_S
        self.sample_matrix=np.zeros((63,8));self.segment_ids=np.repeat(np.arange(7),9)
        for i in range(7):
            for k,f in enumerate(np.linspace(0.,1.,9)):self.sample_matrix[9*i+k,i:i+2]=[1-f,f]
        self._objective_cache=None;self._constraint_cache=None

    def points(self,x):return np.vstack([self.B[:2],np.asarray(x).reshape(7,2)])

    def residual_jacobian(self,x):
        p=self.points(x);delta=p[1]-p[0];den=max(float(delta@delta),1e-24)
        angle=np.arctan2(delta[1],delta[0])-self.B[2]
        heading=2*np.sin(angle/2)/SIGMA_H
        jh=np.zeros((1,14));jh[0,:2]=np.cos(angle/2)/SIGMA_H*np.array([-delta[1],delta[0]])/den
        r=np.r_[(p[1:]-self.q[1:]).ravel()/SIGMA_P,(self.D@p).ravel()/SIGMA_S,heading]
        return r,np.vstack([np.eye(14)/SIGMA_P,self.smooth_j,jh])

    def objective(self,x):
        if self._objective_cache is None or not np.array_equal(x,self._objective_cache[0]):
            r,j=self.residual_jacobian(x);self._objective_cache=(x.copy(),.5*float(r@r),j.T@r)
        return self._objective_cache[1:]

    def constraints(self,x):
        if self._constraint_cache is not None and np.array_equal(x,self._constraint_cache[0]):return self._constraint_cache[1:]
        p=self.points(x);delta=np.diff(p,axis=0);lengths=norm(delta);jl=np.zeros((7,14))
        for i in range(7):
            if i:jl[i,2*(i-1):2*i]-=delta[i]/lengths[i]
            jl[i,2*i:2*i+2]+=delta[i]/lengths[i]
        points=self.sample_matrix@p;distance,grad=self.field.query(points)
        sdf=distance-self.field.error_bound-lengths[self.segment_ids]/16-SAFETY
        js=np.zeros((63,14));js[:,0::2]=grad[:,0,None]*self.sample_matrix[:,1:];js[:,1::2]=grad[:,1,None]*self.sample_matrix[:,1:]
        js-=jl[self.segment_ids]/16
        k,jk=menger(p);jk=jk[:,1:,:].reshape(6,14)
        g=np.r_[sdf,8-k,8+k,lengths-.5*self.lengths,lengths.sum()-.7*self.lengths.sum()]
        j=np.vstack([js,-jk,jk,jl,jl.sum(axis=0)])
        self._constraint_cache=(x.copy(),g,j)
        return g,j

    def solve(self):
        start=time.perf_counter()
        solution=minimize(lambda x:self.objective(x)[0],self.initial,jac=lambda x:self.objective(x)[1],method='SLSQP',bounds=self.bounds,
            constraints=[dict(type='ineq',fun=lambda x:self.constraints(x)[0],jac=lambda x:self.constraints(x)[1])],
            options=dict(maxiter=100,ftol=1e-8,disp=False))
        solver_wall=time.perf_counter()-start;p=self.points(solution.x);g,_=self.constraints(solution.x)
        violation=max(0.,float(-g.min()),float(np.max(self.bounds.lb-solution.x)),float(np.max(solution.x-self.bounds.ub)))
        exact=float(self.field.exact_clearance(p));accepted=bool(solution.success and violation<=TOL and exact>=SAFETY)
        r,_=self.residual_jacobian(solution.x)
        return p,dict(accepted=accepted,solver_success=bool(solution.success),solver_status=int(solution.status),message=str(solution.message),
            iterations=int(solution.nit),objective=float(solution.fun),constraint_violation=violation,depth_clearance_m=exact,
            minimum_certified_sdf_clearance_m=float(g[:63].min()+SAFETY),solver_wall_s=solver_wall,
            solve_certificate_wall_s=time.perf_counter()-start,factor_costs=dict(intent=.5*float(r[:14]@r[:14]),smoothness=.5*float(r[14:26]@r[14:26]),heading=.5*float(r[26]**2)),
            disposition='ACCEPTED' if accepted else 'NONCONVERGED' if not solution.success else 'CONSTRAINT_FAILED' if violation>TOL else 'CERTIFICATE_REJECTED')


def solve_sample(native,B,field):
    start=time.perf_counter();q,init=initialize(native,B)
    if q is None:return dict(**init,accepted=False,path=None,reference=None,attempt_wall_s=time.perf_counter()-start,solver_started=False)
    try:
        graph=RepairGraph(q,B,field)
        fixed_gap=float(field.query(np.asarray(B)[None,:2])[0][0])-field.error_bound-.5*graph.lengths[0]/16
        path,result=graph.solve()
        edits=np.linalg.norm(path-q,axis=1);a=q[-1]-np.asarray(B)[:2];b=path[-1]-np.asarray(B)[:2]
        change=float((np.arctan2(b[1],b[0])-np.arctan2(a[1],a[0])+np.pi)%(2*np.pi)-np.pi) if min(np.linalg.norm(a),np.linalg.norm(b))>1e-12 else None
        return dict(**init,**result,path=path.tolist(),reference=q.tolist(),mean_edit_m=float(edits.mean()),max_edit_m=float(edits.max()),
            endpoint_direction_change_deg=abs(change)*180/np.pi if change is not None else None,
            maximum_abs_curvature_m_inv=float(np.max(np.abs(menger(path)[0]))),length_ratio=float(norm(np.diff(path,axis=0)).sum()/graph.lengths.sum()),
            attempt_wall_s=time.perf_counter()-start,solver_started=True,
            fixed_B_necessary_upper_clearance_m=fixed_gap,fixed_B_safety_impossible=fixed_gap<SAFETY-TOL)
    except ValueError as exc:
        return dict(**init,accepted=False,disposition='SDF_OR_NUMERICAL_ERROR',path=None,reference=q.tolist(),error=str(exc),
                    attempt_wall_s=time.perf_counter()-start,solver_started=True)
