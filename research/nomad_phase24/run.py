"""Frozen Phase24 offline check; one NORMAL->DETOUR retry only by design."""
import argparse,json,time,multiprocessing as mp,subprocess,fcntl,hashlib
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase19r.evaluate import clean
from nomad_phase23 import baselines
from nomad_phase23.run import method_record,commit
from nomad_phase23.prediction import concatenate
from nomad_phase23.rollout import unified_simulate,evaluate
from nomad_phase23.runtime import Journal,managed_pool,stage,reconcile,ExecutionSignal
from nomad_phase23.anytime import raise_late_errors
from nomad_phase20d.pool import initialize,ping
from nomad_phase20c.detour_known import radial_reference
from nomad_phase23o2.report import plan_passage
from .inputs import HERE,OUT,read,write
from .context import reconstruct
from .decision import available_history,choose_mode,resolve_direction,advanced_case,pose_history
from .graph import plan
from .report import generate

def save(path,value):write(path,clean(value))
def definition_hash(p):return hashlib.sha256(json.dumps({k:v for k,v in p.items() if k!='definition_sha256'},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def join_motion(a,b):
    assert np.allclose(np.asarray(a['poses'])[-1],np.asarray(b['poses'])[0],rtol=0,atol=1e-12)
    return dict(b,poses=np.vstack([np.asarray(a['poses'])[:-1],np.asarray(b['poses'])]),speeds=list(a['speeds'])+list(b['speeds']),omegas=list(a['omegas'])+list(b['omegas']),
        step_dt_s=list(a['step_dt_s'])+list(b['step_dt_s']),duration_s=a['duration_s']+b['duration_s'],distance_m=a['distance_m']+b['distance_m'],
        commands=list(a.get('commands',[]))+[dict(c,tick=c['tick']+len(a['speeds']),time_s=a['duration_s']+c.get('time_s',c['tick']/72)) for c in b.get('commands',[])])

def combine_plans(first,second):
    assert first['mode']=='NORMAL' and not first['accepted'] and second['mode']=='DETOUR'
    return dict(second,prediction=join_motion(first['prediction'],second['prediction']),compute_s=first['compute_s']+second['compute_s'],application_delay_s=1.,source_B=first['source_B'])

def evaluate_g(c,result,policy,journal):
    def rollout():
        future=dict(c,B=result['B_pred'],previous_vw=result['application_previous_vw'])
        return concatenate(result['prediction'],unified_simulate(future,result,policy))
    trace=stage('ROLLOUT',30.,rollout,journal);metrics=stage('ORACLE',60.,lambda:evaluate(trace,c),journal)
    row=dict(case_id=c['case_id'],group=c['group'],scene=c['scene'],input_stage=c['input_stage'],method='G',accepted=result['accepted'],output_type=result['output_type'],
        compute_s=result['compute_s'],application_delay_s=result['application_delay_s'],mode_initial=result['mode_initial'],mode_final=result['mode'],normal_to_detour=result['normal_to_detour'],
        stage_count=len(result['solve_stages']),stage_compute_s=[s['compute_s'] for s in result['solve_stages']],stage_output_types=[s['output_type'] for s in result['solve_stages']],
        initial_mode_source=result['decision']['mode_source'],mode_source='MODE_FALLBACK' if result['normal_to_detour'] else result['decision']['mode_source'],direction_source=result['direction']['source'] if result.get('direction') else None,
        minimum_hard_depth_relaxed=False,**metrics)
    value=dict(plan=result,row=row,trace=trace['poses'].tolist());row['planned_box_passage']=plan_passage(dict(case=c),value);return value

def baseline_case(c,decision):
    if decision['mode_source']!='MODE_RECOMPUTED':return dict(c)
    fired=decision['mode']=='DETOUR';poses=pose_history(c);radial,_=radial_reference(poses,len(poses)-1)
    # Frozen20F B uses the component direction; its A branch retains radial
    # start->current. Solver/selection/controller implementations are unchanged.
    return dict(c,trigger='B' if fired else None,baseline_u_ref=decision['u_ref'] if fired else radial.tolist())

def reusable(c,new,old_plan):
    same_trigger=(c.get('trigger')=='B')==(new.get('trigger')=='B')
    if not same_trigger:return False
    if c.get('trigger')!='B' and old_plan['disposition'] in ('SAFE_SAMPLE','R2'):return True
    return bool(np.allclose(c['baseline_u_ref'],new['baseline_u_ref'],rtol=0,atol=1e-12))

def execute(args,journal):
    p=read(HERE/'protocol.json');manifest=read(OUT/'manifest.json');old=read(ROOT/'research/nomad_phase23/protocol.json')
    assert p['status']=='FROZEN' and definition_hash(p)==p['definition_sha256'];assert not p['estimate']['over_one_hour']
    assert sha256_file(OUT/'manifest.json')==p['manifest_sha256']
    for f,h in p['frozen_sources'].items():assert sha256_file(ROOT/f)==h,f
    for f,h in manifest['input_hashes'].items():assert sha256_file(f)==h,f
    if (OUT/'complete.json').exists():journal.update('COMPLETE');return
    deadline=time.monotonic()+args.budget_s;cases=manifest['cases'];mapping_file=OUT/'history_manifest.json';mapping=read(mapping_file) if mapping_file.exists() else {}
    available={}
    for c in cases:available[c['case_id']]=available_history(c)
    needed=[c for c in cases if available[c['case_id']][0] and c['snapshot_file'] not in mapping]
    for run in sorted({c['run'] for c in needed}):
        if time.monotonic()>deadline:journal.update('BUDGET_STOP_HISTORY');return
        journal.update('HISTORY_REPLAY',run);mapping.update(reconstruct([c for c in needed if c['run']==run],OUT/'history'));save(mapping_file,mapping);print('[history]',Path(run).name,flush=True)
    decisions_file=OUT/'decisions.json';decisions=read(decisions_file) if decisions_file.exists() else {}
    for c in cases:
        if c['case_id'] not in decisions:
            history=mapping.get(c['snapshot_file']) if available[c['case_id']][0] else None
            decisions[c['case_id']]=choose_mode(c,history,available[c['case_id']][1]);save(decisions_file,decisions)
    ctx=mp.get_context('spawn');queue=ctx.Queue()
    with managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
        ff=[pool.submit(ping) for _ in range(4)]
        for _ in range(4):queue.get(timeout=90)
        for f in ff:f.result()
        for c in sorted(cases,key=lambda c:(c['run'],c['tick'])):
            file=OUT/'records'/(c['case_id']+'.json');record=read(file) if file.exists() else dict(case=c,methods={},pending={});d=decisions[c['case_id']]
            if time.monotonic()>deadline:journal.update('BUDGET_STOP_CASES');return
            if 'G' not in record['methods']:
                pending=record['pending'];journal.update('G_STAGE1',c['case_id'])
                if 'G1' not in pending:pending['G1']=stage('SOLVE',5.,lambda:plan(pool,c,d['mode'],d['u_ref'],old['policy']),journal);save(file,record)
                first=pending['G1'];stages=[first];result=dict(first);direction=d['direction'];transition=first['mode']=='NORMAL' and not first['accepted']
                if transition:
                    second_case,poses=advanced_case(c,first['prediction']);u,detail=resolve_direction(second_case,d['history_file'],poses,len(poses)-1);journal.update('G_STAGE2',c['case_id'])
                    if 'G2' not in pending:pending['G2']=stage('SOLVE',5.,lambda:plan(pool,second_case,'DETOUR',u,old['policy']),journal);save(file,record)
                    second=pending['G2'];stages.append(second);result=combine_plans(first,second);direction=detail
                result.update(mode_initial=first['mode'],normal_to_detour=transition,solve_stages=stages,decision=d,direction=direction)
                record['methods']['G']=evaluate_g(c,result,old['policy'],journal);pending.pop('G1',None);pending.pop('G2',None);save(file,record)
            source=read(c['c0_record']);bc=baseline_case(c,d)
            for method in (('C0','C1') if c['group']=='sudden' else ('C0',)):
                if method in record['methods']:continue
                if time.monotonic()>deadline:journal.update('BUDGET_STOP_COMPARISON');return
                previous=source['methods'][method]
                if reusable(c,bc,previous['plan']):value=previous;value['row']['reused']=True
                else:
                    journal.update('BASELINE',c['case_id'],method);history=mapping.get(c['snapshot_file'])
                    if history is None:
                        with np.load(c['snapshot_file']) as z:assert 'last_free_tick' in z.files,'Cannot recompute baseline without original recent-free history'
                        history=c['snapshot_file']
                    if method not in record['pending']:record['pending'][method]=stage('BASELINE_SOLVE',10.,lambda:baselines.plan(pool,bc,method,history),journal);save(file,record)
                    value=method_record(bc,method,record['pending'][method],old,journal);record['pending'].pop(method);value['row']['reused']=False
                value['row'].update(output_type='FEASIBLE' if value['plan']['accepted'] else 'STOP',input_stage=c['input_stage']);value['row']['planned_box_passage']=plan_passage(dict(case=c),value);record['methods'][method]=value;save(file,record)
            if 'U' not in record['methods']:
                value=read(c['u_record'])['methods'][c['u_selected_key']];value['row'].update(method='U',input_stage=c['input_stage'],reused=True,output_type='FEASIBLE' if value['plan']['accepted'] else 'STOP');value['row']['planned_box_passage']=plan_passage(dict(case=c),value);record['methods']['U']=value;save(file,record)
            journal.update('CASE_DONE',c['case_id']);print('[offline]',c['case_id'],flush=True)
    raise_late_errors();journal.update('REPORT');records=[read(OUT/'records'/(c['case_id']+'.json')) for c in cases];verdict=generate(p,records)
    save(OUT/'complete.json',dict(gate=verdict,execution_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),new_tuning=False,new_inference=False,new_navigation=False));journal.update('COMPLETE');print(json.dumps(verdict),flush=True)

def status():
    s=reconcile(OUT/'state.json')
    if s.get('error'):s['error']={k:v for k,v in s['error'].items() if k!='traceback'}
    return dict(records=len(list((OUT/'records').glob('*.json'))),planned=242,state=s)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--all',action='store_true');ap.add_argument('--status',action='store_true');ap.add_argument('--budget-s',type=float,default=3600.);args=ap.parse_args()
    if args.status:print(json.dumps(status()));return
    assert args.all
    with (OUT/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            with Journal(OUT) as j:execute(args,j)
        except ExecutionSignal as e:raise SystemExit(128+e.signum)
if __name__=='__main__':main()
