# Phase60-P SIGN 전이 파일럿

| status | planned | completed | protocol_sha256 | model_sha256 | sigma2 | baseline_hashes | baseline_enriched_from_saved_logs |
|---|---|---|---|---|---|---|---|
| COMPLETE | 18 | 18 | 96c16d63403bc8ae0a32291b5550f72ba250f5212346066356c6159925ee810c | f806c6236bfdf0470faca8578fcb9ab749770d859856de411d4d341f0417c8ca | 0.14923 | {'Phase58': 'c56ee2f1d6800c9adb302650a50dc6e2e4e8058ce8fbe889397e45bce590201a', 'Phase59': '4edfd598d050a1634ec2a3387054a742e7f784dd3d1d5eb0579c014fd06fca8e'} | True |

동결 보정 파일의 σ²=0.14923311275040188를 직접 읽고 model_sha256 `f806c6236bfdf0470faca8578fcb9ab749770d859856de411d4d341f0417c8ca` 일치를 검사했다. 보정값 재추정·반올림 대체는 하지 않는다. 전이는 LOC_V2 Filter(SIGN) 그대로이며 정수 node offset에서 Gaussian 밀도를 평가해 전역 노드 범위로 행 정규화한다.

Phase59-P와 방법·장면·jitter·seed·블록 순서·실행기·EC·Graph·latch·만료·방출·후보 창·부목표·도착 조건이 같다. 바뀐 것은 전이뿐이다. 직전 추론 MAP 노드의 동결 인접차 접선에 observation-tick odometry XY 증분을 투영한다. Topomap 노드 pose와 오도메트리가 같은 좌표계라는 가정이 필요하다. OBS/MEM은 쓰지 않는다.

성공은 기존 선언 시 거리≤0.5m AND 충돌 없음이다. 실제 목표0.7m 도달은 선언과 무관한72Hz 저장 거리 최소≤0.7m이며,미선언은 그 조건을 만족하고 종료까지 선언이 없는 run이다. 0.5m 기준 미선언도 별도 열로 유지한다. 거짓 목표 판정은 추론 MAP==goal AND 관측 시점 true_node<goal−2의 건수로,거리 기준 잘못된 도착과 구별한다.

선언 시 추정 노드는 선언 로그의 closest이고 실제 노드는 선언 순간 실제 pose에 최근접인 Topomap 노드다. Phase58-P·59-P 같은(scene,seed,method)를 옆 열에 둔다. 보조 항목은 report 실행 시 저장 로그에서만 읽으며 기존 결과를 수정하지 않는다. 준비 시점에는 미계산 비교 항목을 —로 둔다.

