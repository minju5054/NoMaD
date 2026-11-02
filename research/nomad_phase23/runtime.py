"""Execution-only watchdogs and failure journaling; no planner/score changes."""
import contextlib,json,os,signal,sys,time,traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

SOLVE_WATCHDOG_S=5.
BASELINE_WATCHDOG_S=10.
ROLLOUT_WATCHDOG_S=30.
ORACLE_WATCHDOG_S=60.
EXACT_WATCHDOG_S=10.
ROTATION_TOLERANCE_RAD=.001  # Existing tolerance, now named and tested.
ROTATION_TIME_PAD_S=2/9

class ExecutionTimeout(RuntimeError):pass
class ExecutionGuardError(RuntimeError):pass
class ExecutionSignal(BaseException):
    def __init__(self,signum):self.signum=signum;super().__init__(signal.Signals(signum).name)

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def process_token(pid):
    try:
        text=Path(f'/proc/{pid}/stat').read_text();rest=text[text.rfind(')')+2:].split()
        return None if rest[0]=='Z' else rest[19]
    except (OSError,IndexError):return None

def reconcile(path):
    path=Path(path);state=json.loads(path.read_text()) if path.exists() else {}
    pid=state.get('pid');token=process_token(pid) if pid else None
    alive=bool(token and (not state.get('process_token') or token==state['process_token']))
    if pid and not alive and state.get('status') not in ('COMPLETE','FAILED','BUDGET_STOP'):
        state.update(status='FAILED',previous_stage=state.get('stage'),stage='FAILED',pid=None,failed_pid=pid,detected_ns=time.time_ns(),
            error=dict(type='UnobservedProcessExit',message='Process disappeared without a terminal state; SIGKILL/OOM cannot be distinguished without kernel evidence'))
        atomic(path,state)
    return dict(state,process_alive=alive)

class Journal:
    def __init__(self,out):self.out=Path(out);self.current={};self.old_handlers={};self.exit_recorded=False
    def event(self,event,**kw):
        row=dict(event=event,time_ns=time.time_ns(),**kw)
        with (self.out/'progress.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    def update(self,stage,case=None,combination=None,**kw):
        if case is not None:self.current['case']=case
        if combination is not None:self.current['combination']=combination
        self.current.update(stage=stage,updated_ns=time.time_ns(),**kw)
        atomic(self.out/'state.json',self.current);self.event('STATE',**self.current)
    def __enter__(self):
        self.out.mkdir(parents=True,exist_ok=True)
        old=reconcile(self.out/'state.json')
        if old:self.event('RESUME',previous=old)
        self.current=dict(pid=os.getpid(),process_token=process_token(os.getpid()),status='RUNNING',started_ns=time.time_ns())
        for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):
            self.old_handlers[signum]=signal.getsignal(signum)
            signal.signal(signum,lambda n,frame:(_ for _ in ()).throw(ExecutionSignal(n)))
        self.update('START');return self
    def __exit__(self,kind,value,tb):
        try:
            if value is not None:
                error=dict(type=type(value).__name__,message=str(value),traceback=''.join(traceback.format_exception(kind,value,tb)),signal=getattr(value,'signum',None))
                file=self.out/'errors'/f'{time.time_ns()}_{os.getpid()}.json';atomic(file,dict(context=self.current,error=error))
                self.current.update(status='FAILED',failed_stage=self.current.get('stage'),stage='FAILED',error=error,error_file=str(file))
                self.event('FAILED',context=self.current)
            elif self.current.get('stage','').startswith('BUDGET_STOP'):self.current['status']='BUDGET_STOP'
            elif self.current.get('stage')=='COMPLETE':self.current['status']='COMPLETE'
            else:self.current.update(status='FAILED',error=dict(type='IncompleteExit',message='Returned without COMPLETE or budget checkpoint'))
        finally:
            self.current.update(pid=None,ended_ns=time.time_ns());atomic(self.out/'state.json',self.current)
            for signum,handler in self.old_handlers.items():signal.signal(signum,handler)
        return False

@contextlib.contextmanager
def wall_limit(seconds,label):
    old=signal.getsignal(signal.SIGALRM);old_timer=signal.getitimer(signal.ITIMER_REAL);start=time.monotonic()
    def expired(signum,frame):raise ExecutionTimeout(f'{label} exceeded {seconds:g}s wall-clock watchdog')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,max(.000001,seconds))
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        if old_timer[0]>0:signal.setitimer(signal.ITIMER_REAL,max(.000001,old_timer[0]-(time.monotonic()-start)),old_timer[1])

def stage(label,seconds,fn,journal=None,timing=None):
    if journal:journal.update(label)
    start=time.perf_counter()
    try:
        with wall_limit(seconds,label):return fn()
    finally:
        elapsed=time.perf_counter()-start
        if timing is not None:timing[label]=elapsed
        if journal:journal.event('STAGE_END',stage=label,case=journal.current.get('case'),combination=journal.current.get('combination'),wall_s=elapsed)

def abort_pool(pool):
    processes=list((getattr(pool,'_processes',None) or {}).values())
    for process in processes:
        if process.is_alive():process.terminate()
    for process in processes:process.join(timeout=.5)
    for process in processes:
        if process.is_alive():process.kill();process.join(timeout=.5)
    pool.shutdown(wait=False,cancel_futures=True)

@contextlib.contextmanager
def managed_pool(**kwargs):
    pool=ProcessPoolExecutor(**kwargs)
    try:
        yield pool
    except BaseException:
        abort_pool(pool);raise
    else:
        try:
            with wall_limit(10.,'POOL_SHUTDOWN'):pool.shutdown(wait=True,cancel_futures=True)
        except BaseException:abort_pool(pool);raise

class SerialPool:
    """Diagnostic only. Never used for the registered four-process run."""
    def map(self,fn,args):return map(fn,args)
