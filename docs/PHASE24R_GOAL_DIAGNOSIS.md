# Phase24-R goal-convergence diagnosis

Saved Phase24-R runs only. New navigation, NoMaD inference, Graph solve, tuning and rollout: **0**. Cost terms were evaluated on saved G poses/dt/reference/SDF with the frozen formula; no optimizer call was made.

## Per-seed result

| seed | G_cause | G_min_goal_m | G_min_goal_t_s | C0_min_goal_m | G_reference_count | C0_reference_count | G_combined_p95_s | G_job_p95_s | certificate_rejections | two_stage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 141 | REFERENCE_WRONG | 0.416 | 38.53 | 0.298 | 36 | 27 | 0.635 | 0.438 | 555 | 8 |
| 142 | LOCALIZATION_LOST | 1.154 | 28.92 | 0.298 | 34 | 40 | 0.641 | 0.481 | 662 | 8 |
| 143 | REFERENCE_WRONG | 0.594 | 34.28 | 0.3 | 33 | 37 | 0.66 | 0.45 | 856 | 11 |
| 144 | LOCALIZATION_LOST | 1.265 | 29.14 | 0.299 | 32 | 25 | 0.669 | 0.462 | 826 | 14 |

## Classification

- **L2 141 — REFERENCE_WRONG**: {'reference_goal_fraction': 0.7407407407407407, 'late_reference_abs_y_m': 0.8156920167233808, 'central_delta_m': 2.3663306508936444e-05, 'stops': 0}.
- **L2 142 — LOCALIZATION_LOST**: {'reference_goal_fraction': 0.7857142857142857, 'late_reference_abs_y_m': 1.068169510533623, 'central_delta_m': 0.0011804626543977514, 'stops': 0}.
- **L2 143 — REFERENCE_WRONG**: {'reference_goal_fraction': 0.7037037037037037, 'late_reference_abs_y_m': 0.6915842987631193, 'central_delta_m': 0.00012004210361471479, 'stops': 0}.
- **L2 144 — LOCALIZATION_LOST**: {'reference_goal_fraction': 0.6153846153846154, 'late_reference_abs_y_m': 1.2835257026732683, 'central_delta_m': 0.0004385801984498894, 'stops': 0}.

Reference goalward means endpoint displacement has positive dot product with B→goal; recenter means |endpoint y|<|B y|. `central_delta_m` is G output central component minus its reference central component; positive means G is relatively more outward. `LOCALIZATION_LOST` requires no post-passage closest-node increase; `NEAR_GOAL_FAILURE` requires within1m plus STOP. These are classification rules for this diagnostic only.

## References, outputs and costs

| seed | method | passage_time_s | minimum_goal_distance_m | minimum_goal_time_s | reference_count | goalward_fraction | recenter_fraction | topomap_start | topomap_end | classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 141 | G | 29.222 | 0.41644 | 67.75 | 36 | 0.96296 | 0.74074 | {'t': 29.666666666666668, 'relative_t': 0.4444444444444464, 'closest': 11, 'subgoal': 11, 'backward': False} | {'t': 89.66666666666667, 'relative_t': 60.44444444444445, 'closest': 17, 'subgoal': 17, 'backward': False} | REFERENCE_WRONG |
| 141 | C0 | 30.708 | 0.29777 | 71.222 | 27 | 1 | 0.88889 | {'t': 31.666666666666668, 'relative_t': 0.9583333333333357, 'closest': 10, 'subgoal': 10, 'backward': True} | {'t': 70.33333333333333, 'relative_t': 39.625, 'closest': 20, 'subgoal': 20, 'backward': False} | — |
| 142 | G | 36.903 | 1.1537 | 65.819 | 34 | 0.89286 | 0.78571 | {'t': 37.666666666666664, 'relative_t': 0.7638888888888928, 'closest': 8, 'subgoal': 8, 'backward': False} | {'t': 89.44444444444444, 'relative_t': 52.54166666666667, 'closest': 9, 'subgoal': 9, 'backward': False} | LOCALIZATION_LOST |
| 142 | C0 | 37.181 | 0.29833 | 77.458 | 40 | 0.925 | 0.75 | {'t': 37.333333333333336, 'relative_t': 0.15277777777778567, 'closest': 9, 'subgoal': 9, 'backward': True} | {'t': 77.11111111111111, 'relative_t': 39.930555555555564, 'closest': 20, 'subgoal': 20, 'backward': False} | — |
| 143 | G | 45.222 | 0.59446 | 79.5 | 33 | 0.96296 | 0.7037 | {'t': 45.333333333333336, 'relative_t': 0.11111111111111427, 'closest': 8, 'subgoal': 8, 'backward': True} | {'t': 89.11111111111111, 'relative_t': 43.88888888888889, 'closest': 19, 'subgoal': 19, 'backward': False} | REFERENCE_WRONG |
| 143 | C0 | 34 | 0.29959 | 75.458 | 37 | 0.89189 | 0.72973 | {'t': 34.44444444444444, 'relative_t': 0.44444444444444287, 'closest': 10, 'subgoal': 10, 'backward': True} | {'t': 74.88888888888889, 'relative_t': 40.888888888888886, 'closest': 20, 'subgoal': 20, 'backward': False} | — |
| 144 | G | 32.444 | 1.2651 | 61.583 | 32 | 0.73077 | 0.61538 | {'t': 32.888888888888886, 'relative_t': 0.44444444444444287, 'closest': 11, 'subgoal': 11, 'backward': True} | {'t': 89.66666666666667, 'relative_t': 57.22222222222223, 'closest': 2, 'subgoal': 2, 'backward': False} | LOCALIZATION_LOST |
| 144 | C0 | 37.653 | 0.29929 | 77.292 | 25 | 0.92 | 0.88 | {'t': 37.888888888888886, 'relative_t': 0.23611111111111427, 'closest': 8, 'subgoal': 8, 'backward': True} | {'t': 76.66666666666667, 'relative_t': 39.0138888888889, 'closest': 19, 'subgoal': 19, 'backward': True} | — |

