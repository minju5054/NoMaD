# HMM 수정안 오프라인 재생

| status | expected_runs | available_runs | replayed_runs | protocol_sha256 |
|---|---|---|---|---|
| COMPLETE_AVAILABLE_ONLY | 86 | 78 | 78 | 90c344085b7c94b1d828f7069d28e3930b351beef9276ada52c241861acfaa6a |

고정 파라미터: ℓ은 기존 양수 인접 Topomap 노드 간격 중앙값이다. NET 진입 위치는 MAP이 바뀔 때마다 갱신하고, NET+MEM의 p_j는 최초 MAP 방문 위치를 영구 보존한다. 파라미터 튜닝·시뮬레이션·NoMaD 재추론·주행 결과 재분류는 하지 않는다.

| 변형 | 고정 정의 |
|---|---|
| HMM0 | Phase42-L WindowHMM 그대로: 매 추론 누적 주행거리 차이, K=max(1,ceil(Δdistance/ℓ)), 원래 방출 |
| NET | w=round(현재 위치와 현재 MAP 진입 위치의 유클리드 거리/ℓ), 최소1 제거, 각 상태 자기 전이 포함 |
| NET+MEM | NET 방출 × exp(−‖p_t−p_j‖²/(2ℓ²)), 미방문 가중1; log 영역에서 계산 |

round는 Python의 최근접 정수(정확한 .5는 짝수 반올림)이며 지도 끝에서 w≤노드 수−1이다. 첫 추론은 Phase42-L처럼 기록 창 안의 균등 prior에서 시작한다. w=0은 상태 전이가 identity라는 뜻이며, 기존 posterior에 질량이 남아 있는 다른 노드로 방출에 의해 MAP이 바뀌는 것까지 금지하지 않는다.

## 입력 가용 범위

| phase | expected | available | replayed | not_finalized | other_excluded |
|---|---|---|---|---|---|
| NIGHT_E1 | 36 | 36 | 36 | 0 | 0 |
| Phase53-P | 20 | 20 | 20 | 0 | 0 |
| Phase57-P | 12 | 7 | 7 | 5 | 0 |
| Phase58-P | 18 | 15 | 15 | 3 | 0 |

대상은 Phase53-P D075 HMM, NIGHT E1, Phase57-P MIN/MIN+G18, Phase58-P 세 방법의 D075다(예정 합계86 run). 각 run의 최종 metrics가 가리키는 attempt만 사용한다. 미완료·입력 누락은 위 표와 coverage.json에 남긴다. 분석 재개 시 새로 완료된 run을 추가하고 이전 입력 hash가 동일한 캐시는 재사용한다. 아직 없는 Phase57/58 run을 완료로 간주하지 않는다.

## HMM0 재현 확인

| inferences | map_matches | width_matches | map_match_rate |
|---|---|---|---|
| 4378 | 4378 | 4378 | 1 |

HMM0는 저장된 hmm_odometry_total_m의 추론 간 차이를 사용한다. true_node는 저장 node_errors를 우선 사용하고 Phase42-L 최근접 노드 함수와 대조한다. 없을 때만 같은 저장 observation pose로 최근접 노드를 구하고 출처를 기록한다. 실제 pose는 이 실험의 exact odometry 가정이며 true_node는 필터 입력으로 쓰지 않는다.

## 노드 오차·거짓 목표·창 이탈

| scope | variant | n | absolute_median | absolute_p95 | signed_mean | false_goal_inferences | false_goal_runs | previous_MAP_outside | predicted_MAP_outside | forced_window_resets | posterior_MAP_outside | truth_outside_window | terminal_drained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL_LOGGED | HMM0 | 4378 | 1 | 9 | 0.2168 | 16 | 16 | 0 | 2 | 0 | 0 | 536 | 15 |
| ALL_LOGGED | NET | 4378 | 1 | 9 | 0.08451 | 7 | 6 | 26 | 21 | 2 | 0 | 536 | 15 |
| ALL_LOGGED | NET+MEM | 4378 | 1 | 7 | 0.9178 | 85 | 15 | 95 | 70 | 2 | 0 | 536 | 15 |
| DELIVERED_OR_DECLARATION | HMM0 | 4363 | 1 | 9 | 0.2074 | 16 | 16 | 0 | 2 | 0 | 0 | 532 | 0 |
| DELIVERED_OR_DECLARATION | NET | 4363 | 1 | 9 | 0.07655 | 7 | 6 | 26 | 21 | 2 | 0 | 532 | 0 |
| DELIVERED_OR_DECLARATION | NET+MEM | 4363 | 1 | 7 | 0.9092 | 82 | 15 | 94 | 69 | 2 | 0 | 532 | 0 |

노드 오차 부호는 MAP−true_node, 거짓 목표는 MAP==goal AND true_node<goal−2다. 기본 ALL_LOGGED는 측정 가능한 저장 추론 전부이며, 실제 전달/선언에 사용된 추론은 DELIVERED_OR_DECLARATION으로 분리한다. false_goal_runs는 반복 판정을 중복 제거한 run 수다. 이는 기존 거리>0.5m 잘못된 도착 정의와 다른 지표다.

창 밖 횟수는 (1) 이전 MAP이 이번 기록 창 밖, (2) 방출 전 전이 예측 MAP이 기록 창 밖, (3) 도달 prior 질량이0이라 기록 창 균등 prior로 강제 초기화한 횟수를 구분한다. 최종 posterior는 기록 창에 제한되므로 posterior_MAP_outside는 구조상0이며, 이를 창 제약 문제가 없다는 근거로 쓰지 않는다.

## 기존 선언 시점에서의 판정

| variant | original | n | matched | would_declare | would_not_declare | unmeasured |
|---|---|---|---|---|---|---|
| HMM0 | ORIGINAL_WRONG_STOP | 28 | 28 | 28 | 0 | 0 |
| HMM0 | ORIGINAL_SUCCESS | 29 | 29 | 29 | 0 | 0 |
| NET | ORIGINAL_WRONG_STOP | 28 | 28 | 13 | 15 | 0 |
| NET | ORIGINAL_SUCCESS | 29 | 29 | 22 | 7 | 0 |
| NET+MEM | ORIGINAL_WRONG_STOP | 28 | 28 | 21 | 7 | 0 |
| NET+MEM | ORIGINAL_SUCCESS | 29 | 29 | 22 | 7 | 0 |

