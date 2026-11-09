import argparse,json,subprocess
from pathlib import Path
import numpy as np
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,verify


def decide(rows):
    valid=[r for r in rows if r.get('technical_validation')=='PASS']
    complete=len(rows)==len(valid)==15
    success=sum(r['success'] for r in valid);wrong=sum(r['wrong_stop'] for r in valid)
    return dict(label=('LOC_OK' if wrong<=3 and success>=8 else 'LOC_NOT_OK') if complete else 'NOT_EVALUATED',
        complete=complete,valid=len(valid),success_0p5=success,wrong_stop=wrong,collision=sum(r['collision'] for r in valid),
        success_threshold=8,wrong_stop_max=3)


def generate(root=RUN_ROOT,output=OUT,document=None,baseline=None):
    p=verify();root=Path(root);output=Path(output)
    old=baseline if baseline is not None else json.loads((OUT/'preparation/baselines.json').read_text())
    rows=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    keys={(r['scene'],r['index']) for r in p['main_order']}
    assert len(rows)==len({(r['scene'],r['index']) for r in rows}) and all((r['scene'],r['index']) in keys for r in rows)
    new=[dict(r,cohort='Phase43-P') for r in rows];all_rows=old+new;d=decide(new);summary=[]
    errors=[e for r in all_rows for e in r.get('node_errors',[])]
    for scene in (*SCENES,'ALL'):
        for cohort in ('Phase38','Phase41','Phase43-P'):
            g=[r for r in all_rows if r['cohort']==cohort and (scene=='ALL' or r['scene']==scene)]
            valid=[r for r in g if r.get('technical_validation')=='PASS'];ev=[e for r in valid for e in r.get('node_errors',[])]
            summary.append(dict(cohort=cohort,scene=scene,completed=len(g),valid=len(valid),success=sum(r['success'] for r in valid),
                collision=sum(r['collision'] for r in valid),wrong_stop=sum(r['wrong_stop'] for r in valid) if cohort!='Phase38' else None,
                timeout=sum(r['timeout_without_declaration'] for r in valid),
                stop_distance_median_m=median([r['stop_distance_m'] for r in valid if r.get('stop_distance_m') is not None]),
                inferences=len(ev),node_error_mae=float(np.mean([e['abs_error'] for e in ev])) if ev else None,
                node_error_p95=float(np.quantile([e['abs_error'] for e in ev],.95)) if ev else None))
    positions=[]
    for r in all_rows:
        q=r.get('stop_pose')
        positions.append(dict(cohort=r['cohort'],scene=r['scene'],seed=r['index'],success=r.get('success'),
            termination=r.get('termination',r.get('classification')),stop_x_m=q[0] if q else None,stop_y_m=q[1] if q else None,
            stop_distance_m=r.get('stop_distance_m'),final_pose=r.get('final_pose')))
    paired=[]
    for r in new:
        for cohort in ('Phase41','Phase38'):
            b=next(x for x in old if x['cohort']==cohort and (x['scene'],x['index'])==(r['scene'],r['index']))
            valid=r.get('technical_validation')==b.get('technical_validation')=='PASS'
            paired.append(dict(scene=r['scene'],seed=r['index'],comparator=cohort,valid=valid,
                success_delta=int(r['success'])-int(b['success']) if valid else None,
                wrong_stop_delta=int(r['wrong_stop'])-int(b['wrong_stop']) if valid and cohort=='Phase41' else None,
                collision_delta=int(r['collision'])-int(b['collision']) if valid else None))
    definitions=[dict(item='주 판정',rule='wrong stop<=3/15 AND success(distance<=0.5m,no collision)>=8'),
        dict(item='Phase41',rule='same15 seeds,jitter,declared-arrival rule; historical execution day'),
        dict(item='Phase38',rule='same15 OURS-DETOUR runs; frozen geometric0.3m rule,wrong declaration not applicable'),
        dict(item='노드 오차',rule='every inference: closest minus nearest Topomap XY node at image observation pose; truth evaluation only'),
        dict(item='후보 창',rule='official candidate_range(HMM MAP,goal,4): inclusive [H-4,H+5] within map limits'),
        dict(item='raw argmin',rule='diagnostic argmin inside current HMM-selected window,not an independent original-policy run')]
    output.mkdir(parents=True,exist_ok=True);save(output/'decision.json',d);save(output/'runs.json',new)
    for name,data in [('summary',summary),('positions',positions),('paired',paired),('node_errors',errors)]:csvout(output/(name+'.csv'),data)
    doc=Path(document) if document else ROOT/'docs/PHASE43P_RESULTS.md'
    doc.write_text('\n\n'.join(table(x) for x in ([d],definitions,summary,paired,positions,errors))+'\n')
    return doc


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase43-P online HMM pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


if __name__=='__main__':main()
