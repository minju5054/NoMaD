# Phase58-P

| status | planned | completed | protocol_sha256 | phase57_results_sha256 | phase57_baseline_records |
|---|---|---|---|---|---|
| COMPLETE | 18 | 18 | 617d7de3b84686e2c10b20c57e3c1eeade14699f61ddf60825cd09dd7df05921 | 37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570 | 0 |

세 방법 모두 Phase53 CUT의 depth 필터·RECOVER·정렬·전속도→0.1→STOP fallback·HMM·1s 만료·공식 도착 판정을 유지하고 ENDPOINT latch를 사용한다. CONS만 후보 순서를 기준 방향과 각도 최소/잔여 길이 최대 순으로 바꾼다. G18은 기존 E2 경계 곡률 조건부 제외 구현을 재사용한다.

좌우 전환은 선택된 NoMaD 후보 끝점 방향의 실제 로봇 heading 기준 부호가 연속 비중립 설치 사이에 바뀐 횟수다. 뒤 선택의 주 집계는 CONS 기준 방향과의 각도 >90°이며, 실제 로봇 heading 대비 >90°도 구분해 표시한다. Graph가 보정된 경우 다음 기준은 보정된 실제 설치 끝점이다.

Phase57 비교는 같은 scene·seed의 이미 발표된 NOMAD_RAW/MIN만 읽는다. 실행 날짜와 정책이 다르며 누락 필드는 —다. 진행 중인 Phase57 로그는 읽거나 변경하지 않는다. 비교 파일 hash는 이 report 생성 시점의 값이다.

| method | scene | n | valid | success | collision | wrong_stop | timeout_without_declaration | box_passage | goal_time_s | stopped_s | left_right_switches | backward_reference_selections | backward_robot_selections | graph_attempts | graph_applied | graph_adoption_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CUT | H1-v2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | — | 10.056 | 57 | 42 | 36 | 0 | 0 | — |
| CUT | SLW | 2 | 2 | 0 | 0 | 1 | 1 | 0 | — | 12.667 | 58 | 50 | 28 | 0 | 0 | — |
| CUT | H2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | — | 9.7778 | 62 | 48 | 16 | 0 | 0 | — |
| CUT | ALL | 6 | 6 | 0 | 0 | 3 | 3 | 2 | — | 11.333 | 177 | 140 | 80 | 0 | 0 | — |
| CONS | H1-v2 | 2 | 2 | 1 | 0 | 1 | 0 | 1 | 46.833 | 9.1111 | 37 | 22 | 12 | 0 | 0 | — |
| CONS | SLW | 2 | 2 | 1 | 0 | 0 | 1 | 0 | 44.333 | 12.167 | 44 | 25 | 20 | 0 | 0 | — |
| CONS | H2 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 70.583 | 6.1806 | 51 | 36 | 11 | 0 | 0 | — |
| CONS | ALL | 6 | 6 | 3 | 0 | 1 | 2 | 2 | 46.833 | 7.2917 | 132 | 83 | 43 | 0 | 0 | — |
| CONS+G18 | H1-v2 | 2 | 2 | 0 | 0 | 2 | 0 | 0 | — | 8.1667 | 29 | 17 | 13 | 99 | 70 | 0.70707 |
| CONS+G18 | SLW | 2 | 2 | 1 | 0 | 1 | 0 | 0 | 63.847 | 7.3889 | 34 | 17 | 17 | 109 | 78 | 0.7156 |
| CONS+G18 | H2 | 2 | 2 | 1 | 0 | 1 | 0 | 2 | 84.333 | 7.8889 | 46 | 25 | 17 | 136 | 115 | 0.84559 |
| CONS+G18 | ALL | 6 | 6 | 2 | 0 | 4 | 0 | 2 | 74.09 | 7.8889 | 109 | 59 | 47 | 344 | 263 | 0.76453 |

