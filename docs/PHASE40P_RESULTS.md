# Phase40-P

{'complete': True, 'n': 20, 'goals': 11, 'collisions': 0, 'ours_only': 3, 'pilot_label': 'PILOT_NOT_OK', 'graph_label': 'NO_GRAPH_GAIN'}

Phase38 비교군은 같은 scene×seed의 과거 주행 재사용이며 실행일이 다르다. 누락·기술 실패 짝은 제외하고, 전체20짝이 갖춰져야 판정한다. McNemar는 기술 통계이며 판정에 사용하지 않는다.

| scene | method | n | goal | collision | arrival_median_s |
|---|---|---|---|---|---|
| SLW | OURS-N | 4 | 2 | 0 | 60.181 |
| SLW | OURS-DETOUR | 4 | 2 | 0 | 54.778 |
| SLW | OURS | 4 | 1 | 0 | 43.375 |
| SLW | ASTAR+EC | 4 | 2 | 0 | 70.806 |
| LC | OURS-N | 4 | 4 | 0 | 31.34 |
| LC | OURS-DETOUR | 4 | 4 | 0 | 29.507 |
| LC | OURS | 4 | 4 | 0 | 32.91 |
| LC | ASTAR+EC | 4 | 3 | 0 | 31.514 |
| L2 | OURS-N | 4 | 2 | 0 | 56.153 |
| L2 | OURS-DETOUR | 4 | 2 | 0 | 48.062 |
| L2 | OURS | 4 | 3 | 0 | 49.361 |
| L2 | ASTAR+EC | 4 | 2 | 0 | 60.278 |
| H1 | OURS-N | 4 | 2 | 0 | 34.097 |
| H1 | OURS-DETOUR | 4 | 4 | 0 | 43.201 |
| H1 | OURS | 4 | 2 | 0 | 31.861 |
| H1 | ASTAR+EC | 4 | 2 | 1 | 30.694 |
| H2 | OURS-N | 4 | 1 | 0 | 79.556 |
| H2 | OURS-DETOUR | 4 | 3 | 0 | 48.306 |
| H2 | OURS | 4 | 2 | 0 | 70.556 |
| H2 | ASTAR+EC | 4 | 3 | 0 | 82.111 |
| ALL | OURS-N | 20 | 11 | 0 | 39.097 |
| ALL | OURS-DETOUR | 20 | 15 | 0 | 47.028 |
| ALL | OURS | 20 | 12 | 0 | 38.882 |
| ALL | ASTAR+EC | 20 | 12 | 1 | 47.417 |

| comparator | metric | n | ours_only | other_only | p_exact |
|---|---|---|---|---|---|
| OURS-DETOUR | success | 20 | 3 | 7 | 0.34375 |
| OURS-DETOUR | collision | 20 | 0 | 0 | 1 |
| OURS | success | 20 | 5 | 6 | 1 |
| OURS | collision | 20 | 0 | 0 | 1 |
| ASTAR+EC | success | 20 | 4 | 5 | 1 |
| ASTAR+EC | collision | 20 | 0 | 1 | 1 |

둘 다 도착한 짝, OURS-N−상대:

| comparator | n | arrival_delta_median_s | distance_delta_median_m |
|---|---|---|---|
| OURS-DETOUR | 8 | 0.90278 | 0.06846 |
| OURS | 6 | -1.4236 | 0.081819 |
| ASTAR+EC | 7 | -2.3333 | -0.024283 |

