"""B-local SE(2)+time graph; depth and all eight policies are its only map/prior inputs."""
import time
import numpy as np
from scipy.optimize import minimize,Bounds
from scipy.ndimage import label
from nomad_phase0.graph_v4 import menger
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase15.evaluate import suffix

N=10;DIM=40
def wrap(a):return (np.asarray(a)+np.pi)%(2*np.pi)-np.pi
def resample(p,n=11):
    p=np.asarray(p,dtype=float);s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    keep=np.r_[True,np.diff(s)>1e-10];p,s=p[keep],s[keep]
    if len(p)==1:return np.repeat(p,n,axis=0)
    return np.c_[np.interp(np.linspace(0,s[-1],n),s,p[:,0]),np.interp(np.linspace(0,s[-1],n),s,p[:,1])]

def prepare_candidates(samples,B,old=None,short_policy='retain'):
    """Suffix projection reused verbatim; no safety filtering or candidate removal."""
    result=[];flags=[]
    for i,p in enumerate(samples):
        tail,length=suffix(p,B);supplemented=False
        if length<.3 and old is not None:
            old_tail,old_length=suffix(old,tail[-1])
            if old_length>0:
                # Only the observed OLD suffix after the new endpoint projection.
                poly=XYPath(old_tail);end=min(.3-length,old_length)
                extension=np.vstack([poly.points[poly.s<end],poly.at(end)])
                tail=np.vstack([tail,extension]);supplemented=True
        p=np.vstack([np.asarray(B)[:2],tail]);total=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
        flags.append(dict(sample=i,native_remaining_m=length,supplemented=supplemented,still_short=total<.3))
        if total<.3 and short_policy!='retain':raise ValueError('SHORT_INPUT_POLICY_NOT_RESOLVED')
        result.append(resample(p))
    q=np.array(result);sigma=float(np.clip(np.median(np.sqrt(np.var(q[:,1:,:],axis=0).sum(axis=1))),.03,.15))
    return q,sigma,flags

def side_initializations(candidates,B,field):
    """Only depth connected components and edge waypoints; no search planner."""
    B=np.asarray(B);forward=np.array([np.cos(B[2]),np.sin(B[2])]);left=np.array([-forward[1],forward[0]])
    cells,valid=field.cells(B[None,:2]);x,y=cells[0];r=int(np.ceil(2./field.h));h,w=field.occupied.shape
    x0,x1=max(0,x-r),min(w,x+r+1);y0,y1=max(0,y-r),min(h,y+r+1)
    if x0>=x1 or y0>=y1:return [],dict(reason='B_OUTSIDE_MAP')
    labs,count=label(field.occupied[y0:y1,x0:x1],structure=np.array([[0,1,0],[1,1,1],[0,1,0]]));crossed=set()
    # Identify components actually intersecting a candidate footprint.
    for path in candidates:
        for a,b in zip(path[:-1],path[1:]):
            q=np.linspace(a,b,max(2,int(np.ceil(np.linalg.norm(b-a)/.02))+1));ij,ok=field.cells(q)
            for ix,iy in ij[ok]:
                rad=int(np.ceil(field.radius/field.h));lo=max(0,iy-y0-rad);hi=min(labs.shape[0],iy-y0+rad+1);lx=max(0,ix-x0-rad);hx=min(labs.shape[1],ix-x0+rad+1)
                if lo<hi and lx<hx:crossed.update(int(v) for v in np.unique(labs[lo:hi,lx:hx]) if v)
    components=[]
    for identity in sorted(crossed):
        yy,xx=np.nonzero(labs==identity);points=field.origin+np.c_[xx+x0,yy+y0]*field.h;delta=points-B[:2]
        near=np.linalg.norm(delta,axis=1)<=2.;points=points[near]
        if not len(points):continue
        along=(points-B[:2])@forward
        if np.max(along)<0:continue
        components.append((max(0.,float(along.min())),identity,points))
    if not components:return [],dict(reason='NO_INTERSECTING_DEPTH_COMPONENT')
    _,identity,points=min(components,key=lambda r:(r[0],r[1]));side=(points-B[:2])@left
    end=np.mean(candidates[:,-1],axis=0);routes=[]
    for sign in (1,-1):
        edge=points[int(np.argmax(sign*side))];via=edge+sign*.25*left
        routes.append(resample(np.vstack([B[:2],via,end])))
    return routes,dict(component=identity,cell_count=len(points),source='4-connected depth component; two straight polylines via edge±0.25m')

