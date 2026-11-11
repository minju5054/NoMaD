# Phase59-P NET 전이 파일럿

| status | planned | completed | protocol_sha256 | phase58_results_sha256 | baseline_enriched_from_saved_logs |
|---|---|---|---|---|---|
| COMPLETE | 18 | 18 | 27081d1ff2f87d8d083ce8f9823e472c2b225b552573a7b32fa116f8cdc14780 | c56ee2f1d6800c9adb302650a50dc6e2e4e8058ce8fbe889397e45bce590201a | True |

Phase58-P와 방법·장면·seed·jitter·블록 순서·실행기·EC·Graph·latch·만료·공식 도착 기준이 같다. 변경은 NET 전이뿐이다. HMM_REPLAY Replay(NET)를 그대로 사용하고, 영상 observation tick의 odometry XY로 현재 MAP 진입 후 순변위를 계산한다. ℓ은 기존 중앙 노드 간격,round는 Python ties-to-even,최소1 없음,자기 전이 포함이다. MEM은 사용하지 않는다.

후보 창은 기존 radius4 규칙으로 온라인 NET MAP을 중심으로 갱신한다. 방출·부목표 threshold3·closest==goal 선언 규칙은 동결이다. 이는 저장된 창을 고정한 오프라인 HMM_REPLAY와 달리 실제 후속 관측 창도 변할 수 있는 주행 비교다.

성공은 기존대로 선언 시 거리≤0.5m AND 충돌 없음이다. reached_goal_0p7은 선언과 무관한72Hz 저장 목표거리 최소≤0.7m이며, arrived_without_declaration은 그 조건을 만족하고 run 종료까지 선언 파일이 없는 경우다. 기존0.5m 기준의 미선언 수도 보조 열로 구분한다. 실제 도착 여부를 새로운 성공으로 바꾸지 않는다.

거짓 목표 판정은 HMM_REPLAY와 동일하게 추론 MAP==goal AND 관측 시점 true_node<goal−2인 건수(종료 후 저장 추론 포함)다. 실제 거리>0.5m의 잘못된 도착과는 다른 지표다. 선언 시 true_node는 선언 순간 실제 pose에 최근접인 Topomap 노드이며 관측 시점 true_node와 구분한다.

Phase58 값은 같은(scene,seed,method) 결과의 옆 열이다. 추가 거리·노드 항목은 report 단계에서 저장 로그로만 읽어 새 표에 계산하고, 기존 Phase58 결과는 수정하지 않는다. 준비 단계에서는 이 보조 재계산을 하지 않아 일부 비교 열이 —다.

| phase | method | scene | n | valid | success | collision | wrong_stop | timeout_without_declaration | reached_goal_0p7 | arrived_without_declaration | arrived_0p5_without_declaration | false_goal_count | false_goal_runs | stop_distance_m_median | goal_time_s_median | stopped_s_median |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
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

