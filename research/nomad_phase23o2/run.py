"""User-run offline training -> frozen c/Tm -> held-out evaluation -> report."""
import argparse,json,itertools,time,multiprocessing as mp,subprocess,fcntl,hashlib
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase23 import planner,baselines
from nomad_phase23.run import method_record,rank_weights,commit
from nomad_phase23.runtime import Journal,managed_pool,stage,reconcile,ExecutionSignal
from nomad_phase23.recent import ensure
from nomad_phase23.anytime import raise_late_errors
from nomad_phase20d.pool import initialize,ping
from nomad_phase19r.evaluate import clean
from .inputs import HERE,OUT,OLD,read,write
from .graph import plan as u2_plan


def grid(p):return [dict(c=c,T_m=t) for c,t in itertools.product(p['grid']['c'],p['grid']['T_m'])]
def definition_hash(p):
    return hashlib.sha256(json.dumps({k:v for k,v in p.items() if k not in ('status','selected','selection_evidence','definition_sha256')},sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(path,value):write(path,clean(value))

def u2_record(c,plan,policy,journal=None):
    chosen=plan.get('active_component');adapted=dict(c);record_plan=dict(plan)
    if chosen:
        record_plan['active_candidate']=chosen['sample']
        if chosen['set_index']:
            adapted['samples_world']=c['memory_sets'][chosen['set_index']-1]['samples_world'];adapted['old_path']=None
    # Same executor/oracle metrics; adapt only which native set the inherited
    # reporting helper calls "active". Restore the full U2 component afterward.
    result=method_record(adapted,'U2',record_plan,dict(policy=policy),journal);result['plan']=plan
    result['row'].update(stratum=c.get('stratum','TRAINING'),active_history=chosen['set_index']>0 if chosen else None,
        active_age_s=chosen['age_s'] if chosen else None,active_set_index=chosen['set_index'] if chosen else None,
        prior_deviation_max_m=plan['prior_deviation_max_m'],prior_deviation_mean_m=plan['prior_deviation_mean_m'],
        prior_departure_030=plan['prior_deviation_max_m']>=.3 if chosen else None,available_sets=1+len(c.get('memory_sets',[])))
    result['row']['failure_dt_active']=sum(r.get('active_dt_bound') or 0 for r in plan['attempts']) if not plan['accepted'] else 0
    return result

def record_case(pool,c,p,old_protocol,mapping,journal,deadline,examples=False):
    folder='examples_only' if examples else c['split'];file=OUT/folder/(c['case_id']+'.json')
    record=read(file) if file.exists() else dict(case=c,methods={},pending_plans={})
    settings=grid(p) if c['split']=='training' else [p['selected']]
    for i,choice in enumerate(settings):
        name=f'U2_{i:02d}' if c['split']=='training' else 'U2'
        if name in record['methods']:continue
        if time.monotonic()>deadline:return False
        journal.update('COMBINATION_START',c['case_id'],name,split=folder)
        pending=record['pending_plans']
        if name not in pending:
            pending[name]=stage('SOLVE',5.,lambda:u2_plan(pool,c,choice,old_protocol['policy']),journal);save(file,record)
        value=u2_record(c,pending[name],old_protocol['policy'],journal);value['row']['method']=name
        record['methods'][name]=value;pending.pop(name);save(file,record);journal.update('COMBINATION_DONE',c['case_id'],name)
    if c['split']!='training':
        original=read(c['baseline_record']) if c.get('baseline_record') else None
        for name in (('U','C0','C1') if c['group']=='sudden' else ('U','C0')):
            if name in record['methods']:continue
            if time.monotonic()>deadline:return False
            journal.update('COMPARISON',c['case_id'],name)
            if original is not None:
                assert np.array_equal(original['case']['B'],c['B'])
                value=original['methods'][name];value['row'].update(case_id=c['case_id'],stratum=c['stratum'],reused_phase23=True)
            else:
                pending=record['pending_plans']
                if name not in pending:
                    pending[name]=stage('SOLVE' if name=='U' else 'BASELINE',5. if name=='U' else 10.,lambda:planner.plan(pool,c,old_protocol['selected'],old_protocol['policy']) if name=='U' else baselines.plan(pool,c,name,mapping[c['snapshot_file']]),journal);save(file,record)
                value=method_record(c,name,pending[name],old_protocol,journal);pending.pop(name);value['row'].update(stratum=c['stratum'],reused_phase23=False)
            record['methods'][name]=value;save(file,record)
    return True

def select(p,m):
    records=[read(OUT/'training'/(c['case_id']+'.json')) for c in m['training']];scores=[]
    for i,settings in enumerate(grid(p)):
        rows=[r['methods'][f'U2_{i:02d}']['row'] for r in records]
        scores.append(dict(index=i,weights=settings,n=len(rows),collisions=sum(r['oracle_collision'] for r in rows),failure_fraction=float(np.mean([not r['accepted'] for r in rows])),
            progress={g:float(np.median([r['progress'] for r in rows if r['group']==g])) for g in ('static','sudden')},p95=float(np.quantile([r['compute_s'] for r in rows],.95)),p50=float(np.median([r['compute_s'] for r in rows]))))
    winner,evidence=rank_weights(scores);return winner['weights'],evidence

def execute(a,journal):
    p=read(HERE/'protocol.json');m=read(OUT/'manifest.json');old_protocol=read(ROOT/'research/nomad_phase23/protocol.json')
    assert definition_hash(p)==p['definition_sha256'];assert sha256_file(OUT/'manifest.json')==p['manifest_sha256']
    assert p['configuration_registered'] and p['dataset_matches_unused_definition']
    for file,h in p['frozen_sources'].items():assert sha256_file(ROOT/file)==h,file
    for file,h in m['input_hashes'].items():assert sha256_file(file)==h,file
    if (OUT/'complete.json').exists():
        if a.publish:subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
        journal.update('COMPLETE');return
    deadline=time.monotonic()+a.budget_s;ctx=mp.get_context('spawn');q=ctx.Queue()
    with managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        futures=[pool.submit(ping) for _ in range(4)]
        for _ in range(4):q.get(timeout=90)
        for f in futures:f.result()
        order=lambda cc:sorted(cc,key=lambda c:(c['run'],c['tick'],c['case_id']))
        if p['status']!='FROZEN':
            for c in order(m['training']):
                if not record_case(pool,c,p,old_protocol,{},journal,deadline):journal.update('BUDGET_STOP_TRAINING');return
                print('[training]',c['case_id'],flush=True)
            p['selected'],p['selection_evidence']=select(p,m);p['status']='FROZEN';save(HERE/'protocol.json',p);save(OUT/'selection.json',dict(selected=p['selected'],**p['selection_evidence']))
            from .report import selection_report
            selection_report(p)
            assert not list((OUT/'evaluation').glob('*.json'))
            commit('Freeze Phase23-O2 Cauchy and memory tuning selection before evaluation',[HERE,OUT/'selection.json',ROOT/'docs/PHASE23O2_UNIFIED.md'])
        if a.stop_after_training:journal.update('BUDGET_STOP_USER_TRAINING_ONLY');return
        mapping_file=OUT/'recent_manifest.json';mapping=read(mapping_file) if mapping_file.exists() else read(OLD/'recent_manifest.json')
        need=[c for c in m['evaluation'] if c['snapshot_file'] not in mapping and not c.get('baseline_record')]
        for run in sorted({c['run'] for c in need}):
            if time.monotonic()>deadline:journal.update('BUDGET_STOP_TIMESTAMP_REPLAY');return
            journal.update('TIMESTAMP_REPLAY',run);mapping.update(ensure([c for c in need if c['run']==run],OUT/'recent'));save(mapping_file,mapping)
        for c in order(m['evaluation'])+m['examples_only']:
            example=c['stratum']=='SEEN_EXAMPLE_ONLY'
            if not record_case(pool,c,p,old_protocol,mapping,journal,deadline,example):journal.update('BUDGET_STOP_EVALUATION');return
            print('[example]' if example else '[evaluation]',c['case_id'],flush=True)
    raise_late_errors();journal.update('REPORT')
    from .report import generate
    verdict=generate();save(OUT/'complete.json',dict(verdict=verdict,execution_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),new_navigation=False,new_inference=False))
    commit('Report Phase23-O2 internal graph changes offline evaluation',[HERE,OUT,ROOT/'docs/PHASE23O2_UNIFIED.md'])
    images=list(OUT.glob('*.png'))
    subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in images]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Add Phase23-O2 figures'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    if a.publish:subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    journal.update('COMPLETE');print(json.dumps(verdict))

def status():
    p=read(HERE/'protocol.json');m=read(OUT/'manifest.json');s=reconcile(OUT/'state.json')
    if s.get('error'):s['error']={k:v for k,v in s['error'].items() if k!='traceback'}
    counts={}
    for split in ('training','evaluation','examples_only'):
        records=[read(f) for f in (OUT/split).glob('*.json')];counts[split]=dict(records=len(records),combinations=sum(len(r['methods']) for r in records),planned=len(m[split]))
    return dict(protocol=p['status'],selected=p['selected'],progress=counts,state=s)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--all',action='store_true');ap.add_argument('--status',action='store_true');ap.add_argument('--budget-s',type=float,default=14400);ap.add_argument('--publish',action='store_true');ap.add_argument('--stop-after-training',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(status()));return
    assert a.all,'Explicit --all required'
    with (OUT/'.run.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            with Journal(OUT) as journal:execute(a,journal)
        except ExecutionSignal as exc:raise SystemExit(128+exc.signum)
if __name__=='__main__':main()