class UnifiedGraph:
    def __init__(self,B,v0,candidates,sigma,field,weights,deadline_ns,kinematic_sigma=.03):
        self.B=np.array(B);a=B[2];self.R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
        self.candidates=(np.asarray(candidates)-self.B[:2])@self.R;self.sigma=sigma;self.field=field;self.weights=weights;self.v0=float(v0);self.deadline=deadline_ns;self.nh_sigma=kinematic_sigma
        self.trajectory=[];self.best=None;self.evaluations=0
        self.jp=np.zeros((11,2,DIM));self.jh=np.zeros((11,DIM));self.jt=np.zeros((10,DIM))
        for i in range(1,11):self.jp[i,0,3*(i-1)]=1;self.jp[i,1,3*(i-1)+1]=1;self.jh[i,3*(i-1)+2]=1
        self.jt[:,30:]=np.eye(10)
        self.bounds=Bounds(np.r_[np.tile([-np.inf,-np.inf,-4*np.pi],10),np.full(10,.05)],np.r_[np.tile([np.inf,np.inf,4*np.pi],10),np.ones(10)])
    def check(self):
        if time.monotonic_ns()>self.deadline:raise TimeoutError('UNIFIED_DEADLINE')
    def unpack(self,x):
        q=np.vstack([np.zeros(3),np.asarray(x[:30]).reshape(10,3)]);return q[:,:2],q[:,2],x[30:]
    def initial(self,path):
        p=(np.asarray(path)-self.B[:2])@self.R;delta=np.diff(p,axis=0);heading=np.r_[0.,np.unwrap(np.arctan2(delta[:,1],delta[:,0]))]
        dt=np.clip(np.maximum(np.linalg.norm(delta,axis=1)/.2,np.abs(wrap(np.diff(heading)))/.4),.05,1.)
        return np.r_[np.c_[p[1:],heading[1:]].ravel(),dt]
    def active(self,p):
        costs=np.square(self.candidates[:,1:]-p[None,1:]).sum(axis=(1,2))/self.sigma**2
        return int(np.argmin(costs)),costs
    def queries(self,p):
        q=np.vstack([p,(p[:-1]+p[1:])/2]);jq=np.concatenate([self.jp,(self.jp[:-1]+self.jp[1:])/2])
        world=q@self.R.T+self.B[:2]
        low=self.field.origin+1e-8;high=self.field.origin+(np.array(self.field.values.shape[::-1])-1)*self.field.h-1e-8
        clipped=np.clip(world,low,high);distance,gradient=self.field.query(clipped)
        delta=world-clipped;outside=np.linalg.norm(delta,axis=1);mask=outside>0
        distance[mask]=-outside[mask]-self.field.radius;gradient[mask]=-delta[mask]/outside[mask,None]
        local_gradient=gradient@self.R
        jd=np.einsum('qi,qij->qj',local_gradient,jq)
        lengths=np.linalg.norm(np.diff(p,axis=0),axis=1);s=np.r_[0.,np.cumsum(lengths)];sq=np.r_[s,(s[:-1]+s[1:])/2]
        cb=float(self.field.query(self.B[None,:2])[0][0]);margin=np.where(sq<=.3+1e-12,min(.025,max(0.,cb-.005)),.025)
        return distance,jd,margin
    def objective(self,x):
        self.check();self.evaluations+=1;p,h,dt=self.unpack(x);active,costs=self.active(p);target=self.candidates[active]
        residual=(p[1:]-target[1:])/self.sigma;J=self.jp[1:]/self.sigma
        value=float(costs[active]);grad=2*np.einsum('qi,qij->j',residual,J)
        d,jd,_=self.queries(p);r=np.maximum(0,.15-d)/.05;value+=float(r@r);grad+=(-2*r/.05)@jd
        delta=np.diff(p,axis=0);jdelta=np.diff(self.jp,axis=0);c=np.cos(h);s=np.sin(h)
        # Signed equivalent of TEB's absolute nonholonomic residual (same square).
        nh=((c[:-1]+c[1:])*delta[:,1]-(s[:-1]+s[1:])*delta[:,0])/self.nh_sigma
        jnh=((c[:-1]+c[1:])[:,None]*jdelta[:,1]-(s[:-1]+s[1:])[:,None]*jdelta[:,0]
             +(-s[:-1]*delta[:,1]-c[:-1]*delta[:,0])[:,None]*self.jh[:-1]+(-s[1:]*delta[:,1]-c[1:]*delta[:,0])[:,None]*self.jh[1:])/self.nh_sigma
        value+=float(nh@nh);grad+=2*nh@jnh
        forward=c[:-1]*delta[:,0]+s[:-1]*delta[:,1];back=np.minimum(0,forward)/self.nh_sigma
        jf=(c[:-1,None]*jdelta[:,0]+s[:-1,None]*jdelta[:,1]+(-s[:-1]*delta[:,0]+c[:-1]*delta[:,1])[:,None]*self.jh[:-1])/self.nh_sigma
        value+=float(back@back);grad+=2*back@jf
        wt,wg,wc=(self.weights[k] for k in ('time','goal','curvature'))
        value+=wt*float(dt.sum());grad+=wt*self.jt.sum(axis=0)
        goal=(p[-1]-target[-1])/.3;value+=wg*float(goal@goal);grad+=2*wg*goal@(self.jp[-1]/.3)
        k,jk=menger(p);jkp=jk.reshape(len(k),22)@self.jp.reshape(22,DIM)
        lengths=np.linalg.norm(np.diff(p,axis=0),axis=1);valid=(lengths[:-1]>=.01)&(lengths[1:]>=.01)&(np.linalg.norm(p[2:]-p[:-2],axis=1)>=.01)
        mask=valid[:-1]&valid[1:];dk=np.diff(k)*mask;jdiff=np.diff(jkp,axis=0)*mask[:,None]
        value+=wc*float(dk@dk);grad+=2*wc*dk@jdiff
        return value,grad
    def constraints(self,x):
        self.check();p,h,dt=self.unpack(x);delta=np.diff(p,axis=0);length=np.linalg.norm(delta,axis=1);jdelta=np.diff(self.jp,axis=0)
        jl=np.einsum('qi,qij->qj',delta/np.maximum(length[:,None],1e-12),jdelta);v=length/dt;jv=jl/dt[:,None]-length[:,None]/dt[:,None]**2*self.jt
        angle=wrap(np.diff(h));ja=np.diff(self.jh,axis=0);w=angle/dt;jw=ja/dt[:,None]-angle[:,None]/dt[:,None]**2*self.jt
        dv=np.r_[v[0]-self.v0,np.diff(v)];jdv=np.vstack([jv[0],np.diff(jv,axis=0)])
        span=np.r_[dt[0],(dt[1:]+dt[:-1])/2];jspan=np.vstack([self.jt[0],(self.jt[1:]+self.jt[:-1])/2]);acc=dv/span;ja0=jdv/span[:,None]-dv[:,None]/span[:,None]**2*jspan
        d,jd,margin=self.queries(p)
        return np.r_[d-margin,.3-v,.4-w,.4+w,.5-acc,.5+acc],np.vstack([jd,-jv,-jw,jw,-ja0,ja0])
    def observe(self,x):
        self.check();value,_=self.objective(x);g,_=self.constraints(x);p,_,_=self.unpack(x);active,_=self.active(p)
        self.trajectory.append(active)
        if g.min()>=-1e-7 and np.all(x>=self.bounds.lb-1e-9) and np.all(x<=self.bounds.ub+1e-9):
            if self.best is None or value<self.best[0]:self.best=(value,x.copy(),time.monotonic_ns())