저장 declared_arrival의 추론 ID와 정확히 같은 추론에서 MAP==goal인지 확인했다. 도착을 하지 않았을 시점 이후의 새로운 관측·움직임은 생성하지 않는다. 따라서 성공 수나 미래 도착 시각을 재계산한 결과가 아니다. 선언을 일으킨 terminal_unapplied 추론은 포함하고, 종료 후 단순 drain은 별도로 표시한다.

| uid | phase | scene | seed | method | variant | original_classification | original_wrong_stop | original_success | declaration_id | declaration_s | original_stop_distance_m | replay_map | goal_node | would_declare | true_node_at_observation | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase53-P/SLW_D075_221_CUT | Phase53-P | SLW | 221 | CUT | HMM0 | WRONG_STOP | True | False | 71 | 73.08 | 3.36 | 15 | 15 | True | 5 | MATCHED |
| Phase53-P/SLW_D075_221_CUT | Phase53-P | SLW | 221 | CUT | NET | WRONG_STOP | True | False | 71 | 73.08 | 3.36 | 15 | 15 | True | 5 | MATCHED |
| Phase53-P/SLW_D075_221_CUT | Phase53-P | SLW | 221 | CUT | NET+MEM | WRONG_STOP | True | False | 71 | 73.08 | 3.36 | 15 | 15 | True | 5 | MATCHED |
| Phase53-P/SLW_D075_221_GRAPH-HO | Phase53-P | SLW | 221 | GRAPH-HO | HMM0 | SUCCESS | False | True | 41 | 43.83 | 0.3066 | 15 | 15 | True | 14 | MATCHED |
| Phase53-P/SLW_D075_221_GRAPH-HO | Phase53-P | SLW | 221 | GRAPH-HO | NET | SUCCESS | False | True | 41 | 43.83 | 0.3066 | 15 | 15 | True | 14 | MATCHED |
| Phase53-P/SLW_D075_221_GRAPH-HO | Phase53-P | SLW | 221 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 41 | 43.83 | 0.3066 | 15 | 15 | True | 14 | MATCHED |
| Phase53-P/LC_D075_221_GRAPH-HO | Phase53-P | LC | 221 | GRAPH-HO | HMM0 | SUCCESS | False | True | 27 | 29.85 | 0.2678 | 14 | 14 | True | 13 | MATCHED |
| Phase53-P/LC_D075_221_GRAPH-HO | Phase53-P | LC | 221 | GRAPH-HO | NET | SUCCESS | False | True | 27 | 29.85 | 0.2678 | 13 | 14 | False | 13 | MATCHED |
| Phase53-P/LC_D075_221_GRAPH-HO | Phase53-P | LC | 221 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 27 | 29.85 | 0.2678 | 13 | 14 | False | 13 | MATCHED |
| Phase53-P/LC_D075_221_CUT | Phase53-P | LC | 221 | CUT | HMM0 | SUCCESS | False | True | 27 | 29.58 | 0.1833 | 14 | 14 | True | 14 | MATCHED |
| Phase53-P/LC_D075_221_CUT | Phase53-P | LC | 221 | CUT | NET | SUCCESS | False | True | 27 | 29.58 | 0.1833 | 13 | 14 | False | 14 | MATCHED |
| Phase53-P/LC_D075_221_CUT | Phase53-P | LC | 221 | CUT | NET+MEM | SUCCESS | False | True | 27 | 29.58 | 0.1833 | 14 | 14 | True | 14 | MATCHED |
| Phase53-P/L2_D075_221_CUT | Phase53-P | L2 | 221 | CUT | HMM0 | SUCCESS | False | True | 39 | 41.58 | 0.2905 | 20 | 20 | True | 19 | MATCHED |
| Phase53-P/L2_D075_221_CUT | Phase53-P | L2 | 221 | CUT | NET | SUCCESS | False | True | 39 | 41.58 | 0.2905 | 20 | 20 | True | 19 | MATCHED |
| Phase53-P/L2_D075_221_CUT | Phase53-P | L2 | 221 | CUT | NET+MEM | SUCCESS | False | True | 39 | 41.58 | 0.2905 | 20 | 20 | True | 19 | MATCHED |
| Phase53-P/L2_D075_221_GRAPH-HO | Phase53-P | L2 | 221 | GRAPH-HO | HMM0 | SUCCESS | False | True | 74 | 76.33 | 0.2579 | 20 | 20 | True | 19 | MATCHED |
| Phase53-P/L2_D075_221_GRAPH-HO | Phase53-P | L2 | 221 | GRAPH-HO | NET | SUCCESS | False | True | 74 | 76.33 | 0.2579 | 20 | 20 | True | 19 | MATCHED |
| Phase53-P/L2_D075_221_GRAPH-HO | Phase53-P | L2 | 221 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 74 | 76.33 | 0.2579 | 20 | 20 | True | 19 | MATCHED |
| Phase53-P/H1_D075_221_GRAPH-HO | Phase53-P | H1 | 221 | GRAPH-HO | HMM0 | WRONG_STOP | True | False | 40 | 42.83 | 2.207 | 14 | 14 | True | 9 | MATCHED |
| Phase53-P/H1_D075_221_GRAPH-HO | Phase53-P | H1 | 221 | GRAPH-HO | NET | WRONG_STOP | True | False | 40 | 42.83 | 2.207 | 14 | 14 | True | 9 | MATCHED |
| Phase53-P/H1_D075_221_GRAPH-HO | Phase53-P | H1 | 221 | GRAPH-HO | NET+MEM | WRONG_STOP | True | False | 40 | 42.83 | 2.207 | 14 | 14 | True | 9 | MATCHED |
| Phase53-P/H2_D075_221_CUT | Phase53-P | H2 | 221 | CUT | HMM0 | SUCCESS | False | True | 81 | 83.58 | 0.3593 | 20 | 20 | True | 19 | MATCHED |
| Phase53-P/H2_D075_221_CUT | Phase53-P | H2 | 221 | CUT | NET | SUCCESS | False | True | 81 | 83.58 | 0.3593 | 20 | 20 | True | 19 | MATCHED |
| Phase53-P/H2_D075_221_CUT | Phase53-P | H2 | 221 | CUT | NET+MEM | SUCCESS | False | True | 81 | 83.58 | 0.3593 | 18 | 20 | False | 19 | MATCHED |
| Phase53-P/SLW_D075_222_GRAPH-HO | Phase53-P | SLW | 222 | GRAPH-HO | HMM0 | WRONG_STOP | True | False | 52 | 54.33 | 0.6595 | 15 | 15 | True | 14 | MATCHED |
| Phase53-P/SLW_D075_222_GRAPH-HO | Phase53-P | SLW | 222 | GRAPH-HO | NET | WRONG_STOP | True | False | 52 | 54.33 | 0.6595 | 11 | 15 | False | 14 | MATCHED |
| Phase53-P/SLW_D075_222_GRAPH-HO | Phase53-P | SLW | 222 | GRAPH-HO | NET+MEM | WRONG_STOP | True | False | 52 | 54.33 | 0.6595 | 15 | 15 | True | 14 | MATCHED |
| Phase53-P/SLW_D075_222_CUT | Phase53-P | SLW | 222 | CUT | HMM0 | SUCCESS | False | True | 40 | 42.83 | 0.3478 | 15 | 15 | True | 15 | MATCHED |
| Phase53-P/SLW_D075_222_CUT | Phase53-P | SLW | 222 | CUT | NET | SUCCESS | False | True | 40 | 42.83 | 0.3478 | 15 | 15 | True | 15 | MATCHED |
| Phase53-P/SLW_D075_222_CUT | Phase53-P | SLW | 222 | CUT | NET+MEM | SUCCESS | False | True | 40 | 42.83 | 0.3478 | 15 | 15 | True | 15 | MATCHED |
| Phase53-P/LC_D075_222_CUT | Phase53-P | LC | 222 | CUT | HMM0 | SUCCESS | False | True | 32 | 34.83 | 0.4122 | 14 | 14 | True | 13 | MATCHED |
| Phase53-P/LC_D075_222_CUT | Phase53-P | LC | 222 | CUT | NET | SUCCESS | False | True | 32 | 34.83 | 0.4122 | 13 | 14 | False | 13 | MATCHED |
| Phase53-P/LC_D075_222_CUT | Phase53-P | LC | 222 | CUT | NET+MEM | SUCCESS | False | True | 32 | 34.83 | 0.4122 | 13 | 14 | False | 13 | MATCHED |
| Phase53-P/LC_D075_222_GRAPH-HO | Phase53-P | LC | 222 | GRAPH-HO | HMM0 | SUCCESS | False | True | 27 | 29.58 | 0.329 | 14 | 14 | True | 14 | MATCHED |
| Phase53-P/LC_D075_222_GRAPH-HO | Phase53-P | LC | 222 | GRAPH-HO | NET | SUCCESS | False | True | 27 | 29.58 | 0.329 | 13 | 14 | False | 14 | MATCHED |
| Phase53-P/LC_D075_222_GRAPH-HO | Phase53-P | LC | 222 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 27 | 29.58 | 0.329 | 13 | 14 | False | 14 | MATCHED |
| Phase53-P/L2_D075_222_GRAPH-HO | Phase53-P | L2 | 222 | GRAPH-HO | HMM0 | WRONG_STOP | True | False | 60 | 61.83 | 7.448 | 20 | 20 | True | 1 | MATCHED |
| Phase53-P/L2_D075_222_GRAPH-HO | Phase53-P | L2 | 222 | GRAPH-HO | NET | WRONG_STOP | True | False | 60 | 61.83 | 7.448 | 20 | 20 | True | 1 | MATCHED |
| Phase53-P/L2_D075_222_GRAPH-HO | Phase53-P | L2 | 222 | GRAPH-HO | NET+MEM | WRONG_STOP | True | False | 60 | 61.83 | 7.448 | 20 | 20 | True | 1 | MATCHED |
| Phase53-P/L2_D075_222_CUT | Phase53-P | L2 | 222 | CUT | HMM0 | WRONG_STOP | True | False | 71 | 73.08 | 6.788 | 20 | 20 | True | 3 | MATCHED |
| Phase53-P/L2_D075_222_CUT | Phase53-P | L2 | 222 | CUT | NET | WRONG_STOP | True | False | 71 | 73.08 | 6.788 | 20 | 20 | True | 3 | MATCHED |
| Phase53-P/L2_D075_222_CUT | Phase53-P | L2 | 222 | CUT | NET+MEM | WRONG_STOP | True | False | 71 | 73.08 | 6.788 | 20 | 20 | True | 3 | MATCHED |
| Phase53-P/H1_D075_222_GRAPH-HO | Phase53-P | H1 | 222 | GRAPH-HO | HMM0 | SUCCESS | False | True | 29 | 31.83 | 0.2772 | 14 | 14 | True | 14 | MATCHED |
| Phase53-P/H1_D075_222_GRAPH-HO | Phase53-P | H1 | 222 | GRAPH-HO | NET | SUCCESS | False | True | 29 | 31.83 | 0.2772 | 13 | 14 | False | 14 | MATCHED |
| Phase53-P/H1_D075_222_GRAPH-HO | Phase53-P | H1 | 222 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 29 | 31.83 | 0.2772 | 13 | 14 | False | 14 | MATCHED |
| Phase53-P/H1_D075_222_CUT | Phase53-P | H1 | 222 | CUT | HMM0 | SUCCESS | False | True | 30 | 32.58 | 0.3296 | 14 | 14 | True | 14 | MATCHED |
| Phase53-P/H1_D075_222_CUT | Phase53-P | H1 | 222 | CUT | NET | SUCCESS | False | True | 30 | 32.58 | 0.3296 | 14 | 14 | True | 14 | MATCHED |
| Phase53-P/H1_D075_222_CUT | Phase53-P | H1 | 222 | CUT | NET+MEM | SUCCESS | False | True | 30 | 32.58 | 0.3296 | 14 | 14 | True | 14 | MATCHED |
| Phase53-P/H2_D075_222_CUT | Phase53-P | H2 | 222 | CUT | HMM0 | SUCCESS | False | True | 75 | 77.08 | 0.3557 | 20 | 20 | True | 20 | MATCHED |
| Phase53-P/H2_D075_222_CUT | Phase53-P | H2 | 222 | CUT | NET | SUCCESS | False | True | 75 | 77.08 | 0.3557 | 20 | 20 | True | 20 | MATCHED |
| Phase53-P/H2_D075_222_CUT | Phase53-P | H2 | 222 | CUT | NET+MEM | SUCCESS | False | True | 75 | 77.08 | 0.3557 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/SLW_D075_225_GRAPH-HO | NIGHT_E1 | SLW | 225 | GRAPH-HO | HMM0 | WRONG_STOP | True | False | 40 | 42.32 | 3.376 | 15 | 15 | True | 7 | MATCHED |
| NIGHT_E1/SLW_D075_225_GRAPH-HO | NIGHT_E1 | SLW | 225 | GRAPH-HO | NET | WRONG_STOP | True | False | 40 | 42.32 | 3.376 | 11 | 15 | False | 7 | MATCHED |
| NIGHT_E1/SLW_D075_225_GRAPH-HO | NIGHT_E1 | SLW | 225 | GRAPH-HO | NET+MEM | WRONG_STOP | True | False | 40 | 42.32 | 3.376 | 11 | 15 | False | 7 | MATCHED |
| NIGHT_E1/SLW_D075_225_OURS-R3 | NIGHT_E1 | SLW | 225 | OURS-R3 | HMM0 | WRONG_STOP | True | False | 46 | 48.11 | 3.142 | 15 | 15 | True | 7 | MATCHED |
| NIGHT_E1/SLW_D075_225_OURS-R3 | NIGHT_E1 | SLW | 225 | OURS-R3 | NET | WRONG_STOP | True | False | 46 | 48.11 | 3.142 | 11 | 15 | False | 7 | MATCHED |
| NIGHT_E1/SLW_D075_225_OURS-R3 | NIGHT_E1 | SLW | 225 | OURS-R3 | NET+MEM | WRONG_STOP | True | False | 46 | 48.11 | 3.142 | 11 | 15 | False | 7 | MATCHED |
| NIGHT_E1/SLW_D075_225_CUT | NIGHT_E1 | SLW | 225 | CUT | HMM0 | SUCCESS | False | True | 51 | 53.32 | 0.3008 | 15 | 15 | True | 14 | MATCHED |
| NIGHT_E1/SLW_D075_225_CUT | NIGHT_E1 | SLW | 225 | CUT | NET | SUCCESS | False | True | 51 | 53.32 | 0.3008 | 15 | 15 | True | 14 | MATCHED |
| NIGHT_E1/SLW_D075_225_CUT | NIGHT_E1 | SLW | 225 | CUT | NET+MEM | SUCCESS | False | True | 51 | 53.32 | 0.3008 | 15 | 15 | True | 14 | MATCHED |
| NIGHT_E1/LC_D075_225_GRAPH-HO | NIGHT_E1 | LC | 225 | GRAPH-HO | HMM0 | SUCCESS | False | True | 28 | 30.33 | 0.3614 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/LC_D075_225_GRAPH-HO | NIGHT_E1 | LC | 225 | GRAPH-HO | NET | SUCCESS | False | True | 28 | 30.33 | 0.3614 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/LC_D075_225_GRAPH-HO | NIGHT_E1 | LC | 225 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 28 | 30.33 | 0.3614 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/LC_D075_225_OURS-R3 | NIGHT_E1 | LC | 225 | OURS-R3 | HMM0 | WRONG_STOP | True | False | 23 | 25.83 | 0.5218 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/LC_D075_225_OURS-R3 | NIGHT_E1 | LC | 225 | OURS-R3 | NET | WRONG_STOP | True | False | 23 | 25.83 | 0.5218 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/LC_D075_225_OURS-R3 | NIGHT_E1 | LC | 225 | OURS-R3 | NET+MEM | WRONG_STOP | True | False | 23 | 25.83 | 0.5218 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/LC_D075_225_CUT | NIGHT_E1 | LC | 225 | CUT | HMM0 | SUCCESS | False | True | 24 | 26.83 | 0.4295 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/LC_D075_225_CUT | NIGHT_E1 | LC | 225 | CUT | NET | SUCCESS | False | True | 24 | 26.83 | 0.4295 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/LC_D075_225_CUT | NIGHT_E1 | LC | 225 | CUT | NET+MEM | SUCCESS | False | True | 24 | 26.83 | 0.4295 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/L2_D075_225_OURS-R3 | NIGHT_E1 | L2 | 225 | OURS-R3 | HMM0 | SUCCESS | False | True | 42 | 44.58 | 0.4726 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/L2_D075_225_OURS-R3 | NIGHT_E1 | L2 | 225 | OURS-R3 | NET | SUCCESS | False | True | 42 | 44.58 | 0.4726 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/L2_D075_225_OURS-R3 | NIGHT_E1 | L2 | 225 | OURS-R3 | NET+MEM | SUCCESS | False | True | 42 | 44.58 | 0.4726 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/L2_D075_225_GRAPH-HO | NIGHT_E1 | L2 | 225 | GRAPH-HO | HMM0 | WRONG_STOP | True | False | 45 | 47.08 | 0.5109 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/L2_D075_225_GRAPH-HO | NIGHT_E1 | L2 | 225 | GRAPH-HO | NET | WRONG_STOP | True | False | 45 | 47.08 | 0.5109 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/L2_D075_225_GRAPH-HO | NIGHT_E1 | L2 | 225 | GRAPH-HO | NET+MEM | WRONG_STOP | True | False | 45 | 47.08 | 0.5109 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/L2_D075_225_CUT | NIGHT_E1 | L2 | 225 | CUT | HMM0 | WRONG_STOP | True | False | 44 | 46.33 | 0.5323 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/L2_D075_225_CUT | NIGHT_E1 | L2 | 225 | CUT | NET | WRONG_STOP | True | False | 44 | 46.33 | 0.5323 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/L2_D075_225_CUT | NIGHT_E1 | L2 | 225 | CUT | NET+MEM | WRONG_STOP | True | False | 44 | 46.33 | 0.5323 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/H1_D075_225_OURS-R3 | NIGHT_E1 | H1 | 225 | OURS-R3 | HMM0 | WRONG_STOP | True | False | 28 | 30.57 | 0.6189 | 14 | 14 | True | 12 | MATCHED |
| NIGHT_E1/H1_D075_225_OURS-R3 | NIGHT_E1 | H1 | 225 | OURS-R3 | NET | WRONG_STOP | True | False | 28 | 30.57 | 0.6189 | 14 | 14 | True | 12 | MATCHED |
| NIGHT_E1/H1_D075_225_OURS-R3 | NIGHT_E1 | H1 | 225 | OURS-R3 | NET+MEM | WRONG_STOP | True | False | 28 | 30.57 | 0.6189 | 14 | 14 | True | 12 | MATCHED |
| NIGHT_E1/H1_D075_225_CUT | NIGHT_E1 | H1 | 225 | CUT | HMM0 | WRONG_STOP | True | False | 27 | 29.58 | 0.5936 | 14 | 14 | True | 12 | MATCHED |
| NIGHT_E1/H1_D075_225_CUT | NIGHT_E1 | H1 | 225 | CUT | NET | WRONG_STOP | True | False | 27 | 29.58 | 0.5936 | 14 | 14 | True | 12 | MATCHED |
| NIGHT_E1/H1_D075_225_CUT | NIGHT_E1 | H1 | 225 | CUT | NET+MEM | WRONG_STOP | True | False | 27 | 29.58 | 0.5936 | 14 | 14 | True | 12 | MATCHED |
| NIGHT_E1/H1_D075_225_GRAPH-HO | NIGHT_E1 | H1 | 225 | GRAPH-HO | HMM0 | SUCCESS | False | True | 32 | 34.83 | 0.3702 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1_D075_225_GRAPH-HO | NIGHT_E1 | H1 | 225 | GRAPH-HO | NET | SUCCESS | False | True | 32 | 34.83 | 0.3702 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1_D075_225_GRAPH-HO | NIGHT_E1 | H1 | 225 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 32 | 34.83 | 0.3702 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H2_D075_225_OURS-R3 | NIGHT_E1 | H2 | 225 | OURS-R3 | HMM0 | WRONG_STOP | True | False | 46 | 48.33 | 0.6518 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/H2_D075_225_OURS-R3 | NIGHT_E1 | H2 | 225 | OURS-R3 | NET | WRONG_STOP | True | False | 46 | 48.33 | 0.6518 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/H2_D075_225_OURS-R3 | NIGHT_E1 | H2 | 225 | OURS-R3 | NET+MEM | WRONG_STOP | True | False | 46 | 48.33 | 0.6518 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/H1-v2_D075_225_OURS-R3 | NIGHT_E1 | H1-v2 | 225 | OURS-R3 | HMM0 | WRONG_STOP | True | False | 46 | 48.83 | 4.245 | 14 | 14 | True | 2 | MATCHED |
| NIGHT_E1/H1-v2_D075_225_OURS-R3 | NIGHT_E1 | H1-v2 | 225 | OURS-R3 | NET | WRONG_STOP | True | False | 46 | 48.83 | 4.245 | 13 | 14 | False | 2 | MATCHED |
| NIGHT_E1/H1-v2_D075_225_OURS-R3 | NIGHT_E1 | H1-v2 | 225 | OURS-R3 | NET+MEM | WRONG_STOP | True | False | 46 | 48.83 | 4.245 | 13 | 14 | False | 2 | MATCHED |
| NIGHT_E1/SLW_D075_226_OURS-R3 | NIGHT_E1 | SLW | 226 | OURS-R3 | HMM0 | WRONG_STOP | True | False | 37 | 39.58 | 3.591 | 15 | 15 | True | 4 | MATCHED |
| NIGHT_E1/SLW_D075_226_OURS-R3 | NIGHT_E1 | SLW | 226 | OURS-R3 | NET | WRONG_STOP | True | False | 37 | 39.58 | 3.591 | 15 | 15 | True | 4 | MATCHED |
| NIGHT_E1/SLW_D075_226_OURS-R3 | NIGHT_E1 | SLW | 226 | OURS-R3 | NET+MEM | WRONG_STOP | True | False | 37 | 39.58 | 3.591 | 13 | 15 | False | 4 | MATCHED |
| NIGHT_E1/LC_D075_226_CUT | NIGHT_E1 | LC | 226 | CUT | HMM0 | SUCCESS | False | True | 23 | 25.33 | 0.296 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/LC_D075_226_CUT | NIGHT_E1 | LC | 226 | CUT | NET | SUCCESS | False | True | 23 | 25.33 | 0.296 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/LC_D075_226_CUT | NIGHT_E1 | LC | 226 | CUT | NET+MEM | SUCCESS | False | True | 23 | 25.33 | 0.296 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/LC_D075_226_OURS-R3 | NIGHT_E1 | LC | 226 | OURS-R3 | HMM0 | SUCCESS | False | True | 24 | 26.83 | 0.4901 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/LC_D075_226_OURS-R3 | NIGHT_E1 | LC | 226 | OURS-R3 | NET | SUCCESS | False | True | 24 | 26.83 | 0.4901 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/LC_D075_226_OURS-R3 | NIGHT_E1 | LC | 226 | OURS-R3 | NET+MEM | SUCCESS | False | True | 24 | 26.83 | 0.4901 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/LC_D075_226_GRAPH-HO | NIGHT_E1 | LC | 226 | GRAPH-HO | HMM0 | SUCCESS | False | True | 24 | 26.58 | 0.1799 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/LC_D075_226_GRAPH-HO | NIGHT_E1 | LC | 226 | GRAPH-HO | NET | SUCCESS | False | True | 24 | 26.58 | 0.1799 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/LC_D075_226_GRAPH-HO | NIGHT_E1 | LC | 226 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 24 | 26.58 | 0.1799 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/L2_D075_226_OURS-R3 | NIGHT_E1 | L2 | 226 | OURS-R3 | HMM0 | SUCCESS | False | True | 41 | 43.58 | 0.4372 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/L2_D075_226_OURS-R3 | NIGHT_E1 | L2 | 226 | OURS-R3 | NET | SUCCESS | False | True | 41 | 43.58 | 0.4372 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/L2_D075_226_OURS-R3 | NIGHT_E1 | L2 | 226 | OURS-R3 | NET+MEM | SUCCESS | False | True | 41 | 43.58 | 0.4372 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/L2_D075_226_CUT | NIGHT_E1 | L2 | 226 | CUT | HMM0 | SUCCESS | False | True | 45 | 47.58 | 0.3837 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/L2_D075_226_CUT | NIGHT_E1 | L2 | 226 | CUT | NET | SUCCESS | False | True | 45 | 47.58 | 0.3837 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/L2_D075_226_CUT | NIGHT_E1 | L2 | 226 | CUT | NET+MEM | SUCCESS | False | True | 45 | 47.58 | 0.3837 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/L2_D075_226_GRAPH-HO | NIGHT_E1 | L2 | 226 | GRAPH-HO | HMM0 | WRONG_STOP | True | False | 38 | 40.83 | 0.571 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/L2_D075_226_GRAPH-HO | NIGHT_E1 | L2 | 226 | GRAPH-HO | NET | WRONG_STOP | True | False | 38 | 40.83 | 0.571 | 19 | 20 | False | 19 | MATCHED |
| NIGHT_E1/L2_D075_226_GRAPH-HO | NIGHT_E1 | L2 | 226 | GRAPH-HO | NET+MEM | WRONG_STOP | True | False | 38 | 40.83 | 0.571 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/H1_D075_226_CUT | NIGHT_E1 | H1 | 226 | CUT | HMM0 | SUCCESS | False | True | 27 | 29.58 | 0.3454 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1_D075_226_CUT | NIGHT_E1 | H1 | 226 | CUT | NET | SUCCESS | False | True | 27 | 29.58 | 0.3454 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1_D075_226_CUT | NIGHT_E1 | H1 | 226 | CUT | NET+MEM | SUCCESS | False | True | 27 | 29.58 | 0.3454 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1_D075_226_GRAPH-HO | NIGHT_E1 | H1 | 226 | GRAPH-HO | HMM0 | WRONG_STOP | True | False | 59 | 61.33 | 2.619 | 14 | 14 | True | 8 | MATCHED |
| NIGHT_E1/H1_D075_226_GRAPH-HO | NIGHT_E1 | H1 | 226 | GRAPH-HO | NET | WRONG_STOP | True | False | 59 | 61.33 | 2.619 | 14 | 14 | True | 8 | MATCHED |
| NIGHT_E1/H1_D075_226_GRAPH-HO | NIGHT_E1 | H1 | 226 | GRAPH-HO | NET+MEM | WRONG_STOP | True | False | 59 | 61.33 | 2.619 | 14 | 14 | True | 8 | MATCHED |
| NIGHT_E1/H1_D075_226_OURS-R3 | NIGHT_E1 | H1 | 226 | OURS-R3 | HMM0 | WRONG_STOP | True | False | 28 | 30.58 | 0.6112 | 14 | 14 | True | 13 | MATCHED |
| NIGHT_E1/H1_D075_226_OURS-R3 | NIGHT_E1 | H1 | 226 | OURS-R3 | NET | WRONG_STOP | True | False | 28 | 30.58 | 0.6112 | 13 | 14 | False | 13 | MATCHED |
| NIGHT_E1/H1_D075_226_OURS-R3 | NIGHT_E1 | H1 | 226 | OURS-R3 | NET+MEM | WRONG_STOP | True | False | 28 | 30.58 | 0.6112 | 13 | 14 | False | 13 | MATCHED |
| NIGHT_E1/H2_D075_226_OURS-R3 | NIGHT_E1 | H2 | 226 | OURS-R3 | HMM0 | WRONG_STOP | True | False | 49 | 51.08 | 0.6717 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/H2_D075_226_OURS-R3 | NIGHT_E1 | H2 | 226 | OURS-R3 | NET | WRONG_STOP | True | False | 49 | 51.08 | 0.6717 | 19 | 20 | False | 19 | MATCHED |
| NIGHT_E1/H2_D075_226_OURS-R3 | NIGHT_E1 | H2 | 226 | OURS-R3 | NET+MEM | WRONG_STOP | True | False | 49 | 51.08 | 0.6717 | 20 | 20 | True | 19 | MATCHED |
| NIGHT_E1/H2_D075_226_GRAPH-HO | NIGHT_E1 | H2 | 226 | GRAPH-HO | HMM0 | SUCCESS | False | True | 73 | 75.58 | 0.487 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/H2_D075_226_GRAPH-HO | NIGHT_E1 | H2 | 226 | GRAPH-HO | NET | SUCCESS | False | True | 73 | 75.58 | 0.487 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/H2_D075_226_GRAPH-HO | NIGHT_E1 | H2 | 226 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 73 | 75.58 | 0.487 | 20 | 20 | True | 20 | MATCHED |
| NIGHT_E1/H1-v2_D075_226_GRAPH-HO | NIGHT_E1 | H1-v2 | 226 | GRAPH-HO | HMM0 | SUCCESS | False | True | 42 | 44.58 | 0.1537 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1-v2_D075_226_GRAPH-HO | NIGHT_E1 | H1-v2 | 226 | GRAPH-HO | NET | SUCCESS | False | True | 42 | 44.58 | 0.1537 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1-v2_D075_226_GRAPH-HO | NIGHT_E1 | H1-v2 | 226 | GRAPH-HO | NET+MEM | SUCCESS | False | True | 42 | 44.58 | 0.1537 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1-v2_D075_226_CUT | NIGHT_E1 | H1-v2 | 226 | CUT | HMM0 | SUCCESS | False | True | 39 | 41.83 | 0.2788 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1-v2_D075_226_CUT | NIGHT_E1 | H1-v2 | 226 | CUT | NET | SUCCESS | False | True | 39 | 41.83 | 0.2788 | 14 | 14 | True | 14 | MATCHED |
| NIGHT_E1/H1-v2_D075_226_CUT | NIGHT_E1 | H1-v2 | 226 | CUT | NET+MEM | SUCCESS | False | True | 39 | 41.83 | 0.2788 | 14 | 14 | True | 14 | MATCHED |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | HMM0 | WRONG_STOP | True | False | 47 | 49.08 | 4.373 | 14 | 14 | True | 1 | MATCHED |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | NET | WRONG_STOP | True | False | 47 | 49.08 | 4.373 | 13 | 14 | False | 1 | MATCHED |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | NET+MEM | WRONG_STOP | True | False | 47 | 49.08 | 4.373 | 14 | 14 | True | 1 | MATCHED |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | HMM0 | WRONG_STOP | True | False | 45 | 47.08 | 3.97 | 14 | 14 | True | 3 | MATCHED |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | NET | WRONG_STOP | True | False | 45 | 47.08 | 3.97 | 11 | 14 | False | 3 | MATCHED |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | NET+MEM | WRONG_STOP | True | False | 45 | 47.08 | 3.97 | 14 | 14 | True | 3 | MATCHED |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | HMM0 | WRONG_STOP | True | False | 56 | 58.58 | 4.029 | 14 | 14 | True | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | NET | WRONG_STOP | True | False | 56 | 58.58 | 4.029 | 11 | 14 | False | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | NET+MEM | WRONG_STOP | True | False | 56 | 58.58 | 4.029 | 14 | 14 | True | 2 | MATCHED |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | HMM0 | WRONG_STOP | True | False | 22 | 24.33 | 2.568 | 14 | 14 | True | 8 | MATCHED |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | NET | WRONG_STOP | True | False | 22 | 24.33 | 2.568 | 10 | 14 | False | 8 | MATCHED |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | NET+MEM | WRONG_STOP | True | False | 22 | 24.33 | 2.568 | 9 | 14 | False | 8 | MATCHED |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | HMM0 | WRONG_STOP | True | False | 62 | 63.83 | 4.174 | 14 | 14 | True | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | NET | WRONG_STOP | True | False | 62 | 63.83 | 4.174 | 13 | 14 | False | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | NET+MEM | WRONG_STOP | True | False | 62 | 63.83 | 4.174 | 14 | 14 | True | 2 | MATCHED |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | HMM0 | WRONG_STOP | True | False | 40 | 42.85 | 3.743 | 14 | 14 | True | 3 | MATCHED |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | NET | WRONG_STOP | True | False | 40 | 42.85 | 3.743 | 11 | 14 | False | 3 | MATCHED |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | NET+MEM | WRONG_STOP | True | False | 40 | 42.85 | 3.743 | 14 | 14 | True | 3 | MATCHED |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | HMM0 | SUCCESS | False | True | 44 | 46.83 | 0.294 | 14 | 14 | True | 13 | MATCHED |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | NET | SUCCESS | False | True | 44 | 46.83 | 0.294 | 13 | 14 | False | 13 | MATCHED |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | NET+MEM | SUCCESS | False | True | 44 | 46.83 | 0.294 | 13 | 14 | False | 13 | MATCHED |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | HMM0 | SUCCESS | False | True | 42 | 44.33 | 0.422 | 15 | 15 | True | 14 | MATCHED |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | NET | SUCCESS | False | True | 42 | 44.33 | 0.422 | 14 | 15 | False | 14 | MATCHED |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | NET+MEM | SUCCESS | False | True | 42 | 44.33 | 0.422 | 14 | 15 | False | 14 | MATCHED |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | HMM0 | WRONG_STOP | True | False | 45 | 47.85 | 0.5262 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | NET | WRONG_STOP | True | False | 45 | 47.85 | 0.5262 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | NET+MEM | WRONG_STOP | True | False | 45 | 47.85 | 0.5262 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | HMM0 | WRONG_STOP | True | False | 45 | 47.58 | 2.939 | 15 | 15 | True | 6 | MATCHED |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | NET | WRONG_STOP | True | False | 45 | 47.58 | 2.939 | 12 | 15 | False | 6 | MATCHED |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | NET+MEM | WRONG_STOP | True | False | 45 | 47.58 | 2.939 | 12 | 15 | False | 6 | MATCHED |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | HMM0 | SUCCESS | False | True | 62 | 63.85 | 0.4434 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | NET | SUCCESS | False | True | 62 | 63.85 | 0.4434 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | NET+MEM | SUCCESS | False | True | 62 | 63.85 | 0.4434 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | HMM0 | WRONG_STOP | True | False | 54 | 56.58 | 0.6949 | 20 | 20 | True | 18 | MATCHED |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | NET | WRONG_STOP | True | False | 54 | 56.58 | 0.6949 | 19 | 20 | False | 18 | MATCHED |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | NET+MEM | WRONG_STOP | True | False | 54 | 56.58 | 0.6949 | 20 | 20 | True | 18 | MATCHED |

