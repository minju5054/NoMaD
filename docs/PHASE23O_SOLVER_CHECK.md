# Phase23-O solver speed and convergence check

**Diagnostic only. No full tuning/evaluation, navigation, inference or method selection was run.** Training-only sample:15static+15sudden, RNG seed20261102. Existing grid has8combinations, so the lower-middle fourth combination is fixed: `time=0.1, goal=4, curvature=0.01`. This is not a selected tuning weight. Cases and this convention were fixed before solver results.

## Timing and feasibility definitions

Before/after: single process, **no wall deadline on SLSQP**, unchanged maxiter100 and ftol1e−8, same sample order and input maps. Feasible means the registered hard constraints and variable bounds are satisfied within1e−7; solver convergence is reported separately. This is node/midpoint depth/kinematics feasibility, not a new continuous collision or closed-loop safety claim.

Best-found time sums candidate preparation, preceding start solve times and the timestamp when the globally lowest-cost feasible iterate was observed. It excludes post-solve diagnostic extraction and is conditional on finding a feasible solution. All-start time includes the full snapshot diagnostic and covers all30cases. Neither is a claim that a controller knew the global best before the remaining starts completed. Parent SDF loading and process startup are excluded consistently; budgeted worker SDF transfers/loading remain included in the4-worker tests.

Eight candidate starts are always kept. Only5/30snapshots had the registered intersecting depth component, so only those have left/right starts:250actual attempts per pass, not300. Missing side starts are marked unavailable rather than failed. No cross-snapshot warm start is used in this isolated diagnostic.

## Before / after

| mode | group | N | feasible | converged_feasible | best_p50_s | best_p95_s | total_p50_s | total_p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| before | static | 15 | 15 | 13 | 0.77335 | 1.5794 | 1.0499 | 1.825 |
| before | sudden | 15 | 14 | 13 | 0.49474 | 1.2664 | 0.94265 | 1.6478 |
| before | ALL | 30 | 29 | 26 | 0.55471 | 1.5216 | 0.99627 | 1.8003 |
| after | static | 15 | 15 | 13 | 0.42063 | 0.86367 | 0.51656 | 0.99569 |
| after | sudden | 15 | 14 | 13 | 0.25259 | 0.70493 | 0.47593 | 0.91303 |
| after | ALL | 30 | 29 | 26 | 0.27753 | 0.8322 | 0.49624 | 1.0091 |

Evaluation counters (all starts):

| mode | objective_api_calls | objective_kernel_calls | constraint_api_calls | constraint_kernel_calls | sdf_query_calls |
| --- | --- | --- | --- | --- | --- |
| before | 71170 | 71170 | 87861 | 87861 | 318062 |
| after | 71170 | 58371 | 87861 | 54229 | 54479 |

## Gradient/Jacobian and implementation

The original solver already passed `jac=True` and analytic constraint Jacobians to SLSQP. No numerical differentiation was used for optimization. The improvement therefore is **reuse/vectorization**, not a switch from numerical to analytic gradients: bounded last-iterate objective/Jacobian caches; shared point/midpoint SDF value/gradient cache; constant query Jacobian/bounds/start margin hoisted per immutable snapshot; vectorized Menger derivative assembly. F1active-component, F2bilinear, F3kinematic, F4–F6formulas, weights and solver options are unchanged. Cache hits still check the deadline.

| tests_passed | tests_total | central_difference_step | absolute_tolerance | objective_max_abs_error | constraint_max_abs_error | constraint_group_errors | isolated_F1_to_F6_gradient_tests | vectorized_menger_bitwise | cache_equivalence_and_deadline | optimized_source_sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | 21 | 1e-07 | 1e-05 | 1.4175e-08 | 4.0037e-09 | {'F2_nodes': 1.568515595185005e-10, 'F2_midpoints': 2.0933915712006979e-10, 'F3_speed': 1.0773499869998204e-09, 'F3_omega_positive': 3.192415221064948e-09, 'F3_omega_negative': 3.192415221064948e-09, 'F3_accel_positive': 4.003688935938499e-09, 'F3_accel_negative': 3.902280276690817e-09} | PASS | PASS | PASS | 069f1c651640e5e32593825b819dffdfb4e6662d839d560047fbfc7bc1fd053d |

