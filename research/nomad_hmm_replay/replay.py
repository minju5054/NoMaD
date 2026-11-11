"""Resumable saved-log replay. No simulator/NoMaD import or new navigation."""
import argparse,fcntl,hashlib,json,os,signal,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from nomad_phase26.storage import atomic_json
from nomad_isaac.common import ROOT,sha256_file
from .data import HERE,OUT,RUN_ROOT,discover,load
from .filter import Replay,VARIANTS

def verify():
    p=json.loads((HERE/'protocol.json').read_text());assert p['status']=='FROZEN'
    for f,h in {**p['source_sha256'],**p['frozen_sources'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return sha256_file(HERE/'protocol.json')
def fingerprint(item,protocol_hash):
    return hashlib.sha256(json.dumps(dict(inputs=item['input_sha256'],protocol=protocol_hash),sort_keys=True).encode()).hexdigest()
def process(item,heartbeat=None):
    events,n,spacing,stop,missing=load(item);filters={v:Replay(n,spacing,v) for v in VARIANTS};out=[]
    for e in events:
        for variant,f in filters.items():
            chosen,detail=f.step(e['ids'],e['distances'],e['odometry_xy'],e['odometry_total_m'])
            out.append(dict(uid=item['uid'],phase=item['phase'],scene=item['scene'],seed=item['seed'],method=item['method'],
                variant=variant,inference_id=e['id'],observation_s=e['time_s'],map_node=chosen,true_node=e['true_node'],goal_node=e['goal_node'],
                abs_error=abs(chosen-e['true_node']),signed_error=chosen-e['true_node'],false_goal=chosen==e['goal_node'] and e['true_node']<e['goal_node']-2,
                declares_goal=chosen==e['goal_node'],logged_map=e['logged_map'],logged_width=e['logged_width'],
                truth_outside_window=e['truth_outside_window'],terminal_drained=e['terminal_drained'],valid_delivery=e['valid_delivery'],
                declared_stop_inference=e['declared_stop_inference'],truth_source=e['truth_source'],**detail))
        if heartbeat:heartbeat(e['id'])
    declarations=[]
    if stop:
        for variant in VARIANTS:
            e=next((r for r in out if r['variant']==variant and r['inference_id']==stop['id']),None)
            declarations.append(dict(uid=item['uid'],phase=item['phase'],scene=item['scene'],seed=item['seed'],method=item['method'],variant=variant,
                original_classification=item['row'].get('classification'),original_wrong_stop=bool(item['row'].get('wrong_stop')),original_success=bool(item['row'].get('success')),
                declaration_id=stop['id'],declaration_s=stop['simulation_time_s'],original_stop_distance_m=item['row'].get('stop_distance_m'),
                replay_map=e['map_node'] if e else None,goal_node=stop['goal_node'],would_declare=e['declares_goal'] if e else None,
                true_node_at_observation=e['true_node'] if e else None,status='MATCHED' if e else 'DECLARATION_INFERENCE_NOT_MEASURED'))
    return dict(uid=item['uid'],phase=item['phase'],scene=item['scene'],method=item['method'],seed=item['seed'],technical_validation=item['row']['technical_validation'],
        input_events=len(events),missing_events=missing,node_count=n,ell_m=spacing,rows=out,declarations=declarations)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    if a.status:
        state=json.loads((RUN_ROOT/'state.json').read_text()) if (RUN_ROOT/'state.json').exists() else dict(status='NOT_STARTED')
        if state.get('status') in ('RUNNING','REPORTING') and state.get('pid'):
            try:alive=Path(f"/proc/{state['pid']}/stat").read_text().split()[21]==state.get('process_token')
            except (FileNotFoundError,ProcessLookupError):alive=False
            if not alive:state['status']='ABNORMAL_EXIT'
        print(json.dumps(state));return
    protocol_hash=verify();items,coverage=discover()
    if a.dry_run:
        print(json.dumps(dict(expected=len(coverage),available=len(items),cohorts={p:sum(x['phase']==p and x['status']=='AVAILABLE' for x in coverage) for p in sorted({x['phase'] for x in coverage})},
            simulations=0,replayed_runs=0,protocol_sha256=protocol_hash)));return
    RUN_ROOT.mkdir(parents=True,exist_ok=True);cache=RUN_ROOT/'cache';cache.mkdir(exist_ok=True)
    with (RUN_ROOT/'analysis.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=dict(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],protocol_sha256=protocol_hash,available=len(items),expected=len(coverage),completed=0,current=None,started_utc=datetime.now(timezone.utc).isoformat())
        atomic_json(RUN_ROOT/'inventory.json',dict(protocol_sha256=protocol_hash,items=items,coverage=coverage))
        def stop(*_):raise KeyboardInterrupt('Replay interrupted')
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        last_log=time.monotonic()
        def heartbeat(inference_id=None):
            nonlocal last_log
            if time.monotonic()-last_log>=60:
                state['inference_id']=inference_id;atomic_json(RUN_ROOT/'state.json',state)
                print('[progress]',state['completed'],'/',len(items),state['current'],'inference',inference_id,flush=True);last_log=time.monotonic()
        try:
            for item in items:
                state['current']=item['uid'];atomic_json(RUN_ROOT/'state.json',state)
                target=cache/(hashlib.sha256(item['uid'].encode()).hexdigest()[:20]+'.json');key=fingerprint(item,protocol_hash)
                if target.exists():
                    result=json.loads(target.read_text());assert result['fingerprint']==key,'Inputs/protocol changed: '+item['uid'];mode='cached'
                else:
                    result=process(item,heartbeat)
                    for file,h in item['input_sha256'].items():assert sha256_file(file)==h,'Input changed during replay: '+file
                    result.update(fingerprint=key,input_sha256=item['input_sha256']);atomic_json(target,result);mode='done'
                state['completed']+=1;atomic_json(RUN_ROOT/'state.json',state)
                atomic_json(RUN_ROOT/'progress.json',dict(completed=state['completed'],available=len(items),last=item['uid']))
                print('[run]',state['completed'],'/',len(items),mode,item['uid'],result['input_events'],'inferences',flush=True);heartbeat()
            state.update(status='REPORTING',current=None);atomic_json(RUN_ROOT/'state.json',state)
            env=dict(os.environ,PYTHONPATH='research')
            subprocess.run(['/usr/bin/python3','-u','-m','nomad_hmm_replay.report','--publish'],cwd=ROOT,env=env,check=True)
            state.update(status='COMPLETE_AVAILABLE' if len(items)<len(coverage) else 'COMPLETE',current=None)
        except BaseException as exc:
            state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));raise
        finally:state.update(pid=None);atomic_json(RUN_ROOT/'state.json',state)
if __name__=='__main__':main()
