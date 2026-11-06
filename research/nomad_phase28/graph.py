"""Single-start analytic SLSQP handoff graph: ten future SE(2) poses + ten dt.

No oracle, selection, trigger, R2/R3, or recovery logic is present here.
"""
import time
import numpy as np
from scipy.optimize import minimize,Bounds
from nomad_phase0.graph_v4 import norm
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase15.evaluate import suffix
from nomad_phase20d.recent import CachedField
from nomad_isaac.common import integrate_se2
from .config import PARAMETERS as P

N=10;DIM=40
def wrap(a):return (np.asarray(a)+np.pi)%(2*np.pi)-np.pi
def reference(path,B):
    tail,_=suffix(path,B);q=np.vstack([np.asarray(B)[:2],tail]);length=np.r_[0.,np.cumsum(norm(np.diff(q,axis=0)))];keep=np.r_[True,np.diff(length)>1e-12];q,length=q[keep],length[keep]
    if len(q)==1:return np.repeat(q,11,axis=0)
    target=np.linspace(0,length[-1],11)
    return np.c_[np.interp(target,length,q[:,0]),np.interp(target,length,q[:,1])]
def backward(path,B):
    q=XYPath(path);s,_=q.project(np.asarray(B)[:2]);ids=np.flatnonzero(q.s>=s+.05)
    if not len(ids):return False
    d=q.points[ids[0]]-np.asarray(B)[:2]
    return bool(abs(float(wrap(np.arctan2(d[1],d[0])-B[2])))>np.pi/2)
def certificate(path,field):
    q=np.asarray(path);d=np.diff(q,axis=0);length=norm(d);f=np.linspace(0,1,9)
    sample=(q[:-1,None,:]+f[None,:,None]*d[:,None,:]).reshape(-1,2)
    cell,valid=field.cells(sample)
    if not valid.all():return dict(passed=False,reason='OUTSIDE_MAP')
    distance=field.query(sample)[0];slack=distance-field.error_bound-np.repeat(length,9)/16-.025
    if slack.min() < -1e-7:return dict(passed=False,reason='NINE_POINT_MARGIN',minimum_slack_m=float(slack.min()))
    fast=object.__new__(CachedField);fast.__dict__.update(field.__dict__);exact=fast.exact_clearance(q)
    return dict(passed=bool(exact>=.025-1e-8),reason='PASS' if exact>=.025-1e-8 else 'EXACT_DISTANCE',exact_clearance_m=float(exact),minimum_slack_m=float(slack.min()))

