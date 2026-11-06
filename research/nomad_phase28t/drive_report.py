"""Post-campaign saved-log report; reused C0/NA, new H only, no smoke inclusion."""
import argparse,subprocess
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from .main_config import OUT,RUN_ROOT,HERE,verify
from .report import read,save,csv_write,table,quant
from .review import baselines,summarize_rows

METRICS=('goal_time_s','mean_speed_m_s','stopped_fraction','alignment_rotation_fraction','minimum_clearance_m','box_passage_from_spawn_s','omega_saturation_fraction')

def generate(root):
    p=verify();new=[read(f) for f in sorted((root/'metrics').glob('*.json'))]
    assert len(new)==10 and {(r['scene'],r['index'],r['method']) for r in new}=={(r['scene'],r['index'],r['method']) for r in p['main_order']}
    assert all(Path(r['output']).is_relative_to(RUN_ROOT/'main') for r in new)
    old=baselines();rows=old+new
    excluded=sorted({(r['scene'],r['index']) for r in rows if r['technical_validation']!='PASS'})
    OUT.mkdir(parents=True,exist_ok=True);save(OUT/'runs.json',rows);save(OUT/'exclusions.json',excluded)
    details,budgets=summarize_rows(rows,OUT)
    # Continuous metrics keep the original audit definitions; detail tables use
    # the same 72Hz stop threshold and account for truncated timed chunks.
    for r in rows:
        if r['technical_validation']!='PASS':continue
        a=next(a for a in details if (a['scene'],a['index'],a['method'])==(r['scene'],r['index'],r['method']))
        r['mean_speed_m_s']=a['mean_speed_m_s'];r['alignment_rotation_fraction']=a['alignment_rotation_s']/a['duration_s']
    save(OUT/'runs.json',rows)
    summaries=[];pairs=[]
    for scene in (*p['scenes'],'ALL'):
        for method in ('C0','C0-NA','C0-H'):
            q=[r for r in rows if r['method']==method and (scene=='ALL' or scene==r['scene']) and (r['scene'],r['index']) not in excluded and r['technical_validation']=='PASS']
            summaries.append(dict(scene=scene,method=method,n=len(q),goal=sum(r['success'] for r in q),collision=sum(r['collision'] for r in q),passage=sum(r['box_passage'] for r in q),
                **{k:quant([r[k] for r in q if r.get(k) is not None]) for k in METRICS}))
    for h in new:
        if (h['scene'],h['index']) in excluded:continue
        for method in ('C0','C0-NA'):
            b=next(r for r in old if (r['scene'],r['index'],r['method'])==(h['scene'],h['index'],method))
            pairs.append(dict(scene=h['scene'],index=h['index'],comparison='H-'+method,goal_difference=int(h['success'])-int(b['success']),collision_difference=int(h['collision'])-int(b['collision']),
                **{k+'_difference':h[k]-b[k] if h.get(k) is not None and b.get(k) is not None else None for k in METRICS}))
    csv_write(OUT/'summary.csv',summaries);csv_write(OUT/'paired.csv',pairs)
    types=[dict(scene=r['scene'],index=r['index'],cases=r.get('handoff_case_count',0),
        **{k:r.get('handoff_case_types',{}).get(k,0) for k in ('OPTIMIZED','INIT_ONLY','FALLBACK')},
        applied=r.get('handoff_applied',0),compute_p50_s=r.get('handoff_all_case_compute_p50_s'),
        compute_p95_s=r.get('handoff_all_case_compute_p95_s')) for r in new]
    csv_write(OUT/'event_types.csv',types)
    text='# Phase28-T C0-H main comparison\n\nOnly ten new H runs; smoke_01/02 excluded. C0: Phase27-R; C0-NA: Phase28, different execution dates. Frozen T timing 24 ticks/0.30s; original R1/NA/decision/depth/evaluator unchanged. Protocol SHA256 `'+sha256_file(HERE/'protocol_main.json')+'`. Technical exclusions: '+str(excluded)+'. No new performance verdict.\n\n'+table(summaries)+'\n\n'+table(pairs)+'\n\nClip, tracking and time-loss decomposition (all technically valid runs; paired primary summaries exclude the listed groups):\n\n'+table(details)+'\n\n'+table(budgets)+'\n\nEach scene/seed/method folder contains clip_commands/clip_causes/clip_combinations, tracking_72hz, time_budget, path_schedules and analysis.json. Clip causes overlap; combinations are disjoint. Tracking uses actual timed H execution only, not fallback. Stop means |v|<0.01 as in the frozen evaluator. Full Σdt schedules replaced before completion are censored; their sum is not a measured arrival-time counterfactual. NA schedules are ideal SP integrals, not equivalent timed trajectories.\n'
    text+='\n\nH event types and timing:\n\n'+table(types)+'\n\nPer-run stage_times.csv reports stage p50/p95 without adding nested stages.\n'
    doc=ROOT/'docs/PHASE28T_RESULTS.md';doc.write_text(text);return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    root=a.run_root.resolve();assert root==RUN_ROOT.resolve();doc=generate(root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase28-T ten-run H comparison','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

if __name__=='__main__':main()
