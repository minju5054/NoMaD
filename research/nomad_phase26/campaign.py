"""Serial, locked, resumable paired campaign; one technical retry only."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_phase0.s0_batch import exclusive_batch
from .config import protocol,verify
from .launch import environment
from .storage import atomic_json,read,capacity,ensure_reserve,disk_full_state
from nomad_phase24r2.campaign import load_state

def write(p,x):atomic_json(p,x,backup=Path(p).name=='state.json')

def jobs(root,smoke=False):
    p=protocol()
    matrix=([dict(scene=s,index=95,method=m) for s in ('H1','H2') for m in p['methods']]+[dict(scene=s,index=95,method='C0') for s in ('SLW','LC','L2')]) if smoke else p['main_order']
    plan=[];sockets=[]
    for row in matrix:
        key=f"{row['scene']}_{row['index']:03d}_{row['method']}"
        outputs=[str(root/'main'/key/f'attempt{i}') for i in (1,2)]
        for output in outputs:
            s=socket_path_for_run(Path(output));assert validate_socket_path(s)<100;sockets.append(str(s))
        plan.append(dict(row,key=key,outputs=outputs))
    assert len(sockets)==len(set(sockets));return plan

def status(root):
    try:s=read(root/'state.json',{})
    except (ValueError,UnicodeDecodeError):return dict(status='STATE_CORRUPT',planned=60)
    live=False
    if s.get('pid'):
        try:live=Path(f"/proc/{s['pid']}/stat").read_text().split()[21]==s.get('process_token')
        except (FileNotFoundError,ProcessLookupError):pass
    label=s.get('status','NOT_STARTED')
    if label=='RUNNING' and not live:label='ABNORMAL_EXIT'
    return dict(status=label,completed=len(list((root/'metrics').glob('*.json'))),planned=s.get('planned',60),current=s.get('current'),pid=s.get('pid') if live else None)

def run_job(root,job,state,smoke=False):
    final=root/'metrics'/(job['key']+'.json')
    if final.exists():return read(final)
    attempts=[]
    for attempt,output in enumerate(job['outputs'],1):
        metric=root/'attempt_metrics'/f"{job['key']}_{attempt}.json";dest=Path(output)
        if metric.exists():r=read(metric)
        else:
            state['current']=job['key']+':'+str(attempt);write(root/'state.json',state)
            if dest.exists():code=0 if (dest/'launch_complete.json').exists() else -1
            else:
                if not smoke:
                    disk=capacity(root,jobs(root));write(root/'capacity.json',disk)
                    if not disk['enough']:state.update(status='LOW_DISK_STOP',current=None);return None
                logfile=root/'logs'/f"{job['key']}_{attempt}.log";logfile.parent.mkdir(exist_ok=True)
                cmd=['/usr/bin/python3','-u','-m','nomad_phase26.launch','--scene',job['scene'],'--method',job['method'],'--index',str(job['index']),'--output',output]
                if smoke:cmd.append('--smoke')
                with logfile.open('x') as stream:
                    proc=subprocess.Popen(cmd,cwd=ROOT,env=environment(),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                    state['active_child_pid']=proc.pid;write(root/'state.json',state)
                    try:code=proc.wait()
                    finally:
                        if proc.poll() is None:
                            os.killpg(proc.pid,signal.SIGTERM)
                            try:proc.wait(timeout=45)
                            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                        state.pop('active_child_pid',None)
            r=dict(job,attempt=attempt,output=output,exit_code=code,technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)
            if code==0:
                try:
                    from .metrics import audit
                    r.update(audit(dest))
                except Exception as exc:r['error']=repr(exc)
            else:r['error']='Launcher failure/interrupted attempt preserved'
            write(metric,r)
        attempts.append(r)
        if r['technical_validation']=='PASS':break
        if smoke:
            # Inspect/fix an implementation failure before spending the one
            # allowed second attempt. Reinvoking preflight skips failed attempt1.
            if attempt==1 and read(root/'allow_smoke_retry',{}).get('key')!=job['key']:raise RuntimeError('Smoke failed; preserve and inspect '+job['key'])
        print('[retry]',job['key'],'technical failure',flush=True)
    r=dict(attempts[-1],attempt_count=len(attempts),attempts=attempts);write(final,r);return r

def campaign(root,smoke=False):
    p=verify()
    if not smoke:
        assert p['status']=='FROZEN' and not p.get('pending_questions')
        ready=read(ROOT/'research/results/phase26/preflight.json');assert ready['passed'] and ready['protocol_sha256']==sha256_file(Path(__file__).with_name('protocol.json'))
        assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip()
    else:
        for scene in ('H1','H2'):assert read(ROOT.parent/f'artifacts/isaac6/phase26_geometry_01/{scene}/geometry_only.json')['passed']
    root.mkdir(parents=True,exist_ok=True);plan=jobs(root,smoke)
    if read(root/'complete.json',{}).get('complete'):print('[complete] no repeats');return
    state=load_state(root) or {}
    if state:print('[resume]',state.get('current'),flush=True)
    state.update(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],planned=len(plan),smoke=smoke)
    if not smoke:
        if (root/'plan.json').exists():assert read(root/'plan.json')['protocol']==p
        else:write(root/'plan.json',dict(protocol=p,jobs=plan))
    def stop(*_):raise KeyboardInterrupt('Campaign interrupted')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        for j in plan:
            if (root/'metrics'/(j['key']+'.json')).exists():continue
            if not smoke:
                disk=capacity(root,plan);write(root/'capacity.json',disk)
                if not disk['enough']:state.update(status='LOW_DISK_STOP',current=None);return
                ensure_reserve(root)
            else:
                import shutil
                if shutil.disk_usage(root).free<25_000_000_000:state.update(status='LOW_DISK_STOP');return
            print('[smoke]' if smoke else '[main]',j['key'],'start',flush=True)
            r=run_job(root,j,state,smoke)
            if r is None:return
            print('[smoke]' if smoke else '[main]',j['key'],r['technical_validation'],flush=True)
            if smoke:assert r['technical_validation']=='PASS'
        if not smoke:
            state['current']='report';write(root/'state.json',state)
            with (root/'report.log').open('a') as stream:subprocess.run(['/usr/bin/python3','-u','-m','nomad_phase26.report','--run-root',str(root),'--publish'],cwd=ROOT,env=environment(),stdout=stream,stderr=subprocess.STDOUT,check=True)
        write(root/'complete.json',dict(complete=True,smoke=smoke));state['status']='COMPLETE'
    except OSError as exc:
        if exc.errno==28:disk_full_state(root,state,exc)
        else:state.update(status='FAILED',error=repr(exc));raise
    except BaseException as exc:state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));raise
    finally:
        state.update(pid=None,current=None);write(root/'state.json',state)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--smoke-only',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(status(root)));return
    if a.dry_run:print(json.dumps(dict(planned=len(jobs(root,a.smoke_only)),navigation_started=0)));return
    with exclusive_batch():campaign(root,a.smoke_only)
if __name__=='__main__':main()
