"""Resumable offline sequence: training -> frozen commit -> evaluation -> report."""
import argparse,itertools,json,multiprocessing as mp,subprocess,time,os,fcntl,hashlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase19r.evaluate import clean,csv_write
from nomad_phase20d.pool import initialize,ping
from nomad_phase15b.depth import Snapshot
from . import planner,baselines
from .recent import ensure
from .rollout import unified_simulate,baseline_guarded,stop_rollout,evaluate
from .prediction import prefix,concatenate
from .response import reaction,stop_metrics
from .report import OUT,HERE,generate,write_selection_report
from .runtime import (Journal,reconcile,managed_pool,stage,ExecutionSignal,
    SOLVE_WATCHDOG_S,BASELINE_WATCHDOG_S,ROLLOUT_WATCHDOG_S,ORACLE_WATCHDOG_S,EXACT_WATCHDOG_S)

def read(f):return json.loads(Path(f).read_text())
def write(f,x):
    f=Path(f);f.parent.mkdir(parents=True,exist_ok=True);tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(clean(x),indent=2)+'\n');tmp.replace(f)
def grid(p):
    return [dict(zip(p['grid'],values)) for values in itertools.product(*p['grid'].values())]
def definition_hash(p):
    mutable={'status','selected','selection_evidence','definition_sha256'}
    return hashlib.sha256(json.dumps({k:v for k,v in p.items() if k not in mutable},sort_keys=True,separators=(',',':')).encode()).hexdigest()
def commit(message,paths):
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--',*[str(Path(f).relative_to(ROOT)) for f in paths]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m',message],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
def method_record(c,name,plan,p,journal=None):
    timing={}
    def rollout():
        if name.startswith('U'):
            waiting=plan['prediction'];next_case=dict(c,B=plan['B_pred'],previous_vw=plan['application_previous_vw'])
            return concatenate(waiting,unified_simulate(next_case,plan,p['policy']))
        model=p['policy'].get('baseline_wait_model')
        if model is None:raise ValueError('Register baseline computation motion before execution')
        if model=='fixed_B':
            plan['application_delay_s']=plan['compute_s'];plan['application_pose']=c['B']
            return baseline_guarded(c['B'],plan['path'],c['previous_vw'][0]) if plan['accepted'] else stop_rollout(c['B'],c['previous_vw'][0])
        waiting=prefix(c,plan['compute_s'],'brake_wait');plan['application_pose']=waiting['B_pred'];plan['application_delay_s']=plan['compute_s']
        future=dict(c,B=waiting['B_pred'],previous_vw=waiting['previous_vw'])
        follow=baseline_guarded(future['B'],plan['path'],future['previous_vw'][0]) if plan['accepted'] else stop_rollout(future['B'],future['previous_vw'][0])
        return concatenate(waiting,follow)
    result=stage('ROLLOUT',ROLLOUT_WATCHDOG_S,rollout,journal,timing)
    values=stage('ORACLE',ORACLE_WATCHDOG_S,lambda:evaluate(result,c),journal,timing)
    def exact():
        field=Snapshot.load(c['snapshot_file'])
        return field.exact_clearance(np.asarray(plan['path'],dtype=float)) if plan.get('path') is not None else None
    depth=stage('EXACT_CLEARANCE',EXACT_WATCHDOG_S,exact,journal,timing)
    intent=None;native_short=remaining_short=None;forward=None
    if name.startswith('U') and plan['accepted']:
        from .graph import prepare_candidates
        B=plan['B_pred'];candidates,_,flags=prepare_candidates(c['samples_world'],B,c.get('old_path'),p['policy']['short_policy']);active=plan['active_candidate'];delta=candidates[active,-1]-B[:2]
        native_short=flags[active]['native_remaining_m']<.3;remaining_short=flags[active]['still_short']
        forward=float((np.asarray(plan['path'])[-1]-B[:2])@np.array([np.cos(B[2]),np.sin(B[2])]))
        if np.linalg.norm(delta)>1e-12:intent=float(delta@np.asarray(c['evaluation_direction']))<=0
    row=dict(case_id=c['case_id'],group=c['group'],scene=c['scene'],index=c['index'],method=name,accepted=plan['accepted'],disposition=plan['disposition'],compute_s=plan['compute_s'],depth_clearance_m=depth,depth_collision=depth<0 if depth is not None else None,intent_error=intent,active_switches=plan.get('active_switches',0),active_native_short=native_short,active_remaining_short=remaining_short,graph_forward_m=forward,
        active_transition_opportunities=sum(r.get('iteration') or 0 for r in plan.get('attempts',[])),
        warm_start_used=plan.get('warm_start_used',False),warm_source_gap_s=plan.get('warm_source_gap_s'),zero_motion_rollout=result['distance_m']<1e-8,
        selected_initialization=plan.get('selected_initialization'),iteration_limit_known=sum(r.get('iteration_limit') is True for r in plan.get('attempts',[])),
        completed_initializations=sum(r.get('completed_before_cutoff',False) for r in plan.get('attempts',[])),pending_initializations=plan.get('pending_at_cutoff',0),
        failure_obstacle_active=sum(r.get('active_obstacle') or 0 for r in plan.get('attempts',[])) if not plan['accepted'] else 0,
        failure_kinematic_active=sum(r.get('active_kinematic') or 0 for r in plan.get('attempts',[])) if not plan['accepted'] else 0,
        computation_prefix_s=result.get('computation_prefix_s',0.),computation_prefix_distance_m=result.get('computation_prefix_distance_m',0.),
        execution_timing_s=timing,rollout_ticks=len(result['speeds']),rollout_tick_cap=result['tick_cap'],**reaction(c,plan,result,c.get('reaction_reference')),**stop_metrics(plan,result),**values)
    return dict(plan=plan,row=row,trace=result['poses'].tolist())
