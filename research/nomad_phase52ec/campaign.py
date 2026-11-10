"""User-launched, resumable graph-only analysis; never starts Isaac/NoMaD."""
import argparse,fcntl,json,multiprocessing as mp,os,signal,subprocess,time
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path
from .evaluate import OUT,freeze,graph_worker_init,solve_one
from .report import graph_summary,main as generate_reports
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase32o.evaluate import save,csvout

HEARTBEAT_S=60.

def inputs():
    path=OUT/'graph_inputs.json';registered=json.loads((OUT/'protocol.json').read_text())['campaign_registration']
    assert sha256_file(path)==registered['graph_inputs_sha256'],'Registered graph inputs changed'
    jobs=json.loads(path.read_text())
    assert len({j['event_id'] for j in jobs})==len(jobs)
    return jobs

def cache(jobs):
    results=[];pending=[]
    for job in jobs:
        if not job['graph_eligible']:continue
        file=OUT/'graph'/f"{job['event_id']}.json"
        if not file.exists():pending.append(job);continue
        try:r=json.loads(file.read_text())
        except (ValueError,OSError) as e:raise RuntimeError(f'Invalid existing cache preserved: {file}') from e
        assert r['event_id']==job['event_id'] and r['uid']==job['uid'] and r['bank_id']==job['bank_id']
        assert r['source_check_ids']==job['check_ids'] and len(r['results'])==8
        candidates=[i for i,c in enumerate(r['results']) if c['accepted']]
        expected=min(candidates,key=lambda i:(r['results'][i]['objective'],i)) if candidates else None
        assert r['selected']==expected and r['found']==(expected is not None)
        for c in r['results']:
            if c['accepted']:
                assert c['solver_success'] and c['independent_ec_pass'] and c['independent_clearance_m']>=.025
                assert c['verification']['terminal_vw']==[0.,0.] and c['verification']['stopped']
        results.append(r)
    return results,pending

def intermediate(jobs,results):
    stats=graph_summary(jobs,results,('phase','scene'));directory=OUT/'intermediate';directory.mkdir(exist_ok=True)
    for r in stats:
        r=dict(r,status='COMPLETE' if r['completed']==r['eligible'] else 'PARTIAL')
        save(directory/f"{r['phase']}_{r['scene']}.json",r)
    csvout(OUT/'intermediate_scene_summary.csv',stats)

def process_token(pid):
    try:return Path(f'/proc/{pid}/stat').read_text().split()[21]
    except (FileNotFoundError,ProcessLookupError):return None

def status(jobs,results,pending):
    p=OUT/'campaign_status.json';saved=json.loads(p.read_text()) if p.exists() else {}
    label=saved.get('status','CACHE_COMPLETE' if not pending else 'NOT_STARTED')
    live=bool(saved.get('pid') and process_token(saved['pid'])==saved.get('process_token'))
    if label=='RUNNING' and not live:label='ABNORMAL_EXIT'
    return dict(status=label,full_speed_unique=len(jobs),eligible=sum(j['graph_eligible'] for j in jobs),cached=len(results),remaining=len(pending),
        pid=saved.get('pid') if live else None,simulations_started=0)

def publish():
    paths=['docs/PHASE52P_EXEC_GRAPH.md','research/results/phase52ec']
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report execution-constrained graph analysis from cached and resumed inputs','--',*paths],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def run(jobs,results,pending,workers=4):
    started=time.monotonic();cached=len(results);stop=[False];state=dict(status='RUNNING',pid=os.getpid(),process_token=process_token(os.getpid()),
        eligible=sum(j['graph_eligible'] for j in jobs),cached_at_start=cached,computed_this_invocation=0,completed=len(results),simulations_started=0)
    def request_stop(*_):stop[0]=True;print('[stop] finish in-flight inputs;no further submissions',flush=True)
    signal.signal(signal.SIGTERM,request_stop);signal.signal(signal.SIGINT,request_stop)
    def progress():
        state.update(completed=len(results),computed_this_invocation=len(results)-cached,elapsed_s=time.monotonic()-started)
        save(OUT/'campaign_status.json',state)
        print(f"[progress] {len(results)}/{state['eligible']} cached={cached} new={len(results)-cached} elapsed={state['elapsed_s']:.1f}s",flush=True)
    progress();intermediate(jobs,results);next_heartbeat=time.monotonic()+HEARTBEAT_S
    try:
        if pending:
            ctx=mp.get_context('spawn');iterator=iter(pending)
            with ProcessPoolExecutor(max_workers=workers,mp_context=ctx,initializer=graph_worker_init) as pool:
                running={}
                def submit():
                    while not stop[0] and len(running)<workers:
                        job=next(iterator,None)
                        if job is None:break
                        running[pool.submit(solve_one,job)]=job
                submit()
                while running:
                    done,_=wait(running,timeout=max(0.,next_heartbeat-time.monotonic()),return_when=FIRST_COMPLETED)
                    for future in done:
                        job=running.pop(future);result=future.result()
                        save(OUT/'graph'/f"{job['event_id']}.json",result);results.append(result)
                        intermediate(jobs,results)
                    if time.monotonic()>=next_heartbeat:
                        progress();next_heartbeat=time.monotonic()+HEARTBEAT_S
                    submit()
        progress();intermediate(jobs,results)
        if len(results)<state['eligible']:
            state.update(status='INTERRUPTED',pid=None);save(OUT/'campaign_status.json',state);return
        print('[report] all inputs complete;generate tables,commit,push',flush=True)
        generate_reports()
        state.update(status='COMPLETE',pid=None,completed=len(results),elapsed_s=time.monotonic()-started);save(OUT/'campaign_status.json',state)
        publish();print('[complete] reports committed and pushed',flush=True)
    except BaseException as exc:
        state.update(status='FAILED',pid=None,error=repr(exc),completed=len(results));save(OUT/'campaign_status.json',state);raise

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
    assert 1<=a.workers<=4;freeze();jobs=inputs();results,pending=cache(jobs)
    if a.status or a.dry_run:
        print(json.dumps(dict(status(jobs,results,pending),dry_run=bool(a.dry_run),workers=a.workers,heartbeat_s=HEARTBEAT_S,
            auto_report_commit_push=True,will_reuse_all_completed=True)));return
    lock_path=ROOT.parent/'artifacts/isaac6/.phase52ec_graph.lock'
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise RuntimeError('Another offline graph campaign holds the lock') from exc
        # Reload after lock acquisition; final JSON is written atomically per input.
        results,pending=cache(jobs);run(jobs,results,pending,a.workers)

if __name__=='__main__':main()
