# E1_D075_R3 밤샘 파일럿

| status | completed | planned | queue_state | protocol_sha256 |
|---|---|---|---|---|
| COMPLETE | 36 | 36 | COMPLETE | 46eb5be0e6a0ee2c2ef39d76b2fa779f6e55b36d2c14e3410da763ba969dde12 |

완료되고 기술 audit PASS인 동일 장면·seed 짝만 비교한다. 미완료/기술 실패는 NOT_RUN/FAIL로 표시하고 대체하지 않는다. 정적 SLW·LC의 상자 통과는 N/A(12블록 중 돌발8블록만 통과 검정 대상). E2 성공 비열등은 성공 차이≥−1회의 파일럿 서술 기준이며 통계적 비열등 검정이 아니다.

| comparison | complete_run_pairs | box_pairs | static_NA_pairs | ours_only_pass | baseline_only_pass | passage_gain | exact_mcnemar_p | both_passage_n | passage_time_delta_median_s | ours_goal | baseline_goal | ours_collision | collision_free_required | candidate_by_passage_rule |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OURS-R3 minus CUT | 12 | 8 | 4 | 2 | 2 | 0 | 1 | 4 | -0.22917 | 3 | 6 | 0 | True | False |
| OURS-R3 minus GRAPH-HO | 12 | 8 | 4 | 1 | 0 | 1 | 1 | 5 | 0.76389 | 3 | 5 | 0 | True | — |

