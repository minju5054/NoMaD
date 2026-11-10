# E3_D150_R3 밤샘 파일럿

| status | completed | planned | queue_state | protocol_sha256 |
|---|---|---|---|---|
| COMPLETE | 36 | 36 | COMPLETE | 123ba3c9c7fd2208f21b9070f92fcc91f418d932d89f0a476856f254ed5ee4ae |

완료되고 기술 audit PASS인 동일 장면·seed 짝만 비교한다. 미완료/기술 실패는 NOT_RUN/FAIL로 표시하고 대체하지 않는다. 정적 SLW·LC의 상자 통과는 N/A(12블록 중 돌발8블록만 통과 검정 대상). E2 성공 비열등은 성공 차이≥−1회의 파일럿 서술 기준이며 통계적 비열등 검정이 아니다.

| comparison | complete_run_pairs | box_pairs | static_NA_pairs | ours_only_pass | baseline_only_pass | passage_gain | exact_mcnemar_p | both_passage_n | passage_time_delta_median_s | ours_goal | baseline_goal | ours_collision | collision_free_required | candidate_by_passage_rule |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OURS-R3 minus CUT | 12 | 8 | 4 | 3 | 0 | 3 | 0.25 | 4 | 5.0833 | 3 | 5 | 0 | True | True |
| OURS-R3 minus GRAPH-HO | 12 | 8 | 4 | 6 | 1 | 5 | 0.125 | 1 | 5.0833 | 3 | 5 | 0 | True | — |

