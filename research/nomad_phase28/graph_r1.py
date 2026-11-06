"""R1: NA-rollout initialization, initial rate bounds, physical variable scaling.

Original five costs, all other constraints, SLSQP options and deadline unchanged.
"""
import time
from types import SimpleNamespace
import numpy as np
from scipy.optimize import minimize,Bounds
from nomad_isaac.common import integrate_se2
from .alignment import NoAlignment
from .graph import HandoffGraph,certificate,wrap
from .tracking import TimedFollower

# One second at the frozen v/omega limits, and one second of interval time.
SCALE=np.r_[np.tile([.3,.3,.4],10),np.ones(10)]

def na_initial(B,vw,path,dt):
    """Exact72Hz NA commands; pad at the reached chunk end, never snap a pose."""
    ctl=NoAlignment();ctl.replace_path(path,B,float(vw[0]));pose=np.asarray(B,float).copy();v,w=map(float,vw)
    horizon=float(np.sum(dt));count=int(np.ceil(horizon*72));poses=[pose.copy()];times=[0.];ended=False;end_time=None
    for tick in range(count):
        s,_=ctl.follower.path.project(pose[:2]);near=np.linalg.norm(pose[:2]-ctl.follower.path.points[-1])<=ctl.follower.settings['endpoint_tolerance_m']
        if s>=ctl.follower.path.s[-1]-1e-12 or near:ended=True
        if not ended and tick%8==0:
            (v,w),diag=ctl.control(pose,v);ended=bool(diag['completed'])
        if ended:
            if end_time is None:end_time=tick/72
            v=w=0.
        else:pose=integrate_se2(pose,v,w,1/72)
        poses.append(pose.copy());times.append((tick+1)/72)
    poses=np.asarray(poses);sample=np.r_[0.,np.cumsum(dt)]
    q=np.c_[np.interp(sample,times,poses[:,0]),np.interp(sample,times,poses[:,1]),np.interp(sample,times,np.unwrap(poses[:,2]))]
    return q,dict(horizon_s=horizon,integration_ticks=count,endpoint_hold=ended,endpoint_reached_s=end_time,
        endpoint_distance_m=float(np.linalg.norm(q[-1,:2]-ctl.follower.path.points[-1])),dt=dt.tolist())

class R1Graph(HandoffGraph):
    def initial(self,warm=None):
        # Reuse the frozen cold/previous-dt horizon, but replace all initial poses.
        clock=super().initial(warm)[30:]
        q,self.initialization=na_initial(self.B,[self.v0,self.w0],self.native_path,clock)
        local=(q[:,:2]-self.B[:2])@self.R
        return np.r_[np.c_[local[1:],np.unwrap(q[:,2]-self.B[2])[1:]].ravel(),clock]
    def __init__(self,B,vw,path,field,alpha,deadline=float('inf')):
        super().__init__(B,vw,path,field,alpha,deadline);self.native_path=np.asarray(path).copy();self.last_iterate=None
    def initial_rates(self,x):
        a=self.quantities(x);span=a['dt'][0]/2;js=self.jt[0]/2
        acc=(a['v'][0]-self.v0)/span;ja=a['jv'][0]/span-acc/span*js
        angular=(a['w'][0]-self.w0)/span;jw=a['jw'][0]/span-angular/span*js
        return float(acc),ja,float(angular),jw
    def constraints(self,x):
        g,j=super().constraints(x);a,ja,w,jw=self.initial_rates(x)
        return np.r_[g,.5-a,.5+a,self.alpha-w,self.alpha+w],np.vstack([j,-ja,ja,-jw,jw])
    def observe(self,x):self.last_iterate=np.array(x).copy();super().observe(x)
    def result(self,x):
        r=super().result(x);a,_,w,_=self.initial_rates(x)
        r.update(max_abs_a=max(r['max_abs_a'],abs(a)),max_abs_angular_acceleration=max(r['max_abs_angular_acceleration'],abs(w)),
            initial_acceleration=a,initial_angular_acceleration=w,initial_vw=[self.v0,self.w0],
            first_midpoint_speed_delta=r['speed'][0]-self.v0,first_midpoint_omega_delta=r['omega'][0]-self.w0,
            initial_time_anchor_speed_error=0.,initial_time_anchor_omega_error=0.)
        return r
    def scaled_objective(self,z):
        f,j=self.objective(z*SCALE);return f,j*SCALE
    def scaled_constraints(self,z):
        g,j=self.constraints(z*SCALE);return g,j*SCALE[None,:]

