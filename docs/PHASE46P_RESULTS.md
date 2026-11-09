| label | complete | paired_n | success | collision | graph_only | phase43_only | net_gain | checks |
|---|---|---|---|---|---|---|---|---|
| B_ONLY_NOT_OK | True | 15 | 6 | 1 | 1 | 4 | -3 | {'success_ge11': False, 'collision_le1': True, 'net_paired_gain_ge2': False} |

| item | definition |
|---|---|
| B_ONLY_OK | 15 valid pairs;success>=11,collision<=1,(current-only minus Phase43-only)>=2 |
| ALL_UNSAFE | No A/R2/R3 chain; frozen OURS-DETOUR fallback. Independently satisfied B remains enabled even on an ALL_UNSAFE tick |
| 대기 | planner_wait=REPAIR_WAIT+DETOUR_WAIT command-hold seconds; STOP_WAIT and physical stopped time shown separately |
| 상자 연관 | Post-run oracle only:minimum distance from triggering component cell centers to any already-spawned actual box XY footprint<=0.3m |
| 거짓 발동 | NON_BOX under that spatial criterion; includes no spawned box. BOX association does not establish blockage/causality |
| 관측 근거 | New runs log exact frozen-predicate component. Historical45 uses only matching archived frame; unavailable history=>UNMEASURED,not false |
| 거짓 발동 결과 | Per-trigger R3 disposition,installation,end reason and final run outcome; chronological association,not a causal attribution |
| 비교 | Same15 scene/seed/jitter pairs versus historical43/45; execution days differ |

| cohort | scene | completed | valid | success_0p5 | wrong_stop | collision | planner_wait_total_s | planner_wait_median_s | stop_wait_total_s | physical_stopped_total_s | r3_installations |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase43-P | SLW | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 6 | 48.528 | 0 |
| Phase45-P | SLW | 3 | 3 | 0 | 0 | 0 | 52.444 | 14.111 | 32.778 | 177.78 | 4 |
| Phase46-P | SLW | 3 | 3 | 0 | 1 | 1 | 25.111 | 9.8889 | 24.875 | 91.222 | 5 |
| Phase43-P | LC | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 9.1111 | 0 |
| Phase45-P | LC | 3 | 3 | 3 | 0 | 0 | 1.3333 | 0.44444 | 1.3333 | 10.25 | 3 |
| Phase46-P | LC | 3 | 3 | 3 | 0 | 0 | 1.4444 | 0.44444 | 0.55556 | 12.611 | 3 |
| Phase43-P | L2 | 3 | 3 | 0 | 2 | 0 | 0 | 0 | 6.1111 | 31 | 0 |
| Phase45-P | L2 | 3 | 3 | 2 | 1 | 0 | 9.1111 | 2.4444 | 8.3333 | 23 | 8 |
| Phase46-P | L2 | 3 | 3 | 0 | 2 | 0 | 9.3333 | 1.4444 | 7.4444 | 28.556 | 7 |
| Phase43-P | H1 | 3 | 3 | 2 | 1 | 0 | 0 | 0 | 9.7778 | 34.917 | 0 |
| Phase45-P | H1 | 3 | 3 | 2 | 0 | 0 | 10.444 | 1 | 9.4444 | 28.556 | 4 |
| Phase46-P | H1 | 3 | 3 | 3 | 0 | 0 | 4.7778 | 1.1111 | 4.2222 | 16.722 | 1 |
| Phase43-P | H2 | 3 | 3 | 1 | 1 | 0 | 0 | 0 | 2 | 26.667 | 0 |
| Phase45-P | H2 | 3 | 3 | 0 | 2 | 0 | 13 | 4.3333 | 10.333 | 43.778 | 2 |
| Phase46-P | H2 | 3 | 3 | 0 | 0 | 0 | 13.889 | 5 | 17.778 | 54.111 | 4 |
| Phase43-P | ALL | 15 | 15 | 9 | 4 | 0 | 0 | 0 | 23.889 | 150.22 | 0 |
| Phase45-P | ALL | 15 | 15 | 7 | 3 | 0 | 86.333 | 2.6667 | 62.222 | 283.36 | 21 |
| Phase46-P | ALL | 15 | 15 | 6 | 3 | 1 | 54.556 | 2.7778 | 54.875 | 203.22 | 20 |

