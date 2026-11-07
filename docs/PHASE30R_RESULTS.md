# Phase30-R same-seed comparison

INCLUDE_TONIGHT

{
  "label": "INCLUDE_TONIGHT",
  "checks": {
    "valid_evidence": true,
    "goal": true,
    "collision": true,
    "time": true
  },
  "goal": 7,
  "baseline_goal": 5,
  "collision": 0,
  "baseline_collision": 3,
  "successful_pairs": 3,
  "goal_time_difference_median_s": -3.375,
  "note": "Missing/technical-invalid outcomes do not establish the safety condition; empty successful pairs do not establish negative median."
}

| scene | method | n | goal | collision | goal_time_s | mean_speed_m_s | detour_execution_s | detour_path_length_m | detour_actual_distance_m | repair_execution_s | repair_path_length_m | box_passage_from_spawn_s | minimum_clearance_m |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW | G18 | 2 | 0 | 2 | — | 0.092476 | 2.8889 | 2.1094 | 0.64872 | 1.1597 | 0.3481 | — | -0.000153 |
| SLW | G18-R | 2 | 2 | 0 | 66.174 | 0.10881 | 1.6111 | 2.6371 | 0.33619 | 1.7778 | 0.52587 | — | 0.030747 |
| LC | G18 | 2 | 2 | 0 | 32.931 | 0.1623 | 2 | 1.6202 | 0.57222 | 0 | 0 | — | 0.15519 |
| LC | G18-R | 2 | 2 | 0 | 49.785 | 0.15717 | 3.7222 | 3.412 | 0.91476 | 0 | 0 | — | 0.082575 |
| L2 | G18 | 2 | 0 | 0 | — | 0.13519 | 3.5556 | 4.4696 | 0.86634 | 0.27778 | 0.14812 | 69.076 | 0.070331 |
| L2 | G18-R | 2 | 1 | 0 | 74.333 | 0.15601 | 6.7222 | 6.2458 | 1.7475 | 0.44444 | 0.16537 | 38.708 | 0.012469 |
| H1 | G18 | 2 | 1 | 1 | 34.556 | 0.17472 | 0.35417 | 0.84347 | 0.083876 | 0 | 0 | 9.0139 | 0.023771 |
| H1 | G18-R | 2 | 1 | 0 | 34.083 | 0.10783 | 1.3333 | 1.6495 | 0.36296 | 0.44444 | 0.12526 | 8.875 | 0.059309 |
| H2 | G18 | 2 | 2 | 0 | 62.458 | 0.15644 | 5.5556 | 4.6184 | 1.435 | 0 | 0 | 34.444 | 0.047744 |
| H2 | G18-R | 2 | 1 | 0 | 54.819 | 0.14885 | 3.7778 | 3.7248 | 0.95538 | 0.88889 | 0.25136 | 34.667 | 0.013576 |
| ALL | G18 | 10 | 5 | 3 | 34.556 | 0.15523 | 2.3889 | 1.6543 | 0.57222 | 0 | 0 | 37.833 | 0.037719 |
| ALL | G18-R | 10 | 7 | 0 | 56.306 | 0.14037 | 2.3333 | 2.6371 | 0.64444 | 0.44444 | 0.12526 | 33.799 | 0.030747 |

| scene | index | new_goal | old_goal | new_collision | old_collision | goal_time_s_difference | mean_speed_m_s_difference | detour_execution_s_difference | detour_path_length_m_difference | box_passage_from_spawn_s_difference | minimum_clearance_m_difference | paired_goal_time_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 201 | True | False | False | True | — | -0.037752 | -0.70833 | -0.48358 | — | 0.072247 | — |
| H1 | 202 | False | True | False | False | — | -0.096039 | 2.6667 | 2.0957 | — | -0.0011731 | — |
| H2 | 201 | True | True | False | False | -3.7778 | 0.00064885 | -0.77778 | -1.5931 | -3.1667 | -0.018345 | -3.7778 |
| H2 | 202 | False | True | False | False | — | -0.015834 | -2.7778 | -0.19426 | — | -0.049991 | — |
| L2 | 201 | True | False | False | False | — | 0.009792 | -6.7778 | -7.47 | -14.556 | -0.010387 | — |
| L2 | 202 | False | False | False | False | — | 0.031834 | 13.111 | 11.022 | -46.181 | -0.10534 | — |
| LC | 201 | True | True | False | False | -3.375 | 0.019697 | 0.11111 | -0.0086073 | — | -0.061415 | -3.375 |
| LC | 202 | True | True | False | False | 37.083 | -0.029947 | 3.3333 | 3.5921 | — | -0.083815 | 37.083 |
| SLW | 201 | True | False | False | True | — | 0.019119 | -1.6667 | -0.2192 | — | 0.02728 | — |
| SLW | 202 | True | False | False | True | — | 0.013556 | -0.88889 | 1.2746 | — | 0.034519 | — |

G18 baseline reuses Phase29 dev seeds201/202; different execution dates. Only NORMAL CLR and R3 CLR preference targets change .15→.08m. R2 has no soft clearance factor and is unchanged.

Detour execution is R3 APPLIED→END (includes its alignment), summed per run; terminal active intervals are censored at run end and flagged. Detour path length sums the polylines actually installed (not just solved). Actual travelled detour distance and R2 repair time/length are separate columns. Box passage time is from spawn; multi-box aggregation is the frozen evaluator value. Goal-time comparison uses both-success pairs only; other medians include all valid outcomes. Minimum clearance is descriptive, not part of INCLUDE_TONIGHT.