| scene | index | method | status | Phase58_status | classification | success | collision | wrong_stop | timeout_without_declaration | stop_distance_m | declaration_estimated_node | declaration_true_node | goal_node | reached_goal_0p7 | arrived_without_declaration | reached_goal_0p5 | arrived_0p5_without_declaration | false_goal_count | minimum_actual_goal_distance_m | goal_time_s | stopped_s | box_passage | graph_adoption_rate | Phase58_classification | Phase58_success | Phase58_collision | Phase58_wrong_stop | Phase58_timeout_without_declaration | Phase58_stop_distance_m | Phase58_declaration_estimated_node | Phase58_declaration_true_node | Phase58_goal_node | Phase58_reached_goal_0p7 | Phase58_arrived_without_declaration | Phase58_reached_goal_0p5 | Phase58_arrived_0p5_without_declaration | Phase58_false_goal_count | Phase58_minimum_actual_goal_distance_m | Phase58_goal_time_s | Phase58_stopped_s | Phase58_box_passage | Phase58_graph_adoption_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-v2 | 227 | CONS | PASS | PASS | SUCCESS | True | False | False | False | 0.38146 | 14 | 13 | 14 | True | False | True | False | 0 | 0.38146 | 49.833 | 5.8333 | True | — | WRONG_STOP | False | False | True | False | 4.0294 | 14 | 2 | 14 | False | False | False | False | 1 | 2.4835 | — | 6.8889 | False | — |
| H1-v2 | 227 | CUT | PASS | PASS | SUCCESS | True | False | False | False | 0.22702 | 14 | 14 | 14 | True | False | True | False | 0 | 0.22702 | 45.333 | 8.1111 | True | — | WRONG_STOP | False | False | True | False | 2.568 | 14 | 8 | 14 | False | False | False | False | 1 | 2.5428 | — | 2.8889 | False | — |
| H1-v2 | 227 | CONS+G18 | PASS | PASS | WRONG_STOP | False | False | True | False | 4.4312 | 14 | 1 | 14 | False | False | False | False | 1 | 2.4642 | — | 5 | False | 0.80702 | WRONG_STOP | False | False | True | False | 4.1742 | 14 | 1 | 14 | False | False | False | False | 1 | 2.4474 | — | 8.2222 | False | 0.74576 |
| H1-v2 | 228 | CONS+G18 | PASS | PASS | TIMEOUT | False | False | False | True | — | — | — | 14 | True | True | True | True | 0 | 0.025123 | — | 8.3333 | True | 0.77528 | WRONG_STOP | False | False | True | False | 3.7431 | 14 | 3 | 14 | False | False | False | False | 1 | 2.5134 | — | 8.1111 | False | 0.65 |
| H1-v2 | 228 | CUT | PASS | PASS | WRONG_STOP | False | False | True | False | 4.7688 | 14 | 0 | 14 | False | False | False | False | 1 | 2.4883 | — | 11.611 | False | — | TIMEOUT | False | False | False | True | — | — | — | 14 | True | True | True | True | 0 | 0.1312 | — | 17.222 | True | — |
| H1-v2 | 228 | CONS | PASS | PASS | SUCCESS | True | False | False | False | 0.47562 | 14 | 13 | 14 | True | False | True | False | 0 | 0.47562 | 53.833 | 8.6667 | True | — | SUCCESS | True | False | False | False | 0.29399 | 14 | 14 | 14 | True | False | True | False | 0 | 0.29399 | 46.833 | 11.333 | True | — |
| SLW | 227 | CONS | PASS | PASS | WRONG_STOP | False | False | True | False | 3.0937 | 15 | 5 | 15 | False | False | False | False | 1 | 2.693 | — | 22.444 | False | — | SUCCESS | True | False | False | False | 0.42198 | 15 | 15 | 15 | True | False | True | False | 0 | 0.42198 | 44.333 | 6.2222 | False | — |
| SLW | 227 | CONS+G18 | PASS | PASS | SUCCESS | True | False | False | False | 0.34581 | 15 | 15 | 15 | True | False | True | False | 0 | 0.34581 | 58.333 | 10.667 | False | 0.54386 | WRONG_STOP | False | False | True | False | 0.52625 | 15 | 15 | 15 | True | False | False | False | 0 | 0.52625 | — | 7.1111 | False | 0.71739 |
| SLW | 227 | CUT | PASS | PASS | SUCCESS | True | False | False | False | 0.35908 | 15 | 15 | 15 | True | False | True | False | 0 | 0.35908 | 52.833 | 8.2222 | False | — | WRONG_STOP | False | False | True | False | 2.9394 | 15 | 5 | 15 | False | False | False | False | 1 | 2.3925 | — | 10 | False | — |
| SLW | 228 | CONS+G18 | PASS | PASS | SUCCESS | True | False | False | False | 0.34674 | 15 | 15 | 15 | True | False | True | False | 0 | 0.34674 | 85.583 | 16.667 | False | 0.61176 | SUCCESS | True | False | False | False | 0.44336 | 15 | 15 | 15 | True | False | True | False | 0 | 0.44336 | 63.847 | 7.6667 | False | 0.71429 |
| SLW | 228 | CONS | PASS | PASS | SUCCESS | True | False | False | False | 0.42015 | 15 | 15 | 15 | True | False | True | False | 0 | 0.42015 | 56.417 | 9.6389 | False | — | TIMEOUT | False | False | False | True | — | — | — | 15 | True | True | False | False | 0 | 0.53004 | — | 18.111 | False | — |
| SLW | 228 | CUT | PASS | PASS | SUCCESS | True | False | False | False | 0.47302 | 15 | 15 | 15 | True | False | True | False | 0 | 0.47302 | 57.833 | 14.222 | False | — | TIMEOUT | False | False | False | True | — | — | — | 15 | False | False | False | False | 0 | 1.2678 | — | 15.333 | False | — |
| H2 | 227 | CUT | PASS | PASS | WRONG_STOP | False | False | True | False | 1.0453 | 20 | 19 | 20 | False | False | False | False | 0 | 1.0256 | — | 6.3333 | True | — | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 4.1917 | — | 12.667 | False | — |
| H2 | 227 | CONS+G18 | PASS | PASS | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 2.2814 | — | 5.6667 | False | 0.87778 | WRONG_STOP | False | False | True | False | 0.69491 | 20 | 19 | 20 | True | False | False | False | 0 | 0.69491 | — | 7.3333 | True | 0.81818 |
| H2 | 227 | CONS | PASS | PASS | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 2.0682 | — | 8 | False | — | TIMEOUT | False | False | False | True | — | — | — | 20 | False | False | False | False | 0 | 2.4655 | — | 4.6667 | False | — |
| H2 | 228 | CUT | PASS | PASS | SUCCESS | True | False | False | False | 0.32951 | 20 | 20 | 20 | True | False | True | False | 0 | 0.32951 | 81.333 | 8.7778 | True | — | WRONG_STOP | False | False | True | False | 0.50212 | 20 | 19 | 20 | True | False | False | False | 0 | 0.50212 | — | 6.8889 | True | — |
| H2 | 228 | CONS | PASS | PASS | WRONG_STOP | False | False | True | False | 0.71532 | 20 | 19 | 20 | True | False | False | False | 0 | 0.50976 | — | 5.4444 | True | — | SUCCESS | True | False | False | False | 0.42165 | 20 | 20 | 20 | True | False | True | False | 0 | 0.42165 | 70.583 | 7.6944 | True | — |
| H2 | 228 | CONS+G18 | PASS | PASS | SUCCESS | True | False | False | False | 0.44053 | 20 | 20 | 20 | True | False | True | False | 0 | 0.44053 | 83.403 | 7.1806 | True | 0.9375 | SUCCESS | True | False | False | False | 0.46833 | 20 | 20 | 20 | True | False | True | False | 0 | 0.46833 | 84.333 | 8.4444 | True | 0.8642 |