class HandoffGraph:
    def __init__(self,B,vw,path,field,alpha,deadline=float('inf')):
        self.B=np.asarray(B,float);self.v0,self.w0=map(float,vw);self.field=field;self.alpha=float(alpha);self.deadline=deadline
        angle=self.B[2];self.R=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        self.target=(reference(path,B)-self.B[:2])@self.R;self.allow_rotation=backward(path,B)
        self.jp=np.zeros((11,2,DIM));self.jh=np.zeros((11,DIM));self.jt=np.zeros((10,DIM))
        for i in range(1,11):self.jp[i,0,3*(i-1)]=1;self.jp[i,1,3*(i-1)+1]=1;self.jh[i,3*(i-1)+2]=1
        self.jt[:,30:]=np.eye(10);self.bounds=Bounds(np.r_[np.tile([-np.inf,-np.inf,-4*np.pi],10),np.full(10,.1)],np.r_[np.tile([np.inf,np.inf,4*np.pi],10),np.ones(10)])
        self.last=None;self.cache=None;self.iterations=0
    def check(self):
        if time.perf_counter()>self.deadline:raise TimeoutError('SOLVE_TIMEOUT')
    def unpack(self,x):
        q=np.vstack([np.zeros(3),np.asarray(x[:30]).reshape(10,3)]);return q[:,:2],q[:,2],x[30:]
    def initial(self,warm=None):
        p=self.target.copy();dt=np.full(10,.4)
        if warm is not None:
            p=(reference(np.asarray(warm['poses'])[:,:2],self.B)-self.B[:2])@self.R
            dt=np.clip(warm['dt'],.1,1.).copy()
        d=np.diff(p,axis=0);h=np.r_[0.,np.unwrap(np.arctan2(d[:,1],d[:,0]))]
        if warm is None:
            dt=np.clip(np.maximum(norm(d)/.2,abs(wrap(np.diff(h)))/.4),.1,1.)
            dt[0]=np.clip(float(np.linalg.norm(d[0]))/self.v0,.1,1.) if self.v0>1e-9 else .1
        first=integrate_se2([0.,0.,0.],self.v0,self.w0,float(dt[0]));p[1]=first[:2];h[1]=first[2]
        return np.r_[np.c_[p[1:],h[1:]].ravel(),dt]
    def quantities(self,x):
        self.check()
        if self.last is not None and np.array_equal(x,self.last):return self.cache
        p,h,dt=self.unpack(x);d=np.diff(p,axis=0);jd=np.diff(self.jp,axis=0);length=np.linalg.norm(d,axis=1)
        jl=np.einsum('qi,qij->qj',d/np.maximum(length[:,None],1e-12),jd)
        angle=wrap(np.diff(h));ja=np.diff(self.jh,axis=0);z=angle/2
        sinc=np.sinc(z/np.pi);ds=np.zeros(10);mask=abs(z)>1e-5
        ds[mask]=.5*(z[mask]*np.cos(z[mask])-np.sin(z[mask]))/z[mask]**2;ds[~mask]=-angle[~mask]/12+angle[~mask]**3/480
        v=length/(dt*sinc);jv=jl/(dt*sinc)[:,None]-v[:,None]/dt[:,None]*self.jt-(v*ds/sinc)[:,None]*ja
        w=angle/dt;jw=ja/dt[:,None]-w[:,None]/dt[:,None]*self.jt
        span=(dt[1:]+dt[:-1])/2;js=(self.jt[1:]+self.jt[:-1])/2
        accel=np.diff(v)/span;jacc=np.diff(jv,axis=0)/span[:,None]-accel[:,None]/span[:,None]*js
        angular=np.diff(w)/span;jangular=np.diff(jw,axis=0)/span[:,None]-angular[:,None]/span[:,None]*js
        q=np.vstack([p,(p[:-1]+p[1:])/2]);jq=np.concatenate([self.jp,(self.jp[:-1]+self.jp[1:])/2]);world=q@self.R.T+self.B[:2]
        low=self.field.origin+1e-8;high=self.field.origin+(np.array(self.field.values.shape[::-1])-1)*self.field.h-1e-8
        clipped=np.clip(world,low,high);distance,gradient=self.field.query(clipped);outside=np.linalg.norm(world-clipped,axis=1);bad=outside>0
        distance[bad]=-outside[bad]-self.field.radius;gradient[bad]=-(world-clipped)[bad]/outside[bad,None]
        jdistance=np.einsum('qi,qij->qj',gradient@self.R,jq)
        self.cache=dict(p=p,h=h,dt=dt,d=d,jd=jd,v=v,jv=jv,w=w,jw=jw,accel=accel,jacc=jacc,angular=angular,jangular=jangular,distance=distance,jdistance=jdistance)
        self.last=np.array(x).copy();return self.cache
    def terms(self,x):
        a=self.quantities(x);p,h,dt,d=a['p'],a['h'],a['dt'],a['d'];terms={};grad={}
        r=(p[1:]-self.target[1:])/.05;j=self.jp[1:]/.05;terms['tracking']=float(np.sum(r*r));grad['tracking']=2*np.einsum('qi,qij->j',r,j)
        c=np.cos(h);s=np.sin(h);r=((c[:-1]+c[1:])*d[:,1]-(s[:-1]+s[1:])*d[:,0])/.03
        j=((c[:-1]+c[1:])[:,None]*a['jd'][:,1]-(s[:-1]+s[1:])[:,None]*a['jd'][:,0]+(-s[:-1]*d[:,1]-c[:-1]*d[:,0])[:,None]*self.jh[:-1]+(-s[1:]*d[:,1]-c[1:]*d[:,0])[:,None]*self.jh[1:])/.03
        forward=c[:-1]*d[:,0]+s[:-1]*d[:,1];back=np.minimum(0,forward)/.03
        jb=(c[:-1,None]*a['jd'][:,0]+s[:-1,None]*a['jd'][:,1]+(-s[:-1]*d[:,0]+c[:-1]*d[:,1])[:,None]*self.jh[:-1])/.03
        terms['nonholonomic']=float(r@r+back@back);grad['nonholonomic']=2*r@j+2*back@jb
        r=np.diff(p,n=2,axis=0)/.03;j=np.diff(self.jp,n=2,axis=0)/.03
        terms['smoothing']=float(np.sum(r*r));grad['smoothing']=2*np.einsum('qi,qij->j',r,j)
        r=np.maximum(0,.15-a['distance'])/.05;terms['clearance']=float(r@r);grad['clearance']=(-2*r/.05)@a['jdistance']
        terms['time']=.1*float(dt.sum());grad['time']=.1*self.jt.sum(axis=0)
        return terms,grad
    def objective(self,x):
        t,j=self.terms(x);return sum(t.values()),sum(j.values())
    def constraints(self,x):
        a=self.quantities(x);g=[a['distance']-.025,.3-a['v'],.4-a['w'],.4+a['w'],.5-a['accel'],.5+a['accel'],self.alpha-a['angular'],self.alpha+a['angular']]
        j=[a['jdistance'],-a['jv'],-a['jw'],a['jw'],-a['jacc'],a['jacc'],-a['jangular'],a['jangular']]
        if not self.allow_rotation:
            # Zero speed cannot carry a nonzero yaw rate unless reference>90deg.
            g += [40*a['v']-a['w'],40*a['v']+a['w']];j += [40*a['jv']-a['jw'],40*a['jv']+a['jw']]
        return np.concatenate(g),np.vstack(j)
    def boundary(self,x):
        a=self.quantities(x);dt=a['dt'][0];pose=integrate_se2([0.,0.,0.],self.v0,self.w0,float(dt));derivative=np.array([self.v0*np.cos(self.w0*dt),self.v0*np.sin(self.w0*dt),self.w0])
        residual=np.r_[a['p'][1]-pose[:2],a['h'][1]-pose[2]]
        jac=np.vstack([self.jp[1],self.jh[1]])-derivative[:,None]*self.jt[0]
        return residual,jac
    def observe(self,x):self.check();self.iterations+=1
    def result(self,x):
        a=self.quantities(x);terms,_=self.terms(x);total=sum(terms.values());world=a['p']@self.R.T+self.B[:2]
        return dict(poses=np.c_[world,wrap(a['h']+self.B[2])].tolist(),dt=a['dt'].tolist(),speed=a['v'].tolist(),omega=a['w'].tolist(),
            cost_terms=terms,cost_fractions={k:v/total if total else 0. for k,v in terms.items()},trajectory_time_s=float(a['dt'].sum()),allow_rotation=self.allow_rotation,
            max_abs_w=float(abs(a['w']).max()),max_abs_a=float(abs(a['accel']).max()),max_abs_angular_acceleration=float(abs(a['angular']).max()),
            start_pose_error=float(np.max(abs(np.r_[world[0]-self.B[:2],wrap(a['h'][0])]))),start_speed_error=float(abs(a['v'][0]-self.v0)),start_omega_error=float(abs(a['w'][0]-self.w0)))

