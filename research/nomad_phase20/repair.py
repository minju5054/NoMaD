"""R2: unchanged Phase19R XY repair, with a local start-clearance relaxation."""
import time
import numpy as np
from scipy.optimize import minimize
from nomad_phase19r.repair import RepairGraph, initialize, SAFETY, TOL
from nomad_phase0.graph_v4 import norm, menger

NEAR_LENGTH=.30


def split_arclength(p,distance=NEAR_LENGTH):
    """Continuous exact certificate: include the cut in both closed subpaths."""
    p=np.asarray(p,dtype=float);lengths=norm(np.diff(p,axis=0));s=np.r_[0.,np.cumsum(lengths)]
    if s[-1]<=distance:return p,None
    i=min(int(np.searchsorted(s,distance,side='right')-1),len(lengths)-1)
    f=(distance-s[i])/lengths[i];q=p[i]+f*(p[i+1]-p[i])
    return np.vstack([p[:i+1],q]),np.vstack([q,p[i+1:]])


class RepairGraphR2(RepairGraph):
    def __init__(self,reference,B,field):
        super().__init__(reference,B,field)
        # Same c_B convention used in Phase16D E1 and Phase19R event records.
        self.cB=float(field.query(np.asarray(B)[None,:2])[0][0])-field.error_bound
        self.near_threshold=min(SAFETY,max(0.,self.cB-.005))

    def thresholds(self,x):
        p=self.points(x);lengths=norm(np.diff(p,axis=0));starts=np.r_[0.,np.cumsum(lengths)[:-1]]
        arclength=(starts[:,None]+lengths[:,None]*np.linspace(0.,1.,9)).ravel()
        return np.where(arclength<=NEAR_LENGTH,self.near_threshold,SAFETY),arclength

    def constraints(self,x):
        base,j=super().constraints(x);g=base.copy();threshold,_=self.thresholds(x)
        g[:63]+=SAFETY-threshold
        # The binary zone has zero derivative within each active set. The hard
        # switch at s=.30 is explicitly nonsmooth, not silently smoothed/frozen.
        return g,j

    def certificate(self,p):
        near,far=split_arclength(p)
        nc=float(self.field.exact_clearance(near));fc=float(self.field.exact_clearance(far)) if far is not None else None
        ok=nc>=self.near_threshold and (fc is None or fc>=SAFETY)
        return dict(certificate_pass=bool(ok),near_exact_clearance_m=nc,far_exact_clearance_m=fc,
                    near_threshold_m=self.near_threshold,cB_depth_clearance_m=self.cB,
                    depth_clearance_m=min(nc,fc) if fc is not None else nc)

    def solve(self):
        if self.cB<0:raise ValueError('NEGATIVE_DEPTH_AT_B')
        start=time.perf_counter()
        solution=minimize(lambda x:self.objective(x)[0],self.initial,jac=lambda x:self.objective(x)[1],method='SLSQP',bounds=self.bounds,
            constraints=[dict(type='ineq',fun=lambda x:self.constraints(x)[0],jac=lambda x:self.constraints(x)[1])],
            options=dict(maxiter=100,ftol=1e-8,disp=False))
        solver_wall=time.perf_counter()-start;p=self.points(solution.x);g,_=self.constraints(solution.x)
        violation=max(0.,float(-g.min()),float(np.max(self.bounds.lb-solution.x)),float(np.max(solution.x-self.bounds.ub)))
        cert=self.certificate(p);accepted=bool(solution.success and violation<=TOL and cert['certificate_pass'])
        r,_=self.residual_jacobian(solution.x);threshold,arclength=self.thresholds(solution.x)
        return p,dict(accepted=accepted,solver_success=bool(solution.success),solver_status=int(solution.status),message=str(solution.message),
            iterations=int(solution.nit),objective=float(solution.fun),constraint_violation=violation,**cert,
            minimum_certified_sdf_clearance_m=float(np.min(g[:63]+threshold)),minimum_sdf_constraint_slack_m=float(g[:63].min()),
            near_inspection_points=int(np.sum(arclength<=NEAR_LENGTH)),solver_wall_s=solver_wall,
            solve_certificate_wall_s=time.perf_counter()-start,factor_costs=dict(intent=.5*float(r[:14]@r[:14]),smoothness=.5*float(r[14:26]@r[14:26]),heading=.5*float(r[26]**2)),
            disposition='ACCEPTED' if accepted else 'NONCONVERGED' if not solution.success else 'CONSTRAINT_FAILED' if violation>TOL else 'CERTIFICATE_REJECTED')


def solve_sample(native,B,field):
    start=time.perf_counter()
    cB=float(field.query(np.asarray(B)[None,:2])[0][0])-field.error_bound
    if cB<0:
        return dict(disposition='NEGATIVE_DEPTH_AT_B',cB_depth_clearance_m=cB,accepted=False,path=None,reference=None,
                    attempt_wall_s=time.perf_counter()-start,solver_started=False)
    q,init=initialize(native,B)
    if q is None:return dict(**init,accepted=False,path=None,reference=None,attempt_wall_s=time.perf_counter()-start,solver_started=False)
    try:
        graph=RepairGraphR2(q,B,field);path,result=graph.solve()
        edits=np.linalg.norm(path-q,axis=1);a=q[-1]-np.asarray(B)[:2];b=path[-1]-np.asarray(B)[:2]
        change=float((np.arctan2(b[1],b[0])-np.arctan2(a[1],a[0])+np.pi)%(2*np.pi)-np.pi) if min(np.linalg.norm(a),np.linalg.norm(b))>1e-12 else None
        return dict(**init,**result,path=path.tolist(),reference=q.tolist(),mean_edit_m=float(edits.mean()),max_edit_m=float(edits.max()),
            endpoint_direction_change_deg=abs(change)*180/np.pi if change is not None else None,
            maximum_abs_curvature_m_inv=float(np.max(np.abs(menger(path)[0]))),length_ratio=float(norm(np.diff(path,axis=0)).sum()/graph.lengths.sum()),
            attempt_wall_s=time.perf_counter()-start,solver_started=True)
    except ValueError as exc:
        return dict(**init,accepted=False,disposition='SDF_OR_NUMERICAL_ERROR',path=None,reference=q.tolist(),error=str(exc),
                    attempt_wall_s=time.perf_counter()-start,solver_started=True)