Median G NORMAL output costs:

| seed | reference | endpoint | clearance | time | curvature | nonholonomic | backward | acceleration | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 141 | 0.1888 | 0.0002 | 0 | 1.6297 | 0.0096 | 0.1517 | 0 | 0 | 2.279 |
| 142 | 0.4724 | 0.0004 | 0 | 2.9765 | 0.0469 | 0.2637 | 0 | 0 | 3.8231 |
| 143 | 0.5853 | 0.0004 | 0 | 1.745 | 0.0154 | 0.165 | 0 | 0 | 3.0512 |
| 144 | 0.8841 | 0.0005 | 0.3062 | 1.8207 | 0.0166 | 0.1538 | 0 | 0 | 6.5956 |

The saved G normal-output costs are also in `references.csv` as JSON `cost_terms`; terms use {'reference': 'sum_i ||p_i-r_i||²/sigma²', 'endpoint': '||p_10-r_10||²/.3²', 'clearance': 'sum_q max(0,.15-d(q))²/.05²', 'time': 'sum dt', 'curvature': '.01 sum(delta kappa)²', 'nonholonomic': 'frozen TEB lateral and backward soft residuals', 'acceleration': 'soft |a|>.5 penalty'}. In all four seeds endpoint cost is nearly zero because G ends near its reference endpoint. Reference/time/nonholonomic terms dominate; clearance cost is material only in seed144. The median G−reference central component is 0.0–1.2mm, so these terms do not show G preferring a more outward endpoint than the selected reference.

## Timing

- L2 141: job p95 0.438s; pipeline p95 0.635s; strict-EDT build p95 0.050s; >0.5s jobs 0/67; NORMAL→DETOUR second stages 8; certificate rejections 555; alternate accepted starts 1; late certificate checks 0; unavailable at the fixed due tick 0; application wall p95 0.499s.
- L2 142: job p95 0.481s; pipeline p95 0.641s; strict-EDT build p95 0.049s; >0.5s jobs 3/68; NORMAL→DETOUR second stages 8; certificate rejections 662; alternate accepted starts 5; late certificate checks 0; unavailable at the fixed due tick 0; application wall p95 0.499s.
- L2 143: job p95 0.450s; pipeline p95 0.660s; strict-EDT build p95 0.048s; >0.5s jobs 0/76; NORMAL→DETOUR second stages 11; certificate rejections 856; alternate accepted starts 4; late certificate checks 0; unavailable at the fixed due tick 0; application wall p95 0.499s.
- L2 144: job p95 0.462s; pipeline p95 0.669s; strict-EDT build p95 0.047s; >0.5s jobs 2/81; NORMAL→DETOUR second stages 14; certificate rejections 826; alternate accepted starts 1; late certificate checks 0; unavailable at the fixed due tick 0; application wall p95 0.499s.

The stored `compute_p95_s≈0.65s` is wall time from dispatch to final broker output. It includes strict EDT/cache construction, all multi-start solver work until the 0.5s deadline, certificate evaluation and transport. A NORMAL failure followed by DETOUR sums two stage times in the pipeline metric. The installed G path remains tied to its fixed 0.5s due tick; if a result is unavailable then, the log records STOP. Thus p95 above0.5s signals CPU/transport completion after the registered deadline, rather than permission to apply late.

## Topomap and near-goal evidence

The per-reference rows record closest/subgoal at each fresh input. Compare first/last `topomap` fields in `summary.csv`; source logs remain untouched. Near-goal rows (goal distance≤1m) include G output type, reference length and compute time in `near_goal.csv`; mode intervals are in `modes.csv`. No G run has a recorded goal-entry because all minimum goal distances remain above0.3m.

![Post-passage paths](../research/results/phase24r_goal_diagnosis/paths.png)

![Goal distance and lateral magnitude](../research/results/phase24r_goal_diagnosis/timeseries.png)
