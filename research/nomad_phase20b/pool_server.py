"""CPU-only persistent four-process pool, isolated from Isaac/Kit process startup."""
import json,os,sys,time,signal
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from nomad_phase15b.depth import Snapshot
from nomad_phase20.repair import solve_sample
from nomad_phase19r.evaluate import clean,select_repair

_field=None
_file=None

def initialize(ready):ready.put(os.getpid())
def ping():return os.getpid()

def solve_one(item):
    global _field,_file
    index,native,B,file=item;started=time.monotonic_ns();load_start=time.perf_counter()
    if _file!=file:_field=Snapshot.load(file);_file=file
    load_s=time.perf_counter()-load_start
    result=solve_sample(np.array(native),B,_field)
    return dict(sample=index,pid=os.getpid(),sample_start_ns=started,sample_end_ns=time.monotonic_ns(),
                snapshot_load_s=load_s,**clean(result))

def parallel_solve(pool,job):
    start=time.monotonic_ns()
    items=[(i,p,job['B'],job['snapshot_file']) for i,p in enumerate(job['samples_world'])]
    results=list(pool.map(solve_one,items));assert [r['sample'] for r in results]==list(range(8))
    end=time.monotonic_ns()
    return dict(kind='RESULT',job_id=job['job_id'],start_ns=start,end_ns=end,selected_sample=select_repair(results),results=results,
        pool_wall_s=(end-start)/1e9,dispatch_to_complete_s=(end-job['dispatch_ns'])/1e9,
        sample_solve_s=[r['attempt_wall_s'] for r in results],sample_total_s=[(r['sample_end_ns']-r['sample_start_ns'])/1e9 for r in results],
        sample_solver_started=[r['solver_started'] for r in results],sample_dispositions=[r['disposition'] for r in results],
        optimizer_wall_s=[r.get('solver_wall_s') for r in results])

def main():
    context=mp.get_context('spawn');ready=context.Queue()
    def interrupted(*_):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupted)
    with ProcessPoolExecutor(max_workers=4,mp_context=context,initializer=initialize,initargs=(ready,)) as pool:
        tasks=[pool.submit(ping) for _ in range(4)]
        pids=[ready.get(timeout=90) for _ in range(4)];assert len(set(pids))==4
        for f in tasks:f.result()
        print(json.dumps(dict(kind='READY',workers=4,pids=pids,python=sys.executable)),flush=True)
        for line in sys.stdin:
            job=json.loads(line)
            if job is None:break
            try:result=parallel_solve(pool,job)
            except Exception as exc:result=dict(kind='RESULT',job_id=job['job_id'],start_ns=time.monotonic_ns(),end_ns=time.monotonic_ns(),
                selected_sample=None,results=[],error=repr(exc))
            print(json.dumps(clean(result),allow_nan=False),flush=True)

if __name__=='__main__':main()
