"""Tables from the fixed solver diagnosis; never selects a method or weights."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from .solver_check import OUT,HERE,read,write,GROUPS
from .report import csv_write

def distribution(values):
    a=[v for v in values if v is not None]
    return dict(n=len(a),p50=float(np.quantile(a,.5)) if a else None,p95=float(np.quantile(a,.95)) if a else None,max=max(a,default=None))

def generate():
    p=read(HERE/'solver_check_protocol.json');passes={mode:[read(OUT/mode/f'{identity}.json') for identity in p['case_ids']] for mode in ('before','after')};summary=[];start_rows=[];snapshot_rows=[]
    for mode,rr in passes.items():
        for group in ('static','sudden','ALL'):
            rows=[r for r in rr if group=='ALL' or r['group']==group];starts=[s for r in rows for s in r['initializations']]
            summary.append(dict(mode=mode,group=group,snapshots=len(rows),any_feasible=sum(r['any_feasible'] for r in rows),final_feasible=sum(r['final_feasible'] for r in rows),converged_feasible=sum(r['converged_feasible'] for r in rows),
                best_found_s=distribution(r['best_found_s'] for r in rows),first_feasible_s=distribution(r['first_feasible_s'] for r in rows),all_starts_s=distribution(r['total_wall_s'] for r in rows),
                starts=len(starts),solver_converged_starts=sum(s['solver_success'] for s in starts),objective_api_calls=sum(s['objective_api_calls'] for s in starts),objective_kernel_calls=sum(s['objective_kernel_calls'] for s in starts),constraint_api_calls=sum(s['constraint_api_calls'] for s in starts),constraint_kernel_calls=sum(s['constraint_kernel_calls'] for s in starts),sdf_query_calls=sum(s['sdf_query_calls'] for s in starts)))
        for r in rr:
            snapshot_rows.append({k:v for k,v in r.items() if k not in ('initializations','component')})
            for s in r['initializations']:start_rows.append(dict(mode=mode,case_id=r['case_id'],group=r['group'],scene=r['scene'],**{k:v for k,v in s.items() if k not in ('best_x','final_x')}))
    by_initial=[]
    for mode in ('before','after'):
        for index in range(10):
            rr=[r for r in start_rows if r['mode']==mode and r['initialization']==index]
            by_initial.append(dict(mode=mode,initialization=index,kind='candidate' if index<8 else 'left' if index==8 else 'right',attempted=len(rr),unavailable=30-len(rr),converged=sum(r['solver_success'] for r in rr),final_feasible=sum(r['final_feasible'] for r in rr),any_feasible=sum(r['any_feasible'] for r in rr),any_feasible_rate=sum(r['any_feasible'] for r in rr)/len(rr) if rr else None,iterations=distribution(r['iterations'] for r in rr),wall_s=distribution(r['wall_s'] for r in rr)))
    variants=[];variant_rows=[]
    for name in ('reference','i','ii','iii'):
        rr=[read(OUT/'variants'/f'{name}_{identity}.json') for identity in p['case_ids']]
        variant_rows.extend({k:v for k,v in r.items() if k!='results'} for r in rr)
        variants.append(dict(variant=name,n=len(rr),deadline_s=rr[0]['budget_s'],starts='8+up to2' if name in ('reference','ii') else '2+up to2',delivered_feasible=sum(r['delivered_feasible'] for r in rr),delivered_feasible_rate=sum(r['delivered_feasible'] for r in rr)/len(rr),internal_feasible_before_deadline=sum(r['feasible_before_deadline'] for r in rr),overruns=sum(r['deadline_overrun'] for r in rr),compute_s=distribution(r['compute_s'] for r in rr)))
    maximum=0.;iteration_mismatch=0;feasible_mismatch=0
    for a,b in zip(passes['before'],passes['after']):
        for x,y in zip(a['initializations'],b['initializations']):
            maximum=max(maximum,float(np.max(abs(np.array(x['final_x'])-y['final_x']))));iteration_mismatch+=x['iterations']!=y['iterations'];feasible_mismatch+=x['final_feasible']!=y['final_feasible']
    outcome=dict(fixed_cases=30,gradient='analytic before and after; finite differences only in tests',maximum_final_state_difference=maximum,iteration_mismatches=iteration_mismatch,final_feasibility_mismatches=feasible_mismatch,summary=summary,variants=variants,selected_variant=None,full_tuning_started=False,full_evaluation_started=False)
    write(OUT/'summary.json',outcome)
    for name,rr in [('starts',start_rows),('snapshots',snapshot_rows),('before_after',summary),('by_initialization',by_initial),('variants',variant_rows)]:csv_write(OUT/f'{name}.csv',rr)
    messages=Counter(r['message'] for r in start_rows if r['mode']=='after');active=Counter(k for r in start_rows if r['mode']=='after' for k in r['active_groups']);failed=[r for r in passes['after'] if not r['any_feasible']]
    tests=read(OUT/'validation.json')
    text='# Phase23-O solver speed and convergence check\n\n'
    text+='**Diagnostic only. No full tuning/evaluation, navigation, inference or method selection was run.** Training-only sample:15static+15sudden, RNG seed20261102. Existing grid has8combinations, so the lower-middle fourth combination is fixed: `time=0.1, goal=4, curvature=0.01`. This is not a selected tuning weight. Cases and this convention were fixed before solver results.\n\n'
    text+='## Timing and feasibility definitions\n\nBefore/after: single process, **no wall deadline on SLSQP**, unchanged maxiter100 and ftol1e−8, same sample order and input maps. Feasible means the registered hard constraints and variable bounds are satisfied within1e−7; solver convergence is reported separately. This is node/midpoint depth/kinematics feasibility, not a new continuous collision or closed-loop safety claim.\n\n'
    text+='Best-found time sums candidate preparation, preceding start solve times and the timestamp when the globally lowest-cost feasible iterate was observed. It excludes post-solve diagnostic extraction and is conditional on finding a feasible solution. All-start time includes the full snapshot diagnostic and covers all30cases. Neither is a claim that a controller knew the global best before the remaining starts completed. Parent SDF loading and process startup are excluded consistently; budgeted worker SDF transfers/loading remain included in the4-worker tests.\n\n'
    text+='Eight candidate starts are always kept. Only5/30snapshots had the registered intersecting depth component, so only those have left/right starts:250actual attempts per pass, not300. Missing side starts are marked unavailable rather than failed. No cross-snapshot warm start is used in this isolated diagnostic.\n\n'
    compact=[dict(mode=r['mode'],group=r['group'],N=r['snapshots'],feasible=r['any_feasible'],converged_feasible=r['converged_feasible'],best_p50_s=round(r['best_found_s']['p50'],6) if r['best_found_s']['p50'] is not None else None,best_p95_s=round(r['best_found_s']['p95'],6) if r['best_found_s']['p95'] is not None else None,total_p50_s=round(r['all_starts_s']['p50'],6),total_p95_s=round(r['all_starts_s']['p95'],6)) for r in summary]
    text+='## Before / after\n\n'+table(compact)+'\n\n'
    text+='Evaluation counters (all starts):\n\n'+table([r for r in summary if r['group']=='ALL'],['mode','objective_api_calls','objective_kernel_calls','constraint_api_calls','constraint_kernel_calls','sdf_query_calls'])+'\n\n'
    text+='## Gradient/Jacobian and implementation\n\nThe original solver already passed `jac=True` and analytic constraint Jacobians to SLSQP. No numerical differentiation was used for optimization. The improvement therefore is **reuse/vectorization**, not a switch from numerical to analytic gradients: bounded last-iterate objective/Jacobian caches; shared point/midpoint SDF value/gradient cache; constant query Jacobian/bounds/start margin hoisted per immutable snapshot; vectorized Menger derivative assembly. F1active-component, F2bilinear, F3kinematic, F4–F6formulas, weights and solver options are unchanged. Cache hits still check the deadline.\n\n'
    text+=table([tests])+'\n\n'
    text+=f'Across all250paired starts, maximum final-state difference={maximum:.3g}, iteration mismatches={iteration_mismatch}, final-feasibility mismatches={feasible_mismatch}. Central finite differences are checked away from max-mixture ties, grid derivative discontinuities, the0.30m margin switch and degenerate spatial-curvature triples; no differentiability claim is made at those kinks.\n\n'
    compact_starts=[dict(mode=r['mode'],initialization=r['initialization'],kind=r['kind'],attempted=r['attempted'],unavailable=r['unavailable'],converged=r['converged'],final_feasible=r['final_feasible'],any_feasible=r['any_feasible'],iterations_p50=r['iterations']['p50'],iterations_p95=r['iterations']['p95'],wall_p50_s=round(r['wall_s']['p50'],6) if r['wall_s']['p50'] is not None else None,wall_p95_s=round(r['wall_s']['p95'],6) if r['wall_s']['p95'] is not None else None) for r in by_initial]
    text+='## Initialization-level success\n\n'+table(compact_starts)+'\n\n'
    text+='Every start has convergence, iterations, SciPy nfev/njev, objective/constraint API and physical-kernel counts, SDF queries, wall time, final feasibility and active/violated groups in [starts.csv](../research/results/phase23o_solver_check/starts.csv). Every snapshot is listed in [snapshots.csv](../research/results/phase23o_solver_check/snapshots.csv).\n\n'
    text+='Post-improvement solver messages: `'+str(dict(messages))+'`. Active constraint incidences: `'+str(dict(active))+'`.\n\n'
    for r in failed:
        text+=f"No feasible iterate for {r['case_id']}: "+str([(s['initialization'],s['iterations'],s['solver_status'],s['violated_groups']) for s in r['initializations']])+'.\n\n'
    compact_variants=[dict(variant=r['variant'],N=r['n'],budget_s=r['deadline_s'],starts=r['starts'],delivered_feasible=r['delivered_feasible'],internal_feasible=r['internal_feasible_before_deadline'],overruns=r['overruns'],p50_s=round(r['compute_s']['p50'],6),p95_s=round(r['compute_s']['p95'],6)) for r in variants]
    text+='## Requested alternatives — measurement only\n\n'+table(compact_variants)+'\n\n'
    text+='These deadline tests use the original4-process envelope with optimized but mathematically identical factors. Reference retains8candidate+up to2side starts at0.25s; (i) keeps2candidate+side starts at0.25s; (ii) keeps all at0.5s; (iii) combines the reduced starts and0.5s. None is selected or installed as the main configuration.\n\n'
    text+='The diagnostic prior-cost calculation is included in the shared preparation budget for all four variants. These are measured diagnostic timings, not an online latency guarantee; small differences between(i) and(iii) are not interpreted as a speed benefit from increasing the deadline.\n\n'
    text+='F1cost evaluated at each candidate’s own initialization is zero by self-match, so “lowest prior cost” is tied; the registered lower-index tie-break retains0and1. No new confidence or outcome-dependent score was invented. The reduced-start result is therefore a fixed subset test, not evidence of informative prior ranking.\n\n'
    text+='Internal feasibility and delivered feasibility differ: the current parent waits for the mapped solves and rejects output when total elapsed time exceeds its deadline. A feasible internal iterate found before the deadline is not necessarily delivered on time. The gap is reported, not counted as on-time success and not fixed by changing the delivery policy in this check.\n\n'
    text+='## Stop\n\nImproved best-found and full multi-start p95 both exceed0.25s. No overall UNIFIED label, new weights or alternative configuration is selected. No full-run nohup command is provided; the next configuration remains the user’s decision. Main250ms budget,4workers, grid and decision criteria are unchanged.\n\n'
    text+=f"Diagnostic protocol SHA256 `{sha256_file(HERE/'solver_check_protocol.json')}`. Full per-start/final-state records are retained in before/after and variants.\n"
    (ROOT/'docs/PHASE23O_SOLVER_CHECK.md').write_text(text)
    print(json.dumps(dict(maximum_final_state_difference=maximum,iterations_changed=iteration_mismatch,selected_variant=None)))
if __name__=='__main__':generate()
