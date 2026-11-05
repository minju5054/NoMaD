"""Pilot-only decisions; no statistical test affects the registered labels."""
import argparse,json,csv,subprocess
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase23.report import csv_write
from .config import protocol,METHODS,PRIMARY,SCENES
from .decisions import classify,exclusions
from .storage import atomic_json

OUT=ROOT/'research/results/phase26';DOC=ROOT/'docs/PHASE26_PILOT.md'

def generate(root,out=OUT,doc=DOC):
    rr=[json.loads(p.read_text()) for p in sorted((root/'metrics').glob('*.json'))];assert len(rr)==60
    excluded=exclusions(rr);eligible=[r for r in rr if r['technical_validation']=='PASS' and (r['method'] not in PRIMARY or (r['scene'],r['index']) not in excluded)]
    out.mkdir(parents=True,exist_ok=True);atomic_json(out/'runs.json',rr);atomic_json(out/'exclusions.json',excluded)
    summary=[]
    for group in (*SCENES,'SUDDEN','STATIC'):
        scenes=SCENES[2:] if group=='SUDDEN' else SCENES[:2] if group=='STATIC' else (group,)
        for m in METHODS:
            rows=[r for r in eligible if r['scene'] in scenes and r['method']==m]
            med=lambda key:float(np.median([r[key] for r in rows if r.get(key) is not None])) if any(r.get(key) is not None for r in rows) else None
            summary.append(dict(group=group,method=m,n=len(rows),goal=sum(r['success'] for r in rows),collision=sum(r['collision'] for r in rows),
                box_collision=sum(r['obstacle_collision'] for r in rows),wall_collision=sum(r['wall_overlap'] for r in rows),corridor_stop=sum(r['corridor'] for r in rows),
                passage=sum(r['box_passage'] for r in rows),passage_time_median_s=med('box_passage_from_spawn_s'),goal_time_median_s=med('goal_time_s'),
                min_clearance_median_m=med('minimum_clearance_m'),omega_saturation_median=med('omega_saturation_fraction'),stop_fraction_median=med('stopped_fraction'),
                recovery_count=sum(r['recovery_count'] for r in rows),detour_triggers=sum(r['detour_trigger_count'] for r in rows),
                detour_latency_median_s=med('detour_latency_median_s'),compute_p95_median_s=med('detour_compute_p95_s')))
    decision=classify(summary);decision['excluded_scene_seed']=excluded;atomic_json(out/'decision.json',decision);csv_write(out/'summary.csv',summary)
    pairs=[]
    for group,scenes in [('SUDDEN',SCENES[2:]),('STATIC',SCENES[:2])]+[(s,(s,)) for s in SCENES]:
        for m in PRIMARY[:-1]:
            wins=losses=ties=0
            for scene in scenes:
                for index in (201,202):
                    if (scene,index) in excluded:continue
                    g=next(r for r in eligible if r['scene']==scene and r['index']==index and r['method']=='C0')
                    c=next(r for r in eligible if r['scene']==scene and r['index']==index and r['method']==m)
                    wins+=g['success']>c['success'];losses+=g['success']<c['success'];ties+=g['success']==c['success']
            pairs.append(dict(group=group,comparison='C0 vs '+m,wins=wins,losses=losses,ties=ties,exact_sign_p=float(binomtest(wins,wins+losses,.5).pvalue) if wins+losses else 1.))
    csv_write(out/'paired.csv',pairs)
    view=[{k:r.get(k) for k in ('scene','index','method','classification','success','collision','box_passage','box_passage_from_spawn_s','goal_time_s','technical_validation','attempt_count')} for r in rr]
    text='# Phase26 preregistered pilot\n\n'+f"Protocol SHA256 `{sha256_file(Path(__file__).with_name('protocol.json'))}`. Small descriptive pilot; no p-value determines a label. H1 is explicitly a u_ref limitation test. Exact simulator odometry. B0 is reference-only.\n\n"
    text+='## Decisions\n\n'+table([decision])+'\n\n## Scene and pooled results\n\n'+table(summary)+'\n\n## Paired seed outcomes\n\n'+table(view)+'\n\n## Descriptive sign counts\n\n'+table(pairs)+'\n\n'
    text+='H2 scene passage requires both boxes; per-box spawn-to-passage times and collision/clearance are in runs.json. Missing passage time is not imputed. Raw attempts and original phase results are preserved. Primary technical failures after one identical-seed retry exclude the complete scene×seed primary group; B0 failure is independent.\n\n'
    text+='Technical exclusions: '+str(excluded)+'\n\n'
    if decision['label'] in ('PILOT_SUPPORTS','PILOT_MIXED'):
        text+='## Draft expansion only — not authorized for execution\n\nFreeze the same six methods and five scenes, add paired seeds203–208 (180new runs), preserve these pilot results separately and preregister confirmatory comparisons before launch. Define uncertainty/validity criteria and held-out interpretation before examining new outcomes; H1 remains a separate direction-limit analysis. No expansion command is generated or executed here.\n'
    doc.write_text(text)
    for f in out.glob('*.csv'):f.write_text(f.read_text())
    return decision

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args();print(json.dumps(generate(a.run_root.resolve())))
    if a.publish:
        paths=[str(DOC.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','-f','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase26 preregistered pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