| scene | index | method | technical | classification | success | collision | wrong_stop | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | align_rotate_s | minimum_clearance_m | graph_adoption_rate | graph_rejection_reasons | detour_applied_count | boundary_curvature_dropped |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW_D150 | 225 | GRAPH-HO | PASS | SUCCESS | True | False | False | False | — | 87.083 | 36.639 | 6.1111 | 0.12244 | 0.1 | {'INITIALIZATION_REJECTED': 45} | 0 | 0 |
| SLW_D150 | 225 | OURS-R3 | PASS | TIMEOUT | False | False | False | False | — | — | 43.778 | 2.5556 | 0.038629 | — | {} | 3 | 0 |
| SLW_D150 | 225 | CUT | PASS | TIMEOUT | False | False | False | False | — | — | 42 | 8 | 0.095825 | — | {} | 0 | 0 |
| LC_D150 | 225 | GRAPH-HO | PASS | SUCCESS | True | False | False | False | — | 47.333 | 14 | 1 | 0.20053 | 0.13793 | {'INITIALIZATION_REJECTED': 25} | 0 | 0 |
| LC_D150 | 225 | OURS-R3 | PASS | SUCCESS | True | False | False | False | — | 52.083 | 18.306 | 2.6667 | 0.15572 | — | {} | 2 | 0 |
| LC_D150 | 225 | CUT | PASS | SUCCESS | True | False | False | False | — | 45.333 | 13.556 | 1 | 0.18312 | — | {} | 0 | 0 |
| L2_D150 | 225 | OURS-R3 | PASS | WRONG_STOP | False | False | True | True | 19.931 | — | 22.083 | 3.6667 | 0.13896 | — | {} | 2 | 0 |
| L2_D150 | 225 | GRAPH-HO | PASS | SUCCESS | True | False | False | True | 14.847 | 66.583 | 20.694 | 4 | 0.048572 | 0.027027 | {'INITIALIZATION_REJECTED': 36} | 0 | 0 |
| L2_D150 | 225 | CUT | PASS | WRONG_STOP | False | False | True | True | 14.903 | — | 19.944 | 3 | 0.026731 | — | {} | 0 | 0 |
| H1_D150 | 225 | OURS-R3 | PASS | WRONG_STOP | False | False | True | True | 21.681 | — | 26.5 | 1 | 0.054322 | — | {} | 1 | 0 |
| H1_D150 | 225 | CUT | PASS | SUCCESS | True | False | False | True | 14.319 | 50.833 | 17.278 | 3 | 0.071272 | — | {} | 0 | 0 |
| H1_D150 | 225 | GRAPH-HO | PASS | TIMEOUT | False | False | False | False | — | — | 53.778 | 5 | 0.063844 | 0.028571 | {'INITIALIZATION_REJECTED': 34} | 0 | 0 |
| H2_D150 | 225 | CUT | PASS | TIMEOUT | False | False | False | False | — | — | 41.333 | 6.6667 | 0.087516 | — | {} | 0 | 0 |
| H2_D150 | 225 | OURS-R3 | PASS | SUCCESS | True | False | False | True | 34.806 | 61.819 | 15.264 | 2 | 0.17787 | — | {} | 3 | 0 |
| H2_D150 | 225 | GRAPH-HO | PASS | TIMEOUT | False | False | False | False | — | — | 42.333 | 6.8889 | 0.033261 | 0.020408 | {'INITIALIZATION_REJECTED': 46, 'EC_TAIL_REJECT': 2} | 0 | 0 |
| H1-v2_D150 | 225 | GRAPH-HO | PASS | WRONG_STOP | False | False | True | False | — | — | 18.528 | 1 | 0.032407 | 0 | {'INITIALIZATION_REJECTED': 20} | 0 | 0 |
| H1-v2_D150 | 225 | OURS-R3 | PASS | TIMEOUT | False | False | False | True | 22.806 | — | 51.111 | 3.5556 | 0.031434 | — | {} | 3 | 0 |
| H1-v2_D150 | 225 | CUT | PASS | SUCCESS | True | False | False | True | 42.278 | 85.583 | 36.806 | 4 | 0.032045 | — | {} | 0 | 0 |
| SLW_D150 | 226 | CUT | PASS | TIMEOUT | False | False | False | False | — | — | 58.889 | 17.222 | 0.066895 | — | {} | 0 | 0 |
| SLW_D150 | 226 | GRAPH-HO | PASS | TIMEOUT | False | False | False | False | — | — | 38.667 | 5 | 0.050241 | 0.019608 | {'INITIALIZATION_REJECTED': 50} | 0 | 0 |
| SLW_D150 | 226 | OURS-R3 | PASS | TIMEOUT | False | False | False | False | — | — | 55.667 | 3 | 0.028085 | — | {} | 1 | 0 |
| LC_D150 | 226 | CUT | PASS | SUCCESS | True | False | False | False | — | 52.333 | 20.667 | 5 | 0.24517 | — | {} | 0 | 0 |
| LC_D150 | 226 | OURS-R3 | PASS | SUCCESS | True | False | False | False | — | 43.833 | 15.056 | 2 | 0.23947 | — | {} | 1 | 0 |
| LC_D150 | 226 | GRAPH-HO | PASS | SUCCESS | True | False | False | False | — | 66.583 | 28.917 | 7 | 0.087853 | 0.027027 | {'INITIALIZATION_REJECTED': 36} | 0 | 0 |
| L2_D150 | 226 | OURS-R3 | PASS | WRONG_STOP | False | False | True | True | 18.083 | — | 18.569 | 1.4444 | 0.12814 | — | {} | 4 | 0 |
| L2_D150 | 226 | CUT | PASS | TIMEOUT | False | False | False | False | — | — | 39.333 | 6 | 0.1694 | — | {} | 0 | 0 |
| L2_D150 | 226 | GRAPH-HO | PASS | TIMEOUT | False | False | False | False | — | — | 41.444 | 4 | 0.21698 | 0 | {'INITIALIZATION_REJECTED': 43} | 0 | 0 |
| H1_D150 | 226 | CUT | PASS | SUCCESS | True | False | False | True | 13.792 | 50.583 | 16.472 | 1 | 0.075197 | — | {} | 0 | 0 |
| H1_D150 | 226 | GRAPH-HO | PASS | TIMEOUT | False | False | False | False | — | — | 49.111 | 5.3333 | 0.04852 | 0.02439 | {'INITIALIZATION_REJECTED': 37, 'SOLVER_OR_CERTIFICATE_REJECT': 3} | 0 | 0 |
| H1_D150 | 226 | OURS-R3 | PASS | WRONG_STOP | False | False | True | True | 18.931 | — | 23.083 | 2 | 0.072714 | — | {} | 1 | 0 |
| H2_D150 | 226 | OURS-R3 | PASS | TIMEOUT | False | False | False | False | — | — | 37.333 | 5.1111 | 0.13264 | — | {} | 1 | 0 |
| H2_D150 | 226 | CUT | PASS | TIMEOUT | False | False | False | False | — | — | 36.333 | 4 | 0.15815 | — | {} | 0 | 0 |
| H2_D150 | 226 | GRAPH-HO | PASS | SUCCESS | True | False | False | True | 51.639 | 82.083 | 30.083 | 4 | 0.052539 | 0 | {'INITIALIZATION_REJECTED': 43, 'EC_TAIL_REJECT': 1} | 0 | 0 |
| H1-v2_D150 | 226 | OURS-R3 | PASS | TIMEOUT | False | False | False | True | 29.542 | — | 52.556 | 7.8889 | 0.049414 | — | {} | 2 | 0 |
| H1-v2_D150 | 226 | GRAPH-HO | PASS | WRONG_STOP | False | False | True | False | — | — | 18.264 | 3 | 0.22751 | 0.08 | {'INITIALIZATION_REJECTED': 23} | 0 | 0 |
| H1-v2_D150 | 226 | CUT | PASS | TIMEOUT | False | False | False | False | — | — | 37.667 | 7.8889 | 0.063887 | — | {} | 0 | 0 |

