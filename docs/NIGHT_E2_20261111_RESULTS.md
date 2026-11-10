# Phase54-P 밤샘 파일럿

| status | completed | planned | queue_state | protocol_sha256 |
|---|---|---|---|---|
| COMPLETE | 48 | 48 | COMPLETE | 28bffd0bc277174fd63eda89acea342088fb787789e7095c41c7637291ef50c0 |

완료되고 기술 audit PASS인 동일 장면·seed 짝만 비교한다. 미완료/기술 실패는 NOT_RUN/FAIL로 표시하고 대체하지 않는다. 정적 SLW·LC의 상자 통과는 N/A(12블록 중 돌발8블록만 통과 검정 대상). E2 성공 비열등은 성공 차이≥−1회의 파일럿 서술 기준이며 통계적 비열등 검정이 아니다.

| condition | primary | complete_pairs | graph_attempts | graph_applied | graph_adoption_rate | align_delta_median_s | both_arrival_n | arrival_delta_median_s | graph_only_goal | cut_only_goal | goal_delta | descriptive_noninferior | margin_runs | not_statistical_test | incomplete |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D075 | False | 12 | 714 | 573 | 0.80252 | 0.77778 | 3 | -0.75 | 2 | 1 | 1 | True | -1 | True | False |
| D150 | True | 12 | 418 | 306 | 0.73206 | -5.7361 | 2 | -1.4861 | 2 | 3 | -1 | True | -1 | True | False |

아래는 네 run이 모두 완료된 장면·seed에서 (GRAPH−CUT) D150 − (GRAPH−CUT) D075이다. 도착시간은 네 run 모두 도착한 경우만 포함.

| scene | index | align_delta150_minus_delta075_s | arrival_delta150_minus_delta075_s |
|---|---|---|---|
| H1 | 225 | -3.1111 | — |
| H1 | 226 | -0.80556 | — |
| H1-v2 | 225 | 2.5556 | — |
| H1-v2 | 226 | 10.111 | — |
| H2 | 225 | -9.4444 | — |
| H2 | 226 | -23.889 | — |
| L2 | 225 | 2.2778 | — |
| L2 | 226 | -6.2222 | — |
| LC | 225 | -8.3611 | — |
| LC | 226 | -8.1944 | — |
| SLW | 225 | 8.1111 | — |
| SLW | 226 | -15.333 | — |

