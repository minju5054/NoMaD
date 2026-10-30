"""R3: 20 XY variables, fixed B, analytic least-squares/constraint derivatives."""
import time
import numpy as np
from scipy.optimize import Bounds,minimize
from nomad_phase0.graph_v4 import norm,menger
from nomad_phase20.repair import split_arclength
from nomad_phase15.evaluate import sample_path

ANGLES=(0,30,-30,60,-60,90,-90)


class DetourGraph:
    def __init__(self,B,u_ref,field,angle):
        self.B=np.asarray(B,dtype=float);self.u=np.asarray(u_ref,dtype=float);self.field=field;self.angle=angle
        np.testing.assert_allclose(np.linalg.norm(self.u),1.,atol=1e-12,rtol=0)
        yaw=np.arctan2(self.u[1],self.u[0])+np.deg2rad(angle)
        self.initial_path=self.B[:2]+np.linspace(0.,1.5,11)[:,None]*np.array([np.cos(yaw),np.sin(yaw)])
        self.initial=self.initial_path[1:].ravel().copy()
        # Redundant coordinate bounds implied by the required 1.6m disk.
        self.bounds=Bounds(np.tile(self.B[:2]-1.6,10),np.tile(self.B[:2]+1.6,10))
        self.cB=float(field.query(self.B[None,:2])[0][0])-field.error_bound
        self.near_threshold=min(.025,max(0.,self.cB-.005))
        self.D=np.zeros((9,11))
        for i in range(9):self.D[i,i:i+3]=[1.,-2.,1.]
        self.smooth_j=np.kron(self.D[:,1:],np.eye(2))/.03
        self.M=np.zeros((90,11));self.segment_ids=np.repeat(np.arange(10),9)
        for i in range(10):
            for k,f in enumerate(np.linspace(0,1,9)):self.M[i*9+k,i:i+2]=[1-f,f]
        self._obj=None;self._con=None

    def points(self,x):return np.vstack([self.B[:2],np.asarray(x).reshape(10,2)])

    def residual_jacobian(self,x):
        p=self.points(x);progress=float((p[-1]-self.B[:2])@self.u)
        rp=max(0.,1.2-progress)/.10;jp=np.zeros((1,20))
        if progress<1.2:jp[0,-2:]=-self.u/.10
        distance,grad=self.field.query(self.M@p);rc=np.maximum(0.,.15-distance)/.05
        jc=np.zeros((90,20));active=distance<.15
        jc[:,0::2]=-grad[:,0,None]*self.M[:,1:]/.05;jc[:,1::2]=-grad[:,1,None]*self.M[:,1:]/.05;jc[~active]=0.
        d=p[1]-p[0];angle=np.arctan2(d[1],d[0])-self.B[2];sigma=np.pi/6
        rh=2*np.sin(angle/2)/sigma;jh=np.zeros((1,20))
        jh[0,:2]=np.cos(angle/2)/sigma*np.array([-d[1],d[0]])/max(float(d@d),1e-24)
        return np.r_[rp,(self.D@p).ravel()/.03,rc,rh],np.vstack([jp,self.smooth_j,jc,jh])

    def objective(self,x):
        if self._obj is None or not np.array_equal(x,self._obj[0]):
            r,j=self.residual_jacobian(x);self._obj=(x.copy(),.5*float(r@r),j.T@r)
        return self._obj[1:]

    def constraints(self,x):
        if self._con is not None and np.array_equal(x,self._con[0]):return self._con[1:]
        p=self.points(x);delta=np.diff(p,axis=0);length=norm(delta);jl=np.zeros((10,20))
        for i in range(10):
            if i:jl[i,2*(i-1):2*i]-=delta[i]/length[i]
            jl[i,2*i:2*i+2]+=delta[i]/length[i]
        s=(np.r_[0.,np.cumsum(length)[:-1]][:,None]+length[:,None]*np.linspace(0,1,9)).ravel()
        threshold=np.where(s<=.30,self.near_threshold,.025)
        distance,grad=self.field.query(self.M@p)
        sdf=distance-self.field.error_bound-length[self.segment_ids]/16-threshold
        js=np.zeros((90,20));js[:,0::2]=grad[:,0,None]*self.M[:,1:];js[:,1::2]=grad[:,1,None]*self.M[:,1:]
        js-=jl[self.segment_ids]/16
        k,jk=menger(p);jk=jk[:,1:,:].reshape(9,20)
        radial=p[1:]-self.B[:2];radii=norm(radial);jr=np.zeros((10,20))
        for i in range(10):jr[i,2*i:2*i+2]=-radial[i]/radii[i]
        g=np.r_[sdf,4-k,4+k,length-.10,.20-length,1.6-radii]
        j=np.vstack([js,-jk,jk,jl,-jl,jr]);self._con=(x.copy(),g,j)
        return g,j

    def certificate(self,p):
        near,far=split_arclength(p)
        a=float(self.field.exact_clearance(near));b=float(self.field.exact_clearance(far)) if far is not None else None
        return dict(certificate_pass=bool(a>=self.near_threshold and (b is None or b>=.025)),
                    near_clearance_m=a,far_clearance_m=b,depth_clearance_m=min(a,b) if b is not None else a)

    def solve(self):
        start=time.perf_counter()
        if self.cB<0:return dict(accepted=False,disposition='NEGATIVE_DEPTH_AT_B',path=None,initial_path=self.initial_path.tolist(),solver_started=False,attempt_wall_s=time.perf_counter()-start,cB=self.cB)
        try:
            result=minimize(lambda x:self.objective(x)[0],self.initial,jac=lambda x:self.objective(x)[1],method='SLSQP',bounds=self.bounds,
                constraints=[dict(type='ineq',fun=lambda x:self.constraints(x)[0],jac=lambda x:self.constraints(x)[1])],options=dict(maxiter=100,ftol=1e-8,disp=False))
            solve_s=time.perf_counter()-start;p=self.points(result.x);g,_=self.constraints(result.x)
            violation=max(0.,float(-g.min()),float(np.max(self.bounds.lb-result.x)),float(np.max(result.x-self.bounds.ub)))
            cert=self.certificate(p);progress=float((p[-1]-self.B[:2])@self.u);length=float(norm(np.diff(p,axis=0)).sum())
            accepted=bool(result.success and violation<=1e-7 and cert['certificate_pass'] and progress>=.5)
            disposition='ACCEPTED' if accepted else 'NONCONVERGED' if not result.success else 'CONSTRAINT_FAILED' if violation>1e-7 else 'CERTIFICATE_REJECTED' if not cert['certificate_pass'] else 'INSUFFICIENT_PROGRESS'
            r,_=self.residual_jacobian(result.x);q,_=sample_path(p)
            return dict(accepted=accepted,disposition=disposition,path=p.tolist(),initial_path=self.initial_path.tolist(),solver_started=True,
                solver_success=bool(result.success),solver_status=int(result.status),message=str(result.message),iterations=int(result.nit),
                constraint_violation=violation,progress_m=progress,length_m=length,maximum_abs_curvature_m_inv=float(np.max(np.abs(menger(p)[0]))),
                maximum_radius_m=float(norm(p[1:]-self.B[:2]).max()),minimum_segment_m=float(norm(np.diff(p,axis=0)).min()),maximum_segment_m=float(norm(np.diff(p,axis=0)).max()),
                unknown_fraction=self.field.unknown_fraction(q),near_threshold_m=self.near_threshold,cB=self.cB,**cert,
                factor_costs=dict(progress=.5*float(r[0]**2),smoothness=.5*float(r[1:19]@r[1:19]),clearance=.5*float(r[19:109]@r[19:109]),heading=.5*float(r[-1]**2)),
                solver_wall_s=solve_s,attempt_wall_s=time.perf_counter()-start)
        except ValueError as exc:
            return dict(accepted=False,disposition='SDF_OR_NUMERICAL_ERROR',path=None,initial_path=self.initial_path.tolist(),solver_started=True,error=str(exc),attempt_wall_s=time.perf_counter()-start)


def solve_initialization(B,u_ref,field,angle):
    start=time.perf_counter()
    try:
        result=DetourGraph(B,u_ref,field,angle).solve();result['total_attempt_s']=time.perf_counter()-start;return result
    except ValueError as exc:return dict(accepted=False,disposition='INITIALIZATION_REJECTED',path=None,initial_path=None,solver_started=False,error=str(exc),total_attempt_s=time.perf_counter()-start)

def select_detour(results):
    accepted=[(i,r) for i,r in enumerate(results) if r['accepted']]
    return min(accepted,key=lambda a:(-a[1]['progress_m'],a[1]['length_m'],a[0]))[0] if accepted else None
