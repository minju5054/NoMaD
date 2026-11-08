"""User-invoked offline run, resumable per variant; no simulation/inference."""
import argparse,fcntl,json,multiprocessing as mp,os,signal,sys,time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from nomad_phase19r.evaluate import clean
from nomad_phase20d.pool import ping
from nomad_phase33p.storage import install
from .inputs import OUT,HERE,ROOT
from .prepare import verify,read
from .pool import initialize,evaluate_job
from .audit import check,reproduction
from .solver import VARIANTS

def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as stream:json.dump(clean(value),stream,allow_nan=False);stream.flush();os.fsync(stream.fileno())
    os.replace(tmp,path)

def status():
    f=OUT/'status.json';s=read(f) if f.exists() else dict(status='NOT_STARTED')
    pid=s.get('pid')
    if pid:
        try:live=Path(f'/proc/{pid}/stat').read_text().split()[21]==s.get('process_token')
        except (FileNotFoundError,ProcessLookupError):live=False
        if not live and s['status']=='RUNNING':s=dict(s,status='ABNORMAL_EXIT')
    return s

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(status()));return
    p=verify(inputs=True);cases=read(OUT/'preparation/inputs.json')
    if a.dry_run:
        print(json.dumps(dict(jobs=len(cases),variants=list(VARIANTS),job_variant_pairs=len(cases)*4,
            workers=4,estimated_minutes=p['estimated_minutes'],measured_solves=0,simulation_runs=0)));return
    assert os.environ.get('OPENBLAS_NUM_THREADS')=='1' and os.environ.get('OMP_NUM_THREADS')=='1'
    OUT.mkdir(parents=True,exist_ok=True);lock=(OUT/'.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    install();start=time.monotonic();state=dict(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],completed=len(list((OUT/'jobs').glob('*.json'))),planned=len(cases)*4,current=None)
    def interrupt(*_):raise KeyboardInterrupt('Offline run interrupted')
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt);atomic(OUT/'status.json',state)
    error=None
    try:
        ctx=mp.get_context('spawn');queue=ctx.Queue()
        with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
            warm=[pool.submit(ping) for _ in range(4)];pids=[queue.get(timeout=90) for _ in range(4)]
            for f in warm:f.result()
            assert len(set(pids))==4
            atomic(OUT/'environment.json',dict(workers=4,pids=pids,python=sys.version,cpu_affinity=sorted(os.sched_getaffinity(0)),protocol=p))
            stop=False
            for ordinal,case in enumerate(cases):
                order=VARIANTS[ordinal%4:]+VARIANTS[:ordinal%4]
                for variant in order:
                    file=OUT/'jobs'/f"{case['case_id']}_{variant}.json"
                    if file.exists():
                        previous=read(file);assert previous['input_sha256']==p['input_sha256'] and previous['case_id']==case['case_id'] and previous['variant']==variant;continue
                    if time.monotonic()-start>=p['runtime_budget_s']:stop=True;break
                    cache=OUT/'scratch'/f"{case['case_id']}_{variant}.npz";cache.parent.mkdir(parents=True,exist_ok=True)
                    job=dict(case['job'],variant=variant,cache_file=str(cache),dispatch_ns=time.monotonic_ns())
                    state.update(current=f"{case['case_id']} {case['scene']} {case['kind']} {variant}",elapsed_s=time.monotonic()-start);atomic(OUT/'status.json',state)
                    numeric=evaluate_job(pool,job)
                    result=dict(case_id=case['case_id'],variant=variant,numeric=numeric,certificate_audit=check(case,variant,numeric),
                        reproduction=reproduction(case,numeric) if variant=='V0' else None,input_sha256=p['input_sha256'])
                    atomic(file,result)
                    if cache.exists():cache.unlink()
                    state.update(completed=state['completed']+1,elapsed_s=time.monotonic()-start);atomic(OUT/'status.json',state)
                    print(f"[resolve] {state['completed']}/{state['planned']} {state['current']} {numeric['pool_wall_s']:.3f}s",flush=True)
                if stop:break
        state['status']='PARTIAL' if state['completed']<state['planned'] else 'COMPLETE'
    except BaseException as exc:state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));error=exc
    finally:
        state.update(pid=None,current=None,elapsed_s=time.monotonic()-start);atomic(OUT/'status.json',state)
        from .report import generate
        generate();fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
    if error is not None:raise error

if __name__=='__main__':main()
