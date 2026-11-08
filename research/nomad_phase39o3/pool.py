"""Only137 R3 jobs x2 new map variants enter the four-worker pool."""
import os,time
from nomad_phase33p.storage import install
from nomad_phase20d.recent import RecentSnapshot,build_cache
from nomad_phase39o2.geometry import obstacle_initializations
from nomad_phase20c.detour import select_detour
from nomad_phase19r.evaluate import clean
from .maps import VARIANTS,policy_map
from .cache import save_bundle,load_bundle
from .solver import solve

_key=None;_bundle=None
def initialize(queue):install();queue.put(os.getpid())
def ping():return os.getpid()
def solve_one(args):
    global _key,_bundle
    index,job,file=args;assert job['variant'] in VARIANTS and job['kind']=='R3'
    started=time.monotonic_ns();key=(file,job['variant'])
    if key!=_key:_bundle=load_bundle(file);_key=key
    result=solve(index,job,*_bundle)
    return clean(dict(index=index,pid=os.getpid(),start_ns=started,end_ns=time.monotonic_ns(),**result))

def evaluate_job(pool,job):
    assert job['variant'] in VARIANTS and job['kind']=='R3','No cached baseline/R2 re-solve permitted'
    start=time.monotonic_ns();base=RecentSnapshot.load(job['snapshot_file']);planning,info=policy_map(base,job['B'],job['variant'])
    cost,cost_info=(planning,dict(reused_policy=True)) if job['soft_policy_map'] else build_cache(base,job['evaluation_tick'])
    gen_start=time.perf_counter();extra,geometry=obstacle_initializations(planning,job['B'],job['u_ref']);gen_s=time.perf_counter()-gen_start
    save_bundle(base,cost,planning,job['cache_file'],job['variant']);job=dict(job,extra_initializations=extra)
    results=list(pool.map(solve_one,[(i,job,job['cache_file']) for i in range(7+len(extra))]))
    selected=select_detour(results);end=time.monotonic_ns()
    return dict(job_id=job['job_id'],kind='R3',variant=job['variant'],results=results,selected_sample=selected,
        selected_initialization_source=results[selected]['initialization_source'] if selected is not None else None,
        pool_wall_s=(end-start)/1e9,start_ns=start,end_ns=end,planning_map=info,cost_map=cost_info,geometry=geometry,
        geometry_wall_s=gen_s,extra_initializations=extra,initialization_count=len(results))
