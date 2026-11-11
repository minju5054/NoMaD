"""Four CPU workers, eleven starts/input; selected inputs remain chronological per run."""
import hashlib,json,multiprocessing as mp,os,signal,subprocess,time
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase15b.depth import Snapshot
from nomad_phase33p.storage import load_snapshot
from .inputs import HERE,OUT,RUN_ROOT,materialize
from .graph import Graph,solve_start
from .certificate import validate

_CACHE=None;_FIELD=None

def worker(payload):
    global _CACHE,_FIELD
    file=payload['snapshot_file']
    if file!=_CACHE:
        assert sha256_file(file)==payload['snapshot_sha256'];_FIELD=load_snapshot(Snapshot,file);_CACHE=file
    c=payload['state'];graph=Graph([*c['pose'],c['v']],c['omega'],payload['samples'],_FIELD,payload['previous'],c['time_s'])
    return solve_start(graph,payload['index'])

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as f:json.dump(value,f,ensure_ascii=False,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def verify():
    p=json.loads((HERE/'protocol.json').read_text());assert p['status']=='FROZEN'
    for name,digest in p['source_sha256'].items():assert sha256_file(ROOT/name)==digest,name
    assert sha256_file(RUN_ROOT/'inventory.json')==p['inventory_sha256']
    inventory=json.loads((RUN_ROOT/'inventory.json').read_text())
    for name,digest in inventory['input_sha256'].items():assert sha256_file(name)==digest,name
    return p

def type_of(states,controls,B):
    x=np.asarray(states);u=np.asarray(controls);travel=float(np.linalg.norm(np.diff(x[:,:2],axis=0),axis=1).sum());rotation=float(np.abs(np.diff(x[:,2])).sum())
    if travel<=.001:label='제자리회전' if rotation>.001 else '정지'
    elif x[0,3]*u[0,0]<-1e-7:label='감속'
    else:label='전진/이동'
    return dict(type=label,planned_distance_m=travel,planned_rotation_rad=rotation,reverse_included=bool(np.any(x[:,3]<-1e-7)))

def side_of(path,B):
    if path is None:return None
    delta=np.asarray(path)[-1,:2]-np.asarray(B)[:2];lateral=float(delta@[-np.sin(B[2]),np.cos(B[2])])
    return 'LEFT' if lateral>.01 else 'RIGHT' if lateral<-.01 else 'CENTER'

def process(case,previous,pool,heartbeat):
    begin=time.perf_counter();samples=materialize(case);field=load_snapshot(Snapshot,case['snapshot_file'])
    assert sha256_file(case['snapshot_file'])==case['snapshot_sha256']
    basic=dict(case_id=case['case_id'],uid=case['uid'],scene=case['scene'],time_s=case['time_s'],after_box_spawn=case['after_box_spawn'],
        found=False,previous_case=previous['case_id'] if previous else None,actual_command_state=case['actual_command_state'],actual_side=side_of(case['actual_path'],case['pose']))
    x0=np.array([*case['pose'],case['v']]);low=field.origin;high=field.origin+(np.array(field.values.shape[::-1])-1)*field.h
    if np.any(x0[:2]<low) or np.any(x0[:2]>=high):return dict(basic,reason='INITIAL_STATE_OUTSIDE_MAP',results=[],wall_s=time.perf_counter()-begin)
    cb=float(field.query(x0[None,:2])[0][0])
    if cb<.025-1e-7 or abs(case['v'])>.3+1e-7 or abs(case['omega'])>.4+1e-7:
        return dict(basic,reason='FIXED_INITIAL_STATE_HARD_INFEASIBLE',initial_clearance_m=cb,results=[],wall_s=time.perf_counter()-begin)
    payload=dict(state={k:case[k] for k in ('pose','v','omega','time_s')},samples=samples.tolist(),previous=previous,
        snapshot_file=case['snapshot_file'],snapshot_sha256=case['snapshot_sha256'])
    t0=time.perf_counter();pending={pool.submit(worker,dict(payload,index=i)):i for i in range(11)};results=[]
    while pending:
        done,_=wait(pending,timeout=1,return_when=FIRST_COMPLETED);heartbeat()
        if time.perf_counter()-t0>300:raise TimeoutError('Input watchdog300s; technical failure,not NO_SOLUTION;resume reruns this unfinished input')
        for future in done:
            result=future.result();assert result['start_index']==pending.pop(future);results.append(result)
    solve_wall=time.perf_counter()-t0;results.sort(key=lambda r:r['start_index']);eligible=sorted([r for r in results if r['hard_feasible']],key=lambda r:(r['objective'],r['start_index']))
    selected=None;validation_start=time.perf_counter()
    for result in eligible:
        result['ec']=validate(case,result,field)
        if result['ec']['passed']:selected=result;break
    elapsed=time.perf_counter()-begin
    out=dict(basic,reason='EC_PASS' if selected else 'NO_EC_VALID_SOLUTION',initial_clearance_m=cb,results=results,
        graph_hard_feasible_starts=len(eligible),solve_job_wall_s=solve_wall,ec_wall_s=time.perf_counter()-validation_start,wall_s=elapsed)
    if selected:
        out.update(found=True,selected=selected['start_index'],states=selected['states'],controls=selected['controls'],objective=selected['objective'],
            active_candidate=selected['active_candidate'],ec=selected['ec'],solver_converged=selected['solver_success'],side=side_of(selected['states'],case['pose']),
            **type_of(selected['states'],selected['controls'],case['pose']))
    return out

def status():
    file=RUN_ROOT/'state.json';s=json.loads(file.read_text()) if file.exists() else dict(status='NOT_STARTED')
    live=False
    if s.get('pid'):
        try:live=Path(f"/proc/{s['pid']}/stat").read_text().split()[21]==s.get('process_token')
        except (FileNotFoundError,ProcessLookupError):pass
    if s.get('status')=='RUNNING' and not live:s['status']='ABNORMAL_EXIT'
    return s

def run():
    import fcntl
    p=verify();inventory=json.loads((RUN_ROOT/'inventory.json').read_text());cases=inventory['cases'];protocol_hash=sha256_file(HERE/'protocol.json')
    RUN_ROOT.mkdir(exist_ok=True,parents=True)
    with (RUN_ROOT/'analysis.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=dict(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],total=len(cases),completed=0,usable=sum(c['status']=='READY' for c in cases),
            protocol_sha256=protocol_hash,current=None,started=time.time())
        last=[0.];counts={};previous=None;uid=None;pool=ProcessPoolExecutor(max_workers=4,mp_context=mp.get_context('spawn'))
        def heartbeat(force=False):
            if force or time.monotonic()-last[0]>=60:
                last[0]=time.monotonic();state['updated']=time.time();atomic(RUN_ROOT/'state.json',state)
                print(f"[progress] {state['completed']}/{state['total']} current={state['current']} scenes={json.dumps(counts)}",flush=True)
        def stop(*_):raise KeyboardInterrupt('Offline study interrupted;finished inputs preserved')
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        try:
            for case in cases:
                if case['uid']!=uid:uid=case['uid'];previous=None
                state['current']=case['case_id'];file=RUN_ROOT/'cache'/f"{case['case_id']}.json"
                if file.exists():
                    r=json.loads(file.read_text());assert r['protocol_sha256']==protocol_hash and r['case_id']==case['case_id']
                    assert r.get('previous_case')==(previous['case_id'] if previous and case['status']=='READY' else None)
                else:
                    r=process(case,previous,pool,heartbeat) if case['status']=='READY' else dict(case_id=case['case_id'],uid=case['uid'],scene=case['scene'],reason=case['status'],found=False,previous_case=None,wall_s=None,results=[])
                    r['protocol_sha256']=protocol_hash;atomic(file,r)
                previous=dict(case_id=case['case_id'],time_s=case['time_s'],states=r['states']) if r['found'] else None
                entry=counts.setdefault(case['scene'],dict(completed=0,found=0));entry['completed']+=1;entry['found']+=int(r['found'])
                state['completed']+=1;atomic(RUN_ROOT/'intermediate'/f"{case['scene']}.json",entry);heartbeat()
            state['current']='report';heartbeat(True)
            subprocess.run(['/usr/bin/python3','-m','nomad_ugraph.report','--publish'],cwd=ROOT,check=True,env=dict(os.environ,PYTHONPATH='research'))
            state.update(status='COMPLETE',current=None)
        except BaseException as exc:
            state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));raise
        finally:
            if state['status']!='COMPLETE':
                for proc in list((getattr(pool,'_processes',None) or {}).values()):proc.terminate()
            pool.shutdown(wait=True,cancel_futures=True);state['pid']=None;heartbeat(True)

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(status()));return
    p=verify()
    if a.dry_run:
        m=json.loads((RUN_ROOT/'inventory.json').read_text());print(json.dumps(dict(selected=len(m['cases']),usable=sum(c['status']=='READY' for c in m['cases']),solver_starts_max=11*sum(c['status']=='READY' for c in m['cases']),simulations=0)));return
    run()
if __name__=='__main__':main()
