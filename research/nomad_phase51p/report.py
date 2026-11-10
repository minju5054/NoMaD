"""Condition summaries and same-seed historical Phase47-C adjacent columns."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,CONDITIONS,BASE_SCENES,verify,split

FIELDS=('success','collision','wrong_stop','timeout_without_declaration','goal_time_s','stopped_s',
        'ec_all_candidates_rejected_s','ec_all_candidates_rejected_max_s')

def baselines():return json.loads((OUT/'preparation/baselines.json').read_text())

def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))];old=baselines()
    have={(r['scene'],r['index'],r['method']):r for r in runs};expected={(j['scene'],j['index'],j['method']) for j in p['main_order']}
    assert len(have)==len(runs) and set(have)<=expected
    by={(r['scene'],r['index']):r for r in old};pairs=[];intervals=[]
    for j in p['main_order']:
        scene,condition=split(j['scene']);r=have.get((j['scene'],j['index'],j['method']));b=by[(scene,j['index'])]
        good=r is not None and r['technical_validation']=='PASS'
        row=dict(condition=condition,scene=scene,seed=j['index'],status='NOT_RUN' if r is None else r['technical_validation'],baseline_output=b['output'])
        for field in FIELDS:
            row[field]=r.get(field) if good else None;row['phase47_'+field]=b[field]
            if field in ('goal_time_s','stopped_s','ec_all_candidates_rejected_s','ec_all_candidates_rejected_max_s'):
                row[field+'_delta']=row[field]-b[field] if row[field] is not None and b[field] is not None else None
        pairs.append(row)
        if good:intervals.extend(dict(condition=condition,scene=scene,seed=j['index'],**e) for e in r['ec_exhausted_intervals'])
    summary=[]
    for condition in CONDITIONS:
        for scene in (*BASE_SCENES,'ALL'):
            group=[r for r in pairs if r['condition']==condition and (scene=='ALL' or r['scene']==scene)];valid=[r for r in group if r['status']=='PASS']
            row=dict(condition=condition,scene=scene,planned=len(group),valid=len(valid),pending=sum(r['status']=='NOT_RUN' for r in group),technical_failure=sum(r['status']=='FAIL' for r in group))
            for field in FIELDS:
                count=field in FIELDS[:4]
                row[field]=sum(r[field] for r in valid) if count else median([r[field] for r in valid if r[field] is not None])
                row['phase47_'+field]=sum(r['phase47_'+field] for r in group) if count else median([r['phase47_'+field] for r in group if r['phase47_'+field] is not None])
            summary.append(row)
    state=dict(status='COMPLETE' if len(runs)==20 else 'PARTIAL',completed=len(runs),planned=20,
        protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest(),historical_execution_days_differ=True)
    definitions=[dict(item=k,definition=v) for k,v in p['report_definitions'].items()]
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',runs);save(output/'analysis.json',state)
    for name,data in [('summary',summary),('paired',pairs),('ec_exhausted_intervals',intervals)]:csvout(output/(name+'.csv'),data)
    doc=Path(document) if document else ROOT/'docs/PHASE51P_RESULTS.md'
    doc.write_text('\n\n'.join(table(d or [dict(n=0)]) for d in ([state],definitions,summary,pairs,intervals))+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase51-P frozen-method environment conditions','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

if __name__=='__main__':main()