| scene | index | method | technical | classification | success | collision | wrong_stop | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | align_rotate_s | minimum_clearance_m | graph_adoption_rate | graph_rejection_reasons | detour_applied_count | boundary_curvature_dropped |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW_D075 | 225 | GRAPH-HO | PASS | WRONG_STOP | False | False | True | False | — | — | 11.333 | 6.1111 | 0.047327 | 0.5 | {'INITIALIZATION_REJECTED': 10, 'SOLVER_OR_CERTIFICATE_REJECT': 11} | 0 | 0 |
| SLW_D075 | 225 | OURS-R3 | PASS | WRONG_STOP | False | False | True | False | — | — | 17.667 | 3.8889 | 0.045802 | — | {} | 0 | 0 |
| SLW_D075 | 225 | CUT | PASS | SUCCESS | True | False | False | False | — | 53.319 | 9.1111 | 5.2222 | 0.052622 | — | {} | 0 | 0 |
| LC_D075 | 225 | GRAPH-HO | PASS | SUCCESS | True | False | False | False | — | 30.333 | 4.4444 | 1.3333 | 0.16815 | 0.86207 | {'INITIALIZATION_REJECTED': 3, 'SOLVER_OR_CERTIFICATE_REJECT': 1} | 0 | 0 |
| LC_D075 | 225 | OURS-R3 | PASS | WRONG_STOP | False | False | True | False | — | — | 3.2778 | 0.27778 | 0.18805 | — | {} | 1 | 0 |
| LC_D075 | 225 | CUT | PASS | SUCCESS | True | False | False | False | — | 26.833 | 3.8333 | 0.83333 | 0.17814 | — | {} | 0 | 0 |
| L2_D075 | 225 | OURS-R3 | PASS | SUCCESS | True | False | False | True | 16.681 | 44.583 | 7.8889 | 0 | 0.03079 | — | {} | 1 | 0 |
| L2_D075 | 225 | GRAPH-HO | PASS | WRONG_STOP | False | False | True | True | 15.972 | — | 4.5556 | 1.4444 | 0.10338 | 0.84091 | {'INITIALIZATION_REJECTED': 4, 'EC_TAIL_REJECT': 1, 'SOLVER_OR_CERTIFICATE_REJECT': 2} | 0 | 0 |
| L2_D075 | 225 | CUT | PASS | WRONG_STOP | False | False | True | True | 18.319 | — | 8.3333 | 1.5556 | 0.079211 | — | {} | 0 | 0 |
| H1_D075 | 225 | OURS-R3 | PASS | WRONG_STOP | False | False | True | True | 11.861 | — | 6 | 0 | 0.041954 | — | {} | 2 | 0 |
| H1_D075 | 225 | CUT | PASS | WRONG_STOP | False | False | True | True | 10.681 | — | 5.8889 | 0 | 0.09049 | — | {} | 0 | 0 |
| H1_D075 | 225 | GRAPH-HO | PASS | SUCCESS | True | False | False | True | 11.097 | 34.833 | 5.5556 | 0 | 0.097145 | 0.83333 | {'INITIALIZATION_REJECTED': 2, 'EC_TAIL_REJECT': 2, 'SOLVER_OR_CERTIFICATE_REJECT': 1} | 0 | 0 |
| H2_D075 | 225 | CUT | PASS | TIMEOUT | False | False | False | False | — | — | 9.6667 | 5.4444 | 0.098498 | — | {} | 0 | 0 |
| H2_D075 | 225 | OURS-R3 | PASS | WRONG_STOP | False | False | True | True | 31.611 | — | 9.5556 | 4 | 0.13628 | — | {} | 2 | 0 |
| H2_D075 | 225 | GRAPH-HO | PASS | TIMEOUT | False | False | False | False | — | — | 6.2222 | 1.7778 | 0.036563 | 0.81522 | {'INITIALIZATION_REJECTED': 8, 'SOLVER_OR_CERTIFICATE_REJECT': 9} | 0 | 0 |
| H1-v2_D075 | 225 | GRAPH-HO | PASS | TIMEOUT | False | False | False | False | — | — | 15.333 | 6.6667 | 0.054086 | 0.74419 | {'INITIALIZATION_REJECTED': 9, 'SOLVER_OR_CERTIFICATE_REJECT': 13} | 0 | 0 |
| H1-v2_D075 | 225 | OURS-R3 | PASS | WRONG_STOP | False | False | True | False | — | — | 5.4444 | 0 | 0.046186 | — | {} | 2 | 0 |
| H1-v2_D075 | 225 | CUT | PASS | TIMEOUT | False | False | False | True | 42.486 | — | 15.889 | 10 | 0.042776 | — | {} | 0 | 0 |
| SLW_D075 | 226 | CUT | PASS | TIMEOUT | False | False | False | False | — | — | 18.333 | 4.8889 | 0.051722 | — | {} | 0 | 0 |
| SLW_D075 | 226 | GRAPH-HO | PASS | TIMEOUT | False | False | False | False | — | — | 26.556 | 15.889 | 0.047514 | 0.35165 | {'INITIALIZATION_REJECTED': 26, 'SOLVER_OR_CERTIFICATE_REJECT': 32, 'EC_TAIL_REJECT': 1} | 0 | 0 |
| SLW_D075 | 226 | OURS-R3 | PASS | WRONG_STOP | False | False | True | False | — | — | 15.444 | 2.4444 | 0.037514 | — | {} | 0 | 0 |
| LC_D075 | 226 | CUT | PASS | SUCCESS | True | False | False | False | — | 25.333 | 2.8889 | 0 | 0.26473 | — | {} | 0 | 0 |
| LC_D075 | 226 | OURS-R3 | PASS | SUCCESS | True | False | False | False | — | 26.833 | 2.8889 | 0 | 0.20004 | — | {} | 1 | 0 |
| LC_D075 | 226 | GRAPH-HO | PASS | SUCCESS | True | False | False | False | — | 26.583 | 2.8889 | 0 | 0.18292 | 0.92 | {'INITIALIZATION_REJECTED': 1, 'SOLVER_OR_CERTIFICATE_REJECT': 1} | 0 | 0 |
| L2_D075 | 226 | OURS-R3 | PASS | SUCCESS | True | False | False | True | 13.5 | 43.583 | 5.8889 | 1.7778 | 0.16936 | — | {} | 1 | 0 |
| L2_D075 | 226 | CUT | PASS | SUCCESS | True | False | False | True | 17.333 | 47.583 | 7.6944 | 1.3611 | 0.070233 | — | {} | 0 | 0 |
| L2_D075 | 226 | GRAPH-HO | PASS | WRONG_STOP | False | False | True | True | 12.042 | — | 5.1667 | 1.6111 | 0.03393 | 0.83784 | {'INITIALIZATION_REJECTED': 3, 'SOLVER_OR_CERTIFICATE_REJECT': 3} | 0 | 0 |
| H1_D075 | 226 | CUT | PASS | SUCCESS | True | False | False | True | 7.1389 | 29.583 | 3.7778 | 0.66667 | 0.13953 | — | {} | 0 | 0 |
| H1_D075 | 226 | GRAPH-HO | PASS | WRONG_STOP | False | False | True | False | — | — | 16 | 3 | 0.0455 | 0.68627 | {'INITIALIZATION_REJECTED': 8, 'SOLVER_OR_CERTIFICATE_REJECT': 7, 'EC_TAIL_REJECT': 1} | 0 | 0 |
| H1_D075 | 226 | OURS-R3 | PASS | WRONG_STOP | False | False | True | False | — | — | 7.5833 | 0.33333 | 0.020729 | — | {} | 0 | 0 |
| H2_D075 | 226 | OURS-R3 | PASS | WRONG_STOP | False | False | True | True | 33.125 | — | 7 | 2.5556 | 0.045337 | — | {} | 2 | 0 |
| H2_D075 | 226 | CUT | PASS | TIMEOUT | False | False | False | False | — | — | 14.222 | 3.5556 | 0.050374 | — | {} | 0 | 0 |
| H2_D075 | 226 | GRAPH-HO | PASS | SUCCESS | True | False | False | True | 54.75 | 75.583 | 8.3333 | 4.8889 | 0.066118 | 0.81081 | {'INITIALIZATION_REJECTED': 7, 'SOLVER_OR_CERTIFICATE_REJECT': 5, 'EC_TAIL_REJECT': 2} | 0 | 0 |
| H1-v2_D075 | 226 | OURS-R3 | PASS | TIMEOUT | False | False | False | True | 47.278 | — | 22 | 4.6667 | 0.052047 | — | {} | 3 | 0 |
| H1-v2_D075 | 226 | GRAPH-HO | PASS | SUCCESS | True | False | False | True | 22.569 | 44.583 | 9 | 1.4444 | 0.044214 | 0.65 | {'INITIALIZATION_REJECTED': 7, 'SOLVER_OR_CERTIFICATE_REJECT': 7} | 0 | 0 |
| H1-v2_D075 | 226 | CUT | PASS | SUCCESS | True | False | False | True | 21.444 | 41.833 | 7.4444 | 2.5556 | 0.041738 | — | {} | 0 | 0 |

