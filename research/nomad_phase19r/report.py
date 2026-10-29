"""Pure saved-result report; oracle boxes appear only in evaluation figures."""
from pathlib import Path
import json
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase17.report import table
from nomad_phase15b.depth import Snapshot
from nomad_phase16.geometry import rect


def render(out,summary,decision,recovery,examples,repairs,protocol,sha,replace_presentation=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    meta=json.loads((out/'inventory.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    for ax,cause in zip(axes,('TRUE_BLOCK','MARGINAL')):
        identifier=meta['example_event_ids'][cause];e=examples.get(str(identifier))
        if e is None:ax.text(.5,.5,f'No {cause} event',ha='center',transform=ax.transAxes);continue
        event=e['event'];B=np.array(event['B']);field=Snapshot.load(event['snapshot_file'])
        iy,ix=np.nonzero(field.occupied);points=field.origin+np.c_[ix,iy]*field.h
        near=np.max(np.abs(points-B[:2]),axis=1)<=1.25
        ax.scatter(points[near,0],points[near,1],s=2,c='.65',label='Saved depth occupancy')
        for i,path in enumerate(e['native']):
            path=np.array(path);ax.plot(path[:,0],path[:,1],color='.65',lw=.8,label='8 original samples' if i==0 else None)
        accepted=[r for r in e['repairs'] if r['accepted']]
        for i,r in enumerate(accepted):
            p=np.array(r['path']);ax.plot(p[:,0],p[:,1],c='tab:purple',alpha=.5,lw=1,label='Accepted repairs' if i==0 else None)
        if e['selected'] is not None:
            r=e['repairs'][e['selected']];p=np.array(r['path']);q=np.array(r['reference'])
            ax.plot(q[:,0],q[:,1],'--',color='tab:blue',label='Resampled intent')
            ax.plot(p[:,0],p[:,1],color='tab:blue',lw=2,label='Selected repair')
            trace=np.array(e['rollout']);ax.plot(trace[:,0],trace[:,1],color='black',lw=2,label='Offline SP rollout')
        else:ax.text(.03,.03,'No accepted repair',transform=ax.transAxes,color='darkred')
        for b in e['config']['obstacles']:
            x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='tab:orange',alpha=.2))
        xmin,xmax,ymin,ymax=rect(e['config']);ax.add_patch(Rectangle((xmin,ymin),xmax-xmin,ymax-ymin,fill=False,color='tab:orange',label='Oracle geometry (evaluation)'))
        ax.scatter(*B[:2],c='red',s=35,label='B');ax.set_xlim(B[0]-1.25,B[0]+1.25);ax.set_ylim(B[1]-1.25,B[1]+1.25);ax.set_aspect('equal')
        ax.set_title(f"{cause}, fixed eval event {identifier}\n{event['scene']} {event['index']} FRESH {event['fresh_id']}\n{event['method']}",fontsize=9)
        ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.legend(fontsize=6,loc='upper left')
    fig.tight_layout();fig.savefig(out/'repair_examples.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    # All accepted sample repairs, separate from the selected-event median gate.
    all_edits=[r['mean_edit_m'] for r in repairs if r['accepted']]
    upper=max(.2,np.ceil(max(all_edits,default=.2)*20)/20)
    for split in ('dev','eval'):
        values=[r['mean_edit_m'] for r in repairs if r['split']==split and r['accepted']]
        if values:ax.hist(values,bins=np.linspace(0,upper,41),histtype='step',density=True,lw=2,label=f'{split}: {len(values)} accepted sample repairs')
    ax.axvline(.15,c='k',ls='--',label='0.15m selected-median criterion');ax.set_xlabel('Mean edit over 8 resampled points (m)');ax.set_ylabel('Probability density (1/m)');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'deviation_hist.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4));causes=['MARGINAL','TRUE_BLOCK','NEAR_START','OTHER'];x=np.arange(4)
    for j,split in enumerate(('dev','eval')):
        rr=[next(r for r in summary if r['split']==split and r['cause']==c) for c in causes]
        vals=[r['repair_success_fraction'] or 0 for r in rr];bars=ax.bar(x+(j-.5)*.35,vals,.35,label=split)
        for bar,r in zip(bars,rr):ax.annotate(f"{r['repair_successes']}/{r['events']}",(bar.get_x()+bar.get_width()/2,bar.get_height()+.02),ha='center',fontsize=8)
    ax.set_ylim(0,1.16);ax.set_xticks(x,causes);ax.set_ylabel('Events with an accepted repair / all events');ax.legend()
    fig.tight_layout();fig.savefig(out/'success_by_cause.png',dpi=150);plt.close(fig)
    symbols=[dict(symbol='b, θ_B',meaning='recorded robot position and yaw at the decision boundary; b is fixed'),
        dict(symbol='q̂_0…q̂_7',meaning='equal-arclength 8-point intent reference; q̂_0=b'),
        dict(symbol='p_0…p_7',meaning='repair points, p_0=b; x=(p_1…p_7) has 14 XY variables, no yaw variables'),
        dict(symbol='σ_p, σ_s, σ_h',meaning='0.10m, 0.02m, π/6 rad'),
        dict(symbol='d_depth(q)',meaning='saved depth occupied-site distance minus radius 0.09m; unknown is not occupied'),
        dict(symbol='h, L_i, ℓ_i⁰',meaning='1cm grid; repaired segment length; initial resampled segment length'),
        dict(symbol='κ_i',meaning='signed Menger curvature for successive triples, i=1…6')]
    text='# Phase 19-R — depth-only XY repair, offline validation\n\n'
    text+=f"Execution SHA: `{sha}`. **{decision['label']}**. No Isaac navigation, NoMaD inference, or Isaac rendering.\n\n"
    text+='## Graph definition and symbols\n\n'+table(symbols)+'\n\n'
    text+=r'\[E(x)=\frac12\left[\sum_{i=1}^7\frac{\|p_i-\hat q_i\|^2}{0.10^2}+\sum_{i=1}^6\frac{\|p_{i+1}-2p_i+p_{i-1}\|^2}{0.02^2}+\left(\frac{2\sin((\operatorname{atan2}(p_1-b)-\theta_B)/2)}{\pi/6}\right)^2\right].\]'+'\n\n'
    text+=r'For $t_j=j/8$, $q_{ij}=(1-t_j)p_i+t_jp_{i+1}$: $d_{depth}(q_{ij})-h/\sqrt2-L_i/16\ge0.025$, $|\kappa_i|\le8$, $L_i\ge0.5\ell_i^0$, $\sum L_i\ge0.7\sum\ell_i^0$, and $|p_{i,a}-\hat q_{i,a}|\le0.75$ for each coordinate.'+'\n\n'
    text+='SLSQP, analytic residual/constraint Jacobians, maxiter=100, ftol=1e−8. Acceptance requires solver success, maximum raw-unit constraint/bound violation ≤1e−7, and exact distance to depth occupied cell centers (minus robot radius) ≥0.025m. No optimizer restart, alternate seed, or parameter tuning.\n\n'
    text+='The native sample remains observation-anchored. Initialization projects B onto it, keeps its suffix, adds the explicit B→projection connector, and resamples that polyline. Eligibility uses native suffix length before adding the connector (≥0.25m). Edit metrics compare the repaired 8 points with this resampled intent reference, including the unchanged B point; they are not same-index distances to the original eight NoMaD outputs.\n\n'
    text+='## Frozen protocol\n\n```json\n'+json.dumps(protocol,indent=2,ensure_ascii=False)+'\n```\n\n'
    text+='## Development and evaluation\n\n'+table(summary,['split','cause','events','repair_successes','repair_success_fraction','accepted_paths','oracle_penetrations','rollout_overlaps','rollout_count','selected_mean_edit_m','selected_rollout_progress_m','zero_progress_selections','per_sample_solve_s','eight_sample_wall_s','no_eligible_events','fixed_B_infeasible_samples','freshest_only_successes','E1_selected','E1_penetrating','E2_selected','E2_penetrating','dispositions'])+'\n\n'
    text+='Per-event causes use Phase16-D priority: MARGINAL if the best original oracle suffix clearance is [0,0.025); otherwise TRUE_BLOCK if all8 penetrate; otherwise NEAR_START if B depth clearance<0.025; otherwise OTHER. The corresponding per-run 70% rule is also recorded in event CSVs. Oracle labels never enter the repair or selection function.\n\n'
    text+=f"Development contains exactly 1,110 Phase16-D listed events including SL gates. Evaluation contains 241 actual ALL_UNSAFE decisions from all Phase18 methods/scenes. {meta['phase18_deferred_without_selection']} FRESH packets deferred during recovery had no selection decision and are separately counted, not relabelled ALL_UNSAFE. Evaluation modes: {meta['eval_modes']}.\n\n"
    text+='## Evaluation-only decision\n\n```json\n'+json.dumps(decision,indent=2,ensure_ascii=False)+'\n```\n\n'
    text+=f"Accepted-path oracle penetration: {decision['accepted_oracle_penetrations']}/{decision['accepted_sample_paths']}. Selected-path oracle penetration: {decision['selected_path_oracle_penetrations']}/{decision['selected_rollout_count']}. Selected SP rollout negative-clearance count: {decision['selected_rollout_overlaps']}/{decision['selected_rollout_count']}. Selected-path nonpenetration therefore did not imply safe execution in the fixed-path PP rollout.\n\n"
    text+='Path safety counts **all accepted sample repairs**, not only the selected one. Rollout safety counts one selected repair per successful event. Unaccepted solver iterates are preserved but are not executed or counted as accepted repair paths. The original FRESHEST-only reference reuses that sample’s one solve; it is never re-solved.\n\n'
    text+='One-sample timing includes initialization, optimizer and exact certificate; the decision p95 uses eligible solver attempts, with short/degenerate exclusions reported separately. Eight-sample timing is actual serial wall time including all8 decisions, excluding snapshot file I/O and oracle evaluation. No latency claim about an online worker is made.\n\n'
    text+='## Actual recovery reference (no offline recovery simulation)\n\n'+table(recovery)+'\n\n'
    text+='These are Phase17/18 main-run actual records, not matched interventions on the Phase16 development events. Rates divide safe first post-rotation FRESH by observed first post-rotation FRESH; missing terminal outcomes remain missing. Exact Phase18 recovery-trigger events are linked in events_eval.csv. Recovery data are evaluation references only.\n\n'
    text+='## Fixed examples\n\nThe first evaluation event of each cause was chosen and written to inventory.json before any saved-event repair solve. Examples remain even when no sample is repairable.\n\n'
    for name in ('repair_examples','deviation_hist','success_by_cause'):text+=f'![{name}](../research/results/phase19r/{name}.png)\n\n'
    text+='## Limits\n\nThis is a path-level offline counterfactual. The inherited Phase18-D SP rollout fixes one path for ≤1.5s, uses actual initial speed, and stops at an endpoint or oracle negative clearance. Its conservative swept lower-bound overlap count and exact negative witness are recorded separately. Future NoMaD responses, depth updates, next FRESH and recovery are absent. A fixed B that already violates the depth constraint cannot be repaired by moving only future points. Unknown cells remain free in depth and can conceal oracle obstacles. Effects can only be established in new closed-loop navigation experiments.\n'
    text+='Event rates are event-weighted and include repeated stops near the same pose; they are not independent navigation trials. The full numerical path journal is retained locally; the committed per-sample CSV preserves all dispositions and metrics.\n'
    with (ROOT/'docs/PHASE19R_REPAIR.md').open('w' if replace_presentation else 'x') as f:f.write(text)
