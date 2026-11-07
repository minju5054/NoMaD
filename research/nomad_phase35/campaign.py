"""One simulator at a time; retry once; deadline/disk/resume/publishing guard."""
import argparse,json,os,re,shutil,signal,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_phase0.s0_batch import exclusive_batch
from nomad_phase26.launch import environment
from nomad_phase26.storage import atomic_json,read
from .config import RUN_ROOT,OUT,METHODS,SMOKE_METHODS,protocol,verify

def write(path,value):atomic_json(path,value,backup=path.name=='state.json')
def plan(smoke=False):
    rows=[dict(scene='H1',index=95,method=m) for m in SMOKE_METHODS] if smoke else protocol()['main_order']
    result=[];sockets=[]
    for row in rows:
        key=f"{row['scene']}_{row['index']:03d}_{row['method']}"
        outputs=[str(RUN_ROOT/('smoke' if smoke else 'main')/key/f'attempt{i}') for i in (1,2)]
        for output in outputs:
            sock=socket_path_for_run(Path(output));assert validate_socket_path(sock)<100;sockets.append(str(sock))
        result.append(dict(row,key=key,outputs=outputs))
    assert len(sockets)==len(set(sockets));return result

def status():
    s=read(RUN_ROOT/'state.json',{});pid=s.get('pid');live=False
    if pid:
        try:live=Path(f'/proc/{pid}/stat').read_text().split()[21]==s.get('process_token')
        except FileNotFoundError:pass
    label=s.get('status','NOT_STARTED')
    if label=='RUNNING' and not live:label='ABNORMAL_EXIT'
    return dict(status=label,stage=s.get('stage'),current=s.get('current'),completed=len(list((RUN_ROOT/'metrics').glob('*.json'))),planned=75,
        smoke_completed=len(list((RUN_ROOT/'smoke_metrics').glob('*.json'))),pid=pid if live else None,reason=s.get('reason'))

def guard(state):
    if time.time()>=protocol()['budget_start_unix']+6.5*3600:
        state.update(status='PARTIAL',reason='6.5-hour deadline reached; active run finished; resumable');return False
    free=shutil.disk_usage(ROOT).free
    write(RUN_ROOT/'capacity.json',dict(free_bytes=free,minimum_bytes=30_000_000_000,checked_unix=time.time()))
    if free<30_000_000_000:
        state.update(status='STOP_BLOCKED',reason='Disk free <30GB before next run');return False
    return True

def fingerprint(output):
    p=Path(output);error=read(p/'FAILED.json',{}).get('error') or read(p/'launch_failure.json',{}).get('error')
    if error:return re.sub(r'0x[0-9a-f]+','ADDRESS',error)
    return 'LAUNCH_FAILED_WITHOUT_ERROR_RECORD'

