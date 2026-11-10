# E3_D150_R3 밤샘 파일럿

| status | completed | planned | queue_state | protocol_sha256 |
|---|---|---|---|---|
| NOT_STARTED | 0 | 36 | READY_PENDING_USER | 123ba3c9c7fd2208f21b9070f92fcc91f418d932d89f0a476856f254ed5ee4ae |

완료되고 기술 audit PASS인 동일 장면·seed 짝만 비교한다. 미완료/기술 실패는 NOT_RUN/FAIL로 표시하고 대체하지 않는다. 정적 SLW·LC의 상자 통과는 N/A(12블록 중 돌발8블록만 통과 검정 대상). E2 성공 비열등은 성공 차이≥−1회의 파일럿 서술 기준이며 통계적 비열등 검정이 아니다.

| comparison | complete_run_pairs | box_pairs | static_NA_pairs | ours_only_pass | baseline_only_pass | passage_gain | exact_mcnemar_p | both_passage_n | passage_time_delta_median_s | ours_goal | baseline_goal | ours_collision | collision_free_required | candidate_by_passage_rule |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OURS-R3 minus CUT | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | — | 0 | 0 | 0 | True | False |
| OURS-R3 minus GRAPH-HO | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | — | 0 | 0 | 0 | True | — |

| scene | index | method | technical | classification | success | collision | wrong_stop | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | align_rotate_s | minimum_clearance_m | graph_adoption_rate | graph_rejection_reasons | detour_applied_count | boundary_curvature_dropped |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW_D150 | 225 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D150 | 225 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D150 | 225 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 225 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 225 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 225 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 225 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 225 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 225 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 225 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 225 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 225 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 225 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 225 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 225 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 225 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 225 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 225 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D150 | 226 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D150 | 226 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D150 | 226 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 226 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 226 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 226 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 226 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 226 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 226 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 226 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 226 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 226 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 226 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 226 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 226 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 226 | OURS-R3 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 226 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 226 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

자료 없음
