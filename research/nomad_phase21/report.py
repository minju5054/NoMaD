"""Preregistered paired exclusions and scene-first decisions; saved data only."""
import argparse,json,math,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean,csv_write
from .config import protocol,METHODS,PRIMARY


def eligibility(records):
    by={(r['scene'],r['index'],r['method']):r for r in records};excluded=[];included=set()
    for scene in ('L2','L2A'):
        for index in protocol()['indices']:
            failed=[m for m in PRIMARY if by.get((scene,index,m),{}).get('technical_validation')!='PASS']
            if failed:excluded.append(dict(scene=scene,index=index,failed_methods=failed))
            else:included.add((scene,index))
    return included,excluded

def summary_rows(records,included):
    result=[]
    for scene in ('L2','L2A','POOLED'):
        for method in METHODS:
            allr=[r for r in records if r['method']==method and (scene=='POOLED' or r['scene']==scene)]
            valid=[r for r in allr if r.get('technical_validation')=='PASS' and (method==METHODS[0] or (r['scene'],r['index']) in included)]
            def values(k):return [r[k] for r in valid if r.get(k) is not None]
            def median(k):v=values(k);return float(np.median(v)) if v else None
            paths=[p for r in valid for p in r.get('path_curvature',[])];count=sum(len(p['path'])-2 for p in paths)
            result.append(dict(scene=scene,method=method,n=len(valid),attempted=len(allr),technical_final=sum(r.get('technical_validation')!='PASS' for r in allr),
                goal=sum(r.get('success',False) for r in valid),passed=sum(r.get('passed_box',False) for r in valid),censored=sum(not r.get('passed_box',False) for r in valid),
                passage_median_s=median('passage_time_capped_s'),goal_median_s=median('goal_time_s'),collisions=sum(r.get('collision',False) or r.get('corridor',False) for r in valid),box_collisions=sum(r.get('collision',False) for r in valid),corridor=sum(r.get('corridor',False) for r in valid),
                minimum_clearance_m=min(values('minimum_clearance_m')+values('minimum_wall_clearance_m'),default=None),minimum_box_clearance_m=min(values('minimum_clearance_m'),default=None),minimum_wall_clearance_m=min(values('minimum_wall_clearance_m'),default=None),curvature_rms=float(np.sqrt(sum(p['rms']**2*(len(p['path'])-2) for p in paths)/count)) if count else None,
                curvature_max=max([p['max_abs'] for p in paths],default=None),curvature_paths=len(paths),angular_delta_rms_median=median('angular_delta_rms'),angular_jerk_rms_median=median('angular_jerk_rms'),planner_median_s=float(np.median([j['dispatch_to_complete_s'] for r in valid for j in r.get('detour_jobs',[])])) if any(r.get('detour_jobs') for r in valid) else None,planner_p95_s=float(np.quantile([j['dispatch_to_complete_s'] for r in valid for j in r.get('detour_jobs',[])],.95)) if any(r.get('detour_jobs') for r in valid) else None,triggers=sum(r.get('trigger_count',0) for r in valid),
                false_trigger_B=sum(r.get('false_trigger_B',0) for r in valid),reblock=sum(r.get('reblock_count',0) for r in valid),detour_applied=sum(r.get('detour_applied',0) for r in valid)))
    return result

def labels(summary):
    result=[]
    for scene in ('L2','L2A','POOLED'):
        rows={r['method']:r for r in summary if r['scene']==scene};graph=rows['M3_GRAPH'];astar=rows['B4_ASTAR'];threshold=3 if scene=='POOLED' else 2
        best=max(rows[m]['goal'] for m in ('B1_SAFE_TE','B2_SAFE_RTC','B3_M1'));heuristic=graph['goal']>=best+threshold
        faster=graph['passage_median_s'] is not None and astar['passage_median_s'] is not None and graph['passage_median_s']<astar['passage_median_s']
        smoother=graph['curvature_rms'] is not None and astar['curvature_rms'] is not None and graph['curvature_rms']<astar['curvature_rms']
        label='INCONCLUSIVE_NO_VALID_PAIRS' if graph['n']==0 else 'GRAPH_BEST' if heuristic and graph['goal']>=astar['goal'] and (faster or smoother) and graph['collisions']==0 else 'GRAPH_BEATS_HEURISTICS' if heuristic else 'NO_GRAPH_ADVANTAGE'
        result.append(dict(scene=scene,label=label,n=graph['n'],threshold=threshold,graph_goal=graph['goal'],best_heuristic_goal=best,astar_goal=astar['goal'],graph_collisions=graph['collisions'],astar_collisions=astar['collisions'],
            graph_passage_median=graph['passage_median_s'],astar_passage_median=astar['passage_median_s'],graph_curvature_rms=graph['curvature_rms'],astar_curvature_rms=astar['curvature_rms'],note='ASTAR_BETTER' if astar['goal']>graph['goal'] else None))
    return dict(final=result[1]['label'],additional='MIXED_HELDOUT' if result[0]['label']!=result[1]['label'] else None,scenes=result)