| scene | index | comparison | box_applicable | ours_pass | baseline_pass | ours_goal | baseline_goal |
|---|---|---|---|---|---|---|---|
| H1-v2_D150 | 225 | OURS-R3 minus CUT | True | True | True | False | True |
| H1-v2_D150 | 226 | OURS-R3 minus CUT | True | True | False | False | False |
| H1_D150 | 225 | OURS-R3 minus CUT | True | True | True | False | True |
| H1_D150 | 226 | OURS-R3 minus CUT | True | True | True | False | True |
| H2_D150 | 225 | OURS-R3 minus CUT | True | True | False | True | False |
| H2_D150 | 226 | OURS-R3 minus CUT | True | False | False | False | False |
| L2_D150 | 225 | OURS-R3 minus CUT | True | True | True | False | False |
| L2_D150 | 226 | OURS-R3 minus CUT | True | True | False | False | False |
| LC_D150 | 225 | OURS-R3 minus CUT | False | False | False | True | True |
| LC_D150 | 226 | OURS-R3 minus CUT | False | False | False | True | True |
| SLW_D150 | 225 | OURS-R3 minus CUT | False | False | False | False | False |
| SLW_D150 | 226 | OURS-R3 minus CUT | False | False | False | False | False |
| H1-v2_D150 | 225 | OURS-R3 minus GRAPH-HO | True | True | False | False | False |
| H1-v2_D150 | 226 | OURS-R3 minus GRAPH-HO | True | True | False | False | False |
| H1_D150 | 225 | OURS-R3 minus GRAPH-HO | True | True | False | False | False |
| H1_D150 | 226 | OURS-R3 minus GRAPH-HO | True | True | False | False | False |
| H2_D150 | 225 | OURS-R3 minus GRAPH-HO | True | True | False | True | False |
| H2_D150 | 226 | OURS-R3 minus GRAPH-HO | True | False | True | False | True |
| L2_D150 | 225 | OURS-R3 minus GRAPH-HO | True | True | True | False | True |
| L2_D150 | 226 | OURS-R3 minus GRAPH-HO | True | True | False | False | False |
| LC_D150 | 225 | OURS-R3 minus GRAPH-HO | False | False | False | True | True |
| LC_D150 | 226 | OURS-R3 minus GRAPH-HO | False | False | False | True | True |
| SLW_D150 | 225 | OURS-R3 minus GRAPH-HO | False | False | False | False | True |
| SLW_D150 | 226 | OURS-R3 minus GRAPH-HO | False | False | False | False | False |

![night20261111_E3_H1-v2_D150_225_CUT](figures/night20261111_E3_H1-v2_D150_225_CUT.png)

![night20261111_E3_H1-v2_D150_225_GRAPH-HO](figures/night20261111_E3_H1-v2_D150_225_GRAPH-HO.png)

![night20261111_E3_H1-v2_D150_225_OURS-R3](figures/night20261111_E3_H1-v2_D150_225_OURS-R3.png)

![night20261111_E3_H1-v2_D150_226_CUT](figures/night20261111_E3_H1-v2_D150_226_CUT.png)

