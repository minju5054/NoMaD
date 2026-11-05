"""Registered solver gates; no online preparation on NO_GO."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase23.report import csv_write
from nomad_phase24.storage import atomic_json
from .inputs import HERE,OUT,read


def quantile(values,q):
    return float(np.quantile(values,q)) if values else None


def summary(records):
    result=[]
    for variant in ('S7','L7','L13'):
        rr=[r['row'] for r in records if r['row']['variant']==variant]
        good=[r for r in rr if r['accepted']];pre=[r for r in rr if r['input_stage']=='PRE_PASSAGE']
        result.append(dict(variant=variant,n=len(rr),accepted=len(good),adoption_rate=len(good)/len(rr),
            compute_p50_s=quantile([r['compute_s'] for r in rr],.5),compute_p95_s=quantile([r['compute_s'] for r in rr],.95),compute_max_s=max(r['compute_s'] for r in rr),
            timeout_1s=sum(r['timeout_1s'] for r in rr),pre_passage_n=len(pre),passage_plans=sum(r['planned_box_passage'] for r in pre),
            clearance_min_m=min([r['depth_min_clearance_m'] for r in good],default=None),clearance_median_m=quantile([r['depth_min_clearance_m'] for r in good],.5),
            curvature_rms_median=quantile([r['curvature_rms'] for r in good],.5),curvature_max=max([r['curvature_max'] for r in good],default=None),
            progress_median_m=quantile([r['progress_m'] for r in good],.5)))
    return result


def gate(rows):
    by={r['variant']:r for r in rows};s=by['S7'];gates=[]
    for variant in ('L7','L13'):
        r=by[variant];checks=dict(adoption=r['adoption_rate']>=s['adoption_rate']-.05-1e-12,
            timing=r['compute_p95_s']<=.1,passage=r['passage_plans']>=s['passage_plans'],
            clearance=r['clearance_median_m'] is not None and s['clearance_median_m'] is not None and r['clearance_median_m']>=s['clearance_median_m']-.01-1e-12)
        gates.append(dict(variant=variant,label='GO_ONLINE' if all(checks.values()) else 'NO_GO',**checks))
    passing=[g['variant'] for g in gates if g['label']=='GO_ONLINE']
    selected=min(passing,key=lambda m:(-by[m]['passage_plans'],m!='L7')) if passing else None
    return dict(label='GO_ONLINE' if selected else 'NO_GO',selected=selected,variants=gates,
                selection_rule='among passing variants more pre-passage planned passages wins; ties L7; never select a failing variant')


def figures(manifest,records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from nomad_isaac.clearance import configured_obstacles
    from nomad_phase22.drive_geometry import corners
    by={(r['row']['case_id'],r['row']['variant']):r for r in records};cases={c['case_id']:c for c in manifest['cases']}
    colors=dict(S7='black',L7='tab:orange',L13='tab:blue')
    fig,axes=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
    for ax,key in zip(axes,manifest['examples']):
        c=cases[key];B=np.array(c['B']);cfg=c['oracle_config'];corr=cfg['corridor']
        for box in configured_obstacles(cfg):ax.add_patch(Polygon(corners(box),fc='.65',ec='.2',alpha=.5))
        ax.axhline(corr['half_width'],color='.4');ax.axhline(-corr['half_width'],color='.4')
        for method,color in colors.items():
            r=by[key,method]
            if r['path'] is not None:
                p=np.array(r['path']);ax.plot(*p.T,color=color,lw=2,label=method+' accepted')
            else:
                ax.plot([],[],color=color,label=method+' no accepted path')
                # Show fixed-start terminal candidates faintly; never present
                # rejected candidates as selected or executed trajectories.
                for a in r['attempts']:
                    if a.get('path') is not None:
                        p=np.array(a['path']);ax.plot(*p.T,':',color=color,alpha=.15,lw=.7)
        u=np.array(c['u_ref'])*.5;ax.quiver(B[0],B[1],u[0],u[1],angles='xy',scale_units='xy',scale=1,color='red')
        ax.scatter(*B[:2],c='red',marker='x');ax.set_xlim(B[0]-1.8,B[0]+1.8);ax.set_ylim(B[1]-1.8,B[1]+1.8)
        ax.set_aspect('equal');ax.set_title(key+' / '+c['scene']);ax.legend(fontsize=8);ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
    fig.savefig(OUT/'paths.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    data=[[r['row']['compute_s'] for r in records if r['row']['variant']==m] for m in colors]
    axes[0].boxplot(data,labels=list(colors));axes[0].axhline(.1,color='red',ls='--',label='gate 0.1s');axes[0].set_ylabel('Four-worker whole-job time (s)');axes[0].legend()
    diffs=[]
    for m in ('L7','L13'):
        vals=[]
        for c in manifest['cases']:
            a,b=by[c['case_id'],m]['row'],by[c['case_id'],'S7']['row']
            if a['accepted'] and b['accepted']:vals.append(a['original_cost']-b['original_cost'])
        diffs.append(vals or [np.nan])
    axes[1].boxplot(diffs,labels=['L7 − S7','L13 − S7']);axes[1].axhline(0,color='.5');axes[1].set_ylabel('Original R3 cost difference (common accepted pairs)')
    fig.savefig(OUT/'timing_cost.png',dpi=150);plt.close(fig)
    return ['paths.png','timing_cost.png']


def generate():
    manifest=read(OUT/'manifest.json');records=[read(OUT/'records'/f"{c['case_id']}_{m}.json") for c in manifest['cases'] for m in ('S7','L7','L13')]
    rows=summary(records);verdict=gate(rows);atomic_json(OUT/'decision.json',verdict)
    csv_write(OUT/'snapshots.csv',[r['row'] for r in records]);csv_write(OUT/'summary.csv',rows)
    starts=[dict(case_id=r['row']['case_id'],variant=r['row']['variant'],**{k:a.get(k) for k in ('angle','accepted','disposition','solver_success','constraint_violation','wall_s','original_cost','failures','stages','error')}) for r in records for a in r['attempts']]
    csv_write(OUT/'starts.csv',starts)
    rejection=[]
    for variant in ('S7','L7','L13'):
        attempts=[a for r in records if r['row']['variant']==variant for a in r['attempts']]
        reasons=Counter(label for a in attempts if not a['accepted'] for label in a['failures'])
        rejection.extend(dict(variant=variant,reason=key,count=value,total_initializations=len(attempts)) for key,value in sorted(reasons.items()))
    csv_write(OUT/'rejections.csv',rejection)
    by={(r['row']['case_id'],r['row']['variant']):r['row'] for r in records};pairs=[]
    for c in manifest['cases']:
        s=by[c['case_id'],'S7']
        for m in ('L7','L13'):
            r=by[c['case_id'],m];common=r['accepted'] and s['accepted'];defined=common and r['side'] is not None and s['side'] is not None
            pairs.append(dict(case_id=c['case_id'],variant=m,common_accepted=common,side_defined=defined,same_side=(r['side']==s['side']) if defined else None,
                cost_difference=r['original_cost']-s['original_cost'] if common else None))
    csv_write(OUT/'paired.csv',pairs)
    groups=[]
    for source in manifest['counts']:
        groups.extend(dict(source=source,**r) for r in summary([r for r in records if r['row']['source']==source]))
    csv_write(OUT/'by_source.csv',groups)
    images=figures(manifest,records);p=read(HERE/'protocol.json')
    pair_summary=[]
    for m in ('L7','L13'):
        rr=[r for r in pairs if r['variant']==m];defined=[r for r in rr if r['side_defined']];common=[r for r in rr if r['common_accepted']]
        pair_summary.append(dict(variant=m,common_accepted=len(common),defined_sides=len(defined),same_side=sum(r['same_side'] for r in defined),
            same_side_fraction=sum(r['same_side'] for r in defined)/len(defined) if defined else None,cost_delta_median=quantile([r['cost_difference'] for r in common],.5)))
    text='''# Phase25 — R3 solver comparison (offline)

| Item | S7 SLSQP | L7 / L13 Levenberg–Marquardt |
|---|---|---|
| Variables | Fixed B +10 future xy points:20 variables | Identical |
| Original cost | One half sum of squared progress, smoothness, clearance and weak start-heading residuals | Identical residuals, including the frozen weak heading term |
| Constraint handling | Hard inequalities, redundant disk-implied coordinate bounds | Positive-part penalty residuals; s=0.01→0.001→0.0001, warm-start each stage |
| Obstacle solve samples | Frozen9points/segment with h/√2+L/16 | Requested11nodes+10midpoints, footprint distance minus threshold; final acceptance uses the full S7 rule |
| Solve | Analytic SLSQP, maxiter100, ftol1e−8 | Analytic scipy least_squares(method='lm'); max_nfev50 per stage, ftol/xtol/gtol1e−8 |
| Initializations | 0,±30,±60,±90degrees | L7 identical; L13 adds ±15,±45,±75degrees |
| Acceptance | Solver success, original hard violation≤1e−7, exact certificate, progress≥0.5m, whole job≤1s | Same final criteria, including the Phase24-R continuous certificate |
| Selection | Largest u_ref progress, then shorter length, then initializer index | Identical |

R3 has only20 variables: a dense Jacobian is sufficient, so sparsity offers little gain here. Any speed difference is principally from the nonlinear least-squares solver/linear algebra and its continuation, not from introducing a sparse graph implementation.

Original residuals: progress max(0,1.2−(p10−B)·u)/0.10; second differences/0.03; clearance max(0,0.15−d)/0.05 at90points; weak start heading 2sin((heading(p1−B)−yaw_B)/2)/(π/6). LM adds obstacle max(0,threshold−d)/s, curvature max(0,|κ|−4)/s, lower/upper segment-length violations of[0.10,0.20]/s and radius excess beyond1.6/s. The first0.3m uses the frozen threshold min(0.025,max(0,d(B)−h/√2−0.005)); base/strict map membership and threshold derivatives use the same piecewise convention as S7. Strict cells include occupied, unknown and free evidence older than2s. No map, decision, execution, R2 repair or prior phase source was modified. A* is not used.

The API's max_nfev50 is a conservative function-evaluation cap for each LM stage, not an invented SLSQP iteration count. Actual nfev/njev/status are saved per stage. All penalties are fixed, with no data-driven adjustment. Out-of-grid or numerical errors are recorded as failed starts, without adding a new objective extension.

## Data and measurement rules

'''
    text+=f"{len(manifest['cases'])} unique inputs: {manifest['counts']}. All saved C0 R3 transports and the fixed pre-passage16 are included. Snapshot hashes and three representative IDs were frozen before solving; originals are read-only. Protocol SHA256 `{sha256_file(HERE/'protocol.json')}`. Offline settings commit `{p['settings_base_commit']}` plus the subsequent freeze commit.\n\n"
    text+='Time is saved-input loading + strict EDT/cache creation + four-worker dispatch/loading + all7or13solves + final certificates/selection. Pool startup is excluded; per-start wall times and preprocessing are also saved. Every variant reloads its fields, and variant order rotates evenly over the129inputs. Whole-job wall time is reported uncapped; results finishing after1s are not selected. The0.1s gate applies to the whole-job p95, not a favorable single start. No online contention or inference was simulated.\n\n'
    text+='Depth clearance is each selected path’s minimum exact base/strict footprint clearance; its median is over accepted paths, with the count shown. Cost differences exclude penalty costs and use only common accepted snapshot pairs. Same-side rate uses common accepted paths with both sides defined, with its denominator shown. Pre-passage counts exclude already-passed/pre-spawn inputs and require oracle box/wall-safe passage. Oracle is evaluation-only. The dedicated16-input subgroup is separately reported. These are path-level offline comparisons, not new navigation outcomes.\n\n'
    text+='Five unit tests passed, including the complete170×20 analytic Jacobian versus Richardson-extrapolated central differences (absolute tolerance1e−5), original-cost/constraint equality, fixed continuation, rejection of a colliding output and the registered gate/selection boundary.\n\n'
    text+='## Registered gates\n\n'+table(verdict['variants'])+f"\n\n**{verdict['label']}**; selected variant: `{verdict['selected']}`. Acceptance≥S7−5percentage points; whole-job p95≤0.1s; pre-passage passage plans≥S7; depth clearance median≥S7−0.01m. Among passing variants the higher passage count wins; ties chooseL7.\n\n"
    text+='## Results\n\n'+table(rows)+'\n\n### Common pairs\n\n'+table(pair_summary)+'\n\n### Source cohorts\n\n'+table(groups)+'\n\n### Failure flags (multiple per start allowed)\n\n'+table(rejection)+'\n\n'
    for image in images:text+=f'![{image}](../research/results/phase25/{image})\n\n'
    if verdict['label']=='NO_GO':text+='Both LM variants failed the registered gate. Online preparation, smoke and main navigation were not run. No constants were changed after seeing these results.\n'
    (ROOT/'docs/PHASE25_LM.md').write_text(text)
    for f in OUT.glob('*.csv'):f.write_text(f.read_text())
    print(json.dumps(dict(decision=verdict,summary=rows)))
    return verdict


if __name__=='__main__':generate()