def case_run(pool,c,p,mapping,deadline,replanners,journal=None):
    file=OUT/c['split']/f"{c['case_id']}.json";record=read(file) if file.exists() else dict(case=c,methods={})
    options=grid(p) if c['split']=='training' else [p['selected']]
    for i,weights in enumerate(options):
        name=f'U{i:02d}' if c['split']=='training' else 'U'
        if name not in replanners:replanners[name]=planner.Replanner(pool,weights,p['policy'])
        if name in record['methods']:
            replanners[name].remember(c,record['methods'][name]['plan']);continue
        if time.monotonic()>deadline:return False
        if journal:journal.update('COMBINATION_START',c['case_id'],name,split=c['split'])
        pending=record.setdefault('pending_plans',{})
        if name in pending:
            plan=pending[name];replanners[name].remember(c,plan)
            if journal:journal.event('PLAN_REUSED',case=c['case_id'],combination=name)
        else:
            plan=stage('SOLVE',SOLVE_WATCHDOG_S,lambda:replanners[name].on_candidates(c),journal)
            pending[name]=plan;write(file,record)
            if journal:journal.event('PLAN_SAVED',case=c['case_id'],combination=name,compute_s=plan['compute_s'])
        record['methods'][name]=method_record(c,name,plan,p,journal);pending.pop(name,None);write(file,record)
        if journal:journal.update('COMBINATION_DONE',c['case_id'],name)
    if c['split']=='evaluation':
        for name in ('C0','C1') if c['group']=='sudden' else ('C0',):
            if name in record['methods']:continue
            if time.monotonic()>deadline:return False
            if journal:journal.update('COMBINATION_START',c['case_id'],name,split=c['split'])
            pending=record.setdefault('pending_plans',{})
            if name in pending:plan=pending[name]
            else:
                plan=stage('BASELINE_SOLVE',BASELINE_WATCHDOG_S,lambda:baselines.plan(pool,c,name,mapping[c['snapshot_file']]),journal)
                pending[name]=plan;write(file,record)
            record['methods'][name]=method_record(c,name,plan,p,journal);pending.pop(name,None);write(file,record)
            if journal:journal.update('COMBINATION_DONE',c['case_id'],name)
    return True