| scene | index | method | status | classification | success | collision | wrong_stop | timeout_without_declaration | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | left_right_switches | backward_reference_selections | backward_robot_selections | graph_adoption_rate | graph_solve_p50_s | graph_solve_p95_s | P57_NOMAD_RAW_status | P57_NOMAD_RAW_classification | P57_NOMAD_RAW_success | P57_NOMAD_RAW_collision | P57_NOMAD_RAW_wrong_stop | P57_NOMAD_RAW_timeout_without_declaration | P57_NOMAD_RAW_box_passage | P57_NOMAD_RAW_box_passage_from_spawn_s | P57_NOMAD_RAW_goal_time_s | P57_NOMAD_RAW_stopped_s | P57_NOMAD_RAW_left_right_switches | P57_NOMAD_RAW_backward_reference_selections | P57_NOMAD_RAW_backward_robot_selections | P57_NOMAD_RAW_graph_adoption_rate | P57_NOMAD_RAW_graph_solve_p50_s | P57_NOMAD_RAW_graph_solve_p95_s | P57_MIN_status | P57_MIN_classification | P57_MIN_success | P57_MIN_collision | P57_MIN_wrong_stop | P57_MIN_timeout_without_declaration | P57_MIN_box_passage | P57_MIN_box_passage_from_spawn_s | P57_MIN_goal_time_s | P57_MIN_stopped_s | P57_MIN_left_right_switches | P57_MIN_backward_reference_selections | P57_MIN_backward_robot_selections | P57_MIN_graph_adoption_rate | P57_MIN_graph_solve_p50_s | P57_MIN_graph_solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-v2 | 227 | CONS | PASS | WRONG_STOP | False | False | True | False | False | — | — | 6.8889 | 21 | 13 | 7 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 227 | CUT | PASS | WRONG_STOP | False | False | True | False | False | — | — | 2.8889 | 11 | 7 | 0 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 227 | CONS+G18 | PASS | WRONG_STOP | False | False | True | False | False | — | — | 8.2222 | 18 | 10 | 3 | 0.74576 | 0.183 | 0.29435 | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 228 | CONS+G18 | PASS | WRONG_STOP | False | False | True | False | False | — | — | 8.1111 | 11 | 7 | 10 | 0.65 | 0.16356 | 0.28412 | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 228 | CUT | PASS | TIMEOUT | False | False | False | True | True | 35.25 | — | 17.222 | 46 | 35 | 36 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 228 | CONS | PASS | SUCCESS | True | False | False | False | True | 20.917 | 46.833 | 11.333 | 16 | 9 | 5 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 227 | CONS | PASS | SUCCESS | True | False | False | False | False | — | 44.333 | 6.2222 | 18 | 10 | 5 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 227 | CONS+G18 | PASS | WRONG_STOP | False | False | True | False | False | — | — | 7.1111 | 17 | 7 | 13 | 0.71739 | 0.19393 | 0.32801 | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 227 | CUT | PASS | WRONG_STOP | False | False | True | False | False | — | — | 10 | 20 | 12 | 6 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 228 | CONS+G18 | PASS | SUCCESS | True | False | False | False | False | — | 63.847 | 7.6667 | 17 | 10 | 4 | 0.71429 | 0.18103 | 0.30364 | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 228 | CONS | PASS | TIMEOUT | False | False | False | True | False | — | — | 18.111 | 26 | 15 | 15 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 228 | CUT | PASS | TIMEOUT | False | False | False | True | False | — | — | 15.333 | 38 | 38 | 22 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 227 | CUT | PASS | TIMEOUT | False | False | False | True | False | — | — | 12.667 | 38 | 30 | 15 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 227 | CONS+G18 | PASS | WRONG_STOP | False | False | True | False | True | 38.514 | — | 7.3333 | 21 | 7 | 8 | 0.81818 | 0.18529 | 0.26224 | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 227 | CONS | PASS | TIMEOUT | False | False | False | True | False | — | — | 4.6667 | 26 | 23 | 9 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 228 | CUT | PASS | WRONG_STOP | False | False | True | False | True | 31.042 | — | 6.8889 | 24 | 18 | 1 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 228 | CONS | PASS | SUCCESS | True | False | False | False | True | 51.639 | 70.583 | 7.6944 | 25 | 13 | 2 | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 228 | CONS+G18 | PASS | SUCCESS | True | False | False | False | True | 63.319 | 84.333 | 8.4444 | 25 | 18 | 9 | 0.8642 | 0.18661 | 0.25871 | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

![H1-v2_227_CONS+G18](../research/results/phase58p/figures/H1-v2_227_CONS+G18.png)

![H1-v2_227_CONS](../research/results/phase58p/figures/H1-v2_227_CONS.png)

![H1-v2_227_CUT](../research/results/phase58p/figures/H1-v2_227_CUT.png)

![H1-v2_228_CONS+G18](../research/results/phase58p/figures/H1-v2_228_CONS+G18.png)

![H1-v2_228_CONS](../research/results/phase58p/figures/H1-v2_228_CONS.png)

![H1-v2_228_CUT](../research/results/phase58p/figures/H1-v2_228_CUT.png)

![H2_227_CONS+G18](../research/results/phase58p/figures/H2_227_CONS+G18.png)

![H2_227_CONS](../research/results/phase58p/figures/H2_227_CONS.png)

![H2_227_CUT](../research/results/phase58p/figures/H2_227_CUT.png)

![H2_228_CONS+G18](../research/results/phase58p/figures/H2_228_CONS+G18.png)

![H2_228_CONS](../research/results/phase58p/figures/H2_228_CONS.png)

![H2_228_CUT](../research/results/phase58p/figures/H2_228_CUT.png)

![SLW_227_CONS+G18](../research/results/phase58p/figures/SLW_227_CONS+G18.png)

![SLW_227_CONS](../research/results/phase58p/figures/SLW_227_CONS.png)

![SLW_227_CUT](../research/results/phase58p/figures/SLW_227_CUT.png)

![SLW_228_CONS+G18](../research/results/phase58p/figures/SLW_228_CONS+G18.png)

![SLW_228_CONS](../research/results/phase58p/figures/SLW_228_CONS.png)

![SLW_228_CUT](../research/results/phase58p/figures/SLW_228_CUT.png)
