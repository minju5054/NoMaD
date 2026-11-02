"""Independent group-level frozen comparisons; all failed plans remain in denominators."""
import json
from pathlib import Path
import numpy as np
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean,csv_write as exclusive_csv_write
from nomad_isaac.common import ROOT,sha256_file

OUT=ROOT/'research/results/phase23o';HERE=Path(__file__).parent
def csv_write(path,rows):
    tmp=path.with_suffix('.csv.tmp');tmp.unlink(missing_ok=True);exclusive_csv_write(tmp,rows);tmp.replace(path)
def summaries(rows):
    answer=[]
    for group in ('static','sudden'):
        for method in ('U','C0','C1'):
            rr=[r for r in rows if r['group']==group and r['method']==method]
            if not rr:continue
            median=lambda k:float(np.median([r[k] for r in rr if r.get(k) is not None])) if any(r.get(k) is not None for r in rr) else None
            answer.append(dict(group=group,method=method,n=len(rr),oracle_collisions=sum(r['oracle_collision'] for r in rr),planning_failure_fraction=sum(not r['accepted'] for r in rr)/len(rr),progress_median=median('progress'),execution_time_median_s=median('execution_time_s'),compute_p50_s=median('compute_s'),compute_p95_s=float(np.quantile([r['compute_s'] for r in rr],.95)),over025=sum(r['compute_s']>.25 for r in rr),
                min_clearance_median=median('oracle_minimum_clearance_m'),omega_saturation_median=median('omega_saturation_fraction'),intent_error_fraction=float(np.mean([r['intent_error'] for r in rr if r.get('intent_error') is not None])) if any(r.get('intent_error') is not None for r in rr) else None,
                passage_fraction=sum(r['box_passage'] for r in rr)/len(rr),active_switches=sum(r.get('active_switches',0) for r in rr),
                active_native_short_fraction=float(np.mean([r['active_native_short'] for r in rr if r.get('active_native_short') is not None])) if any(r.get('active_native_short') is not None for r in rr) else None,
                active_remaining_short_fraction=float(np.mean([r['active_remaining_short'] for r in rr if r.get('active_remaining_short') is not None])) if any(r.get('active_remaining_short') is not None for r in rr) else None,
                short_active_graph_forward_median_m=float(np.median([r['graph_forward_m'] for r in rr if r.get('active_native_short')])) if any(r.get('active_native_short') for r in rr) else None,
                still_short_graph_forward_median_m=float(np.median([r['graph_forward_m'] for r in rr if r.get('active_remaining_short')])) if any(r.get('active_remaining_short') for r in rr) else None,
                warm_start_used=sum(r.get('warm_start_used',False) for r in rr),zero_motion_rollouts=sum(r.get('zero_motion_rollout',False) for r in rr),
                active_switch_fraction=sum(r.get('active_switches',0) for r in rr)/max(1,sum(r.get('active_transition_opportunities',0) for r in rr))))
    return answer
def decision(summary):
    flags={}
    for group in ('static','sudden'):
        u=next(r for r in summary if r['group']==group and r['method']=='U');b=next(r for r in summary if r['group']==group and r['method']=='C0')
        flags[group]=dict(safety=u['oracle_collisions']<=b['oracle_collisions'],planning=u['planning_failure_fraction']<=b['planning_failure_fraction']+.05+1e-12,progress=u['progress_median']>=.95*b['progress_median'],timing=u['compute_p95_s']<=.25)
    passed={g:all(f.values()) for g,f in flags.items()}
    label='UNIFIED_NOT_READY' if not all(f['timing'] for f in flags.values()) else 'UNIFIED_READY' if all(passed.values()) else 'UNIFIED_PARTIAL' if any(passed.values()) else 'UNIFIED_NOT_READY'
    return dict(label=label,groups=flags,passed=passed)

