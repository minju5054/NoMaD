"""Stream feasible iterates; never wait for unfinished starts at the cutoff."""
import multiprocessing as mp,time,traceback,queue
from multiprocessing.connection import wait
import numpy as np
from scipy.optimize import minimize
from nomad_phase15b.depth import Snapshot
from .optimized import OptimizedGraph
from .graph import wrap

_late_errors=queue.SimpleQueue()
_field_key=None;_field=None

def constraint_status(g,x):
    h=g.constraint_cache[1][0]
    return dict(active_obstacle=int(np.sum(np.abs(h[:21])<=1e-5)),active_kinematic=int(np.sum(np.abs(h[21:])<=1e-5)),
        violated_obstacle=int(np.sum(h[:21]<-1e-7)),violated_kinematic=int(np.sum(h[21:]<-1e-7)),
        active_dt_bound=int(np.sum((np.abs(x[30:]-.05)<=1e-5)|(np.abs(x[30:]-1.)<=1e-5))))

def worker(payload,channel):
    global _field_key,_field
    index=payload['index'];deadline=payload['deadline_ns'];iteration=0;last_published=None;switches=0
    def send(message):
        try:channel.send(dict(index=index,published_ns=time.monotonic_ns(),**message))
        except (BrokenPipeError,EOFError,OSError):pass
    try:
        key=(payload['snapshot_file'],deadline)
        if key!=_field_key:_field=Snapshot.load(payload['snapshot_file']);_field_key=key
        g=OptimizedGraph(payload['B'],payload['v0'],np.asarray(payload['candidates']),payload['sigma'],_field,payload['weights'],deadline,.03)
        def observe(x):
            nonlocal last_published,switches
            g.observe(x)
            if len(g.trajectory)>1:switches+=g.trajectory[-1]!=g.trajectory[-2]
            message=dict(kind='PROGRESS',iteration=iteration,mixture_switches=switches,**constraint_status(g,x))
            if g.best is not None and g.best[2]!=last_published:
                cost,z,ready=g.best;p,h,dt=g.unpack(z);world=p@g.R.T+g.B[:2];active,_=g.active(p)
                message.update(kind='FEASIBLE',cost=cost,ready_ns=ready,path=world.tolist(),poses=np.c_[world,wrap(h+g.B[2])].tolist(),dt=dt.tolist(),active_candidate=active)
                last_published=ready
            send(message)
        def callback(x):
            nonlocal iteration
            iteration+=1;observe(x)
        x=g.initial(np.asarray(payload['path']));observe(x)
        result=minimize(g.objective,x,jac=True,method='SLSQP',bounds=g.bounds,constraints=[dict(type='ineq',fun=lambda z:g.constraints(z)[0],jac=lambda z:g.constraints(z)[1])],callback=callback,options=dict(maxiter=100,ftol=1e-8))
        iteration=int(result.nit);observe(result.x)
        send(dict(kind='DONE',iteration=iteration,iteration_limit=iteration>=100,solver_success=bool(result.success),message=str(result.message)))
    except TimeoutError:send(dict(kind='DONE',iteration=iteration,iteration_limit=False,solver_success=False,message='DEADLINE'))
    except BaseException as exc:
        send(dict(kind='ERROR',error=repr(exc),traceback=traceback.format_exc()));raise
    finally:channel.close()

def select_messages(messages,deadline_ns):
    eligible=[m for m in messages if m.get('kind')=='FEASIBLE' and m['ready_ns']<=deadline_ns and m['published_ns']<=deadline_ns and m['received_ns']<=deadline_ns]
    return min(eligible,key=lambda m:(m['cost'],m['index'])) if eligible else None

def raise_late_errors():
    while True:
        try:error=_late_errors.get_nowait()
        except queue.Empty:break
        raise RuntimeError('Late worker execution error (path discarded): '+error)

def collect(pool,payloads,deadline_ns,task=worker):
    raise_late_errors()
    receivers={};futures=[];messages=[];latest={};errors=[]
    for payload in payloads:
        receive,send=mp.Pipe(duplex=False);future=pool.submit(task,payload,send);futures.append(future);receivers[receive]=payload['index']
        def cleanup(f,sender=send):
            sender.close()
            if not f.cancelled():
                error=f.exception()
                if error is not None:_late_errors.put(repr(error))
        future.add_done_callback(cleanup)
    try:
        while receivers:
            remaining=(deadline_ns-time.monotonic_ns())/1e9
            if remaining<=0:break
            ready=wait(list(receivers),timeout=remaining)
            for connection in ready:
                try:message=connection.recv()
                except EOFError:
                    connection.close();receivers.pop(connection,None);continue
                received=time.monotonic_ns();message['received_ns']=received
                if received>deadline_ns or message['published_ns']>deadline_ns:continue
                messages.append(message);latest[message['index']]={**latest.get(message['index'],{}),**message}
                if message['kind']=='ERROR':errors.append(message)
                if message['kind'] in ('DONE','ERROR'):
                    connection.close();receivers.pop(connection,None)
        if errors:raise RuntimeError(errors[0]['error']+'\n'+errors[0]['traceback'])
        selected=select_messages(messages,deadline_ns)
        return dict(selected=selected,messages=messages,latest=latest,pending_at_cutoff=len(receivers),cutoff_ns=deadline_ns,returned_ns=time.monotonic_ns())
    finally:
        for connection in receivers:connection.close()
        for future in futures:future.cancel()  # Running calls stop on their unchanged graph deadline.
