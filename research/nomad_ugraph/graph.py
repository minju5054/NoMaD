"""Analytic SLSQP with exact elimination of the hard unicycle equalities.

The specified26states and25controls exist in the solution. Only50control
coordinates are optimized; fixing x0 and eliminating x[k+1]=F(x[k],u[k]) is
algebraically equivalent to the150-variable multiple-shooting formulation.
"""
import numpy as np
from scipy.optimize import minimize,Bounds
from nomad_phase0.pure_pursuit import XYPath
from .dynamics import DT,N,step,trajectory

TOL=1e-7

def references(samples,B):
    refs=[];directions=[];remaining=[]
    for xy in np.asarray(samples,float):
        try:
            path=XYPath(xy);s,_=path.project(B[:2]);length=float(path.s[-1]-s)
            ref=np.asarray([path.at(t) for t in np.linspace(s,path.s[-1],N+1)])
        except ValueError:
            ref=np.repeat(xy[-1][None],N+1,axis=0);length=0.
        delta=xy[-1]-B[:2];norm=np.linalg.norm(delta)
        refs.append(ref);directions.append(delta/norm if norm>1e-12 else np.zeros(2));remaining.append(length)
    return np.asarray(refs),np.asarray(directions),remaining

def shifted_prior(previous,current_time):
    if previous is None:return None,None
    times=previous['time_s']+DT*np.arange(N+1);query=current_time+DT*np.arange(N+1)
    valid=(query>=times[0])&(query<=times[-1]+1e-10)
    if not valid.any():return None,None
    xy=np.asarray(previous['states'])[:,:2]
    return np.column_stack([np.interp(query,times,xy[:,axis]) for axis in (0,1)]),valid

