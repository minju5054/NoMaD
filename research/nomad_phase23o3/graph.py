"""F7 stays inside the graph; no trigger, u_ref, search or extra execution rule."""
import time,types,traceback
import numpy as np
from scipy.optimize import minimize
from nomad_phase15b.depth import Snapshot
from nomad_phase23 import anytime
from nomad_phase23.graph import wrap
from nomad_phase23o2.graph import U2Graph,mixture,plan as u2_plan


def intent_direction(local_candidates,ages,T_m):
    delta=np.asarray(local_candidates)[:,-1]-np.asarray(local_candidates)[:,0];length=np.linalg.norm(delta,axis=1);valid=length>=.05
    if not valid.any():return np.zeros(2),dict(enabled=False,reason='NO_VALID_ENDPOINT',valid_candidates=0)
    weights=np.exp(-np.asarray(ages)[valid]/T_m);mean=np.sum(weights[:,None]*delta[valid]/length[valid,None],axis=0)/weights.sum();norm=float(np.linalg.norm(mean))
    if norm<=1e-12:return np.zeros(2),dict(enabled=False,reason='UNDEFINED_CANCELED_MEAN',valid_candidates=int(valid.sum()))
    return mean/norm,dict(enabled=True,reason='MEMORY_ENDPOINTS',valid_candidates=int(valid.sum()),mean_norm=norm)


class U3Graph(U2Graph):
    def __init__(self,*args,**kwargs):
        weights=args[5] if len(args)>5 else kwargs['weights'];self.w7=float(weights['u2']['w7'])
        super().__init__(*args,**kwargs);self.direction,self.direction_info=intent_direction(self.candidates,self.ages,self.memory_T);self.u3_cache=None
    def f7(self,x):
        p,_,_=self.unpack(x);progress=float((p[-1]-p[0])@self.direction)
        residual=max(0.,1.2-progress)/.10 if self.direction_info['enabled'] else 0.
        grad=-2*self.w7*residual/.10*self.direction@(self.jp[-1]-self.jp[0])
        return self.w7*residual**2,grad,progress,residual
    def objective(self,x):
        self.check()
        if self.u3_cache is not None and np.array_equal(x,self.u3_cache[0]):return self.u3_cache[1]
        value,grad=super().objective(x);extra,j,_,_=self.f7(x)
        result=(value+extra,grad+j);self.u3_cache=(np.array(x,copy=True),result);return result


def iterate_candidate(g,x):
    """Last iterate may relax only kinematics, never the depth inequalities."""
    value,_=g.objective(x);h,_=g.constraints(x);p,yaw,dt=g.unpack(x)
    v=np.linalg.norm(np.diff(p,axis=0),axis=1)/dt;w=wrap(np.diff(yaw))/dt
    f2=float(h[:21].min());ok=bool(np.isfinite(x).all() and f2>=0. and np.max(v)<=.33+1e-12 and np.max(np.abs(w))<=.44+1e-12 and np.min(dt)>=.045-1e-12 and np.max(dt)<=1.10+1e-12)
    if not ok:return None
    world=p@g.R.T+g.B[:2];active,_=g.active(p)
    return dict(cost=value,ready_ns=time.monotonic_ns(),path=world.tolist(),poses=np.c_[world,wrap(yaw+g.B[2])].tolist(),dt=dt.tolist(),active_candidate=active,
        f2_minimum_slack_m=f2,v_max=float(v.max()),omega_max=float(np.abs(w).max()),dt_min=float(dt.min()),dt_max=float(dt.max()),output_type='KINEMATIC_TOLERATED')

_key=None;_field=None