| scene | seed | comparator | valid | current_success | baseline_success | success_delta | wrong_stop_delta | collision_delta | planner_wait_delta_s |
|---|---|---|---|---|---|---|---|---|---|
| H1 | 217 | Phase43-P | True | True | True | 0 | 0 | 0 | 2.7778 |
| H1 | 217 | Phase45-P | True | True | True | 0 | 0 | 0 | 1.7778 |
| H1 | 219 | Phase43-P | True | True | False | 1 | -1 | 0 | 0.88889 |
| H1 | 219 | Phase45-P | True | True | False | 1 | 0 | 0 | -7.6667 |
| H1 | 220 | Phase43-P | True | True | True | 0 | 0 | 0 | 1.1111 |
| H1 | 220 | Phase45-P | True | True | True | 0 | 0 | 0 | 0.22222 |
| H2 | 217 | Phase43-P | True | False | False | 0 | -1 | 0 | 5 |
| H2 | 217 | Phase45-P | True | False | False | 0 | -1 | 0 | 0.66667 |
| H2 | 219 | Phase43-P | True | False | True | -1 | 0 | 0 | 5.2222 |
| H2 | 219 | Phase45-P | True | False | False | 0 | 0 | 0 | -0.77778 |
| H2 | 220 | Phase43-P | True | False | False | 0 | 0 | 0 | 3.6667 |
| H2 | 220 | Phase45-P | True | False | False | 0 | -1 | 0 | 1 |
| L2 | 217 | Phase43-P | True | False | False | 0 | 0 | 0 | 6.8889 |
| L2 | 217 | Phase45-P | True | False | True | -1 | 0 | 0 | 0.66667 |
| L2 | 219 | Phase43-P | True | False | False | 0 | 0 | 0 | 1 |
| L2 | 219 | Phase45-P | True | False | True | -1 | 1 | 0 | 0.55556 |
| L2 | 220 | Phase43-P | True | False | False | 0 | 0 | 0 | 1.4444 |
| L2 | 220 | Phase45-P | True | False | False | 0 | 0 | 0 | -1 |
| LC | 217 | Phase43-P | True | True | True | 0 | 0 | 0 | 0.44444 |
| LC | 217 | Phase45-P | True | True | True | 0 | 0 | 0 | 3.5527e-15 |
| LC | 219 | Phase43-P | True | True | True | 0 | 0 | 0 | 0.55556 |
| LC | 219 | Phase45-P | True | True | True | 0 | 0 | 0 | 0.22222 |
| LC | 220 | Phase43-P | True | True | True | 0 | 0 | 0 | 0.44444 |
| LC | 220 | Phase45-P | True | True | True | 0 | 0 | 0 | -0.11111 |
| SLW | 217 | Phase43-P | True | False | True | -1 | 0 | 0 | 10.111 |
| SLW | 217 | Phase45-P | True | False | False | 0 | 0 | 0 | -18.333 |
| SLW | 219 | Phase43-P | True | False | True | -1 | 0 | 1 | 9.8889 |
| SLW | 219 | Phase45-P | True | False | False | 0 | 0 | 1 | -4.2222 |
| SLW | 220 | Phase43-P | True | False | True | -1 | 1 | 0 | 5.1111 |
| SLW | 220 | Phase45-P | True | False | False | 0 | 1 | 0 | -4.7778 |