| scene | index | method | technical | classification | success | collision | wrong_stop | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | align_rotate_s | minimum_clearance_m | graph_adoption_rate | graph_rejection_reasons | detour_applied_count | boundary_curvature_dropped |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW_D075 | 225 | GRAPH-HOLD | PASS | SUCCESS | True | False | False | False | — | 55.083 | 8.7778 | 3.1111 | 0.047391 | 0.72222 | {'EC_TAIL_REJECT': 2, 'SOLVER_OR_CERTIFICATE_REJECT': 13} | 0 | 6 |
| SLW_D075 | 225 | CUT-HOLD | PASS | WRONG_STOP | False | False | True | False | — | — | 45.778 | 0 | 0.022888 | — | {} | 0 | 0 |
| LC_D075 | 225 | GRAPH-HOLD | PASS | SUCCESS | True | False | False | False | — | 32.333 | 4.8889 | 1.4444 | 0.17842 | 0.83333 | {'SOLVER_OR_CERTIFICATE_REJECT': 5} | 0 | 4 |
| LC_D075 | 225 | CUT-HOLD | PASS | SUCCESS | True | False | False | False | — | 26.833 | 2.8889 | 0 | 0.18305 | — | {} | 0 | 0 |
| L2_D075 | 225 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 7 | 3.2222 | 0.1268 | 0.8764 | {'SOLVER_OR_CERTIFICATE_REJECT': 11} | 0 | 6 |
| L2_D075 | 225 | CUT-HOLD | PASS | WRONG_STOP | False | False | True | True | 20.958 | — | 5.7778 | 2.5556 | 0.085046 | — | {} | 0 | 0 |
| H1_D075 | 225 | GRAPH-HOLD | PASS | WRONG_STOP | False | False | True | False | — | — | 6.7778 | 1.1111 | 0.068264 | 0.83784 | {'SOLVER_OR_CERTIFICATE_REJECT': 5, 'EC_TAIL_REJECT': 1} | 0 | 4 |
| H1_D075 | 225 | CUT-HOLD | PASS | SUCCESS | True | False | False | True | 7.4722 | 28.833 | 2.8889 | 0 | 0.032294 | — | {} | 0 | 0 |
| H2_D075 | 225 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 7.4444 | 3.8889 | 0.070247 | 0.86517 | {'SOLVER_OR_CERTIFICATE_REJECT': 12} | 0 | 6 |
| H2_D075 | 225 | CUT-HOLD | PASS | WRONG_STOP | False | False | True | False | — | — | 6.4444 | 3 | 0.043802 | — | {} | 0 | 0 |
| H1-v2_D075 | 225 | CUT-HOLD | PASS | TIMEOUT | False | False | False | True | 46.639 | — | 36.667 | 3.4444 | 0.035845 | — | {} | 0 | 0 |
| H1-v2_D075 | 225 | GRAPH-HOLD | PASS | WRONG_STOP | False | False | True | True | 19.958 | — | 11.444 | 2.5556 | 0.026147 | 0.6 | {'SOLVER_OR_CERTIFICATE_REJECT': 14, 'EC_TAIL_REJECT': 2} | 0 | 7 |
| SLW_D150 | 225 | CUT-HOLD | PASS | SUCCESS | True | False | False | False | — | 45.583 | 9.6667 | 3.6667 | 0.05299 | — | {} | 0 | 0 |
| SLW_D150 | 225 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 31.444 | 14.889 | 0.050444 | 0.44898 | {'EC_TAIL_REJECT': 2, 'SOLVER_OR_CERTIFICATE_REJECT': 24, 'INITIALIZATION_REJECTED': 1} | 0 | 14 |
| LC_D150 | 225 | GRAPH-HOLD | PASS | SUCCESS | True | False | False | False | — | 36.833 | 4.8889 | 1.1111 | 0.28285 | 0.9 | {'SOLVER_OR_CERTIFICATE_REJECT': 2} | 0 | 2 |
| LC_D150 | 225 | CUT-HOLD | PASS | WRONG_STOP | False | False | True | False | — | — | 12.361 | 8.0278 | 0.15056 | — | {} | 0 | 0 |
| L2_D150 | 225 | CUT-HOLD | PASS | SUCCESS | True | False | False | True | 12.889 | 50.833 | 11.5 | 7.1667 | 0.17735 | — | {} | 0 | 0 |
| L2_D150 | 225 | GRAPH-HOLD | PASS | WRONG_STOP | False | False | True | False | — | — | 14.333 | 10.111 | 0.047753 | 0.83871 | {'SOLVER_OR_CERTIFICATE_REJECT': 5} | 0 | 5 |
| H1_D150 | 225 | CUT-HOLD | PASS | SUCCESS | True | False | False | True | 10.403 | 38.333 | 9.5556 | 4.7778 | 0.074734 | — | {} | 0 | 0 |
| H1_D150 | 225 | GRAPH-HOLD | PASS | SUCCESS | True | False | False | True | 6.8333 | 40.333 | 7.1111 | 2.7778 | 0.092261 | 0.78261 | {'SOLVER_OR_CERTIFICATE_REJECT': 4, 'EC_TAIL_REJECT': 1} | 0 | 3 |
| H2_D150 | 225 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 15.556 | 10.889 | 0.062835 | 0.73077 | {'EC_TAIL_REJECT': 3, 'SOLVER_OR_CERTIFICATE_REJECT': 11} | 0 | 8 |
| H2_D150 | 225 | CUT-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 25.556 | 19.444 | 0.040423 | — | {} | 0 | 0 |
| H1-v2_D150 | 225 | GRAPH-HOLD | PASS | SUCCESS | True | False | False | True | 21.889 | 47.597 | 10 | 6.1111 | 0.12196 | 0.68966 | {'EC_TAIL_REJECT': 3, 'SOLVER_OR_CERTIFICATE_REJECT': 6} | 0 | 5 |
| H1-v2_D150 | 225 | CUT-HOLD | PASS | SUCCESS | True | False | False | True | 14.292 | 52.569 | 11.556 | 4.4444 | 0.038639 | — | {} | 0 | 0 |
| SLW_D075 | 226 | CUT-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 22.222 | 12.667 | 0.064117 | — | {} | 0 | 0 |
| SLW_D075 | 226 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 32.111 | 22.222 | 0.037007 | 0.48837 | {'EC_TAIL_REJECT': 1, 'SOLVER_OR_CERTIFICATE_REJECT': 43} | 0 | 24 |
| LC_D075 | 226 | CUT-HOLD | PASS | SUCCESS | True | False | False | False | — | 27.583 | 4.2222 | 1 | 0.24509 | — | {} | 0 | 0 |
| LC_D075 | 226 | GRAPH-HOLD | PASS | SUCCESS | True | False | False | False | — | 26.833 | 3.3333 | 0.33333 | 0.22144 | 0.96 | {'SOLVER_OR_CERTIFICATE_REJECT': 1} | 0 | 2 |
| L2_D075 | 226 | CUT-HOLD | PASS | SUCCESS | True | False | False | True | 47.75 | 82.833 | 8.2222 | 2.2222 | 0.042832 | — | {} | 0 | 0 |
| L2_D075 | 226 | GRAPH-HOLD | PASS | SUCCESS | True | False | False | True | 36.569 | 70.583 | 3.8889 | 0.88889 | 0.11857 | 0.98551 | {'SOLVER_OR_CERTIFICATE_REJECT': 1} | 0 | 2 |
| H1_D075 | 226 | CUT-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 36.111 | 4.8889 | 0.061845 | — | {} | 0 | 0 |
| H1_D075 | 226 | GRAPH-HOLD | PASS | SUCCESS | True | False | False | True | 7.6944 | 29.833 | 2.8889 | 0 | 0.12128 | 0.9 | {'SOLVER_OR_CERTIFICATE_REJECT': 3} | 0 | 1 |
| H2_D075 | 226 | GRAPH-HOLD | PASS | WRONG_STOP | False | False | True | True | 66.458 | — | 13.222 | 9.2222 | 0.056536 | 0.89744 | {'SOLVER_OR_CERTIFICATE_REJECT': 8} | 0 | 7 |
| H2_D075 | 226 | CUT-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 7.6667 | 3.8889 | 0.045525 | — | {} | 0 | 0 |
| H1-v2_D075 | 226 | CUT-HOLD | PASS | TIMEOUT | False | False | False | True | 50.5 | — | 22.778 | 15.778 | 0.045072 | — | {} | 0 | 0 |
| H1-v2_D075 | 226 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | True | 53.708 | — | 13.222 | 4.8889 | 0.038301 | 0.78161 | {'SOLVER_OR_CERTIFICATE_REJECT': 18, 'EC_TAIL_REJECT': 1} | 0 | 9 |
| SLW_D150 | 226 | CUT-HOLD | PASS | SUCCESS | True | False | False | False | — | 78.333 | 28.333 | 21.778 | 0.04961 | — | {} | 0 | 0 |
| SLW_D150 | 226 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 20.444 | 16 | 0.039629 | 0.72222 | {'SOLVER_OR_CERTIFICATE_REJECT': 15} | 0 | 10 |
| LC_D150 | 226 | GRAPH-HOLD | PASS | SUCCESS | True | False | False | False | — | 28.083 | 3.6667 | 0 | 0.16518 | 0.86667 | {'SOLVER_OR_CERTIFICATE_REJECT': 2} | 0 | 1 |
| LC_D150 | 226 | CUT-HOLD | PASS | WRONG_STOP | False | False | True | False | — | — | 13.194 | 8.8611 | 0.066749 | — | {} | 0 | 0 |
| L2_D150 | 226 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | True | 57.042 | — | 15 | 10.333 | 0.062887 | 0.7451 | {'EC_TAIL_REJECT': 2, 'SOLVER_OR_CERTIFICATE_REJECT': 11} | 0 | 8 |
| L2_D150 | 226 | CUT-HOLD | PASS | TIMEOUT | False | False | False | True | 49.778 | — | 23.111 | 17.889 | 0.05004 | — | {} | 0 | 0 |
| H1_D150 | 226 | CUT-HOLD | PASS | WRONG_STOP | False | False | True | False | — | — | 11.472 | 7.1389 | 0.070523 | — | {} | 0 | 0 |
| H1_D150 | 226 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 64.889 | 1.4444 | 0.15206 | 0.88889 | {'SOLVER_OR_CERTIFICATE_REJECT': 2} | 0 | 2 |
| H2_D150 | 226 | GRAPH-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 20.556 | 9.7778 | 0.056732 | 0.80392 | {'EC_TAIL_REJECT': 3, 'SOLVER_OR_CERTIFICATE_REJECT': 7} | 0 | 13 |
| H2_D150 | 226 | CUT-HOLD | PASS | TIMEOUT | False | False | False | False | — | — | 34.333 | 28.333 | 0.072843 | — | {} | 0 | 0 |
| H1-v2_D150 | 226 | GRAPH-HOLD | PASS | WRONG_STOP | False | False | True | False | — | — | 12.444 | 8.6667 | 0.042712 | 0.68 | {'SOLVER_OR_CERTIFICATE_REJECT': 7, 'EC_TAIL_REJECT': 1} | 0 | 5 |
| H1-v2_D150 | 226 | CUT-HOLD | PASS | WRONG_STOP | False | False | True | False | — | — | 13.444 | 9.4444 | 0.071875 | — | {} | 0 | 0 |

