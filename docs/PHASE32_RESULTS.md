# Phase32 EC 실행 비교

**EC_HELPS**. Protocol SHA256 `3b0e631cde0bc69d82b81815aad39b847f931f03c748a5e5e28d284dde2b3378`.

| label | evidence_valid | checks | ec_goal | ec_collision | baseline_goal | baseline_collision | reason | historical_execution_days_differ |
|---|---|---|---|---|---|---|---|---|
| EC_HELPS | True | {'collision_strictly_less': True, 'goal_at_least_baseline_minus_one': True} | 19 | 1 | 20 | 4 | registered predicates | True |

## 사용자 승인 사전등록 이탈

2026-11-07: Phase32-O OFFLINE_FAIL(전체 위치오차 p95 0.030037125m >0.03m)을 그대로 보존한다. 동일 C0-NA 구간 오차0m라는 근거로 사용자 승인에 따라 온라인 비교를 준비/실행했다. 오프라인 판정을 PASS로 바꾸지 않았다.

## 방법×장면

| group | method | scene | n | valid | goal | collision | goal_time_median_s | stop_fraction_median | ec_checks | ec_rejects | ec_reject_rate | ec_reject_stopped_s | slow_held_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase32 EC | C0-NA+EC | H1 | 5 | 5 | 5 | 0 | 28.361 | 0.14496 | 405 | 17 | 0.041975 | 3.8889 | 5 |
| Phase32 EC | C0-NA+EC | H2 | 5 | 5 | 2 | 0 | 54.785 | 0.22716 | 972 | 62 | 0.063786 | 20.222 | 1 |
| Phase32 EC | C0-NA+EC | L2 | 5 | 5 | 4 | 0 | 49.472 | 0.13457 | 791 | 13 | 0.016435 | 4 | 0 |
| Phase32 EC | C0-NA+EC | ALL | 15 | 15 | 11 | 0 | 45.889 | 0.14496 | 2168 | 92 | 0.042435 | 28.111 | 6 |
| Phase32 EC | G18+EC | H1 | 5 | 5 | 3 | 1 | 31 | 0.12203 | 649 | 22 | 0.033898 | 0 | 0 |
| Phase32 EC | G18+EC | H2 | 5 | 5 | 1 | 0 | 64.556 | 0.13457 | 1224 | 83 | 0.06781 | 10.222 | 9.2222 |
| Phase32 EC | G18+EC | L2 | 5 | 5 | 4 | 0 | 46.917 | 0.10596 | 820 | 21 | 0.02561 | 0 | 0.22222 |
| Phase32 EC | G18+EC | ALL | 15 | 15 | 8 | 1 | 43.903 | 0.11387 | 2693 | 126 | 0.046788 | 10.222 | 9.4444 |
| historical different-day | C0-NA | H1 | 5 | 5 | 5 | 0 | 31.486 | 0.15217 | 0 | 0 | — | 0 | 0 |
| historical different-day | C0-NA | H2 | 5 | 5 | 2 | 2 | 50.861 | 0.15062 | 0 | 0 | — | 0 | 0 |
| historical different-day | C0-NA | L2 | 5 | 5 | 3 | 0 | 48.986 | 0.15558 | 0 | 0 | — | 0 | 0 |
| historical different-day | C0-NA | ALL | 15 | 15 | 10 | 2 | 39.056 | 0.15217 | 0 | 0 | — | 0 | 0 |
| historical different-day | G18 | H1 | 5 | 5 | 4 | 1 | 34.944 | 0.13083 | 0 | 0 | — | 0 | 0 |
| historical different-day | G18 | H2 | 5 | 5 | 3 | 1 | 58.597 | 0.14241 | 0 | 0 | — | 0 | 0 |
| historical different-day | G18 | L2 | 5 | 5 | 3 | 0 | 48.236 | 0.1358 | 0 | 0 | — | 0 | 0 |
| historical different-day | G18 | ALL | 15 | 15 | 10 | 2 | 48.042 | 0.1358 | 0 | 0 | — | 0 | 0 |

