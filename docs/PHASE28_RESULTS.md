# Phase28 results — R1 online

C0 rows reuse Phase27-R; new NA/H runs occurred later. Descriptive continuous outcomes; no new performance label. Goal time uses successes only; other metrics include valid failures. Medians per method/scene; event-type fractions pool cases, not run-level percentages. Technical paired exclusions: []

Protocol SHA256 `b272242cbe907a4559967b4caf1d998caf1f3b0bb2d7fdc53c9475c736d97bcc`. Registered gate remains GATE_FAIL; user deviation: {"user_authorized": true, "date": "2026-11-06T19:55:55+09:00", "original_gate_label": "GATE_FAIL", "original_gate": {"label": "GATE_FAIL", "sets": {"same": {"n": 200, "optimized": 160, "accepted": 171, "optimized_fraction": 0.8, "accepted_fraction": 0.855, "p95_s": 0.08663808084675108, "checks": {"optimized": true, "accepted": false, "timing": true}, "passed": false}, "new": {"n": 200, "optimized": 153, "accepted": 173, "optimized_fraction": 0.765, "accepted_fraction": 0.865, "p95_s": 0.08848874605428134, "checks": {"optimized": true, "accepted": false, "timing": true}, "passed": false}}, "failed_checks": ["same:accepted", "new:accepted"], "criteria": {"per_sample_set_n": 200, "optimized_min": 0.7, "accepted_min": 0.9, "p95_max_s": 0.15, "require_both_sets": true}}, "user_rationale": "FALLBACK uses frozen C0-NA, therefore user accepts the narrowly failed gate and elects to drive", "caveat": "Same fallback does not guarantee no worse outcome: waiting, state, accepted paths, and handover timing can differ.", "action": "Exception to eligibility gate only; R1 values, costs, limits and0.15s deadline unchanged; no navigation by agent"}. Identical fallback does not guarantee noninferiority because waiting, state and accepted trajectories can differ.

| scene | method | n | goal | collision | goal_time_s | mean_speed_m_s | stopped_fraction | alignment_rotation_fraction | alignment_brake_fraction | minimum_clearance_m | feedback_clip_fraction | handoff_calls | handoff_applied | handoff_case_count | OPTIMIZED_count | INIT_ONLY_count | FALLBACK_count | OPTIMIZED_fraction | INIT_ONLY_fraction | FALLBACK_fraction | all_case_compute_p95_median_s | feedback_clip_fraction_pooled |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW | C0 | 2 | 0 | 0 | — | 0.0588 | 0.6716 | 0.4864 | 0.02778 | 0.08967 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SLW | C0-NA | 2 | 0 | 1 | — | 0.09592 | 0.4107 | 0.1111 | 0.04173 | 0.003266 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SLW | C0-H | 2 | 0 | 2 | — | 0.1334 | 0.4166 | 0.1277 | 0.02934 | -0.0003854 | — | 33 | 0 | 33 | 0 | 0 | 33 | 0 | 0 | 1 | 0.1591 | — |
| LC | C0 | 2 | 2 | 0 | 37.8 | 0.1413 | 0.2851 | 0.1733 | 0.08372 | 0.1534 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| LC | C0-NA | 2 | 1 | 1 | 26.47 | 0.1804 | 0.1623 | 0.0332 | 0.03949 | 0.08792 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| LC | C0-H | 2 | 2 | 0 | 30.23 | 0.1769 | 0.1696 | 0.03424 | 0.04428 | 0.1162 | — | 50 | 0 | 50 | 0 | 0 | 50 | 0 | 0 | 1 | 0.1618 | — |
| L2 | C0 | 2 | 2 | 0 | 54.09 | 0.161 | 0.2271 | 0.1371 | 0.05669 | 0.1368 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| L2 | C0-NA | 2 | 2 | 0 | 49.13 | 0.1748 | 0.1413 | 0.02829 | 0.03278 | 0.08028 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| L2 | C0-H | 2 | 2 | 0 | 54.17 | 0.1639 | 0.1831 | 0.05619 | 0.04522 | 0.06071 | — | 89 | 0 | 89 | 0 | 0 | 89 | 0 | 0 | 1 | 0.1709 | — |
| H1 | C0 | 2 | 1 | 1 | 29.99 | 0.148 | 0.2974 | 0.1695 | 0.05324 | 0.07147 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| H1 | C0-NA | 2 | 2 | 0 | 31.78 | 0.172 | 0.1521 | 0.02269 | 0.008813 | 0.0932 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| H1 | C0-H | 2 | 1 | 1 | 66 | 0.1147 | 0.3136 | 0.06074 | 0.04455 | 0.02421 | — | 103 | 0 | 103 | 0 | 0 | 103 | 0 | 0 | 1 | 0.1626 | — |
| H2 | C0 | 2 | 1 | 0 | 54.93 | 0.1491 | 0.2641 | 0.1626 | 0.06788 | 0.03962 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| H2 | C0-NA | 2 | 0 | 1 | — | 0.1606 | 0.189 | 0.03552 | 0.04696 | 0.02847 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| H2 | C0-H | 2 | 1 | 1 | 55.56 | 0.1377 | 0.248 | 0.05898 | 0.04276 | 0.02057 | — | 93 | 0 | 93 | 0 | 0 | 93 | 0 | 0 | 1 | 0.1691 | — |
| ALL | C0 | 10 | 6 | 1 | 42.34 | 0.1431 | 0.2791 | 0.1777 | 0.05681 | 0.1368 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| ALL | C0-NA | 10 | 5 | 3 | 32.89 | 0.1659 | 0.1539 | 0.02884 | 0.03277 | 0.02845 | — | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| ALL | C0-H | 10 | 6 | 4 | 52.85 | 0.1578 | 0.2494 | 0.04906 | 0.04522 | 0.03567 | — | 368 | 0 | 368 | 0 | 0 | 368 | 0 | 0 | 1 | 0.1641 | — |

