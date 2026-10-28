"""CPU-only preregistered multiscene pilot report and narrow result publication."""
import argparse,csv,json,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase0.chunk_report import trace
from nomad_phase12.report import wilson
from .config import METHODS,protocol,scene
from .campaign import read,write
from nomad_phase16.geometry import rect
OUT=ROOT/'research/results/phase17';DOC=ROOT/'docs/PHASE17_RECOVERY_CLR.md';PROPOSED='FRESHEST-SAFE+GRAPH-depth-CLR'
from .offline_report import offline_report

def csv_write(p,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
def table(rows,keys=None):
    if not rows:return 'None.'
    keys=keys or list(rows[0]);fmt=lambda x:f'{x:.5g}' if isinstance(x,float) else '—' if x is None else str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(keys)+' |','| '+' | '.join(['---']*len(keys))+' |']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])
def groups(records,passed):
    result=[]
    for sc in [*passed,'ALL']:
        for method in METHODS:
            rr=[r for r in records if r['method']==method and (sc=='ALL' or r['scene']==sc)];v=[r for r in rr if r.get('technical_validation')=='PASS']
            def mean(key):
                x=[r[key] for r in v if r.get(key) is not None];return float(np.mean(x)) if x else None
            def nested(section,key):
                x=[r[section][key] for r in v if r.get(section,{}).get(key) is not None];return float(np.mean(x)) if x else None
            accepted=sum(r['graph_accepted'] for r in v);calls=sum(r['graph_calls'] for r in v)
            result.append(dict(scene=sc,method=method,planned=5*len(passed) if sc=='ALL' else 5,valid=len(v),technical=len(rr)-len(v),success=sum(r['success'] for r in v),
                no_detour_success=sum(r['no_detour_success'] for r in v),collision=sum(r['collision'] for r in v),corridor=sum(r['corridor'] for r in v),stuck=sum(r['stuck'] for r in v),
                safety_failures=sum(r['collision'] or r['corridor'] for r in v),success_wilson95=wilson(sum(r['success'] for r in v),len(v)),
                goal_time_mean_s=mean('goal_time_s'),checkpoint_mean_s=mean('checkpoint_time_s'),checkpoint_mean_speed_m_s=mean('checkpoint_mean_speed_m_s'),
                minimum_oracle_clearance_m=min((r['minimum_oracle_clearance_m'] for r in v),default=None),curv_slow_fraction=mean('curv_slow_fraction'),
                recovery_count=sum(r.get('recovery_count',0) for r in v),recovery_fraction=mean('recovery_time_fraction'),
                post_recovery_safe_fraction=sum(r.get('recovery_safe_outcomes',0) for r in v)/sum(r.get('recovery_observed_outcomes',0) for r in v) if sum(r.get('recovery_observed_outcomes',0) for r in v) else None,
                recovery_limit_runs=sum(r.get('recovery_count',0)>=12 for r in v),
                clearance_delta_median=pooled(v,'accepted_clearance_delta_m','median'),clearance_active_fraction=sum(r.get('clearance_active_jobs',0) for r in v)/sum(r.get('clearance_solved_jobs',0) for r in v) if sum(r.get('clearance_solved_jobs',0) for r in v) else None,
                keep_active_events=sum(r['fallback_events'].get('KEEP_ACTIVE',0) for r in v),stop_wait_events=sum(r['fallback_events'].get('STOP_WAIT',0) for r in v),
                te_removed_chunks=sum(r.get('te_removed_chunks',0) for r in v),te_expired_chunks_at_fallback=sum(r.get('te_expired_chunks_at_fallback',0) for r in v),
                keep_active_fraction=float(np.mean([r['fallback_time_fraction']['KEEP_ACTIVE'] for r in v])) if v else None,
                stop_wait_fraction=float(np.mean([r['fallback_time_fraction']['STOP_WAIT'] for r in v])) if v else None,
                graph_calls=calls,graph_accepted=accepted,graph_acceptance=accepted/calls if calls else None,initialization_rejected=sum(r['graph_initialization_rejected'] for r in v),
                solve_run_median_mean_s=nested('solve_time_s','median'),solve_run_p95_mean_s=nested('solve_time_s','p95'),
                sdf_active_fraction=sum(r['sdf_active_count'] or 0 for r in v)/accepted if accepted and method==PROPOSED else None,
                dangerous_false_safe_count=sum(r['dangerous_false_safe_count'] for r in v),unknown_fraction_mean=nested('selected_unknown_fraction','median'),depth_update_run_median_mean_ms=nested('depth_update_ms','median'),depth_update_run_p95_mean_ms=nested('depth_update_ms','p95'),
                unknown_risky_path_points=sum(r['unknown_risky_path_points'] for r in v),unknown_associated_safety_failures=sum(r['unknown_associated_safety_failure'] for r in v)))
    return result

