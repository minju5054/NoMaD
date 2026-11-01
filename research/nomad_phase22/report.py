"""Offline mechanism report and scientific figures from completed evaluation only."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from nomad_isaac.common import ROOT
from nomad_phase17.report import table
from nomad_phase19r.evaluate import csv_write
from .metrics import decision

OUT=ROOT/'research/results/phase22o';COLORS={'P0':'tab:blue','P1':'tab:orange','P2':'purple','P3':'tab:green'}

def summary(rows):
    result=[]
    for scene in ('L2','L2A','ALL'):
        for m in COLORS:
            rr=[r for r in rows if r['method']==m and (scene=='ALL' or r['scene']==scene)]
            def median(k):
                x=[r[k] for r in rr if r.get(k) is not None];return float(np.median(x)) if x else None
            times=[r['compute_s'] for r in rr]
            result.append(dict(scene=scene,method=m,n=len(rr),plans=sum(r['accepted'] for r in rr),plan_failed=sum(r['planning_failed'] for r in rr),
                oracle_collisions=sum(r.get('oracle_collision',False) for r in rr),completed=sum(r.get('completed',False) for r in rr),safe_completion=sum(r.get('safe_completion',False) for r in rr),
                depth_collisions=sum(r.get('depth_clearance_m',0) is not None and r.get('depth_clearance_m',0)<0 for r in rr),oracle_minimum_clearance_m=min([r['oracle_minimum_clearance_m'] for r in rr if r.get('oracle_minimum_clearance_m') is not None],default=None),
                wide_choice=sum(r.get('wide_choice') is True for r in rr),wide_choice_n=sum(r.get('wide_choice') is not None for r in rr),
                completion_median_s=median('completion_time_s'),jerk_median=median('jerk_rms'),omega_saturation_median=median('omega_saturation_fraction'),tracking_rms_median=median('tracking_rms'),tracking_max_median=median('tracking_max'),
                curvature_rms_median=median('curvature_rms'),curvature_max_median=median('curvature_max'),delta_curvature_rms_median=median('delta_curvature_rms'),heading_error_median_rad=median('heading_error_rad'),lateral_error_median_m=median('lateral_error_m'),
                compute_p50_s=float(np.median(times)) if times else None,compute_p95_s=float(np.quantile(times,.95)) if times else None,over_1s=sum(r['over_1s'] for r in rr)))
    return result

def figures(records,rows,examples):
    by={r['case']['case_id']:r for r in records};fig,axes=plt.subplots(3,2,figsize=(16,12),constrained_layout=True)
    for row,identity in enumerate(examples):
        r=by[identity];case=r['case'];cfg=case['oracle_config'];half=cfg['corridor']['half_width'];allpoints=[np.array(case['B'])[None,:2]]
        for plan in r['plans'].values():
            if plan.get('path') is not None:allpoints.append(np.array(plan['path']))
        allpoints.extend(np.array(t['poses'])[:,:2] for t in r['traces'].values());extent=np.concatenate(allpoints)
        for column,ax in enumerate(axes[row]):
            ax.axhline(half,c='.4');ax.axhline(-half,c='.4');ax.axvline(cfg['corridor']['xmin'],c='.4');ax.axvline(cfg['corridor']['xmax'],c='.4')
            for box in cfg['obstacles']:
                center=np.array(box['center_xy_m']);size=np.array(box['size_xyz_m'][:2]);ax.add_patch(Rectangle(center-size/2,*size,color='.5',alpha=.35))
            for method,color in COLORS.items():
                plan=r['plans'][method]
                if plan.get('path') is not None:
                    q=np.array(plan['path']);ax.plot(q[:,0],q[:,1],color=color,lw=1.5,alpha=1 if plan['accepted'] else .3,label=method+('' if plan['accepted'] else ' rejected'))
                else:ax.plot([],[],color=color,label=method+' '+plan['disposition'])
                trace=r['traces'].get(method)
                if trace:
                    q=np.array(trace['poses']);ax.plot(q[:,0],q[:,1],'--',color=color,lw=1)
            B=np.array(case['B']);u=np.array(case['u_ref']);ax.scatter(*B[:2],marker='^',color='black',s=30);ax.arrow(*B[:2],*(.25*u),width=.012,color='black')
            if column==0:
                ax.set_xlim(max(cfg['corridor']['xmin']-.1,B[0]-1),min(cfg['corridor']['xmax']+.1,B[0]+2.4));ax.set_ylim(-half-.2,half+.2)
            else:
                ax.set_xlim(min(cfg['corridor']['xmin']-.2,extent[:,0].min()-.2),max(cfg['corridor']['xmax']+.2,extent[:,0].max()+.2));ax.set_ylim(min(-half-.2,extent[:,1].min()-.2),max(half+.2,extent[:,1].max()+.2))
            ax.set_aspect('equal');ax.legend(fontsize=6);ax.set_title(f"{identity} / {case['scene']} seed{case['index']} / {case['method']} — {'local detail' if column==0 else 'full rollout extent'}",fontsize=9)
    fig.suptitle('Solid: plan; dashed: fixed-path rollout. Failed/censored trajectories are retained.');fig.savefig(OUT/'representatives.png',dpi=140);plt.close(fig)
    keys=['completion_time_s','jerk_rms','curvature_rms','heading_error_rad','lateral_error_m','compute_s'];fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    for ax,key in zip(axes.ravel(),keys):
        data=[];positions=[]
        for i,method in enumerate(COLORS):
            values=[r[key] for r in rows if r['method']==method and r.get(key) is not None]
            if values:data.append(values);positions.append(i);ax.scatter(i+np.linspace(-.1,.1,len(values)),values,c=COLORS[method],s=12,alpha=.6)
        if data:ax.boxplot(data,positions=positions,widths=.4,showfliers=False)
        ax.set_xticks(range(4),list(COLORS));ax.set_title(key);ax.grid(alpha=.15)
    fig.savefig(OUT/'metric_distributions.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),constrained_layout=True);byrow={(r['case_id'],r['method']):r for r in rows}
    for ax,key in zip(axes,('completion_time_s','jerk_rms','lateral_error_m')):
        for identity in sorted({r['case_id'] for r in rows}):
            a,b=byrow[identity,'P0'],byrow[identity,'P2']
            if a.get(key) is not None and b.get(key) is not None:ax.plot([0,1],[a[key],b[key]],'.-',alpha=.5,lw=.7)
        ax.set_xticks([0,1],['P0','P2']);ax.set_title(key)
    fig.savefig(OUT/'paired_P2_P0.png',dpi=140);plt.close(fig)

def generate():
    manifest=json.loads((OUT/'manifest.json').read_text());records=[json.loads(p.read_text()) for p in sorted((OUT/'evaluation').glob('E*.json'))];assert len(records)==24
    rows=[r for item in records for r in item['rows']];stats=summary(rows);verdict=decision(rows);(OUT/'decision.json').write_text(json.dumps(verdict,indent=2)+'\n')
    for name,value in [('snapshots',rows),('summary',stats)]:
        (OUT/f'{name}.csv').unlink(missing_ok=True);csv_write(OUT/f'{name}.csv',value)
    figures(records,rows,manifest['examples']);p=json.loads((ROOT/'research/nomad_phase22/protocol.json').read_text())
    text='# Phase22-O — A* + Graph refinement / offline mechanism validation\n\n'
    text+=f"Frozen weights: `{p['selected']}`. Training26 saved20D/E/F snapshots; evaluation24 final Phase21 B4/M3 A/B triggers. Disjoint run/seed/snapshot identities verified. No Isaac, new render or NoMaD inference. Original files and Phase21 parameters unchanged.\n\n"
    text+='P0 is frozen Phase21 A* R3. P1 is frozen20F seven-start R3, four CPU workers. P2 uses only resampled P0 as initialization plus the registered path-tube, curvature, curvature-change and terminal consistency terms. P3 uses the selected Chaikin strength with three halvings and P0 fallback. P2 failure behavior: '+str(p['p2_failure'])+'.\n\n'
    text+='Every method has the same1s planning budget. P2/P3 include P0 plus transfer/refinement; timings exceeding1s are reported and rejected. Worker initialization is outside the per-snapshot budget, matching the existing runtime. Planning is counterfactually applied at fixed B: solve latency does not move B.\n\n'
    text+='Anchor convention: '+str(p['anchor_mode'])+'. Spawn-preceding odometry is a logged experimental appearance-time input, not an online detector; the two pre-spawn training snapshots use current B rather than future pose. Oracle box/wall coordinates enter only passive evaluation.\n\n'
    complete=OUT/'complete.json'
    if complete.exists():text+='Evaluation frozen Git SHA: `'+json.loads(complete.read_text())['git_sha']+'`.\n\n'
    text+='Summary tables and distribution plots use all available values per method. The registered comparison medians below use only the explicitly reported common safe-completion subset, which is3 snapshots here; these denominators must not be conflated.\n\n'
    text+='## By scene and overall\n\n'+table(stats)+'\n\n## Registered decision\n\n'+table([dict(label=verdict['label'],LOW_N=verdict['LOW_N'],snapshot_n=verdict['snapshot_n'],common_completion_n=verdict['common_completion_n'],side_n=verdict['side_n'],same_side=verdict['same_side'],**verdict['criteria'])])+'\n\n'
    text+='Criteria(iii–v) use the same jointly planned, collision-free completed snapshots across P0/P2/P3; the paired N is shown, no failed or censored time is imputed. Side matching excludes undefined P0 choices and counts missing P2 side as mismatch; no side denominator cannot pass. Wider-gap rates exclude equal-width ties. Front-face/gap intent and actual rear-footprint passage side are separately recorded.\n\n'
    text+=table([dict(method=m,**values) for m,values in verdict['medians'].items()])+'\n\n'
    text+='## All snapshots, including failures\n\n'+table(rows,['case_id','scene','index','source_method','method','disposition','completed','oracle_collision','oracle_minimum_clearance_m','side','side_source','executed_side','compute_s'])+'\n\n'
    for name in ('representatives.png','metric_distributions.png','paired_P2_P0.png'):text+=f'![{name}](../research/results/phase22o/{name})\n\n'
    text+='The controller reuses protected SPAlignment at9/72Hz, with a60s diagnostic cap. Oracle evaluation is passive; collision does not shorten execution to make a method appear faster. The0.30m tube is a distance constraint, not a mathematical homotopy guarantee. A first-stage ALL_UNSAFE snapshot is counterfactually evaluated at the R3 slot for every method; it is not a replay of the original R2 output. The fixed controller can miss its1cm endpoint tolerance and continue until the60s cap; incompletion and the full trajectory are preserved. There is no next FRESH, depth update,3D contact physics or NoMaD reaction. These results cannot establish closed-loop navigation improvement.\n\n'
    if verdict['label'] in ('REFINE_READY','REFINE_PARTIAL'):
        text+='## Draft only — next navigation comparison (DO NOT EXECUTE)\n\nMethods P0/P1/P2, shared frozen selection/fallback/SP/alignment/trigger stack. Scene L2 plus one newly preregistered held-out corridor/box placement; seeds121–124,2×3×4=24 runs, approximately1.3h using Phase21 measured per-run wall time. Freeze held-out geometry before any method run and prohibit tuning/retries except one registered technical retry. Primary goal success and box passage; paired time/jerk and collisions are co-reported. Candidate advancement rule: P2 goal count no worse than both baselines, zero oracle collisions, passage median≤1.05×P0 and jerk median≤.7×P0; otherwise no demonstrated live advantage. Prioritize held-out results and retain all failures. This is a proposal only; no navigation has been scheduled.\n\n'
    text+=verdict['label']+(' / LOW_N' if verdict['LOW_N'] else '')+'\n'
    (ROOT/'docs/PHASE22O_REFINE.md').write_text(text)
