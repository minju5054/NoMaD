"""Serial24-run pilot with lock/resume, no outcome-based retries or skips."""
import argparse,json,os,signal,subprocess,time,errno
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_phase0.s0_batch import exclusive_batch
from .online_config import verify,protocol
from .online_launch import environment

from .storage import (read,atomic_json,capacity,ensure_reserve,disk_full_state,has_disk_error,operational_hash)

def write(p,x):atomic_json(p,x,backup=Path(p).name=='state.json')

def load_state(root):
    try:
        current=read(root/'state.json')
        if current is not None or not (root/'plan.json').exists():return current
    except (ValueError,UnicodeDecodeError):pass
    try:backup=read(root/'state.json.bak')
    except (ValueError,UnicodeDecodeError):backup=None
    if backup is None:
        saved=read(root/'plan.json');assert saved,'No valid state/backup/plan; preserve directory'
        backup=dict(protocol=saved['protocol'],jobs={},created_git_sha='RECOVERED_FROM_PLAN')
    damaged=root/('state.corrupt.'+str(time.time_ns())+'.json')
    if (root/'state.json').exists():os.replace(root/'state.json',damaged)
    backup.update(pid=None,current=None,status='RECOVERED_METADATA',recovered_from=str(damaged));write(root/'state.json',backup)
    return backup

def jobs(root):
    result=[];sockets=[]
    for row in protocol()['main_order']:
        key=f"{row['scene']}_{row['index']:03d}_{row['method']}";output=root/'main'/key;s=socket_path_for_run(output);assert validate_socket_path(s)<100;sockets.append(str(s));result.append(dict(row,key=key,output=str(output)))
    assert len(sockets)==len(set(sockets));return result

def status(root):
    try:state=read(root/'state.json',{})
    except (ValueError,UnicodeDecodeError):return dict(status='STATE_CORRUPT',completed=len(list((root/'metrics').glob('*.json'))),planned=24)
    done=read(root/'complete.json',{});live=False
    if state.get('pid'):
        try:live=Path(f"/proc/{state['pid']}/stat").read_text().split()[21]==state.get('process_token')
        except (FileNotFoundError,ProcessLookupError):pass
    label='COMPLETE' if done.get('report_complete') else 'RUNNING' if live else state.get('status','INTERRUPTED') if state else 'NOT_STARTED'
    if not live and label=='RUNNING':label='ABNORMAL_EXIT'
    return dict(status=label,completed=len(list((root/'metrics').glob('*.json'))),planned=24,current=state.get('current'),pid=state.get('pid') if live else None)