| phase | method | scene | n | valid | success | collision | wrong_stop | timeout_without_declaration | reached_goal_0p7 | arrived_without_declaration | arrived_0p5_without_declaration | false_goal_count | false_goal_runs | stop_distance_m_median | goal_time_s_median | stopped_s_median |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase60 SIGN | CUT | H1-v2 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0.2443 | 60.583 | 9.0694 |
| Phase60 SIGN | CUT | SLW | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | — | — | 20.556 |
| Phase60 SIGN | CUT | H2 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0.36399 | 73.583 | 9.1667 |
| Phase60 SIGN | CUT | ALL | 6 | 6 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0.28682 | 68.083 | 10.569 |
| Phase60 SIGN | CONS | H1-v2 | 2 | 2 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 2.786 | — | 9.3889 |
| Phase60 SIGN | CONS | SLW | 2 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 1 | 1.9712 | — | 10.056 |
| Phase60 SIGN | CONS | H2 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0.44313 | 44.833 | 6.0278 |
| Phase60 SIGN | CONS | ALL | 6 | 6 | 1 | 0 | 3 | 2 | 1 | 0 | 0 | 2 | 2 | 1.7645 | 44.833 | 7.7222 |
| Phase60 SIGN | CONS+G18 | H1-v2 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0.26054 | 54.847 | 5.7569 |
| Phase60 SIGN | CONS+G18 | SLW | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0.39702 | 64.611 | 29.583 |
| Phase60 SIGN | CONS+G18 | H2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | — | — | 9.4444 |
| Phase60 SIGN | CONS+G18 | ALL | 6 | 6 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0.31084 | 55.847 | 10.062 |
| Phase58 HMM0 | CUT | H1-v2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2.568 | — | 10.056 |
| Phase58 HMM0 | CUT | SLW | 2 | 2 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 2.9394 | — | 12.667 |
| Phase58 HMM0 | CUT | H2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0.50212 | — | 9.7778 |
| Phase58 HMM0 | CUT | ALL | 6 | 6 | 0 | 0 | 3 | 3 | 2 | 1 | 1 | 2 | 2 | 2.568 | — | 11.333 |
| Phase58 HMM0 | CONS | H1-v2 | 2 | 2 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 1 | 2.1617 | 46.833 | 9.1111 |
| Phase58 HMM0 | CONS | SLW | 2 | 2 | 1 | 0 | 0 | 1 | 2 | 1 | 0 | 0 | 0 | 0.42198 | 44.333 | 12.167 |
| Phase58 HMM0 | CONS | H2 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0.42165 | 70.583 | 6.1806 |
| Phase58 HMM0 | CONS | ALL | 6 | 6 | 3 | 0 | 1 | 2 | 4 | 1 | 0 | 1 | 1 | 0.42182 | 46.833 | 7.2917 |
| Phase58 HMM0 | CONS+G18 | H1-v2 | 2 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2 | 3.9587 | — | 8.1667 |
| Phase58 HMM0 | CONS+G18 | SLW | 2 | 2 | 1 | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0.4848 | 63.847 | 7.3889 |
| Phase58 HMM0 | CONS+G18 | H2 | 2 | 2 | 1 | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0.58162 | 84.333 | 7.8889 |
| Phase58 HMM0 | CONS+G18 | ALL | 6 | 6 | 2 | 0 | 4 | 0 | 4 | 0 | 0 | 2 | 2 | 0.61058 | 74.09 | 7.8889 |
| Phase59 NET | CUT | H1-v2 | 2 | 2 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 1 | 2.4979 | 45.333 | 9.8611 |
| Phase59 NET | CUT | SLW | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0.41605 | 55.333 | 11.222 |
| Phase59 NET | CUT | H2 | 2 | 2 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0.68741 | 81.333 | 7.5556 |
| Phase59 NET | CUT | ALL | 6 | 6 | 4 | 0 | 2 | 0 | 4 | 0 | 0 | 1 | 1 | 0.41605 | 55.333 | 8.5 |
| Phase59 NET | CONS | H1-v2 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0.42854 | 51.833 | 7.25 |
| Phase59 NET | CONS | SLW | 2 | 2 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 1 | 1.7569 | 56.417 | 16.042 |
| Phase59 NET | CONS | H2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0.71532 | — | 6.7222 |
| Phase59 NET | CONS | ALL | 6 | 6 | 3 | 0 | 2 | 1 | 4 | 0 | 0 | 1 | 1 | 0.47562 | 53.833 | 8.3333 |
| Phase59 NET | CONS+G18 | H1-v2 | 2 | 2 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 4.4312 | — | 6.6667 |
| Phase59 NET | CONS+G18 | SLW | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0.34627 | 71.958 | 13.667 |
| Phase59 NET | CONS+G18 | H2 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0.44053 | 83.403 | 6.4236 |
| Phase59 NET | CONS+G18 | ALL | 6 | 6 | 3 | 0 | 1 | 2 | 4 | 1 | 1 | 1 | 1 | 0.39363 | 83.403 | 7.7569 |

