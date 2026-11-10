"""Automatic table report; historical published aggregates reused without replay."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,CONDITIONS,BASE_SCENES,verify,split
FIELDS=('success','collision','wrong_stop','timeout_without_declaration','goal_time_s','stopped_s','align_rotate_s',
    'heading_discontinuity_p50_deg','heading_discontinuity_p95_deg','minimum_clearance_m','ec_rejects','graph_adoption_rate','graph_solve_p50_s','graph_solve_p95_s')

def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in runs]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    baseline=json.loads((OUT/'preparation/baselines.json').read_text());summary=[];states=[];paired=[]
    for condition in CONDITIONS:
        for method in METHODS:
            for scene in (*BASE_SCENES,'ALL'):
                rr=[r for r in runs if r['method']==method and r.get('condition',split(r['scene'])[1])==condition and (scene=='ALL' or split(r['scene'])[0]==scene)]
                good=[r for r in rr if r['technical_validation']=='PASS']
                summary.append(dict(condition=condition,scene=scene,method=method,n=len(rr),valid=len(good),
                    **{k:sum(bool(r[k]) for r in good) for k in FIELDS[:4]},
                    **{k+'_median':median([r[k] for r in good if r.get(k) is not None]) for k in FIELDS[4:]}))
    by={(r['scene'],r['index'],r['method']):r for r in runs}
    for j in p['main_order']:
        r=by.get((j['scene'],j['index'],j['method']));scene,condition=split(j['scene'])
        row=dict(scene=scene,condition=condition,seed=j['index'],method=j['method'],status=r['technical_validation'] if r else 'NOT_RUN')
        row.update({k:r.get(k) if r and r['technical_validation']=='PASS' else None for k in FIELDS})
        for b in baseline:
            if b['base_scene']==scene and b['index']==j['index']:
                prefix=b['historical_group']+'_'+b['method']
                for k in FIELDS:row[prefix+'_'+k]=b.get(k)
        paired.append(row)
    for r in runs:
        states.extend(dict(scene=r['scene'],seed=r['index'],method=r['method'],state=k,seconds=v) for k,v in r.get('command_state_seconds',{}).items())
    status=dict(status='COMPLETE' if len(runs)==40 else 'PREPARED_NOT_RUN' if not runs else 'PARTIAL',completed=len(runs),planned=40,
        protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',runs);save(output/'status.json',status)
    for name,data in [('summary',summary),('paired',paired),('command_states',states)]:csvout(output/(name+'.csv'),data)
    doc=Path(document) if document else ROOT/'docs/PHASE53P_RESULTS.md'
    doc.write_text('# Phase53-P\n\n'+table([status])+'\n\n'+table([dict(item=k,value=v) for k,v in p['report_definitions'].items()])+'\n\n'+table(summary)+'\n\n'+table(paired)+'\n\n'+table(states or [dict(status='NOT_RUN')])+'\n')
    return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase53-P braking-tail CUT and frozen CLR handoff','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
