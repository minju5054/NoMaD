# Phase61-P — oracle 위치추정 분석용 조건

**실용 위치추정 성능 실험이 아니다.** 영상 관측 시점 시뮬레이터 실제 robot pose와 Topomap 노드 pose를 사용해 XY 최근접 노드를 선택한다. HMM은 사용하지 않는다. 이 oracle 정보는 위치추정에만 쓰며 장애물·EC·Graph에는 새 oracle 정보를 제공하지 않는다.

| status | planned | completed | oracle_localization_analysis_only | pose_clock | delivery_delay_s | protocol_sha256 |
|---|---|---|---|---|---|---|
| COMPLETE | 18 | 18 | True | observation_pose | 0.75 | 63d91d2ecae5eecef4ad3edfbcadd18ae0cb107c6e864f2fb8e80f71c9a527e4 |

관측 시점 최근접 노드를 먼저 계산한 뒤 기존 candidate_range(radius4) 창과 subgoal 규칙을 그 노드에 적용한다. NoMaD 거리의 threshold3와 창 끝 clamp,closest==goal 선언은 그대로다. D075 전달 지연도 유지하므로 선언은 적용 시점의 실제 위치가 아니라 관측 시점 oracle 노드에 기반한다.

Phase58-P의 CUT/CONS/CONS+G18·EC-tail·ENDPOINT latch·depth 필터·회복·정렬·0.1 fallback·1s 만료·도착 평가를 그대로 유지한다. 새 seed229·230은 기존 jitter 생성 규칙에 입력하며 H1-v2 고정 상자는 그대로다.

| method | scene | n | valid | success | collision | wrong_stop | timeout_without_declaration | box_passage | goal_time_s_median | stopped_s_median | box_passage_from_spawn_s_median | left_right_switches | backward_reference_selections | backward_robot_selections | graph_attempts | graph_applied | graph_adoption_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CUT | H1-v2 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 59.417 | 10.097 | 37.986 | 71 | 52 | 22 | 0 | 0 | — |
| CUT | SLW | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | 24.833 | — | 76 | 62 | 47 | 0 | 0 | — |
| CUT | H2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | — | 9.9931 | 60.944 | 79 | 60 | 29 | 0 | 0 | — |
| CUT | ALL | 6 | 6 | 1 | 0 | 1 | 4 | 2 | 59.417 | 12.778 | 49.465 | 226 | 174 | 98 | 0 | 0 | — |
| CONS | H1-v2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | 12.778 | — | 48 | 33 | 24 | 0 | 0 | — |
| CONS | SLW | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 61.597 | 8.8958 | — | 46 | 35 | 20 | 0 | 0 | — |
| CONS | H2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | 10 | — | 65 | 47 | 13 | 0 | 0 | — |
| CONS | ALL | 6 | 6 | 2 | 0 | 0 | 4 | 0 | 61.597 | 10.333 | — | 159 | 115 | 57 | 0 | 0 | — |
| CONS+G18 | H1-v2 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 51.361 | 11.958 | 20.097 | 31 | 16 | 14 | 129 | 98 | 0.75969 |
| CONS+G18 | SLW | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | 15.333 | — | 57 | 39 | 44 | 176 | 111 | 0.63068 |
| CONS+G18 | H2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | — | 4.6667 | 57.236 | 58 | 36 | 20 | 165 | 146 | 0.88485 |
| CONS+G18 | ALL | 6 | 6 | 1 | 0 | 1 | 4 | 2 | 51.361 | 8.625 | 38.667 | 146 | 91 | 78 | 470 | 355 | 0.75532 |