class R1Follower(TimedFollower):
    """Same feedback/clip; interpolate from the now explicit initial v/omega."""
    def __init__(self,result,start_s,alpha):
        xy=np.asarray(result['poses'])[:,:2]
        if np.max(np.linalg.norm(xy-xy[0],axis=1))<=1e-12:
            # A padded stationary initial trajectory is a valid timed output;
            # do not invent a spatial chord just to construct a PP helper.
            self.result=result;self.q=np.asarray(result['poses']);self.dt=np.asarray(result['dt']);self.times=np.r_[0.,np.cumsum(self.dt)];self.mid=(self.times[:-1]+self.times[1:])/2
            self.start_s=start_s;self.now_s=start_s;self.alpha=alpha;self.mode='GO';self.trigger_S=False;self.target_yaw=None
            self.follower=SimpleNamespace(path=SimpleNamespace(points=xy.copy(),s=np.zeros(len(xy))))
            self.plan=dict(s_m=[0.]*len(xy),v_m_s=[0.]*len(xy),v_limit_m_s=[0.]*len(xy),kappa_m_inv=[0.]*len(xy))
        else:super().__init__(result,start_s,alpha)
        self.mid=np.r_[0.,self.mid]
        self.result=dict(result,speed=[result['initial_vw'][0],*result['speed']],omega=[result['initial_vw'][1],*result['omega']])
        self.previous_w=result['initial_vw'][1]

def violations(graph,x,revision):
    """Pure diagnostic evaluation, excluded from planner latency after its return."""
    deadline=graph.deadline;graph.deadline=float('inf')
    try:
        if not np.isfinite(x).all():return dict(groups={'NONFINITE':dict(maximum=None,count=int((~np.isfinite(x)).sum()),relative_max=None,unit='nonfinite')},dominant='NONFINITE')
        a=graph.quantities(x);dt=a['dt'];res={}
        def add(name,values,scale,unit):
            v=np.maximum(0.,np.atleast_1d(values));res[name]=dict(maximum=float(v.max()),count=int(np.sum(v>1e-7)),relative_max=float(v.max()/scale),unit=unit)
        add('SDF',.025-a['distance'],.025,'m');add('SPEED',a['v']-.3,.3,'m/s');add('OMEGA',abs(a['w'])-.4,.4,'rad/s')
        add('ACCELERATION',abs(a['accel'])-.5,.5,'m/s2');add('ANGULAR_ACCELERATION',abs(a['angular'])-graph.alpha,graph.alpha,'rad/s2')
        if not graph.allow_rotation:add('NO_STATIONARY_ROTATION',abs(a['w'])-40*a['v'],.4,'rad/s')
        add('DT_LOWER',.1-dt,.1,'s');add('DT_UPPER',dt-1.,1.,'s');add('YAW_BOUND',abs(a['h'][1:])-4*np.pi,4*np.pi,'rad')
        if revision=='ORIGINAL':
            e,_=graph.boundary(x);add('FIRST_TWIST_POSITION_EQUALITY',abs(e[:2]),.05,'m');add('FIRST_TWIST_HEADING_EQUALITY',abs(e[2]),.4,'rad')
        else:
            av,_,aw,_=graph.initial_rates(x);add('INITIAL_ACCELERATION',abs(av)-.5,.5,'m/s2');add('INITIAL_ANGULAR_ACCELERATION',abs(aw)-graph.alpha,graph.alpha,'rad/s2')
        bad=[(k,v) for k,v in res.items() if v['maximum']>1e-7]
        dominant=max(bad,key=lambda z:z[1]['relative_max'])[0] if bad else 'NONE_FEASIBLE'
        return dict(groups=res,dominant=dominant)
    finally:graph.deadline=deadline

