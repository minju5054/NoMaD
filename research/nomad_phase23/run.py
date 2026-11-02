"""Resumable offline sequence: training -> frozen commit -> evaluation -> report."""
import argparse,itertools,json,multiprocessing as mp,subprocess,time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase19r.evaluate import clean,csv_write
from nomad_phase20d.pool import initialize,ping
from nomad_phase15b.depth import Snapshot
from . import planner,baselines
from .recent import ensure
from .rollout import unified_simulate,baseline_simulate,stop_rollout,evaluate
from .report import OUT,HERE,generate

def read(f):return json.loads(Path(f).read_text())
def write(f,x):
    f=Path(f);f.parent.mkdir(parents=True,exist_ok=True);tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(clean(x),indent=2)+'\n');tmp.replace(f)
def grid(p):
    return [dict(zip(p['grid'],values)) for values in itertools.product(*p['grid'].values())]
def commit(message,paths):
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--',*[str(Path(f).relative_to(ROOT)) for f in paths]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m',message],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
def method_record(c,name,plan,p):
    result=unified_simulate(c,plan,p['policy']) if name.startswith('U') else baseline_simulate(c['B'],plan['path'],c['previous_vw'][0]) if plan['accepted'] else stop_rollout(c['B'],c['previous_vw'][0])
    values=evaluate(result,c);field=Snapshot.load(c['snapshot_file']);depth=field.exact_clearance(plan['path']) if plan.get('path') is not None else None
    intent=None
    if name.startswith('U') and plan['accepted']:
        from .graph import prepare_candidates
        candidates,_,_=prepare_candidates(c['samples_world'],c['B'],c.get('old_path'),p['policy']['short_policy']);delta=candidates[plan['active_candidate'],-1]-c['B'][:2]
        if np.linalg.norm(delta)>1e-12:intent=float(delta@np.array([np.cos(c['B'][2]),np.sin(c['B'][2])]))<=0
    row=dict(case_id=c['case_id'],group=c['group'],scene=c['scene'],index=c['index'],method=name,accepted=plan['accepted'],disposition=plan['disposition'],compute_s=plan['compute_s'],depth_clearance_m=depth,depth_collision=depth<0 if depth is not None else None,intent_error=intent,active_switches=plan.get('active_switches',0),**values)
    return dict(plan=plan,row=row,trace=result['poses'].tolist())
def case_run(pool,c,p,mapping,deadline):
    file=OUT/c['split']/f"{c['case_id']}.json";record=read(file) if file.exists() else dict(case=c,methods={})
    options=grid(p) if c['split']=='training' else [p['selected']]
    for i,weights in enumerate(options):
        name=f'U{i:02d}' if c['split']=='training' else 'U'
        if name in record['methods']:continue
        if time.monotonic()>deadline:return False
        plan=planner.plan(pool,c,weights,p['policy']);record['methods'][name]=method_record(c,name,plan,p);write(file,record)
    if c['split']=='evaluation':
        for name in ('C0','C1') if c['group']=='sudden' else ('C0',):
            if name in record['methods']:continue
            if time.monotonic()>deadline:return False
            plan=baselines.plan(pool,c,name,mapping[c['snapshot_file']]);record['methods'][name]=method_record(c,name,plan,p);write(file,record)
    return True
def select_weights(p,manifest):
    records=[read(OUT/'training'/f"{c['case_id']}.json") for c in manifest['training']];scores=[]
    for i,weights in enumerate(grid(p)):
        rr=[r['methods'][f'U{i:02d}']['row'] for r in records]
        progress={g:float(np.median([r['progress'] for r in rr if r['group']==g])) for g in ('static','sudden')}
        scores.append(dict(index=i,weights=weights,collisions=sum(r['oracle_collision'] for r in rr),failures=sum(not r['accepted'] for r in rr),progress=progress,p95=float(np.quantile([r['compute_s'] for r in rr],.95))))
    for item in scores:
        # Equal-weight ranks compare groups without adding metres to binary passage.
        rank=sum(sum(other['progress'][g]>item['progress'][g] for other in scores) for g in ('static','sudden'))/2
        item['score']=(item['collisions'],item['failures'],rank,item['p95'],item['index'])
    return min(scores,key=lambda r:r['score'])['weights'],scores

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--all',action='store_true');ap.add_argument('--status',action='store_true');ap.add_argument('--budget-s',type=float,default=1800.);ap.add_argument('--publish',action='store_true');a=ap.parse_args();p=read(HERE/'protocol.json');m=read(OUT/'manifest.json')
    pending=[k for k,v in p['policy'].items() if v is None]
    if a.status:print(json.dumps(dict(protocol=p['status'],pending=pending,training_records=len(list((OUT/'training').glob('*.json'))),training_total=len(m['training']),evaluation_records=len(list((OUT/'evaluation').glob('*.json'))),evaluation_total=len(m['evaluation']),complete=(OUT/'complete.json').exists())));return
    assert a.all and not pending,'Resolve and preregister missing execution/input/tuning definitions before running'
    assert p['selection_rule']=='collision_failure_progress_time','Unregistered selection rule'
    started=time.monotonic();deadline=started+a.budget_s
    for f,h in m['input_hashes'].items():assert sha256_file(f)==h,f
    commit('Register Phase23 offline graph definitions before tuning',[HERE,OUT/'manifest.json',OUT/'.gitignore'])
    ctx=mp.get_context('spawn');q=ctx.Queue()
    with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        futures=[pool.submit(ping) for _ in range(4)]
        for _ in range(4):q.get(timeout=90)
        for f in futures:f.result()
        if p['status']!='FROZEN':
            for c in m['training']:
                if not case_run(pool,c,p,{},deadline):print('[budget] training checkpoint saved');return
                print('[training]',c['case_id'],flush=True)
            selected,scores=select_weights(p,m);write(OUT/'selection.json',dict(selected=selected,scores=scores));p.update(selected=selected,status='FROZEN');write(HERE/'protocol.json',p)
            commit('Freeze Phase23 selected weights before evaluation',[HERE,OUT/'selection.json'])
        mapfile=OUT/'recent_manifest.json';mapping=read(mapfile) if mapfile.exists() else {}
        for run in sorted({c['run'] for c in m['evaluation']}):
            needed=[c for c in m['evaluation'] if c['run']==run and c['snapshot_file'] not in mapping]
            if not needed:continue
            if time.monotonic()>deadline:print('[budget] depth timestamp replay checkpoint saved');return
            mapping.update(ensure(needed,OUT/'recent'));write(mapfile,mapping)
        for c in m['evaluation']:
            if not case_run(pool,c,p,mapping,deadline):print('[budget] evaluation checkpoint saved');return
            print('[evaluation]',c['case_id'],flush=True)
    verdict=generate();write(OUT/'complete.json',dict(verdict=verdict,execution_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),new_navigation=False,new_inference=False))
    commit('Report Phase23 unified graph offline validation',[HERE,OUT,ROOT/'docs/PHASE23O_UNIFIED.md'])
    subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in OUT.glob('*.png')]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Add Phase23 offline figures'],cwd=ROOT,check=True)
    if a.publish:subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    print(json.dumps(verdict))
if __name__=='__main__':main()