def solve_start(B,v0,candidates,sigma,field,weights,path,deadline_ns,kinematic_sigma=.03,warm_state=None):
    started=time.monotonic_ns();g=UnifiedGraph(B,v0,candidates,sigma,field,weights,deadline_ns,kinematic_sigma);status='TIMEOUT';success=False
    try:
        initial=g.initial(path)
        if warm_state is not None:
            poses=np.asarray(warm_state['poses']);local=(poses[1:,:2]-g.B[:2])@g.R
            initial=np.r_[np.c_[local,wrap(poses[1:,2]-B[2])].ravel(),np.clip(warm_state['dt'],.05,1.)]
        g.observe(initial)
        result=minimize(g.objective,initial,jac=True,method='SLSQP',bounds=g.bounds,constraints=[dict(type='ineq',fun=lambda x:g.constraints(x)[0],jac=lambda x:g.constraints(x)[1])],callback=g.observe,options=dict(maxiter=100,ftol=1e-8))
        success=bool(result.success);status=str(result.message);g.observe(result.x)
    except TimeoutError:pass
    ended=time.monotonic_ns();out=dict(accepted=g.best is not None,solver_success=success,disposition=status,wall_s=(ended-started)/1e9,end_ns=ended,active_switches=sum(a!=b for a,b in zip(g.trajectory[:-1],g.trajectory[1:])),iterate_count=len(g.trajectory),evaluations=g.evaluations)
    if g.best is not None:
        cost,x,ready=g.best;p,h,dt=g.unpack(x);world=p@g.R.T+g.B[:2];active,_=g.active(p)
        out.update(cost=cost,poses=np.c_[world,wrap(h+B[2])].tolist(),path=world.tolist(),dt=dt.tolist(),speed=(np.linalg.norm(np.diff(p,axis=0),axis=1)/dt).tolist(),active_candidate=active,ready_ns=ready)
    return out
