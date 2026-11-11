# Phase55-P U-Graph 폐루프 파일럿

| status | planned | completed | protocol_sha256 |
|---|---|---|---|
| COMPLETE | 24 | 24 | 6ebbc5ead8a42acac1eecd16eb1e609eaefed9bc5d9697e5abe41d8f993cd61b |

PP+SP가 Graph XY를 추종하며 Graph v/ω 계획을 직접 실행하지 않는다. 결과 없음은 —로 표시한다. 역사 비교는 다른 날짜의 같은 scene·조건·seed이며 H1-v2 비교군은 없다. Phase53 CUT은 1s 만료+EC-tail, Phase52 CUT-HOLD는 HOLD+기존 EC이므로 실행 정책 차이가 있다.

| condition | completed | success | collision | wrong_stop | timeout_without_declaration | box_passage | goal_time_s_median | stopped_s_median | align_rotate_s_median | graph_adoption_rate_median | graph_solve_p50_s_median | graph_solve_p95_s_median | left_right_switches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D075 | 12 | 5 | 1 | 5 | 1 | 5 | 43.458 | 6.7222 | 0 | 1 | 0.23322 | 0.28539 | 264 |
| D150 | 12 | 2 | 1 | 3 | 6 | 2 | 57.681 | 15.667 | 0 | 1 | 0.24106 | 0.29066 | 218 |