| scene | index | method | status | classification | success | collision | wrong_stop | timeout_without_declaration | stop_distance_m | declaration_estimated_node | declaration_true_node | goal_node | reached_goal_0p7 | arrived_without_declaration | reached_goal_0p5 | arrived_0p5_without_declaration | false_goal_count | minimum_actual_goal_distance_m | goal_time_s | stopped_s | box_passage | graph_adoption_rate | Phase58_status | Phase58_classification | Phase58_success | Phase58_collision | Phase58_wrong_stop | Phase58_timeout_without_declaration | Phase58_stop_distance_m | Phase58_declaration_estimated_node | Phase58_declaration_true_node | Phase58_goal_node | Phase58_reached_goal_0p7 | Phase58_arrived_without_declaration | Phase58_reached_goal_0p5 | Phase58_arrived_0p5_without_declaration | Phase58_false_goal_count | Phase58_minimum_actual_goal_distance_m | Phase58_goal_time_s | Phase58_stopped_s | Phase58_box_passage | Phase58_graph_adoption_rate | Phase59_status | Phase59_classification | Phase59_success | Phase59_collision | Phase59_wrong_stop | Phase59_timeout_without_declaration | Phase59_stop_distance_m | Phase59_declaration_estimated_node | Phase59_declaration_true_node | Phase59_goal_node | Phase59_reached_goal_0p7 | Phase59_arrived_without_declaration | Phase59_reached_goal_0p5 | Phase59_arrived_0p5_without_declaration | Phase59_false_goal_count | Phase59_minimum_actual_goal_distance_m | Phase59_goal_time_s | Phase59_stopped_s | Phase59_box_passage | Phase59_graph_adoption_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-v2 | 227 | CONS | PASS | TIMEOUT | False | False | False | True | — | — | — | 14 | False | False | False | False | 0 | 2.4894 | — | 13.111 | False | — | PASS | WRONG_STOP | False | False | True | False | 4.0294 | 14 | 2 | 14 | False | False | False | False | 1 | 2.4835 | — | 6.8889 | False | — | PASS | SUCCESS | True | False | False | False | 0.38146 | 14 | 13 | 14 | True | False | True | False | 0 | 0.38146 | 49.833 | 5.8333 | True | — |
| H1-v2 | 227 | CUT | PASS | TIMEOUT | False | False | False | True | — | — | — | 14 | False | False | False | False | 0 | 1.9607 | — | 8.7778 | False | — | PASS | WRONG_STOP | False | False | True | False | 2.568 | 14 | 8 | 14 | False | False | False | False | 1 | 2.5428 | — | 2.8889 | False | — | PASS | SUCCESS | True | False | False | False | 0.22702 | 14 | 14 | 14 | True | False | True | False | 0 | 0.22702 | 45.333 | 8.1111 | True | — |
| H1-v2 | 227 | CONS+G18 | PASS | SUCCESS | True | False | False | False | 0.31084 | 14 | 14 | 14 | True | False | True | False | 0 | 0.31084 | 55.847 | 6.8472 | True | 0.84615 | PASS | WRONG_STOP | False | False | True | False | 4.1742 | 14 | 1 | 14 | False | False | False | False | 1 | 2.4474 | — | 8.2222 | False | 0.74576 | PASS | WRONG_STOP | False | False | True | False | 4.4312 | 14 | 1 | 14 | False | False | False | False | 1 | 2.4642 | — | 5 | False | 0.80702 |
| H1-v2 | 228 | CONS+G18 | PASS | SUCCESS | True | False | False | False | 0.21024 | 14 | 14 | 14 | True | False | True | False | 0 | 0.21024 | 53.847 | 4.6667 | True | 0.82353 | PASS | WRONG_STOP | False | False | True | False | 3.7431 | 14 | 3 | 14 | False | False | False | False | 1 | 2.5134 | — | 8.1111 | False | 0.65 | PASS | TIMEOUT | False | False | False | True | — | — | — | 14 | True | True | True | True | 0 | 0.025123 | — | 8.3333 | True | 0.77528 |
| H1-v2 | 228 | CUT | PASS | SUCCESS | True | False | False | False | 0.2443 | 14 | 14 | 14 | True | False | True | False | 0 | 0.2443 | 60.583 | 9.3611 | True | — | PASS | TIMEOUT | False | False | False | True | — | — | — | 14 | True | True | True | True | 0 | 0.1312 | — | 17.222 | True | — | PASS | WRONG_STOP | False | False | True | False | 4.7688 | 14 | 0 | 14 | False | False | False | False | 1 | 2.4883 | — | 11.611 | False | — |
| H1-v2 | 228 | CONS | PASS | WRONG_STOP | False | False | True | False | 2.786 | 14 | 8 | 14 | False | False | False | False | 1 | 2.4788 | — | 5.6667 | False | — | PASS | SUCCESS | True | False | False | False | 0.29399 | 14 | 14 | 14 | True | False | True | False | 0 | 0.29399 | 46.833 | 11.333 | True | — | PASS | SUCCESS | True | False | False | False | 0.47562 | 14 | 13 | 14 | True | False | True | False | 0 | 0.47562 | 53.833 | 8.6667 | True | — |
| SLW | 227 | CONS | PASS | WRONG_STOP | False | False | True | False | 0.74295 | 15 | 14 | 15 | False | False | False | False | 0 | 0.74295 | — | 7.3333 | False | — | PASS | SUCCESS | True | False | False | False | 0.42198 | 15 | 15 | 15 | True | False | True | False | 0 | 0.42198 | 44.333 | 6.2222 | False | — | PASS | WRONG_STOP | False | False | True | False | 3.0937 | 15 | 5 | 15 | False | False | False | False | 1 | 2.693 | — | 22.444 | False | — |
| SLW | 227 | CONS+G18 | PASS | SUCCESS | True | False | False | False | 0.39702 | 15 | 15 | 15 | True | False | True | False | 0 | 0.39702 | 64.611 | 13.278 | False | 0.61905 | PASS | WRONG_STOP | False | False | True | False | 0.52625 | 15 | 15 | 15 | True | False | False | False | 0 | 0.52625 | — | 7.1111 | False | 0.71739 | PASS | SUCCESS | True | False | False | False | 0.34581 | 15 | 15 | 15 | True | False | True | False | 0 | 0.34581 | 58.333 | 10.667 | False | 0.54386 |
| SLW | 227 | CUT | PASS | TIMEOUT | False | False | False | True | — | — | — | 15 | False | False | False | False | 0 | 2.6239 | — | 14.778 | False | — | PASS | WRONG_STOP | False | False | True | False | 2.9394 | 15 | 5 | 15 | False | False | False | False | 1 | 2.3925 | — | 10 | False | — | PASS | SUCCESS | True | False | False | False | 0.35908 | 15 | 15 | 15 | True | False | True | False | 0 | 0.35908 | 52.833 | 8.2222 | False | — |
| SLW | 228 | CONS+G18 | PASS | TIMEOUT | False | False | False | True | — | — | — | 15 | False | False | False | False | 0 | 2.7134 | — | 45.889 | False | 0.34177 | PASS | SUCCESS | True | False | False | False | 0.44336 | 15 | 15 | 15 | True | False | True | False | 0 | 0.44336 | 63.847 | 7.6667 | False | 0.71429 | PASS | SUCCESS | True | False | False | False | 0.34674 | 15 | 15 | 15 | True | False | True | False | 0 | 0.34674 | 85.583 | 16.667 | False | 0.61176 |
| SLW | 228 | CONS | PASS | WRONG_STOP | False | False | True | False | 3.1994 | 15 | 7 | 15 | False | False | False | False | 1 | 3.1994 | — | 12.778 | False | — | PASS | TIMEOUT | False | False | False | True | — | — | — | 15 | True | True | False | False | 0 | 0.53004 | — | 18.111 | False | — | PASS | SUCCESS | True | False | False | False | 0.42015 | 15 | 15 | 15 | True | False | True | False | 0 | 0.42015 | 56.417 | 9.6389 | False | — |
| SLW | 228 | CUT | PASS | TIMEOUT | False | False | False | True | — | — | — | 15 | False | False | False | False | 0 | 2.6395 | — | 26.333 | False | — | PASS | TIMEOUT | False | False | False | True | — | — | — | 15 | False | False | False | False | 0 | 1.2678 | — | 15.333 | False | — | PASS | SUCCESS | True | False | False | False | 0.47302 | 15 | 15 | 15 | True | False | True | False | 0 | 0.47302 | 57.833 | 14.222 | False | — |
| H2 | 227 | CUT | PASS | SUCCESS | True | False | False | False | 0.44116 | 20 | 20 | 20 | True | False | True | False | 0 | 0.44116 | 68.083 | 6.5556 | True | — | PASS | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 4.1917 | — | 12.667 | False | — | PASS | WRONG_STOP | False | False | True | False | 1.0453 | 20 | 19 | 20 | False | False | False | False | 0 | 1.0256 | — | 6.3333 | True | — |
| H2 | 227 | CONS+G18 | PASS | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 2.6707 | — | 5.1111 | False | 0.85227 | PASS | WRONG_STOP | False | False | True | False | 0.69491 | 20 | 19 | 20 | True | False | False | False | 0 | 0.69491 | — | 7.3333 | True | 0.81818 | PASS | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 2.2814 | — | 5.6667 | False | 0.87778 |
| H2 | 227 | CONS | PASS | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 5.0972 | — | 8.1111 | False | — | PASS | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 2.4655 | — | 4.6667 | False | — | PASS | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 2.0682 | — | 8 | False | — |
| H2 | 228 | CUT | PASS | SUCCESS | True | False | False | False | 0.28682 | 20 | 20 | 20 | True | False | True | False | 0 | 0.28682 | 79.083 | 11.778 | True | — | PASS | WRONG_STOP | False | False | True | False | 0.50212 | 20 | 19 | 20 | True | False | False | False | 0 | 0.50212 | — | 6.8889 | True | — | PASS | SUCCESS | True | False | False | False | 0.32951 | 20 | 20 | 20 | True | False | True | False | 0 | 0.32951 | 81.333 | 8.7778 | True | — |
| H2 | 228 | CONS | PASS | SUCCESS | True | False | False | False | 0.44313 | 20 | 20 | 20 | True | False | True | False | 0 | 0.44313 | 44.833 | 3.9444 | True | — | PASS | SUCCESS | True | False | False | False | 0.42165 | 20 | 20 | 20 | True | False | True | False | 0 | 0.42165 | 70.583 | 7.6944 | True | — | PASS | WRONG_STOP | False | False | True | False | 0.71532 | 20 | 19 | 20 | True | False | False | False | 0 | 0.50976 | — | 5.4444 | True | — |
| H2 | 228 | CONS+G18 | PASS | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 2.0525 | — | 13.778 | False | 0.77647 | PASS | SUCCESS | True | False | False | False | 0.46833 | 20 | 20 | 20 | True | False | True | False | 0 | 0.46833 | 84.333 | 8.4444 | True | 0.8642 | PASS | SUCCESS | True | False | False | False | 0.44053 | 20 | 20 | 20 | True | False | True | False | 0 | 0.44053 | 83.403 | 7.1806 | True | 0.9375 |