def exact_sign(w,l):
    n=w+l;return min(1.,2*sum(math.comb(n,k) for k in range(min(w,l)+1))/2**n) if n else None

def pairs(records,included):
    by={(r['scene'],r['index'],r['method']):r for r in records};details=[];stats=[]
    for scene,index in sorted(included):
        g=by[scene,index,'M3_GRAPH']
        for method in PRIMARY[:-1]:
            r=by[scene,index,method];details.append(dict(scene=scene,index=index,baseline=method,graph_goal=g['success'],baseline_goal=r['success'],goal_difference=int(g['success'])-int(r['success']),
                graph_passed=g['passed_box'],baseline_passed=r['passed_box'],graph_passage_s=g['passage_time_capped_s'],baseline_passage_s=r['passage_time_capped_s'],
                graph_censored=g['passage_censored'],baseline_censored=r['passage_censored'],goal_time_difference_s=g['goal_time_s']-r['goal_time_s'] if g['success'] and r['success'] else None))
    for scene in ('L2','L2A','POOLED'):
        for method in PRIMARY[:-1]:
            rr=[r for r in details if r['baseline']==method and (scene=='POOLED' or r['scene']==scene)];w=sum(r['goal_difference']>0 for r in rr);l=sum(r['goal_difference']<0 for r in rr)
            stats.append(dict(scene=scene,baseline=method,n=len(rr),goal_wins=w,goal_losses=l,goal_ties=len(rr)-w-l,exact_sign_p_reference=exact_sign(w,l)))
    return details,stats

