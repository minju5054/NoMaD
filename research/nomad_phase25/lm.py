"""Frozen R3 residuals; LM continuation replaces only the constrained solver."""
import time
import numpy as np
from scipy.optimize import least_squares
from nomad_phase0.graph_v4 import norm, menger
from nomad_phase20c.detour import ANGLES, select_detour
from nomad_phase20c.detour_known import KnownDetourGraph
from nomad_phase15.evaluate import sample_path
from nomad_phase24r.safety import certificate

SCALES=(.01,.001,.0001)
ANGLES13=(0,15,-15,30,-30,45,-45,60,-60,75,-75,90,-90)


class LMGraph(KnownDetourGraph):
    def __init__(self,*args):
        super().__init__(*args)
        self.Q=np.vstack([np.eye(11),(np.eye(11)[:-1]+np.eye(11)[1:])/2])
        self.residual_cache=None

    def penalty_inequalities(self,x):
        """Positive = satisfied. Obstacle penalty at 11 nodes +10 midpoints.

        The final acceptance still uses the frozen 90-point, h/sqrt2+L/16
        inequalities, disk/bounds, curvature, lengths and exact certificate.
        Piecewise near/far membership is held fixed locally, as in S7's
        analytic Jacobian; no derivative exists at its arclength switch.
        """
        p=self.points(x);delta=np.diff(p,axis=0);length=norm(delta)
        jl=np.zeros((10,20))
        for i in range(10):
            if i:jl[i,2*(i-1):2*i]-=delta[i]/length[i]
            jl[i,2*i:2*i+2]+=delta[i]/length[i]
        s=np.r_[0.,np.cumsum(length)];sq=np.r_[s,(s[:-1]+s[1:])/2]
        q=self.Q@p;near=sq<=.30
        distance=np.empty(21);gradient=np.empty((21,2))
        for mask,field in ((near,self.base_field),(~near,self.strict_field)):
            if mask.any():distance[mask],gradient[mask]=field.query(q[mask])
        js=np.zeros((21,20));js[:,0::2]=gradient[:,0,None]*self.Q[:,1:];js[:,1::2]=gradient[:,1,None]*self.Q[:,1:]
        obstacle=distance-np.where(near,self.near_threshold,.025)
        curvature,jk=menger(p);jk=jk[:,1:,:].reshape(9,20)
        radial=p[1:]-self.B[:2];radii=norm(radial);jr=np.zeros((10,20))
        for i in range(10):jr[i,2*i:2*i+2]=-radial[i]/radii[i]
        h=np.r_[obstacle,4-np.abs(curvature),length-.10,.20-length,1.6-radii]
        jac=np.vstack([js,-np.sign(curvature)[:,None]*jk,jl,-jl,jr])
        return h,jac

    def lm_residual(self,x,scale):
        if self.residual_cache is None or self.residual_cache[1]!=scale or not np.array_equal(x,self.residual_cache[0]):
            base,jbase=super().residual_jacobian(x)
            h,jh=self.penalty_inequalities(x);active=h<0
            penalty=np.maximum(0.,-h)/scale
            jac=-jh/scale;jac[~active]=0.
            self.residual_cache=(np.array(x,copy=True),scale,np.r_[base,penalty],np.vstack([jbase,jac]))
        return self.residual_cache[2:]

    def solve(self):
        start=time.perf_counter();stages=[];x=self.initial.copy()
        if self.cB<0:
            return dict(accepted=False,disposition='NEGATIVE_DEPTH_AT_B',path=None,initial_path=self.initial_path.tolist(),solver_started=False,cB=self.cB,total_attempt_s=time.perf_counter()-start,stages=[])
        try:
            for scale in SCALES:
                before=time.perf_counter()
                r=least_squares(lambda z:self.lm_residual(z,scale)[0],x,
                    jac=lambda z:self.lm_residual(z,scale)[1],method='lm',max_nfev=50,
                    ftol=1e-8,xtol=1e-8,gtol=1e-8)
                x=r.x.copy()
                stages.append(dict(scale=scale,nfev=int(r.nfev),njev=int(r.njev),success=bool(r.success),status=int(r.status),wall_s=time.perf_counter()-before))
            p=self.points(x);hard,_=self.constraints(x)
            violation=max(0.,float(-hard.min()),float(np.max(self.bounds.lb-x)),float(np.max(x-self.bounds.ub)))
            cert=self.certificate(p);progress=float((p[-1]-self.B[:2])@self.u)
            length=float(norm(np.diff(p,axis=0)).sum())
            accepted=bool(r.success and violation<=1e-7 and cert['certificate_pass'] and progress>=.5)
            disposition='ACCEPTED' if accepted else 'NONCONVERGED' if not r.success else 'CONSTRAINT_FAILED' if violation>1e-7 else 'CERTIFICATE_REJECTED' if not cert['certificate_pass'] else 'INSUFFICIENT_PROGRESS'
            raw,_=super().residual_jacobian(x);q,_=sample_path(p)
            return dict(accepted=accepted,disposition=disposition,path=p.tolist(),initial_path=self.initial_path.tolist(),solver_started=True,
                solver_success=bool(r.success),solver_status=int(r.status),message=str(r.message),stages=stages,
                constraint_violation=violation,progress_m=progress,length_m=length,
                maximum_abs_curvature_m_inv=float(np.max(np.abs(menger(p)[0]))),
                unknown_fraction=self.base_field.unknown_fraction(q),near_threshold_m=self.near_threshold,cB=self.cB,**cert,
                original_cost=.5*float(raw@raw),penalized_cost=float(r.cost),
                solver_wall_s=sum(s['wall_s'] for s in stages),total_attempt_s=time.perf_counter()-start)
        except (ValueError,FloatingPointError) as exc:
            return dict(accepted=False,disposition='SDF_OR_NUMERICAL_ERROR',path=None,initial_path=self.initial_path.tolist(),solver_started=True,error=str(exc),stages=stages,total_attempt_s=time.perf_counter()-start)


