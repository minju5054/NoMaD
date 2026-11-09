| status | completed | planned | paired_valid | protocol_sha256 |
|---|---|---|---|---|
| COMPLETE | 15 | 15 | 15 | 47c83820cb37b7fac9761ae9861af0bf4a9e3f61945d810ab7d2ea947f9de2a2 |

| item | definition |
|---|---|
| 주 성공 | Declared arrival distance<=0.5m AND no collision; Phase41/43 unchanged |
| 비교 | Same15 scene/seed/jitter blocks versus stored Phase43-P OURS-DETOUR+HMM; different execution day |
| Graph | Phase38 OURS frozen R2/R3/strict map/certificate/EC; no VN,escape or nonblocking changes |
| HANDOVER_10S | Primary:10s after END of an actually applied R3,clipped to run termination; failed/unapplied attempts excluded |
| INSTALL_10S | Supplement:10s after R3 APPLIED,includes detour execution; clipped to run termination |
| 노드 오차 | Input observation time; absolute HMM closest minus nearest Topomap XY node; overlapping windows deduplicated per run/scope |
| 무자료 | No completed detour or no inference in window => n0/NA,never zero error; no new binary gate registered |

| cohort | scene | completed | valid | success_0p5 | wrong_stop | collision | r2_installations | r3_installations |
|---|---|---|---|---|---|---|---|---|
| Phase43-P | SLW | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| Phase45-P | SLW | 3 | 3 | 0 | 0 | 0 | 3 | 4 |
| Phase43-P | LC | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| Phase45-P | LC | 3 | 3 | 3 | 0 | 0 | 0 | 3 |
| Phase43-P | L2 | 3 | 3 | 0 | 2 | 0 | 0 | 0 |
| Phase45-P | L2 | 3 | 3 | 2 | 1 | 0 | 1 | 8 |
| Phase43-P | H1 | 3 | 3 | 2 | 1 | 0 | 0 | 0 |
| Phase45-P | H1 | 3 | 3 | 2 | 0 | 0 | 0 | 4 |
| Phase43-P | H2 | 3 | 3 | 1 | 1 | 0 | 0 | 0 |
| Phase45-P | H2 | 3 | 3 | 0 | 2 | 0 | 2 | 2 |
| Phase43-P | ALL | 15 | 15 | 9 | 4 | 0 | 0 | 0 |
| Phase45-P | ALL | 15 | 15 | 7 | 3 | 0 | 6 | 21 |

| n | success_delta | wrong_stop_delta | collision_delta |
|---|---|---|---|
| 15 | -2 | -1 | 0 |

| scene | seed | paired_valid | phase43_success | phase45_success | success_delta | wrong_stop_delta | collision_delta |
|---|---|---|---|---|---|---|---|
| H1 | 217 | True | True | True | 0 | 0 | 0 |
| H1 | 219 | True | False | False | 0 | -1 | 0 |
| H1 | 220 | True | True | True | 0 | 0 | 0 |
| H2 | 217 | True | False | False | 0 | 0 | 0 |
| H2 | 219 | True | True | False | -1 | 0 | 0 |
| H2 | 220 | True | False | False | 0 | 1 | 0 |
| L2 | 217 | True | False | True | 1 | 0 | 0 |
| L2 | 219 | True | False | True | 1 | -1 | 0 |
| L2 | 220 | True | False | False | 0 | 0 | 0 |
| LC | 217 | True | True | True | 0 | 0 | 0 |
| LC | 219 | True | True | True | 0 | 0 | 0 |
| LC | 220 | True | True | True | 0 | 0 | 0 |
| SLW | 217 | True | True | False | -1 | 0 | 0 |
| SLW | 219 | True | True | False | -1 | 0 | 0 |
| SLW | 220 | True | True | False | -1 | 0 | 0 |

