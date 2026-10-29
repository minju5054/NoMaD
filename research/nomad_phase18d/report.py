"""Saved results only; no solve or controller invocation during report generation."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase17.report import table
from nomad_phase0.graph_v4 import menger
from nomad_phase16.geometry import rect
from .diagnose import CLR,stats

def render(out,summary,inputs,failures,terms,combo_summary,selection,replace_presentation=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Rectangle
    final=[r for r in failures if r['row_type']=='FINAL_CAUSE']
    for r in [r for r in final if r['method']==CLR]:
        d=inputs.cache[r['run']];last=max(d['jobs'].values(),key=lambda j:j['switch_sim_s']) if d['jobs'] else None
        raw=np.asarray(r.get('raw') if r.get('raw') is not None else last['world_xy'])
        path=r.get('path');kind=r['path_kind']
        if path is None and last:
            result=d['results'].get(last['job_id'])
            if result and result.get('poses') is not None:path=np.array(result['poses'])[:,:2];kind='Last returned iterate; not active at termination'
        fig,ax=plt.subplots(figsize=(10,5))
        for xy,style,label in ((raw,'--','Selected native'),(path,'-','Applied/returned path')):
            if xy is None:continue
            xy=np.asarray(xy);ax.plot(xy[:,0],xy[:,1],ls=style,color='.5',lw=1,label=label)
            if len(xy)>=3:
                k=np.abs(menger(xy)[0]);values=np.r_[k[0],k]
                lc=LineCollection(np.stack([xy[:-1],xy[1:]],axis=1),cmap='viridis',norm=plt.Normalize(0,8),linestyles=style,linewidths=2.5)
                lc.set_array(values);ax.add_collection(lc)
        ax.plot(d['poses'][:,0],d['poses'][:,1],color='black',lw=1,label='Actual recorded robot')
        ax.scatter(*d['poses'][-1,:2],marker='x',color='red',s=70)
        B=r.get('B',last['boundary']);ax.scatter(*B[:2],marker='o',color='orange',label='B')
        for b in d['config']['obstacles']:
            x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='.6',alpha=.35))
        xmin,xmax,ymin,ymax=rect(d['config']);ax.add_patch(Rectangle((xmin,ymin),xmax-xmin,ymax-ymin,fill=False,color='k'))
        fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0,8),cmap='viridis'),ax=ax,label='|Menger curvature| (1/m), clipped display at 8')
        ax.set_aspect('equal');ax.set_title(f"SLW {r['index']} CLR: {r['label']}\n{kind}");ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/f"slw_curvature_{r['index']}.png",dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4));variants=['CLR','NO_PROGRESS','NO_CLEARANCE','NO_BOTH']
    for i,v in enumerate(variants):
        rr=[r for r in terms if r['variant']==v and r['accepted'] and r.get('turn') and r.get('curvature_ratio') is not None]
        x=[r['curvature_ratio'] for r in rr]
        if x:ax.scatter(i+np.linspace(-.15,.15,len(x)),x,s=20);ax.plot([i-.2,i+.2],[np.median(x)]*2,c='k',lw=3)
        ax.annotate(f'n={len(x)}',(i,.95),xycoords=('data','axes fraction'),ha='center',fontsize=8)
    ax.axhline(.8,ls='--',color='.5');ax.set_xticks(range(4),variants);ax.set_ylabel('Corrected/native peak curvature ratio');fig.tight_layout();fig.savefig(out/'term_attribution.png',dpi=150);plt.close(fig)
    common=[r for r in combo_summary if r['scope']=='ALL_PATHS_COMMON_VALID'];lookup={(r['scene'],r['path_type'],r['speed']):r for r in common}
    fig,ax=plt.subplots(figsize=(11,5));colors=plt.get_cmap('tab10').colors
    path_order=['FRESHEST-SAFE','HERMITE','CLR','K','KP'];checks={(r['path_type'],r['speed']):r for r in selection['checks']}
    for (sc,p,s),a in lookup.items():
        if sc!='SLW':continue
        b=lookup['CL',p,s]
        if b['mean_progress_m'] is None:continue
        chosen=selection['chosen'] and (p,s)==(selection['chosen']['path_type'],selection['chosen']['speed'])
        check=checks.get((p,s),{});failed=check and not(check['timing_pass'] and check['acceptance_pass'])
        label=f"{p}+{s}: ({a['overlap']}, {b['mean_progress_m']:.4f})"+(' [solve gate fail]' if failed else '')+(' [selected]' if chosen else '')
        ax.scatter(a['overlap'],b['mean_progress_m'],marker='*' if chosen else '^' if s=='SP' else 'o',
            s=150 if chosen else 50,color=colors[path_order.index(p)],label=label,facecolors='none' if failed else colors[path_order.index(p)])
    ax.set_xticks(sorted({r['overlap'] for r in common if r['scene']=='SLW'}));ax.margins(x=.12)
    ax.set_xlabel('SLW negative-clearance rollout count (common cases)');ax.set_ylabel('CL mean travel distance (m)')
    ax.legend(loc='center left',bbox_to_anchor=(1.01,.5),fontsize=8);fig.tight_layout();fig.savefig(out/'combo_tradeoff.png',dpi=150);plt.close(fig)
    example=out/'speed_example.json';fig,axs=plt.subplots(2,1,figsize=(8,6),sharex=True)
    if example.exists():
        e=json.loads(example.read_text())
        for rule in ('CURV','SP'):
            r=e[rule];t=np.arange(len(r['speeds']))/72;axs[0].plot(t,r['speeds'],label=rule);axs[1].plot(t,r['omegas'],label=rule)
        axs[0].set_title(f"Same saved CLR path: {e['run']}, FRESH {e['fresh_id']}")
    else:axs[0].text(.5,.5,'No common accepted turning example',ha='center',transform=axs[0].transAxes)
    for ax in axs:ax.legend();ax.grid(alpha=.2)
    axs[0].set_ylabel('v (m/s)');axs[1].set_ylabel('omega (rad/s)');axs[1].set_xlabel('Offline elapsed seconds');fig.tight_layout();fig.savefig(out/'speed_profile_example.png',dpi=150);plt.close(fig)
    text='# Phase 18-D — curvature and anticipatory speed offline diagnosis\n\n'
    text+=f"Execution SHA: `{summary['git_sha']}`. **{summary['regression']['label']}**, max position error {summary['regression']['maximum_position_error_m']:.9g} m. No Isaac navigation, NoMaD inference or rendering was run.\n\n"
    text+='A fixed path is followed from the recorded B for at most 1.5 seconds. There is no future FRESH, regeneration, depth update, waypoint expiry or recovery in these counterfactuals. Oracle geometry is used solely for post-interval evaluation/termination. PP and speed targets never receive it. These rollouts cannot replace closed-loop navigation evidence.\n\n'
    text+='## Measurement protocol\n\n```json\n'+json.dumps(summary['protocol'],indent=2,ensure_ascii=False)+'\n```\n\n'
    text+='## Regression\n\n'+table(summary['regression_rows'])+'\n\n'
    text+='## A: failure labels\n\n'+table(final,['run','method','classification','path_kind','label','native_kappa_max','path_kappa_max','curvature_ratio','dominant_sign_agrees','mean_speed_m_s','omega_saturation_fraction','clearance_off_wall_gain_m'])+'\n\n'
    text+='Last three actual FRESH decisions (mode changes and unavailable paths retained)\n\n'+table([r for r in failures if r['row_type']=='FRESH'],['run','id','start_s','end_s','fallback','path_kind','native_kappa_max','path_kappa_max','curvature_ratio','mean_speed_m_s','omega_saturation_fraction','max_cross_track_m','minimum_obstacle_clearance_m','minimum_wall_clearance_m','safe_same_box'])+'\n\n'
    text+='## Factor removal, one solve per variant per final submitted job\n\n'+table(terms,['run','fresh_id','variant','disposition','curvature_ratio','path_wall_clearance_m','rollout_minimum_clearance_m','rollout_overlap','stored_regression_path_error_m'])+'\n\n'
    text+='Paired accepted turning solutions: ratio change relative to CLR\n\n'+table(summary['term_contributions'])+'\n\n'
    text+='Only 1–2 accepted turning pairs support each factor-removal comparison here; their changes do not identify a robust progress/clearance-factor cause. The unchanged hard curvature limit is 8/m. When native curvature exceeds 8/m, the new soft preservation residual cannot reach zero while satisfying that hard constraint.\n\n'
    clr_final=[r for r in final if r['method']==CLR]
    text+='CLR final executed path kinds: '+json.dumps(dict(Counter(r['path_kind'] for r in clr_final)))+'. In particular, a native fallback failure is not a failure while executing a corrected path.\n\n'
    text+='Final submitted jobs can differ from the path actually executed at failure. CLEARANCE_PUSH requires the tested job to match the final active correction; unavailable/rejected solutions are never treated as applied paths. Labels follow the prescribed first-match order and are mechanism candidates, not isolated causal proofs.\n\n'
    text+='## B: identical-case comparison\n\n'+table(common,['scene','path_type','speed','n','overlap','negative_witness','conservative_only_negative','margin_violation','mean_progress_m','mean_speed_m_s','omega_saturation_fraction','maximum_cross_track_m','endpoint_stops','curvature_ratio'])+'\n\n'
    text+='Graph acceptance uses all actual submitted inputs, including zero-speed initialization rejections. A missing saved worker result has an explicit acceptance interval. Stored CLR timing and new sequential CPU timing were collected under different load.\n\n'+table(summary['graph_summary'])+'\n\n'
    text+='Coverage (all requested FRESH, all ten rows per FRESH, never omitted)\n\n'+table(summary['coverage'])+'\n\n'
    text+='Method-available descriptive rows are also saved in combo_summary.csv; primary pairing uses the common accepted-path intersection. This conditioning limits generalization and is not a failure-free claim about the original pipeline. STOP_WAIT/deferred/absent/rejected graph cases remain explicitly unavailable rather than receiving a fabricated trajectory.\n\n'
    text+='## Preregistered selection and SP_FAIRNESS\n\n'+table(selection['checks'])+'\n\n'+table(selection['SP_FAIRNESS'],['scene','path_type','speed','n','overlap','mean_progress_m'])+'\n\n'
    text+=f"**{selection['label']}**. This is same-data offline selection. Confirmation requires new seeds and new scenes in real closed-loop runs.\n\n"
    for f in sorted(out.glob('*.png')):text+=f'![{f.stem}](../research/results/phase18d/{f.name})\n\n'
    text+='All rejected solves and cases are preserved. No outcome-based tuning or retry was used.\n'
    with (ROOT/'docs/PHASE18D_CURVATURE.md').open('w' if replace_presentation else 'x') as f:f.write(text)