| scene | index | comparison | box_applicable | ours_pass | baseline_pass | ours_goal | baseline_goal |
|---|---|---|---|---|---|---|---|
| H1-v2_D075 | 225 | OURS-R3 minus CUT | True | False | True | False | False |
| H1-v2_D075 | 226 | OURS-R3 minus CUT | True | True | True | False | True |
| H1_D075 | 225 | OURS-R3 minus CUT | True | True | True | False | False |
| H1_D075 | 226 | OURS-R3 minus CUT | True | False | True | False | True |
| H2_D075 | 225 | OURS-R3 minus CUT | True | True | False | False | False |
| H2_D075 | 226 | OURS-R3 minus CUT | True | True | False | False | False |
| L2_D075 | 225 | OURS-R3 minus CUT | True | True | True | True | False |
| L2_D075 | 226 | OURS-R3 minus CUT | True | True | True | True | True |
| LC_D075 | 225 | OURS-R3 minus CUT | False | False | False | False | True |
| LC_D075 | 226 | OURS-R3 minus CUT | False | False | False | True | True |
| SLW_D075 | 225 | OURS-R3 minus CUT | False | False | False | False | True |
| SLW_D075 | 226 | OURS-R3 minus CUT | False | False | False | False | False |
| H1-v2_D075 | 225 | OURS-R3 minus GRAPH-HO | True | False | False | False | False |
| H1-v2_D075 | 226 | OURS-R3 minus GRAPH-HO | True | True | True | False | True |
| H1_D075 | 225 | OURS-R3 minus GRAPH-HO | True | True | True | False | True |
| H1_D075 | 226 | OURS-R3 minus GRAPH-HO | True | False | False | False | False |
| H2_D075 | 225 | OURS-R3 minus GRAPH-HO | True | True | False | False | False |
| H2_D075 | 226 | OURS-R3 minus GRAPH-HO | True | True | True | False | True |
| L2_D075 | 225 | OURS-R3 minus GRAPH-HO | True | True | True | True | False |
| L2_D075 | 226 | OURS-R3 minus GRAPH-HO | True | True | True | True | False |
| LC_D075 | 225 | OURS-R3 minus GRAPH-HO | False | False | False | False | True |
| LC_D075 | 226 | OURS-R3 minus GRAPH-HO | False | False | False | True | True |
| SLW_D075 | 225 | OURS-R3 minus GRAPH-HO | False | False | False | False | False |
| SLW_D075 | 226 | OURS-R3 minus GRAPH-HO | False | False | False | False | False |

![night20261111_E1_H1-v2_D075_225_CUT](figures/night20261111_E1_H1-v2_D075_225_CUT.png)

![night20261111_E1_H1-v2_D075_225_GRAPH-HO](figures/night20261111_E1_H1-v2_D075_225_GRAPH-HO.png)