| cohort | scene | seed | scope | n | mae | p50 | p95 |
|---|---|---|---|---|---|---|---|
| Phase43-P | H1 | 217 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | H1 | 217 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | H1 | 219 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | H1 | 219 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | H1 | 220 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | H1 | 220 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | H2 | 217 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | H2 | 217 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | H2 | 219 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | H2 | 219 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | H2 | 220 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | H2 | 220 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | L2 | 217 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | L2 | 217 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | L2 | 219 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | L2 | 219 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | L2 | 220 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | L2 | 220 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | LC | 217 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | LC | 217 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | LC | 219 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | LC | 219 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | LC | 220 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | LC | 220 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | SLW | 217 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | SLW | 217 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | SLW | 219 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | SLW | 219 | INSTALL_10S | 0 | — | — | — |
| Phase43-P | SLW | 220 | HANDOVER_10S | 0 | — | — | — |
| Phase43-P | SLW | 220 | INSTALL_10S | 0 | — | — | — |
| Phase45-P | H1 | 217 | HANDOVER_10S | 4 | 0 | 0 | 0 |
| Phase45-P | H1 | 217 | INSTALL_10S | 6 | 0.16667 | 0 | 0.75 |
| Phase45-P | H1 | 219 | HANDOVER_10S | 20 | 8.55 | 7.5 | 12 |
| Phase45-P | H1 | 219 | INSTALL_10S | 20 | 8 | 7.5 | 12 |
| Phase45-P | H1 | 220 | HANDOVER_10S | 2 | 0 | 0 | 0 |
| Phase45-P | H1 | 220 | INSTALL_10S | 5 | 0 | 0 | 0 |
| Phase45-P | H2 | 217 | HANDOVER_10S | 10 | 1.5 | 1.5 | 3 |
| Phase45-P | H2 | 217 | INSTALL_10S | 10 | 1.8 | 2 | 3 |
| Phase45-P | H2 | 219 | HANDOVER_10S | 4 | 2 | 2 | 2.85 |
| Phase45-P | H2 | 219 | INSTALL_10S | 6 | 2.1667 | 2 | 3 |
| Phase45-P | H2 | 220 | HANDOVER_10S | 0 | — | — | — |
| Phase45-P | H2 | 220 | INSTALL_10S | 0 | — | — | — |
| Phase45-P | L2 | 217 | HANDOVER_10S | 22 | 0.81818 | 0.5 | 2 |
| Phase45-P | L2 | 217 | INSTALL_10S | 25 | 1.04 | 1 | 4.4 |
| Phase45-P | L2 | 219 | HANDOVER_10S | 10 | 2.5 | 2 | 6.2 |
| Phase45-P | L2 | 219 | INSTALL_10S | 10 | 3.6 | 3 | 7.1 |
| Phase45-P | L2 | 220 | HANDOVER_10S | 25 | 6.12 | 7 | 9 |
| Phase45-P | L2 | 220 | INSTALL_10S | 25 | 6.16 | 7 | 8.8 |
| Phase45-P | LC | 217 | HANDOVER_10S | 7 | 0.57143 | 1 | 1 |
| Phase45-P | LC | 217 | INSTALL_10S | 8 | 0.5 | 0.5 | 1 |
| Phase45-P | LC | 219 | HANDOVER_10S | 4 | 0.75 | 1 | 1 |
| Phase45-P | LC | 219 | INSTALL_10S | 5 | 0.8 | 1 | 1 |
| Phase45-P | LC | 220 | HANDOVER_10S | 6 | 0.16667 | 0 | 0.75 |
| Phase45-P | LC | 220 | INSTALL_10S | 8 | 0.25 | 0 | 1 |
| Phase45-P | SLW | 217 | HANDOVER_10S | 10 | 0.1 | 0 | 0.55 |
| Phase45-P | SLW | 217 | INSTALL_10S | 10 | 0.1 | 0 | 0.55 |
| Phase45-P | SLW | 219 | HANDOVER_10S | 0 | — | — | — |
| Phase45-P | SLW | 219 | INSTALL_10S | 0 | — | — | — |
| Phase45-P | SLW | 220 | HANDOVER_10S | 25 | 3.8 | 2 | 12 |
| Phase45-P | SLW | 220 | INSTALL_10S | 28 | 4.5 | 2 | 12 |