| scene | index | condition | align_delta_s | arrival_delta_s | goal_delta |
|---|---|---|---|---|---|
| H1-v2_D075 | 225 | D075 | -0.88889 | — | 0 |
| H1-v2_D075 | 226 | D075 | -10.889 | — | 0 |
| H1_D075 | 225 | D075 | 1.1111 | — | -1 |
| H1_D075 | 226 | D075 | -4.8889 | — | 1 |
| H2_D075 | 225 | D075 | 0.88889 | — | 0 |
| H2_D075 | 226 | D075 | 5.3333 | — | 0 |
| L2_D075 | 225 | D075 | 0.66667 | — | 0 |
| L2_D075 | 226 | D075 | -1.3333 | -12.25 | 0 |
| LC_D075 | 225 | D075 | 1.4444 | 5.5 | 0 |
| LC_D075 | 226 | D075 | -0.66667 | -0.75 | 0 |
| SLW_D075 | 225 | D075 | 3.1111 | — | 1 |
| SLW_D075 | 226 | D075 | 9.5556 | — | 0 |
| H1-v2_D150 | 225 | D150 | 1.6667 | -4.9722 | 0 |
| H1-v2_D150 | 226 | D150 | -0.77778 | — | 0 |
| H1_D150 | 225 | D150 | -2 | 2 | 0 |
| H1_D150 | 226 | D150 | -5.6944 | — | 0 |
| H2_D150 | 225 | D150 | -8.5556 | — | 0 |
| H2_D150 | 226 | D150 | -18.556 | — | 0 |
| L2_D150 | 225 | D150 | 2.9444 | — | -1 |
| L2_D150 | 226 | D150 | -7.5556 | — | 0 |
| LC_D150 | 225 | D150 | -6.9167 | — | 1 |
| LC_D150 | 226 | D150 | -8.8611 | — | 1 |
| SLW_D150 | 225 | D150 | 11.222 | — | -1 |
| SLW_D150 | 226 | D150 | -5.7778 | — | -1 |

