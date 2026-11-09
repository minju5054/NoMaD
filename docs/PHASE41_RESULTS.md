| status | completed | paired_valid | planned | protocol_sha256 |
|---|---|---|---|---|
| COMPLETE | 15 | 15 | 15 | 3bd94c578cb18be8fb1095046763ad42e19082d21c84ce54356e78117707df4c |

| metric | definition |
|---|---|
| Phase41 main | declared arrival AND goal distance<=0.5m AND no collision |
| Phase41 auxiliary | same declaration; distance<=0.3m / <=1.0m |
| Phase38 existing | frozen geometric0.3m arrival outcome; different execution day |
| wrong stop | Phase41 declaration at>0.5m; not applicable to Phase38 geometric-stop rule |
| timeout | simulation/navigation wall timeout without terminal arrival; collision/corridor stops counted separately |

| group | scene | method | completed | valid | technical_failures | success | collision | success_0p3 | success_1p0 | wrong_stop | timeout_without_arrival | stop_distance_median_m |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase38 existing | SLW | OURS-DETOUR | 3 | 3 | 0 | 1 | 0 | 1 | 1 | — | 2 | 0.29815 |
| Phase41 declared | SLW | OURS-DETOUR | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3.0501 |
| Phase38 existing | LC | OURS-DETOUR | 3 | 3 | 0 | 3 | 0 | 3 | 3 | — | 0 | 0.29943 |
| Phase41 declared | LC | OURS-DETOUR | 3 | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 0 | 0.37147 |
| Phase38 existing | L2 | OURS-DETOUR | 3 | 3 | 0 | 1 | 0 | 1 | 1 | — | 2 | 0.29835 |
| Phase41 declared | L2 | OURS-DETOUR | 3 | 3 | 0 | 1 | 0 | 0 | 1 | 2 | 0 | 5.2696 |
| Phase38 existing | H1 | OURS-DETOUR | 3 | 3 | 0 | 3 | 0 | 3 | 3 | — | 0 | 0.29884 |
| Phase41 declared | H1 | OURS-DETOUR | 3 | 3 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 0.64692 |
| Phase38 existing | H2 | OURS-DETOUR | 3 | 3 | 0 | 2 | 0 | 2 | 2 | — | 1 | 0.2995 |
| Phase41 declared | H2 | OURS-DETOUR | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 5.3026 |
| Phase38 existing | ALL | OURS-DETOUR | 15 | 15 | 0 | 10 | 0 | 10 | 10 | — | 5 | 0.29916 |
| Phase41 declared | ALL | OURS-DETOUR | 15 | 15 | 0 | 4 | 0 | 0 | 7 | 11 | 0 | 2.5472 |

| n | success_delta | success_0p3_delta | collision_delta | phase41_only | phase38_only |
|---|---|---|---|---|---|
| 15 | -6 | -10 | 0 | 0 | 6 |

| scene | index | paired_valid | phase38_success | phase41_success | success_delta | success_0p3_delta | collision_delta | phase38_stop_distance_m | phase41_stop_distance_m | phase38_final_distance_m | phase41_final_distance_m | phase38_termination | phase41_termination |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 217 | True | True | False | -1 | -1 | 0 | 0.29854 | 0.88083 | 0.29854 | 0.88083 | goal_entry | declared_arrival |
| H1 | 219 | True | True | False | -1 | -1 | 0 | 0.29964 | 0.64692 | 0.29964 | 0.64692 | goal_entry | declared_arrival |
| H1 | 220 | True | True | False | -1 | -1 | 0 | 0.29884 | 0.50287 | 0.29884 | 0.50287 | goal_entry | declared_arrival |
| H2 | 217 | True | True | False | -1 | -1 | 0 | 0.29995 | 5.3026 | 0.29995 | 5.3026 | goal_entry | declared_arrival |
| H2 | 219 | True | True | False | -1 | -1 | 0 | 0.29905 | 5.1326 | 0.29905 | 5.1326 | goal_entry | declared_arrival |
| H2 | 220 | True | False | False | 0 | 0 | 0 | — | 5.3937 | 0.83861 | 5.3937 | simulation_timeout | declared_arrival |
| L2 | 217 | True | True | True | 0 | -1 | 0 | 0.29835 | 0.39606 | 0.29835 | 0.39606 | goal_entry | declared_arrival |
| L2 | 219 | True | False | False | 0 | 0 | 0 | — | 5.2696 | 2.5646 | 5.2696 | simulation_timeout | declared_arrival |
| L2 | 220 | True | False | False | 0 | 0 | 0 | — | 5.591 | 2.8716 | 5.591 | simulation_timeout | declared_arrival |
| LC | 217 | True | True | True | 0 | -1 | 0 | 0.29959 | 0.43095 | 0.29959 | 0.43095 | goal_entry | declared_arrival |
| LC | 219 | True | True | True | 0 | -1 | 0 | 0.29928 | 0.37147 | 0.29928 | 0.37147 | goal_entry | declared_arrival |
| LC | 220 | True | True | True | 0 | -1 | 0 | 0.29943 | 0.37019 | 0.29943 | 0.37019 | goal_entry | declared_arrival |
| SLW | 217 | True | True | False | -1 | -1 | 0 | 0.29815 | 3.4443 | 0.29815 | 3.4443 | goal_entry | declared_arrival |
| SLW | 219 | True | False | False | 0 | 0 | 0 | — | 2.5472 | 3.2053 | 2.5472 | simulation_timeout | declared_arrival |
| SLW | 220 | True | False | False | 0 | 0 | 0 | — | 3.0501 | 3.2433 | 3.0501 | simulation_timeout | declared_arrival |
