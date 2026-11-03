"""Training-only U3 study; never dispatch the held-out evaluation matrix."""
import argparse,json,itertools,time,multiprocessing as mp,subprocess,fcntl,hashlib
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase23.run import method_record,commit
from nomad_phase23 import baselines
from nomad_phase23.runtime import Journal,managed_pool,stage,reconcile,ExecutionSignal
from nomad_phase23.anytime import raise_late_errors
from nomad_phase23.recent import ensure
from nomad_phase20d.pool import initialize,ping
from nomad_phase23o2.inputs import read,write
from nomad_phase23o2.run import u2_record
from nomad_phase23o2.report import plan_passage
from nomad_phase19r.evaluate import clean
from .graph import plan
from .report import HERE,OUT,scores,select,generate,selection_report


def grid(p):return [dict(w7=w,T_m=t) for w,t in itertools.product(p['grid']['w7'],p['grid']['T_m'])]
def save(path,value):write(path,clean(value))
def definition_hash(p):return hashlib.sha256(json.dumps({k:v for k,v in p.items() if k not in ('status','selected','selected_index','selection_evidence','definition_sha256')},sort_keys=True,separators=(',',':')).encode()).hexdigest()
def training_record(c,result,policy,journal):
    value=u2_record(c,result,policy,journal);row=value['row'];row.update(method='U3',output_type=result['output_type'],f7_enabled=result['direction_info']['enabled'],f7_positive_residual=result['f7_residual']>0 if result['f7_residual'] is not None else None)
    row['planned_box_passage']=plan_passage(dict(case=c),value);return value

def execute(args,journal):
    p=read(HERE/'protocol.json');m=read(OUT/'manifest.json');old=read(ROOT/'research/nomad_phase23/protocol.json')
    assert definition_hash(p)==p['definition_sha256'];assert sha256_file(OUT/'manifest.json')==p['manifest_sha256']
    for f,h in p['frozen_sources'].items():assert sha256_file(ROOT/f)==h,f
    for f,h in m['input_hashes'].items():assert sha256_file(f)==h,f
    if (OUT/'complete.json').exists():journal.update('COMPLETE');return
    deadline=time.monotonic()+args.budget_s;ctx=mp.get_context('spawn');q=ctx.Queue()
    with managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        futures=[pool.submit(ping) for _ in range(4)]
        for _ in range(4):q.get(timeout=90)
        for f in futures:f.result()
        mapfile=OUT/'recent_manifest.json';mapping=read(mapfile) if mapfile.exists() else read(ROOT/'research/results/phase23o/recent_manifest.json')
        needed=[c for c in m['training'] if c['snapshot_file'] not in mapping]
        for run in sorted({c['run'] for c in needed}):
            if time.monotonic()>deadline:journal.update('BUDGET_STOP_TIMESTAMP');return
            journal.update('TIMESTAMP_REPLAY',run);mapping.update(ensure([c for c in needed if c['run']==run],OUT/'recent'));save(mapfile,mapping);print('[timestamp]',Path(run).name,flush=True)
        for c in sorted(m['training'],key=lambda c:(c['run'],c['tick'])):
            file=OUT/'comparators'/(c['case_id']+'.json');record=read(file) if file.exists() else dict(case=c,methods={},pending_plans={})
            if 'U2' not in record['methods']:
                original=read(c['u2_record']);value=original['methods'][m['u2_selected_key']];value['row'].update(method='U2',output_type='FEASIBLE' if value['plan']['accepted'] else 'STOP');value['row']['planned_box_passage']=plan_passage(dict(case=c),value);record['methods']['U2']=value;save(file,record)
            for method in (('C0','C1') if c['group']=='sudden' else ('C0',)):
                if method in record['methods']:continue
                if time.monotonic()>deadline:journal.update('BUDGET_STOP_COMPARATORS');return
                journal.update('COMPARATOR',c['case_id'],method)
                pending=record['pending_plans']
                if method not in pending:pending[method]=stage('BASELINE',10.,lambda:baselines.plan(pool,c,method,mapping[c['snapshot_file']]),journal);save(file,record)
                value=method_record(c,method,pending[method],old,journal);value['row'].update(output_type='FEASIBLE' if pending[method]['accepted'] else 'STOP');value['row']['planned_box_passage']=plan_passage(dict(case=c),value);record['methods'][method]=value;pending.pop(method);save(file,record)
            print('[comparators]',c['case_id'],flush=True)
        if p['status']!='FROZEN':
            for c in sorted(m['training'],key=lambda c:(c['run'],c['tick'])):
                file=OUT/'training'/(c['case_id']+'.json');record=read(file) if file.exists() else dict(case=c,methods={},pending_plans={})
                for i,setting in enumerate(grid(p)):
                    name=f'U3_{i:02d}'
                    if name in record['methods']:continue
                    if time.monotonic()>deadline:journal.update('BUDGET_STOP_TRAINING');return
                    journal.update('COMBINATION_START',c['case_id'],name);pending=record['pending_plans']
                    if name not in pending:pending[name]=stage('SOLVE',5.,lambda:plan(pool,c,setting,old['policy']),journal);save(file,record)
                    value=training_record(c,pending[name],old['policy'],journal);value['row']['method']=name;record['methods'][name]=value;pending.pop(name);save(file,record);journal.update('COMBINATION_DONE',c['case_id'],name)
                print('[training]',c['case_id'],flush=True)
            records=[read(OUT/'training'/(c['case_id']+'.json')) for c in m['training']];winner,evidence=select(scores(records,grid(p)))
            p.update(status='FROZEN',selected=winner['settings'],selected_index=winner['index'],selection_evidence=evidence);save(HERE/'protocol.json',p);save(OUT/'selection.json',dict(selected=p['selected'],**evidence));selection_report(p)
            commit('Freeze U3 training-only F7 selection before online gate',[HERE,OUT/'selection.json',ROOT/'docs/PHASE23O3_UNIFIED.md'])
    raise_late_errors();journal.update('REPORT');verdict=generate(p,m);save(OUT/'complete.json',dict(gate=verdict['label'],execution_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),evaluation_cases_rerun=0,online_started=False));journal.update('COMPLETE');print(json.dumps(dict(label=verdict['label'],failed=verdict['failed'])),flush=True)

def status():
    state=reconcile(OUT/'state.json')
    if state.get('error'):state['error']={k:v for k,v in state['error'].items() if k!='traceback'}
    counts={}
    for split in ('comparators','training'):
        rr=[read(f) for f in (OUT/split).glob('*.json')];counts[split]=dict(records=len(rr),methods=sum(len(r['methods']) for r in rr))
    return dict(protocol=read(HERE/'protocol.json')['status'],progress=counts,state=state)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--all',action='store_true');ap.add_argument('--status',action='store_true');ap.add_argument('--budget-s',type=float,default=14400);args=ap.parse_args()
    if args.status:print(json.dumps(status()));return
    assert args.all
    with (OUT/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            with Journal(OUT) as journal:execute(args,journal)
        except ExecutionSignal as exc:raise SystemExit(128+exc.signum)
if __name__=='__main__':main()
