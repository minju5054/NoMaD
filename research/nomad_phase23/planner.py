"""Ten non-search initializations under one0.25s wall deadline, four workers."""
import time
import numpy as np
from nomad_phase15b.depth import Snapshot
from .graph import prepare_candidates,side_initializations,solve_start

_key=None;_field=None
def worker(args):
    global _key,_field
    index,case,candidates,sigma,path,weights,deadline,nh=args
    if case['snapshot_file']!=_key:_field=Snapshot.load(case['snapshot_file']);_key=case['snapshot_file']
    r=solve_start(case['B'],case['previous_vw'][0],np.asarray(candidates),sigma,_field,weights,np.asarray(path),deadline,nh)
    return dict(index=index,**r)

def plan(pool,case,weights,policy):
    # SDF input is already available at the hypothetical planning invocation.
    field=Snapshot.load(case['snapshot_file']);started=time.monotonic_ns();deadline=started+250_000_000
    candidates,sigma,flags=prepare_candidates(case['samples_world'],case['B'],case.get('old_path'),policy['short_policy'])
    lateral,component=side_initializations(candidates,case['B'],field);starts=list(candidates)+lateral
    args=[(i,{k:case[k] for k in ('snapshot_file','B','previous_vw')},candidates,sigma,p,weights,deadline,policy['kinematic_sigma']) for i,p in enumerate(starts)]
    results=list(pool.map(worker,args));ended=time.monotonic_ns()
    feasible=[r for r in results if r['accepted'] and r['ready_ns']<=deadline]
    selected=min(feasible,key=lambda r:(r['cost'],r['index'])) if feasible else None
    return dict(accepted=selected is not None,disposition='FEASIBLE' if selected else 'NO_FEASIBLE_BEFORE_DEADLINE',selected=selected,
        path=selected['path'] if selected else None,poses=selected['poses'] if selected else None,dt=selected['dt'] if selected else None,
        sigma_policy_m=sigma,candidate_flags=flags,component=component,initialization_count=len(starts),attempts=results,
        compute_s=(ended-started)/1e9,deadline_s=.25,deadline_overrun=ended>deadline,active_candidate=selected.get('active_candidate') if selected else None,
        active_switches=sum(r['active_switches'] for r in results),iterate_count=sum(r['iterate_count'] for r in results))