![H1-v2_227_CONS+G18](../research/results/phase60p/figures/H1-v2_227_CONS+G18.png)

![H1-v2_227_CONS](../research/results/phase60p/figures/H1-v2_227_CONS.png)

![H1-v2_227_CUT](../research/results/phase60p/figures/H1-v2_227_CUT.png)

![H1-v2_228_CONS+G18](../research/results/phase60p/figures/H1-v2_228_CONS+G18.png)

![H1-v2_228_CONS](../research/results/phase60p/figures/H1-v2_228_CONS.png)

![H1-v2_228_CUT](../research/results/phase60p/figures/H1-v2_228_CUT.png)

![H2_227_CONS+G18](../research/results/phase60p/figures/H2_227_CONS+G18.png)

![H2_227_CONS](../research/results/phase60p/figures/H2_227_CONS.png)

![H2_227_CUT](../research/results/phase60p/figures/H2_227_CUT.png)

![H2_228_CONS+G18](../research/results/phase60p/figures/H2_228_CONS+G18.png)

![H2_228_CONS](../research/results/phase60p/figures/H2_228_CONS.png)

![H2_228_CUT](../research/results/phase60p/figures/H2_228_CUT.png)

![SLW_227_CONS+G18](../research/results/phase60p/figures/SLW_227_CONS+G18.png)

![SLW_227_CONS](../research/results/phase60p/figures/SLW_227_CONS.png)

![SLW_227_CUT](../research/results/phase60p/figures/SLW_227_CUT.png)

![SLW_228_CONS+G18](../research/results/phase60p/figures/SLW_228_CONS+G18.png)

![SLW_228_CONS](../research/results/phase60p/figures/SLW_228_CONS.png)

![SLW_228_CUT](../research/results/phase60p/figures/SLW_228_CUT.png)