## 장면별

| phase | scene | variant | n | absolute_median | absolute_p95 | signed_mean | false_goal_inferences | false_goal_runs | previous_MAP_outside | predicted_MAP_outside | forced_window_resets | posterior_MAP_outside | truth_outside_window | terminal_drained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NIGHT_E1 | H1 | HMM0 | 207 | 0 | 2 | 0.1643 | 1 | 1 | 0 | 0 | 0 | 0 | 2 | 0 |
| NIGHT_E1 | H1 | NET | 207 | 0 | 1 | 0.1787 | 1 | 1 | 0 | 0 | 0 | 0 | 2 | 0 |
| NIGHT_E1 | H1 | NET+MEM | 207 | 0 | 1 | 0.3237 | 4 | 1 | 0 | 0 | 0 | 0 | 2 | 0 |
| NIGHT_E1 | H1-v2 | HMM0 | 397 | 2 | 9 | -1.834 | 1 | 1 | 0 | 1 | 0 | 0 | 98 | 2 |
| NIGHT_E1 | H1-v2 | NET | 397 | 2 | 10 | -1.819 | 0 | 0 | 6 | 4 | 0 | 0 | 98 | 2 |
| NIGHT_E1 | H1-v2 | NET+MEM | 397 | 1 | 5 | -0.3778 | 0 | 0 | 18 | 13 | 0 | 0 | 98 | 2 |
| NIGHT_E1 | H2 | HMM0 | 440 | 1 | 7 | 0.4318 | 0 | 0 | 0 | 0 | 0 | 0 | 45 | 2 |
| NIGHT_E1 | H2 | NET | 440 | 1 | 7 | 0.1568 | 0 | 0 | 5 | 3 | 0 | 0 | 45 | 2 |
| NIGHT_E1 | H2 | NET+MEM | 440 | 1 | 3 | 0.9795 | 6 | 1 | 14 | 11 | 0 | 0 | 45 | 2 |
| NIGHT_E1 | L2 | HMM0 | 261 | 1 | 6 | -0.9655 | 0 | 0 | 0 | 0 | 0 | 0 | 27 | 0 |
| NIGHT_E1 | L2 | NET | 261 | 1 | 6 | -1.195 | 0 | 0 | 0 | 0 | 0 | 0 | 27 | 0 |
| NIGHT_E1 | L2 | NET+MEM | 261 | 1 | 2 | 0.02299 | 0 | 0 | 8 | 5 | 0 | 0 | 27 | 0 |
| NIGHT_E1 | LC | HMM0 | 152 | 0 | 1 | 0.2434 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| NIGHT_E1 | LC | NET | 152 | 0 | 1 | 0.2171 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| NIGHT_E1 | LC | NET+MEM | 152 | 0 | 1 | 0.2763 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| NIGHT_E1 | SLW | HMM0 | 355 | 1 | 5 | 0.9493 | 3 | 3 | 0 | 1 | 0 | 0 | 30 | 1 |
| NIGHT_E1 | SLW | NET | 355 | 0 | 4 | 0.6282 | 1 | 1 | 7 | 6 | 1 | 0 | 30 | 1 |
| NIGHT_E1 | SLW | NET+MEM | 355 | 0 | 5 | 0.7493 | 0 | 0 | 5 | 4 | 0 | 0 | 30 | 1 |
| Phase53-P | H1 | HMM0 | 191 | 1 | 8 | -1.707 | 1 | 1 | 0 | 0 | 0 | 0 | 37 | 1 |
| Phase53-P | H1 | NET | 191 | 1 | 8 | -1.602 | 2 | 1 | 0 | 0 | 0 | 0 | 37 | 1 |
| Phase53-P | H1 | NET+MEM | 191 | 1 | 6 | -0.7749 | 1 | 1 | 1 | 1 | 0 | 0 | 37 | 1 |
| Phase53-P | H2 | HMM0 | 338 | 2 | 15 | 2.151 | 0 | 0 | 0 | 0 | 0 | 0 | 76 | 2 |
| Phase53-P | H2 | NET | 338 | 2 | 14 | 2.13 | 0 | 0 | 1 | 2 | 0 | 0 | 76 | 2 |
| Phase53-P | H2 | NET+MEM | 338 | 2 | 16 | 2.784 | 15 | 2 | 16 | 14 | 1 | 0 | 76 | 2 |
| Phase53-P | L2 | HMM0 | 248 | 2 | 17 | 2.762 | 2 | 2 | 0 | 0 | 0 | 0 | 75 | 0 |
| Phase53-P | L2 | NET | 248 | 2 | 17 | 2.536 | 2 | 2 | 1 | 1 | 0 | 0 | 75 | 0 |
| Phase53-P | L2 | NET+MEM | 248 | 1 | 18 | 4.101 | 20 | 2 | 3 | 2 | 0 | 0 | 75 | 0 |
| Phase53-P | LC | HMM0 | 117 | 0 | 1 | 0.188 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase53-P | LC | NET | 117 | 0 | 1 | 0.1368 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase53-P | LC | NET+MEM | 117 | 0 | 1 | 0.2222 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Phase53-P | SLW | HMM0 | 208 | 0 | 3 | 0.6731 | 1 | 1 | 0 | 0 | 0 | 0 | 9 | 0 |
| Phase53-P | SLW | NET | 208 | 0 | 2 | 0.2019 | 1 | 1 | 2 | 2 | 1 | 0 | 9 | 0 |
| Phase53-P | SLW | NET+MEM | 208 | 0 | 2 | 0.5385 | 1 | 1 | 2 | 2 | 1 | 0 | 9 | 0 |
| Phase57-P | H1-v2 | HMM0 | 272 | 2 | 6 | 0.2096 | 2 | 2 | 0 | 0 | 0 | 0 | 17 | 2 |
| Phase57-P | H1-v2 | NET | 272 | 1 | 6 | -0.1838 | 0 | 0 | 1 | 1 | 0 | 0 | 17 | 2 |
| Phase57-P | H1-v2 | NET+MEM | 272 | 1 | 8.45 | 1.158 | 11 | 2 | 3 | 1 | 0 | 0 | 17 | 2 |
| Phase57-P | SLW | HMM0 | 265 | 1 | 2 | 0.7547 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| Phase57-P | SLW | NET | 265 | 0 | 2 | 0.6642 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| Phase57-P | SLW | NET+MEM | 265 | 1 | 5 | 1.785 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| Phase58-P | H1-v2 | HMM0 | 318 | 2 | 12 | -1.472 | 4 | 4 | 0 | 0 | 0 | 0 | 82 | 1 |
| Phase58-P | H1-v2 | NET | 318 | 1 | 12 | -1.396 | 0 | 0 | 1 | 1 | 0 | 0 | 82 | 1 |
| Phase58-P | H1-v2 | NET+MEM | 318 | 1 | 9 | 0.08491 | 15 | 3 | 15 | 9 | 0 | 0 | 82 | 1 |
| Phase58-P | H2 | HMM0 | 233 | 1 | 11 | 0.5966 | 0 | 0 | 0 | 0 | 0 | 0 | 29 | 2 |
| Phase58-P | H2 | NET | 233 | 1 | 11.4 | 0.4764 | 0 | 0 | 0 | 0 | 0 | 0 | 29 | 2 |
| Phase58-P | H2 | NET+MEM | 233 | 1 | 14 | 1.601 | 10 | 1 | 5 | 4 | 0 | 0 | 29 | 2 |
| Phase58-P | SLW | HMM0 | 376 | 1 | 4 | 0.4122 | 1 | 1 | 0 | 0 | 0 | 0 | 9 | 1 |
| Phase58-P | SLW | NET | 376 | 0 | 3 | 0.3936 | 0 | 0 | 2 | 1 | 0 | 0 | 9 | 1 |
| Phase58-P | SLW | NET+MEM | 376 | 0 | 3 | 0.5851 | 2 | 1 | 5 | 4 | 0 | 0 | 9 | 1 |

## 재생 한계

기록된 candidate_ids와 NoMaD 거리값만 모든 변형에 똑같이 사용한다. 대안 MAP±4로 후보 창을 새로 열거나 창 밖 거리값을 만들지 않는다. 기록 창과 새 필터가 충돌하면 Phase42-L의 강제 window reset을 그대로 적용하고 횟수를 공개한다. 실제 온라인 창·subgoal·후속 이미지·경로가 달라지는 효과는 이 재생으로 알 수 없다. 입력 누락 추론도 별도 CSV에 기록했다.
