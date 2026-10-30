"""Saved-result presentation only; this module performs no rollout or solve."""
import json
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase16.geometry import rect
from .evaluate import dump


def render(out,data,summary,pairs,times,decision,examples,protocol,sha,verification,replace=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    for name,example in examples.items():
        fig,axes=plt.subplots(1,2,figsize=(12,5.3));path=np.array(example['path']);B=np.array(example['identity']['B'])
        cloud=np.concatenate([path,B[None,:2]]+[np.array(r['poses'])[:,:2] for r in example['results'].values()])
        lo=cloud.min(axis=0)-.2;hi=cloud.max(axis=0)+.2;span=max(*(hi-lo),.8);mid=(lo+hi)/2
        for ax,rule in zip(axes,('SP','SRG')):
            r=example['results'][rule];poses=np.array(r['poses'])
            for b in example['config']['obstacles']:
                x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2]
                ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='tab:orange',alpha=.3))
            xmin,xmax,ymin,ymax=rect(example['config'])
            ax.add_patch(Rectangle((xmin,ymin),xmax-xmin,ymax-ymin,fill=False,color='tab:orange',label='Oracle geometry (evaluation only)'))
            ax.plot(path[:,0],path[:,1],'--',c='.4',label='Fixed saved path')
            color='tab:blue' if rule=='SP' else 'tab:green';first=r['first_overlap_tick']
            stop=len(poses) if first is None else first+1
            ax.plot(poses[:stop,0],poses[:stop,1],color=color,lw=2,label=f'{rule} counterfactual')
            if first is not None:ax.plot(poses[first:,0],poses[first:,1],':',color=color,lw=1.8,label='Kinematic continuation after overlap')
            ax.scatter(*B[:2],marker='s',c='k',s=25,label='Actual boundary B')
            for i,p in enumerate(r['pivots']):ax.scatter(*p['xy'],marker='D',facecolors='none',edgecolors='purple',s=60,label='Pivot candidate' if i==0 else None)
            rotations=[e for e in r['events'] if e['event']=='ROTATION_START']
            for i,e in enumerate(rotations):
                ax.scatter(*e['pose'][:2],marker='o',facecolors='none',edgecolors='red',s=90,label='In-place rotation' if i==0 else None)
                ax.arrow(e['pose'][0],e['pose'][1],.1*np.cos(e['target']),.1*np.sin(e['target']),color='red',width=.001,head_width=.02,length_includes_head=True)
            if r['first_overlap_tick'] is not None:
                q=poses[r['first_overlap_tick']];ax.scatter(*q[:2],marker='x',c='red',s=70,label='First overlap bound')
                ax.add_patch(Circle(q[:2],.09,fill=False,color='red',alpha=.5))
            ax.set_xlim(mid[0]-span/2,mid[0]+span/2);ax.set_ylim(mid[1]-span/2,mid[1]+span/2);ax.set_aspect('equal')
            ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
            ax.set_title(f"{rule}: overlap={r['overlap']}, complete={r['completed']}\n{r['duration_s']:.2f}s, rotation {r['rotation_time_s']:.2f}s, min {r['minimum_clearance_m']:.3f}m",fontsize=10)
            ax.legend(fontsize=6,loc='best')
        identity=example['identity'];fig.suptitle(f"Predetermined {name} example: {identity['run']} / FRESH {identity['fresh_id']}",fontsize=9)
        fig.tight_layout();fig.savefig(out/f'srg_example_{name}.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for ax,scope in zip(axes,('COMMON','AVAILABLE')):
        for method,color in zip(('FRESHEST-SAFE','HERMITE','CLR'),('tab:blue','tab:orange','tab:green')):
            rr=[r['ratio'] for r in pairs if r['path_type']==method and r['both_complete'] and (scope!='COMMON' or r['common'])]
            if rr:ax.hist(rr,bins=24,histtype='step',lw=1.8,label=f'{method} (n={len(rr)})',color=color)
        ax.axvline(1.,c='.5',ls=':');ax.axvline(1.10,c='k',ls='--',label='1.10 time-cost threshold')
        ax.set_title(f'D2 / {scope} / paired completions',fontsize=10)
        ax.set_xlabel('SRG completion time / SP completion time');ax.set_ylabel('Event-path pairs');ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(out/'time_ratio_cl.png',dpi=150);plt.close(fig)
    cols=['dataset','scope','path_type','rule','n','overlaps','margin_violations','completions','safe_completions','completion_time_median_s','distance_mean_m','rotation_time_mean_s','trigger_fraction']
    text='# Phase 19-S — conditional stop–rotate–go, post-hoc offline validation\n\n'
    text+=f"Execution SHA: `{sha}`. Protocol SHA256: `{sha256_file(out/'protocol.json')}`. **{decision['label']}**.\n\n"
    text+='## Fixed rules\n\n'
    text+='SP uses the protected Phase18-D Menger-based forward/backward speed profile, interpolation at the current PP projection, execution floor 0.05m/s, maximum 0.3m/s, acceleration 0.5m/s² and ω clipping ±0.4rad/s. The protected PP lookahead is 0.25m. Commands update at 9Hz and exact SE(2) integration at 72Hz. No stored path is re-anchored.\n\n'
    text+='SRG S: at rollout start only, if actual v<0.01m/s and heading error to the first existing path point at least 0.05m from B is ≥20°, brake to zero and rotate toward that point. SRG P: combine <1cm chords for turn detection only; ≥45° turns ahead of the initial projection split the unchanged native polyline into legs. Each incoming pivot leg uses SP with terminal v_limit=0 and the same backward/forward passes. The 0.05m/s floor is removed on pivot stopping legs; otherwise a zero-speed pivot would be impossible. Within 1cm of a pivot, finish bounded braking, then rotate to the next merged-chord heading. A new leg resumes SP and acceleration limiting from zero.\n\n'
    text+='Rotation keeps v exactly zero and |ω|≤0.4. The final 9Hz rotation command is reduced to hit the target yaw without overshoot; there is no pose or yaw teleport. S is checked once at initial departure; subsequent explicit pivot rotations implement P. P candidates behind B are excluded. Multiple pivots are handled in path order. The original unmerged points remain in each PP leg.\n\n'
    text+='Both rules stop the numerical trial at endpoint tolerance 1cm or 8s. Oracle geometry is queried only in a separate evaluation pass, after all commands/poses have been generated. An oracle overlap does not change the fixed-path controller or abort this 8s trajectory. Consequently, a kinematic completion after an overlap is **not** a safe completion. Both-completed time pairs and both-safely-completed time pairs are shown separately. This explicitly differs from the previous ≤1.5s evaluation cutoff at first overlap.\n\n'
    text+='## Dataset coverage and verification\n\n'
    text+='D1/D2 reuse the exact Phase18-D common 85/166 events (the original five-path intersection, not recomputed for three paths). Method-available rows are also included; unavailable paths remain excluded with reasons in unavailable.csv. D3 contains all 90 selected evaluation repairs and D4 all 755 selected development repairs. No repair/Graph solve is repeated. Original sample choice and paths are unchanged.\n\n'
    text+='The SP prefix of every available path is checked against its saved Phase18-D/19-R ≤1.5s result, including the old first-overlap cutoff.\n\n'+table([verification])+'\n\n'
    text+='## Safety, completion and progress\n\n'+table(summary,cols)+'\n\n'
    text+='Overlap uses the existing swept conservative lower bound <0; exact negative witnesses and conservative-only negatives remain separate in rollouts.csv. Clearance includes the 0.09m circular footprint and the outer corridor rectangle. No new safety geometry formula is introduced. Completion-average speed is the fixed path arclength divided by completion time, as requested; actual travelled distance/time and initial remaining arclength are separate fields. Incomplete trials retain progress and FOLLOWING/BRAKING/ROTATING reasons.\n\n'
    text+='## D2 paired time cost\n\n'+table(times)+'\n\n'
    text+='The primary median pools the three path types over the original 166 common events, using only pairs with two completion times. It is event-path weighted; repetitions/path types are not independent trials. Per-path and all-available ratios, p90, completion attrition, and collision-free pairs are reported separately. No censored time is replaced by 8s. Trigger rate divides triggered SRG trials by all eligible SRG trials, not only completed pairs.\n\n'
    trigger_rows=[]
    for dataset in ('D1','D2','D3','D4'):
        rr=[r for r in data if r['dataset']==dataset and r['rule']=='SRG']
        trigger_rows.append(dict(dataset=dataset,event_paths=len(rr),initial_v_below_001=sum(r['previous_v']<.01 for r in rr),
            S_events=sum(r['trigger_S'] for r in rr),P_events=sum(r['trigger_P'] for r in rr),
            trials_with_pivot_candidates=sum(r['pivot_candidates']>0 for r in rr),triggered_completions=sum(r['trigger_any'] and r['completed'] for r in rr)))
    text+='## Trigger coverage and completion censoring\n\n'+table(trigger_rows)+'\n\n'
    triggered=[r for r in pairs if r['trigger']]
    text+=f"D2 all-available trigger trials: {len(triggered)}. Among them, both complete={sum(r['both_complete'] for r in triggered)}, SP only={sum(r['sp_complete'] and not r['srg_complete'] for r in triggered)}, SRG only={sum(r['srg_complete'] and not r['sp_complete'] for r in triggered)}, neither={sum(not r['sp_complete'] and not r['srg_complete'] for r in triggered)}. The observed paired median of 1.0 therefore does **not** establish negligible SRG time cost: no triggered D2 trial provides two completion times. The common D1/D2 sets have no fired triggers; equality there reflects an inactive conditional rule.\n\n"
    prefix=[dict(dataset=d,rule=s,overlaps=sum(r['legacy_1p5s_prefix']['overlap'] for r in data if r['dataset']==d and r['rule']==s)) for d in ('D3','D4') for s in ('SP','SRG')]
    text+='The ≤1.5s prefixes are also shown for horizon context; they are extracted from the already computed trajectories, without new rollouts.\n\n'+table(prefix)+'\n\n'
    text+='The reported total ω-saturation includes deliberate in-place rotation. Translation-only saturation is a separate CSV field; rotation saturation is not treated as understeering.\n\n'
    text+='## Prespecified decision\n\n```json\n'+json.dumps(decision,indent=2)+'\n```\n\n'
    text+='Safety requires D3 overlap≤1% and no D1 overlap increase for any path type in either the common or all-available scope. The D2 timing threshold uses the common pooled completion pairs. Empty completion pairs would be reported as INCONCLUSIVE_NO_COMPLETION_PAIRS instead of an invented median.\n\n'
    text+='The historical D3 SP count is 10/90 at ≤1.5s. The table above is the new, identical-horizon 8s SP→SRG comparison. A larger SP count at 8s is additional exposure, not a regression mismatch.\n\n'
    text+='## Predetermined figures\n\nThe SLW example is the first published Phase18-D UNDERTURN_EXECUTION row, using its saved active path and boundary. It may belong to a different method than the CLR source dataset and is supplemental only. The repair example is the first D3 event with a previously recorded SP overlap; neither figure is selected from new SRG outcomes.\n\n'
    for f in ('srg_example_slw','srg_example_repair','time_ratio_cl'):text+=f'![{f}](../research/results/phase19s/{f}.png)\n\n'
    text+='## Limits\n\nD1 and D3 reuse data involved in earlier decisions; this is post-hoc offline analysis. D4 is descriptive development data. The controller sees only geometry of one fixed path and the recorded B/speed. Future FRESH, regenerated NoMaD predictions, depth updates, timeout replacement, online solve delay and feedback from a changed observation are absent. Geometry during rotation is invariant for the assumed circular SE(2) footprint; this is not a validation of robot dynamics or collision-free translation into/out of a pivot. Effects can only be confirmed with new seeds and closed-loop navigation.\n\n'
    text+='## Frozen protocol\n\n```json\n'+json.dumps(protocol,indent=2,ensure_ascii=False)+'\n```\n'
    with (ROOT/'docs/PHASE19S_STOP_ROTATE_GO.md').open('w' if replace else 'x') as f:f.write(text)


if __name__=='__main__':
    from .evaluate import main
    main()
