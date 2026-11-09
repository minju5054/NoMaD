"""Prespecified two primary paired exact McNemar comparisons, tables only."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
from nomad_phase38.statistics import holm
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,verify

PRIMARY=(('PRIMARY1','OURS-DETOUR+HMM','OURS-DETOUR','success','higher'),
         ('PRIMARY2','OURS-DETOUR','NOMAD_RAW','collision','lower'))


def primary_tests(rows):
    by={(r['scene'],r['index'],r['method']):r for r in rows};tests=[];pairs=[]
    for name,left,right,outcome,better in PRIMARY:
        n00=n01=n10=n11=0;excluded=[]
        for scene in SCENES:
            for index in INDICES:
                a=by.get((scene,index,left));b=by.get((scene,index,right))
                if not a or not b or a.get('technical_validation')!='PASS' or b.get('technical_validation')!='PASS':
                    excluded.append(dict(scene=scene,seed=index));continue
                x,y=bool(a[outcome]),bool(b[outcome]);n11+=x and y;n10+=x and not y;n01+=not x and y;n00+=not x and not y
                pairs.append(dict(comparison=name,scene=scene,seed=index,left=left,right=right,outcome=outcome,left_value=x,right_value=y,delta=int(x)-int(y)))
        n=n00+n01+n10+n11;discordant=n10+n01
        p=float(binomtest(n10,discordant,.5,alternative='two-sided').pvalue) if discordant else 1. if n else None
        tests.append(dict(comparison=name,left=left,right=right,outcome=outcome,favorable_direction=better,n=n,
            both_false=n00,right_only=n01,left_only=n10,both_true=n11,left_count=n10+n11,right_count=n01+n11,
            paired_difference_pp=100*(n10-n01)/n if n else None,p_exact_two_sided=p,excluded=excluded))
    adjusted=holm([t['p_exact_two_sided'] if t['p_exact_two_sided'] is not None else 1. for t in tests])
    for t,p in zip(tests,adjusted):
        t['p_holm_two_primary']=p if t['n'] else None
        t['full_20_pairs']=t['n']==20
        # Do not turn missing/technical runs into non-events or make an early
        # confirmatory rejection from an incomplete sample.
        t['reject_equal_holm_0p05']=bool(p<=.05) if t['n']==20 else None
    return tests,pairs


def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output)
    rows=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']}
    actual=[(r['scene'],r['index'],r['method']) for r in rows]
    assert len(actual)==len(set(actual)) and set(actual)<=expected
    tests,pairs=primary_tests(rows);summary=[]
    for scene in (*SCENES,'ALL'):
        for method in METHODS:
            group=[r for r in rows if r['method']==method and (scene=='ALL' or r['scene']==scene)]
            valid=[r for r in group if r.get('technical_validation')=='PASS'];errors=[e['abs_error'] for r in valid for e in r.get('node_errors',[])]
            summary.append(dict(scene=scene,method=method,completed=len(group),valid=len(valid),technical_failure=len(group)-len(valid),
                success_0p5=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),wrong_stop=sum(r['wrong_stop'] for r in valid),
                timeout=sum(r['timeout_without_declaration'] for r in valid),
                stop_distance_median_m=median([r['stop_distance_m'] for r in valid if r.get('stop_distance_m') is not None]),
                node_error_mae=float(np.mean(errors)) if errors else None,node_error_p95=float(np.quantile(errors,.95)) if errors else None))
    positions=[dict(scene=r['scene'],seed=r['index'],method=r['method'],success=r.get('success'),wrong_stop=r.get('wrong_stop'),
        stop_pose=r.get('stop_pose'),stop_distance_m=r.get('stop_distance_m'),final_pose=r.get('final_pose'),
        final_distance_m=r.get('final_goal_distance_m'),termination=r.get('termination',r.get('classification'))) for r in rows]
    errors=[e for r in rows for e in r.get('node_errors',[])]
    state=dict(experiment='CONFIRMATORY',status='COMPLETE' if len(rows)==60 else 'PARTIAL',completed=len(rows),planned=60,
        protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
    definitions=[dict(item='성공/정지',definition='All methods:closest_node==goal_node => immediate zero command and declared arrival. Success=distance<=0.5m AND no collision'),
        dict(item='주1',definition='HMM vs original localization on OURS-DETOUR:paired success,exact two-sided McNemar'),
        dict(item='주2',definition='OURS-DETOUR vs NOMAD_RAW:paired collision,exact two-sided McNemar'),
        dict(item='다중 비교',definition='Raw p and Holm over the two primary tests;family alpha0.05,full20 valid pairs required for rejection display,no composite pass label'),
        dict(item='기술 실패',definition='One retry;missing/failed pair excluded separately per primary comparison,not coded as success/failure'),
        dict(item='노드 오차',definition='Every saved inference:input observation pose nearest Topomap XY node;true node used only in report'),
        dict(item='RAW',definition='Frozen sample0+PP/SP;no depth/filter/EC/recovery. Original localization for methods1/2,Phase43 HMM only for method3')]
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',rows);save(output/'analysis.json',dict(state,primary_tests=tests))
    for name,data in [('summary',summary),('primary_tests',tests),('paired',pairs),('stop_positions',positions),('node_errors',errors)]:csvout(output/(name+'.csv'),data)
    doc=Path(document) if document else ROOT/'docs/PHASE47C_RESULTS.md'
    doc.write_text('\n\n'.join(table(data or [dict(n=0)]) for data in ([state],definitions,tests,summary,positions,pairs))+'\n');return doc


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase47-C paired confirmatory comparisons','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


if __name__=='__main__':main()