![night20261111_E1_H1-v2_D075_225_OURS-R3](figures/night20261111_E1_H1-v2_D075_225_OURS-R3.png)

![night20261111_E1_H1-v2_D075_226_CUT](figures/night20261111_E1_H1-v2_D075_226_CUT.png)

![night20261111_E1_H1-v2_D075_226_GRAPH-HO](figures/night20261111_E1_H1-v2_D075_226_GRAPH-HO.png)

![night20261111_E1_H1-v2_D075_226_OURS-R3](figures/night20261111_E1_H1-v2_D075_226_OURS-R3.png)

![night20261111_E1_H1_D075_225_CUT](figures/night20261111_E1_H1_D075_225_CUT.png)

![night20261111_E1_H1_D075_225_GRAPH-HO](figures/night20261111_E1_H1_D075_225_GRAPH-HO.png)

![night20261111_E1_H1_D075_225_OURS-R3](figures/night20261111_E1_H1_D075_225_OURS-R3.png)

![night20261111_E1_H1_D075_226_CUT](figures/night20261111_E1_H1_D075_226_CUT.png)

![night20261111_E1_H1_D075_226_GRAPH-HO](figures/night20261111_E1_H1_D075_226_GRAPH-HO.png)

![night20261111_E1_H1_D075_226_OURS-R3](figures/night20261111_E1_H1_D075_226_OURS-R3.png)

![night20261111_E1_H2_D075_225_CUT](figures/night20261111_E1_H2_D075_225_CUT.png)

![night20261111_E1_H2_D075_225_GRAPH-HO](figures/night20261111_E1_H2_D075_225_GRAPH-HO.png)

![night20261111_E1_H2_D075_225_OURS-R3](figures/night20261111_E1_H2_D075_225_OURS-R3.png)

![night20261111_E1_H2_D075_226_CUT](figures/night20261111_E1_H2_D075_226_CUT.png)

![night20261111_E1_H2_D075_226_GRAPH-HO](figures/night20261111_E1_H2_D075_226_GRAPH-HO.png)

![night20261111_E1_H2_D075_226_OURS-R3](figures/night20261111_E1_H2_D075_226_OURS-R3.png)

![night20261111_E1_L2_D075_225_CUT](figures/night20261111_E1_L2_D075_225_CUT.png)

![night20261111_E1_L2_D075_225_GRAPH-HO](figures/night20261111_E1_L2_D075_225_GRAPH-HO.png)

![night20261111_E1_L2_D075_225_OURS-R3](figures/night20261111_E1_L2_D075_225_OURS-R3.png)

![night20261111_E1_L2_D075_226_CUT](figures/night20261111_E1_L2_D075_226_CUT.png)

![night20261111_E1_L2_D075_226_GRAPH-HO](figures/night20261111_E1_L2_D075_226_GRAPH-HO.png)

![night20261111_E1_L2_D075_226_OURS-R3](figures/night20261111_E1_L2_D075_226_OURS-R3.png)

![night20261111_E1_LC_D075_225_CUT](figures/night20261111_E1_LC_D075_225_CUT.png)

![night20261111_E1_LC_D075_225_GRAPH-HO](figures/night20261111_E1_LC_D075_225_GRAPH-HO.png)

![night20261111_E1_LC_D075_225_OURS-R3](figures/night20261111_E1_LC_D075_225_OURS-R3.png)

![night20261111_E1_LC_D075_226_CUT](figures/night20261111_E1_LC_D075_226_CUT.png)

![night20261111_E1_LC_D075_226_GRAPH-HO](figures/night20261111_E1_LC_D075_226_GRAPH-HO.png)

![night20261111_E1_LC_D075_226_OURS-R3](figures/night20261111_E1_LC_D075_226_OURS-R3.png)

![night20261111_E1_SLW_D075_225_CUT](figures/night20261111_E1_SLW_D075_225_CUT.png)

![night20261111_E1_SLW_D075_225_GRAPH-HO](figures/night20261111_E1_SLW_D075_225_GRAPH-HO.png)

![night20261111_E1_SLW_D075_225_OURS-R3](figures/night20261111_E1_SLW_D075_225_OURS-R3.png)

![night20261111_E1_SLW_D075_226_CUT](figures/night20261111_E1_SLW_D075_226_CUT.png)

![night20261111_E1_SLW_D075_226_GRAPH-HO](figures/night20261111_E1_SLW_D075_226_GRAPH-HO.png)

![night20261111_E1_SLW_D075_226_OURS-R3](figures/night20261111_E1_SLW_D075_226_OURS-R3.png)