| scene | index | method | status | classification | success | collision | wrong_stop | timeout_without_declaration | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | left_right_switches | backward_reference_selections | backward_robot_selections | graph_adoption_rate | graph_solve_p50_s | graph_solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-v2 | 229 | CONS | PASS | TIMEOUT | False | False | False | True | False | — | — | 12.667 | 22 | 19 | 15 | — | — | — |
| H1-v2 | 229 | CUT | PASS | TIMEOUT | False | False | False | True | False | — | — | 14.444 | 45 | 32 | 13 | — | — | — |
| H1-v2 | 229 | CONS+G18 | PASS | SUCCESS | True | False | False | False | True | 20.097 | 51.361 | 6.3611 | 13 | 5 | 0 | 0.84783 | 0.21791 | 0.34735 |
| H1-v2 | 230 | CONS+G18 | PASS | TIMEOUT | False | False | False | True | False | — | — | 17.556 | 18 | 11 | 14 | 0.71084 | 0.16109 | 0.25923 |
| H1-v2 | 230 | CUT | PASS | SUCCESS | True | False | False | False | True | 37.986 | 59.417 | 5.75 | 26 | 20 | 9 | — | — | — |
| H1-v2 | 230 | CONS | PASS | TIMEOUT | False | False | False | True | False | — | — | 12.889 | 26 | 14 | 9 | — | — | — |
| SLW | 229 | CONS | PASS | SUCCESS | True | False | False | False | False | — | 57.347 | 7.9028 | 21 | 14 | 9 | — | — | — |
| SLW | 229 | CONS+G18 | PASS | TIMEOUT | False | False | False | True | False | — | — | 10.889 | 29 | 19 | 19 | 0.70787 | 0.1593 | 0.31866 |
| SLW | 229 | CUT | PASS | TIMEOUT | False | False | False | True | False | — | — | 25.556 | 37 | 30 | 25 | — | — | — |
| SLW | 230 | CONS+G18 | PASS | TIMEOUT | False | False | False | True | False | — | — | 19.778 | 28 | 20 | 25 | 0.55172 | 0.16182 | 0.28689 |
| SLW | 230 | CONS | PASS | SUCCESS | True | False | False | False | False | — | 65.847 | 9.8889 | 25 | 21 | 11 | — | — | — |
| SLW | 230 | CUT | PASS | TIMEOUT | False | False | False | True | False | — | — | 24.111 | 39 | 32 | 22 | — | — | — |
| H2 | 229 | CUT | PASS | TIMEOUT | False | False | False | True | False | — | — | 11.111 | 37 | 32 | 15 | — | — | — |
| H2 | 229 | CONS+G18 | PASS | WRONG_STOP | False | False | True | False | True | 57.236 | — | 3.7778 | 30 | 21 | 11 | 0.83117 | 0.15996 | 0.23079 |
| H2 | 229 | CONS | PASS | TIMEOUT | False | False | False | True | False | — | — | 10.778 | 33 | 21 | 7 | — | — | — |
| H2 | 230 | CUT | PASS | WRONG_STOP | False | False | True | False | True | 60.944 | — | 8.875 | 42 | 28 | 14 | — | — | — |
| H2 | 230 | CONS | PASS | TIMEOUT | False | False | False | True | False | — | — | 9.2222 | 32 | 26 | 6 | — | — | — |
| H2 | 230 | CONS+G18 | PASS | TIMEOUT | False | False | False | True | False | — | — | 5.5556 | 28 | 15 | 9 | 0.93182 | 0.16004 | 0.23348 |

## 쌍별 성공 차이

동일(scene,seed)의 두 run이 모두 기술 PASS인 경우만 성공 차이(left−right)를 계산한다. 미실행·기술 실패는 —이며 실패0으로 대체하지 않는다. 통계 검정이나 새 성과 판정 기준은 추가하지 않았다.

| comparison | valid_pairs | planned_pairs | left_success | right_success | success_difference | left_only | right_only | both_success | both_failure |
|---|---|---|---|---|---|---|---|---|---|
| CONS minus CUT | 6 | 6 | 2 | 1 | 1 | 2 | 1 | 0 | 3 |
| CONS+G18 minus CUT | 6 | 6 | 1 | 1 | 0 | 1 | 1 | 0 | 4 |
| CONS+G18 minus CONS | 6 | 6 | 1 | 2 | -1 | 1 | 2 | 0 | 3 |