def judgments(gs,passed):
    lookup={(r['scene'],r['method']):r for r in gs};threshold=2 if len(passed)<=2 else 3
    def compare(other,metric='success',prefix=''):
        a=lookup['ALL',PROPOSED];b=lookup['ALL',other]
        if not passed or a['valid']!=a['planned'] or b['valid']!=b['planned']:return 'PILOT_INCONCLUSIVE'
        if a[metric]>=b[metric]+threshold and a['safety_failures']<=b['safety_failures']:return 'PILOT_'+prefix+('HELPS' if prefix else 'BETTER')
        if a[metric]<=b[metric]-threshold:return 'PILOT_'+prefix+('HURTS' if prefix else 'WORSE')
        return 'PILOT_'+prefix+'EQUAL'
    labels={'P1_CLEARANCE_TERM':compare(METHODS[4],prefix='CLR_'),'threshold':threshold}
    for i in (0,1,2,3,6):
        labels[f"{'P3' if i==6 else 'P2'}_6_vs_{i+1}"]=compare(METHODS[i])
        labels[f'no_detour_6_vs_{i+1}']=compare(METHODS[i],'no_detour_success')
    return labels

def pairs(records,passed):
    result=[]
    for sc in [*passed,'ALL']:
        for other in METHODS[:5]:
            lookup={(r['scene'],r['index'],r['method']):r for r in records if r.get('technical_validation')=='PASS' and r.get('checkpoint_time_s') is not None}
            matched=[]
            for s in passed if sc=='ALL' else [sc]:
                for index in range(61,66):
                    a,b=lookup.get((s,index,PROPOSED)),lookup.get((s,index,other))
                    if a and b:matched.append((index,s,a['checkpoint_time_s']-b['checkpoint_time_s']))
            d=np.array([v[2] for v in matched]);ci=None
            if len(d):
                # Shared seed index is the resampling unit across scenes.
                ids=sorted(set(v[0] for v in matched));clusters=[np.array([v[2] for v in matched if v[0]==i]) for i in ids]
                rng=np.random.default_rng(20261029);draws=rng.integers(0,len(ids),(20000,len(ids)))
                sums=np.array([v.sum() for v in clusters]);n=np.array([len(v) for v in clusters]);boot=sums[draws].sum(axis=1)/n[draws].sum(axis=1);ci=np.quantile(boot,[.025,.975]).tolist()
            result.append(dict(scene=sc,method=PROPOSED,comparator=other,n=len(d),mean_difference_s=float(d.mean()) if len(d) else None,ci95_s=ci,negative_pairs=int(sum(d<0)),resampling='paired seed clusters across scenes'))
    return result

