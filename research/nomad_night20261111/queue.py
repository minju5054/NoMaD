"""One nohup queue, serial launches, persistent6h cutoff, no smoke retries."""
import argparse,hashlib,json,os,select,signal,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from nomad_phase0.s0_batch import exclusive_batch
from nomad_phase26 import campaign as base
from nomad_phase26.launch import environment
from nomad_phase40p.launch import bind
from nomad_phase40p.campaign import capacity
from .config import ROOT,HERE,QUEUE_ROOT,RESULTS,DEFS,protocol,verify

class DeadlineReached(Exception):pass

def now():return datetime.now(timezone.utc).isoformat()
def env(e):return dict(environment(),NOMAD_NIGHT_EXPERIMENT=e)
def jobs(e,smoke=False):
    root=QUEUE_ROOT/'smoke'/e if smoke else QUEUE_ROOT/e
    p=protocol(e)
    if smoke:p=dict(p,main_order=[DEFS[e]['smoke']])
    plan=bind(base.jobs,protocol=lambda:p)(root,False)
    if smoke:
        for j in plan:j['outputs']=j['outputs'][:1]
    return root,plan

def status():
    s=base.status(QUEUE_ROOT);state=base.read(QUEUE_ROOT/'state.json',{})
    s['completed']=sum(len(list((QUEUE_ROOT/e/'metrics').glob('*.json'))) for e in DEFS)
    return dict(s,started_utc=state.get('started_utc'),deadline_utc=state.get('deadline_utc'),
        experiments={e:dict(base.status(QUEUE_ROOT/e),planned=len(protocol(e)['main_order'])) for e in DEFS},
        smoke=base.read(QUEUE_ROOT/'smoke_selection.json',{}))

def check_start(deadline):
    if deadline is not None and time.time()>=deadline:raise DeadlineReached('6h deadline: do not start another run or retry')
    if not capacity(QUEUE_ROOT,[])['enough']:raise OSError('LOW_DISK_STOP: free space below30GB')

def one_job(e,root,j,state,smoke=False,deadline=None,started=None):
    final=root/'metrics'/f"{j['key']}.json"
    if final.exists():return base.read(final)
    attempts=[]
    for attempt,output in enumerate(j['outputs'],1):
        mp=root/'attempt_metrics'/f"{j['key']}_{attempt}.json";out=Path(output)
        if mp.exists():r=base.read(mp)
        else:
            state.update(current=j['key']+f':{attempt}');base.write(root/'state.json',state)
            if out.exists():code=0 if (out/'launch_complete.json').exists() else -1
            else:
                check_start(deadline);base.ensure_reserve(root)
                logfile=root/'logs'/f"{j['key']}_{attempt}.log";logfile.parent.mkdir(exist_ok=True)
                cmd=['/usr/bin/python3','-u','-m','nomad_night20261111.launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',output]
                if smoke:cmd.append('--smoke')
                with logfile.open('x') as f:
                    check_start(deadline)
                    child=subprocess.Popen(cmd,cwd=ROOT,env=env(e),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
                    state['active_child_pid']=child.pid;base.write(root/'state.json',state)
                    if started:started(e,j,child.pid)
                    try:code=child.wait()
                    finally:
                        if child.poll() is None:
                            os.killpg(child.pid,signal.SIGTERM)
                            try:child.wait(timeout=45)
                            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                        state.pop('active_child_pid',None)
            r=dict(j,attempt=attempt,output=output,exit_code=code,technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)
            if code==0:
                try:
                    from .metrics import audit
                    r.update(audit(out))
                except Exception as exc:r['error']=repr(exc)
            else:r['error']='Launcher failure; preserved; no source repair during this queue'
            base.write(mp,r)
        attempts.append(r)
        if r['technical_validation']=='PASS':break
        print('[technical]',e,j['key'],attempt,r.get('error'),flush=True)
    result=dict(attempts[-1],attempt_count=len(attempts),attempts=attempts)
    base.write(final,result);return result

def smoke():
    selection={}
    with exclusive_batch():
        for e in DEFS:
            p=verify(e);root,plan=jobs(e,True);root.mkdir(parents=True,exist_ok=True)
            state=dict(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],planned=1,smoke=True)
            print('[smoke]',e,plan[0]['key'],'start',flush=True)
            try:
                r=one_job(e,root,plan[0],state,True);passed=r['technical_validation']=='PASS'
                selection[e]=dict(status='PASS' if passed else 'SKIPPED',reason='AUDIT_PASS' if passed else r.get('error','AUDIT_FAIL'),
                    protocol_sha256=hashlib.sha256((HERE/f'protocol_{e}.json').read_bytes()).hexdigest(),key=plan[0]['key'],output=r['output'],attempts=r['attempt_count'])
                state['status']='COMPLETE' if passed else 'SKIPPED'
            except Exception as exc:
                selection[e]=dict(status='SKIPPED',reason=repr(exc));state.update(status='SKIPPED',error=repr(exc))
            finally:state.update(pid=None,current=None);base.write(root/'state.json',state)
            base.write(QUEUE_ROOT/'smoke_selection.json',selection);base.write(RESULTS/'smoke_selection.json',selection)
            print('[smoke]',e,selection[e]['status'],flush=True)
    return selection