| cohort | scene | trigger_b | box | non_box | unmeasured | false_r3_installed | false_r3_dispositions | false_r3_end_reasons |
|---|---|---|---|---|---|---|---|---|
| Phase43-P | SLW | 0 | 0 | 0 | 0 | 0 | {} | {} |
| Phase45-P | SLW | 31 | 0 | 31 | 0 | 4 | {'ACCEPTED': 4, 'REJECTED': 26, 'UNRESOLVED_AT_TERMINATION': 1} | {'PATH_BECAME_UNSAFE': 4, 'REJECTED': 26, 'None': 1} |
| Phase46-P | SLW | 42 | 0 | 42 | 0 | 5 | {'ACCEPTED': 5, 'APPLICATION_UNSAFE': 1, 'REJECTED': 36} | {'PATH_BECAME_UNSAFE': 4, 'APPLICATION_UNSAFE': 1, 'REJECTED': 36, 'NO_NEW_OBSTACLE_AHEAD': 1} |
| Phase43-P | LC | 0 | 0 | 0 | 0 | 0 | {} | {} |
| Phase45-P | LC | 3 | 0 | 3 | 0 | 3 | {'ACCEPTED': 3} | {'PATH_BECAME_UNSAFE': 3} |
| Phase46-P | LC | 3 | 0 | 3 | 0 | 3 | {'ACCEPTED': 3} | {'PATH_BECAME_UNSAFE': 3} |
| Phase43-P | L2 | 0 | 0 | 0 | 0 | 0 | {} | {} |
| Phase45-P | L2 | 14 | 8 | 6 | 0 | 5 | {'ACCEPTED': 5, 'APPLICATION_UNSAFE': 1} | {'PATH_BECAME_UNSAFE': 3, 'NO_NEW_OBSTACLE_AHEAD': 2, 'APPLICATION_UNSAFE': 1} |
| Phase46-P | L2 | 16 | 10 | 6 | 0 | 5 | {'REJECTED': 1, 'ACCEPTED': 5} | {'REJECTED': 1, 'NO_NEW_OBSTACLE_AHEAD': 2, 'PATH_BECAME_UNSAFE': 3} |
| Phase43-P | H1 | 0 | 0 | 0 | 0 | 0 | {} | {} |
| Phase45-P | H1 | 19 | 2 | 17 | 0 | 1 | {'REJECTED': 14, 'ACCEPTED': 1, 'APPLICATION_UNSAFE': 2} | {'REJECTED': 14, 'PATH_BECAME_UNSAFE': 1, 'APPLICATION_UNSAFE': 2} |
| Phase46-P | H1 | 8 | 1 | 7 | 0 | 1 | {'REJECTED': 6, 'ACCEPTED': 1} | {'REJECTED': 6, 'PATH_BECAME_UNSAFE': 1} |
| Phase43-P | H2 | 0 | 0 | 0 | 0 | 0 | {} | {} |
| Phase45-P | H2 | 20 | 16 | 3 | 1 | 0 | {'REJECTED': 3} | {'REJECTED': 3} |
| Phase46-P | H2 | 23 | 23 | 0 | 0 | 0 | {} | {} |
| Phase43-P | ALL | 0 | 0 | 0 | 0 | 0 | {} | {} |
| Phase45-P | ALL | 87 | 26 | 60 | 1 | 13 | {'REJECTED': 43, 'ACCEPTED': 13, 'APPLICATION_UNSAFE': 3, 'UNRESOLVED_AT_TERMINATION': 1} | {'REJECTED': 43, 'PATH_BECAME_UNSAFE': 11, 'APPLICATION_UNSAFE': 3, 'NO_NEW_OBSTACLE_AHEAD': 2, 'None': 1} |
| Phase46-P | ALL | 92 | 34 | 58 | 0 | 14 | {'REJECTED': 43, 'ACCEPTED': 14, 'APPLICATION_UNSAFE': 1} | {'REJECTED': 43, 'PATH_BECAME_UNSAFE': 11, 'NO_NEW_OBSTACLE_AHEAD': 3, 'APPLICATION_UNSAFE': 1} |

