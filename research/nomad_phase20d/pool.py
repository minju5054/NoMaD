"""R2 and cached-R3 tasks share one persistent four-process pool."""
import json,os,sys,time,signal,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from nomad_phase19r.evaluate import clean,select_repair
from nomad_phase20.repair import solve_sample
from nomad_phase20c.detour import ANGLES,select_detour
from nomad_phase20c.detour_known import solve_initialization
from nomad_phase15.evaluate import sample_path
from .recent import RecentSnapshot,build_cache,save_cache,load_cache

_key=None;_base=None;_strict=None
def initialize(q):q.put(os.getpid())
def ping():return os.getpid()

def solve_one(args):
    global _key,_base,_strict
    kind,index,job,file=args;start=time.monotonic_ns()
    if (kind,file)!=_key:
        if kind=='R3':_base,_strict=load_cache(file)
        else:_base=RecentSnapshot.load(file);_strict=None
        _key=(kind,file)
    r=solve_initialization(job['B'],job['u_ref'],_base,_strict,ANGLES[index]) if kind=='R3' else solve_sample(job['samples_world'][index],job['B'],_base)
    return clean(dict(index=index,pid=os.getpid(),start_ns=start,end_ns=time.monotonic_ns(),**r))

def evaluate_job(pool,job):
    started=time.monotonic_ns();kind=job['kind'];cache=None
    if kind=='R3':
        base=RecentSnapshot.load(job['snapshot_file']);strict,cache=build_cache(base,job['evaluation_tick'])
        file=job['cache_file'];save_cache(base,strict,file)
    else:file=job['snapshot_file']
    n=7 if kind=='R3' else 8
    result=list(pool.map(solve_one,[(kind,i,job,file) for i in range(n)]))
    selected=select_detour(result) if kind=='R3' else select_repair(result);end=time.monotonic_ns()
    return dict(job_id=job['job_id'],kind=kind,start_ns=started,end_ns=end,results=result,selected_sample=selected,
        selected_initialization=selected if kind=='R3' else None,pool_wall_s=(end-started)/1e9,dispatch_to_complete_s=(end-job['dispatch_ns'])/1e9,
        sample_solve_s=[r.get('total_attempt_s',r.get('attempt_wall_s')) for r in result],cache=cache)

def main():
    ctx=mp.get_context('spawn');q=ctx.Queue()
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
    with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        ff=[pool.submit(ping) for _ in range(4)];pids=[q.get(timeout=90) for _ in range(4)]
        for f in ff:f.result()
        print(json.dumps(dict(kind='READY',workers=4,pids=pids,python=sys.executable)),flush=True)
        for line in sys.stdin:
            job=json.loads(line)
            if job is None:break
            try:r=evaluate_job(pool,job)
            except BaseException as exc:r=dict(job_id=job['job_id'],kind=job['kind'],start_ns=time.monotonic_ns(),end_ns=time.monotonic_ns(),results=[],selected_sample=None,error=repr(exc))
            print(json.dumps(clean(r),allow_nan=False),flush=True)

if __name__=='__main__':main()