| cohort | scene | seed | job_id | scope | start_s | end_s | available_s | truncated | reason | n | mae | p50 | p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase45-P | H1 | 217 | 1 | INSTALL_10S | 25.222 | 31.833 | 6.6111 | True | — | 6 | 0.16667 | 0 | 0.75 |
| Phase45-P | H1 | 217 | 1 | HANDOVER_10S | 27.778 | 31.833 | 4.0556 | True | NO_NEW_OBSTACLE_AHEAD | 4 | 0 | 0 | 0 |
| Phase45-P | H1 | 219 | 0 | INSTALL_10S | 30.333 | 40.333 | 10 | False | — | 10 | 6 | 7 | 7 |
| Phase45-P | H1 | 219 | 0 | HANDOVER_10S | 31.556 | 41.556 | 10 | False | PATH_BECAME_UNSAFE | 10 | 6.7 | 7 | 7 |
| Phase45-P | H1 | 219 | 8 | INSTALL_10S | 56.778 | 66.778 | 10 | False | — | 10 | 10 | 9.5 | 12 |
| Phase45-P | H1 | 219 | 8 | HANDOVER_10S | 59 | 69 | 10 | False | PATH_BECAME_UNSAFE | 10 | 10.4 | 10.5 | 12 |
| Phase45-P | H1 | 220 | 1 | INSTALL_10S | 23.889 | 28.833 | 4.9444 | True | — | 5 | 0 | 0 | 0 |
| Phase45-P | H1 | 220 | 1 | HANDOVER_10S | 26.333 | 28.833 | 2.5 | True | PATH_BECAME_UNSAFE | 2 | 0 | 0 | 0 |
| Phase45-P | H2 | 217 | 4 | INSTALL_10S | 68.222 | 78.222 | 10 | False | — | 10 | 1.8 | 2 | 3 |
| Phase45-P | H2 | 217 | 4 | HANDOVER_10S | 70.111 | 80.111 | 10 | False | NO_NEW_OBSTACLE_AHEAD | 10 | 1.5 | 1.5 | 3 |
| Phase45-P | H2 | 219 | 11 | INSTALL_10S | 83.333 | 90 | 6.6667 | True | — | 6 | 2.1667 | 2 | 3 |
| Phase45-P | H2 | 219 | 11 | HANDOVER_10S | 85.556 | 90 | 4.4444 | True | NO_NEW_OBSTACLE_AHEAD | 4 | 2 | 2 | 2.85 |
| Phase45-P | L2 | 217 | 7 | INSTALL_10S | 50 | 60 | 10 | False | — | 10 | 1.8 | 1.5 | 5 |
| Phase45-P | L2 | 217 | 7 | HANDOVER_10S | 52.556 | 62.556 | 10 | False | PATH_BECAME_UNSAFE | 9 | 1.3333 | 1 | 3.8 |
| Phase45-P | L2 | 217 | 8 | INSTALL_10S | 58.111 | 68.111 | 10 | False | — | 10 | 0.4 | 0 | 1.55 |
| Phase45-P | L2 | 217 | 8 | HANDOVER_10S | 59.556 | 69.556 | 10 | False | PATH_BECAME_UNSAFE | 9 | 0.55556 | 0 | 1.6 |
| Phase45-P | L2 | 217 | 9 | INSTALL_10S | 65 | 75 | 10 | False | — | 10 | 0.5 | 0.5 | 1 |
| Phase45-P | L2 | 217 | 9 | HANDOVER_10S | 65 | 75 | 10 | False | NO_NEW_OBSTACLE_AHEAD | 10 | 0.5 | 0.5 | 1 |
| Phase45-P | L2 | 219 | 0 | INSTALL_10S | 15.111 | 25.111 | 10 | False | — | 10 | 3.6 | 3 | 7.1 |
| Phase45-P | L2 | 219 | 0 | HANDOVER_10S | 17.111 | 27.111 | 10 | False | NO_NEW_OBSTACLE_AHEAD | 10 | 2.5 | 2 | 6.2 |
| Phase45-P | L2 | 220 | 1 | INSTALL_10S | 19.556 | 29.556 | 10 | False | — | 10 | 7.8 | 7.5 | 9.55 |
| Phase45-P | L2 | 220 | 1 | HANDOVER_10S | 20 | 30 | 10 | False | PATH_BECAME_UNSAFE | 10 | 7.7 | 7.5 | 9.55 |
| Phase45-P | L2 | 220 | 2 | INSTALL_10S | 23.556 | 33.556 | 10 | False | — | 10 | 7.7 | 8 | 9.55 |
| Phase45-P | L2 | 220 | 2 | HANDOVER_10S | 25.778 | 35.778 | 10 | False | PATH_BECAME_UNSAFE | 10 | 7.6 | 8 | 9.55 |
| Phase45-P | L2 | 220 | 3 | INSTALL_10S | 36.667 | 46.667 | 10 | False | — | 10 | 4.8 | 5.5 | 7 |
| Phase45-P | L2 | 220 | 3 | HANDOVER_10S | 37.222 | 47.222 | 10 | False | NO_NEW_OBSTACLE_AHEAD | 10 | 4.1 | 5 | 7 |
| Phase45-P | L2 | 220 | 4 | INSTALL_10S | 40.667 | 47.833 | 7.1667 | True | — | 7 | 2.8571 | 2 | 5.7 |
| Phase45-P | L2 | 220 | 4 | HANDOVER_10S | 43.333 | 47.833 | 4.5 | True | PATH_BECAME_UNSAFE | 4 | 1 | 1 | 1.85 |
| Phase45-P | LC | 217 | 0 | INSTALL_10S | 23.222 | 31.833 | 8.6111 | True | — | 8 | 0.5 | 0.5 | 1 |
| Phase45-P | LC | 217 | 0 | HANDOVER_10S | 24.778 | 31.833 | 7.0556 | True | PATH_BECAME_UNSAFE | 7 | 0.57143 | 1 | 1 |
| Phase45-P | LC | 219 | 0 | INSTALL_10S | 21.111 | 26.833 | 5.7222 | True | — | 5 | 0.8 | 1 | 1 |
| Phase45-P | LC | 219 | 0 | HANDOVER_10S | 22.556 | 26.833 | 4.2778 | True | PATH_BECAME_UNSAFE | 4 | 0.75 | 1 | 1 |
| Phase45-P | LC | 220 | 0 | INSTALL_10S | 22.556 | 30.639 | 8.0833 | True | — | 8 | 0.25 | 0 | 1 |
| Phase45-P | LC | 220 | 0 | HANDOVER_10S | 24 | 30.639 | 6.6389 | True | PATH_BECAME_UNSAFE | 6 | 0.16667 | 0 | 0.75 |
| Phase45-P | SLW | 217 | 0 | INSTALL_10S | 12.444 | 22.444 | 10 | False | — | 10 | 0.1 | 0 | 0.55 |
| Phase45-P | SLW | 217 | 0 | HANDOVER_10S | 13.556 | 23.556 | 10 | False | PATH_BECAME_UNSAFE | 10 | 0.1 | 0 | 0.55 |
| Phase45-P | SLW | 220 | 3 | INSTALL_10S | 23.333 | 33.333 | 10 | False | — | 10 | 0.7 | 1 | 1 |
| Phase45-P | SLW | 220 | 3 | HANDOVER_10S | 25.778 | 35.778 | 10 | False | PATH_BECAME_UNSAFE | 10 | 0.9 | 1 | 1 |
| Phase45-P | SLW | 220 | 8 | INSTALL_10S | 44.889 | 54.889 | 10 | False | — | 10 | 2.3 | 2.5 | 3 |
| Phase45-P | SLW | 220 | 8 | HANDOVER_10S | 45.778 | 55.778 | 10 | False | PATH_BECAME_UNSAFE | 10 | 2.6 | 3 | 3.55 |
| Phase45-P | SLW | 220 | 16 | INSTALL_10S | 82.333 | 90 | 7.6667 | True | — | 8 | 12 | 12 | 12 |
| Phase45-P | SLW | 220 | 16 | HANDOVER_10S | 85 | 90 | 5 | True | PATH_BECAME_UNSAFE | 5 | 12 | 12 | 12 |
