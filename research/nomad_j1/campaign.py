"""Seed-block budget, sequential GPU runs, resume, first-result notification."""
import argparse
import fcntl
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from nomad_phase26.storage import atomic_json
from nomad_isaac.common import sha256_file
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_j0.campaign import cleanup
from .config import ROOT,HERE,OUT,RUN_ROOT,SMOKE_ROOT,INDICES,order,verify

def jobs(root):
    rows=[]
    for j in order():
        key=f"{j['scene']}_{j['index']}_D750_{j['method']}";out=Path(root)/'main'/key/'attempt1'
        argv=['/usr/bin/python3','-u','-m','nomad_j1.launch','--scene',j['scene'],'--method',j['method'],
              '--index',str(j['index']),'--delay','.75','--output',str(out)]
        rows.append(dict(j,key=key,output=str(out),argv=argv,socket_bytes=validate_socket_path(socket_path_for_run(out))))
    assert len(rows)==195 and len({r['key'] for r in rows})==195
    return rows

def status(root):
    f=Path(root)/'state.json'
    return json.loads(f.read_text()) if f.exists() else dict(status='NOT_STARTED',planned=195)

def next_block_allowed(elapsed,block_started):return bool(block_started or elapsed<5.5*3600)

def notify_first(row):
    # Optional one-shot FIFO. No monitoring process or log polling is needed.
    fifo=os.environ.get('J1_FIRST_NOTICE_FIFO',str(ROOT.parent/'artifacts/isaac6/.j1_first_notice.fifo'))
    if fifo:
        try:
            fd=os.open(fifo,os.O_WRONLY|os.O_NONBLOCK)
            try:os.write(fd,(json.dumps(row)+'\n').encode())
            finally:os.close(fd)
        except (FileNotFoundError,OSError):pass

def execute(root,retry_first=False):
    from nomad_phase0.s0_batch import exclusive_batch
    from .metrics import audit
    p=verify();root.mkdir(parents=True,exist_ok=True)
    for folder in ('metrics','attempt_metrics','launcher_logs'):(root/folder).mkdir(exist_ok=True)
    digest=sha256_file(HERE/'protocol.json');prior=status(root)
    assert prior.get('protocol_sha256',digest)==digest
    plan=jobs(root);proc=None;started=time.monotonic();first_notice=False
    state=dict(status='RUNNING',pid=os.getpid(),planned=195,protocol_sha256=digest,session_started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
               session_budget_s=5.5*3600,current=None,stage='MAIN')
    def save():
        state['completed']=len(list((root/'metrics').glob('*.json')));state['elapsed_this_session_s']=time.monotonic()-started
        atomic_json(root/'state.json',state)
    def interrupted(*_):raise KeyboardInterrupt('J1 interrupted; same command resumes')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    with (root/'campaign.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with exclusive_batch():
            retry_key=None
            if retry_first:
                first=plan[0];file=root/'metrics'/(first['key']+'.json')
                assert file.exists() and json.loads(file.read_text())['classification']=='TECHNICAL_FAILURE'
                assert not (root/'retry_first_used.json').exists(),'Only one first-run plumbing retry is permitted'
                atomic_json(root/'retry_first_used.json',dict(key=first['key'],old_metric=json.loads(file.read_text())))
                retry_key=first['key'];file.unlink()
            save()
            try:
                stop=False
                for index in INDICES:
                    block=[j for j in plan if j['index']==index]
                    remaining=[j for j in block if not (root/'metrics'/(j['key']+'.json')).exists()]
                    if not remaining:continue
                    if not next_block_allowed(time.monotonic()-started,len(remaining)<15):
                        state.update(status='PARTIAL',reason='BUDGET_NO_NEW_SEED_BLOCK');break
                    state['seed_block']=index;save()
                    for j in remaining:
                        if shutil.disk_usage(ROOT).free<30_000_000_000:
                            state.update(status='PARTIAL',reason='DISK_BELOW_30GB');stop=True;break
                        verify();attempt=2 if j['key']==retry_key else 1
                        output=Path(j['output']) if attempt==1 else Path(j['output']).with_name('attempt2')
                        argv=list(j['argv']);argv[-1]=str(output);state.update(current=j['key'],attempt=attempt,stage='LAUNCH');save()
                        try:
                            if not output.exists():
                                with (root/'launcher_logs'/f"{j['key']}_attempt{attempt}.log").open('x') as log:
                                    proc=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                                    code=proc.wait();proc=None
                                    if code:raise RuntimeError(f'Launcher exit {code}')
                            assert (output/'launch_complete.json').exists(),'Preserved incomplete attempt; no automatic retry'
                            state['stage']='AUDIT';save();r=audit(output)
                        except Exception as e:r=dict(technical_validation='FAIL',classification='TECHNICAL_FAILURE',error=repr(e))
                        r.update({k:j[k] for k in ('scene','index','method','delay','key')});r.update(output=str(output),attempt=attempt)
                        atomic_json(root/'attempt_metrics'/f"{j['key']}_attempt{attempt}.json",r)
                        atomic_json(root/'metrics'/(j['key']+'.json'),r);cleanup(output);save()
                        notice=dict(event='RUN_DONE',key=j['key'],classification=r['classification'],completed=state['completed'],attempt=attempt,pid=os.getpid())
                        print(json.dumps(notice),flush=True)
                        if not first_notice:notify_first(notice);first_notice=True
                        if j['key']==plan[0]['key'] and r['classification']=='TECHNICAL_FAILURE':
                            state.update(status='STOP_FIRST_TECHNICAL_FAILURE',reason=r['error']);stop=True;break
                    if stop:break
                    state['completed_seed_blocks']=[i for i in INDICES if all((root/'metrics'/(j['key']+'.json')).exists() for j in plan if j['index']==i)];save()
                else:state.update(status='COMPLETE',reason=None)
            except BaseException as e:
                state.update(status='INTERRUPTED' if isinstance(e,KeyboardInterrupt) else 'FAILED',reason=repr(e))
                if proc is not None and proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=40)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                raise
            finally:state['current']=None;save()
            state['stage']='REPORT';save()
            # Reporting-only plumbing: persist the failure instead of leaving
            # a stale REPORT state without the exit/error cause. Scheduling,
            # block budget, methods and audit call site remain unchanged.
            try:
                with (root/'report.log').open('a') as log:
                    result=subprocess.run(['/usr/bin/python3','-m','nomad_j1.report','--run-root',str(root),'--publish'],cwd=ROOT,
                                          stdout=log,stderr=subprocess.STDOUT)
                if result.returncode:raise RuntimeError(f'Report exit {result.returncode}; see report.log')
            except BaseException as exc:
                state.update(stage='REPORT_FAILED',report_status='FAILED',report_error=repr(exc));save();raise
            state['report_status']='PUBLISHED';state.pop('report_error',None)
            state['stage']='DONE';save()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--status',action='store_true');ap.add_argument('--retry-first',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(status(root)));return
    verify()
    if a.dry_run:print(json.dumps(dict(planned=195,seed_blocks=13,jobs=jobs(root),simulations_started=0)));return
    assert ROOT==Path('/home/gpuadmin/Workspace/NoMaD/visualnav-transformer'),'Execution must use original repository folder'
    execute(root,a.retry_first)

if __name__=='__main__':main()