| cohort | scene | seed | job_id | trigger_s | component_id | component_source | component_cells | classification | minimum_box_distance_m | matched_box_ids | reason | r3_installed | r3_disposition | r3_end_reason | run_success | run_collision | run_termination |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase45-P | H1 | 217 | 0 | 21.222 | 105 | ARCHIVED_EXACT_FRAME | 85 | NON_BOX | 0.53397 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase45-P | H1 | 217 | 1 | 24.667 | 347 | ARCHIVED_EXACT_FRAME | 13 | BOX | 0.21397 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | True | False | declared_arrival |
| Phase45-P | H1 | 219 | 0 | 29.889 | 260 | ARCHIVED_EXACT_FRAME | 1969 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 1 | 34.556 | 100 | ARCHIVED_EXACT_FRAME | 680 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 2 | 38.111 | 100 | ARCHIVED_EXACT_FRAME | 669 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 3 | 42.333 | 260 | ARCHIVED_EXACT_FRAME | 1488 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 4 | 45.889 | 260 | ARCHIVED_EXACT_FRAME | 1483 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | APPLICATION_UNSAFE | APPLICATION_UNSAFE | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 5 | 49.444 | 111 | ARCHIVED_EXACT_FRAME | 128 | NON_BOX | 0.50217 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 6 | 53 | 187 | ARCHIVED_EXACT_FRAME | 84 | NON_BOX | 0.31217 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 9 | 62 | 477 | ARCHIVED_EXACT_FRAME | 1068 | NON_BOX | 1.2322 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | APPLICATION_UNSAFE | APPLICATION_UNSAFE | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 10 | 66.111 | 477 | ARCHIVED_EXACT_FRAME | 1012 | NON_BOX | 1.2322 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 11 | 69.556 | 477 | ARCHIVED_EXACT_FRAME | 971 | NON_BOX | 1.2322 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 12 | 73 | 477 | ARCHIVED_EXACT_FRAME | 963 | NON_BOX | 1.2322 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 13 | 76.556 | 477 | ARCHIVED_EXACT_FRAME | 888 | NON_BOX | 1.2322 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 14 | 81.111 | 477 | ARCHIVED_EXACT_FRAME | 859 | NON_BOX | 1.2322 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 15 | 84.667 | 477 | ARCHIVED_EXACT_FRAME | 859 | NON_BOX | 1.2322 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 219 | 16 | 88.111 | 473 | ARCHIVED_EXACT_FRAME | 16 | NON_BOX | 1.1754 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H1 | 220 | 0 | 20 | 145 | ARCHIVED_EXACT_FRAME | 15 | NON_BOX | 0.59069 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase45-P | H1 | 220 | 1 | 23.444 | 309 | ARCHIVED_EXACT_FRAME | 12 | BOX | 0.24069 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase45-P | H2 | 217 | 0 | 16 | 207 | ARCHIVED_EXACT_FRAME | 439 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 217 | 1 | 22.889 | 207 | ARCHIVED_EXACT_FRAME | 401 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 217 | 2 | 59.889 | 796 | ARCHIVED_EXACT_FRAME | 449 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 217 | 3 | 63.889 | 796 | ARCHIVED_EXACT_FRAME | 364 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 217 | 4 | 67.556 | 796 | ARCHIVED_EXACT_FRAME | 364 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | False | False | declared_arrival |
| Phase45-P | H2 | 217 | 5 | 82.444 | 823 | ARCHIVED_EXACT_FRAME | 5 | NON_BOX | 1.845 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 217 | 6 | 86 | 823 | ARCHIVED_EXACT_FRAME | 5 | NON_BOX | 1.845 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 219 | 0 | 14.889 | 218 | ARCHIVED_EXACT_FRAME | 417 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H2 | 219 | 1 | 18.333 | 218 | ARCHIVED_EXACT_FRAME | 344 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H2 | 219 | 6 | 25.667 | 218 | ARCHIVED_EXACT_FRAME | 340 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H2 | 219 | 7 | 29.333 | 218 | EXACT_TRIGGER_MAP_NOT_RETAINED | — | UNMEASURED | — | [] | MISSING_EXACT_TRIGGER_COMPONENT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H2 | 219 | 8 | 33.889 | 218 | ARCHIVED_EXACT_FRAME | 340 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H2 | 219 | 9 | 62.667 | 286 | ARCHIVED_EXACT_FRAME | 29 | NON_BOX | 2.1846 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H2 | 219 | 10 | 79.333 | 863 | ARCHIVED_EXACT_FRAME | 409 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | H2 | 219 | 11 | 82.889 | 863 | ARCHIVED_EXACT_FRAME | 395 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | False | False | simulation_timeout |
| Phase45-P | H2 | 220 | 0 | 16.556 | 228 | ARCHIVED_EXACT_FRAME | 452 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 220 | 1 | 20 | 228 | ARCHIVED_EXACT_FRAME | 390 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 220 | 2 | 23.556 | 228 | ARCHIVED_EXACT_FRAME | 390 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 220 | 3 | 27.111 | 228 | ARCHIVED_EXACT_FRAME | 390 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | H2 | 220 | 4 | 30.667 | 228 | ARCHIVED_EXACT_FRAME | 390 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase45-P | L2 | 217 | 0 | 15.222 | 202 | ARCHIVED_EXACT_FRAME | 475 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase45-P | L2 | 217 | 1 | 18.667 | 202 | ARCHIVED_EXACT_FRAME | 461 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase45-P | L2 | 217 | 3 | 22.556 | 202 | ARCHIVED_EXACT_FRAME | 460 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase45-P | L2 | 217 | 4 | 26.333 | 202 | ARCHIVED_EXACT_FRAME | 460 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase45-P | L2 | 217 | 5 | 30.222 | 202 | ARCHIVED_EXACT_FRAME | 460 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase45-P | L2 | 217 | 6 | 34 | 202 | ARCHIVED_EXACT_FRAME | 460 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase45-P | L2 | 217 | 7 | 49.444 | 202 | ARCHIVED_EXACT_FRAME | 926 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase45-P | L2 | 217 | 8 | 57.556 | 593 | ARCHIVED_EXACT_FRAME | 15 | NON_BOX | 1.1156 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase45-P | L2 | 217 | 9 | 64.444 | 623 | ARCHIVED_EXACT_FRAME | 802 | NON_BOX | 1.7209 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | True | False | declared_arrival |
| Phase45-P | L2 | 219 | 0 | 14.667 | 208 | ARCHIVED_EXACT_FRAME | 458 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | True | False | declared_arrival |
| Phase45-P | L2 | 220 | 2 | 23.111 | 184 | ARCHIVED_EXACT_FRAME | 296 | NON_BOX | 0.83357 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | declared_arrival |
| Phase45-P | L2 | 220 | 3 | 36.222 | 248 | ARCHIVED_EXACT_FRAME | 644 | NON_BOX | 2.6853 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | False | False | declared_arrival |
| Phase45-P | L2 | 220 | 4 | 40.222 | 248 | ARCHIVED_EXACT_FRAME | 4877 | NON_BOX | 2.6853 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | declared_arrival |
| Phase45-P | L2 | 220 | 5 | 46.333 | 248 | ARCHIVED_EXACT_FRAME | 4005 | NON_BOX | 2.6853 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | APPLICATION_UNSAFE | APPLICATION_UNSAFE | False | False | declared_arrival |
| Phase45-P | LC | 217 | 0 | 22.778 | 96 | ARCHIVED_EXACT_FRAME | 307 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase45-P | LC | 219 | 0 | 20.778 | 161 | ARCHIVED_EXACT_FRAME | 14 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase45-P | LC | 220 | 0 | 22 | 128 | ARCHIVED_EXACT_FRAME | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase45-P | SLW | 217 | 0 | 11.889 | 16 | ARCHIVED_EXACT_FRAME | 447 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase45-P | SLW | 217 | 17 | 34.333 | 16 | ARCHIVED_EXACT_FRAME | 431 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 217 | 22 | 41.667 | 16 | ARCHIVED_EXACT_FRAME | 431 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 0 | 12.889 | 2 | ARCHIVED_EXACT_FRAME | 360 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 3 | 21.667 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 4 | 25.111 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 8 | 34.889 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 15 | 47.889 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 18 | 56.778 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 20 | 61.889 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 21 | 67.889 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 22 | 71.889 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 25 | 82.889 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 219 | 28 | 89.667 | 2 | ARCHIVED_EXACT_FRAME | 339 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | UNRESOLVED_AT_TERMINATION | — | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 0 | 12.222 | 3 | ARCHIVED_EXACT_FRAME | 106 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 1 | 15.778 | 3 | ARCHIVED_EXACT_FRAME | 106 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 2 | 19.333 | 3 | ARCHIVED_EXACT_FRAME | 105 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 3 | 22.889 | 3 | ARCHIVED_EXACT_FRAME | 105 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 4 | 28.889 | 101 | ARCHIVED_EXACT_FRAME | 7 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 5 | 32.333 | 101 | ARCHIVED_EXACT_FRAME | 7 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 6 | 36.889 | 106 | ARCHIVED_EXACT_FRAME | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 7 | 40.556 | 106 | ARCHIVED_EXACT_FRAME | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 8 | 44.444 | 85 | ARCHIVED_EXACT_FRAME | 48 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 9 | 48.778 | 4 | ARCHIVED_EXACT_FRAME | 80 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 10 | 52.333 | 3 | ARCHIVED_EXACT_FRAME | 178 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 11 | 56.667 | 1 | ARCHIVED_EXACT_FRAME | 22 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 12 | 60.333 | 1 | ARCHIVED_EXACT_FRAME | 22 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 13 | 64 | 5 | ARCHIVED_EXACT_FRAME | 54 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 15 | 67.444 | 34 | ARCHIVED_EXACT_FRAME | 7 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 16 | 81.889 | 267 | ARCHIVED_EXACT_FRAME | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase45-P | SLW | 220 | 17 | 88 | 262 | ARCHIVED_EXACT_FRAME | 11 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H1 | 217 | 0 | 20.333 | 346 | LIVE_EXACT_COMPONENT | 6 | NON_BOX | 0.50146 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase46-P | H1 | 217 | 1 | 23.889 | 124 | LIVE_EXACT_COMPONENT | 108 | NON_BOX | 0.49146 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase46-P | H1 | 217 | 2 | 28.667 | 124 | LIVE_EXACT_COMPONENT | 108 | NON_BOX | 0.49146 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase46-P | H1 | 217 | 3 | 32.556 | 186 | LIVE_EXACT_COMPONENT | 112 | BOX | 0.26146 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase46-P | H1 | 219 | 0 | 19.667 | 174 | LIVE_EXACT_COMPONENT | 6 | NON_BOX | 0.59102 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase46-P | H1 | 219 | 1 | 23.111 | 286 | LIVE_EXACT_COMPONENT | 19 | NON_BOX | 0.31102 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase46-P | H1 | 220 | 0 | 21.111 | 101 | LIVE_EXACT_COMPONENT | 129 | NON_BOX | 0.50222 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase46-P | H1 | 220 | 1 | 24.667 | 317 | LIVE_EXACT_COMPONENT | 17 | NON_BOX | 0.39222 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | True | False | declared_arrival |
| Phase46-P | H2 | 217 | 0 | 18.889 | 242 | LIVE_EXACT_COMPONENT | 439 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | False | False | simulation_timeout |
| Phase46-P | H2 | 217 | 1 | 41.333 | 493 | LIVE_EXACT_COMPONENT | 416 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 217 | 2 | 46.889 | 493 | LIVE_EXACT_COMPONENT | 397 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 217 | 3 | 50.556 | 493 | LIVE_EXACT_COMPONENT | 345 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 217 | 4 | 54.222 | 493 | LIVE_EXACT_COMPONENT | 344 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 217 | 5 | 57.889 | 493 | LIVE_EXACT_COMPONENT | 344 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 217 | 6 | 61.556 | 493 | LIVE_EXACT_COMPONENT | 344 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 217 | 7 | 72.556 | 526 | LIVE_EXACT_COMPONENT | 1639 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase46-P | H2 | 219 | 0 | 15.111 | 210 | LIVE_EXACT_COMPONENT | 449 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase46-P | H2 | 219 | 1 | 19 | 210 | LIVE_EXACT_COMPONENT | 382 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 219 | 2 | 22.556 | 210 | LIVE_EXACT_COMPONENT | 381 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 219 | 3 | 53.556 | 210 | LIVE_EXACT_COMPONENT | 1174 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | False | False | simulation_timeout |
| Phase46-P | H2 | 219 | 4 | 67.333 | 772 | LIVE_EXACT_COMPONENT | 414 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 219 | 5 | 70.889 | 772 | LIVE_EXACT_COMPONENT | 415 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 219 | 6 | 74.444 | 772 | LIVE_EXACT_COMPONENT | 415 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 219 | 7 | 78.111 | 772 | LIVE_EXACT_COMPONENT | 415 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 219 | 8 | 82.667 | 772 | LIVE_EXACT_COMPONENT | 415 | BOX | 0 | ['DynamicObstacle2'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 220 | 0 | 16.333 | 239 | LIVE_EXACT_COMPONENT | 481 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 220 | 1 | 19.778 | 239 | LIVE_EXACT_COMPONENT | 482 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 220 | 2 | 23.556 | 239 | LIVE_EXACT_COMPONENT | 460 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 220 | 3 | 27.222 | 239 | LIVE_EXACT_COMPONENT | 452 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 220 | 4 | 30.778 | 239 | LIVE_EXACT_COMPONENT | 452 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | H2 | 220 | 5 | 34.444 | 239 | LIVE_EXACT_COMPONENT | 452 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 0 | 15.667 | 226 | LIVE_EXACT_COMPONENT | 484 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 1 | 19.333 | 226 | LIVE_EXACT_COMPONENT | 453 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 2 | 24.667 | 226 | LIVE_EXACT_COMPONENT | 403 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 3 | 28.444 | 226 | LIVE_EXACT_COMPONENT | 402 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 4 | 32.111 | 226 | LIVE_EXACT_COMPONENT | 402 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 5 | 35.667 | 226 | LIVE_EXACT_COMPONENT | 402 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 6 | 39.667 | 226 | LIVE_EXACT_COMPONENT | 402 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 7 | 43.222 | 226 | LIVE_EXACT_COMPONENT | 402 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 8 | 66 | 583 | LIVE_EXACT_COMPONENT | 17 | NON_BOX | 1.8512 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 9 | 71.778 | 78 | LIVE_EXACT_COMPONENT | 302 | NON_BOX | 0.89292 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | False | False | simulation_timeout |
| Phase46-P | L2 | 217 | 10 | 81.667 | 602 | LIVE_EXACT_COMPONENT | 340 | NON_BOX | 1.7115 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase46-P | L2 | 219 | 0 | 14.667 | 227 | LIVE_EXACT_COMPONENT | 356 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | declared_arrival |
| Phase46-P | L2 | 219 | 1 | 32.667 | 260 | LIVE_EXACT_COMPONENT | 780 | NON_BOX | 2.6465 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | declared_arrival |
| Phase46-P | L2 | 220 | 0 | 16.667 | 227 | LIVE_EXACT_COMPONENT | 612 | BOX | 0 | ['DynamicObstacle'] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | False | False | declared_arrival |
| Phase46-P | L2 | 220 | 1 | 26.556 | 234 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | 1.6202 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | declared_arrival |
| Phase46-P | L2 | 220 | 2 | 32 | 245 | LIVE_EXACT_COMPONENT | 1217 | NON_BOX | 2.4748 | [] | CELL_CENTER_TO_BOX_FOOTPRINT | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | False | False | declared_arrival |
| Phase46-P | LC | 217 | 0 | 22.444 | 118 | LIVE_EXACT_COMPONENT | 28 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase46-P | LC | 219 | 0 | 26.889 | 246 | LIVE_EXACT_COMPONENT | 66 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase46-P | LC | 220 | 0 | 20.667 | 147 | LIVE_EXACT_COMPONENT | 10 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | True | False | declared_arrival |
| Phase46-P | SLW | 217 | 0 | 12.889 | 1 | LIVE_EXACT_COMPONENT | 36 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 1 | 19.333 | 19 | LIVE_EXACT_COMPONENT | 329 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | APPLICATION_UNSAFE | APPLICATION_UNSAFE | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 2 | 22.889 | 102 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 3 | 27.778 | 109 | LIVE_EXACT_COMPONENT | 9 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 4 | 32.889 | 109 | LIVE_EXACT_COMPONENT | 9 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 5 | 36.667 | 123 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 6 | 44 | 102 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 7 | 50.889 | 1 | LIVE_EXACT_COMPONENT | 307 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 8 | 54.333 | 1 | LIVE_EXACT_COMPONENT | 284 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 9 | 58 | 1 | LIVE_EXACT_COMPONENT | 284 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 10 | 61.444 | 1 | LIVE_EXACT_COMPONENT | 284 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 11 | 67.778 | 98 | LIVE_EXACT_COMPONENT | 15 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 12 | 71.444 | 98 | LIVE_EXACT_COMPONENT | 15 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 13 | 75.889 | 135 | LIVE_EXACT_COMPONENT | 97 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 14 | 82 | 135 | LIVE_EXACT_COMPONENT | 51 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 15 | 85.556 | 135 | LIVE_EXACT_COMPONENT | 51 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 217 | 16 | 89.111 | 135 | LIVE_EXACT_COMPONENT | 51 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | simulation_timeout |
| Phase46-P | SLW | 219 | 0 | 12.889 | 2 | LIVE_EXACT_COMPONENT | 353 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 1 | 16.333 | 2 | LIVE_EXACT_COMPONENT | 351 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | PATH_BECAME_UNSAFE | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 2 | 22.889 | 2 | LIVE_EXACT_COMPONENT | 331 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 3 | 26.889 | 2 | LIVE_EXACT_COMPONENT | 329 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 4 | 30.889 | 2 | LIVE_EXACT_COMPONENT | 329 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 5 | 34.556 | 2 | LIVE_EXACT_COMPONENT | 329 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 6 | 38.333 | 2 | LIVE_EXACT_COMPONENT | 329 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 7 | 41.778 | 2 | LIVE_EXACT_COMPONENT | 329 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 8 | 45.222 | 4 | LIVE_EXACT_COMPONENT | 119 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 9 | 51.444 | 120 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 10 | 58.889 | 120 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 11 | 62.556 | 120 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 12 | 66.444 | 120 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 13 | 70.111 | 120 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 14 | 73.667 | 4 | LIVE_EXACT_COMPONENT | 123 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 15 | 77.222 | 2 | LIVE_EXACT_COMPONENT | 333 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 219 | 16 | 80.778 | 2 | LIVE_EXACT_COMPONENT | 333 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | True | corridor_footprint_stop |
| Phase46-P | SLW | 220 | 0 | 14.333 | 98 | LIVE_EXACT_COMPONENT | 8 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | True | ACCEPTED | NO_NEW_OBSTACLE_AHEAD | False | False | declared_arrival |
| Phase46-P | SLW | 220 | 1 | 27.444 | 118 | LIVE_EXACT_COMPONENT | 16 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase46-P | SLW | 220 | 2 | 34.778 | 155 | LIVE_EXACT_COMPONENT | 6 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase46-P | SLW | 220 | 3 | 38.667 | 155 | LIVE_EXACT_COMPONENT | 6 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase46-P | SLW | 220 | 4 | 42.667 | 157 | LIVE_EXACT_COMPONENT | 6 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase46-P | SLW | 220 | 5 | 46.333 | 159 | LIVE_EXACT_COMPONENT | 9 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase46-P | SLW | 220 | 6 | 50 | 165 | LIVE_EXACT_COMPONENT | 5 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | declared_arrival |
| Phase46-P | SLW | 220 | 7 | 53.667 | 158 | LIVE_EXACT_COMPONENT | 12 | NON_BOX | — | [] | NO_SPAWNED_SUDDEN_BOX | False | REJECTED | REJECTED | False | False | declared_arrival |
