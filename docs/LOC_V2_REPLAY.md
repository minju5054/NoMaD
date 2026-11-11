# 위치추정 v2 오프라인 재생

| status | calibration_runs | evaluation_runs | model_sha256 | protocol_sha256 |
|---|---|---|---|---|
| PREPARED_NOT_RUN | 0 | 0 | — | be81e9b807ca0059bf7e7070ae0c22d5509b8b69fe4893ef4ab8710dddfdcf08 |

성과 표는 평가 데이터 Phase57·58·59-P의 seed227·228 HMM run만 사용한다. 보정은 Phase47-C·52-P·53-P·NIGHT E1/E3의 HMM0 run만 사용하며 평가 결과로 보정값을 선택하거나 변경하지 않는다.

## 데이터 범위와 보정 메타데이터

| split | phase | registered_runs | available_runs | processed_runs | used_runs | used_inferences | missing_inferences | used_adjacent_pairs |
|---|---|---|---|---|---|---|---|---|
| CAL | Phase47-C | — | 0 | 0 | 0 | 0 | 0 | 0 |
| CAL | Phase52-P | — | 0 | 0 | 0 | 0 | 0 | 0 |
| CAL | Phase53-P | — | 0 | 0 | 0 | 0 | 0 | 0 |
| CAL | NIGHT_E1 | — | 0 | 0 | 0 | 0 | 0 | 0 |
| CAL | NIGHT_E3 | — | 0 | 0 | 0 | 0 | 0 | 0 |
| EVAL | Phase57-P | — | 0 | 0 | 0 | 0 | 0 | — |
| EVAL | Phase58-P | — | 0 | 0 | 0 | 0 | 0 | — |
| EVAL | Phase59-P | — | 0 | 0 | 0 | 0 | 0 | — |

| status |
|---|
| NOT_FITTED |

Phase47-C는 OURS-DETOUR+HMM, Phase57-P는 MIN/MIN+G18만 포함한다. 나머지 지정 phase는 HMM 사용 전 방법이며 보정 Phase52/53/NIGHT는 D075·D150을 모두 포함한다. 보정172개·평가48개가 예정 범위다. 미완료/파일 누락은 coverage.json에 표시하고, 사용 run·추론 수는 위 표로 공개한다. 보정·평가 폴더 및 seed 집합의 비중복을 검사한다. 보정 자료의 성능 수치는 이 문서에 보고하지 않는다.

## 고정 정식화와 사용 가정

Topomap 노드 pose와 오도메트리가 동일한 좌표계로 제공된다고 가정한다. 경로 접선은 내부 노드에서 p[j+1]−p[j−1]의 단위벡터,양 끝은 단방향 인접차다. 길이0이면 가장 가까운 유효 인접 선분을 쓴다. ℓ은 기존 양수 인접 노드 간격 중앙값이다.

| 변형 | 방출 | 전이 |
|---|---|---|
| HMM0 | 기존 exp(−NoMaD 거리) | 기존 최소1+ceil 주행거리 폭 |
| NET | 기존 | 동결 HMM_REPLAY NET |
| OBS | 보정 히스토그램 곱 | HMM0 |
| SIGN | 기존 | 부호 있는 Gaussian |
| OBS+SIGN | 보정 히스토그램 곱 | SIGN |

OBS에서 가설 노드 i의 방출은 ∏_j p(bin(d_j) | k=j−i)이다. k=−4..+4와 양쪽 범위 밖을 합친1행,거리 bin0.5,Laplace1이다. bin의 유한 범위는 보정 데이터의 min/max로만 정하고 양 끝 underflow/overflow bin을 따로 둔다. 평가 거리로 범위를 늘리지 않는다.

SIGN 보정은 직전 추론의 로그 HMM0 MAP 접선에 현재−직전 odometry XY를 투영한 s를 쓰고, residual=(true_node_t−true_node_prev)−s/ℓ의 모집단 분산(ddof0)을 구한다. 평가 시에는 각 변형의 직전 MAP 접선을 쓴다. 전이 가중치는 정수 offset j−i에서 N(s/ℓ,σ²) 밀도를 평가해 전체 지도 노드 범위에서 행 정규화한다. 분산 floor·support cutoff·평가 튜닝은 없다.

각 재생은 기록된 후보 창과 거리값에 조건부로 수행한다. 창 밖 거리는 생성하지 않고,창 안 도달 prior가0이면 기존 Phase42-L처럼 창 균등 prior로 재초기화한다. 첫 prior와 동률 규칙도 기존 그대로다. HMM0/NET 및 선언 시점 연결은 nomad_hmm_replay 코드를 재사용한다.

## 평가 데이터 성과

| variant | inferences | absolute_median | absolute_p95 | signed_mean | false_goal_count | false_goal_runs | original_wrong_stop | wrong_stop_blocked | wrong_stop_unmeasured | original_success | success_declaration_retained | success_unmeasured |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HMM0 | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| NET | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| OBS | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| SIGN | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| OBS+SIGN | 0 | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

오차는 관측 시점 MAP−true_node이며 거짓 목표는 MAP==goal AND true_node<goal−2다. 거짓 목표 run 수는 해당 추론이 하나 이상인 평가 run 수다. 기존 잘못된 도착/성공은 원래 선언을 발생시킨 추론 ID에서만 차단/유지 여부를 비교하며 주행 성공 수를 다시 정의하지 않는다.

## 실제 목표 노드 도달 이후 지연

| variant | true_goal_runs | delay_median_inferences | right_censored_runs | delay_observed_runs | delay_p95_inferences | negative_early_goal_runs | signed_first_MAP_median | no_true_goal_runs |
|---|---|---|---|---|---|---|---|---|
| HMM0 | 0 | — | 0 | 0 | — | 0 | — | 0 |
| NET | 0 | — | 0 | 0 | — | 0 | — | 0 |
| OBS | 0 | — | 0 | 0 | — | 0 | — | 0 |
| SIGN | 0 | — | 0 | 0 | — | 0 | — | 0 |
| OBS+SIGN | 0 | — | 0 | 0 | — | 0 | — | 0 |

주 지연의0은 저장 추론에서 true_node가 처음 goal이 된 추론이다. 그 추론 이후 첫 MAP=goal까지의 추론 ID 간격을 센다. 끝까지 이후 확인이 없으면 우측 검열로 두고 지연 중앙값에서 제외하며,검열 수를 중앙값 바로 옆에 표시한다. 실제 목표 노드를 관측하지 않은 run은 별도로 표시한다.

실제 도달 전에 MAP=goal이 있었으면 negative_early_goal_runs로 별도 집계한다. signed_first_MAP_median은 최초 MAP=goal ID−최초 true_node=goal ID의 부호 있는 보조 중앙값으로 음수를 포함한다. 조기 판정과 이후 검열은 동시에 성립할 수 있다(일찍 goal을 냈지만 실제 도달 뒤 다시 goal을 내지 못한 경우). 따라서 주 지연과 조기 판정을 합쳐 검열을 숨기지 않는다.

| status |
|---|
| NOT_RUN |

## 평가 phase·장면별

| status |
|---|
| NOT_RUN |

## 기존 선언 시점 비교

| status |
|---|
| NOT_RUN |

## 한계

1. OBS는 창 안 거리값들이 서로 독립이라는 가정의 곱이므로 과신할 수 있다.
2. SIGN 분산은 로그의 HMM0 MAP 접선 기준으로 보정했으므로 MAP이 틀렸던 구간의 오차가 분산에 포함된다.