| scene | condition | seed | status | U_classification | U_success | U_collision | U_wrong_stop | U_timeout_without_declaration | U_box_passage | U_box_passage_from_spawn_s | U_goal_time_s | U_stopped_s | U_align_rotate_s | U_graph_adoption_rate | U_graph_solve_p50_s | U_graph_solve_p95_s | U_graph_left_right_switches | U_all_path_left_right_switches | Phase53_CUT_classification | Phase53_CUT_success | Phase53_CUT_collision | Phase53_CUT_wrong_stop | Phase53_CUT_timeout_without_declaration | Phase53_CUT_box_passage | Phase53_CUT_box_passage_from_spawn_s | Phase53_CUT_goal_time_s | Phase53_CUT_stopped_s | Phase53_CUT_align_rotate_s | Phase53_CUT_graph_adoption_rate | Phase53_CUT_graph_solve_p50_s | Phase53_CUT_graph_solve_p95_s | Phase53_CUT_graph_left_right_switches | Phase53_CUT_all_path_left_right_switches | Phase52_CUT-HOLD_classification | Phase52_CUT-HOLD_success | Phase52_CUT-HOLD_collision | Phase52_CUT-HOLD_wrong_stop | Phase52_CUT-HOLD_timeout_without_declaration | Phase52_CUT-HOLD_box_passage | Phase52_CUT-HOLD_box_passage_from_spawn_s | Phase52_CUT-HOLD_goal_time_s | Phase52_CUT-HOLD_stopped_s | Phase52_CUT-HOLD_align_rotate_s | Phase52_CUT-HOLD_graph_adoption_rate | Phase52_CUT-HOLD_graph_solve_p50_s | Phase52_CUT-HOLD_graph_solve_p95_s | Phase52_CUT-HOLD_graph_left_right_switches | Phase52_CUT-HOLD_all_path_left_right_switches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW | D075 | 221 | PASS | COLLISION | False | True | False | False | False | — | — | 6.2222 | 0 | 0.96396 | 0.2409 | 0.32034 | 16 | 16 | WRONG_STOP | False | False | True | False | False | — | — | 54.222 | 19.222 | — | — | — | — | — | TIMEOUT | False | False | False | True | False | — | — | 22.333 | 12.667 | — | — | — | — | — |
| LC | D075 | 221 | PASS | WRONG_STOP | False | False | True | False | False | — | — | 3.5556 | 0 | 1 | 0.23153 | 0.26706 | 15 | 15 | SUCCESS | True | False | False | False | False | — | 29.583 | 3.2222 | 0 | — | — | — | — | — | SUCCESS | True | False | False | False | False | — | 28.083 | 3.2222 | 0.22222 | — | — | — | — | — |
| L2 | D075 | 221 | PASS | SUCCESS | True | False | False | False | True | 17.236 | 63.361 | 4.5833 | 0 | 1 | 0.23708 | 0.28693 | 26 | 26 | SUCCESS | True | False | False | False | True | 10.681 | 41.583 | 3.7778 | 0.77778 | — | — | — | — | — | SUCCESS | True | False | False | False | True | 10.528 | 37.833 | 3.6667 | 0.66667 | — | — | — | — | — |
| H1 | D075 | 221 | PASS | SUCCESS | True | False | False | False | True | 14.069 | 43.458 | 5.6806 | 0 | 1 | 0.23205 | 0.28771 | 18 | 18 | TIMEOUT | False | False | False | True | False | — | — | 21 | 7.5556 | — | — | — | — | — | WRONG_STOP | False | False | True | False | True | 7.3333 | — | 3.3333 | 0.33333 | — | — | — | — | — |
| H2 | D075 | 221 | PASS | WRONG_STOP | False | False | True | False | False | — | — | 15.111 | 0 | 0.88189 | 0.24441 | 0.60929 | 17 | 17 | SUCCESS | True | False | False | False | True | 66.875 | 83.583 | 6 | 2.5556 | — | — | — | — | — | TIMEOUT | False | False | False | True | False | — | — | 6.6667 | 3.4444 | — | — | — | — | — |
| H1-v2 | D075 | 221 | PASS | SUCCESS | True | False | False | False | True | 21.153 | 56.903 | 8.125 | 0 | 0.96835 | 0.23439 | 0.30107 | 21 | 21 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | D075 | 222 | PASS | WRONG_STOP | False | False | True | False | False | — | — | 9.1111 | 0 | 1 | 0.23586 | 0.28385 | 18 | 18 | SUCCESS | True | False | False | False | False | — | 42.833 | 7.7778 | 2.4444 | — | — | — | — | — | TIMEOUT | False | False | False | True | False | — | — | 21.111 | 16.111 | — | — | — | — | — |
| LC | D075 | 222 | PASS | SUCCESS | True | False | False | False | False | — | 34.889 | 3.7778 | 0 | 1 | 0.22891 | 0.27554 | 14 | 14 | SUCCESS | True | False | False | False | False | — | 34.833 | 5.1111 | 1.7778 | — | — | — | — | — | SUCCESS | True | False | False | False | False | — | 30.833 | 4 | 0.88889 | — | — | — | — | — |
| L2 | D075 | 222 | PASS | WRONG_STOP | False | False | True | False | True | 26.361 | — | 7.2222 | 0 | 1 | 0.2372 | 0.40728 | 36 | 36 | WRONG_STOP | False | False | True | False | False | — | — | 16.889 | 8.3333 | — | — | — | — | — | TIMEOUT | False | False | False | True | False | — | — | 10 | 6.3333 | — | — | — | — | — |
| H1 | D075 | 222 | PASS | SUCCESS | True | False | False | False | True | 11.056 | 38.903 | 4.4583 | 0 | 1 | 0.23143 | 0.26283 | 25 | 25 | SUCCESS | True | False | False | False | True | 6.9306 | 32.583 | 4.4444 | 1.2222 | — | — | — | — | — | SUCCESS | True | False | False | False | True | 6.1806 | 27.833 | 3.3333 | 0.33333 | — | — | — | — | — |
| H2 | D075 | 222 | PASS | TIMEOUT | False | False | False | True | False | — | — | 10.111 | 0 | 0.98062 | 0.23178 | 0.27541 | 40 | 40 | SUCCESS | True | False | False | False | True | 57.417 | 77.083 | 6.8889 | 3.1111 | — | — | — | — | — | WRONG_STOP | False | False | True | False | True | 27.556 | — | 5 | 1.7778 | — | — | — | — | — |
| H1-v2 | D075 | 222 | PASS | WRONG_STOP | False | False | True | False | False | — | — | 19.569 | 0 | 1 | 0.2318 | 0.27714 | 18 | 18 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | D150 | 221 | PASS | TIMEOUT | False | False | False | True | False | — | — | 22.111 | 0 | 0.96226 | 0.2423 | 0.38615 | 22 | 22 | SUCCESS | True | False | False | False | False | — | 88.833 | 38.5 | 7 | — | — | — | — | — | TIMEOUT | False | False | False | True | False | — | — | 24.778 | 16.556 | — | — | — | — | — |
| LC | D150 | 221 | PASS | WRONG_STOP | False | False | True | False | False | — | — | 16.444 | 0 | 0.97826 | 0.23578 | 0.28015 | 11 | 11 | SUCCESS | True | False | False | False | False | — | 48.833 | 16.167 | 3 | — | — | — | — | — | SUCCESS | True | False | False | False | False | — | 35.083 | 7.5556 | 3.5556 | — | — | — | — | — |
| L2 | D150 | 221 | PASS | TIMEOUT | False | False | False | True | False | — | — | 15.889 | 0 | 1 | 0.24122 | 0.28899 | 27 | 27 | SUCCESS | True | False | False | False | True | 32.458 | 82.083 | 31.194 | 4 | — | — | — | — | — | TIMEOUT | False | False | False | True | True | 76.514 | — | 69 | 5.3333 | — | — | — | — | — |
| H1 | D150 | 221 | PASS | SUCCESS | True | False | False | False | True | 18.139 | 63.681 | 12.569 | 0 | 1 | 0.2409 | 0.29234 | 13 | 13 | WRONG_STOP | False | False | True | False | True | 19.389 | — | 19 | 1 | — | — | — | — | — | SUCCESS | True | False | False | False | True | 24.847 | 59.583 | 21.333 | 16.556 | — | — | — | — | — |
| H2 | D150 | 221 | PASS | TIMEOUT | False | False | False | True | False | — | — | 19.778 | 0 | 0.98113 | 0.2403 | 0.43523 | 20 | 20 | TIMEOUT | False | False | False | True | False | — | — | 29.333 | 5 | — | — | — | — | — | TIMEOUT | False | False | False | True | False | — | — | 28.444 | 23 | — | — | — | — | — |
| H1-v2 | D150 | 221 | PASS | WRONG_STOP | False | False | True | False | False | — | — | 17.778 | 0 | 1 | 0.24459 | 0.34785 | 13 | 13 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | D150 | 222 | PASS | COLLISION | False | True | False | False | False | — | — | 23.778 | 0 | 0.99359 | 0.24019 | 0.29567 | 13 | 13 | TIMEOUT | False | False | False | True | False | — | — | 44.222 | 8.8889 | — | — | — | — | — | TIMEOUT | False | False | False | True | False | — | — | 24.889 | 17.778 | — | — | — | — | — |
| LC | D150 | 222 | PASS | SUCCESS | True | False | False | False | False | — | 51.681 | 13.792 | 0 | 1 | 0.23266 | 0.28586 | 14 | 14 | SUCCESS | True | False | False | False | False | — | 50.833 | 17.833 | 3 | — | — | — | — | — | WRONG_STOP | False | False | True | False | False | — | — | 26.75 | 21.306 | — | — | — | — | — |
| L2 | D150 | 222 | PASS | TIMEOUT | False | False | False | True | False | — | — | 11.111 | 0 | 1 | 0.24368 | 0.28241 | 27 | 27 | TIMEOUT | False | False | False | True | True | 66.542 | — | 35.556 | 4 | — | — | — | — | — | SUCCESS | True | False | False | False | True | 49.222 | 89.333 | 25.667 | 20.333 | — | — | — | — | — |
| H1 | D150 | 222 | PASS | WRONG_STOP | False | False | True | False | True | 17.361 | — | 15.125 | 0 | 1 | 0.24084 | 0.28506 | 16 | 16 | SUCCESS | True | False | False | False | True | 9.8333 | 52.333 | 16.444 | 2 | — | — | — | — | — | WRONG_STOP | False | False | True | False | False | — | — | 8.8611 | 4.75 | — | — | — | — | — |
| H2 | D150 | 222 | PASS | TIMEOUT | False | False | False | True | False | — | — | 15.444 | 0 | 1 | 0.24299 | 0.30843 | 23 | 23 | TIMEOUT | False | False | False | True | False | — | — | 40.556 | 6 | — | — | — | — | — | SUCCESS | True | False | False | False | True | 52.319 | 80.333 | 26.111 | 21 | — | — | — | — | — |
| H1-v2 | D150 | 222 | PASS | TIMEOUT | False | False | False | True | False | — | — | 13 | 0 | 1 | 0.24171 | 0.28549 | 19 | 19 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

