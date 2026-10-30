"""Same broker/deadline envelope as20F; substitute A* for each stage's solver."""
import json,os,sys,time,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from nomad_phase19r.evaluate import clean,select_repair
from nomad_phase20d.recent import RecentSnapshot,build_cache,save_cache,load_cache
from .astar import solve,solve_repair
from .config import protocol

_key=None;_base=None;_strict=None
def initialize(q):q.put(os.getpid())
def ping():return os.getpid()
def one(args):
    global _key,_base,_strict
    index,job,file,weight,iterations=args;kind=job['kind']
    if (kind,file)!=_key:
        if kind=='R3':_base,_strict=load_cache(file)
        else:_base=RecentSnapshot.load(file);_strict=_base
        _key=(kind,file)
    deadline=job['dispatch_ns']+1_000_000_000
    r=solve(job['B'],job['u_ref'],_base,_strict,weight,iterations,11,deadline) if kind=='R3' else solve_repair(job['samples_world'][index],job['B'],_base,weight,iterations,deadline)
    return clean(dict(index=index,pid=os.getpid(),**r))
def evaluate_job(pool,job,weight,iterations):
    start=time.monotonic_ns();cache=None
    if job['kind']=='R3':
        base=RecentSnapshot.load(job['snapshot_file']);strict,cache=build_cache(base,job['evaluation_tick']);file=job['cache_file'];save_cache(base,strict,file)
    else:file=job['snapshot_file']
    n=1 if job['kind']=='R3' else 8;results=list(pool.map(one,[(i,job,file,weight,iterations) for i in range(n)]))
    selected=(0 if results[0]['accepted'] else None) if job['kind']=='R3' else select_repair(results)
    end=time.monotonic_ns()
    return dict(job_id=job['job_id'],kind=job['kind'],start_ns=start,end_ns=end,results=results,selected_sample=selected,
        pool_wall_s=(end-start)/1e9,dispatch_to_complete_s=(end-job['dispatch_ns'])/1e9,sample_solve_s=[r['total_attempt_s'] for r in results],cache=cache,planner='ASTAR')
def main():
    p=protocol();chosen=p['astar']['selected'];assert chosen
    ctx=mp.get_context('spawn');q=ctx.Queue()
    with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        ff=[pool.submit(ping) for _ in range(4)];pids=[q.get(timeout=90) for _ in range(4)]
        for f in ff:f.result()
        print(json.dumps(dict(kind='READY',workers=4,pids=pids,python=sys.executable)),flush=True)
        for line in sys.stdin:
            job=json.loads(line)
            if job is None:break
            try:r=evaluate_job(pool,job,chosen['lambda'],chosen['smoothing_iterations'])
            except BaseException as e:r=dict(kind=job['kind'],job_id=job['job_id'],start_ns=time.monotonic_ns(),end_ns=time.monotonic_ns(),selected_sample=None,results=[],error=repr(e))
            print(json.dumps(clean(r),allow_nan=False),flush=True)
if __name__=='__main__':main()
