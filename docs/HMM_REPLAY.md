# HMM 수정안 오프라인 재생

| status | expected_runs | available_runs | replayed_runs | protocol_sha256 |
|---|---|---|---|---|
| PREPARED_NOT_RUN | 86 | 0 | 0 | 90c344085b7c94b1d828f7069d28e3930b351beef9276ada52c241861acfaa6a |

고정 파라미터: ℓ은 기존 양수 인접 Topomap 노드 간격 중앙값이다. NET 진입 위치는 MAP이 바뀔 때마다 갱신하고, NET+MEM의 p_j는 최초 MAP 방문 위치를 영구 보존한다. 파라미터 튜닝·시뮬레이션·NoMaD 재추론·주행 결과 재분류는 하지 않는다.

| 변형 | 고정 정의 |
|---|---|
| HMM0 | Phase42-L WindowHMM 그대로: 매 추론 누적 주행거리 차이, K=max(1,ceil(Δdistance/ℓ)), 원래 방출 |
| NET | w=round(현재 위치와 현재 MAP 진입 위치의 유클리드 거리/ℓ), 최소1 제거, 각 상태 자기 전이 포함 |
| NET+MEM | NET 방출 × exp(−‖p_t−p_j‖²/(2ℓ²)), 미방문 가중1; log 영역에서 계산 |

round는 Python의 최근접 정수(정확한 .5는 짝수 반올림)이며 지도 끝에서 w≤노드 수−1이다. 첫 추론은 Phase42-L처럼 기록 창 안의 균등 prior에서 시작한다. w=0은 상태 전이가 identity라는 뜻이며, 기존 posterior에 질량이 남아 있는 다른 노드로 방출에 의해 MAP이 바뀌는 것까지 금지하지 않는다.

## 입력 가용 범위

| status |
|---|
| NOT_RUN |

대상은 Phase53-P D075 HMM, NIGHT E1, Phase57-P MIN/MIN+G18, Phase58-P 세 방법의 D075다(예정 합계86 run). 각 run의 최종 metrics가 가리키는 attempt만 사용한다. 미완료·입력 누락은 위 표와 coverage.json에 남긴다. 분석 재개 시 새로 완료된 run을 추가하고 이전 입력 hash가 동일한 캐시는 재사용한다. 아직 없는 Phase57/58 run을 완료로 간주하지 않는다.

## HMM0 재현 확인

| inferences | map_matches | width_matches | map_match_rate |
|---|---|---|---|
| 0 | 0 | 0 | — |

HMM0는 저장된 hmm_odometry_total_m의 추론 간 차이를 사용한다. true_node는 저장 node_errors를 우선 사용하고 Phase42-L 최근접 노드 함수와 대조한다. 없을 때만 같은 저장 observation pose로 최근접 노드를 구하고 출처를 기록한다. 실제 pose는 이 실험의 exact odometry 가정이며 true_node는 필터 입력으로 쓰지 않는다.

## 노드 오차·거짓 목표·창 이탈

| scope | variant | n | absolute_median | absolute_p95 | signed_mean | false_goal_inferences | false_goal_runs | previous_MAP_outside | predicted_MAP_outside | forced_window_resets | posterior_MAP_outside | truth_outside_window | terminal_drained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL_LOGGED | HMM0 | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ALL_LOGGED | NET | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ALL_LOGGED | NET+MEM | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| DELIVERED_OR_DECLARATION | HMM0 | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| DELIVERED_OR_DECLARATION | NET | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| DELIVERED_OR_DECLARATION | NET+MEM | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

노드 오차 부호는 MAP−true_node, 거짓 목표는 MAP==goal AND true_node<goal−2다. 기본 ALL_LOGGED는 측정 가능한 저장 추론 전부이며, 실제 전달/선언에 사용된 추론은 DELIVERED_OR_DECLARATION으로 분리한다. false_goal_runs는 반복 판정을 중복 제거한 run 수다. 이는 기존 거리>0.5m 잘못된 도착 정의와 다른 지표다.

창 밖 횟수는 (1) 이전 MAP이 이번 기록 창 밖, (2) 방출 전 전이 예측 MAP이 기록 창 밖, (3) 도달 prior 질량이0이라 기록 창 균등 prior로 강제 초기화한 횟수를 구분한다. 최종 posterior는 기록 창에 제한되므로 posterior_MAP_outside는 구조상0이며, 이를 창 제약 문제가 없다는 근거로 쓰지 않는다.

## 기존 선언 시점에서의 판정

| variant | original | n | matched | would_declare | would_not_declare | unmeasured |
|---|---|---|---|---|---|---|
| HMM0 | ORIGINAL_WRONG_STOP | 0 | 0 | 0 | 0 | 0 |
| HMM0 | ORIGINAL_SUCCESS | 0 | 0 | 0 | 0 | 0 |
| NET | ORIGINAL_WRONG_STOP | 0 | 0 | 0 | 0 | 0 |
| NET | ORIGINAL_SUCCESS | 0 | 0 | 0 | 0 | 0 |
| NET+MEM | ORIGINAL_WRONG_STOP | 0 | 0 | 0 | 0 | 0 |
| NET+MEM | ORIGINAL_SUCCESS | 0 | 0 | 0 | 0 | 0 |

저장 declared_arrival의 추론 ID와 정확히 같은 추론에서 MAP==goal인지 확인했다. 도착을 하지 않았을 시점 이후의 새로운 관측·움직임은 생성하지 않는다. 따라서 성공 수나 미래 도착 시각을 재계산한 결과가 아니다. 선언을 일으킨 terminal_unapplied 추론은 포함하고, 종료 후 단순 drain은 별도로 표시한다.

| status |
|---|
| NOT_RUN |

## 장면별

| status |
|---|
| NOT_RUN |

## 재생 한계

기록된 candidate_ids와 NoMaD 거리값만 모든 변형에 똑같이 사용한다. 대안 MAP±4로 후보 창을 새로 열거나 창 밖 거리값을 만들지 않는다. 기록 창과 새 필터가 충돌하면 Phase42-L의 강제 window reset을 그대로 적용하고 횟수를 공개한다. 실제 온라인 창·subgoal·후속 이미지·경로가 달라지는 효과는 이 재생으로 알 수 없다. 입력 누락 추론도 별도 CSV에 기록했다.