| scene | index | planner_installations | escape_installations | consecutive_escape_installations | escape_time_p50_s | escape_time_p95_s | escape_two_second_cap_installations | escape_two_second_cap_jobs | escape_periodic_rejections | waiting_seconds | stopped_while_waiting_seconds | result_dispositions | compute_p50_s | compute_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 217 | {'R3': 5} | 0 | 0 | — | — | 0 | 0 | 0 | 4.6667 | 0.33333 | {'ACCEPTED': 5, 'REJECTED': 1} | 0.5439 | 0.59319 |
| H1 | 218 | {'R3': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 2.3333 | 0 | {'REJECTED': 2, 'ACCEPTED': 1} | 0.56303 | 0.56612 |
| H1 | 219 | {'R3': 6} | 0 | 0 | — | — | 0 | 0 | 0 | 8.5556 | 1.5556 | {'ACCEPTED': 6, 'REJECTED': 5} | 0.51154 | 0.6535 |
| H1 | 220 | {'R3': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 1.5556 | 0 | {'REJECTED': 1, 'ACCEPTED': 1} | 0.48559 | 0.491 |
| H2 | 217 | {'R3': 4, 'R2': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 7.7778 | 1 | {'ACCEPTED': 5, 'REJECTED': 4, 'TIMEOUT': 1} | 0.45348 | 0.64114 |
| H2 | 218 | {'R2': 4, 'R3': 4} | 0 | 0 | — | — | 0 | 0 | 0 | 9.3333 | 2.4444 | {'ACCEPTED': 8, 'REJECTED': 3, 'TIMEOUT': 1} | 0.59975 | 0.71502 |
| H2 | 219 | {'R3': 4} | 0 | 0 | — | — | 0 | 0 | 0 | 7 | 0.77778 | {'ACCEPTED': 4, 'RECOVERY_ACTIVE': 1, 'REJECTED': 4} | 0.52942 | 0.64642 |
| H2 | 220 | {'R3': 3} | 0 | 0 | — | — | 0 | 0 | 0 | 5.4444 | 1.1111 | {'ACCEPTED': 3, 'EXEC_CERT_REJECT': 1, 'TIMEOUT': 1, 'REJECTED': 2} | 0.6021 | 0.70742 |
| L2 | 217 | {'R3': 3} | 0 | 0 | — | — | 0 | 0 | 0 | 2.3333 | 0 | {'ACCEPTED': 3} | 0.55263 | 0.57556 |
| L2 | 218 | {'R3': 5} | 0 | 0 | — | — | 0 | 0 | 0 | 6.2222 | 0.66667 | {'ACCEPTED': 5, 'REJECTED': 3} | 0.47834 | 0.61929 |
| L2 | 219 | {'R3': 3} | 0 | 0 | — | — | 0 | 0 | 0 | 7.3889 | 0.22222 | {'EXEC_CERT_REJECT': 1, 'ACCEPTED': 3, 'REJECTED': 5} | 0.42136 | 0.62599 |
| L2 | 220 | {'R3': 5} | 0 | 0 | — | — | 0 | 0 | 0 | 7.7778 | 0.66667 | {'ACCEPTED': 5, 'TIMEOUT': 1, 'REJECTED': 4} | 0.46757 | 0.6821 |
| LC | 217 | {'R3': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 0.77778 | 0 | {'ACCEPTED': 1} | 0.38762 | 0.38762 |
| LC | 218 | {'R3': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 0.77778 | 0 | {'ACCEPTED': 1} | 0.43566 | 0.43566 |
| LC | 219 | {'R3': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 0.77778 | 0 | {'ACCEPTED': 1} | 0.62681 | 0.62681 |
| LC | 220 | {'R3': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 0.77778 | 0 | {'ACCEPTED': 1} | 0.37056 | 0.37056 |
| SLW | 217 | {'R2': 1, 'R3': 1} | 0 | 0 | — | — | 0 | 0 | 0 | 17.889 | 11.222 | {'ACCEPTED': 2, 'EXEC_CERT_REJECT': 6, 'REJECTED': 7, 'TIMEOUT': 8} | 0.61062 | 0.79813 |
| SLW | 218 | {'R3': 3} | 0 | 0 | — | — | 0 | 0 | 0 | 5.5694 | 1.2222 | {'REJECTED': 4, 'ACCEPTED': 3} | 0.50535 | 0.58937 |
| SLW | 219 | {'R3': 5} | 0 | 0 | — | — | 0 | 0 | 0 | 13.222 | 2.4444 | {'RECOVERY_ACTIVE': 2, 'REJECTED': 9, 'ACCEPTED': 5, 'TIMEOUT': 1} | 0.58254 | 0.67106 |
| SLW | 220 | {'R2': 2, 'R3': 3} | 0 | 0 | — | — | 0 | 0 | 0 | 7.7778 | 1.3333 | {'ACCEPTED': 5, 'REJECTED': 5} | 0.53276 | 0.68191 |

탈출 t_esc 분포는 escape_times.csv에 설치 단위로 저장한다. 2초 상한은 설치 건수와 고유 job 수를 함께 보고하며, 같은 job의 재설치로 절대시각을 연장하지 않는다. 대기 중 정지는 EC 대안 없음·회복 등 실제 정지이며 계산 자체의 강제 정지 명령은 없다.
