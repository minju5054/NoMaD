"""Serial, resumable asset/gate reuse -> main -> CPU report. No retries."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_phase0.s0_batch import exclusive_batch
from .config import METHODS,protocol,verify_sources

def write(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
def read(path,default=None):return json.loads(Path(path).read_text()) if Path(path).exists() else default
def clean_env():
    e=os.environ.copy()
    for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):e.pop(k,None)
    e.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-phase18-mpl');return e
def plan_jobs(root):
    jobs=[]
    for item in protocol()['main_order']:
        j=dict(item);j['key']=f"{j['scene']}_{j['index']:03d}_D750_{j['method']}";j['output']=str(root/'main'/j['key']);j['delay']=.75
        j['seed_offset']=10000*j['index'];j['run_id']=f"{j['scene']}_{j['index']}";jobs.append(j)
    assert len(jobs)==144 and len({j['key'] for j in jobs})==144
    for j in jobs:
        p=socket_path_for_run(j['output']);j['socket_path']=str(p);j['socket_bytes']=validate_socket_path(p)
    assert len({j['socket_path'] for j in jobs})==len(jobs),'Socket hash collision'
    return jobs

def status(root):
    s=read(root/'state.json',{});records=s.get('stages',{})
    complete=read(root/'complete.json',{})
    return dict(state='COMPLETE' if complete.get('report_complete') else 'REPORT_PENDING' if complete else 'INTERRUPTED' if s.get('interrupted') else 'RUNNING' if s else 'NOT_STARTED',
        stages_finished=sum(r.get('state')=='END' for r in records.values()),main_finished=sum(k.startswith('main:') and r.get('state')=='END' for k,r in records.items()),
        main_planned=s.get('main_planned'),current=s.get('current'),pid=s.get('pid'))

def campaign(root):
    p=verify_sources();assert p['status']=='FROZEN','Protocol must be frozen before campaign'
    ready=read(ROOT/'research/results/phase18_preflight/readiness.json',{})
    assert ready.get('passed'),'Stored RTC replay and one excluded RTC smoke must pass before campaign'
    assert sha256_file(Path(__file__).with_name('protocol.json'))==ready['protocol_sha256']
    for name,h in ready['runtime_source_sha256'].items():assert sha256_file(ROOT/name)==h,name
    assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip(),'Tracked edits must be committed'
    jobs=plan_jobs(root);env=clean_env();root.mkdir(parents=True,exist_ok=True)
    if read(root/'complete.json',{}).get('report_complete'):
        print('[campaign] already complete; no execution',flush=True);return
    state=read(root/'state.json');resuming=state is not None
    if state is None:
        assert not any(root.iterdir()),'Unrecognized existing root is preserved'
        state=dict(protocol=p,source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in Path(__file__).parent.glob('*') if f.is_file()},stages={},created_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
        write(root/'plan.json',dict(protocol=p,protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json')),jobs=jobs,git_sha=state['created_git_sha']))
    assert state['protocol']==p
    for n,h in state['source_sha256'].items():assert sha256_file(ROOT/n)==h,n
    state.update(pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],interrupted=False)
    with (root/'journal.jsonl').open('a') as journal:
        def log(event,**details):
            journal.write(json.dumps(dict(event=event,time_ns=time.time_ns(),**details))+'\n');journal.flush();write(root/'state.json',state)
        log('RESUME' if resuming else 'START',completed=len(state['stages']))
        active=None
        def interrupt(*_):
            state['interrupted']=True
            if active is not None and active.poll() is None:
                os.killpg(active.pid,signal.SIGTERM)
                try:active.wait(timeout=45)
                except subprocess.TimeoutExpired:os.killpg(active.pid,signal.SIGKILL);active.wait()
            log('INTERRUPTED',current=state.get('current'));raise KeyboardInterrupt
        signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
        def stage(kind,key,argv,output):
            nonlocal active
            name=kind+':'+key;old=state['stages'].get(name)
            if old and old.get('state')=='END':return old
            if old:
                # A completed artifact can be recovered without rerunning. An
                # incomplete started attempt is terminal technical failure.
                code=0 if (output/'launch_complete.json').exists() else -1
                record={**old,'state':'END','exit_code':code,'resumed_without_retry':True}
            else:
                assert not output.exists(),'No overwrite/retry'
                state['current']=name;state['stages'][name]=dict(state='START',output=str(output));log('STAGE_START',stage=name)
                (root/'logs').mkdir(exist_ok=True)
                with (root/'logs'/f'{kind}_{key}.log').open('x') as stream:
                    active=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                    code=active.wait();active=None
                record=dict(state='END',output=str(output),exit_code=code)
            state['stages'][name]=record;state['current']=None;log('STAGE_END',stage=name,exit_code=record['exit_code'])
            return record
        try:
            maps=p['topomaps'];gate={sc:'PASS' for sc in maps}
            for sc,info in maps.items():
                name='topomap:'+sc
                if name not in state['stages']:
                    state['stages'][name]=dict(state='END',exit_code=0,reused=True,output=info['manifest']);log('TOPOMAP_REUSE',scene=sc,manifest=info['manifest'])
                print(f'[topomap] {sc} reused',flush=True)
            for file in p['gate_metric_files']:
                g=read(file);name='gate:'+g['key']
                if name not in state['stages']:
                    state['stages'][name]=dict(state='END',exit_code=0,reused=True,output=g['output']);log('GATE_REUSE',key=g['key'],source=file)
            print('[gate] Phase17 six PASS results reused; no new gate navigation',flush=True)
            resolved=dict(p,topomaps=maps,execution_git_sha=state['created_git_sha']);write(root/'resolved_protocol.json',resolved)
            def nav(kind,j,manifest):
                output=Path(j['output']);argv=['/usr/bin/python3','-u','-m','nomad_phase18.launch','--mode','navigation','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--delay',str(j['delay']),'--topomap',manifest,'--output',str(output)]
                r=stage(kind,j['key'],argv,output);metric=root/'metrics'/f"{kind}_{j['key']}.json";metric.parent.mkdir(exist_ok=True)
                if metric.exists():return read(metric)
                result=dict(**j,classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False,error=f"Launcher exit {r['exit_code']}")
                if r['exit_code']==0:
                    try:
                        from .metrics import audit
                        result.update(audit(output));result.pop('error',None)
                    except Exception as exc:result['error']=repr(exc)
                write(metric,result);return result
            write(root/'gates.json',gate);passed=list(maps);state['main_planned']=144;log('GATES_REUSED',gate=gate)
            for j in jobs:
                assert j['scene'] in passed,'All three preregistered scenes must remain included'
                r=nav('main',j,maps[j['scene']]['manifest']);print(f"[main] {j['key']} {r['classification']}",flush=True)
            state['current']=None;complete=dict(gates=gate,main_expected=state['main_planned'],complete=True,report_complete=False)
            write(root/'complete.json',complete);log('NAVIGATION_COMPLETE')
            # Report runs in the installed CPU interpreter, never NoMaD's venv.
            command=['/usr/bin/python3','-m','nomad_phase18.report','--run-root',str(root),'--publish']
            state['current']='report';write(root/'state.json',state)
            with (root/'report.log').open('a') as stream:
                active=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                code=active.wait();active=None
                if code:raise RuntimeError(f'Report exit {code}; navigation preserved; resume retries report only')
            complete['report_complete']=True;write(root/'complete.json',complete)
            print('[report] done (committed and pushed)',flush=True)
        finally:state['pid']=None;state['current']=None;write(root/'state.json',state)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);g=ap.add_mutually_exclusive_group();g.add_argument('--status',action='store_true');g.add_argument('--stop',action='store_true');g.add_argument('--dry-run',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(status(root)));return
    if a.stop:
        s=read(root/'state.json',{});pid=s.get('pid');assert pid,'No recorded active campaign'
        assert Path(f'/proc/{pid}/stat').read_text().split()[21]==s['process_token'],'Stale PID'
        assert 'nomad_phase18.campaign' in Path(f'/proc/{pid}/cmdline').read_text();os.kill(pid,signal.SIGTERM);print('Stop requested; raw preserved');return
    if a.dry_run:
        jobs=plan_jobs(root);print(json.dumps(dict(main_max=len(jobs),new_gate_runs=0,new_reference_runs=0,methods=list(METHODS),socket_max_bytes=max(j['socket_bytes'] for j in jobs),navigation_started=0)));return
    with exclusive_batch():campaign(root)
if __name__=='__main__':main()