| comparison | scene | seed | left_status | right_status | left_success | right_success | success_difference |
|---|---|---|---|---|---|---|---|
| CONS minus CUT | H1-v2 | 229 | PASS | PASS | False | False | 0 |
| CONS minus CUT | H1-v2 | 230 | PASS | PASS | False | True | -1 |
| CONS minus CUT | SLW | 229 | PASS | PASS | True | False | 1 |
| CONS minus CUT | SLW | 230 | PASS | PASS | True | False | 1 |
| CONS minus CUT | H2 | 229 | PASS | PASS | False | False | 0 |
| CONS minus CUT | H2 | 230 | PASS | PASS | False | False | 0 |
| CONS+G18 minus CUT | H1-v2 | 229 | PASS | PASS | True | False | 1 |
| CONS+G18 minus CUT | H1-v2 | 230 | PASS | PASS | False | True | -1 |
| CONS+G18 minus CUT | SLW | 229 | PASS | PASS | False | False | 0 |
| CONS+G18 minus CUT | SLW | 230 | PASS | PASS | False | False | 0 |
| CONS+G18 minus CUT | H2 | 229 | PASS | PASS | False | False | 0 |
| CONS+G18 minus CUT | H2 | 230 | PASS | PASS | False | False | 0 |
| CONS+G18 minus CONS | H1-v2 | 229 | PASS | PASS | True | False | 1 |
| CONS+G18 minus CONS | H1-v2 | 230 | PASS | PASS | False | False | 0 |
| CONS+G18 minus CONS | SLW | 229 | PASS | PASS | False | True | -1 |
| CONS+G18 minus CONS | SLW | 230 | PASS | PASS | False | True | -1 |
| CONS+G18 minus CONS | H2 | 229 | PASS | PASS | False | False | 0 |
| CONS+G18 minus CONS | H2 | 230 | PASS | PASS | False | False | 0 |

![H1-v2_229_CONS+G18](../research/results/phase61p/figures/H1-v2_229_CONS+G18.png)

![H1-v2_229_CONS](../research/results/phase61p/figures/H1-v2_229_CONS.png)

![H1-v2_229_CUT](../research/results/phase61p/figures/H1-v2_229_CUT.png)

![H1-v2_230_CONS+G18](../research/results/phase61p/figures/H1-v2_230_CONS+G18.png)

![H1-v2_230_CONS](../research/results/phase61p/figures/H1-v2_230_CONS.png)

![H1-v2_230_CUT](../research/results/phase61p/figures/H1-v2_230_CUT.png)

![H2_229_CONS+G18](../research/results/phase61p/figures/H2_229_CONS+G18.png)

![H2_229_CONS](../research/results/phase61p/figures/H2_229_CONS.png)

![H2_229_CUT](../research/results/phase61p/figures/H2_229_CUT.png)

![H2_230_CONS+G18](../research/results/phase61p/figures/H2_230_CONS+G18.png)

![H2_230_CONS](../research/results/phase61p/figures/H2_230_CONS.png)

![H2_230_CUT](../research/results/phase61p/figures/H2_230_CUT.png)

![SLW_229_CONS+G18](../research/results/phase61p/figures/SLW_229_CONS+G18.png)

![SLW_229_CONS](../research/results/phase61p/figures/SLW_229_CONS.png)

![SLW_229_CUT](../research/results/phase61p/figures/SLW_229_CUT.png)

![SLW_230_CONS+G18](../research/results/phase61p/figures/SLW_230_CONS+G18.png)

![SLW_230_CONS](../research/results/phase61p/figures/SLW_230_CONS.png)

![SLW_230_CUT](../research/results/phase61p/figures/SLW_230_CUT.png)
