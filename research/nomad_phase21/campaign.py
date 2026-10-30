"""Serial paired campaign, one technical retry, persistent lock/resume/no overwrite."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase0.s0_batch import exclusive_batch
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from .config import protocol,verify_sources
from .preflight import env

def read(p,default=None):return json.loads(Path(p).read_text()) if Path(p).exists() else default
def write(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2)+'\n');tmp.replace(p)
def jobs(root):
    result=[];sockets=[]
    for j in protocol()['main_order']:
        j=dict(j,key=f"{j['scene']}_{j['index']:03d}_{j['method']}");j['outputs']=[str(root/'main'/j['key']/f'attempt{a}') for a in (1,2)]
        for path in j['outputs']:
            sock=socket_path_for_run(path);assert validate_socket_path(sock)<100;sockets.append(str(sock))
        result.append(j)
    assert len(set(sockets))==len(sockets);return result

def status(root):
    s=read(root/'state.json',{});c=read(root/'complete.json',{});done=sum((root/'metrics'/f"{j['key']}.json").exists() for j in read(root/'plan.json',{}).get('jobs',[]))
    return dict(state='COMPLETE' if c.get('report_complete') else 'REPORT_PENDING' if c else 'RUNNING' if s.get('pid') else 'INTERRUPTED' if s else 'NOT_STARTED',jobs_finished=done,planned=s.get('planned'),current=s.get('current'),pid=s.get('pid'))

def campaign(root):
    p=verify_sources();assert p['status']=='FROZEN';ready=read(ROOT/'research/results/phase21_preflight/readiness.json');assert ready['passed']
    assert ready['protocol_sha256']==sha256_file(Path(__file__).with_name('protocol.json'))
    for name,h in ready['source_sha256'].items():assert sha256_file(ROOT/name)==h,name
    assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip()
    plan=jobs(root);root.mkdir(parents=True,exist_ok=True)
    if read(root/'complete.json',{}).get('report_complete'):print('[campaign] already complete');return
    state=read(root/'state.json');resume=state is not None
    if state is None:
        assert not any(root.iterdir()),'Existing unidentified output preserved'
        state=dict(protocol=p,attempts={},source_sha256=ready['source_sha256'],created_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),planned=len(plan))
        write(root/'plan.json',dict(protocol=p,jobs=plan,git_sha=state['created_git_sha']))
    assert state['protocol']==p
    for name,h in state['source_sha256'].items():assert sha256_file(ROOT/name)==h,name
    state.update(pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],interrupted=False);active=None
    with (root/'journal.jsonl').open('a') as journal:
        def log(event,**kw):journal.write(json.dumps(dict(event=event,time_ns=time.time_ns(),**kw))+'\n');journal.flush();write(root/'state.json',state)
        def stop(*_):
            state['interrupted']=True
            if active is not None and active.poll() is None:
                os.killpg(active.pid,signal.SIGTERM)
                try:active.wait(timeout=45)
                except subprocess.TimeoutExpired:os.killpg(active.pid,signal.SIGKILL);active.wait()
            log('INTERRUPTED');raise KeyboardInterrupt
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);log('RESUME' if resume else 'START')
        try:
            for job in plan:
                final=root/'metrics'/f"{job['key']}.json"
                if final.exists():continue
                attempt_results=[]
                for attempt,output in enumerate(job['outputs'],1):
                    dest=Path(output);name=f"{job['key']}:attempt{attempt}";record=state['attempts'].get(name);metric=root/'attempt_metrics'/f"{job['key']}_{attempt}.json"
                    if metric.exists():r=read(metric)
                    else:
                        if record is None:
                            assert not dest.exists(),'No overwrite of unidentified attempt'
                            state['current']=name;state['attempts'][name]=dict(state='START',output=output);log('ATTEMPT_START',key=job['key'],attempt=attempt)
                            command=['/usr/bin/python3','-u','-m','nomad_phase21.launch','--mode','navigation','--scene',job['scene'],'--method',job['method'],'--index',str(job['index']),'--delay','.75','--topomap',p['SO']['topomap'],'--output',output]
                            logfile=root/'logs'/f"{job['key']}_{attempt}.log";logfile.parent.mkdir(exist_ok=True)
                            with logfile.open('x') as f:active=subprocess.Popen(command,cwd=ROOT,env=env(),stdout=f,stderr=subprocess.STDOUT,start_new_session=True);code=active.wait();active=None
                        else:code=0 if (dest/'launch_complete.json').exists() else -1
                        r=dict(scene=job['scene'],index=job['index'],method=job['method'],seed_offset=job['seed_offset'],attempt=attempt,output=output,technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False,exit_code=code)
                        if code==0:
                            try:
                                from .metrics import audit
                                r.update(audit(dest))
                            except Exception as exc:r['error']=repr(exc)
                        else:r['error']=f'Launcher exit {code}; preserved attempt'
                        write(metric,r)
                    attempt_results.append(r);state['attempts'][name]=dict(state='END',output=output,technical_validation=r['technical_validation']);log('ATTEMPT_END',key=job['key'],attempt=attempt,validation=r['technical_validation'])
                    if r['technical_validation']=='PASS':break
                    if attempt==1:print(f"[retry] {job['key']} same seed, final allowed attempt",flush=True)
                r={**attempt_results[-1],'attempts':attempt_results,'attempt_count':len(attempt_results)};write(final,r);state['current']=None;log('JOB_END',key=job['key'],classification=r['classification']);print(f"[main] {job['key']} {r['classification']}",flush=True)
            write(root/'complete.json',dict(navigation_complete=True,report_complete=False,planned=len(plan)));log('NAVIGATION_COMPLETE')
            state['current']='report';write(root/'state.json',state)
            with (root/'report.log').open('a') as stream:
                active=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase21.report','--run-root',str(root),'--publish'],cwd=ROOT,env=env(),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);code=active.wait();active=None
            if code:raise RuntimeError('Report failed; saved navigation retained; resume report only')
            write(root/'complete.json',dict(navigation_complete=True,report_complete=True,planned=len(plan)));print('[report] committed and pushed',flush=True)
        finally:state['pid']=None;state['current']=None;write(root/'state.json',state)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);g=ap.add_mutually_exclusive_group();g.add_argument('--status',action='store_true');g.add_argument('--stop',action='store_true');g.add_argument('--dry-run',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(status(root)));return
    if a.stop:
        s=read(root/'state.json');pid=s['pid'];assert pid and Path(f'/proc/{pid}/stat').read_text().split()[21]==s['process_token'];assert 'nomad_phase21.campaign' in Path(f'/proc/{pid}/cmdline').read_text();os.kill(pid,signal.SIGTERM);print('Stop requested');return
    if a.dry_run:print(json.dumps(dict(planned=len(jobs(root)),max_technical_retries=1,indices=protocol()['indices'],new_navigation_started=0)));return
    with exclusive_batch():campaign(root)
if __name__=='__main__':main()