FORMULAS=r'''
## Input/output and pipeline

| Component | Input / output |
|---|---|
| U input | Eight observation-anchored NoMaD XY candidates; available depth V1 SDF; actual B pose and linear speed; OLD remainder for short-candidate supplementation |
| U solve | B-local poses $x_0\ldots x_{10}$ and ten $\Delta t$; four-worker SLSQP multi-start; no oracle, Topomap pose, trigger, progress history, u_ref or A* input |
| U output | Eleven world SE(2) poses and ten time intervals; graph segment speeds → PP direction at lookahead0.25m; separately registered handling of pure graph rotations |
| Evaluation only | Oracle rotated boxes/walls, Topomap next-node metadata, recorded trigger membership |

| Current rule | Unified counterpart |
|---|---|
| FRESHEST + candidate rejection | F1 selects a max-mixture component inside the objective; all8 candidates retained |
| Depth safety filter | F2 point/midpoint constraints and clearance preference |
| SP + heuristic start alignment | F3 pose/time kinematics; PP + graph speed; no heading-threshold alignment rule |
| Trigger/u_ref detour target | F5 active NoMaD candidate endpoint, applied at every selected snapshot |
| Detour handover | Single finite trajectory; no online handover trigger in U |

## Factor definitions

Let $p_i\in\mathbb R^2$, $\theta_i\in\mathbb R$, $\tau_i=\Delta t_i$;
$p_0=0,\theta_0=0$ in B-local coordinates. The supplied SDF already subtracts radius0.09m; it is **not subtracted twice**.
All distances are metres and times seconds. $R_Bp_i+b$ transforms queries to world coordinates.

F1: $j^*=\arg\min_{j\in0..7}\sum_{i=1}^{10}\|p_i-\hat p_{ji}\|^2/\sigma_p^2$ (ties: smallest index).
$\sigma_p=\operatorname{clip}(\operatorname{median}_i\sqrt{\operatorname{Var}_j\hat p_{ji,x}+\operatorname{Var}_j\hat p_{ji,y}},.03,.15)$.
Only this component contributes F1 and F5 at each objective evaluation. Candidate headings/timestamps are not assumed native.
Suffix projection reuses the protected PP polyline rule; short suffixes append only the required prefix of the projected OLD remainder up to0.3m, then arclength-resample. Short/unavailable OLD handling is registered separately.

F2 queries $Q=\{p_0,...,p_{10},(p_i+p_{i+1})/2\}$.
$d(q)\ge m(q)$, where $m=\min(.025,\max(0,d(B)-.005))$ for current path arclength≤0.30m and $m=.025$ thereafter.
Soft loss $\sum_{q\in Q}[\max(0,.15-d(q))/.05]^2$.
These are node/midpoint constraints, **not a continuous-segment safety certificate**. Out-of-grid queries are infeasible; unknown cells inside the input grid retain the source V1 free-space treatment.

F3: $\ell_i=\|p_{i+1}-p_i\|$, $v_i=\ell_i/\tau_i$, $\omega_i=\operatorname{wrap}(\theta_{i+1}-\theta_i)/\tau_i$.
Hard $v_i\le.3$, $|\omega_i|\le.4$, $.05\le\tau_i\le1$.
Initial acceleration $a_0=(v_0-v_{actual})/\tau_0$; subsequent $a_i=2(v_i-v_{i-1})/(\tau_i+\tau_{i-1})$; $|a_i|\le.5$.
The actual initial speed is a boundary value, not an invented native waypoint time.
TEB-style nonholonomic residual $r_{nh,i}=((\cos\theta_i+\cos\theta_{i+1})\delta y_i-(\sin\theta_i+\sin\theta_{i+1})\delta x_i)/\sigma_{nh}$.
Forward consistency $r_{back,i}=\min(0,\delta p_i\cdot[\cos\theta_i,\sin\theta_i])/\sigma_{nh}$.
Their squared sums are fixed-weight terms; $\sigma_{nh}$ is preregistered and not tuned.

F4: $w_t\sum_i\tau_i$ (equivalently unary residual $\sqrt{w_t\tau_i}$).
F5: $w_g\|p_{10}-\hat p_{j^*,10}\|^2/.3^2$.
F6: $w_c\sum_i(\kappa_{i+1}-\kappa_i)^2$, with signed Menger curvature and analytic derivatives reused from Graph v4.
Only adjacent valid triples (chords and endpoint chord≥1cm) contribute; zero-translation rotation has no defined spatial curvature.
Total objective is F1+F2soft+F3soft+F4+F5+F6. Hard constraints are F2/F3.

Eight policy starts plus up to two straight polylines through depth-component left/right edges offset0.25m; a missing intersecting component produces no fabricated side seed.
Connected components use4-connectivity, within2m of B and intersecting a candidate footprint.
SLSQP uses analytic Jacobians, maxiter100, ftol1e−8. Any observed feasible iterate (violation≤1e−7) before the shared250ms deadline can be selected by minimum objective; solver success and feasibility are recorded separately.
The reported wall time includes initialization, IPC, worker SDF loading and result collection, including overruns.

References: [Olson & Agarwal author manuscript](https://april.eecs.umich.edu/pdfs/olson2013ijrr.pdf) and [official TEB nonholonomic formulation](https://github.com/rst-tu-dortmund/teb_local_planner/blob/noetic-devel/include/teb_local_planner/g2o_types/edge_kinematics.h), [TEB acceleration](https://github.com/rst-tu-dortmund/teb_local_planner/blob/noetic-devel/include/teb_local_planner/g2o_types/edge_acceleration.h).
The max-mixture here is the user-specified equal-weight policy-candidate adaptation, not a reproduction of SLAM results.
'''

