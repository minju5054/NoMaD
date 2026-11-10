"""Two offline analyses, cached by frozen analysis protocol and input hashes."""
import argparse,json,os,time,hashlib,multiprocessing as mp
from pathlib import Path
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase32o.evaluate import save,csvout
from .inputs import Run,datasets,HASHES,register,read
from .rollout import original,certify
from . import fast
from .graph import solve_event
from nomad_phase33p.storage import load_snapshot
from nomad_phase15b.depth import Snapshot

OUT=ROOT/'research/results/phase52ec';HERE=Path(__file__).parent

def registered_rules():
    return dict(phase='52-EC-OFFLINE',input_phases=['phase47c','phase52p'],expected_runs=100,
        start='B=recorded EC start actual pose;recorded actual v,w;exact check snapshot only;missing maps excluded with counts',
        termination='Brake request at earlier path endpoint recognition or2.0s;latched stop_command until v=0,w=0',
        clock='72Hz integration,9Hz control. Continuation keeps absolute phase;2s brake request applied at next9Hz tick (0 or4 extra ticks on these logs),all held-motion ticks checked',
        replay='Original INSTALL checks rebuild fresh frozen NA profile;continuation restores installed generation and recorded control-state evolution before check;regression matches pass,duration,endpoint,clearance<=1e-6m',
        tail_comparison='All recorded checks;confirmed PASS->REJECT requires original replay match. Mismatches separated,not claimed as tail effects',
        graph='Reduced SE(2) execution graph:14 XY variables (B+7 future points);all72Hz SE(2) states eliminated through frozen PP/SP integrate_se2 equality factors;no independent yaw/time variables',
        graph_reference='Each of8 current stored NoMaD candidates separately:project B,connect B to suffix,re-sample8 arc-length points;B fixed;no0.25m short cutoff,degenerate suffix reported',
        objective='sum_i ||p_i-q_candidate_i||^2 only;unit weight,no extra sigma or tuning',
        bounds='Each future XY coordinate within +/-0.75m of its own initial reference',
        execution_constraint='Minimum continuous circular-footprint clearance on PP/SP72Hz trajectory including braking tail >=0.025m;terminal v=w=0 by construction',
        graph_clock='New-path INSTALL EC semantics:initial PP control at t=0,then9Hz;actual initial pose/v/w from check. No replanning delay,NoMaD regeneration or depth update simulated',
        optimizer=dict(method='SLSQP',maxiter=100,ftol=1e-8,objective_gradient='analytic',constraint_gradient='2-point finite difference',eps_m=1e-6),
        acceleration='Compiled arithmetic mirror with exact arc/site clearance clipped only above+0.075m;no fast-math;geometry-equivalent .025 feasible set;tested vs Python',
        acceptance='Solver success + numerical violation<=1e-7 + independent Python braking-tail EC >=.025 and terminal stop;reject independent failures',
        infeasible_boundary='If fixed initial footprint itself fails exact.025 clearance,all8 starts proven infeasible without SLSQP;count as no solution and record reason',
        dedup='Unique(run,tick,pose,v,w,snapshot frame/file,current candidate bank id,cap). Original REJECT only;full-speed inputs solved once;0.1m/s unique inputs counted but never solved',
        candidate_selection='Lowest objective among independently verified8 solutions,tie sample index. Report original-candidate tail PASS and solved-only rescue separately',
        timing='Four independent event workers,BLAS1. Per-event time includes8 starts and independent checks;map loading/startup separate. Per-start timing also reported',
        limitations='Same historical data;offline feasibility only. Distance-only objective can shorten/stop or rotate without progress:travel and <=5cm motion reported. No oracle used for solve/certificate',
        no_simulation=True,no_new_inference=True,no_parameter_tuning=True)

def freeze():
    target=OUT/'protocol.json';rules=registered_rules();sources={str(p.relative_to(ROOT)):sha256_file(p) for p in HERE.iterdir() if p.suffix in ('.py','.cpp')}
    if target.exists():
        previous=read(target);assert previous['rules']==rules and previous['source_sha256']==sources,'Analysis code/definitions changed after freeze'
        return previous
    p=dict(status='FROZEN',rules=rules,source_sha256=sources);save(target,p);return p

def uidfile(run):return run.uid.replace('/','_')