![H1-v2_227_CONS+G18](../research/results/phase59p/figures/H1-v2_227_CONS+G18.png)

![H1-v2_227_CONS](../research/results/phase59p/figures/H1-v2_227_CONS.png)

![H1-v2_227_CUT](../research/results/phase59p/figures/H1-v2_227_CUT.png)

![H1-v2_228_CONS+G18](../research/results/phase59p/figures/H1-v2_228_CONS+G18.png)

![H1-v2_228_CONS](../research/results/phase59p/figures/H1-v2_228_CONS.png)

![H1-v2_228_CUT](../research/results/phase59p/figures/H1-v2_228_CUT.png)

![H2_227_CONS+G18](../research/results/phase59p/figures/H2_227_CONS+G18.png)

![H2_227_CONS](../research/results/phase59p/figures/H2_227_CONS.png)

![H2_227_CUT](../research/results/phase59p/figures/H2_227_CUT.png)

![H2_228_CONS+G18](../research/results/phase59p/figures/H2_228_CONS+G18.png)

![H2_228_CONS](../research/results/phase59p/figures/H2_228_CONS.png)

![H2_228_CUT](../research/results/phase59p/figures/H2_228_CUT.png)

![SLW_227_CONS+G18](../research/results/phase59p/figures/SLW_227_CONS+G18.png)

![SLW_227_CONS](../research/results/phase59p/figures/SLW_227_CONS.png)

![SLW_227_CUT](../research/results/phase59p/figures/SLW_227_CUT.png)

![SLW_228_CONS+G18](../research/results/phase59p/figures/SLW_228_CONS+G18.png)

![SLW_228_CONS](../research/results/phase59p/figures/SLW_228_CONS.png)

![SLW_228_CUT](../research/results/phase59p/figures/SLW_228_CUT.png)