EXECUTION='''
## Registered execution and warm starts

Translation uses protected PP lookahead0.25m and graph segment speeds linearly interpolated at the **projected arclength**, with knots at translating-segment midpoints. No elapsed-time lookup or SP is used for U. Rotation segments are those with graph v<0.01m/s: brake within0.5m/s², then use graph omega's signed magnitude (limited to0.4rad/s). Only the last9Hz angular step is shortened to avoid overshooting the target heading. Completed rotation segments advance the segment cursor; zero-speed rotation knots are excluded from translating-speed interpolation. No heading-threshold start alignment is introduced. No solution or total250ms deadline overrun produces a bounded braking stop. The22-O2 endpoint/projection/time stopping rules remain; U has no heuristic-alignment time exemption.

The replanning interface runs on each candidate arrival with a nominal4Hz/250ms period and a last accepted **U-only** warm start. The original8candidate starts and up to2depth-edge starts remain; a usable previous U suffix adds one warm initialization (maximum11), inside the same total250ms budget. Warm states are separated by run, split and weight combination. Exhausted prior paths are not fabricated. A* output is never a U seed or fallback; an A*-derived historical OLD path is withheld from U supplementation and recorded.

This offline dataset contains selected saved candidate arrivals, not a new4Hz closed-loop stream. It evaluates those arrivals chronologically and records the actual gap to the warm-source snapshot. No missing candidates are generated and no future depth/NoMaD feedback is invented. Thus the evaluation cannot establish closed-loop4Hz behavior.

Short original FRESH means native suffix<0.3m. Available non-A* OLD geometry may supplement it as originally specified; if it is still short, all8mixture candidates remain and resampling stays inside the available polyline. The report separately gives native-short and still-short active fractions (denominator: plans with an active candidate), and graph endpoint forward displacement conditional on each category. Forward displacement is measured along B heading, not u_ref.
'''

def selection_section(p):
    evidence=p.get('selection_evidence')
    if evidence is None:return '## Weight selection\n\nNot executed.\n\n'
    return '## Frozen weight selection evidence\n\nTiming gate p95≤0.25s first. If all exceed it, choose minimum p95 and flag. Otherwise: fewest oracle collisions, lowest planning-failure fraction, lowest sum of within-group progression-median ranks, then lowest compute p50 (exact ties: lower grid index).\n\n'+str({k:v for k,v in evidence.items() if k!='table'})+'\n\n'+table(evidence['table'])+'\n\n'

def write_selection_report(p,destination=None):
    destination=Path(destination) if destination else ROOT/'docs/PHASE23O_UNIFIED.md'
    destination.write_text('# Phase23-O — training selection; evaluation not yet executed\n\n'+FORMULAS+EXECUTION+'\n\n'+selection_section(p)+'Evaluation label: **NOT_EVALUATED**. Selected weights and this table are committed before evaluation begins.\n')