Across all250paired starts, maximum final-state difference=0, iteration mismatches=0, final-feasibility mismatches=0. Central finite differences are checked away from max-mixture ties, grid derivative discontinuities, the0.30m margin switch and degenerate spatial-curvature triples; no differentiability claim is made at those kinks.

## Initialization-level success

| mode | initialization | kind | attempted | unavailable | converged | final_feasible | any_feasible | iterations_p50 | iterations_p95 | wall_p50_s | wall_p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| before | 0 | candidate | 30 | 0 | 17 | 18 | 22 | 68 | 100 | 0.094394 | 0.26386 |
| before | 1 | candidate | 30 | 0 | 19 | 21 | 24 | 80 | 100 | 0.11254 | 0.21552 |
| before | 2 | candidate | 30 | 0 | 16 | 20 | 21 | 57 | 100 | 0.087577 | 0.24001 |
| before | 3 | candidate | 30 | 0 | 19 | 21 | 24 | 72 | 100 | 0.10196 | 0.24696 |
| before | 4 | candidate | 30 | 0 | 19 | 20 | 25 | 56.5 | 100 | 0.086709 | 0.21085 |
| before | 5 | candidate | 30 | 0 | 17 | 19 | 24 | 53.5 | 100 | 0.085005 | 0.24692 |
| before | 6 | candidate | 30 | 0 | 17 | 18 | 22 | 57.5 | 100 | 0.11603 | 0.2682 |
| before | 7 | candidate | 30 | 0 | 21 | 23 | 24 | 64.5 | 100 | 0.094912 | 0.22992 |
| before | 8 | left | 5 | 25 | 1 | 1 | 1 | 27 | 59.4 | 0.066481 | 0.090477 |
| before | 9 | right | 5 | 25 | 0 | 1 | 1 | 36 | 100 | 0.12234 | 0.18932 |
| after | 0 | candidate | 30 | 0 | 17 | 18 | 22 | 68 | 100 | 0.050301 | 0.14664 |
| after | 1 | candidate | 30 | 0 | 19 | 21 | 24 | 80 | 100 | 0.054341 | 0.12114 |
| after | 2 | candidate | 30 | 0 | 16 | 20 | 21 | 57 | 100 | 0.042941 | 0.13334 |
| after | 3 | candidate | 30 | 0 | 19 | 21 | 24 | 72 | 100 | 0.053455 | 0.13505 |
| after | 4 | candidate | 30 | 0 | 19 | 20 | 25 | 56.5 | 100 | 0.045674 | 0.12354 |
| after | 5 | candidate | 30 | 0 | 17 | 19 | 24 | 53.5 | 100 | 0.043484 | 0.13723 |
| after | 6 | candidate | 30 | 0 | 17 | 18 | 22 | 57.5 | 100 | 0.060724 | 0.15836 |
| after | 7 | candidate | 30 | 0 | 21 | 23 | 24 | 64.5 | 100 | 0.046845 | 0.13397 |
| after | 8 | left | 5 | 25 | 1 | 1 | 1 | 27 | 59.4 | 0.039014 | 0.047126 |
| after | 9 | right | 5 | 25 | 0 | 1 | 1 | 36 | 100 | 0.077159 | 0.10219 |

Every start has convergence, iterations, SciPy nfev/njev, objective/constraint API and physical-kernel counts, SDF queries, wall time, final feasibility and active/violated groups in [starts.csv](../research/results/phase23o_solver_check/starts.csv). Every snapshot is listed in [snapshots.csv](../research/results/phase23o_solver_check/snapshots.csv).

