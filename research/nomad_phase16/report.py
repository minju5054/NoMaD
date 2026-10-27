"""CPU-only preregistered multiscene pilot report and narrow result publication."""
import argparse,csv,json,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase0.chunk_report import trace
from nomad_phase12.report import wilson
from .config import METHODS,protocol,scene
from .campaign import read,write
from .geometry import rect
OUT=ROOT/'research/results/phase16';DOC=ROOT/'docs/PHASE16_MULTISCENE.md';PROPOSED='FRESHEST-SAFE+GRAPH-depth'

def csv_write(p,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('x',newline='') as f:
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
            result.append(dict(scene=sc,method=method,planned=6*len(passed) if sc=='ALL' else 6,valid=len(v),technical=len(rr)-len(v),success=sum(r['success'] for r in v),
                no_detour_success=sum(r['no_detour_success'] for r in v),collision=sum(r['collision'] for r in v),corridor=sum(r['corridor'] for r in v),stuck=sum(r['stuck'] for r in v),
                safety_failures=sum(r['collision'] or r['corridor'] for r in v),success_wilson95=wilson(sum(r['success'] for r in v),len(v)),
                goal_time_mean_s=mean('goal_time_s'),checkpoint_mean_s=mean('checkpoint_time_s'),checkpoint_mean_speed_m_s=mean('checkpoint_mean_speed_m_s'),
                minimum_oracle_clearance_m=min((r['minimum_oracle_clearance_m'] for r in v),default=None),curv_slow_fraction=mean('curv_slow_fraction'),
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
    lookup={(r['scene'],r['method']):r for r in gs};delta=2 if len(passed)==1 else 3
    def compare(method):
        a=lookup['ALL',PROPOSED];b=lookup['ALL',method]
        if not passed or a['valid']!=a['planned'] or b['valid']!=b['planned']:return 'PILOT_INCONCLUSIVE'
        if a['success']>=b['success']+delta and a['safety_failures']<=b['safety_failures']:return 'PILOT_GRAPH_HELPS'
        if a['success']<=b['success']-delta:return 'PILOT_GRAPH_HURTS'
        return 'PILOT_GRAPH_EQUAL'
    labels={f'5_vs_{i+1}':compare(METHODS[i]) for i in (0,1,2)}
    a=lookup['ALL',PROPOSED];b=lookup['ALL','FRESHEST-SAFE+GRAPH-GF']
    labels['Q2_all']='PILOT_INCONCLUSIVE' if not passed or a['valid']!=a['planned'] or b['valid']!=b['planned'] else 'PILOT_CONSTRAINT_SAFER' if a['safety_failures']<=b['safety_failures']-2 else 'PILOT_CONSTRAINT_NO_DIFFERENCE'
    labels['Q2_scenes']={sc:('PILOT_INCONCLUSIVE' if lookup[sc,PROPOSED]['sdf_active_fraction'] is None else 'PILOT_CONSTRAINT_ACTIVE' if lookup[sc,PROPOSED]['sdf_active_fraction']>=.05 else 'PILOT_CONSTRAINT_ACTIVITY_BELOW_5_PERCENT') for sc in passed}
    return labels

def pairs(records,passed):
    result=[]
    for sc in [*passed,'ALL']:
        for other in (METHODS[0],METHODS[1],METHODS[2],METHODS[5]):
            lookup={(r['scene'],r['index'],r['method']):r for r in records if r.get('technical_validation')=='PASS' and r.get('checkpoint_time_s') is not None}
            matched=[]
            for s in passed if sc=='ALL' else [sc]:
                for index in range(55,61):
                    a,b=lookup.get((s,index,PROPOSED)),lookup.get((s,index,other))
                    if a and b:matched.append((index,s,a['checkpoint_time_s']-b['checkpoint_time_s']))
            d=np.array([v[2] for v in matched]);ci=None
            if len(d):
                # Shared seed index is the resampling unit across scenes.
                ids=sorted(set(v[0] for v in matched));clusters=[np.array([v[2] for v in matched if v[0]==i]) for i in ids]
                rng=np.random.default_rng(20261028);draws=rng.integers(0,len(ids),(20000,len(ids)))
                sums=np.array([v.sum() for v in clusters]);n=np.array([len(v) for v in clusters]);boot=sums[draws].sum(axis=1)/n[draws].sum(axis=1);ci=np.quantile(boot,[.025,.975]).tolist()
            result.append(dict(scene=sc,method=PROPOSED,comparator=other,n=len(d),mean_difference_s=float(d.mean()) if len(d) else None,ci95_s=ci,negative_pairs=int(sum(d<0)),resampling='paired seed clusters across scenes'))
    return result

def figures(root,records,gs,passed):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    colors=plt.get_cmap('tab10').colors
    from .preflight import inspection_plot
    for sc in ('SL','LC','CL'):
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
        vals=[next(g['success'] for g in gs if g['scene']==s and g['method']==m) for s in passed];ax.bar(x+(i-2.5)*width,vals,width,label=m)
    ax.set_xticks(x,passed);ax.set_ylim(0,6.5);ax.set_ylabel('PILOT successes / 6');ax.legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'success_by_scene.png',dpi=150);plt.close(fig)

def publish():
    paths=['docs/PHASE16_MULTISCENE.md','research/results/phase16']
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    images=list(OUT.glob('*.png'))
    if images:subprocess.run(['git','add','-f','--',*[str(p.relative_to(ROOT)) for p in images]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase16 multiscene depth pilot'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def render(root):
    assert (root/'complete.json').exists();gates=read(root/'gates.json');passed=[s for s,v in gates.items() if v=='PASS'];records=[read(p) for p in sorted((root/'metrics').glob('main_*.json'))]
    assert len(records)==len(passed)*36
    if OUT.exists():assert read(OUT/'runs.json')==records and DOC.exists();return
    OUT.mkdir(parents=True);gs=groups(records,passed);paired=pairs(records,passed);labels=judgments(gs,passed)
    write(OUT/'runs.json',records);write(OUT/'decisions.json',labels);write(OUT/'resolved_protocol.json',read(root/'resolved_protocol.json'));csv_write(OUT/'summary.csv',gs);csv_write(OUT/'paired.csv',paired)
    figures(root,records,gs,passed)
    text='# Phase 16 — multiscene depth PILOT\n\nOracle geometry is used only for reference demonstration preparation and posthoc evaluation. All six methods use RGB-only NoMaD, the same noisy V1 depth map infrastructure, exact simulator odometry, and SE(2) kinematics. No PhysX/real-robot claim. Methods 1–5 share the depth sample-selection rule; closed-loop observations can differ. Original sample-0 TE is an external baseline.\n\n'
    text+='Reference preparation is an oracle-guided human-demonstration analogue. The center-distance target is 0.25m from both obstacles and walls (not footprint clearance); sub-0.5m passages use a geometrically verified centerline exception if needed. The frozen clearance-weighted, smoothed path defines reference_length_m; the old shortest-grid length remains diagnostic only. Topomap uses actual Isaac RGB along the fixed PP reference rollout at 2s spacing including start/terminal; NoMaD never receives the route world poses. Static rendering features/camera and all solver weights remain frozen.\n\n'
    text+='Scenes and map manifests\n\n'+table([dict(scene=s,reference_length_m=scene(s)['reference_length_m'],reference=scene(s)['reference_preparation'],offline_pp=scene(s)['reference_offline_pp_check'],checkpoint=scene(s)['checkpoint'],map=read(root/'resolved_protocol.json')['topomaps'].get(s),gate=gates[s]) for s in ('SL','LC','CL')])+'\n\n'
    gate_runs=[read(p) for p in sorted((root/'metrics').glob('gate_*.json'))];text+='Gate attempts (excluded from main results)\n\n'+table(gate_runs,['scene','index','success','classification','technical_validation'])+'\n\n'
    text+='Main summary\n\n'+table(gs,['scene','method','planned','valid','technical','success','no_detour_success','collision','corridor','stuck','goal_time_mean_s','checkpoint_mean_s','minimum_oracle_clearance_m'])+'\n\n'
    text+='Seed × scene × method\n\n'+table(records,['index','scene','method','classification','goal_time_s','checkpoint_time_s','distance_m','no_detour_success'])+'\n\n'
    text+='Preregistered PILOT decisions\n\n```json\n'+json.dumps(labels,indent=2)+'\n```\n\n'
    text+='Fallback / Graph / depth metrics\n\n'+table(gs,['scene','method','keep_active_events','stop_wait_events','keep_active_fraction','stop_wait_fraction','te_removed_chunks','te_expired_chunks_at_fallback','graph_calls','graph_acceptance','initialization_rejected','solve_run_median_mean_s','solve_run_p95_mean_s','sdf_active_fraction','dangerous_false_safe_count','unknown_fraction_mean','depth_update_run_p95_mean_ms'])+'\n\n'
    text+='Q3: unknown-risk path points and spatially associated safety failures (within 0.12m of the terminal footprint center)\n\n'+table([g for g in gs if g['scene']=='LC'],['method','unknown_risky_path_points','unknown_associated_safety_failures'])+'\n\nUnknown-associated events are not causal proof; the number of failures caused by unknown geometry is not identifiable from these logs alone. Counts are descriptive and not used in a decision label.\n\n'
    text+='Paired checkpoint differences\n\n'+table(paired)+'\n\n20,000 bootstrap replicates, seed 20261028; across scenes the paired seed index is resampled as a cluster. Missing checkpoints are never imputed. Timing aggregates are averages of run-level median/p95. Technical failures remain in the table; affected efficacy comparisons are inconclusive.\n\n'
    text+='Technical failures\n\n'+table([r for r in records+gate_runs if r['technical_validation']!='PASS'],['scene','index','method','error'])+'\n\n'
    for f in sorted(OUT.glob('*.png')):text+=f'![{f.stem}](../research/results/phase16/{f.name})\n\n'
    text+='Smoke and reference/gate results are excluded from the main experimental denominators. KEEP_ACTIVE preserves path progress; STOP_WAIT decelerates rather than instantaneously repairing a safety violation. SAFE+TE filters existing, unexpired components only at ALL_UNSAFE events, inserts no unsafe chunk, retains only safe suffixes of length >=0.25m, and renormalizes the original oldest-first exp(-0.5k) weights. Expiry remains one second; other ticks use unchanged Phase12 TE.\n'
    DOC.write_text(text)
def main():
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,required=True);p.add_argument('--publish',action='store_true');a=p.parse_args();render(a.run_root.resolve())
    if a.publish:publish()
    print(json.dumps(read(OUT/'decisions.json')))
if __name__=='__main__':main()
