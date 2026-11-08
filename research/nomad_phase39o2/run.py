"""Explicit user command only: execute VB/VO/VE, never V0."""
import argparse,fcntl,json,multiprocessing as mp,os,signal,sys,time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from nomad_phase19r.evaluate import clean
from nomad_phase33p.storage import install
from nomad_isaac.common import sha256_file
from .data import ROOT,HERE,OUT,read,runtime_cases
from .prepare import verify
from .pool import initialize,ping,evaluate_job
from .solver import VARIANTS
from .audit import check

def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as f:json.dump(clean(data),f,allow_nan=False);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def status():
    file=OUT/'status.json';s=read(file) if file.exists() else dict(status='NOT_STARTED',V0_solves=0)
    if s.get('pid'):
        try:live=Path(f"/proc/{s['pid']}/stat").read_text().split()[21]==s['process_token']
        except (FileNotFoundError,ProcessLookupError):live=False
        if not live and s['status']=='RUNNING':s=dict(s,status='ABNORMAL_EXIT')
    return s

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(status()));return
    p=verify(references=True);cases=runtime_cases();digest=sha256_file(HERE/'protocol.json')
    if a.dry_run:
        print(json.dumps(dict(jobs=len(cases),new_variants=list(VARIANTS),new_job_variants=len(cases)*3,workers=4,
            V0_reused=len(cases),V0_solves=0,measured_solves=0,estimated_minutes=p['estimated_minutes'])));return
    assert os.environ.get('OPENBLAS_NUM_THREADS')==os.environ.get('OMP_NUM_THREADS')=='1'
    OUT.mkdir(parents=True,exist_ok=True);lock=(OUT/'.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    install();started=time.monotonic();state=dict(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],planned=len(cases)*3,
        completed=len(list((OUT/'jobs').glob('*.json'))),current=None,V0_solves=0)
    def stop(*_):raise KeyboardInterrupt('Offline run interrupted')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);atomic(OUT/'status.json',state);error=None
    try:
        ctx=mp.get_context('spawn');queue=ctx.Queue()
        with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
            warm=[pool.submit(ping) for _ in range(4)];pids=[queue.get(timeout=90) for _ in range(4)]
            for f in warm:f.result()
            assert len(set(pids))==4;atomic(OUT/'environment.json',dict(workers=4,pids=pids,python=sys.version,cpu_affinity=sorted(os.sched_getaffinity(0)),protocol=p))
            budget=False
            for ordinal,case in enumerate(cases):
                order=VARIANTS[ordinal%3:]+VARIANTS[:ordinal%3]
                for variant in order:
                    file=OUT/'jobs'/f"{case['case_id']}_{variant}.json"
                    if file.exists():
                        old=read(file);assert old['protocol_sha256']==digest and old['case_id']==case['case_id'] and old['variant']==variant;continue
                    if time.monotonic()-started>=p['runtime_budget_s']:budget=True;break
                    cache=OUT/'scratch'/f"{case['case_id']}_{variant}.npz";cache.parent.mkdir(parents=True,exist_ok=True)
                    job=dict(case['job'],variant=variant,extra_initializations=[],cache_file=str(cache),dispatch_ns=time.monotonic_ns())
                    state.update(current=f"{case['case_id']} {case['kind']} {variant}",elapsed_s=time.monotonic()-started);atomic(OUT/'status.json',state)
                    numeric=evaluate_job(pool,job);audit=check(case,variant,numeric)
                    atomic(file,dict(case_id=case['case_id'],variant=variant,numeric=numeric,certificate_audit=audit,protocol_sha256=digest))
                    if cache.exists():cache.unlink()
                    state.update(completed=state['completed']+1,elapsed_s=time.monotonic()-started);atomic(OUT/'status.json',state)
                    print(f"[resolve] {state['completed']}/{state['planned']} {state['current']} {numeric['pool_wall_s']:.3f}s",flush=True)
                if budget:break
        state['status']='COMPLETE' if state['completed']==state['planned'] else 'PARTIAL'
    except BaseException as exc:state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));error=exc
    finally:
        state.update(pid=None,current=None,elapsed_s=time.monotonic()-started);atomic(OUT/'status.json',state)
        from .report import generate
        generate();fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
    if error is not None:raise error
if __name__=='__main__':main()
