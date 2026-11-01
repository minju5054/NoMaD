"""Registered live comparison; no inference, solver or navigation in reporting."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean,csv_write
from .drive_config import protocol,METHODS


def included_pairs(records):
    lookup={(r['scene'],r['index'],r['method']):r for r in records};included=set();excluded=[]
    for scene in ('L2','L2B'):
        for index in protocol()['indices']:
            failed=[m for m in METHODS if lookup.get((scene,index,m),{}).get('technical_validation')!='PASS']
            if failed:excluded.append(dict(scene=scene,index=index,failed_methods=failed))
            else:included.add((scene,index))
    return included,excluded

def summarize(records,included):
    result=[]
    for scene in ('L2','L2B','POOLED'):
        for method in METHODS:
            allr=[r for r in records if r['method']==method and (scene=='POOLED' or r['scene']==scene)];rr=[r for r in allr if (r['scene'],r['index']) in included]
            def median(key):
                v=[r[key] for r in rr if r.get(key) is not None];return float(np.median(v)) if v else None
            def timing(key):
                v=[x for r in rr for x in r.get(key,[])];return dict(n=len(v),p50=float(np.median(v)) if v else None,p95=float(np.quantile(v,.95)) if v else None)
            result.append(dict(scene=scene,method=method,n=len(rr),goal=sum(r['success'] for r in rr),passage=sum(r['passed_box'] for r in rr),passage_censored=sum(not r['passed_box'] for r in rr),passage_median_s=median('passage_time_capped_s'),
                goal_time_median_s=median('goal_time_s'),collisions=sum(r.get('collision',False) or r.get('corridor',False) for r in rr),box_collisions=sum(r.get('collision',False) for r in rr),wall_intrusions=sum(r.get('corridor',False) for r in rr),
                detour_clearance_median_m=median('detour_minimum_clearance_m'),detour_box_clearance_median_m=median('detour_minimum_box_clearance_m'),detour_wall_clearance_median_m=median('detour_minimum_wall_clearance_m'),
                jerk_rms_median=median('detour_execution_jerk_rms'),curvature_rms_median=median('detour_execution_curvature_rms'),reblock=sum(r.get('handover_reblock_count',0) for r in rr),handover_3s_progress_median_m=median('handover_3s_progress_mean_m'),
                GRAPH_FALLBACK_runs=sum(r.get('GRAPH_FALLBACK_used',False) for r in rr),branch_applications={k:sum(r.get('branch_applications',{}).get(k,0) for r in rr) for k in ('REFINED','A*_RAW','GRAPH_FALLBACK','NONE')},
                backend_time_s=timing('branch_backend_times_s'),decision_latency_s=timing('branch_decision_times_s'),
                technical_final=sum(r.get('technical_validation')!='PASS' for r in allr),technical_attempts=sum(a.get('technical_validation')!='PASS' for r in allr for a in r.get('attempts',[]))))
    return result

def pairs(records,included):
    by={(r['scene'],r['index'],r['method']):r for r in records};result=[]
    for scene,index in sorted(included):
        a,b=by[scene,index,'P0_ASTAR'],by[scene,index,'P2F_ASTAR_GRAPH'];r=dict(scene=scene,index=index)
        for label,x in (('P0',a),('P2F',b)):
            for k in ('success','passed_box','passage_time_capped_s','goal_time_s','detour_minimum_clearance_m','detour_execution_jerk_rms','handover_3s_progress_mean_m','GRAPH_FALLBACK_used'):r[label+'_'+k]=x.get(k)
        result.append(r)
    return result

def decisions(summary,paired):
    p=protocol();result=[]
    for scene in ('L2','L2B','POOLED'):
        a,b=[next(r for r in summary if r['scene']==scene and r['method']==m) for m in ('P0_ASTAR','P2F_ASTAR_GRAPH')];pp=[r for r in paired if scene=='POOLED' or r['scene']==scene]
        med={};counts={}
        for key in ('detour_minimum_clearance_m','detour_execution_jerk_rms'):
            eligible=[r for r in pp if r['P0_'+key] is not None and r['P2F_'+key] is not None];counts[key]=len(eligible)
            med[key]={m:float(np.median([r[m+'_'+key] for r in eligible])) if eligible else None for m in ('P0','P2F')}
        clearance=counts['detour_minimum_clearance_m']>0 and med['detour_minimum_clearance_m']['P2F']>=med['detour_minimum_clearance_m']['P0']+.03
        jerk=counts['detour_execution_jerk_rms']>0 and med['detour_execution_jerk_rms']['P2F']<=.7*med['detour_execution_jerk_rms']['P0'];benefit=clearance or jerk
        speed=a['passage_median_s'] is not None and b['passage_median_s'] is not None and b['passage_median_s']<=1.15*a['passage_median_s']
        conditions=dict(valid_pairs=b['n']>0,zero_P2F_collisions=b['collisions']==0,goal_not_lower=b['goal']>=a['goal'],passage_within15percent=bool(speed),clearance_benefit=bool(clearance),jerk_benefit=bool(jerk),absolute_goal_difference_le1=abs(b['goal']-a['goal'])<=1,no_secondary_benefit=not benefit,goal_deficit_ge2=b['goal']<=a['goal']-2,more_P2F_collisions=b['collisions']>a['collisions'])
        if b['n']==0:label=p['unclassified_label']
        elif b['collisions']==0 and b['goal']>=a['goal'] and speed and benefit:label='REFINE_HELPS'
        elif b['goal']<=a['goal']-2 or b['collisions']>a['collisions']:label='REFINE_HURTS'
        elif b['collisions']==0 and abs(b['goal']-a['goal'])<=1 and not benefit:label='REFINE_NEUTRAL'
        else:label=p['unclassified_label']
        result.append(dict(scene=scene,label=label,n=b['n'],P0_goal=a['goal'],P2F_goal=b['goal'],P0_collision=a['collisions'],P2F_collision=b['collisions'],passage_within15percent=speed,clearance_benefit=bool(clearance),jerk_benefit=bool(jerk),secondary_pair_n=counts,secondary_medians=med,conditions_met=[k for k,v in conditions.items() if v],conditions_not_met=[k for k,v in conditions.items() if not v]))
    return dict(final=result[1]['label'],additional='MIXED_HELDOUT' if result[0]['label']!=result[1]['label'] else None,scenes=result)


def render(records,out,doc,figures=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);included,excluded=included_pairs(records);summary=summarize(records,included);paired=pairs(records,included);verdict=decisions(summary,paired)
    for name,data in [('runs',records),('decisions',verdict),('exclusions',excluded)]: (out/f'{name}.json').write_text(json.dumps(clean(data),indent=2,ensure_ascii=False)+'\n')
    for name,data in [('summary',summary),('paired',paired)]:
        (out/f'{name}.csv').unlink(missing_ok=True);csv_write(out/f'{name}.csv',data)
    if figures:
        from .drive_visualize import generate
        generate(records,summary,paired,included,out)
    p=protocol();text='# Phase22 — preregistered A* + Graph refinement drive comparison\n\n'
    text+=f"Protocol SHA256 `{sha256_file(Path(__file__).with_name('drive_protocol.json'))}`; seeds {p['indices']}; {len(p['main_order'])} planned runs. Final label: **{verdict['final']}**; additional: **{verdict['additional'] or 'none'}**. L2B takes priority; pooled results are descriptive.\n\n"
    text+='P0 is frozen Phase21 B4; P1 is frozen Phase21 M3. P2F keeps R2 as Phase21 A* and substitutes only the R3 composite: A* → frozen6250433 refinement; refinement failure/timeout uses its cached A* path; A* failure attempts the unchanged seven-start Graph only within the remaining1s. No remaining budget gives NONE. All use unchanged SP/alignment/selection/fallback/recovery/trigger/NoMaD timing. The22-O2 evaluator cutoff is not an online controller change.\n\n'
    text+='Anchor source: '+str(p['anchor_mode'])+'. Box/wall coordinates are not sent to planners. L2B uses actual±20° box rendering and exact rigid-transformed swept collision, not an enclosing-AABB collision approximation. Front placement follows the inherited world+X support-distance convention; the actual forward-ray distance is also logged.\n\n'
    text+='Unlike22-O offline (spawn-previous odometry), the online return line uses observable depth history only. Trigger B uses the component first-occupied t_new pose and the frozen20-F u_ref from [t_new−216,t_new] (its existing heading fallback for displacement<0.3m). Trigger A uses its unchanged20-F u_ref through the trigger B pose. Weights and optimizer remain frozen; spawn timing is not supplied to the planner.\n\n'
    text+='## Outcomes and execution metrics\n\n'+table(summary)+'\n\n## Registered decisions\n\n'+table(verdict['scenes'])+'\n\n'
    text+='Secondary comparisons use matched seeds with both detour metrics observed, without imputation. All primary matched seeds contribute to goal and capped/censored90s passage medians. Actual applied-detour intervals include alignment; curvature uses actual w/v only while translating. Jerk uses consecutive9Hz omega samples within the same interval. No-passage/failed plans and technical exclusions are retained.\n\n'
    text+='## Seed pairs\n\n'+table(paired)+'\n\n## Technical exclusions\n\n'+table(excluded)+'\n\n'
    text+='## All three methods by seed\n\n'+table(records,['scene','index','method','success','passed_box','passage_time_capped_s','goal_time_s','collision','corridor','GRAPH_FALLBACK_used','technical_validation'])+'\n\n'
    text+='## Branches and run provenance\n\n'+table(records,['scene','index','method','classification','attempt_count','execution_git_sha','GRAPH_FALLBACK_used','branch_selections','branch_applications','branch_executed','branch_backend_time_s','branch_decision_latency_s','stage_time_s','handover_reblock_count','handover_3s_progress_mean_m','output','error'])+'\n\n'
    text+='Branch selections and applications are separate; GRAPH_FALLBACK-used requires at least one executed interval. Cached A* fallback preserves its real predeadline readiness timestamp, while decision/delivery/backend completion times remain separately recorded, including late refinement results. A terminal run before3s after handover is censored, not extrapolated.\n\n'
    for name in ('outcomes.png','heldout_paths.png','clearance_jerk.png'):text+=f'![{name}](../research/results/phase22/{name})\n\n'
    text+='This is a small paired pilot. Same seeds do not imply identical closed-loop RGB/FRESH. Exact simulator odometry is assumed; oracle geometry and appearance timing are evaluation/placement only.\n'
    doc.parent.mkdir(exist_ok=True);doc.write_text(text);return verdict


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args();root=a.run_root.resolve();plan=json.loads((root/'plan.json').read_text());records=[]
    for j in plan['jobs']:
        r=json.loads((root/'metrics'/f"{j['key']}.json").read_text());f=Path(r['output'])/'provenance.json'
        if f.exists():r['execution_git_sha']=json.loads(f.read_text())['git_sha']
        records.append(r)
    out=ROOT/'research/results/phase22';doc=ROOT/'docs/PHASE22_REFINE_DRIVE.md';v=render(records,out,doc)
    if a.publish:
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip();subprocess.run(['git','add','--',str(out.relative_to(ROOT)),str(doc.relative_to(ROOT))],cwd=ROOT,check=True)
        subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in out.glob('*.png')]],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase22 refinement drive pilot'],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    print(json.dumps(v,ensure_ascii=False))
if __name__=='__main__':main()