def figures(root,records,gs,passed):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    colors=plt.get_cmap('tab10').colors
    from nomad_phase16.preflight import inspection_plot
    for sc in ('SLW','LC','CL'):
        folder=root/'topomap'/sc
        if (folder/'start_occupancy.npz').exists():inspection_plot(folder,OUT/f'scene_{sc}.png')
    def pathplot(rr,sc,target):
        c=scene(sc);fig,ax=plt.subplots(figsize=(11,6))
        for r in rr:
            run=Path(r['output']);file=run/'agent_trajectory.csv'
            if not file.exists():continue
            _,p=trace(run);j=METHODS.index(r['method']);ax.plot(p[:,0],p[:,1],color=colors[j],label=r['method']);ax.scatter(*p[-1,:2],marker='x',color=colors[j])
            if r['method']==PROPOSED and (run/'depth/final.npz').exists():
                with np.load(run/'depth/final.npz') as z:
                    y,x=np.nonzero(z['occupied']);xy=z['origin']+np.column_stack([x,y])*float(z['h']);ax.scatter(xy[:,0],xy[:,1],color='.7',s=.3,alpha=.3)
        for b in c['obstacles']:
            x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='.5',alpha=.4))
        x0,x1,y0,y1=rect(c);ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,color='black'));ax.set_xlim(x0-.1,x1+.1);ax.set_ylim(y0-.1,y1+.1);ax.set_aspect('equal');ax.legend(fontsize=7);ax.set_title(sc+' | PILOT; oracle geometry shown only for evaluation');fig.tight_layout();fig.savefig(target,dpi=150);plt.close(fig)
    for sc in passed:
        rr=[r for r in records if r['scene']==sc and r['index']==55];pathplot(rr,sc,OUT/f'paths_{sc}.png')
    for r in records:
        if r.get('classification')=='SAFETY_FAILURE':pathplot([r],r['scene'],OUT/f"failure_{r['scene']}_{r['method']}_{r['index']}.png")
    fig,ax=plt.subplots(figsize=(12,5));x=np.arange(len(passed));width=.12
    for i,m in enumerate(METHODS):
        vals=[next(g['success'] for g in gs if g['scene']==s and g['method']==m) for s in passed];ax.bar(x+(i-3)*width,vals,width,label=m)
    ax.set_xticks(x,passed);ax.set_ylim(0,5.5);ax.set_ylabel('PILOT successes / 5');ax.legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'success_by_scene.png',dpi=150);plt.close(fig)

