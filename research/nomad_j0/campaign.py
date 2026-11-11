"""Resumable single-simulator queue. All zero-delay blocks precede D750."""
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
from nomad_isaac.socket_path import socket_path_for_run, validate_socket_path
from .config import ROOT,HERE,OUT,RUN_ROOT,order,verify

def jobs(root):
    result=[]
    for item in order():
        key=f"{item['scene']}_D{round(item['delay']*1000):03d}_{item['index']}_{item['method']}"
        output=Path(root)/'main'/key/'attempt1'
        argv=['/usr/bin/python3','-u','-m','nomad_j0.launch','--scene',item['scene'],'--index',str(item['index']),
              '--method',item['method'],'--delay',str(item['delay']),'--output',str(output)]
        result.append(dict(item,key=key,output=str(output),argv=argv,socket_bytes=validate_socket_path(socket_path_for_run(output))))
    assert len(result)==20 and len({r['key'] for r in result})==20
    return result

def status(root):
    f=Path(root)/'state.json'
    return json.loads(f.read_text()) if f.exists() else dict(status='NOT_STARTED',planned=20)

def cleanup(output):
    # Only launcher-owned cache subdirectories; preserve raw data and manifests.
    for part in ('portable','cache','pycache'):
        p=Path(output)/part
        if p.exists():shutil.rmtree(p)

def execute(root,plan=None,report_argv=None):
    from nomad_phase0.s0_batch import exclusive_batch
    from .metrics import audit
    p=verify();root.mkdir(parents=True,exist_ok=True)
    plan=jobs(root) if plan is None else plan
    for name in ('metrics','launcher_logs'):(root/name).mkdir(exist_ok=True)
    digest=sha256_file(HERE/'protocol.json');old=status(root)
    assert old.get('protocol_sha256',digest)==digest,'Cannot resume a different frozen protocol'
    state=dict(status='RUNNING',planned=len(plan),protocol_sha256=digest,started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),pid=os.getpid())
    start=time.monotonic();proc=None
    def save():
        state['completed']=len(list((root/'metrics').glob('*.json')))
        state['elapsed_this_session_s']=time.monotonic()-start
        atomic_json(root/'state.json',state)
    def interrupted(*_):raise KeyboardInterrupt('J0 interrupted; resume the same root')
    signal.signal(signal.SIGTERM,interrupted)
    with (root/'campaign.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with exclusive_batch():
            save()
            try:
                for j in plan:
                    metric=root/'metrics'/(j['key']+'.json')
                    if metric.exists():continue
                    if time.monotonic()-start>=p['session_budget_s']:
                        state.update(status='PARTIAL',reason='ONE_HOUR_SESSION_BUDGET');break
                    if shutil.disk_usage(ROOT).free<30_000_000_000:
                        state.update(status='BLOCKED',reason='DISK_BELOW_30GB');break
                    verify();output=Path(j['output']);state.update(current=j['key'],stage='LAUNCH');save()
                    try:
                        if not output.exists():
                            with (root/'launcher_logs'/(j['key']+'.log')).open('x') as log:
                                proc=subprocess.Popen(j['argv'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                                code=proc.wait();proc=None
                                if code:raise RuntimeError(f'Launcher exit {code}')
                        # Resume completed raw runs without rerunning a simulation.
                        assert (output/'launch_complete.json').exists(),'Preserved incomplete attempt; no automatic retry'
                        state['stage']='AUDIT';save();r=audit(output)
                    except Exception as e:
                        r=dict(technical_validation='FAIL',classification='TECHNICAL_FAILURE',error=repr(e))
                    r.update({k:j[k] for k in ('scene','index','method','delay','key','output')})
                    atomic_json(metric,r);cleanup(output);save()
                    print(json.dumps(dict(event='RUN_DONE',key=j['key'],completed=state['completed'],classification=r['classification'])),flush=True)
                else:state.update(status='COMPLETE',reason=None)
            except BaseException as e:
                state.update(status='INTERRUPTED' if isinstance(e,KeyboardInterrupt) else 'FAILED',reason=repr(e))
                if proc is not None and proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=40)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                raise
            finally:
                state['current']=None;save()
            state['stage']='REPORT';save()
            subprocess.run(report_argv or ['/usr/bin/python3','-m','nomad_j0.report','--run-root',str(root),'--publish'],cwd=ROOT,check=True)
            state['stage']='DONE';save()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT)
    ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(status(root)));return
    verify()
    if a.dry_run:
        print(json.dumps(dict(planned=20,simulations_started=0,jobs=jobs(root))));return
    execute(root)

if __name__=='__main__':main()