def run_job(job,state,smoke=False):
    directory=RUN_ROOT/('smoke_metrics' if smoke else 'metrics');final=directory/(job['key']+'.json')
    if final.exists():return read(final)
    attempts=[]
    for attempt,output in enumerate(job['outputs'],1):
        metric=RUN_ROOT/'attempt_metrics'/f"{'smoke_' if smoke else ''}{job['key']}_{attempt}.json"
        dest=Path(output)
        if metric.exists():r=read(metric)
        else:
            if not guard(state):return None
            state['current']=job['key']+f':{attempt}';write(RUN_ROOT/'state.json',state)
            if dest.exists():code=0 if (dest/'launch_complete.json').exists() else -1
            else:
                log=RUN_ROOT/'logs'/f"{'smoke_' if smoke else ''}{job['key']}_{attempt}.log";log.parent.mkdir(parents=True,exist_ok=True)
                cmd=['/usr/bin/python3','-u','-m','nomad_phase35.launch','--scene',job['scene'],'--method',job['method'],'--index',str(job['index']),'--output',output]
                if smoke:cmd.append('--smoke')
                with log.open('x') as stream:
                    proc=subprocess.Popen(cmd,cwd=ROOT,env=environment(),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                    state['active_child_pid']=proc.pid;write(RUN_ROOT/'state.json',state)
                    try:code=proc.wait()
                    finally:
                        if proc.poll() is None:
                            os.killpg(proc.pid,signal.SIGTERM)
                            try:proc.wait(timeout=45)
                            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                        state.pop('active_child_pid',None)
            r=dict(job,attempt=attempt,output=output,exit_code=code,technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False,collision=None)
            if code==0:
                try:
                    from .metrics import audit
                    r.update(audit(dest))
                except Exception as exc:r['error']=repr(exc)
            else:r['error']=fingerprint(output)
            write(metric,r)
        attempts.append(r)
        if r['technical_validation']=='PASS':break
        print('[technical_failure]',job['key'],attempt,r.get('error'),flush=True)
        if smoke:
            errors=state.setdefault('smoke_error_counts',{});key=r.get('error','UNKNOWN')
            # Count each attempt only once when resuming after a technical fix.
            seen=state.setdefault('smoke_error_attempts',[])
            if str(metric) not in seen:errors[key]=errors.get(key,0)+1;seen.append(str(metric))
            if errors[key]>=2 or attempt==2:
                state.update(status='STOP_BLOCKED',reason='Smoke technical error repeated or retry exhausted: '+key);return None
            if read(RUN_ROOT/'allow_smoke_retry.json',{}).get('key')!=job['key']:
                state.update(status='AWAITING_TECHNICAL_FIX',reason='Inspect first smoke error before one retry: '+key);return None
    r=dict(attempts[-1],attempt_count=len(attempts),attempts=attempts);write(final,r);return r

def publish(stage):
    subprocess.run(['/usr/bin/python3','-m','nomad_phase35.report','--stage',stage,'--publish'],cwd=ROOT,env=environment(),check=True)

def campaign(stage):
    p=verify();RUN_ROOT.mkdir(parents=True,exist_ok=True)
    planfile=RUN_ROOT/'plan.json'
    if planfile.exists():assert read(planfile)['order']==p['main_order']
    else:write(planfile,dict(order=p['main_order'],protocol_sha256=__import__('hashlib').sha256((Path(__file__).with_name('protocol.json')).read_bytes()).hexdigest()))
    state=read(RUN_ROOT/'state.json',{});state.update(status='RUNNING',stage=stage,pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],current=None,reason=None)
    def stop(*_):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        if stage in ('all','smoke'):
            state['stage']='smoke'
            for job in plan(True):
                print('[smoke]',job['key'],'start',flush=True)
                r=run_job(job,state,True)
                if r is None:return
                print('[smoke]',job['key'],'TECHNICAL_PASS',flush=True)
            state.update(status='SMOKE_PASS',reason='Four requested technical smokes passed');write(RUN_ROOT/'state.json',state);publish('smoke')
            if stage=='smoke':return
        assert all(read(RUN_ROOT/'smoke_metrics'/(j['key']+'.json'),{}).get('technical_validation')=='PASS' for j in plan(True))
        state.update(status='RUNNING',stage='main',reason=None)
        jobs=plan();published=set(state.get('published_blocks',[]))
        for i,job in enumerate(jobs):
            if not (RUN_ROOT/'metrics'/(job['key']+'.json')).exists():
                if not guard(state):return
                print('[main]',i+1,'/75',job['key'],'start',flush=True)
                if run_job(job,state) is None:return
            if (i+1)%25==0:
                block=(i+1)//5
                if block not in published:
                    write(RUN_ROOT/'state.json',state);publish(f'blocks_{block}')
                    published.add(block);state['published_blocks']=sorted(published)
        state.update(status='COMPLETE',reason='All 75 preregistered runs finished',current=None)
        write(RUN_ROOT/'complete.json',dict(complete=True,planned=75))
    except BaseException as exc:
        state.update(status='PARTIAL' if isinstance(exc,KeyboardInterrupt) else 'STOP_BLOCKED',reason=repr(exc));raise
    finally:
        state.update(pid=None,current=None);write(RUN_ROOT/'state.json',state)
        publish(state['status'])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=('all','smoke','main'),default='all');ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(status()));return
    if a.dry_run:verify();print(json.dumps(dict(main=len(plan()),smoke=len(plan(True)),sockets=2*(len(plan())+len(plan(True))),navigation_started=0)));return
    with exclusive_batch():campaign(a.stage)
if __name__=='__main__':main()
