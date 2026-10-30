"""Saved-result pilot report, fixed six case visualizations, narrow commit/push."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean,csv_write
from .config import protocol,METHODS


def groups(records):
    result=[]
    for level in ('L1','L2','L3'):
        for method in METHODS:
            rr=[r for r in records if r['scene']==level and r['method']==method];valid=[r for r in rr if r.get('technical_validation')=='PASS']
            def mean(k):
                xs=[r[k] for r in valid if r.get(k) is not None];return float(np.mean(xs)) if xs else None
            def pooled(section,key):
                vals=[x for r in valid for j in r.get('repair_job_timings',[]) for x in (j[key] if isinstance(j[key],list) else [j[key]])]
                return float(np.median(vals)) if vals and section=='median' else float(np.quantile(vals,.95)) if vals else None
            accepted=sum(r.get('repair_accepted',0) for r in valid);attempts=sum(r.get('repair_attempts',0) for r in valid)
            result.append(dict(scene=level,method=method,planned=6 if level=='L1' else 3,valid=len(valid),
                success=sum(r.get('success',False) for r in valid),collision=sum(r.get('collision',False) for r in valid),corridor=sum(r.get('corridor',False) for r in valid),
                stuck=sum(r.get('stuck',False) for r in valid),technical=len(rr)-len(valid),goal_time_s=mean('goal_time_s'),
                passed_box=sum(r.get('passed_box',False) for r in valid),box_passage_time_s=mean('box_passage_time_s'),all_unsafe=sum(r.get('all_unsafe',0) for r in valid),
                all_unsafe_per_run=mean('all_unsafe'),recovery_count=sum(r.get('recovery_count',0) for r in valid),stopped_fraction=mean('stopped_fraction'),
                repair_attempts=attempts,repair_accepted=accepted,repair_rejected=sum(r.get('repair_rejected',0) for r in valid),repair_timeout=sum(r.get('repair_timeout',0) for r in valid),
                repair_acceptance=accepted/attempts if attempts else None,sample_solve_median_s=pooled('median','sample_solve_s'),sample_solve_p95_s=pooled('p95','sample_solve_s'),
                eight_solve_median_s=pooled('median','pool_wall_s'),eight_solve_p95_s=pooled('p95','pool_wall_s'),
                dispatch_complete_median_s=pooled('median','dispatch_to_complete_s'),dispatch_complete_p95_s=pooled('p95','dispatch_to_complete_s'),
                post_repair_safe=sum(r.get('post_repair_safe_count',0) for r in valid),post_repair_observed=sum(r.get('post_repair_fresh_count',0) for r in valid),
                post_repair_safe_fraction=sum(r.get('post_repair_safe_count',0) for r in valid)/sum(r.get('post_repair_fresh_count',0) for r in valid) if sum(r.get('post_repair_fresh_count',0) for r in valid) else None))
    return result


def decisions(records,summary):
    result=[]
    for level in ('L1','L2','L3'):
        a,b=[next(r for r in summary if r['scene']==level and r['method']==m) for m in METHODS]
        lookup={(r['index'],r['method']):r for r in records if r['scene']==level and r.get('technical_validation')=='PASS'}
        pairs=[]
        for index in sorted(set(r['index'] for r in records if r['scene']==level)):
            x,y=lookup.get((index,METHODS[0])),lookup.get((index,METHODS[1]))
            if x and y and x.get('box_passage_time_s') is not None and y.get('box_passage_time_s') is not None:pairs.append(dict(index=index,difference_s=y['box_passage_time_s']-x['box_passage_time_s']))
        all_faster=bool(pairs) and all(p['difference_s']<0 for p in pairs)
        if a['valid']!=a['planned'] or b['valid']!=b['planned']:label='PILOT_INCONCLUSIVE'
        elif b['repair_accepted']>=2 and (b['success']>=a['success']+1 or (b['success']==a['success'] and all_faster)):label='REPAIR_HELPS'
        elif b['repair_accepted']<2:label='REPAIR_UNUSED'
        else:label='REPAIR_NO_HELP'
        result.append(dict(scene=level,label=label,scope='파일럿',M1_success=a['success'],M2_success=b['success'],success_difference=b['success']-a['success'],
            success_rate_difference=b['success']/b['planned']-a['success']/a['planned'],M1_all_unsafe=a['all_unsafe'],M2_all_unsafe=b['all_unsafe'],
            M1_all_unsafe_per_run=a['all_unsafe_per_run'],M2_all_unsafe_per_run=b['all_unsafe_per_run'],M2_repair_accepted=b['repair_accepted'],
            passed_pairs=len(pairs),all_pair_passage_times_shorter=all_faster,passage_pairs=pairs))
    return result


def render(records,out,doc,make_figures=True):
    p=protocol();summary=groups(records);verdict=decisions(records,summary);out.mkdir(parents=True,exist_ok=True)
    for name,value in [('runs',records),('decisions',verdict)]:
        with (out/f'{name}.json').open('w') as f:json.dump(clean(value),f,indent=2)
    for name,value in [('summary',summary),('blockage_trend',verdict)]:
        path=out/f'{name}.csv'
        if path.exists():path.unlink()
        csv_write(path,value)
    if make_figures:
        from .visualize import generate,trend
        generate([r for r in records if r['scene'] in ('L2','L3')],out);trend(summary,out)
    text='# Phase 20-B — blockage-level repair pilot / 파일럿\n\n'
    text+=f"Protocol hash: `{sha256_file(ROOT/'research/nomad_phase20b/protocol.json')}`. New runs: L2/L3 × M1/M2 × indices80–82. L1 is reused; no navigation retry.\n\n"
    text+='The Phase20 R2/SP/start-alignment/selection/fallback/recovery code is unchanged. M2 alone uses four CPU processes and a fixed1.0s wait limit. Processes initialize before the navigation clock without warmup solves; per-job timing includes snapshot loading and process scheduling, with sample solve/certificate times separately recorded. All late and terminal results retain timing logs. Oracle geometry is used only for placement/rendering and evaluation.\n\n'
    text+='Per-sample attempt timings include initialization and certificate. Short-path/negative-B rejections do not run SLSQP: solver_started, disposition and optimizer-only time are preserved per sample to distinguish these from actual solves.\n\n'
    text+='Box center y is fixed in corridor coordinates (L2=0; L3 even+0.3/odd−0.3m), preserving the specified gaps despite robot lateral drift. d=1.0m is measured from footprint front to the front box face along +X. L3 narrow gap0.20m is smaller than the0.23m required by radius0.09 plus two0.025m margins; it is not a proof that a0.18m diameter circle geometrically cannot fit.\n\n'
    text+='## Per-level results\n\n'+table(summary)+'\n\n## Pilot labels and descriptive blockage trend\n\n'+table(verdict)+'\n\n'
    text+='REPAIR_HELPS follows the frozen success/acceptance rule, including the equal-success paired-passage alternative. An empty paired subset never counts as all-faster. Technical/missing trials are retained and make an interpreted per-level label inconclusive.\n\n'
    text+='L1 has six seeds and the former serial0.5s repair backend; L2/L3 have three new seeds and the four-process1.0s backend. Across-level count/rate differences are descriptive, not paired causal estimates. In saved L1, both methods passed the box6/6, while goal success was M1=5/6 and M2=6/6. Goal success and box passage remain separate.\n\n'
    text+='## Seed × level × method\n\n'+table(records,['scene','index','method','classification','success','goal_time_s','passed_box','box_passage_time_s','pass_side','all_unsafe','repair_attempts','repair_accepted','repair_rejected','repair_timeout','repair_dispositions','recovery_count','stopped_fraction','sample_solve_s','eight_solve_s','post_repair_safe_count','post_repair_fresh_count'])+'\n\n'
    text+='## Technical failures\n\n'+table([r for r in records if r.get('technical_validation')!='PASS'],['scene','index','method','output','error'])+'\n\n'
    text+='## Frozen scene and per-seed visualizations\n\n![scene levels](../research/results/phase20b/scene_levels.png)\n\n'
    for level in ('L2','L3'):
        for seed in (80,81,82):
            text+=f'### {level} / seed {seed}\n\n'
            for name in (f'drive_{level}_{seed}.png',f'drive_{level}_{seed}.gif',f'rgb_strip_{level}_{seed}.png'):text+=f'![{name}](../research/results/phase20b/{name})\n\n'
    text+='![blockage trend](../research/results/phase20b/blockage_trend.png)\n\n'
    text+='Animation uses stored72Hz poses at1 simulation-second intervals,10fps for10× playback, capped at15s. After a run ends its last pose is held and labelled; no missing motion or RGB is invented. Depth animation never uses a snapshot before its actual publication. Static overlays use the first map that observed that run’s box.\n\n'
    text+='The simulator provides exact pose (no odometry error), RGB remains the only NoMaD input, and unknown depth cells remain free. No Graph or placement parameter was tuned from pilot results. A single scene family and N=3 do not establish generalization or statistical superiority.\n'
    doc.write_text(text);return verdict


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    plan=json.loads((root/'plan.json').read_text());assert len(plan['jobs'])==12
    records=[json.loads((root/'metrics'/f"main_{j['key']}.json").read_text()) for j in plan['jobs']]
    reused=json.loads((ROOT/'research/results/phase20/runs.json').read_text());records=[{**r,'scene':'L1','reused':True} for r in reused]+records
    out=ROOT/'research/results/phase20b';doc=ROOT/'docs/PHASE20B_BLOCKAGE.md';v=render(records,out,doc)
    if a.publish:
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
        subprocess.run(['git','add','--',str(out.relative_to(ROOT)),str(doc.relative_to(ROOT))],cwd=ROOT,check=True)
        media=[*out.glob('*.png'),*out.glob('*.gif')]
        subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in media]],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase20B blockage-level repair pilot'],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    print(json.dumps(v))

if __name__=='__main__':main()