Post-improvement solver messages: `{'Optimization terminated successfully': 146, 'Iteration limit reached': 87, 'Positive directional derivative for linesearch': 9, 'Inequality constraints incompatible': 7, 'More than 3*n iterations in LSQ subproblem': 1}`. Active constraint incidences: `{'F3_omega_negative': 141, 'F3_accel_positive': 134, 'F3_accel_negative': 66, 'F3_speed': 114, 'F3_omega_positive': 136, 'F3_dt_upper': 85, 'F3_dt_lower': 22, 'F2_nodes': 3}`.

No feasible iterate for TD0226: [(0, 100, 9, ['F3_omega_negative', 'F3_accel_positive']), (1, 100, 9, ['F3_speed', 'F3_omega_negative', 'F3_accel_positive', 'F3_accel_negative']), (2, 14, 4, ['F2_nodes', 'F2_midpoints', 'F3_speed', 'F3_omega_positive', 'F3_omega_negative', 'F3_accel_positive', 'F3_accel_negative']), (3, 100, 9, ['F3_omega_negative']), (4, 23, 8, ['F2_nodes', 'F2_midpoints', 'F3_speed', 'F3_omega_negative', 'F3_accel_positive', 'F3_accel_negative']), (5, 10, 4, ['F2_nodes', 'F2_midpoints', 'F3_speed', 'F3_omega_negative', 'F3_accel_positive', 'F3_accel_negative']), (6, 49, 8, ['F2_nodes', 'F2_midpoints', 'F3_speed', 'F3_omega_negative', 'F3_accel_positive', 'F3_accel_negative']), (7, 21, 4, ['F2_nodes', 'F2_midpoints', 'F3_speed', 'F3_omega_negative', 'F3_accel_positive', 'F3_accel_negative']), (8, 23, 4, ['F2_nodes', 'F2_midpoints', 'F3_speed', 'F3_omega_positive', 'F3_accel_positive', 'F3_accel_negative']), (9, 36, 8, ['F2_nodes', 'F2_midpoints', 'F3_speed', 'F3_omega_positive', 'F3_omega_negative', 'F3_accel_positive', 'F3_accel_negative'])].

## Requested alternatives — measurement only

| variant | N | budget_s | starts | delivered_feasible | internal_feasible | overruns | p50_s | p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reference | 30 | 0.25 | 8+up to2 | 19 | 29 | 10 | 0.19282 | 0.25034 |
| i | 30 | 0.25 | 2+up to2 | 26 | 26 | 0 | 0.092065 | 0.17735 |
| ii | 30 | 0.5 | 8+up to2 | 29 | 29 | 0 | 0.18518 | 0.33606 |
| iii | 30 | 0.5 | 2+up to2 | 26 | 26 | 0 | 0.088966 | 0.17522 |

These deadline tests use the original4-process envelope with optimized but mathematically identical factors. Reference retains8candidate+up to2side starts at0.25s; (i) keeps2candidate+side starts at0.25s; (ii) keeps all at0.5s; (iii) combines the reduced starts and0.5s. None is selected or installed as the main configuration.

The diagnostic prior-cost calculation is included in the shared preparation budget for all four variants. These are measured diagnostic timings, not an online latency guarantee; small differences between(i) and(iii) are not interpreted as a speed benefit from increasing the deadline.

F1cost evaluated at each candidate’s own initialization is zero by self-match, so “lowest prior cost” is tied; the registered lower-index tie-break retains0and1. No new confidence or outcome-dependent score was invented. The reduced-start result is therefore a fixed subset test, not evidence of informative prior ranking.

Internal feasibility and delivered feasibility differ: the current parent waits for the mapped solves and rejects output when total elapsed time exceeds its deadline. A feasible internal iterate found before the deadline is not necessarily delivered on time. The gap is reported, not counted as on-time success and not fixed by changing the delivery policy in this check.

## Stop

Improved best-found and full multi-start p95 both exceed0.25s. No overall UNIFIED label, new weights or alternative configuration is selected. No full-run nohup command is provided; the next configuration remains the user’s decision. Main250ms budget,4workers, grid and decision criteria are unchanged.

Diagnostic protocol SHA256 `962189d1544283d68c6a681398d59ab1068591efda50ffb2790f8e40e638530a`. Full per-start/final-state records are retained in before/after and variants.