def rank_weights(scores):
    eligible=[r for r in scores if r['p95']<=.5]
    all_exceed=not eligible;rank_pool=eligible if eligible else scores
    for item in scores:
        item['timing_eligible']=item['p95']<=.5
        item['progress_rank']={g:sum(other['progress'][g]>item['progress'][g] for other in rank_pool) for g in ('static','sudden')}
        rank=sum(item['progress_rank'].values())
        item['score']=(item['collisions'],item['failure_fraction'],rank,item['p50'],item['index'])
    winner=min(rank_pool,key=lambda r:(r['p95'],r['index'])) if all_exceed else min(eligible,key=lambda r:r['score'])
    for item in scores:item['selected']=item['index']==winner['index']
    return winner,dict(all_combinations_exceed_limit=all_exceed,timing_limit_s=.5,reason='MINIMUM_P95_FALLBACK' if all_exceed else 'TIMING_GATE_THEN_COLLISION_FAILURE_RANKSUM_P50',table=scores)

def select_weights(p,manifest):
    records=[read(OUT/'training'/f"{c['case_id']}.json") for c in manifest['training']];scores=[]
    for i,weights in enumerate(grid(p)):
        rr=[r['methods'][f'U{i:02d}']['row'] for r in records]
        progress={g:float(np.median([r['progress'] for r in rr if r['group']==g])) for g in ('static','sudden')}
        scores.append(dict(index=i,weights=weights,n=len(rr),collisions=sum(r['oracle_collision'] for r in rr),failure_fraction=sum(not r['accepted'] for r in rr)/len(rr),progress=progress,p95=float(np.quantile([r['compute_s'] for r in rr],.95)),p50=float(np.median([r['compute_s'] for r in rr]))))
    winner,evidence=rank_weights(scores);return winner['weights'],evidence

