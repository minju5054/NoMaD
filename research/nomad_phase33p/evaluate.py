"""One paired solver replay per fixed event; no navigation, tuning or retries."""
import argparse,hashlib,json,os,time,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import FunctionType
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase19r.evaluate import clean
from nomad_phase32o.evaluate import save,csvout
from .config import OUT,verify
from .storage import install

_key=None;_base=None;_strict=None

def bind(fn,**updates):return FunctionType(fn.__code__,dict(fn.__globals__,**updates),fn.__name__,fn.__defaults__,fn.__closure__)

def init_normal():
    os.sched_setaffinity(0,{7});install()

def init_pool(ready):
    cpus=set(os.sched_getaffinity(0))-{7}
    if cpus:os.sched_setaffinity(0,cpus)
    install();ready.put(os.getpid())

def ping():return dict(pid=os.getpid(),cores=sorted(os.sched_getaffinity(0)))

def solve_normal(case,variant):
    from nomad_phase20d.recent import RecentSnapshot
    from nomad_phase17.graph import ClearanceGraph
    from .graph import NormalGraph
    field=RecentSnapshot.load(case['snapshot_file']);job=case['job'];cls=ClearanceGraph if variant=='G18' else NormalGraph
    start=time.perf_counter()
    try:
        graph=cls(job['path'],job['boundary'],job['previous_vw'],field,job.get('previous_xy'));poses,details=graph.solve()
        result=dict(solve_success=bool(details['feasible']),path=poses[:,:2].tolist(),details=details,
                    reason='ACCEPTED' if details['feasible'] else 'NONCONVERGED' if not details['success'] else 'CONSTRAINT_FAILED' if not details['constraints_satisfied'] else 'CERTIFICATE_FAILED')
    except ValueError as exc:result=dict(solve_success=False,path=None,reason='INITIALIZATION_OR_SDF_REJECTED',error=repr(exc))
    result.update(compute_s=time.perf_counter()-start,worker_pid=os.getpid(),cores=sorted(os.sched_getaffinity(0)))
    return clean(result)

def solve_one(args):
    global _key,_base,_strict
    from nomad_phase20d.recent import RecentSnapshot,load_cache
    from nomad_phase20.repair import solve_sample
    from nomad_phase20c.detour_known import solve_initialization
    from nomad_phase20c.detour import ANGLES
    from .graph import RepairGraph,DetourGraph
    kind,index,job,file=args;start=time.monotonic_ns()
    if (kind,file)!=_key:
        if kind=='R3':_base,_strict=load_cache(file)
        else:_base=RecentSnapshot.load(file);_strict=None
        _key=(kind,file)
    if kind=='R3':
        solve=solve_initialization if job['phase33_variant']=='G18' else bind(solve_initialization,KnownDetourGraph=DetourGraph)
        result=solve(job['B'],job['u_ref'],_base,_strict,ANGLES[index])
    else:
        solve=solve_sample if job['phase33_variant']=='G18' else bind(solve_sample,RepairGraphR2=RepairGraph)
        result=solve(job['samples_world'][index],job['B'],_base)
    return clean(dict(index=index,pid=os.getpid(),start_ns=start,end_ns=time.monotonic_ns(),**result))

def solve_pool(pool,case,variant):
    from nomad_phase20d.pool import evaluate_job
    # Reuse the frozen complete-job body and original selection rules. Only the
    # selected numerical class changes in each worker. No source input is written.
    function=bind(evaluate_job,solve_one=solve_one)
    cache=OUT/'temporary_cache'/f"{case['case_id']}_{variant}.npz";cache.parent.mkdir(exist_ok=True)
    job=dict(case['job'],phase33_variant=variant,cache_file=str(cache),dispatch_ns=time.monotonic_ns())
    started=time.perf_counter()
    try:details=function(pool,job)
    finally:cache.unlink(missing_ok=True)
    elapsed=time.perf_counter()-started;selected=details['selected_sample'];success=selected is not None
    path=details['results'][selected]['path'] if success else None
    return clean(dict(solve_success=success,path=path,compute_s=details['pool_wall_s'],offline_with_cleanup_s=elapsed,details=details,reason='ACCEPTED' if success else 'NO_ACCEPTED_INITIALIZATION'))