![night20261111_E2_H1-v2_D075_225_CUT-HOLD](figures/night20261111_E2_H1-v2_D075_225_CUT-HOLD.png)

![night20261111_E2_H1-v2_D075_225_GRAPH-HOLD](figures/night20261111_E2_H1-v2_D075_225_GRAPH-HOLD.png)

![night20261111_E2_H1-v2_D075_226_CUT-HOLD](figures/night20261111_E2_H1-v2_D075_226_CUT-HOLD.png)

![night20261111_E2_H1-v2_D075_226_GRAPH-HOLD](figures/night20261111_E2_H1-v2_D075_226_GRAPH-HOLD.png)

![night20261111_E2_H1-v2_D150_225_CUT-HOLD](figures/night20261111_E2_H1-v2_D150_225_CUT-HOLD.png)

![night20261111_E2_H1-v2_D150_225_GRAPH-HOLD](figures/night20261111_E2_H1-v2_D150_225_GRAPH-HOLD.png)

![night20261111_E2_H1-v2_D150_226_CUT-HOLD](figures/night20261111_E2_H1-v2_D150_226_CUT-HOLD.png)

![night20261111_E2_H1-v2_D150_226_GRAPH-HOLD](figures/night20261111_E2_H1-v2_D150_226_GRAPH-HOLD.png)