| scene | seed | state | seconds |
|---|---|---|---|
| H1-v2_D075 | 221 | INITIAL_CHUNK_WAIT | 2.8889 |
| H1-v2_D075 | 221 | NORMAL | 47.333 |
| H1-v2_D075 | 221 | ENDPOINT | 2.6667 |
| H1-v2_D075 | 221 | STOP_WAIT | 2.0139 |
| H1-v2_D075 | 221 | RECOVER_ROTATE | 1.7778 |
| H1-v2_D075 | 221 | WAIT_FRESH | 0.22222 |
| H1-v2_D075 | 222 | INITIAL_CHUNK_WAIT | 2.8889 |
| H1-v2_D075 | 222 | NORMAL | 33.111 |
| H1-v2_D075 | 222 | ENDPOINT | 9.8889 |
| H1-v2_D075 | 222 | STOP_WAIT | 8.0139 |
| H1-v2_D150 | 221 | INITIAL_CHUNK_WAIT | 3.6667 |
| H1-v2_D150 | 221 | NORMAL | 61.681 |
| H1-v2_D150 | 221 | ENDPOINT | 8.4444 |
| H1-v2_D150 | 221 | STOP_WAIT | 7.8889 |
| H1-v2_D150 | 222 | INITIAL_CHUNK_WAIT | 3.6667 |
| H1-v2_D150 | 222 | NORMAL | 76.444 |
| H1-v2_D150 | 222 | ENDPOINT | 3.6667 |
| H1-v2_D150 | 222 | STOP_WAIT | 6.2222 |
| H1_D075 | 221 | INITIAL_CHUNK_WAIT | 2.8889 |
| H1_D075 | 221 | NORMAL | 36.778 |
| H1_D075 | 221 | ENDPOINT | 3.1111 |
| H1_D075 | 221 | STOP_WAIT | 0.68056 |
| H1_D075 | 222 | INITIAL_CHUNK_WAIT | 2.8889 |
| H1_D075 | 222 | NORMAL | 33.667 |
| H1_D075 | 222 | ENDPOINT | 1.6667 |
| H1_D075 | 222 | STOP_WAIT | 0.68056 |
| H1_D150 | 221 | INITIAL_CHUNK_WAIT | 3.6667 |
| H1_D150 | 221 | NORMAL | 50.778 |
| H1_D150 | 221 | ENDPOINT | 5.5556 |
| H1_D150 | 221 | STOP_WAIT | 3.6806 |
| H1_D150 | 222 | INITIAL_CHUNK_WAIT | 3.6667 |
| H1_D150 | 222 | NORMAL | 42 |
| H1_D150 | 222 | ENDPOINT | 7.4583 |
| H1_D150 | 222 | STOP_WAIT | 5.1111 |
| H2_D075 | 221 | INITIAL_CHUNK_WAIT | 2.8889 |
| H2_D075 | 221 | NORMAL | 29.792 |
| H2_D075 | 221 | ENDPOINT | 3.8889 |
| H2_D075 | 221 | STOP_WAIT | 2.7778 |
| H2_D075 | 221 | RECOVER_ROTATE | 3.5556 |
| H2_D075 | 221 | WAIT_FRESH | 2 |
| H2_D075 | 222 | INITIAL_CHUNK_WAIT | 2.8889 |
| H2_D075 | 222 | NORMAL | 79.444 |
| H2_D075 | 222 | ENDPOINT | 3.8889 |
| H2_D075 | 222 | STOP_WAIT | 1.7778 |
| H2_D075 | 222 | RECOVER_ROTATE | 1.7778 |
| H2_D075 | 222 | WAIT_FRESH | 0.22222 |
| H2_D150 | 221 | INITIAL_CHUNK_WAIT | 3.6667 |
| H2_D150 | 221 | NORMAL | 68.667 |
| H2_D150 | 221 | ENDPOINT | 8.1111 |
| H2_D150 | 221 | STOP_WAIT | 7.5556 |
| H2_D150 | 221 | RECOVER_ROTATE | 1.7778 |
| H2_D150 | 221 | WAIT_FRESH | 0.22222 |
| H2_D150 | 222 | INITIAL_CHUNK_WAIT | 3.6667 |
| H2_D150 | 222 | NORMAL | 72.889 |
| H2_D150 | 222 | ENDPOINT | 9.6667 |
| H2_D150 | 222 | STOP_WAIT | 3.7778 |
| L2_D075 | 221 | INITIAL_CHUNK_WAIT | 2.8889 |
| L2_D075 | 221 | NORMAL | 58.111 |
| L2_D075 | 221 | ENDPOINT | 2.25 |
| L2_D075 | 221 | STOP_WAIT | 0.11111 |
| L2_D075 | 222 | INITIAL_CHUNK_WAIT | 2.8889 |
| L2_D075 | 222 | NORMAL | 67.792 |
| L2_D075 | 222 | ENDPOINT | 3.7778 |
| L2_D075 | 222 | STOP_WAIT | 0.88889 |
| L2_D150 | 221 | INITIAL_CHUNK_WAIT | 3.6667 |
| L2_D150 | 221 | NORMAL | 73 |
| L2_D150 | 221 | ENDPOINT | 8.4444 |
| L2_D150 | 221 | STOP_WAIT | 4.8889 |
| L2_D150 | 222 | INITIAL_CHUNK_WAIT | 3.6667 |
| L2_D150 | 222 | NORMAL | 78.333 |
| L2_D150 | 222 | ENDPOINT | 5.7778 |
| L2_D150 | 222 | STOP_WAIT | 2.2222 |
| LC_D075 | 221 | INITIAL_CHUNK_WAIT | 2.8889 |
| LC_D075 | 221 | NORMAL | 32.236 |
| LC_D075 | 221 | ENDPOINT | 0.77778 |
| LC_D075 | 222 | INITIAL_CHUNK_WAIT | 3 |
| LC_D075 | 222 | NORMAL | 30.222 |
| LC_D075 | 222 | ENDPOINT | 1.5556 |
| LC_D075 | 222 | STOP_WAIT | 0.11111 |
| LC_D150 | 221 | INITIAL_CHUNK_WAIT | 3.6667 |
| LC_D150 | 221 | NORMAL | 42.569 |
| LC_D150 | 221 | ENDPOINT | 6.3333 |
| LC_D150 | 221 | STOP_WAIT | 5.7778 |
| LC_D150 | 221 | RECOVER_ROTATE | 1.7778 |
| LC_D150 | 221 | WAIT_FRESH | 0.11111 |
| LC_D150 | 222 | INITIAL_CHUNK_WAIT | 3.6667 |
| LC_D150 | 222 | NORMAL | 36.333 |
| LC_D150 | 222 | ENDPOINT | 5.4444 |
| LC_D150 | 222 | STOP_WAIT | 6.2361 |
| SLW_D075 | 221 | INITIAL_CHUNK_WAIT | 2.8889 |
| SLW_D075 | 221 | NORMAL | 32.222 |
| SLW_D075 | 221 | ENDPOINT | 3.2222 |
| SLW_D075 | 221 | STOP_WAIT | 1.0694 |
| SLW_D075 | 222 | INITIAL_CHUNK_WAIT | 2.7778 |
| SLW_D075 | 222 | NORMAL | 41.569 |
| SLW_D075 | 222 | ENDPOINT | 4.7778 |
| SLW_D075 | 222 | STOP_WAIT | 2.2222 |
| SLW_D150 | 221 | INITIAL_CHUNK_WAIT | 3.6667 |
| SLW_D150 | 221 | NORMAL | 67 |
| SLW_D150 | 221 | ENDPOINT | 7.2222 |
| SLW_D150 | 221 | STOP_WAIT | 8.3333 |
| SLW_D150 | 221 | RECOVER_ROTATE | 3.5556 |
| SLW_D150 | 221 | WAIT_FRESH | 0.22222 |
| SLW_D150 | 222 | INITIAL_CHUNK_WAIT | 3.6667 |
| SLW_D150 | 222 | NORMAL | 42.778 |
| SLW_D150 | 222 | ENDPOINT | 12.667 |
| SLW_D150 | 222 | STOP_WAIT | 9.1389 |