![night20261111_E3_H1-v2_D150_226_GRAPH-HO](figures/night20261111_E3_H1-v2_D150_226_GRAPH-HO.png)

![night20261111_E3_H1-v2_D150_226_OURS-R3](figures/night20261111_E3_H1-v2_D150_226_OURS-R3.png)

![night20261111_E3_H1_D150_225_CUT](figures/night20261111_E3_H1_D150_225_CUT.png)

![night20261111_E3_H1_D150_225_GRAPH-HO](figures/night20261111_E3_H1_D150_225_GRAPH-HO.png)

![night20261111_E3_H1_D150_225_OURS-R3](figures/night20261111_E3_H1_D150_225_OURS-R3.png)

![night20261111_E3_H1_D150_226_CUT](figures/night20261111_E3_H1_D150_226_CUT.png)

![night20261111_E3_H1_D150_226_GRAPH-HO](figures/night20261111_E3_H1_D150_226_GRAPH-HO.png)

![night20261111_E3_H1_D150_226_OURS-R3](figures/night20261111_E3_H1_D150_226_OURS-R3.png)

![night20261111_E3_H2_D150_225_CUT](figures/night20261111_E3_H2_D150_225_CUT.png)

![night20261111_E3_H2_D150_225_GRAPH-HO](figures/night20261111_E3_H2_D150_225_GRAPH-HO.png)

![night20261111_E3_H2_D150_225_OURS-R3](figures/night20261111_E3_H2_D150_225_OURS-R3.png)

![night20261111_E3_H2_D150_226_CUT](figures/night20261111_E3_H2_D150_226_CUT.png)

![night20261111_E3_H2_D150_226_GRAPH-HO](figures/night20261111_E3_H2_D150_226_GRAPH-HO.png)

![night20261111_E3_H2_D150_226_OURS-R3](figures/night20261111_E3_H2_D150_226_OURS-R3.png)

![night20261111_E3_L2_D150_225_CUT](figures/night20261111_E3_L2_D150_225_CUT.png)

![night20261111_E3_L2_D150_225_GRAPH-HO](figures/night20261111_E3_L2_D150_225_GRAPH-HO.png)

![night20261111_E3_L2_D150_225_OURS-R3](figures/night20261111_E3_L2_D150_225_OURS-R3.png)

![night20261111_E3_L2_D150_226_CUT](figures/night20261111_E3_L2_D150_226_CUT.png)

![night20261111_E3_L2_D150_226_GRAPH-HO](figures/night20261111_E3_L2_D150_226_GRAPH-HO.png)

![night20261111_E3_L2_D150_226_OURS-R3](figures/night20261111_E3_L2_D150_226_OURS-R3.png)

![night20261111_E3_LC_D150_225_CUT](figures/night20261111_E3_LC_D150_225_CUT.png)

![night20261111_E3_LC_D150_225_GRAPH-HO](figures/night20261111_E3_LC_D150_225_GRAPH-HO.png)

![night20261111_E3_LC_D150_225_OURS-R3](figures/night20261111_E3_LC_D150_225_OURS-R3.png)

![night20261111_E3_LC_D150_226_CUT](figures/night20261111_E3_LC_D150_226_CUT.png)

![night20261111_E3_LC_D150_226_GRAPH-HO](figures/night20261111_E3_LC_D150_226_GRAPH-HO.png)

![night20261111_E3_LC_D150_226_OURS-R3](figures/night20261111_E3_LC_D150_226_OURS-R3.png)

![night20261111_E3_SLW_D150_225_CUT](figures/night20261111_E3_SLW_D150_225_CUT.png)

![night20261111_E3_SLW_D150_225_GRAPH-HO](figures/night20261111_E3_SLW_D150_225_GRAPH-HO.png)

![night20261111_E3_SLW_D150_225_OURS-R3](figures/night20261111_E3_SLW_D150_225_OURS-R3.png)

![night20261111_E3_SLW_D150_226_CUT](figures/night20261111_E3_SLW_D150_226_CUT.png)

![night20261111_E3_SLW_D150_226_GRAPH-HO](figures/night20261111_E3_SLW_D150_226_GRAPH-HO.png)

![night20261111_E3_SLW_D150_226_OURS-R3](figures/night20261111_E3_SLW_D150_226_OURS-R3.png)
