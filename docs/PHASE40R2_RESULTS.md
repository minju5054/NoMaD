| complete | n | goals | collisions | ours_only | pilot_label | graph_label |
|---|---|---|---|---|---|---|
| True | 20 | 13 | 0 | 2 | PILOT_NOT_OK | NO_GRAPH_GAIN |

| scene | method | n | goal | collision | arrival_median_s |
|---|---|---|---|---|---|
| SLW | OURS-R2 | 4 | 1 | 0 | 46.611 |
| SLW | OURS-DETOUR | 4 | 2 | 0 | 54.778 |
| SLW | OURS | 4 | 1 | 0 | 43.375 |
| SLW | ASTAR+EC | 4 | 2 | 0 | 70.806 |
| LC | OURS-R2 | 4 | 4 | 0 | 34.521 |
| LC | OURS-DETOUR | 4 | 4 | 0 | 29.507 |
| LC | OURS | 4 | 4 | 0 | 32.91 |
| LC | ASTAR+EC | 4 | 3 | 0 | 31.514 |
| L2 | OURS-R2 | 4 | 3 | 0 | 45.514 |
| L2 | OURS-DETOUR | 4 | 2 | 0 | 48.062 |
| L2 | OURS | 4 | 3 | 0 | 49.361 |
| L2 | ASTAR+EC | 4 | 2 | 0 | 60.278 |
| H1 | OURS-R2 | 4 | 4 | 0 | 35.312 |
| H1 | OURS-DETOUR | 4 | 4 | 0 | 43.201 |
| H1 | OURS | 4 | 2 | 0 | 31.861 |
| H1 | ASTAR+EC | 4 | 2 | 1 | 30.694 |
| H2 | OURS-R2 | 4 | 1 | 0 | 51.278 |
| H2 | OURS-DETOUR | 4 | 3 | 0 | 48.306 |
| H2 | OURS | 4 | 2 | 0 | 70.556 |
| H2 | ASTAR+EC | 4 | 3 | 0 | 82.111 |
| ALL | OURS-R2 | 20 | 13 | 0 | 40.917 |
| ALL | OURS-DETOUR | 20 | 15 | 0 | 47.028 |
| ALL | OURS | 20 | 12 | 0 | 38.882 |
| ALL | ASTAR+EC | 20 | 12 | 1 | 47.417 |

| comparator | metric | n | ours_only | other_only | p_exact |
|---|---|---|---|---|---|
| OURS-DETOUR | success | 20 | 2 | 4 | 0.6875 |
| OURS-DETOUR | collision | 20 | 0 | 0 | 1 |
| OURS | success | 20 | 4 | 3 | 1 |
| OURS | collision | 20 | 0 | 0 | 1 |
| ASTAR+EC | success | 20 | 6 | 5 | 1 |
| ASTAR+EC | collision | 20 | 0 | 1 | 1 |

| comparator | n | arrival_delta_median_s | distance_delta_median_m |
|---|---|---|---|
| OURS-DETOUR | 11 | -0.25 | 0.046694 |
| OURS | 9 | -0.13889 | 0.037003 |
| ASTAR+EC | 7 | -2.0278 | 0.17516 |

| scene | index | planner_installations | escape_installations | consecutive_escape_installations | escape_time_p50_s | escape_time_p95_s | escape_two_second_cap_installations | escape_two_second_cap_jobs | escape_periodic_rejections | waiting_seconds | stopped_while_waiting_seconds | result_dispositions | compute_p50_s | compute_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 217 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | {} | — | — |
| H1 | 218 | {'R2': 3} | 0 | 0 | — | — | 0 | 0 | 0 | 4.6667 | 3.3333 | {'ACCEPTED': 3, 'REJECTED': 3} | 0.21401 | 0.27892 |
| H1 | 219 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | {} | — | — |
| H1 | 220 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | {} | — | — |
| H2 | 217 | {'R2': 2} | 0 | 0 | — | — | 0 | 0 | 0 | 2.3333 | 1.5556 | {'EXEC_CERT_REJECT': 1, 'ACCEPTED': 2} | 0.2108 | 0.22253 |
| H2 | 218 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | {} | — | — |
| H2 | 219 | {'R2': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 0.77778 | 0.77778 | {'ACCEPTED': 1} | 0.18895 | 0.18895 |
| H2 | 220 | {'R2': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 0.77778 | 0 | {'ACCEPTED': 1} | 0.23028 | 0.23028 |
| L2 | 217 | {'R2': 2} | 2 | 1 | 2 | 2 | 2 | 2 | 0 | 4.6667 | 4.1111 | {'REJECTED': 1, 'EXEC_CERT_REJECT': 3, 'ACCEPTED': 2} | 0.23517 | 0.26351 |
| L2 | 218 | {'R2': 2} | 0 | 0 | — | — | 0 | 0 | 0 | 1.5556 | 1.5556 | {'ACCEPTED': 2} | 0.19351 | 0.19825 |
| L2 | 219 | {'R2': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 0.77778 | 0.44444 | {'ACCEPTED': 1} | 0.23363 | 0.23363 |
| L2 | 220 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | {} | — | — |
| LC | 217 | {'R2': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 1.5556 | 1.4444 | {'EXEC_CERT_REJECT': 1, 'ACCEPTED': 1} | 0.20363 | 0.20801 |
| LC | 218 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | {} | — | — |
| LC | 219 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 0.77778 | 0.66667 | {'REJECTED': 1} | 0.18491 | 0.18491 |
| LC | 220 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | {} | — | — |
| SLW | 217 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | {} | — | — |
| SLW | 218 | {'R2': 3} | 0 | 0 | — | — | 0 | 0 | 0 | 5.4444 | 3.1111 | {'REJECTED': 4, 'ACCEPTED': 3} | 0.15891 | 0.17471 |
| SLW | 219 | {} | 0 | 0 | — | — | 0 | 0 | 0 | 2.3333 | 1.6667 | {'REJECTED': 3} | 0.22531 | 0.29824 |
| SLW | 220 | {'R2': 5} | 2 | 1 | 0.25 | 0.2625 | 0 | 0 | 0 | 8.5556 | 7 | {'REJECTED': 4, 'ACCEPTED': 5, 'EXEC_CERT_REJECT': 1, 'SUPERSEDED': 1} | 0.16586 | 0.20915 |