def run_body(a,p,m,journal):
    assert p.get('runtime_scope_confirmed',False),'Runtime estimate exceeds2h; wait for the user scope decision'
    pending=[k for k,v in p['policy'].items() if v is None]
    assert a.all and not pending,'Resolve and preregister missing execution/input/tuning definitions before running'
    assert p['selection_rule']=='timing_gate_collision_failure_rank_sum_p50','Unregistered selection rule'
    assert definition_hash(p)==p['definition_sha256'],'Registered design changed'
    if (OUT/'complete.json').exists():
        if a.publish:subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
        journal.update('COMPLETE');print('[complete] no solves repeated');return
    for file,h in p['source_sha256'].items():assert sha256_file(ROOT/file)==h,file
    assert sha256_file(OUT/'manifest.json')==p['manifest_sha256']
    if p.get('input_context_sha256'):
        assert sha256_file(OUT/'input_context_050.json')==p['input_context_sha256']
        context=read(OUT/'input_context_050.json')
        for file,h in context['input_hashes'].items():assert sha256_file(file)==h,file
        references={v['reaction_reference']['snapshot_file']:v['reaction_reference']['snapshot_sha256'] for v in context['contexts'].values() if v.get('reaction_reference',{}).get('snapshot_file')}
        for file,h in references.items():assert sha256_file(file)==h,file
        for split in ('training','evaluation'):
            m[split]=[dict(c,**context['contexts'][c['case_id']]) for c in m[split]]
    def state(stage,case=None):journal.update(stage,case)
    state('VERIFY_INPUTS')
    started=time.monotonic();deadline=started+a.budget_s
    for f,h in m['input_hashes'].items():assert sha256_file(f)==h,f
    commit('Register Phase23 offline graph definitions before tuning',[HERE,OUT/'manifest.json',OUT/'.gitignore'])
    ctx=mp.get_context('spawn');q=ctx.Queue()
    with managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        futures=[pool.submit(ping) for _ in range(4)]
        for _ in range(4):q.get(timeout=90)
        for f in futures:f.result()
        replanners={};order=lambda items:sorted(items,key=lambda c:(c['run'],c['tick'],c['case_id']))
        if p['status']!='FROZEN':
            for c in order(m['training']):
                state('TRAINING',c['case_id'])
                if not case_run(pool,c,p,{},deadline,replanners,journal):state('BUDGET_STOP_TRAINING',c['case_id']);print('[budget] training checkpoint saved');return
                print('[training]',c['case_id'],flush=True)
            selected,evidence=select_weights(p,m);write(OUT/'selection.json',dict(selected=selected,**evidence))
            p.update(selected=selected,selection_evidence=evidence,status='FROZEN');write(HERE/'protocol.json',p)
            write_selection_report(p)
            assert not list((OUT/'evaluation').glob('*.json')),'Evaluation must follow frozen selection'
            commit('Freeze Phase23 selected weights and selection report before evaluation',[HERE,OUT/'selection.json',ROOT/'docs/PHASE23O_UNIFIED.md'])
        replanners={}  # No training warm solution can leak into the evaluation split.
        mapfile=OUT/'recent_manifest.json';mapping=read(mapfile) if mapfile.exists() else {}
        for run in sorted({c['run'] for c in m['evaluation']}):
            needed=[c for c in m['evaluation'] if c['run']==run and c['snapshot_file'] not in mapping]
            if not needed:continue
            if time.monotonic()>deadline:state('BUDGET_STOP_TIMESTAMP_REPLAY');print('[budget] depth timestamp replay checkpoint saved');return
            state('TIMESTAMP_REPLAY',run)
            mapping.update(ensure(needed,OUT/'recent'));write(mapfile,mapping)
        for c in order(m['evaluation']):
            state('EVALUATION',c['case_id'])
            if not case_run(pool,c,p,mapping,deadline,replanners,journal):state('BUDGET_STOP_EVALUATION',c['case_id']);print('[budget] evaluation checkpoint saved');return
            print('[evaluation]',c['case_id'],flush=True)
    from .anytime import raise_late_errors
    raise_late_errors()
    state('REPORT');verdict=generate();write(OUT/'complete.json',dict(verdict=verdict,execution_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),new_navigation=False,new_inference=False))
    commit('Report Phase23 unified graph offline validation',[HERE,OUT,ROOT/'docs/PHASE23O_UNIFIED.md'])
    subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in OUT.glob('*.png')]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Add Phase23 offline figures'],cwd=ROOT,check=True)
    if a.publish:subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    state('COMPLETE')
    print(json.dumps(verdict))
def status():
    p=read(HERE/'protocol.json');m=read(OUT/'manifest.json');s=reconcile(OUT/'state.json')
    if s.get('error'):
        s=dict(s,error={k:v for k,v in s['error'].items() if k!='traceback'})
    counts={}
    for split in ('training','evaluation'):
        records=[read(f) for f in (OUT/split).glob('*.json')]
        counts[split]=dict(records=len(records),completed_combinations=sum(len(r['methods']) for r in records),pending_plans=sum(len(r.get('pending_plans',{})) for r in records),total_cases=len(m[split]))
    return dict(protocol=p['status'],progress=counts,complete=(OUT/'complete.json').exists(),state=s)

def main():
    import sys
    ap=argparse.ArgumentParser();ap.add_argument('--all',action='store_true');ap.add_argument('--status',action='store_true');ap.add_argument('--budget-s',type=float,default=1800.);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(status()));return
    lock=(OUT/'.run.lock').open('a');fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        with Journal(OUT) as journal:run_body(a,read(HERE/'protocol.json'),read(OUT/'manifest.json'),journal)
    except ExecutionSignal as exc:raise SystemExit(128+exc.signum)
    finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN);lock.close()

if __name__=='__main__':main()
