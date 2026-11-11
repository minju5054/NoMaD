# Phase58-P

| status | planned | completed | protocol_sha256 | phase57_results_sha256 | phase57_baseline_records |
|---|---|---|---|---|---|
| PREPARED_NOT_RUN | 18 | 0 | 617d7de3b84686e2c10b20c57e3c1eeade14699f61ddf60825cd09dd7df05921 | 37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570 | 0 |

세 방법 모두 Phase53 CUT의 depth 필터·RECOVER·정렬·전속도→0.1→STOP fallback·HMM·1s 만료·공식 도착 판정을 유지하고 ENDPOINT latch를 사용한다. CONS만 후보 순서를 기준 방향과 각도 최소/잔여 길이 최대 순으로 바꾼다. G18은 기존 E2 경계 곡률 조건부 제외 구현을 재사용한다.

좌우 전환은 선택된 NoMaD 후보 끝점 방향의 실제 로봇 heading 기준 부호가 연속 비중립 설치 사이에 바뀐 횟수다. 뒤 선택의 주 집계는 CONS 기준 방향과의 각도 >90°이며, 실제 로봇 heading 대비 >90°도 구분해 표시한다. Graph가 보정된 경우 다음 기준은 보정된 실제 설치 끝점이다.

Phase57 비교는 같은 scene·seed의 이미 발표된 NOMAD_RAW/MIN만 읽는다. 실행 날짜와 정책이 다르며 누락 필드는 —다. 진행 중인 Phase57 로그는 읽거나 변경하지 않는다. 비교 파일 hash는 이 report 생성 시점의 값이다.

| method | scene | n | valid | success | collision | wrong_stop | timeout_without_declaration | box_passage | goal_time_s | stopped_s | left_right_switches | backward_reference_selections | backward_robot_selections | graph_attempts | graph_applied | graph_adoption_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CUT | H1-v2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CUT | SLW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CUT | H2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CUT | ALL | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CONS | H1-v2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CONS | SLW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CONS | H2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CONS | ALL | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CONS+G18 | H1-v2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CONS+G18 | SLW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CONS+G18 | H2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |
| CONS+G18 | ALL | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | 0 | 0 | 0 | — |

| scene | index | method | status | classification | success | collision | wrong_stop | timeout_without_declaration | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | left_right_switches | backward_reference_selections | backward_robot_selections | graph_adoption_rate | graph_solve_p50_s | graph_solve_p95_s | P57_NOMAD_RAW_status | P57_NOMAD_RAW_classification | P57_NOMAD_RAW_success | P57_NOMAD_RAW_collision | P57_NOMAD_RAW_wrong_stop | P57_NOMAD_RAW_timeout_without_declaration | P57_NOMAD_RAW_box_passage | P57_NOMAD_RAW_box_passage_from_spawn_s | P57_NOMAD_RAW_goal_time_s | P57_NOMAD_RAW_stopped_s | P57_NOMAD_RAW_left_right_switches | P57_NOMAD_RAW_backward_reference_selections | P57_NOMAD_RAW_backward_robot_selections | P57_NOMAD_RAW_graph_adoption_rate | P57_NOMAD_RAW_graph_solve_p50_s | P57_NOMAD_RAW_graph_solve_p95_s | P57_MIN_status | P57_MIN_classification | P57_MIN_success | P57_MIN_collision | P57_MIN_wrong_stop | P57_MIN_timeout_without_declaration | P57_MIN_box_passage | P57_MIN_box_passage_from_spawn_s | P57_MIN_goal_time_s | P57_MIN_stopped_s | P57_MIN_left_right_switches | P57_MIN_backward_reference_selections | P57_MIN_backward_robot_selections | P57_MIN_graph_adoption_rate | P57_MIN_graph_solve_p50_s | P57_MIN_graph_solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-v2 | 227 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 227 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 227 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 228 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 228 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 228 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 227 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 227 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 227 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 228 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 228 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 228 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 227 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 227 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 227 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 228 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 228 | CONS | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 228 | CONS+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | NOT_AVAILABLE | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