| scene | index | method | goal | baseline_goal | collision | baseline_collision | goal_difference | collision_difference | goal_time_s_difference | mean_speed_m_s_difference | stopped_fraction_difference | alignment_rotation_fraction_difference | minimum_clearance_m_difference |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW | 201 | C0-NA | False | False | False | False | 0 | 0 | — | 0.04195 | -0.3185 | -0.5864 | -0.1549 |
| SLW | 201 | C0-H | False | False | True | False | 0 | 1 | — | 0.03271 | -0.175 | -0.3767 | -0.1623 |
| SLW | 202 | C0-NA | False | False | True | False | 0 | 1 | — | 0.0323 | -0.2033 | -0.1643 | -0.01794 |
| SLW | 202 | C0-H | False | False | True | False | 0 | 1 | — | 0.1165 | -0.335 | -0.3407 | -0.01781 |
| LC | 201 | C0-NA | True | True | False | False | 0 | 0 | -10.39 | 0.054 | -0.09714 | -0.09592 | 0.02803 |
| LC | 201 | C0-H | True | True | False | False | 0 | 0 | -8.542 | 0.04751 | -0.07397 | -0.08497 | 0.01158 |
| LC | 202 | C0-NA | False | True | True | False | -1 | 1 | — | 0.02421 | -0.1484 | -0.1843 | -0.159 |
| LC | 202 | C0-H | True | True | False | False | 0 | 0 | -6.597 | 0.02361 | -0.1569 | -0.1931 | -0.08602 |
| L2 | 201 | C0-NA | True | True | False | False | 0 | 0 | -12.96 | 0.03065 | -0.1051 | -0.1453 | -0.1169 |
| L2 | 201 | C0-H | True | True | False | False | 0 | 0 | -12.08 | 0.03111 | -0.1122 | -0.1146 | -0.04802 |
| L2 | 202 | C0-NA | True | True | False | False | 0 | 0 | 3.042 | -0.003049 | -0.06645 | -0.07239 | 0.003913 |
| L2 | 202 | C0-H | True | True | False | False | 0 | 0 | 12.24 | -0.02531 | 0.02424 | -0.04721 | -0.1041 |
| H1 | 201 | C0-NA | True | True | False | False | 0 | 0 | 0.6806 | -0.0002392 | -0.06274 | -0.07831 | 0.00857 |
| H1 | 201 | C0-H | False | True | True | False | -1 | 1 | — | -0.06054 | 0.07562 | -0.06443 | -0.1439 |
| H1 | 202 | C0-NA | True | False | False | True | 1 | -1 | — | 0.04837 | -0.2278 | -0.2152 | 0.0349 |
| H1 | 202 | C0-H | True | False | False | True | 1 | -1 | — | -0.006046 | -0.04313 | -0.153 | 0.04936 |
| H2 | 201 | C0-NA | False | False | False | False | 0 | 0 | — | 0.01098 | -0.1469 | -0.1346 | 0.01661 |
| H2 | 201 | C0-H | False | False | True | False | 0 | 1 | — | -0.0401 | 0.04043 | -0.0897 | -0.04083 |
| H2 | 202 | C0-NA | False | True | True | False | -1 | 1 | — | 0.01216 | -0.003219 | -0.1196 | -0.03889 |
| H2 | 202 | C0-H | True | True | False | False | 0 | 0 | 0.625 | 0.01729 | -0.07259 | -0.1175 | 0.002734 |

H event types/reasons and all-case timing: `handoff_statistics.json`. Effective FALLBACK includes discarded/superseded H jobs, which are distinguished by reason and applied flags; it does not imply an explicit NA installation for a discarded job. Numerical solver output types are separately reported. Clip fractions count actual H feedforward+feedback commands. Original R1 numerical code, C0-NA, decision, detour, selector and evaluator remain frozen.
