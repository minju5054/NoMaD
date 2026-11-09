import argparse,json,subprocess
from pathlib import Path
from collections import Counter
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,verify


def decide(new,baseline43):
    by={(r['scene'],r['index']):r for r in baseline43};pairs=[]
    for r in new:
        b=by.get((r['scene'],r['index']))
        if b and r.get('technical_validation')==b.get('technical_validation')=='PASS':pairs.append((r,b))
    complete=len(new)==len(pairs)==len(by)==15 and len({(r['scene'],r['index']) for r in new})==15
    goals=sum(r['success'] for r,_ in pairs);collisions=sum(r['collision'] for r,_ in pairs)
    only=sum(r['success'] and not b['success'] for r,b in pairs);opposite=sum(not r['success'] and b['success'] for r,b in pairs)
    checks=dict(success_ge11=goals>=11,collision_le1=collisions<=1,net_paired_gain_ge2=only-opposite>=2)
    return dict(label=('B_ONLY_OK' if all(checks.values()) else 'B_ONLY_NOT_OK') if complete else 'NOT_EVALUATED',
        complete=complete,paired_n=len(pairs),success=goals,collision=collisions,graph_only=only,phase43_only=opposite,net_gain=only-opposite,checks=checks)


def generate(root=RUN_ROOT,output=OUT,document=None,baseline=None):
    p=verify();root=Path(root);output=Path(output)
    old=baseline if baseline is not None else json.loads((OUT/'preparation/baselines.json').read_text())
    new=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    keys={(j['scene'],j['index']) for j in p['main_order']}
    assert len(new)==len({(r['scene'],r['index']) for r in new}) and all((r['scene'],r['index']) in keys for r in new)
    d=decide(new,[r for r in old if r['cohort']=='Phase43-P'])
    rows=old+[dict(r,cohort='Phase46-P') for r in new];summary=[];trigger_summary=[]
    for scene in (*SCENES,'ALL'):
        for cohort in ('Phase43-P','Phase45-P','Phase46-P'):
            group=[r for r in rows if r['cohort']==cohort and (scene=='ALL' or r['scene']==scene)]
            valid=[r for r in group if r.get('technical_validation')=='PASS']
            ev=[e for r in valid for e in r.get('trigger_b_analysis',[])];false=[e for e in ev if e['classification']=='NON_BOX']
            summary.append(dict(cohort=cohort,scene=scene,completed=len(group),valid=len(valid),success_0p5=sum(r['success'] for r in valid),
                wrong_stop=sum(r['wrong_stop'] for r in valid),collision=sum(r['collision'] for r in valid),
                planner_wait_total_s=sum(r['planner_wait_s'] for r in valid),planner_wait_median_s=median([r['planner_wait_s'] for r in valid]),
                stop_wait_total_s=sum(r['stop_wait_s'] for r in valid),physical_stopped_total_s=sum(r['total_stopped_s'] for r in valid),
                r3_installations=sum(r.get('r3_installations',r.get('detour_applied_count',0)) for r in valid)))
            trigger_summary.append(dict(cohort=cohort,scene=scene,trigger_b=len(ev),box=sum(e['classification']=='BOX' for e in ev),
                non_box=sum(e['classification']=='NON_BOX' for e in ev),unmeasured=sum(e['classification']=='UNMEASURED' for e in ev),
                false_r3_installed=sum(e['r3_installed'] for e in false),false_r3_dispositions=dict(Counter(e['r3_disposition'] for e in false)),
                false_r3_end_reasons=dict(Counter(str(e['r3_end_reason']) for e in false))))
    pairs=[]
    for r in new:
        for cohort in ('Phase43-P','Phase45-P'):
            b=next(x for x in old if x['cohort']==cohort and (x['scene'],x['index'])==(r['scene'],r['index']))
            valid=r.get('technical_validation')==b.get('technical_validation')=='PASS'
            pairs.append(dict(scene=r['scene'],seed=r['index'],comparator=cohort,valid=valid,
                current_success=r.get('success') if valid else None,baseline_success=b['success'],
                success_delta=int(r['success'])-int(b['success']) if valid else None,
                wrong_stop_delta=int(r['wrong_stop'])-int(b['wrong_stop']) if valid else None,
                collision_delta=int(r['collision'])-int(b['collision']) if valid else None,
                planner_wait_delta_s=r['planner_wait_s']-b['planner_wait_s'] if valid else None))
    events=[dict(cohort=r['cohort'],scene=r['scene'],seed=r['index'],**e) for r in rows for e in r.get('trigger_b_analysis',[])]
    definitions=[dict(item='B_ONLY_OK',definition='15 valid pairs;success>=11,collision<=1,(current-only minus Phase43-only)>=2'),
        dict(item='ALL_UNSAFE',definition='No A/R2/R3 chain; frozen OURS-DETOUR fallback. Independently satisfied B remains enabled even on an ALL_UNSAFE tick'),
        dict(item='대기',definition='planner_wait=REPAIR_WAIT+DETOUR_WAIT command-hold seconds; STOP_WAIT and physical stopped time shown separately'),
        dict(item='상자 연관',definition='Post-run oracle only:minimum distance from triggering component cell centers to any already-spawned actual box XY footprint<=0.3m'),
        dict(item='거짓 발동',definition='NON_BOX under that spatial criterion; includes no spawned box. BOX association does not establish blockage/causality'),
        dict(item='관측 근거',definition='New runs log exact frozen-predicate component. Historical45 uses only matching archived frame; unavailable history=>UNMEASURED,not false'),
        dict(item='거짓 발동 결과',definition='Per-trigger R3 disposition,installation,end reason and final run outcome; chronological association,not a causal attribution'),
        dict(item='비교',definition='Same15 scene/seed/jitter pairs versus historical43/45; execution days differ')]
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',new);save(output/'decision.json',d)
    for name,data in [('summary',summary),('paired',pairs),('trigger_summary',trigger_summary),('trigger_b_events',events),
        ('false_trigger_events',[e for e in events if e['classification']=='NON_BOX'])]:csvout(output/(name+'.csv'),data)
    doc=Path(document) if document else ROOT/'docs/PHASE46P_RESULTS.md'
    doc.write_text('\n\n'.join(table(data or [dict(n=0)]) for data in ([d],definitions,summary,pairs,trigger_summary,events))+'\n');return doc


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase46-P B-only Graph pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


if __name__=='__main__':main()
