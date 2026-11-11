# Phase61-P — oracle 위치추정 분석용 조건

**실용 위치추정 성능 실험이 아니다.** 영상 관측 시점 시뮬레이터 실제 robot pose와 Topomap 노드 pose를 사용해 XY 최근접 노드를 선택한다. HMM은 사용하지 않는다. 이 oracle 정보는 위치추정에만 쓰며 장애물·EC·Graph에는 새 oracle 정보를 제공하지 않는다.

| status | planned | completed | oracle_localization_analysis_only | pose_clock | delivery_delay_s | protocol_sha256 |
|---|---|---|---|---|---|---|
| PREPARED_NOT_RUN | 18 | 0 | True | observation_pose | 0.75 | 63d91d2ecae5eecef4ad3edfbcadd18ae0cb107c6e864f2fb8e80f71c9a527e4 |

관측 시점 최근접 노드를 먼저 계산한 뒤 기존 candidate_range(radius4) 창과 subgoal 규칙을 그 노드에 적용한다. NoMaD 거리의 threshold3와 창 끝 clamp,closest==goal 선언은 그대로다. D075 전달 지연도 유지하므로 선언은 적용 시점의 실제 위치가 아니라 관측 시점 oracle 노드에 기반한다.

Phase58-P의 CUT/CONS/CONS+G18·EC-tail·ENDPOINT latch·depth 필터·회복·정렬·0.1 fallback·1s 만료·도착 평가를 그대로 유지한다. 새 seed229·230은 기존 jitter 생성 규칙에 입력하며 H1-v2 고정 상자는 그대로다.

| method | scene | n | valid | success | collision | wrong_stop | timeout_without_declaration | box_passage | goal_time_s_median | stopped_s_median | box_passage_from_spawn_s_median | left_right_switches | backward_reference_selections | backward_robot_selections | graph_attempts | graph_applied | graph_adoption_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CUT | H1-v2 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CUT | SLW | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CUT | H2 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CUT | ALL | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CONS | H1-v2 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CONS | SLW | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CONS | H2 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CONS | ALL | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CONS+G18 | H1-v2 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CONS+G18 | SLW | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CONS+G18 | H2 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |
| CONS+G18 | ALL | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — | 0 | 0 | — |

| scene | index | method | status | classification | success | collision | wrong_stop | timeout_without_declaration | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | left_right_switches | backward_reference_selections | backward_robot_selections | graph_adoption_rate | graph_solve_p50_s | graph_solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-v2 | 229 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 229 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 229 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 230 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 230 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 230 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 229 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 229 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 229 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 230 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 230 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 230 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 229 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 229 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 229 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 230 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 230 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 230 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## 쌍별 성공 차이

동일(scene,seed)의 두 run이 모두 기술 PASS인 경우만 성공 차이(left−right)를 계산한다. 미실행·기술 실패는 —이며 실패0으로 대체하지 않는다. 통계 검정이나 새 성과 판정 기준은 추가하지 않았다.

| comparison | valid_pairs | planned_pairs | left_success | right_success | success_difference | left_only | right_only | both_success | both_failure |
|---|---|---|---|---|---|---|---|---|---|
| CONS minus CUT | 0 | 6 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| CONS+G18 minus CUT | 0 | 6 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| CONS+G18 minus CONS | 0 | 6 | 0 | 0 | — | 0 | 0 | 0 | 0 |

| comparison | scene | seed | left_status | right_status | left_success | right_success | success_difference |
|---|---|---|---|---|---|---|---|
| CONS minus CUT | H1-v2 | 229 | NOT_RUN | NOT_RUN | — | — | — |
| CONS minus CUT | H1-v2 | 230 | NOT_RUN | NOT_RUN | — | — | — |
| CONS minus CUT | SLW | 229 | NOT_RUN | NOT_RUN | — | — | — |
| CONS minus CUT | SLW | 230 | NOT_RUN | NOT_RUN | — | — | — |
| CONS minus CUT | H2 | 229 | NOT_RUN | NOT_RUN | — | — | — |
| CONS minus CUT | H2 | 230 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CUT | H1-v2 | 229 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CUT | H1-v2 | 230 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CUT | SLW | 229 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CUT | SLW | 230 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CUT | H2 | 229 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CUT | H2 | 230 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CONS | H1-v2 | 229 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CONS | H1-v2 | 230 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CONS | SLW | 229 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CONS | SLW | 230 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CONS | H2 | 229 | NOT_RUN | NOT_RUN | — | — | — |
| CONS+G18 minus CONS | H2 | 230 | NOT_RUN | NOT_RUN | — | — | — |
