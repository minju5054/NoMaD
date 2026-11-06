"""One simulator, persistent attempts, stage gates, six-and-half-hour cutoff."""
import argparse,json,os,re,shutil,signal,subprocess,time
from pathlib import Path
from nomad_phase0.s0_batch import exclusive_batch
from nomad_phase26.launch import environment
from nomad_phase26.storage import atomic_json
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from .config import ROOT,HERE,OUT,RUN_ROOT,protocol,verify
from .report import read,generate,publish,dev_gate,baselines
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);atomic_json(path,value)
def signature(out):
    text=(out/'async_thread_failure.txt').read_text() if (out/'async_thread_failure.txt').exists() else json.dumps(read(out/'FAILED.json',read(out/'launch_failure.json',{})))
    for name in ('simulator.log','worker.log','phase29_worker.log'):
        if (out/name).exists():
            lines=(out/name).read_text(errors='replace').splitlines();errors=[x for x in lines if any(k in x for k in ('Error:','AssertionError','Exception:'))]
            if errors:text+=' '+errors[-1]
    return re.sub(r'\b\d+\b','#',text[-1200:]) or 'LAUNCH_FAILURE_NO_DETAIL'
def stop(state,label,reason):
    state.update(label=label,reason=reason,status=label,current=None);write(RUN_ROOT/'state.json',state);generate(label=label,reason=reason);publish(state['stage']+' '+label)
def run_job(stage,row,state,p):
    key=f"{stage}_{row['scene']}_{row['index']}_{row['method']}";metric=RUN_ROOT/'metrics'/(key+'.json')
    if metric.exists():return read(metric)
    for attempt in (1,2):
        output=RUN_ROOT/stage/f"{row['scene']}_{row['index']}_{row['method']}"/f'attempt{attempt}';saved=RUN_ROOT/'attempt_metrics'/f'{key}_{attempt}.json'
        was_saved=saved.exists()
        if was_saved:r=read(saved)
        else:
            if time.time()>=p['deadline_epoch']:stop(state,'PARTIAL','6.5h deadline; no next run started');return None
            if shutil.disk_usage(ROOT).free<p['disk_min_bytes']:stop(state,'STOP_BLOCKED','Available disk below30GB');return None
            state.update(current=key+f':{attempt}');write(RUN_ROOT/'state.json',state)
            if output.exists():code=0 if (output/'launch_complete.json').exists() else -1
            else:
                log=RUN_ROOT/'logs'/f'{key}_{attempt}.log';log.parent.mkdir(exist_ok=True)
                cmd=['/usr/bin/python3','-u','-m','nomad_phase29.launch','--scene',row['scene'],'--method',row['method'],'--index',str(row['index']),'--output',str(output)]
                with log.open('x') as f:
                    child=subprocess.Popen(cmd,cwd=ROOT,env=environment(),stdout=f,stderr=subprocess.STDOUT,start_new_session=True);state['child_pid']=child.pid;write(RUN_ROOT/'state.json',state)
                    try:code=child.wait()
                    finally:
                        if child.poll() is None:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=60)
                        state.pop('child_pid',None)
            r=dict(row,stage=stage,key=key,attempt=attempt,output=str(output),technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False,exit_code=code)
            if code==0:
                try:
                    from .metrics import audit
                    r.update(audit(output))
                except Exception as exc:r['error']=repr(exc)
            if r['technical_validation']!='PASS':r['signature']=signature(output)
            write(saved,r)
        print(f"[{stage}] {key} attempt{attempt} {r['technical_validation']} {r['classification']}",flush=True)
        if r['technical_validation']=='PASS':write(metric,r);return r
        if 'counted' not in r:
            signatures=state.setdefault('error_counts',{});s=r['signature'];signatures[s]=signatures.get(s,0)+1;r['counted']=True;write(saved,r);write(RUN_ROOT/'state.json',state)
        if state['error_counts'][r['signature']]>=2:
            write(metric,r);stop(state,'STOP_BLOCKED','Same technical error occurred twice: '+r['signature']);return None
        if stage=='smoke' and attempt==1 and not was_saved:
            state.update(label='PARTIAL',reason='Inspect technical smoke failure before one permitted retry',status='NEEDS_TECHNICAL_FIX');write(RUN_ROOT/'state.json',state);generate();publish('smoke technical failure preserved');return None
    write(metric,r);return r
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(read(RUN_ROOT/'state.json',dict(status='NOT_STARTED'))));return
    p=verify()
    for stage in ('smoke','dev','confirm'):
        for r in p[stage]:
            for attempt in (1,2):assert validate_socket_path(socket_path_for_run(RUN_ROOT/stage/f"{r['scene']}_{r['index']}_{r['method']}"/f'attempt{attempt}'))<100
    if a.dry_run:print(json.dumps(dict(smoke=2,dev=20,conditional_confirm=60,remaining_s=p['deadline_epoch']-time.time(),free_GB=shutil.disk_usage(ROOT).free/1e9,navigation_started=0)));return
    with exclusive_batch():
        RUN_ROOT.mkdir(exist_ok=True);state=read(RUN_ROOT/'state.json',dict(stage='smoke',completed_stages=[],error_counts={}))
        if state.get('status') in ('STOP_BLOCKED','STOP_DEV_FAIL','COMPLETE'):print('terminal',state['status']);return
        state.update(pid=os.getpid(),status='RUNNING')
        def interrupted(*_):raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        try:
            for stage in ('smoke','dev','confirm'):
                if stage in state['completed_stages']:continue
                state['stage']=stage;write(RUN_ROOT/'state.json',state)
                for row in p[stage]:
                    if run_job(stage,row,state,p) is None:return
                    if time.time()>=p['deadline_epoch']:stop(state,'PARTIAL','6.5h deadline reached; active run finished, remaining matrix resumable');return
                state['completed_stages'].append(stage);write(RUN_ROOT/'state.json',state)
                generate(label='PARTIAL',reason=stage+' complete; next registered stage')
                publish(stage+' complete')
                if stage=='dev':
                    gate=dev_gate([read(f) for f in (RUN_ROOT/'metrics').glob('dev_*.json')],baselines())
                    if not gate['passed']:stop(state,'STOP_DEV_FAIL','Dev gate failed: '+json.dumps(gate['checks']));return
                    # Freeze existing preregistered matrix, no parameter changes.
                    write(HERE/'confirm_frozen.json',dict(status='FROZEN',frozen_at_epoch=time.time(),protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest(),matrix=p['confirm'],dev_gate=gate));publish('confirm FROZEN')
            state.update(status='COMPLETE',reason='All registered stages complete',current=None);write(RUN_ROOT/'state.json',state);generate();publish('final')
        except BaseException as exc:
            state.update(status='INTERRUPTED',label='PARTIAL',reason=repr(exc));write(RUN_ROOT/'state.json',state);generate();raise
        finally:state['pid']=None;write(RUN_ROOT/'state.json',state)
if __name__=='__main__':main()
