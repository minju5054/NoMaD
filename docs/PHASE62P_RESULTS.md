# Phase62-P UG-GOAL — oracle 위치추정 분석용 조건

| status | planned | completed | oracle_analysis_only | protocol_sha256 | phase61_results_sha256 |
|---|---|---|---|---|---|
| PREPARED_NOT_RUN | 6 | 0 | True | 30e2a7ef2573ab8c343f06ce1cfe673b75266ac8de07d51eba1186dd6a1d9dd0 | 53682defa4d3d68ae94212db4514f56c6d4fd51354f7df0989f2e4d03702064c |

Phase61-P의 oracle 위치추정·D075·ENDPOINT latch·1s 만료·PP/SP·EC 제동꼬리·CUT fallback을 유지한다. U-Graph는 Phase55-P의0≤v≤0.3 solver에 r_goal=(p_N−target_xy)/0.3m 한 항만 더했다. 나머지 factor·초기값11개·4process·solver 옵션은 동결이다.

목표는 최근 도착 chunk의 관측 시점 oracle 노드+2(마지막 노드 clamp)이며 다음 chunk 전까지0.5초 주기 재풀이에서도 고정한다. 실제 풀이 시작점은 그때의 실제 pose/v/ω다. Graph XY를 동결 PP/SP로 실행하며 Graph v/ω를 직접 실행하지 않는다.

U 채택률은 실제 설치된 U 해/풀이 시도다. 해 길이는 실제 채택된 U XY 호장(정지 해0 포함)의 중앙값이다. 풀이 pose–목표 거리는 모든 풀이 시점 실제 pose와 고정 목표 노드 사이 거리의 run별 중앙값이며,ALL은 풀이 사건을 합쳐 구한 중앙값이다. Phase61 같은 scene·seed 결과는 기존 발표값을 옆 열에 그대로 둔다.

| phase | method | scene | n | valid | success | collision | wrong_stop | timeout_without_declaration | box_passage | goal_time_s_median | stopped_s_median | box_passage_from_spawn_s_median | u_attempts | u_applied | u_adoption_rate | u_solution_length_median_m | u_goal_distance_at_solve_median_m |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase62 | UG-GOAL | H1-v2 | 0 | 0 | — | — | — | — | — | — | — | — | 0 | 0 | — | — | — |
| Phase62 | UG-GOAL | SLW | 0 | 0 | — | — | — | — | — | — | — | — | 0 | 0 | — | — | — |
| Phase62 | UG-GOAL | H2 | 0 | 0 | — | — | — | — | — | — | — | — | 0 | 0 | — | — | — |
| Phase62 | UG-GOAL | ALL | 0 | 0 | — | — | — | — | — | — | — | — | 0 | 0 | — | — | — |
| Phase61 | CUT | H1-v2 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 59.417 | 10.097 | 37.986 | — | — | — | — | — |
| Phase61 | CUT | SLW | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | 24.833 | — | — | — | — | — | — |
| Phase61 | CUT | H2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | — | 9.9931 | 60.944 | — | — | — | — | — |
| Phase61 | CUT | ALL | 6 | 6 | 1 | 0 | 1 | 4 | 2 | 59.417 | 12.778 | 49.465 | — | — | — | — | — |
| Phase61 | CONS | H1-v2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | 12.778 | — | — | — | — | — | — |
| Phase61 | CONS | SLW | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 61.597 | 8.8958 | — | — | — | — | — | — |
| Phase61 | CONS | H2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | 10 | — | — | — | — | — | — |
| Phase61 | CONS | ALL | 6 | 6 | 2 | 0 | 0 | 4 | 0 | 61.597 | 10.333 | — | — | — | — | — | — |
| Phase61 | CONS+G18 | H1-v2 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 51.361 | 11.958 | 20.097 | — | — | — | — | — |
| Phase61 | CONS+G18 | SLW | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | 15.333 | — | — | — | — | — | — |
| Phase61 | CONS+G18 | H2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | — | 4.6667 | 57.236 | — | — | — | — | — |
| Phase61 | CONS+G18 | ALL | 6 | 6 | 1 | 0 | 1 | 4 | 2 | 51.361 | 8.625 | 38.667 | — | — | — | — | — |

| scene | index | method | status | classification | success | collision | wrong_stop | timeout_without_declaration | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | u_adoption_rate | u_solution_length_median_m | u_goal_distance_at_solve_median_m | P61_CUT_status | P61_CUT_classification | P61_CUT_success | P61_CUT_collision | P61_CUT_wrong_stop | P61_CUT_timeout_without_declaration | P61_CUT_box_passage | P61_CUT_box_passage_from_spawn_s | P61_CUT_goal_time_s | P61_CUT_stopped_s | P61_CONS_status | P61_CONS_classification | P61_CONS_success | P61_CONS_collision | P61_CONS_wrong_stop | P61_CONS_timeout_without_declaration | P61_CONS_box_passage | P61_CONS_box_passage_from_spawn_s | P61_CONS_goal_time_s | P61_CONS_stopped_s | P61_CONS+G18_status | P61_CONS+G18_classification | P61_CONS+G18_success | P61_CONS+G18_collision | P61_CONS+G18_wrong_stop | P61_CONS+G18_timeout_without_declaration | P61_CONS+G18_box_passage | P61_CONS+G18_box_passage_from_spawn_s | P61_CONS+G18_goal_time_s | P61_CONS+G18_stopped_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-v2 | 229 | UG-GOAL | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | PASS | TIMEOUT | False | False | False | True | False | — | — | 14.444 | PASS | TIMEOUT | False | False | False | True | False | — | — | 12.667 | PASS | SUCCESS | True | False | False | False | True | 20.097 | 51.361 | 6.3611 |
| H1-v2 | 230 | UG-GOAL | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | PASS | SUCCESS | True | False | False | False | True | 37.986 | 59.417 | 5.75 | PASS | TIMEOUT | False | False | False | True | False | — | — | 12.889 | PASS | TIMEOUT | False | False | False | True | False | — | — | 17.556 |
| SLW | 229 | UG-GOAL | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | PASS | TIMEOUT | False | False | False | True | False | — | — | 25.556 | PASS | SUCCESS | True | False | False | False | False | — | 57.347 | 7.9028 | PASS | TIMEOUT | False | False | False | True | False | — | — | 10.889 |
| SLW | 230 | UG-GOAL | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | PASS | TIMEOUT | False | False | False | True | False | — | — | 24.111 | PASS | SUCCESS | True | False | False | False | False | — | 65.847 | 9.8889 | PASS | TIMEOUT | False | False | False | True | False | — | — | 19.778 |
| H2 | 229 | UG-GOAL | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | PASS | TIMEOUT | False | False | False | True | False | — | — | 11.111 | PASS | TIMEOUT | False | False | False | True | False | — | — | 10.778 | PASS | WRONG_STOP | False | False | True | False | True | 57.236 | — | 3.7778 |
| H2 | 230 | UG-GOAL | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | PASS | WRONG_STOP | False | False | True | False | True | 60.944 | — | 8.875 | PASS | TIMEOUT | False | False | False | True | False | — | — | 9.2222 | PASS | TIMEOUT | False | False | False | True | False | — | — | 5.5556 |