| scene | index | method | ec_goal | baseline_goal | ec_collision | baseline_collision | goal_time_delta_s | baseline_output |
|---|---|---|---|---|---|---|---|---|
| H1 | 201 | C0-NA+EC | True | True | False | False | -2.3056 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase28_pilot_01/main/H1_201_C0-NA/attempt1 |
| H1 | 201 | G18+EC | True | False | False | True | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/dev/H1_201_G18/attempt1 |
| H1 | 202 | C0-NA+EC | True | True | False | False | -5.0972 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase28_pilot_01/main/H1_202_C0-NA/attempt1 |
| H1 | 202 | G18+EC | False | True | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/dev/H1_202_G18/attempt1 |
| H1 | 203 | C0-NA+EC | True | True | False | False | 6.1944 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H1_203_C0-NA/attempt1 |
| H1 | 203 | G18+EC | True | True | False | False | -8.6806 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H1_203_G18/attempt1 |
| H1 | 204 | C0-NA+EC | True | True | False | False | -4.9722 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H1_204_C0-NA/attempt1 |
| H1 | 204 | G18+EC | True | True | False | False | -1.3194 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H1_204_G18/attempt1 |
| H1 | 205 | C0-NA+EC | True | True | False | False | 1.7083 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H1_205_C0-NA/attempt1 |
| H1 | 205 | G18+EC | False | True | True | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H1_205_G18/attempt1 |
| H2 | 201 | C0-NA+EC | False | False | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase28_pilot_01/main/H2_201_C0-NA/attempt1 |
| H2 | 201 | G18+EC | False | True | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/dev/H2_201_G18/attempt1 |
| H2 | 202 | C0-NA+EC | False | False | False | True | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase28_pilot_01/main/H2_202_C0-NA/attempt1 |
| H2 | 202 | G18+EC | True | True | False | False | -1.7639 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/dev/H2_202_G18/attempt1 |
| H2 | 203 | C0-NA+EC | True | False | False | True | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H2_203_C0-NA/attempt1 |
| H2 | 203 | G18+EC | False | False | False | True | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H2_203_G18/attempt1 |
| H2 | 204 | C0-NA+EC | True | True | False | False | -5.5972 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H2_204_C0-NA/attempt1 |
| H2 | 204 | G18+EC | False | False | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H2_204_G18/attempt1 |
| H2 | 205 | C0-NA+EC | False | True | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H2_205_C0-NA/attempt1 |
| H2 | 205 | G18+EC | False | True | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/H2_205_G18/attempt1 |
| L2 | 201 | C0-NA+EC | True | True | False | False | -3.3889 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase28_pilot_01/main/L2_201_C0-NA/attempt1 |
| L2 | 201 | G18+EC | True | False | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/dev/L2_201_G18/attempt1 |
| L2 | 202 | C0-NA+EC | True | True | False | False | 1.6806 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase28_pilot_01/main/L2_202_C0-NA/attempt1 |
| L2 | 202 | G18+EC | True | False | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/dev/L2_202_G18/attempt1 |
| L2 | 203 | C0-NA+EC | True | True | False | False | -0.58333 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/L2_203_C0-NA/attempt1 |
| L2 | 203 | G18+EC | True | True | False | False | -4.0833 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/L2_203_G18/attempt1 |
| L2 | 204 | C0-NA+EC | False | False | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/L2_204_C0-NA/attempt1 |
| L2 | 204 | G18+EC | False | True | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/L2_204_G18/attempt1 |
| L2 | 205 | C0-NA+EC | True | False | False | False | — | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/L2_205_C0-NA/attempt1 |
| L2 | 205 | G18+EC | True | True | False | False | 5.4306 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase29_01/confirm/L2_205_G18/attempt1 |

기존 C0-NA/G18은 같은 scene×seed지만 다른 날 실행된 역사적 비교다. C0-NA201/202는Phase28,203~205는Phase29 confirm; G18은Phase29 dev/confirm이다. Phase31-P는206/207이라 이번 비교 키에 없다.

## EC 메커니즘

