"""Single A-star initialization, analytic added factors and a .30m path tube."""
import time
import numpy as np
from nomad_phase0.graph_v4 import menger
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase20c.detour_known import KnownDetourGraph
from nomad_phase21.astar import certificate

class Deadline(Exception):pass

def resample(xy):
    path=XYPath(xy);return np.array([path.at(s) for s in np.linspace(0,path.s[-1],11)])

def tube(path,reference):
    p=np.asarray(path);q=XYPath(reference);a=q.points[:-1];d=q.delta;den=np.sum(d*d,axis=1)
    fraction=np.clip(np.sum((p[:,None,:]-a[None])*d[None],axis=2)/den,0,1)
    nearest=a[None]+fraction[:,:,None]*d[None];dist2=np.sum((p[:,None]-nearest)**2,axis=2);index=np.argmin(dist2,axis=1)
    delta=p-nearest[np.arange(len(p)),index];g=.30**2-np.sum(delta*delta,axis=1);jac=np.zeros((len(p),20))
    for i in range(1,len(p)):jac[i,2*(i-1):2*i]=-2*delta[i]
    return g,jac

class RefineGraph(KnownDetourGraph):
    def __init__(self,B,u,base,strict,p0,anchor,settings,deadline_ns):
        super().__init__(B,u,base,strict,0);self.p0=np.asarray(p0);self.anchor=np.asarray(anchor)[:2];self.settings=settings;self.deadline_ns=deadline_ns
        self.initial_path=resample(p0);self.initial_path[0]=np.asarray(B)[:2];self.initial=self.initial_path[1:].ravel().copy()
    def check(self):
        if time.monotonic_ns()>=self.deadline_ns:raise Deadline()
    def residual_jacobian(self,x):
        self.check();r,j=super().residual_jacobian(x);p=self.points(x);k,jk=menger(p);jk=jk[:,1:,:].reshape(len(k),20);s=self.settings
        active=np.abs(k)>1.33;rk=np.maximum(0,np.abs(k)-1.33)/s['sigma_k'];jcurv=np.sign(k)[:,None]*jk/s['sigma_k'];jcurv[~active]=0
        rd=np.diff(k)/s['sigma_delta'];jd=np.diff(jk,axis=0)/s['sigma_delta']
        edge=p[-1]-p[-2];angle=np.arctan2(edge[1],edge[0])-np.arctan2(self.u[1],self.u[0]);angle=(angle+np.pi)%(2*np.pi)-np.pi
        rh=2*np.sin(angle/2)/s['sigma_heading'];heading_grad=np.cos(angle/2)/s['sigma_heading']*np.array([-edge[1],edge[0]])/max(float(edge@edge),1e-24)
        jh=np.zeros((1,20));jh[0,-4:-2]=-heading_grad;jh[0,-2:]=heading_grad
        normal=np.array([-self.u[1],self.u[0]]);rl=float((p[-1]-self.anchor)@normal)/s['sigma_lateral'];jl=np.zeros((1,20));jl[0,-2:]=normal/s['sigma_lateral']
        return np.r_[r,rk,rd,rh,rl],np.vstack([j,jcurv,jd,jh,jl])
    def constraints(self,x):
        self.check();g,j=super().constraints(x);h,jh=tube(self.points(x),self.p0);return np.r_[g,h],np.vstack([j,jh])
    def certificate(self,p):
        self.check();c=super().certificate(p);g,_=tube(p,self.p0);c['certificate_pass']=bool(c['certificate_pass'] and g.min()>=-1e-7);c['max_p0_distance_m']=float(np.sqrt(max(0.,.09-float(g.min()))));return c
    def solve(self):
        r=super().solve()
        if r.get('path') is not None:
            residual,_=self.residual_jacobian(np.array(r['path'])[1:].ravel());r['factor_costs']['heading']=.5*float(residual[109]**2)
            r['factor_costs'].update(executability=.5*float(residual[110:119]@residual[110:119]),curvature_change=.5*float(residual[119:127]@residual[119:127]),terminal_heading=.5*float(residual[127]**2),terminal_lateral=.5*float(residual[128]**2))
        return r

def graph_refine(B,u,base,strict,p0,anchor,settings,deadline_ns):
    start=time.monotonic_ns()
    try:r=RefineGraph(B,u,base,strict,p0,anchor,settings,deadline_ns).solve()
    except Deadline:r=dict(accepted=False,path=None,disposition='TIMEOUT')
    except ValueError as exc:r=dict(accepted=False,path=None,disposition='INITIALIZATION_REJECTED',error=str(exc))
    r['refinement_wall_s']=(time.monotonic_ns()-start)/1e9;return r

def smooth(B,u,base,strict,p0,strength,deadline_ns):
    start=time.monotonic_ns();p0=np.asarray(p0);original=resample(p0)
    curve=np.vstack([p0[:1],np.stack([.75*p0[:-1]+.25*p0[1:],.25*p0[:-1]+.75*p0[1:]],axis=1).reshape(-1,2),p0[-1:]])
    rounded=resample(curve);attempts=[]
    for retry in range(4):
        if time.monotonic_ns()>=deadline_ns:return dict(accepted=False,path=None,disposition='TIMEOUT',attempts=attempts,refinement_wall_s=(time.monotonic_ns()-start)/1e9)
        alpha=strength/(2**retry);p=(1-alpha)*original+alpha*rounded;p[0]=np.asarray(B)[:2];p[-1]=p0[-1]
        c=certificate(p,B,np.asarray(u),base,strict);valid=c['certificate_pass'] and c['progress_m']>=.5 and c['minimum_segment_m']>=.1-1e-7 and c['maximum_segment_m']<=.2+1e-7 and c['maximum_radius_m']<=1.6+1e-7
        attempts.append(dict(strength=alpha,valid=valid))
        if valid:return dict(accepted=True,path=p.tolist(),disposition='ACCEPTED',attempts=attempts,refinement_wall_s=(time.monotonic_ns()-start)/1e9,**c)
    return dict(accepted=True,path=p0.tolist(),disposition='P0_FALLBACK',attempts=attempts,refinement_wall_s=(time.monotonic_ns()-start)/1e9)