class Graph:
    def __init__(self,initial,omega,samples,field,previous=None,time_s=0.):
        self.x0=np.asarray(initial,float);assert self.x0.shape==(4,) and np.isfinite(self.x0).all()
        self.omega=float(omega);self.samples=np.asarray(samples,float);assert self.samples.shape==(8,8,2)
        self.ref,self.direction,self.remaining=references(self.samples,self.x0)
        self.previous,self.previous_mask=shifted_prior(previous,time_s);self.field=field
        assert abs(field.radius-.09)<1e-12
        self.low=field.origin+1e-9;self.high=field.origin+(np.array(field.values.shape[::-1])-1)*field.h-1e-9
        lo=np.tile([-.5,-.4],N);hi=np.tile([.5,.4],N);lo[1]=hi[1]=self.omega
        self.bounds=Bounds(lo,hi);self.cache=None
        self.smooth=np.zeros((2*(N-1),2*N))
        for k in range(N-1):
            for axis,scale in ((0,.5),(1,.4)):
                row=2*k+axis;self.smooth[row,2*k+axis]=-1/scale;self.smooth[row,2*(k+1)+axis]=1/scale
    def values(self,z):
        if self.cache is not None and np.array_equal(z,self.cache[0]):return self.cache[1]
        x,j=trajectory(self.x0,z);p=x[:,:2];jp=j[:,:2];clipped=np.clip(p,self.low,self.high)
        d,gradient=self.field.query(clipped);mask=(p>=self.low)&(p<=self.high)
        jd=np.einsum('ki,kij->kj',gradient*mask,jp)
        diff=p[None]-self.ref;mix=np.sum(diff**2,axis=(1,2))/.1**2;active=int(np.argmin(mix));err=diff[active]
        costs=dict(intent=float(mix[active]));g=2*np.einsum('ki,kij->j',err,jp)/.1**2
        costs['consistency']=0.
        if self.previous is not None:
            ids=self.previous_mask.copy();delta=p[ids]-self.previous[ids]
            costs['consistency']=float(np.sum(delta**2)/.2**2);g+=2*np.einsum('ki,kij->j',delta,jp[ids])/.2**2
        costs['progress']=-float((p[-1]-p[0])@self.direction[active]);g-=self.direction[active]@jp[-1]
        deficit=np.maximum(0,.15-d);costs['clearance']=float(np.sum(deficit**2)/.05**2);g-=2*deficit@jd/.05**2
        residual=self.smooth@z;costs['control_smoothness']=float(residual@residual);g+=2*residual@self.smooth
        constraints=np.r_[.3-x[:,3],.3+x[:,3],d-.025,(p-self.low).ravel(),(self.high-p).ravel()]
        jac=np.vstack([-j[:,3],j[:,3],jd,jp.reshape(-1,2*N),-jp.reshape(-1,2*N)])
        result=dict(states=x,sensitivity=j,distances=d,active=active,costs=costs,objective=sum(costs.values()),gradient=g,
                    inequalities=constraints,jacobian=jac,terminal=x[-1,3],terminal_jacobian=j[-1,3])
        self.cache=(np.array(z,copy=True),result);return result
    def objective(self,z):
        r=self.values(z);return r['objective'],r['gradient']
    def inequality(self,z):return self.values(z)['inequalities']
    def inequality_jac(self,z):return self.values(z)['jacobian']
    def equality(self,z):return np.array([self.values(z)['terminal']])
    def equality_jac(self,z):return self.values(z)['terminal_jacobian'][None]
    def check(self,z):
        r=self.values(z);bounds=float(max(np.max(self.bounds.lb-z),np.max(z-self.bounds.ub),0.))
        violation=float(max(-r['inequalities'].min(),abs(r['terminal']),bounds,0.))
        return dict(hard_feasible=violation<=TOL,maximum_violation=violation,minimum_node_clearance_m=float(r['distances'].min()),
                    terminal_v=float(r['states'][-1,3]),maximum_abs_v=float(abs(r['states'][:,3]).max()),maximum_abs_omega=float(abs(z.reshape(N,2)[:,1]).max()),maximum_abs_a=float(abs(z.reshape(N,2)[:,0]).max()))
    def initial_controls(self,which):
        q=self.x0.copy();u=[]
        for k in range(N):
            if which<8:
                target=self.ref[which,min(k+1,N)];delta=target-q[:2];forward=np.array([np.cos(q[2]),np.sin(q[2])]);lateral=np.array([-forward[1],forward[0]])
                target_v=float(np.clip(float(delta@forward)/DT,-.3,.3))
                desired_w=float(np.clip(2*target_v*(delta@lateral)/max(delta@delta,1e-8),-.4,.4))
            else:target_v=0.;desired_w=.4 if which==9 else -.4 if which==10 else 0.
            braking=(N-k)<=int(np.ceil(abs(q[3])/(.5*DT)))+1
            if braking or which>=8:a=-np.sign(q[3])*min(.5,abs(q[3])/DT)
            else:a=float(np.clip((target_v-q[3])/DT,-.5,.5))
            w=self.omega if k==0 else desired_w
            control=[float(a),float(w)];u.extend(control);q=step(q,control)[0]
        return np.asarray(u)

def solve_start(graph,index,maxiter=100):
    import time
    start=time.perf_counter();z=graph.initial_controls(index)
    result=minimize(graph.objective,z,jac=True,method='SLSQP',bounds=graph.bounds,
        constraints=[dict(type='ineq',fun=graph.inequality,jac=graph.inequality_jac),dict(type='eq',fun=graph.equality,jac=graph.equality_jac)],
        options=dict(maxiter=maxiter,ftol=1e-8,disp=False))
    value=graph.values(result.x);check=graph.check(result.x)
    return dict(start_index=index,solver_success=bool(result.success),status=int(result.status),message=str(result.message),iterations=int(result.nit),
        evaluations=int(result.nfev),objective=float(value['objective']),costs=value['costs'],active_candidate=value['active'],
        controls=result.x.reshape(N,2).tolist(),states=value['states'].tolist(),wall_s=time.perf_counter()-start,**check)