def input_manifest(cases):
    converted={r['path']:r for r in (json.loads(s) for s in (OUT/'storage/roots/phase32_01/manifest.jsonl').read_text().splitlines())}
    files={ROOT/'research/results/phase32/runs.json'}
    for case in cases:
        files.update((Path(case['snapshot_file']),Path(case['ec_context']['snapshot']['file'])))
        root=Path(case['output']);files.update(root/n for n in ('repair.jsonl','phase29_paths.jsonl','detour.jsonl','exec_cert.jsonl'))
        if case['state']!='NORMAL':files.add(root/'repair_jobs'/f"transport_{case['job']['job_id']:04d}.json")
    rows=[]
    for file in sorted(files):
        digest=sha256_file(file);r=converted.get(str(file));rows.append(dict(file=str(file),sha256=digest,original_sha256=r['original_sha256'] if r else digest,arrays_sha256=r.get('arrays_sha256') if r else None))
    save(OUT/'input_manifest.json',rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--status',action='store_true');args=ap.parse_args()
    if args.status:
        print((OUT/'status.json').read_text() if (OUT/'status.json').exists() else 'NOT_STARTED');return
    if not args.run:ap.error('--run required')
    protocol=verify();cases=json.loads((OUT/'cohort.json').read_text());assert len(cases)==247
    assert json.loads((OUT/'storage/state.json').read_text())['status']=='COMPLETE'
    if (OUT/'offline_rows.json').exists():raise FileExistsError('Finished results preserved; no repeated evaluation')
    install()
    for item in json.loads((OUT/'input_manifest.json').read_text()):assert sha256_file(item['file'])==item['sha256'],item['file']
    from nomad_phase20d.recent import RecentSnapshot
    from nomad_phase32o.exec_cert import certify
    results=[];started=time.monotonic();ctx=mp.get_context('spawn');ready=ctx.Queue()
    with ProcessPoolExecutor(max_workers=1,mp_context=ctx,initializer=init_normal) as normal,ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=init_pool,initargs=(ready,)) as pool:
        normal_info=normal.submit(ping).result();warm=[pool.submit(ping) for _ in range(4)];pool_pids=[ready.get(timeout=90) for _ in range(4)];assert len(set(pool_pids))==4
        pool_info=[f.result() for f in warm]
        save(OUT/'environment.json',dict(python=os.sys.executable,numpy=np.__version__,normal=normal_info,pool=pool_info,pool_ready_pids=pool_pids,load_average=os.getloadavg(),protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json'))))
        try:
            for i,case in enumerate(cases):
                cache=OUT/'cases'/f"{case['case_id']}.json"
                if cache.exists():
                    existing=json.loads(cache.read_text());results.extend(existing['rows']);continue
                ec=case['ec_context'];field=RecentSnapshot.load(ec['snapshot']['file']);cap=case['installation'].get('speed_cap_m_s')
                installed=certify(ec['pose'],ec['actual_vw'],case['application']['path_world'],field,speed_cap=cap)
                per_case=[];paths={};variants=('G18','G18X') if i%2==0 else ('G18X','G18')
                for variant in variants:
                    result=normal.submit(solve_normal,case,variant).result() if case['state']=='NORMAL' else solve_pool(pool,case,variant)
                    check=certify(ec['pose'],ec['actual_vw'],result['path'],field,speed_cap=cap) if result['solve_success'] else dict(passed=False,reason='NO_FEASIBLE_CERTIFIED_SOLUTION')
                    row=dict(case_id=case['case_id'],event_key=case['event_key'],state=case['state'],scene=case['scene'],index=case['index'],variant=variant,
                             input_source=case['input_source'],source_job_id=case['job']['job_id'],solve_success=result['solve_success'],compute_s=result['compute_s'],
                             ec_pass=bool(check['passed']),solve_and_ec=bool(result['solve_success'] and check['passed']),ec_reason=check['reason'],ec_clearance_m=check.get('clearance_m'),
                             failure_reason=result['reason'],initialization_error=result.get('error'),installed_ec_pass=bool(installed['passed']),installed_ec_clearance_m=installed.get('clearance_m'),
                             speed_cap_m_s=cap,solve_snapshot=case['snapshot_file'],ec_snapshot=ec['snapshot']['file'])
                    per_case.append(row);paths[variant]=dict(result=result,ec=check)
                save(cache,dict(case_id=case['case_id'],rows=per_case,numerical=paths,installed_ec=installed));results.extend(per_case)
                save(OUT/'status.json',dict(status='RUNNING',done=i+1,total=247,last=case['case_id'],elapsed_s=time.monotonic()-started))
                if (i+1)%10==0:print('[offline]',i+1,'/247',flush=True)
        except BaseException as exc:
            save(OUT/'status.json',dict(status='FAILED',error=repr(exc),done=len(results)//2,elapsed_s=time.monotonic()-started));raise
    save(OUT/'offline_rows.json',results);csvout(OUT/'offline.csv',results);save(OUT/'status.json',dict(status='COMPLETE',done=247,total=247,elapsed_s=time.monotonic()-started,navigation_started=0))
    print('Offline complete; navigation started 0',flush=True)

if __name__=='__main__':main()