def render(records,out,doc,figures=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);included,excluded=eligibility(records);summary=summary_rows(records,included);verdict=labels(summary);pair_rows,pair_stats=pairs(records,included)
    for name,value in [('runs',records),('decisions',verdict),('exclusions',excluded)]: (out/f'{name}.json').write_text(json.dumps(clean(value),indent=2,ensure_ascii=False)+'\n')
    for name,value in [('summary',summary),('paired',pair_rows),('paired_sign',pair_stats)]:
        (out/f'{name}.csv').unlink(missing_ok=True);csv_write(out/f'{name}.csv',value)
    if figures:
        from .visualize import generate
        generate(records,summary,out,included)
    p=protocol();text='# Phase21 — 사전등록 돌발 장애물 baseline 비교\n\n'
    text+=f"Protocol SHA256 `{sha256_file(ROOT/'research/nomad_phase21/protocol.json')}`. Base20F `3744de7`. Main seeds {p['indices']}, {len(p['main_order'])} planned runs; at most one same-seed technical retry. Final label prioritizes held-out L2A; pooled results are descriptive.\n\n"
    text+='## Frozen methods\n\nB1 SAFE_TE and B2 SAFE_RTC: **Phase18 handoff 규칙 + 20-F 공통 실행기**. All use PP lookahead0.25m, SP speed planning, start alignment, D750 and unchanged NoMaD metric scaling. B0 uses sample0 without depth/filter/fallback/recovery and is reference-only. B1 keeps TE target averaging/K3/expiry/KEEP, with SP/alignment from its latest selected active chunk. B2 uses the unchanged RTC hard-masking ablation (DDPM adaptation), beta5, and SAFE selection over all8 generated samples. B3/M3 use protected20F implementations. A* replaces only stage solvers, retaining A/B transitions and B-only new-obstacle direction/early-end. Oracle geometry is evaluation/placement-only; odometry is exact simulator pose.\n\n'
    text+=f"A* frozen selection: {p['astar']['selected']}; tuned only on saved20D/E/F jobs, before L2A geometry. R2 keeps native endpoint/nearest safe cell within0.2m, unknown-free,8 output points and0.75m trust. R3 uses recency/unknown-blocked map and B+10 points. Residual curvature>4 after selected smoothing is retained and flagged; it is not silently hidden.\n\n"
    text+='## Results (primary matched groups; B0 reference)\n\n'+table(summary)+'\n\n## Scene labels and ASTAR comparison\n\n'+table(verdict['scenes'])+f"\n\nFinal: **{verdict['final']}**. Additional: **{verdict['additional'] or 'none'}**.\n\n"
    text+='Scene goal advantage threshold remains2 and pooled threshold3, even if the timing rule reduced the seed count to4. No valid pairs yields an unavailable-data label, not evidence of no effect. GRAPH_BEST additionally needs no fewer goals than ASTAR, strictly smaller passage median or curvature RMS, and zero Graph collisions in the analyzed sample. GRAPH_BEATS_HEURISTICS requires only the heuristic threshold; ASTAR differences and collisions remain visible.\n\n'
    text+='## Pair exclusions\n\n'+table(excluded)+'\n\nA primary-method final technical failure excludes all5 primary methods at that scene×seed. B0 failure never excludes primary pairs. All attempts remain archived.\n\n'
    text+='## Seed pairs\n\n'+table(pair_rows)+'\n\n## Win/loss/sign test (technical reference only)\n\n'+table(pair_stats)+'\n\n'
    text+='Oracle collision counts include box overlap or wall intrusion; box/wall counts are also separate. Minimum clearance includes both box and wall. Passage time is spawn-to-footprint passage; nonpassage has the preregistered90s censored display value. Reported median is the median of these capped values, not a claim of90s actual follow-up after an early collision. Technical missing data are excluded, never imputed. Goal time uses goal-success pairs only. Curvature RMS pools Menger vertices from actually applied repair/detour paths; unavailable if none. Angular jerk is the second9Hz command difference divided by dt²; |delta omega| is separately saved. A triggers may intentionally start without new cells and are counted separately from unintended B triggers. Reblock is the first subsequent trigger after handover and before physical box passage.\n\n'
    failures=[dict(scene=r['scene'],index=r['index'],method=r['method'],attempt=a.get('attempt'),output=a.get('output'),error=a.get('error')) for r in records for a in r.get('attempts',[]) if a.get('technical_validation')!='PASS']
    text+='## Technical failure attempts (including recovered retries)\n\n'+table(failures)+'\n\n'
    text+='## Technical attempts and provenance\n\n'+table(records,['scene','index','method','classification','attempt_count','execution_git_sha','output','error'])+'\n\n'
    for name in ('outcomes.png','heldout_seed.png','curvature.png'):text+=f'![{name}](../research/results/phase21/{name})\n\n'
    text+='L2A geometry was checked by depth-only spawn rendering at both parity offsets before any method execution. No held-out navigation result was used for tuning. Identical seed offsets do not imply identical closed-loop RGB or FRESH trajectories. N is small; exact sign p-values are descriptive and do not replace the registered decision rules.\n'
    doc.parent.mkdir(exist_ok=True);doc.write_text(text);return verdict

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args();root=a.run_root.resolve();plan=json.loads((root/'plan.json').read_text());records=[]
    for j in plan['jobs']:
        r=json.loads((root/'metrics'/f"{j['key']}.json").read_text());f=Path(r['output'])/'provenance.json'
        if f.exists():r['execution_git_sha']=json.loads(f.read_text())['git_sha']
        records.append(r)
    out=ROOT/'research/results/phase21';doc=ROOT/'docs/PHASE21_BASELINE_SUDDEN.md';v=render(records,out,doc)
    if a.publish:
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip();subprocess.run(['git','add','--',str(out.relative_to(ROOT)),str(doc.relative_to(ROOT))],cwd=ROOT,check=True)
        subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in out.glob('*.png')]],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report preregistered Phase21 sudden baseline comparison'],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    print(json.dumps(v,ensure_ascii=False))
if __name__=='__main__':main()