def validate(result,graph):
    """Same final hard rules for every variant; independent failure flags."""
    path=result.get('path')
    if path is None:
        return dict(result,failures=[result['disposition']],final_certificate=None)
    x=np.asarray(path)[1:].ravel();h,_=graph.constraints(x)
    cert=certificate(path,graph.B,graph.base_field,graph.strict_field)
    failures=[]
    for name,part in (('OBSTACLE',h[:90]),('CURVATURE',h[90:108]),('SPACING',h[108:128]),('RADIUS',h[128:])):
        if part.min() < -1e-7:failures.append(name)
    if not result.get('solver_success'):failures.append('NONCONVERGED')
    if not cert['passed']:failures.append('CERTIFICATE_'+cert['reason'])
    if result.get('progress_m',0)<.5:failures.append('INSUFFICIENT_PROGRESS')
    residual,_=graph.residual_jacobian(x)
    return dict(result,accepted=bool(result['accepted'] and cert['passed']),
                disposition='CERTIFICATE_REJECTED' if result['accepted'] and not cert['passed'] else result['disposition'],
                failures=failures,final_certificate=cert,original_cost=.5*float(residual@residual))


def solve_start(B,u,base,strict,angle,variant):
    start=time.perf_counter()
    try:
        g=(KnownDetourGraph if variant=='S7' else LMGraph)(B,u,base,strict,angle)
        r=validate(g.solve(),g)
        r.update(angle=angle,wall_s=time.perf_counter()-start)
        return r
    except (ValueError,FloatingPointError) as exc:
        return dict(accepted=False,disposition='INITIALIZATION_REJECTED',path=None,angle=angle,
                    error=str(exc),failures=['INITIALIZATION_REJECTED'],wall_s=time.perf_counter()-start)