def publish():
    paths=['docs/PHASE17_RECOVERY_CLR.md','research/results/phase17']
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    images=list(OUT.glob('*.png'))
    if images:subprocess.run(['git','add','-f','--',*[str(p.relative_to(ROOT)) for p in images]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase17 multiscene depth pilot'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def render(root):
    assert (root/'complete.json').exists();gates=read(root/'gates.json');passed=[s for s,v in gates.items() if v=='PASS'];records=[read(p) for p in sorted((root/'metrics').glob('main_*.json'))]
    assert len(records)==len(passed)*35
    if (OUT/'runs.json').exists():assert read(OUT/'runs.json')==records
    OUT.mkdir(parents=True,exist_ok=True);gs=groups(records,passed);paired=pairs(records,passed);labels=judgments(gs,passed)
    write(OUT/'runs.json',records);write(OUT/'decisions.json',labels);write(OUT/'resolved_protocol.json',read(root/'resolved_protocol.json'));csv_write(OUT/'summary.csv',gs);csv_write(OUT/'paired.csv',paired)
    figures(root,records,gs,passed)
    text='# Phase 17 — recovery + clearance preference PILOT\n\nOracle geometry is used only for reference demonstration preparation and posthoc evaluation. All seven methods use RGB-only NoMaD, the same noisy V1 depth map infrastructure, exact simulator odometry, and SE(2) kinematics. No PhysX/real-robot claim. Methods 1–6 share depth selection, fallback and recovery; closed-loop observations can differ. Original sample-0 TE is an external baseline.\n\n'
    text+='Reference preparation is an oracle-guided human-demonstration analogue. The center-distance target is 0.25m from both obstacles and walls (not footprint clearance); sub-0.5m passages use a geometrically verified centerline exception if needed. The frozen clearance-weighted, smoothed path defines reference_length_m; the old shortest-grid length remains diagnostic only. Topomap uses actual Isaac RGB along the fixed PP reference rollout at 2s spacing including start/terminal; NoMaD never receives the route world poses. Static rendering features/camera and existing solver weights remain frozen; only method 6 adds the declared CLR residual.\n\n'
    text+='Scenes and map manifests\n\n'+table([dict(scene=s,reference_length_m=scene(s)['reference_length_m'],reference=scene(s)['reference_preparation'],offline_pp=scene(s)['reference_offline_pp_check'],checkpoint=scene(s)['checkpoint'],map=read(root/'resolved_protocol.json')['topomaps'].get(s),gate=gates[s]) for s in ('SLW','LC','CL')])+'\n\n'
    text+='SLW: 1.8m-wide slalom corridor with three alternating wall-attached boxes and 0.8m passages. LC: asymmetric [-1,4.2]² outer rectangle, a large inner-corner wall box, and an initially occluded after-corner obstacle. CL: unchanged Phase16 boxes from placement seed 20261028; placements and reference routes are never adjusted to navigation outcomes.\n\n'
    gate_runs=[read(p) for p in sorted((root/'metrics').glob('gate_*.json'))];text+='Gate attempts (excluded from main results)\n\n'+table(gate_runs,['scene','index','success','classification','technical_validation'])+'\n\n'
    text+='NOMAD_INFEASIBLE is the prescribed operational exclusion label for this particular D0 SAFE+RECOVER_ROTATE gate, not a proof of geometric impossibility or an isolated failure of the NoMaD policy.\n\n'
    text+='Main summary\n\n'+table(gs,['scene','method','planned','valid','technical','success','no_detour_success','collision','corridor','stuck','goal_time_mean_s','checkpoint_mean_s','minimum_oracle_clearance_m'])+'\n\n'
    text+='Seed × scene × method\n\n'+table(records,['index','scene','method','classification','goal_time_s','checkpoint_time_s','distance_m','no_detour_success'])+'\n\n'
    text+='Preregistered PILOT decisions\n\n```json\n'+json.dumps(labels,indent=2)+'\n```\n\n'
    text+='Fallback / Graph / depth metrics\n\n'+table(gs,['scene','method','recovery_count','recovery_fraction','post_recovery_safe_fraction','recovery_limit_runs','clearance_delta_median','clearance_active_fraction','keep_active_events','stop_wait_events','keep_active_fraction','stop_wait_fraction','te_removed_chunks','te_expired_chunks_at_fallback','graph_calls','graph_acceptance','initialization_rejected','solve_run_median_mean_s','solve_run_p95_mean_s','sdf_active_fraction','dangerous_false_safe_count','unknown_fraction_mean','depth_update_run_p95_mean_ms'])+'\n\n'
    text+='Q3: unknown-risk path points and spatially associated safety failures (within 0.12m of the terminal footprint center)\n\n'+table([g for g in gs if g['scene']=='LC'],['method','unknown_risky_path_points','unknown_associated_safety_failures'])+'\n\nUnknown-associated events are not causal proof; the number of failures caused by unknown geometry is not identifiable from these logs alone. All active TE component paths are included at application events. STOP_WAIT is excluded from path-following association; braking is not a certified trajectory. Rejected ALL_UNSAFE candidate uncertainty is recorded separately from newly selected safe paths. Counts are descriptive and not used in a decision label.\n\n'
    text+='Paired checkpoint differences\n\n'+table(paired)+'\n\n20,000 bootstrap replicates, seed 20261029; across scenes the paired seed index is resampled as a cluster. Missing checkpoints are never imputed. Timing aggregates are averages of run-level median/p95. Technical failures remain in the table; affected efficacy comparisons are inconclusive.\n\n'
    text+='Technical failures\n\n'+table([r for r in records+gate_runs if r['technical_validation']!='PASS'],['scene','index','method','error'])+'\n\n'
    for f in sorted(OUT.glob('*.png')):text+=f'![{f.stem}](../research/results/phase17/{f.name})\n\n'
    text+='Smoke and reference/gate results are excluded from the main experimental denominators. KEEP_ACTIVE preserves path progress; STOP_WAIT decelerates rather than instantaneously repairing a safety violation. SAFE+TE filters existing, unexpired components only at ALL_UNSAFE events, inserts no unsafe chunk, retains only safe suffixes of length >=0.25m, and renormalizes the original oldest-first exp(-0.5k) weights. Expiry remains one second; other ticks use unchanged Phase12 TE.\n'
    text+=extended_report(root,records,gs)
    DOC.write_text(text)
def main():
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,required=True);p.add_argument('--publish',action='store_true');a=p.parse_args();render(a.run_root.resolve())
    if a.publish:
        publish();complete=read(a.run_root/'complete.json');complete['report_complete']=True;write(a.run_root/'complete.json',complete)
    print(json.dumps(read(OUT/'decisions.json')))

def pooled(records,key,stat):
    values=[x for r in records for x in r.get(key,[])]
    return float(np.median(values)) if values else None

def extended_report(root,records,gs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from .metrics import rows
    offline=read(OUT/'offline_summary.json')
    text='\nOffline readiness (391 fixed inputs; one attempt each)\n\n'+table([dict(label=offline['label'],
        baseline_acceptance_bounds=[offline['baseline_acceptance_lower'],offline['baseline_acceptance_upper']],
        clr_acceptance=offline['clr_acceptance'],attempt_time_s=offline['clr_attempt_wall_s'],
        solver_started_time_s=offline['clr_started_attempt_wall_s'])])+'\n\n'
    text+='Only method 6 adds `max(0, (0.15 − d_depth)/0.05)` at the existing 9 points per segment. All hard constraints, exact depth certificate and other constants are unchanged. The offline timing excludes file I/O and oracle evaluation. Missing baseline worker results remain explicit bounds.\n\n'
    text+='Recovery: two consecutive STOP_WAIT FRESH decisions and actual v<0.01 trigger up to 12 turns. ±30° depth rays are sampled every 1cm including B, maximum 2m; longer ray wins, ties turn left. Rotation uses v=0, |ω|=0.3 and ends exactly at 30° with a shortened final 72Hz interval. NoMaD/RGB continue; intermediate FRESH selections are deferred and Graph results discarded. The next FRESH after rotation resumes normal selection. No oracle direction or goal input is used.\n\n'
    mechanisms=[]
    for method in METHODS[3:6]:
        rr=[r for r in records if r['method']==method and r.get('technical_validation')=='PASS']
        delta=[v for r in rr for v in r.get('accepted_clearance_delta_m',[])]
        clearance=[r['minimum_obstacle_clearance_m'] for r in rr]
        def dist(x):return dict(median=float(np.median(x)),p10=float(np.quantile(x,.1)),p90=float(np.quantile(x,.9))) if x else None
        mechanisms.append(dict(method=method,accepted_correction_delta_m=dist(delta),run_min_obstacle_clearance_m=dist(clearance),
            delta_median_nonnegative=bool(np.median(delta)>=0) if delta else None))
    text+='Clearance mechanisms (posthoc oracle evaluation only)\n\n'+table(mechanisms)+'\n\n'
    old=read(ROOT/'research/results/phase16/runs.json',[])
    comparison=[]
    for method in METHODS:
        for sc in ('SLW','LC','CL'):
            prior_scene='SL' if sc=='SLW' else sc
            a=[r for r in records if r['scene']==sc and r['method']==method and r.get('technical_validation')=='PASS']
            b=[r for r in old if r['scene']==prior_scene and r['method']==method and r.get('technical_validation')=='PASS']
            comparison.append(dict(scene=sc,method=method,phase17_n=len(a),phase17_stuck=sum(r['stuck'] for r in a),phase16_n=len(b),phase16_stuck=sum(r['stuck'] for r in b)))
    text+='Phase16 stuck reference\n\n'+table(comparison)+'\n\nDifferent seeds, changed SLW geometry and recovery imply this is not a paired or causal comparison. SL had no Phase16 main runs. No recovery is claimed for original TE.\n\n'
    fig,ax=plt.subplots(figsize=(9,4));data=[];labels=[]
    for method in METHODS[3:6]:
        x=[v*100 for r in records if r['method']==method for v in r.get('accepted_clearance_delta_m',[])]
        if x:data.append(x);labels.append(method.replace('FRESHEST-SAFE+',''))
    if data:ax.boxplot(data,labels=labels,showfliers=False)
    ax.axhline(0,color='k',lw=.8);ax.set_ylabel('Corrected − selected native clearance (cm)');fig.tight_layout();fig.savefig(OUT/'clearance_delta.png',dpi=150);plt.close(fig)
    example=next((r for r in records if r.get('recovery_count',0)),None)
    fig,ax=plt.subplots(figsize=(8,5))
    if example:
        _,pose=trace(Path(example['output']));ax.plot(pose[:,0],pose[:,1],color='black')
        for e in rows(Path(example['output'])/'recovery.jsonl'):
            if e['event']=='START':ax.scatter(*e['pose'][:2],c='red',marker='o');ax.annotate(str(e['recovery_id']),e['pose'][:2])
        ax.set_title(example['key']);ax.set_aspect('equal');text+='Recovery example: '+example['key']+'\n\n'
    else:ax.text(.5,.5,'No recovery event recorded',ha='center',transform=ax.transAxes)
    fig.tight_layout();fig.savefig(OUT/'recovery_example.png',dpi=150);plt.close(fig)
    for name in ('clearance_delta','recovery_example'):text+=f'![{name}](../research/results/phase17/{name}.png)\n\n'
    text+='All decisions are PILOT labels. New-seed closed-loop outcomes include recovery and observation changes; no isolated Graph causal superiority is inferred.\n'
    return text

if __name__=='__main__':main()