def worker(payload,channel):
    global _key,_field
    index=payload['index'];deadline=payload['deadline_ns'];iteration=0;last_published=None;switches=0
    def send(message):
        try:channel.send(dict(index=index,published_ns=time.monotonic_ns(),**message))
        except (BrokenPipeError,EOFError,OSError):pass
    try:
        key=(payload['snapshot_file'],deadline)
        if key!=_key:_field=Snapshot.load(payload['snapshot_file']);_key=key
        g=U3Graph(payload['B'],payload['v0'],np.asarray(payload['candidates']),payload['sigma'],_field,payload['weights'],deadline,.03)
        def observe(x):
            nonlocal last_published,switches
            g.observe(x)
            if len(g.trajectory)>1:switches+=g.trajectory[-1]!=g.trajectory[-2]
            # A delivered feasible iterate always takes precedence, so avoid
            # serializing unused tolerated paths once this start is feasible.
            last=iterate_candidate(g,x) if g.best is None else None
            message=dict(kind='PROGRESS',iteration=iteration,mixture_switches=switches,last_candidate=last,**anytime.constraint_status(g,x))
            if g.best is not None and g.best[2]!=last_published:
                cost,z,ready=g.best;p,yaw,dt=g.unpack(z);world=p@g.R.T+g.B[:2];active,_=g.active(p)
                message.update(kind='FEASIBLE',cost=cost,ready_ns=ready,path=world.tolist(),poses=np.c_[world,wrap(yaw+g.B[2])].tolist(),dt=dt.tolist(),active_candidate=active,output_type='FEASIBLE');last_published=ready
            send(message)
        def callback(x):
            nonlocal iteration
            iteration+=1;observe(x)
        x=g.initial(np.asarray(payload['path']));observe(x)
        result=minimize(g.objective,x,jac=True,method='SLSQP',bounds=g.bounds,constraints=[dict(type='ineq',fun=lambda z:g.constraints(z)[0],jac=lambda z:g.constraints(z)[1])],callback=callback,options=dict(maxiter=100,ftol=1e-8))
        iteration=int(result.nit);observe(result.x)
        send(dict(kind='DONE',iteration=iteration,iteration_limit=iteration>=100,solver_success=bool(result.success),message=str(result.message)))
    except TimeoutError:send(dict(kind='DONE',iteration=iteration,iteration_limit=False,solver_success=False,message='DEADLINE'))
    except BaseException as exc:send(dict(kind='ERROR',error=repr(exc),traceback=traceback.format_exc()));raise
    finally:channel.close()


def choose_output(delivery,deadline):
    if delivery['selected'] is not None:return dict(delivery['selected'],output_type='FEASIBLE')
    candidates=[]
    for index,last in delivery['latest'].items():
        candidate=last.get('last_candidate')
        if candidate is not None and candidate['ready_ns']<=deadline and last['received_ns']<=deadline:
            candidates.append(dict(candidate,index=index,received_ns=last['received_ns']))
    return min(candidates,key=lambda r:(r['cost'],r['index'])) if candidates else None

class Collector:
    @staticmethod
    def collect(pool,payloads,deadline_ns,task):
        result=anytime.collect(pool,payloads,deadline_ns,task=task);result['selected']=choose_output(result,deadline_ns);return result

_plan_kernel=types.FunctionType(u2_plan.__code__,dict(u2_plan.__globals__,anytime=Collector,worker=worker),argdefs=u2_plan.__defaults__)
def plan(pool,case,settings,policy):
    result=_plan_kernel(pool,case,dict(c=1.,T_m=settings['T_m'],w7=settings['w7']),policy)
    selected=result['selected'];output_type=selected['output_type'] if selected else 'STOP';result.update(output_type=output_type,disposition=output_type)
    q,_,ages,_,_=mixture(case,result['B_pred']);B=np.asarray(result['B_pred']);a=B[2];R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
    direction,info=intent_direction((q-B[:2])@R,ages,settings['T_m']);world=R@direction
    progress=float((np.asarray(result['path'])[-1]-B[:2])@world) if selected else None
    residual=max(0.,1.2-progress)/.1 if selected and info['enabled'] else None
    result.update(direction_local=direction.tolist(),direction_world=world.tolist(),direction_info=info,f7_progress_m=progress,f7_residual=residual,f7_weight=settings['w7'])
    return result