| method | scene | index | ec_checks | ec_rejects | ec_by_state | ec_compute_p50_s | ec_compute_p95_s | ec_fallback_routes | ec_all_routes | ec_slow_installs | ec_slow_activations | ec_slow_ranks | ec_slow_held_s | ec_reject_stopped_s | ec_reject_stop_wait_s | ec_periodic_delays_ticks | ec_periodic_delays_wall_ms | ec_periodic_max_delay_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C0-NA+EC | H1 | 201 | 71 | 1 | {'NORMAL': {'checks': 65, 'rejects': 1}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 6, 'rejects': 0}} | 0.0050737 | 0.009812 | {'NEXT_SAFE_FULL': 1} | {'PRIMARY_FULL': 24, 'NEXT_SAFE_FULL': 1, 'SOLVER_EC_PASS': 1, 'R3_EC_PASS': 1} | 0 | 0 | [] | 0 | 0 | 0 | [4] | [61.34968] | 55.556 |
| G18+EC | H1 | 201 | 83 | 1 | {'NORMAL': {'checks': 83, 'rejects': 1}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 0, 'rejects': 0}} | 0.0046012 | 0.014424 | {'NEXT_SAFE_FULL': 1} | {'PRIMARY_FULL': 53, 'NEXT_SAFE_FULL': 1} | 0 | 0 | [] | 0 | 0 | 0 | [4] | [61.770748] | 55.556 |
| C0-NA+EC | H1 | 202 | 75 | 2 | {'NORMAL': {'checks': 75, 'rejects': 2}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 0, 'rejects': 0}} | 0.0043923 | 0.0085768 | {'NEXT_SAFE_FULL': 2} | {'PRIMARY_FULL': 25, 'NEXT_SAFE_FULL': 2} | 0 | 0 | [] | 0 | 0 | 0 | [4] | [62.990156] | 55.556 |
| G18+EC | H1 | 202 | 252 | 5 | {'NORMAL': {'checks': 229, 'rejects': 4}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 23, 'rejects': 1}} | 0.0073151 | 0.015776 | {'NEXT_SAFE_FULL': 1, 'R3_FAILURE': 1} | {'PRIMARY_FULL': 135, 'SOLVER_EC_PASS': 3, 'R3_EC_PASS': 3, 'NEXT_SAFE_FULL': 1} | 0 | 0 | [] | 0 | 0 | 0 | [0] | [6.540879] | 0 |
| C0-NA+EC | H1 | 203 | 104 | 14 | {'NORMAL': {'checks': 102, 'rejects': 13}, 'R2': {'checks': 1, 'rejects': 1}, 'R3': {'checks': 1, 'rejects': 0}} | 0.004828 | 0.0087366 | {'NEXT_SAFE_FULL': 3, 'SAFE_SLOW': 1, 'R2_TO_R3': 1} | {'PRIMARY_FULL': 30, 'SOLVER_EC_PASS': 1, 'NEXT_SAFE_FULL': 3, 'SAFE_SLOW': 1, 'R2_TO_R3': 1} | 1 | 1 | [1] | 5 | 3.8889 | 0.66667 | [4] | [70.177394] | 55.556 |
| G18+EC | H1 | 203 | 84 | 0 | {'NORMAL': {'checks': 76, 'rejects': 0}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 8, 'rejects': 0}} | 0.0056982 | 0.0098376 | {} | {'PRIMARY_FULL': 50, 'SOLVER_EC_PASS': 2, 'R3_EC_PASS': 1} | 0 | 0 | [] | 0 | 0 | 0 | [] | [] | — |
| C0-NA+EC | H1 | 204 | 68 | 0 | {'NORMAL': {'checks': 68, 'rejects': 0}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 0, 'rejects': 0}} | 0.0041867 | 0.011759 | {} | {'PRIMARY_FULL': 24} | 0 | 0 | [] | 0 | 0 | 0 | [] | [] | — |
| G18+EC | H1 | 204 | 91 | 3 | {'NORMAL': {'checks': 91, 'rejects': 3}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 0, 'rejects': 0}} | 0.0045649 | 0.012168 | {'NEXT_SAFE_FULL': 2} | {'PRIMARY_FULL': 57, 'NEXT_SAFE_FULL': 2} | 0 | 0 | [] | 0 | 0 | 0 | [4, 4] | [76.963744, 78.734406] | 55.556 |
| C0-NA+EC | H1 | 205 | 87 | 0 | {'NORMAL': {'checks': 75, 'rejects': 0}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 12, 'rejects': 0}} | 0.0047216 | 0.0095228 | {} | {'PRIMARY_FULL': 27, 'SOLVER_EC_PASS': 2, 'R3_EC_PASS': 2} | 0 | 0 | [] | 0 | 0 | 0 | [] | [] | — |
| G18+EC | H1 | 205 | 139 | 13 | {'NORMAL': {'checks': 133, 'rejects': 13}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 6, 'rejects': 0}} | 0.0050754 | 0.010475 | {'NEXT_SAFE_FULL': 6, 'STOP_WAIT': 1} | {'PRIMARY_FULL': 66, 'SOLVER_EC_PASS': 1, 'R3_EC_PASS': 1, 'NEXT_SAFE_FULL': 6, 'STOP_WAIT': 1} | 0 | 0 | [] | 0 | 0 | 0 | [4, 4] | [68.939556, 69.778001] | 55.556 |
| C0-NA+EC | H2 | 201 | 234 | 12 | {'NORMAL': {'checks': 214, 'rejects': 12}, 'R2': {'checks': 2, 'rejects': 0}, 'R3': {'checks': 18, 'rejects': 0}} | 0.0073065 | 0.014818 | {'NEXT_SAFE_FULL': 8} | {'PRIMARY_FULL': 73, 'NEXT_SAFE_FULL': 8, 'SOLVER_EC_PASS': 4, 'R3_EC_PASS': 3, 'R2_EC_PASS': 1} | 0 | 0 | [] | 0 | 0 | 0 | [4, 4, 4, 4, 0] | [58.593846, 62.464085, 16.34625, 72.54358, 16.878132] | 55.556 |
| G18+EC | H2 | 201 | 258 | 15 | {'NORMAL': {'checks': 248, 'rejects': 15}, 'R2': {'checks': 4, 'rejects': 0}, 'R3': {'checks': 6, 'rejects': 0}} | 0.0076712 | 0.015886 | {'NEXT_SAFE_FULL': 4, 'SAFE_SLOW': 1} | {'PRIMARY_FULL': 145, 'NEXT_SAFE_FULL': 4, 'SAFE_SLOW': 1, 'SOLVER_EC_PASS': 3, 'R2_EC_PASS': 2, 'R3_EC_PASS': 1} | 1 | 1 | [1] | 0.33333 | 0 | 0 | [4, 0] | [145.969878, 12.884204] | 55.556 |
| C0-NA+EC | H2 | 202 | 210 | 24 | {'NORMAL': {'checks': 160, 'rejects': 18}, 'R2': {'checks': 12, 'rejects': 6}, 'R3': {'checks': 38, 'rejects': 0}} | 0.0067825 | 0.013841 | {'SAFE_SLOW': 2, 'STOP_WAIT': 1, 'R2_TO_R3': 6} | {'PRIMARY_FULL': 54, 'SAFE_SLOW': 2, 'SOLVER_EC_PASS': 8, 'R3_EC_PASS': 5, 'R2_EC_PASS': 3, 'STOP_WAIT': 1, 'R2_TO_R3': 6} | 2 | 1 | [1, 1] | 1 | 15.444 | 2 | [0, 0] | [55.425473, 14.914661] | 0 |
| G18+EC | H2 | 202 | 177 | 2 | {'NORMAL': {'checks': 157, 'rejects': 0}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 20, 'rejects': 2}} | 0.0060816 | 0.01416 | {'R3_FAILURE': 2} | {'PRIMARY_FULL': 100, 'R3_FAILURE': 2, 'SOLVER_EC_PASS': 3, 'R3_EC_PASS': 3} | 0 | 0 | [] | 0 | 1 | 1 | [] | [] | — |
| C0-NA+EC | H2 | 203 | 156 | 7 | {'NORMAL': {'checks': 130, 'rejects': 7}, 'R2': {'checks': 4, 'rejects': 0}, 'R3': {'checks': 22, 'rejects': 0}} | 0.0058177 | 0.013087 | {'NEXT_SAFE_FULL': 2} | {'PRIMARY_FULL': 45, 'NEXT_SAFE_FULL': 2, 'SOLVER_EC_PASS': 5, 'R2_EC_PASS': 2, 'R3_EC_PASS': 2} | 0 | 0 | [] | 0 | 0 | 0 | [4] | [88.931007] | 55.556 |
| G18+EC | H2 | 203 | 264 | 11 | {'NORMAL': {'checks': 214, 'rejects': 11}, 'R2': {'checks': 7, 'rejects': 0}, 'R3': {'checks': 43, 'rejects': 0}} | 0.0073986 | 0.013126 | {'NEXT_SAFE_FULL': 1, 'SAFE_SLOW': 1} | {'PRIMARY_FULL': 120, 'SOLVER_EC_PASS': 9, 'R2_EC_PASS': 3, 'NEXT_SAFE_FULL': 1, 'R3_EC_PASS': 5, 'SAFE_SLOW': 1, 'PRIMARY_RETAINED_SLOW': 1} | 2 | 1 | [1, 1] | 1.2222 | 0 | 0 | [] | [] | — |
| C0-NA+EC | H2 | 204 | 139 | 6 | {'NORMAL': {'checks': 133, 'rejects': 6}, 'R2': {'checks': 6, 'rejects': 0}, 'R3': {'checks': 0, 'rejects': 0}} | 0.0058663 | 0.012708 | {'NEXT_SAFE_FULL': 3} | {'PRIMARY_FULL': 42, 'NEXT_SAFE_FULL': 3, 'SOLVER_EC_PASS': 3, 'R2_EC_PASS': 3} | 0 | 0 | [] | 0 | 0 | 0 | [0] | [17.318282] | 0 |
| G18+EC | H2 | 204 | 236 | 18 | {'NORMAL': {'checks': 171, 'rejects': 14}, 'R2': {'checks': 8, 'rejects': 4}, 'R3': {'checks': 57, 'rejects': 0}} | 0.0071696 | 0.013075 | {'NEXT_SAFE_FULL': 4, 'SAFE_SLOW': 1, 'R2_TO_R3': 4} | {'PRIMARY_FULL': 96, 'NEXT_SAFE_FULL': 4, 'SOLVER_EC_PASS': 9, 'R3_EC_PASS': 7, 'SAFE_SLOW': 1, 'PRIMARY_RETAINED_SLOW': 1, 'R2_EC_PASS': 2, 'R2_TO_R3': 4} | 4 | 1 | [1, 1] | 7.6667 | 7.2222 | 1.1111 | [4, 4, 0] | [116.011433, 62.842716, 46.957099] | 55.556 |
| C0-NA+EC | H2 | 205 | 233 | 13 | {'NORMAL': {'checks': 196, 'rejects': 11}, 'R2': {'checks': 4, 'rejects': 2}, 'R3': {'checks': 33, 'rejects': 0}} | 0.0072794 | 0.013202 | {'NEXT_SAFE_FULL': 6, 'R2_TO_R3': 2} | {'PRIMARY_FULL': 67, 'NEXT_SAFE_FULL': 6, 'R2_TO_R3': 2, 'SOLVER_EC_PASS': 7, 'R2_EC_PASS': 1, 'R3_EC_PASS': 4} | 0 | 0 | [] | 0 | 4.7778 | 0.88889 | [4, 4] | [73.333532, 63.306491] | 55.556 |
| G18+EC | H2 | 205 | 289 | 37 | {'NORMAL': {'checks': 267, 'rejects': 37}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 22, 'rejects': 0}} | 0.0059296 | 0.015573 | {'NEXT_SAFE_FULL': 3, 'STOP_WAIT': 2} | {'PRIMARY_FULL': 140, 'NEXT_SAFE_FULL': 3, 'STOP_WAIT': 2, 'SOLVER_EC_PASS': 3, 'R3_EC_PASS': 3} | 0 | 0 | [] | 0 | 2 | 0.11111 | [0] | [69.453293] | 0 |
| C0-NA+EC | L2 | 201 | 131 | 1 | {'NORMAL': {'checks': 117, 'rejects': 1}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 14, 'rejects': 0}} | 0.0075703 | 0.014939 | {'NEXT_SAFE_FULL': 1} | {'PRIMARY_FULL': 41, 'NEXT_SAFE_FULL': 1, 'SOLVER_EC_PASS': 2, 'R3_EC_PASS': 2} | 0 | 0 | [] | 0 | 0 | 0 | [0] | [12.106405] | 0 |
| G18+EC | L2 | 201 | 125 | 0 | {'NORMAL': {'checks': 110, 'rejects': 0}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 15, 'rejects': 0}} | 0.0079788 | 0.016587 | {} | {'PRIMARY_FULL': 69, 'SOLVER_EC_PASS': 2, 'R3_EC_PASS': 2} | 0 | 0 | [] | 0 | 0 | 0 | [] | [] | — |
| C0-NA+EC | L2 | 202 | 150 | 0 | {'NORMAL': {'checks': 128, 'rejects': 0}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 22, 'rejects': 0}} | 0.0078705 | 0.013415 | {} | {'PRIMARY_FULL': 45, 'SOLVER_EC_PASS': 3, 'R3_EC_PASS': 2} | 0 | 0 | [] | 0 | 0 | 0 | [] | [] | — |
| G18+EC | L2 | 202 | 138 | 1 | {'NORMAL': {'checks': 132, 'rejects': 1}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 6, 'rejects': 0}} | 0.0063192 | 0.014086 | {'NEXT_SAFE_FULL': 1} | {'PRIMARY_FULL': 80, 'NEXT_SAFE_FULL': 1, 'SOLVER_EC_PASS': 1, 'R3_EC_PASS': 1} | 0 | 0 | [] | 0 | 0 | 0 | [] | [] | — |
| C0-NA+EC | L2 | 203 | 130 | 0 | {'NORMAL': {'checks': 108, 'rejects': 0}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 22, 'rejects': 0}} | 0.0071328 | 0.0154 | {} | {'PRIMARY_FULL': 40, 'SOLVER_EC_PASS': 3, 'R3_EC_PASS': 3} | 0 | 0 | [] | 0 | 0 | 0 | [] | [] | — |
| G18+EC | L2 | 203 | 128 | 0 | {'NORMAL': {'checks': 113, 'rejects': 0}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 15, 'rejects': 0}} | 0.0075393 | 0.013376 | {} | {'PRIMARY_FULL': 73, 'SOLVER_EC_PASS': 2, 'R3_EC_PASS': 2} | 0 | 0 | [] | 0 | 0 | 0 | [] | [] | — |
| C0-NA+EC | L2 | 204 | 243 | 4 | {'NORMAL': {'checks': 208, 'rejects': 4}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 35, 'rejects': 0}} | 0.0084551 | 0.016055 | {'NEXT_SAFE_FULL': 4} | {'PRIMARY_FULL': 73, 'NEXT_SAFE_FULL': 4, 'SOLVER_EC_PASS': 4, 'R3_EC_PASS': 4} | 0 | 0 | [] | 0 | 0 | 0 | [4, 0] | [61.372344, 22.764153] | 55.556 |
| G18+EC | L2 | 204 | 273 | 20 | {'NORMAL': {'checks': 221, 'rejects': 20}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 52, 'rejects': 0}} | 0.0068268 | 0.014863 | {'SAFE_SLOW': 1, 'NEXT_SAFE_FULL': 3} | {'PRIMARY_FULL': 123, 'SAFE_SLOW': 1, 'SOLVER_EC_PASS': 7, 'R3_EC_PASS': 7, 'NEXT_SAFE_FULL': 3} | 1 | 1 | [1] | 0.22222 | 0 | 0 | [4, 4] | [109.085868, 120.306299] | 55.556 |
| C0-NA+EC | L2 | 205 | 137 | 8 | {'NORMAL': {'checks': 99, 'rejects': 0}, 'R2': {'checks': 5, 'rejects': 2}, 'R3': {'checks': 33, 'rejects': 6}} | 0.0079689 | 0.015741 | {'R2_TO_R3': 2, 'R3_FAILURE': 2} | {'PRIMARY_FULL': 35, 'SOLVER_EC_PASS': 6, 'R3_EC_PASS': 4, 'R2_EC_PASS': 2, 'R2_TO_R3': 2, 'R3_FAILURE': 2} | 0 | 0 | [] | 0 | 4 | 0.55556 | [] | [] | — |
| G18+EC | L2 | 205 | 156 | 0 | {'NORMAL': {'checks': 128, 'rejects': 0}, 'R2': {'checks': 0, 'rejects': 0}, 'R3': {'checks': 28, 'rejects': 0}} | 0.0074748 | 0.014094 | {} | {'PRIMARY_FULL': 80, 'SOLVER_EC_PASS': 5, 'R3_EC_PASS': 4} | 0 | 0 | [] | 0 | 0 | 0 | [] | [] | — |

| method | n | p50_s | p95_s |
|---|---|---|---|
| C0-NA+EC | 2168 | 0.0066288 | 0.013898 |
| G18+EC | 2693 | 0.006707 | 0.014683 |

CHECK는 candidate별 검사 호출 수(따라서 R3 한 job에 여러 검사)다. INSTALL/주기 검사와 상태를 로그에 분리했다. 감속 유지시간은cap latch 활성 시간(정지 포함), REJECT 정지시간은rejection latch 후 실제|v|<0.01인시간이며 STOP_WAIT/회복/계산대기를 로그로 분리할 수 있다. 주기검사는36tick, 적용은 다음9Hz tick이며0/4tick(최대55.56ms) simulation-clock 지연과 별도의 실제 wall-clock 지연을 모두 남긴다.