def publish_report(e):
    root=QUEUE_ROOT/e;root.mkdir(parents=True,exist_ok=True)
    with (root/'report.log').open('a') as f:
        subprocess.run(['/usr/bin/python3','-u','-m','nomad_night20261111.report','--publish'],cwd=ROOT,env=env(e),stdout=f,stderr=subprocess.STDOUT,check=True)

def run(ready_fd=None):
    with exclusive_batch():
        selection=base.read(QUEUE_ROOT/'smoke_selection.json',{});assert set(selection)==set(DEFS)
        for e in DEFS:verify(e)
        eligible=[e for e in DEFS if selection[e]['status']=='PASS']
        assert eligible,'All experiments skipped; no queue launched'
        for e in eligible:assert selection[e]['protocol_sha256']==hashlib.sha256((HERE/f'protocol_{e}.json').read_bytes()).hexdigest()
        assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip()
        state=base.read(QUEUE_ROOT/'state.json',{})
        if 'deadline_epoch_s' not in state:
            epoch=time.time();state.update(started_utc=now(),started_epoch_s=epoch,deadline_epoch_s=epoch+6*3600,
                deadline_utc=datetime.fromtimestamp(epoch+6*3600,timezone.utc).isoformat())
        state.update(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],planned=sum(len(protocol(e)['main_order']) for e in eligible))
        base.write(QUEUE_ROOT/'state.json',state)
        acknowledged=False
        def announce(e,j,pid):
            nonlocal acknowledged,ready_fd
            state.update(current=e+'/'+j['key'],active_child_pid=pid);base.write(QUEUE_ROOT/'state.json',state)
            if not acknowledged:
                receipt=dict(status='STARTED',queue_pid=os.getpid(),launch_pid=pid,experiment=e,key=j['key'],started_utc=state['started_utc'],deadline_utc=state['deadline_utc'])
                base.write(QUEUE_ROOT/'start_receipt.json',receipt)
                if ready_fd is not None:os.write(ready_fd,(json.dumps(receipt)+'\n').encode());os.close(ready_fd);ready_fd=None
                acknowledged=True
        def stop(*_):raise KeyboardInterrupt('Queue interrupted')
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        deadline=state['deadline_epoch_s'];expired=False
        try:
            for e in DEFS:
                root,plan=jobs(e);root.mkdir(parents=True,exist_ok=True)
                if selection[e]['status']!='PASS':
                    base.write(root/'state.json',dict(status='SKIPPED',reason=selection[e]['reason'],planned=len(plan)));publish_report(e);continue
                saved=base.read(root/'plan.json')
                if saved:assert saved['protocol']==protocol(e)
                else:base.write(root/'plan.json',dict(protocol=protocol(e),jobs=plan))
                es=dict(status='RUNNING',pid=os.getpid(),process_token=state['process_token'],planned=len(plan))
                try:
                    for j in plan:
                        if (root/'metrics'/f"{j['key']}.json").exists():continue
                        check_start(deadline)
                        print('[main]',e,j['key'],'start',flush=True)
                        r=one_job(e,root,j,es,deadline=deadline,started=announce)
                        print('[audit]',e,j['key'],r['technical_validation'],flush=True)
                    es['status']='COMPLETE'
                except DeadlineReached:
                    expired=True;es['status']='PARTIAL_TIME_LIMIT';print('[deadline]',e,'no new run',flush=True)
                finally:es.update(pid=None,current=None);base.write(root/'state.json',es)
                publish_report(e)
            state['status']='PARTIAL_TIME_LIMIT' if expired else 'COMPLETE'
        except BaseException as exc:state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));raise
        finally:
            if ready_fd is not None:os.close(ready_fd)
            state.update(pid=None,active_child_pid=None);base.write(QUEUE_ROOT/'state.json',state)

def start():
    # Exactly one nohup. One blocking startup acknowledgment, no polling or
    # monitoring after the first launch receipt. No wait for run completion.
    assert not base.status(QUEUE_ROOT).get('pid'),'Queue already running'
    selection=base.read(QUEUE_ROOT/'smoke_selection.json',{})
    assert set(selection)==set(DEFS) and any(r['status']=='PASS' for r in selection.values()),'No passed experiment to start'
    check_start(None);r,w=os.pipe();log=QUEUE_ROOT.parent/'night_queue_20261111_01.log'
    with log.open('a') as stream:
        proc=subprocess.Popen(['nohup','/usr/bin/python3','-u','-m','nomad_night20261111.queue','--run','--ready-fd',str(w)],cwd=ROOT,env=environment(),
            stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(w,))
    os.close(w)
    try:
        if not select.select([r],[],[],45)[0]:raise TimeoutError(f'No startup acknowledgment;inspect {log};do not launch duplicate queue pid{proc.pid}')
        message=os.read(r,10000)
        if not message:raise RuntimeError(f'Queue exited before startup acknowledgment;inspect {log}')
        print(message.decode().strip());print('LOG',log)
    finally:os.close(r)

def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for name in ('smoke','run','start','status','dry-run'):g.add_argument('--'+name,action='store_true')
    ap.add_argument('--ready-fd',type=int);a=ap.parse_args()
    if a.status:print(json.dumps(status()));return
    if a.dry_run:
        for e in DEFS:verify(e)
        print(json.dumps(dict(experiments={e:dict(planned=len(jobs(e)[1]),jobs=jobs(e)[1],smoke=jobs(e,True)[1]) for e in DEFS},simulations_started=0)));return
    if a.smoke:smoke()
    elif a.start:start()
    else:run(a.ready_fd)
if __name__=='__main__':main()
