# Phase54-P 밤샘 파일럿

| status | completed | planned | queue_state | protocol_sha256 |
|---|---|---|---|---|
| NOT_STARTED | 0 | 48 | SKIPPED | 28bffd0bc277174fd63eda89acea342088fb787789e7095c41c7637291ef50c0 |

완료되고 기술 audit PASS인 동일 장면·seed 짝만 비교한다. 미완료/기술 실패는 NOT_RUN/FAIL로 표시하고 대체하지 않는다. 정적 SLW·LC의 상자 통과는 N/A(12블록 중 돌발8블록만 통과 검정 대상). E2 성공 비열등은 성공 차이≥−1회의 파일럿 서술 기준이며 통계적 비열등 검정이 아니다.

| condition | primary | complete_pairs | graph_attempts | graph_applied | graph_adoption_rate | align_delta_median_s | both_arrival_n | arrival_delta_median_s | graph_only_goal | cut_only_goal | goal_delta | descriptive_noninferior | margin_runs | not_statistical_test | incomplete |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D075 | False | 0 | 0 | 0 | — | — | 0 | — | 0 | 0 | 0 | — | -1 | True | True |
| D150 | True | 0 | 0 | 0 | — | — | 0 | — | 0 | 0 | 0 | — | -1 | True | True |

아래는 네 run이 모두 완료된 장면·seed에서 (GRAPH−CUT) D150 − (GRAPH−CUT) D075이다. 도착시간은 네 run 모두 도착한 경우만 포함.

자료 없음

| scene | index | method | technical | classification | success | collision | wrong_stop | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | align_rotate_s | minimum_clearance_m | graph_adoption_rate | graph_rejection_reasons | detour_applied_count | boundary_curvature_dropped |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW_D075 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D075 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D075 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D075 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D075 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D075 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D075 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D075 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D075 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D075 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D075 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D075 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D150 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D150 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 225 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 225 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D075 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D075 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D075 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D075 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D075 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D075 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D075 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D075 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D075 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D075 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D075 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D075 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D150 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW_D150 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| LC_D150 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| L2_D150 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1_D150 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2_D150 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 226 | GRAPH-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 226 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

자료 없음