def campaign(root):
    p=verify();assert p['status']=='FROZEN';ready=read(ROOT/'research/results/phase24_online/online_readiness.json');assert ready['passed'] and ready['protocol_sha256']==sha256_file(Path(__file__).with_name('online_protocol.json'))
    for f,h in ready['source_sha256'].items():assert sha256_file(ROOT/f)==operational_hash(f,h),f
    assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip()
    plan=jobs(root);root.mkdir(parents=True,exist_ok=True)
    if read(root/'complete.json',{}).get('report_complete'):print('[complete] no runs repeated');return
    state=load_state(root);resume=state is not None
    if state is None:
        assert not any(root.iterdir()),'Preserve unidentified directory'
        state=dict(protocol=p,jobs={},created_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip());write(root/'plan.json',dict(jobs=plan,protocol=p))
    assert state['protocol']==p;state.update(pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21]);active=None
    with (root/'journal.jsonl').open('ab',buffering=0) as stream:
        def log(event,**kw):
            write(root/'state.json',state);stream.write((json.dumps(dict(event=event,time_ns=time.time_ns(),**kw))+'\n').encode());os.fsync(stream.fileno())
        def stop(*_):
            if active is not None and active.poll() is None:
                os.killpg(active.pid,signal.SIGTERM)
                try:active.wait(timeout=45)
                except subprocess.TimeoutExpired:os.killpg(active.pid,signal.SIGKILL);active.wait()
            state['status']='INTERRUPTED';log('INTERRUPTED');raise KeyboardInterrupt
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        try:
            state['status']='RUNNING';log('RESUME' if resume else 'START')
            for job in plan:
                metric=root/'metrics'/(job['key']+'.json')
                if metric.exists():continue
                dest=Path(job['output']);old=state['jobs'].get(job['key']) or ('RECOVERED_ATTEMPT' if dest.exists() else None);state['current']=job['key']
                if old is None:
                    disk=capacity(root,plan);write(root/'capacity.json',disk)
                    if not disk['enough']:
                        state.update(status='LOW_DISK_STOP',capacity=disk,current=None);log('LOW_DISK_STOP',free_bytes=disk['free_bytes'],required_free_bytes=disk['required_free_bytes']);print('[disk] stopped before next run: insufficient free space',flush=True);return
                    ensure_reserve(root)
                    assert not dest.exists();state['jobs'][job['key']]='START';log('RUN_START',job=job)
                    file=root/'logs'/(job['key']+'.log');file.parent.mkdir(exist_ok=True)
                    with file.open('x') as output:
                        command=['/usr/bin/python3','-u','-m','nomad_phase24.online_launch','--scene',job['scene'],'--method',job['method'],'--index',str(job['index']),'--output',str(dest)]
                        active=subprocess.Popen(command,cwd=ROOT,env=environment(),stdout=output,stderr=subprocess.STDOUT,start_new_session=True);code=active.wait();active=None
                else:code=0 if (dest/'launch_complete.json').exists() else -1
                result=dict(job,technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False,exit_code=code)
                if code==0:
                    try:
                        from .online_metrics import audit
                        result.update(audit(dest))
                    except Exception as exc:result['error']=repr(exc)
                else:result['error']='Launcher failure/interrupted attempt preserved; no retry'
                disk_error=code!=0 and has_disk_error(dest,root/'logs'/(job['key']+'.log'))
                if disk_error:result.update(technical_failure_reason='DISK_FULL',error='OSError28 confirmed in preserved attempt logs')
                write(metric,result);state['jobs'][job['key']]='END';log('RUN_END',key=job['key'],classification=result['classification']);print('[main]',job['key'],result['classification'],flush=True)
                if disk_error:
                    state.update(status='DISK_FULL_STOP',current=None);log('DISK_FULL_STOP',key=job['key']);return
            write(root/'complete.json',dict(navigation_complete=True,report_complete=False));state['current']='report';write(root/'state.json',state)
            with (root/'report.log').open('a') as output:
                active=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase24.online_report','--run-root',str(root),'--publish'],cwd=ROOT,env=environment(),stdout=output,stderr=subprocess.STDOUT,start_new_session=True);code=active.wait();active=None
            if code:raise RuntimeError('Report failed; resume runs no navigation again')
            write(root/'complete.json',dict(navigation_complete=True,report_complete=True));state['status']='COMPLETE';print('[report] generated, committed and pushed',flush=True)
        except OSError as exc:
            if exc.errno!=errno.ENOSPC:
                state.update(status='FAILED',error=repr(exc));raise
            disk_full_state(root,state,exc);print('[disk] stopped; atomic state preserved',flush=True)
        except BaseException as exc:
            state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));raise
        finally:
            state['pid']=None;state['current']=None
            if active is not None and active.poll() is None:
                os.killpg(active.pid,signal.SIGTERM)
                try:active.wait(timeout=45)
                except subprocess.TimeoutExpired:os.killpg(active.pid,signal.SIGKILL);active.wait()
            try:write(root/'state.json',state)
            except OSError as exc:
                if exc.errno!=errno.ENOSPC:raise
                disk_full_state(root,state,exc)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--stop',action='store_true');ap.add_argument('--disk-check',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    if a.disk_check:
        value=capacity(root,jobs(root));print(json.dumps({k:v for k,v in value.items() if k!='details'}));return
    if a.status:print(json.dumps(status(root)));return
    if a.dry_run:print(json.dumps(dict(planned=len(jobs(root)),new_navigation_started=0)));return
    if a.stop:
        s=read(root/'state.json');pid=s['pid'];assert Path(f'/proc/{pid}/stat').read_text().split()[21]==s['process_token'];assert 'nomad_phase24.campaign' in Path(f'/proc/{pid}/cmdline').read_text();os.kill(pid,signal.SIGTERM);print('Stop requested');return
    with exclusive_batch():campaign(root)
if __name__=='__main__':main()