![night20261111_E2_H1_D075_225_CUT-HOLD](figures/night20261111_E2_H1_D075_225_CUT-HOLD.png)

![night20261111_E2_H1_D075_225_GRAPH-HOLD](figures/night20261111_E2_H1_D075_225_GRAPH-HOLD.png)

![night20261111_E2_H1_D075_226_CUT-HOLD](figures/night20261111_E2_H1_D075_226_CUT-HOLD.png)

![night20261111_E2_H1_D075_226_GRAPH-HOLD](figures/night20261111_E2_H1_D075_226_GRAPH-HOLD.png)

![night20261111_E2_H1_D150_225_CUT-HOLD](figures/night20261111_E2_H1_D150_225_CUT-HOLD.png)

![night20261111_E2_H1_D150_225_GRAPH-HOLD](figures/night20261111_E2_H1_D150_225_GRAPH-HOLD.png)

![night20261111_E2_H1_D150_226_CUT-HOLD](figures/night20261111_E2_H1_D150_226_CUT-HOLD.png)

![night20261111_E2_H1_D150_226_GRAPH-HOLD](figures/night20261111_E2_H1_D150_226_GRAPH-HOLD.png)

![night20261111_E2_H2_D075_225_CUT-HOLD](figures/night20261111_E2_H2_D075_225_CUT-HOLD.png)

![night20261111_E2_H2_D075_225_GRAPH-HOLD](figures/night20261111_E2_H2_D075_225_GRAPH-HOLD.png)

![night20261111_E2_H2_D075_226_CUT-HOLD](figures/night20261111_E2_H2_D075_226_CUT-HOLD.png)

![night20261111_E2_H2_D075_226_GRAPH-HOLD](figures/night20261111_E2_H2_D075_226_GRAPH-HOLD.png)

![night20261111_E2_H2_D150_225_CUT-HOLD](figures/night20261111_E2_H2_D150_225_CUT-HOLD.png)

![night20261111_E2_H2_D150_225_GRAPH-HOLD](figures/night20261111_E2_H2_D150_225_GRAPH-HOLD.png)

