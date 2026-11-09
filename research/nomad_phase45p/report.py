import argparse,json,subprocess
from pathlib import Path
import numpy as np
from nomad_phase31p.report import table
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,verify


def generate(root=RUN_ROOT,output=OUT,document=None,baseline=None):
    p=verify();root=Path(root);output=Path(output)
    old=baseline if baseline is not None else json.loads((OUT/'preparation/baselines.json').read_text())
    new=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    keys={(j['scene'],j['index']) for j in p['main_order']}
    assert len(old)==15 and {(r['scene'],r['index']) for r in old}==keys
    assert len(new)==len({(r['scene'],r['index']) for r in new}) and all((r['scene'],r['index']) in keys for r in new)
    all_rows=[dict(r,cohort='Phase43-P') for r in old]+[dict(r,cohort='Phase45-P') for r in new];summary=[]
    for scene in (*SCENES,'ALL'):
        for cohort in ('Phase43-P','Phase45-P'):
            group=[r for r in all_rows if r['cohort']==cohort and (scene=='ALL' or r['scene']==scene)]
            valid=[r for r in group if r.get('technical_validation')=='PASS']
            summary.append(dict(cohort=cohort,scene=scene,completed=len(group),valid=len(valid),
                success_0p5=sum(r['success'] for r in valid),wrong_stop=sum(r['wrong_stop'] for r in valid),collision=sum(r['collision'] for r in valid),
                r2_installations=sum(r.get('r2_installations',0) for r in valid),r3_installations=sum(r.get('r3_installations',0) for r in valid)))
    pairs=[];post=[];windows=[]
    for r in new:
        b=next(x for x in old if (x['scene'],x['index'])==(r['scene'],r['index']));valid=r.get('technical_validation')==b.get('technical_validation')=='PASS'
        pairs.append(dict(scene=r['scene'],seed=r['index'],paired_valid=valid,
            phase43_success=b['success'],phase45_success=r.get('success') if valid else None,
            success_delta=int(r['success'])-int(b['success']) if valid else None,
            wrong_stop_delta=int(r['wrong_stop'])-int(b['wrong_stop']) if valid else None,
            collision_delta=int(r['collision'])-int(b['collision']) if valid else None))
    for r in all_rows:
        detail=r.get('post_detour',{})
        for scope,key in (('HANDOVER_10S','handover_10s'),('INSTALL_10S','install_10s')):
            post.append(dict(cohort=r['cohort'],scene=r['scene'],seed=r['index'],scope=scope,**detail.get(key,dict(n=0,mae=None,p50=None,p95=None))))
        windows.extend(dict(cohort=r['cohort'],scene=r['scene'],seed=r['index'],**w) for w in detail.get('windows',[]))
    paired_valid=[r for r in pairs if r['paired_valid']]
    change=[dict(n=len(paired_valid),success_delta=sum(r['success_delta'] for r in paired_valid),
                 wrong_stop_delta=sum(r['wrong_stop_delta'] for r in paired_valid),collision_delta=sum(r['collision_delta'] for r in paired_valid))]
    definitions=[dict(item='주 성공',definition='Declared arrival distance<=0.5m AND no collision; Phase41/43 unchanged'),
        dict(item='비교',definition='Same15 scene/seed/jitter blocks versus stored Phase43-P OURS-DETOUR+HMM; different execution day'),
        dict(item='Graph',definition='Phase38 OURS frozen R2/R3/strict map/certificate/EC; no VN,escape or nonblocking changes'),
        dict(item='HANDOVER_10S',definition='Primary:10s after END of an actually applied R3,clipped to run termination; failed/unapplied attempts excluded'),
        dict(item='INSTALL_10S',definition='Supplement:10s after R3 APPLIED,includes detour execution; clipped to run termination'),
        dict(item='노드 오차',definition='Input observation time; absolute HMM closest minus nearest Topomap XY node; overlapping windows deduplicated per run/scope'),
        dict(item='무자료',definition='No completed detour or no inference in window => n0/NA,never zero error; no new binary gate registered')]
    state=dict(status='COMPLETE' if len(new)==15 else 'PARTIAL',completed=len(new),planned=15,paired_valid=len(paired_valid),
               protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',new);save(output/'analysis.json',state)
    for name,rows in [('summary',summary),('paired',pairs),('changes',change),('post_detour',post),('detour_windows',windows)]:csvout(output/(name+'.csv'),rows)
    doc=Path(document) if document else ROOT/'docs/PHASE45P_RESULTS.md'
    doc.write_text('\n\n'.join(table(x or [dict(n=0)]) for x in ([state],definitions,summary,change,pairs,post,windows))+'\n');return doc


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase45-P frozen OURS plus HMM pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


if __name__=='__main__':main()