def solve(B,vw,path,field,alpha,warm=None,started=None):
    started=time.perf_counter() if started is None else started
    graph=R1Graph(B,vw,path,field,alpha,started+.15);x0=last=None;initial_valid=False;initial_result=None;initial_cert=None;returned=False
    out=dict(accepted=False,solver_success=False,output_type='FALLBACK',disposition='SOLVER_FAILURE',iterations=0,warm_dt_used=warm is not None)
    try:
        x0=graph.initial(warm);last=x0.copy();graph.check();g,_=graph.constraints(x0)
        bounds_ok=bool(np.all(x0>=graph.bounds.lb-1e-9) and np.all(x0<=graph.bounds.ub+1e-9))
        if g.min()>=-1e-7 and bounds_ok:
            initial_result=graph.result(x0);initial_cert=certificate(np.asarray(initial_result['poses'])[:,:2],field);graph.check();initial_valid=initial_cert['passed']
        res=minimize(graph.scaled_objective,x0/SCALE,jac=True,method='SLSQP',bounds=Bounds(graph.bounds.lb/SCALE,graph.bounds.ub/SCALE),
            constraints=[dict(type='ineq',fun=lambda z:graph.scaled_constraints(z)[0],jac=lambda z:graph.scaled_constraints(z)[1])],
            callback=lambda z:graph.observe(z*SCALE),options=dict(maxiter=100,ftol=1e-8))
        returned=True;last=res.x*SCALE;graph.check();out.update(solver_success=bool(res.success),exit_mode=int(res.status),message=str(res.message),iterations=int(res.nit))
        if res.success:
            g,_=graph.constraints(last)
            feasible=bool(g.min()>=-1e-7 and np.all(last>=graph.bounds.lb-1e-9) and np.all(last<=graph.bounds.ub+1e-9))
            if feasible:
                candidate=graph.result(last);cert=certificate(np.asarray(candidate['poses'])[:,:2],field);graph.check();out['optimized_certificate']=cert
                if cert['passed']:out.update(candidate,accepted=True,output_type='OPTIMIZED',disposition='OPTIMIZED')
                else:out['disposition']='CERTIFICATE_FAILURE'
            else:out['disposition']='CONSTRAINT_FAILURE'
        if not out['accepted'] and initial_valid:
            reason=out['disposition'];out.update(initial_result,accepted=True,output_type='INIT_ONLY',disposition='INIT_ONLY',optimized_failure=reason,initial_certificate=initial_cert)
    except TimeoutError:out.update(accepted=False,output_type='FALLBACK',disposition='TIMEOUT')
    except Exception as exc:out.update(accepted=False,output_type='FALLBACK',disposition='EXCEPTION',error=repr(exc))
    out['planning_wall_s']=time.perf_counter()-started;out['wall_s']=out['planning_wall_s'];out['over_deadline']=out['wall_s']>.15
    if out['over_deadline']:out.update(accepted=False,output_type='FALLBACK',disposition='TIMEOUT')
    # Retain last major iterate, rather than silently losing failure evidence.
    if graph.last_iterate is not None and not returned:last=graph.last_iterate
    out['initial_valid']=bool(initial_valid);out['initial_certificate']=initial_cert;out['initialization']=getattr(graph,'initialization',None)
    diagnostic_start=time.perf_counter()
    if x0 is not None:out['initial_x']=x0.tolist();out['initial_violation']=violations(graph,x0,'R1')
    if last is not None:out['last_x']=last.tolist();out['last_violation']=violations(graph,last,'R1')
    out['diagnostic_wall_s']=time.perf_counter()-diagnostic_start
    out['wall_s']=time.perf_counter()-started;out['over_deadline']=out['wall_s']>.15
    if out['over_deadline']:out.update(accepted=False,output_type='FALLBACK',disposition='TIMEOUT')
    return out