def generate():
    p=json.loads((HERE/'protocol.json').read_text());m=json.loads((OUT/'manifest.json').read_text());records=[json.loads(f.read_text()) for f in sorted((OUT/'evaluation').glob('*.json'))];rows=[v['row'] for r in records for v in r['methods'].values()]
    assert len(records)==len(m['evaluation']);summary=summaries(rows);verdict=decision(summary)
    csv_write(OUT/'snapshots.csv',rows);csv_write(OUT/'summary.csv',summary);(OUT/'decision.json').write_text(json.dumps(clean(verdict),indent=2)+'\n')
    paired=[]
    for r in records:
        u,b=r['methods']['U']['row'],r['methods']['C0']['row'];paired.append(dict(case_id=u['case_id'],group=u['group'],scene=u['scene'],U_collision=u['oracle_collision'],C0_collision=b['oracle_collision'],progress_delta=u['progress']-b['progress'],time_delta=u['execution_time_s']-b['execution_time_s']))
    csv_write(OUT/'paired.csv',paired);plots(records,rows,m['examples'])
    text='# Phase23-O — offline unified SE(2) graph\n\n'+FORMULAS+EXECUTION+'\n\n'+selection_section(p)
    text+=f"Protocol SHA256 `{sha256_file(HERE/'protocol.json')}`. Label **{verdict['label']}**. Training{len(m['training'])}, evaluation{len(m['evaluation'])}; distinct runs and indices.\n\n"
    text+='Registered execution/input handling: `'+str(p['policy'])+'`. Selected weights: `'+str(p['selected'])+'`.\n\n'+table(summary)+'\n\n'+table([dict(group=g,**v) for g,v in verdict['groups'].items()])+'\n\n'
    slw=[r for r in rows if r['scene']=='SLW'];text+='SLW saturation: '+str({method:float(np.median([r['omega_saturation_fraction'] for r in slw if r['method']==method])) for method in ('U','C0')})+'\n\n'
    text+='C0/C1 retain frozen selection and R2→R3 solvers (C1 reference on sudden cases only). Missing Phase18 free timestamps are replayed from saved depth and V1 occupancy is checked for exact equality. U receives the unchanged source V1 snapshot. C0/C1 follow22-O2 SP/alignment and stopping. Fallback has no future NoMaD regeneration; recovery-driven replanning cannot be inferred from a fixed snapshot. All failed plans stay in denominators; braking displacement and collision are evaluated too. Sudden progress is the binary footprint passage indicator; therefore a zero baseline median can make the95% progression condition weak. Passage fractions are shown separately.\n\n'
    text+='This is a fixed-path offline counterfactual, not closed-loop navigation evidence. No new RGB, depth render, inference or Isaac run was performed. Timing and safety claims apply only to this evaluation. Full per-case checkpoints stay locally in training/evaluation; summary, examples and provenance are published.\n\n'
    for file in ('examples.png','distributions.png','paired.png'):text+=f'![{file}](../research/results/phase23o/{file})\n\n'
    if verdict['label'] in ('UNIFIED_READY','UNIFIED_PARTIAL'):text+='## Draft only — not executed\n\nNew held-out seeds, L2+SLW ×4seeds×U/C0=16runs. Freeze identical sensing, timing and executors; compare goal/collision first, then paired passage/progress and computation deadlines. A trial would proceed only without increased collisions and with at least equal goal count in each scene; any25% technical invalidity makes it inconclusive. This is a proposed pilot requiring separate approval, not part of this offline run.\n'
    (ROOT/'docs/PHASE23O_UNIFIED.md').write_text(text);return verdict

def plots(records,rows,examples):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from nomad_phase22.drive_geometry import corners
    by={r['case']['case_id']:r for r in records};colors=dict(U='purple',C0='darkorange',C1='steelblue')
    fig,axes=plt.subplots(1,3,figsize=(16,5),constrained_layout=True)
    for ax,identity in zip(axes,examples):
        r=by[identity];c=r['case'];cfg=c['oracle_config']
        for path in c['samples_world']:a=np.asarray(path);ax.plot(*a.T,color='.75',lw=.7)
        for box in cfg['obstacles']:ax.add_patch(Polygon(corners(box),color='.4',alpha=.3))
        for method,v in r['methods'].items():
            if v['plan'].get('path') is not None:a=np.array(v['plan']['path']);ax.plot(*a.T,ls='--',color=colors[method],alpha=.65)
            a=np.array(v['trace']);ax.plot(a[:,0],a[:,1],color=colors[method],label=method)
        ax.scatter(*c['B'][:2],marker='x',c='black');ax.set_aspect('equal');ax.set_title(c['scene']+' '+identity);ax.legend();ax.set_xlabel('World x(m)');ax.set_ylabel('World y(m)')
    fig.savefig(OUT/'examples.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
    for i,g in enumerate(('static','sudden')):
        for j,k in enumerate(('oracle_minimum_clearance_m','progress','compute_s')):
            ax=axes[i,j]
            for x,method in enumerate(('U','C0','C1')):
                a=[r[k] for r in rows if r['group']==g and r['method']==method]
                if a:ax.boxplot([a],positions=[x],widths=.5,showfliers=False);ax.scatter(np.full(len(a),x),a,s=3,alpha=.2,c=colors[method])
            ax.set_xticks([0,1,2],['U','C0','C1']);ax.set_title(g+' '+k)
    fig.savefig(OUT/'distributions.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    for ax,g in zip(axes,('static','sudden')):
        rr=[r for r in records if r['case']['group']==g]
        ax.scatter([r['methods']['C0']['row']['progress'] for r in rr],[r['methods']['U']['row']['progress'] for r in rr],s=9,alpha=.5);ax.set_title(g);ax.set_xlabel('C0 progress');ax.set_ylabel('U progress')
    fig.savefig(OUT/'paired.png',dpi=140);plt.close(fig)