![night20261111_E2_H2_D150_226_CUT-HOLD](figures/night20261111_E2_H2_D150_226_CUT-HOLD.png)

![night20261111_E2_H2_D150_226_GRAPH-HOLD](figures/night20261111_E2_H2_D150_226_GRAPH-HOLD.png)

![night20261111_E2_L2_D075_225_CUT-HOLD](figures/night20261111_E2_L2_D075_225_CUT-HOLD.png)

![night20261111_E2_L2_D075_225_GRAPH-HOLD](figures/night20261111_E2_L2_D075_225_GRAPH-HOLD.png)

![night20261111_E2_L2_D075_226_CUT-HOLD](figures/night20261111_E2_L2_D075_226_CUT-HOLD.png)

![night20261111_E2_L2_D075_226_GRAPH-HOLD](figures/night20261111_E2_L2_D075_226_GRAPH-HOLD.png)

![night20261111_E2_L2_D150_225_CUT-HOLD](figures/night20261111_E2_L2_D150_225_CUT-HOLD.png)

![night20261111_E2_L2_D150_225_GRAPH-HOLD](figures/night20261111_E2_L2_D150_225_GRAPH-HOLD.png)

![night20261111_E2_L2_D150_226_CUT-HOLD](figures/night20261111_E2_L2_D150_226_CUT-HOLD.png)

![night20261111_E2_L2_D150_226_GRAPH-HOLD](figures/night20261111_E2_L2_D150_226_GRAPH-HOLD.png)

![night20261111_E2_LC_D075_225_CUT-HOLD](figures/night20261111_E2_LC_D075_225_CUT-HOLD.png)

![night20261111_E2_LC_D075_225_GRAPH-HOLD](figures/night20261111_E2_LC_D075_225_GRAPH-HOLD.png)

![night20261111_E2_LC_D075_226_CUT-HOLD](figures/night20261111_E2_LC_D075_226_CUT-HOLD.png)

![night20261111_E2_LC_D075_226_GRAPH-HOLD](figures/night20261111_E2_LC_D075_226_GRAPH-HOLD.png)

![night20261111_E2_LC_D150_225_CUT-HOLD](figures/night20261111_E2_LC_D150_225_CUT-HOLD.png)

![night20261111_E2_LC_D150_225_GRAPH-HOLD](figures/night20261111_E2_LC_D150_225_GRAPH-HOLD.png)

![night20261111_E2_LC_D150_226_CUT-HOLD](figures/night20261111_E2_LC_D150_226_CUT-HOLD.png)

![night20261111_E2_LC_D150_226_GRAPH-HOLD](figures/night20261111_E2_LC_D150_226_GRAPH-HOLD.png)

![night20261111_E2_SLW_D075_225_CUT-HOLD](figures/night20261111_E2_SLW_D075_225_CUT-HOLD.png)

![night20261111_E2_SLW_D075_225_GRAPH-HOLD](figures/night20261111_E2_SLW_D075_225_GRAPH-HOLD.png)

![night20261111_E2_SLW_D075_226_CUT-HOLD](figures/night20261111_E2_SLW_D075_226_CUT-HOLD.png)

![night20261111_E2_SLW_D075_226_GRAPH-HOLD](figures/night20261111_E2_SLW_D075_226_GRAPH-HOLD.png)

![night20261111_E2_SLW_D150_225_CUT-HOLD](figures/night20261111_E2_SLW_D150_225_CUT-HOLD.png)

![night20261111_E2_SLW_D150_225_GRAPH-HOLD](figures/night20261111_E2_SLW_D150_225_GRAPH-HOLD.png)

![night20261111_E2_SLW_D150_226_CUT-HOLD](figures/night20261111_E2_SLW_D150_226_CUT-HOLD.png)

![night20261111_E2_SLW_D150_226_GRAPH-HOLD](figures/night20261111_E2_SLW_D150_226_GRAPH-HOLD.png)