def replay_run(phase,row):
    run=Run(phase,row);records=[];groups={};slow={};counts=Counter()
    for check in run.checks:
        m=run.metadata(check);counts['recorded_checks']+=1
        bank=run.bank(check);path=run.paths.get(check['path_sha256']);field=run.field(check)
        missing=None
        if field is None:missing='MISSING_EXACT_MAP'
        elif path is None:missing='UNRESOLVED_PATH'
        m.update(status=missing or 'ASSESSED',bank_id=bank['id'] if bank else None,logged_clearance_m=check.get('clearance_m'),logged_duration_s=check.get('duration_s'))
        if missing:counts[missing]+=1
        else:
            try:
                controller=run.controller(check);old=original(check,path,field,controller)
                new=certify(check['pose'],check['actual_vw'],path,field,check['speed_cap_m_s'],controller,check['check_tick'])
                clearance_match=(old.get('clearance_m') is None and check.get('clearance_m') is None) or (old.get('clearance_m') is not None and check.get('clearance_m') is not None and abs(old['clearance_m']-check['clearance_m'])<=1e-6)
                match=bool(old['passed']==check['passed'] and old['endpoint_reached']==check['endpoint_reached'] and abs(old['duration_s']-check['duration_s'])<1e-9 and clearance_match)
                p=XYPath(path);s,_=p.project(check['pose'][:2])
                m.update(replay_match=match,old_replay_passed=old['passed'],old_replay_clearance_m=old.get('clearance_m'),
                    new_passed=new['passed'],new_clearance_m=new.get('clearance_m'),pass_to_reject=bool(match and check['passed'] and not new['passed']),
                    unverified_pass_to_reject=bool(not match and check['passed'] and not new['passed']),
                    remaining_length_m=float(p.s[-1]-s),stop_reason=new['stop_reason'],new_duration_s=new['duration_s'],
                    brake_request_s=new['brake_request_s'],brake_start_s=new['brake_start_s'],braking_s=new['braking_s'],control_rounding_ticks=new['control_rounding_ticks'])
            except (ValueError,AssertionError) as exc:
                m.update(status='REPLAY_ERROR',error=str(exc));counts['REPLAY_ERROR']+=1
        records.append(m)
        if check['passed']:continue
        unique=(check['check_tick'],tuple(check['pose']),tuple(check['actual_vw']),check['snapshot']['frame_id'],check['snapshot']['file'],bank['id'] if bank else None)
        store=slow if check['speed_cap_m_s']==.1 else groups
        if unique not in store:
            job=dict(m,pose=check['pose'],vw=check['actual_vw'],check_ids=[],raw_record_count=0,snapshot=check['snapshot'],
                candidates=bank['worlds'].tolist() if bank else None,graph_eligible=field is not None and bank is not None,
                graph_exclusion='MISSING_EXACT_MAP' if field is None else 'NO_STORED_CANDIDATE_BANK' if bank is None else None)
            job['event_id']=hashlib.sha256(repr((run.uid,unique,check['speed_cap_m_s'])).encode()).hexdigest()[:20];store[unique]=job
        store[unique]['check_ids'].append(check['check_id']);store[unique]['raw_record_count']+=1
    result=dict(uid=run.uid,records=records,full_speed_groups=list(groups.values()),slow_groups=list(slow.values()),counts=dict(counts),
        input_hashes={p:h for p,h in HASHES.items() if Path(p).is_relative_to(run.root)})
    return result

_cached_file=None;_field=None

def graph_worker_init():fast.library()
def solve_one(job):
    global _cached_file,_field
    start=time.perf_counter();file=job['snapshot']['file']
    if file!=_cached_file:_field=load_snapshot(Snapshot,file);_cached_file=file
    loaded=time.perf_counter();r=solve_event(job,_field);r.update(map_load_s=loaded-start,total_wall_s=time.perf_counter()-start,
        source_check_ids=job['check_ids'],source_raw_record_count=job['raw_record_count'],bank_id=job['bank_id'],uid=job['uid'])
    return r

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['replay','graph','all'],default='all');ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
    assert 1<=a.workers<=4;freeze();OUT.mkdir(parents=True,exist_ok=True);(OUT/'replay').mkdir(exist_ok=True);(OUT/'graph').mkdir(exist_ok=True)
    checks=[];jobs=[];slow=[];start=time.perf_counter()
    for i,(phase,row) in enumerate(datasets(),1):
        uid=f"{phase}/{row['scene']}/{row['index']}/{row['method']}";file=OUT/'replay'/f"{uid.replace('/','_')}.json"
        if file.exists():r=json.loads(file.read_text());HASHES.update(r['input_hashes'])
        elif a.stage=='graph':raise FileNotFoundError(file)
        else:
            try:r=replay_run(phase,row);save(file,r)
            except BaseException as exc:save(OUT/'status.json',dict(status='FAILED_REPLAY',uid=uid,error=repr(exc)));raise
        checks.extend(r['records']);jobs.extend(r['full_speed_groups']);slow.extend(r['slow_groups'])
        if i%5==0:print(f'[EC replay] {i}/100,checks={len(checks)},elapsed={time.perf_counter()-start:.1f}s',flush=True)
    save(OUT/'graph_inputs.json',jobs);save(OUT/'slow_inputs_count_only.json',[{k:v for k,v in j.items() if k!='candidates'} for j in slow]);csvout(OUT/'ec_checks.csv',checks)
    save(OUT/'input_hashes.json',HASHES)
    if a.stage=='replay':return
    pending=[j for j in jobs if j['graph_eligible'] and not (OUT/'graph'/f"{j['event_id']}.json").exists()];fast.library()
    ctx=mp.get_context('spawn');done=0
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=ctx,initializer=graph_worker_init) as pool:
        for j,result in zip(pending,pool.map(solve_one,pending)):
            save(OUT/'graph'/f"{j['event_id']}.json",result);done+=1
            if done%10==0 or done==len(pending):print(f'[graph] {done}/{len(pending)},elapsed={time.perf_counter()-start:.1f}s',flush=True)
            save(OUT/'status.json',dict(status='GRAPH',done=done,pending=len(pending),elapsed_s=time.perf_counter()-start))
    save(OUT/'status.json',dict(status='COMPLETE',full_speed_unique=len(jobs),slow_unique_not_solved=len(slow),graph_eligible=sum(j['graph_eligible'] for j in jobs),
        total_ec_checks=len(checks),elapsed_s=time.perf_counter()-start,simulations=0,new_inference=0))

if __name__=='__main__':main()
