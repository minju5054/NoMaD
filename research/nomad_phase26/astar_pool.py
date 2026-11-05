"""C0 broker and R2 SLSQP; only R3 uses frozen Phase21 A* (4.0,0)."""
import json,sys,time,multiprocessing as mp,os
from concurrent.futures import ProcessPoolExecutor
from nomad_phase20d.pool import evaluate_job as r2_job,initialize,ping
from nomad_phase21.pool import one
from nomad_phase20d.recent import RecentSnapshot,build_cache,save_cache
from nomad_phase19r.evaluate import clean

def evaluate(pool,job):
    if job['kind']=='R2':return r2_job(pool,job)
    start=time.monotonic_ns();base=RecentSnapshot.load(job['snapshot_file']);strict,cache=build_cache(base,job['evaluation_tick']);save_cache(base,strict,job['cache_file'])
    r=pool.submit(one,(0,job,job['cache_file'],4.,0)).result();end=time.monotonic_ns()
    return dict(job_id=job['job_id'],kind='R3',start_ns=start,end_ns=end,results=[r],selected_sample=0 if r['accepted'] else None,
                selected_initialization=0 if r['accepted'] else None,pool_wall_s=(end-start)/1e9,dispatch_to_complete_s=(end-job['dispatch_ns'])/1e9,
                sample_solve_s=[r['total_attempt_s']],cache=cache,planner='ASTAR_R3_ONLY')

def main():
    ctx=mp.get_context('spawn');q=ctx.Queue()
    with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        jobs=[pool.submit(ping) for _ in range(4)];pids=[q.get(timeout=90) for _ in range(4)]
        for f in jobs:f.result()
        print(json.dumps(dict(kind='READY',workers=4,pids=pids,python=sys.executable)),flush=True)
        for line in sys.stdin:
            job=json.loads(line)
            if job is None:break
            try:r=evaluate(pool,job)
            except BaseException as exc:r=dict(job_id=job['job_id'],kind=job['kind'],start_ns=time.monotonic_ns(),end_ns=time.monotonic_ns(),results=[],selected_sample=None,error=repr(exc))
            print(json.dumps(clean(r),allow_nan=False),flush=True)
if __name__=='__main__':main()
