"""Fit/freeze on calibration only, then five-variant held-out replay; resumable."""
import argparse,fcntl,hashlib,json,os,signal,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.storage import atomic_json
from nomad_phase40p.launch import bind
from nomad_hmm_replay.replay import process as frozen_process
from .data import HERE,OUT,RUN_ROOT,discover,load
from .calibration import contributions,fit
from .filter import Filter,VARIANTS

def verify():
    p=json.loads((HERE/'protocol.json').read_text());assert p['status']=='FROZEN'
    for f,h in {**p['source_sha256'],**p['frozen_sources'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return sha256_file(HERE/'protocol.json')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def fingerprint(item,protocol,model=None):return digest(dict(inputs=item['input_sha256'],protocol=protocol,model=model))
def cache_path(root,item):return Path(root)/(hashlib.sha256(item['uid'].encode()).hexdigest()[:20]+'.json')

def delays(rows):
    output=[]
    for variant in VARIANTS:
        events=sorted([r for r in rows if r['variant']==variant],key=lambda r:r['inference_id'])
        reached=next((r for r in events if r['true_node']==r['goal_node']),None)
        first=next((r for r in events if r['map_node']==r['goal_node']),None)
        after=next((r for r in events if reached and r['inference_id']>=reached['inference_id'] and r['map_node']==r['goal_node']),None)
        early=bool(reached and first and first['inference_id']<reached['inference_id'])
        row=dict(variant=variant,true_goal_reached=reached is not None,true_goal_inference_id=reached['inference_id'] if reached else None,
            first_MAP_goal_id=first['inference_id'] if first else None,first_MAP_after_true_goal_id=after['inference_id'] if after else None,
            delay_after_true_inferences=after['inference_id']-reached['inference_id'] if after else None,
            right_censored_after_true=bool(reached and after is None),early_negative_delay=early,
            signed_first_MAP_delay=first['inference_id']-reached['inference_id'] if first and reached else None,
            status='NO_TRUE_GOAL_OBSERVATION' if reached is None else 'RIGHT_CENSORED' if after is None else 'OBSERVED',
            censored_followup_inferences=events[-1]['inference_id']-reached['inference_id'] if reached and after is None else None)
        if events:row.update({k:events[0][k] for k in ('uid','phase','scene','seed','method')})
        output.append(row)
    return output

def evaluate(item,model,heartbeat=None):
    assert item['split']=='EVAL'
    events,xy,spacing,stop,missing=load(item)
    # The frozen replay loop supplies truth/error/declaration bookkeeping; the
    # filter never receives true_node or saved outcome labels.
    loader=lambda unused:(events,len(xy),spacing,stop,missing)
    factory=lambda n,ell,variant:Filter(xy,ell,variant,model)
    result=bind(frozen_process,load=loader,Replay=factory,VARIANTS=VARIANTS)(item,heartbeat)
    context={k:item[k] for k in ('uid','phase','scene','seed','method')}
    result['delays']=[dict(context,**{k:v for k,v in r.items() if k not in context}) for r in delays(result['rows'])];return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    if a.status:
        state=json.loads((RUN_ROOT/'state.json').read_text()) if (RUN_ROOT/'state.json').exists() else dict(status='NOT_STARTED')
        if state.get('status') in ('CALIBRATING','EVALUATING','REPORTING') and state.get('pid'):
            try:alive=Path(f"/proc/{state['pid']}/stat").read_text().split()[21]==state.get('process_token')
            except (FileNotFoundError,ProcessLookupError):alive=False
            if not alive:state['status']='ABNORMAL_EXIT'
        print(json.dumps(state));return
    protocol=verify();groups,coverage=discover()
    if a.dry_run:
        print(json.dumps(dict(calibration_available=len(groups['CAL']),evaluation_available=len(groups['EVAL']),
            calibration_expected=sum(x['split']=='CAL' for x in coverage),evaluation_expected=sum(x['split']=='EVAL' for x in coverage),
            simulations=0,real_replays=0,calibration_fits=0,protocol_sha256=protocol)));return
    RUN_ROOT.mkdir(parents=True,exist_ok=True)
    with (RUN_ROOT/'analysis.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=dict(status='CALIBRATING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],current=None,completed_cal=0,completed_eval=0,
            protocol_sha256=protocol,started_utc=datetime.now(timezone.utc).isoformat())
        inventory=dict(groups=groups,coverage=coverage,protocol_sha256=protocol);atomic_json(RUN_ROOT/'inventory.json',inventory)
        def stop(*_):raise KeyboardInterrupt('Interrupted')
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);last_log=time.monotonic()
        def heartbeat(inference_id=None):
            nonlocal last_log
            if time.monotonic()-last_log>=60:
                state['inference_id']=inference_id;atomic_json(RUN_ROOT/'state.json',state)
                print('[progress]',state['status'],state['completed_cal'],state['completed_eval'],state['current'],inference_id,flush=True);last_log=time.monotonic()
        try:
            cal_cache=RUN_ROOT/'cal_cache';cal_cache.mkdir(exist_ok=True);parts=[]
            for item in groups['CAL']:
                state['current']=item['uid'];atomic_json(RUN_ROOT/'state.json',state)
                path=cache_path(cal_cache,item);key=fingerprint(item,protocol)
                if path.exists():part=json.loads(path.read_text());assert part['fingerprint']==key,'Calibration input changed'
                else:
                    part=contributions(item,heartbeat)
                    for file,h in item['input_sha256'].items():assert sha256_file(file)==h,'Input changed: '+file
                    part['fingerprint']=key;atomic_json(path,part)
                parts.append(part);state['completed_cal']+=1;atomic_json(RUN_ROOT/'state.json',state)
                print('[cal]',state['completed_cal'],'/',len(groups['CAL']),item['uid'],flush=True)
            corpus=digest([dict(uid=p['uid'],fingerprint=p['fingerprint']) for p in parts]);model_path=RUN_ROOT/'calibration.json'
            if model_path.exists():
                model=json.loads(model_path.read_text());assert model['training_fingerprint']==corpus,'Frozen calibration corpus changed; use a new analysis root'
                assert model['protocol_sha256']==protocol
            else:
                model=fit(parts);model.update(training_fingerprint=corpus,protocol_sha256=protocol,frozen_at_utc=datetime.now(timezone.utc).isoformat(),frozen_before_evaluation=True)
                atomic_json(model_path,model)
            model_hash=sha256_file(model_path);state.update(status='EVALUATING',model_sha256=model_hash,evaluation_started_utc=datetime.now(timezone.utc).isoformat())
            atomic_json(RUN_ROOT/'state.json',state);eval_cache=RUN_ROOT/'eval_cache';eval_cache.mkdir(exist_ok=True)
            for item in groups['EVAL']:
                state['current']=item['uid'];atomic_json(RUN_ROOT/'state.json',state);path=cache_path(eval_cache,item);key=fingerprint(item,protocol,model_hash)
                if path.exists():result=json.loads(path.read_text());assert result['fingerprint']==key,'Evaluation input/model changed'
                else:
                    result=evaluate(item,model,heartbeat)
                    for file,h in item['input_sha256'].items():assert sha256_file(file)==h,'Input changed: '+file
                    result.update(fingerprint=key,input_sha256=item['input_sha256']);atomic_json(path,result)
                state['completed_eval']+=1;atomic_json(RUN_ROOT/'state.json',state)
                print('[eval]',state['completed_eval'],'/',len(groups['EVAL']),item['uid'],flush=True)
            state.update(status='REPORTING',current=None);atomic_json(RUN_ROOT/'state.json',state)
            subprocess.run(['/usr/bin/python3','-u','-m','nomad_loc_v2.report','--publish'],cwd=ROOT,env=dict(os.environ,PYTHONPATH='research'),check=True)
            state.update(status='COMPLETE' if len(groups['CAL'])+len(groups['EVAL'])==len(coverage) else 'COMPLETE_AVAILABLE_ONLY')
        except BaseException as exc:
            state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));raise
        finally:state.update(pid=None);atomic_json(RUN_ROOT/'state.json',state)
if __name__=='__main__':main()