def solve(B,vw,path,field,alpha,warm=None,started=None):
    started=time.perf_counter() if started is None else started;deadline=started+.15;graph=HandoffGraph(B,vw,path,field,alpha,deadline)
    out=dict(accepted=False,solver_success=False,disposition='SOLVER_FAILURE',iterations=0,warm_start=warm is not None)
    try:
        x=graph.initial(warm)
        res=minimize(graph.objective,x,jac=True,method='SLSQP',bounds=graph.bounds,
            constraints=[dict(type='ineq',fun=lambda x:graph.constraints(x)[0],jac=lambda x:graph.constraints(x)[1]),dict(type='eq',fun=lambda x:graph.boundary(x)[0],jac=lambda x:graph.boundary(x)[1])],
            callback=graph.observe,options=dict(maxiter=100,ftol=1e-8))
        graph.check();out.update(solver_success=bool(res.success),message=str(res.message),iterations=int(res.nit))
        if res.success:
            out.update(graph.result(res.x));g,_=graph.constraints(res.x);e,_=graph.boundary(res.x)
            feasible=bool(g.min()>=-1e-7 and abs(e).max()<=1e-7 and out['start_speed_error']<=1e-7 and out['start_omega_error']<=1e-7)
            out['feasible']=feasible
            if feasible:
                cert=certificate(np.asarray(out['poses'])[:,:2],field);out['certificate']=cert;graph.check()
                out.update(accepted=cert['passed'],disposition='ACCEPTED' if cert['passed'] else 'CERTIFICATE_FAILURE')
            else:out['disposition']='CONSTRAINT_FAILURE'
    except TimeoutError:out.update(accepted=False,disposition='TIMEOUT')
    except Exception as exc:out.update(accepted=False,disposition='EXCEPTION',error=repr(exc))
    out['wall_s']=time.perf_counter()-started;out['over_deadline']=out['wall_s']>.15
    if out['over_deadline']:out.update(accepted=False,disposition='TIMEOUT')
    return out
