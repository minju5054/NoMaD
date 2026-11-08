"""Same four-worker job envelope; V0 has no dispatch route."""
import os,time
from nomad_phase33p.storage import install
from nomad_phase20d.recent import RecentSnapshot,build_cache,save_cache,load_cache
from nomad_phase19r.evaluate import clean,select_repair
from nomad_phase20c.detour import select_detour
from .solver import solve,VARIANTS
from .geometry import obstacle_initializations

_key=None;_base=None;_strict=None
def initialize(queue):install();queue.put(os.getpid())
def ping():return os.getpid()

def solve_one(args):
    global _key,_base,_strict
    kind,index,job,file=args;assert job['variant'] in VARIANTS,'V0 cannot be dispatched'
    started=time.monotonic_ns();key=(kind,file,job['variant'])
    if key!=_key:
        if kind=='R3':_base,_strict=load_cache(file)
        else:_base=RecentSnapshot.load(file);_strict=None
        _key=key
    result=solve(kind,index,job,_base,_strict)
    return clean(dict(index=index,pid=os.getpid(),start_ns=started,end_ns=time.monotonic_ns(),**result))

def evaluate_job(pool,job):
    assert job['variant'] in VARIANTS,'V0 cannot be solved'
    start=time.monotonic_ns();kind=job['kind'];cache=None;geometry=None;extra=[];gen_s=0.
    if kind=='R3':
        base=RecentSnapshot.load(job['snapshot_file']);strict,cache=build_cache(base,job['evaluation_tick'])
        if job['variant'] in ('VO','VE'):
            before=time.perf_counter();extra,geometry=obstacle_initializations(strict,job['B'],job['u_ref']);gen_s=time.perf_counter()-before
        file=job['cache_file'];save_cache(base,strict,file)
    else:file=job['snapshot_file']
    job=dict(job,extra_initializations=extra);n=7+len(extra) if kind=='R3' else 8
    results=list(pool.map(solve_one,[(kind,i,job,file) for i in range(n)]))
    selected=select_detour(results) if kind=='R3' else select_repair(results);end=time.monotonic_ns()
    return dict(job_id=job['job_id'],kind=kind,variant=job['variant'],results=results,selected_sample=selected,
        selected_initialization_source=results[selected]['initialization_source'] if selected is not None else None,
        pool_wall_s=(end-start)/1e9,start_ns=start,end_ns=end,cache=cache,geometry=geometry,geometry_wall_s=gen_s,
        extra_initializations=extra,initialization_count=n)
