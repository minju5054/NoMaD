# 위치추정 v2 오프라인 재생

| status | calibration_runs | evaluation_runs | model_sha256 | protocol_sha256 |
|---|---|---|---|---|
| PARTIAL_OR_AVAILABLE_ONLY | 172 | 43 | f806c6236bfdf0470faca8578fcb9ab749770d859856de411d4d341f0417c8ca | be81e9b807ca0059bf7e7070ae0c22d5509b8b69fe4893ef4ab8710dddfdcf08 |

성과 표는 평가 데이터 Phase57·58·59-P의 seed227·228 HMM run만 사용한다. 보정은 Phase47-C·52-P·53-P·NIGHT E1/E3의 HMM0 run만 사용하며 평가 결과로 보정값을 선택하거나 변경하지 않는다.

## 데이터 범위와 보정 메타데이터

| split | phase | registered_runs | available_runs | processed_runs | used_runs | used_inferences | missing_inferences | used_adjacent_pairs |
|---|---|---|---|---|---|---|---|---|
| CAL | Phase47-C | 20 | 20 | 20 | 20 | 978 | 0 | 958 |
| CAL | Phase52-P | 40 | 40 | 40 | 40 | 1863 | 0 | 1823 |
| CAL | Phase53-P | 40 | 40 | 40 | 40 | 1912 | 0 | 1872 |
| CAL | NIGHT_E1 | 36 | 36 | 36 | 36 | 1812 | 0 | 1776 |
| CAL | NIGHT_E3 | 36 | 36 | 36 | 36 | 1484 | 0 | 1448 |
| EVAL | Phase57-P | 12 | 7 | 7 | 7 | 537 | 0 | — |
| EVAL | Phase58-P | 18 | 18 | 18 | 18 | 1125 | 0 | — |
| EVAL | Phase59-P | 18 | 18 | 18 | 18 | 1190 | 0 | — |

| sigma2 | residual_mean | residual_count | candidate_distance_count | distance_bin_count | frozen_at_utc |
|---|---|---|---|---|---|
| 0.1492 | 8.966e-05 | 7877 | 70838 | 42 | 2026-11-11T08:29:17.824101+00:00 |

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
| HMM0 | 2852 | 1 | 8 | 0.08976 | 14 | 10 | 15 | 0 | 0 | 15 | 15 | 0 |
| NET | 2852 | 1 | 7 | 0.006311 | 3 | 3 | 15 | 8 | 0 | 15 | 13 | 0 |
| OBS | 2852 | 1 | 7 | 0.4905 | 105 | 10 | 15 | 11 | 0 | 15 | 3 | 0 |
| SIGN | 2852 | 1 | 7 | 0.2384 | 1 | 1 | 15 | 12 | 0 | 15 | 12 | 0 |
| OBS+SIGN | 2852 | 1 | 7 | 0.4863 | 47 | 3 | 15 | 14 | 0 | 15 | 2 | 0 |

오차는 관측 시점 MAP−true_node이며 거짓 목표는 MAP==goal AND true_node<goal−2다. 거짓 목표 run 수는 해당 추론이 하나 이상인 평가 run 수다. 기존 잘못된 도착/성공은 원래 선언을 발생시킨 추론 ID에서만 차단/유지 여부를 비교하며 주행 성공 수를 다시 정의하지 않는다.

## 실제 목표 노드 도달 이후 지연

| variant | true_goal_runs | delay_median_inferences | right_censored_runs | delay_observed_runs | delay_p95_inferences | negative_early_goal_runs | signed_first_MAP_median | no_true_goal_runs |
|---|---|---|---|---|---|---|---|---|
| HMM0 | 11 | 0 | 2 | 9 | 1.2 | 0 | 0 | 32 |
| NET | 11 | 0 | 2 | 9 | 0 | 0 | 0 | 32 |
| OBS | 11 | 0 | 9 | 2 | 0 | 0 | 0 | 32 |
| SIGN | 11 | 0 | 3 | 8 | 0 | 1 | 0 | 32 |
| OBS+SIGN | 11 | 0 | 9 | 2 | 0 | 0 | 0 | 32 |

주 지연의0은 저장 추론에서 true_node가 처음 goal이 된 추론이다. 그 추론 이후 첫 MAP=goal까지의 추론 ID 간격을 센다. 끝까지 이후 확인이 없으면 우측 검열로 두고 지연 중앙값에서 제외하며,검열 수를 중앙값 바로 옆에 표시한다. 실제 목표 노드를 관측하지 않은 run은 별도로 표시한다.

실제 도달 전에 MAP=goal이 있었으면 negative_early_goal_runs로 별도 집계한다. signed_first_MAP_median은 최초 MAP=goal ID−최초 true_node=goal ID의 부호 있는 보조 중앙값으로 음수를 포함한다. 조기 판정과 이후 검열은 동시에 성립할 수 있다(일찍 goal을 냈지만 실제 도달 뒤 다시 goal을 내지 못한 경우). 따라서 주 지연과 조기 판정을 합쳐 검열을 숨기지 않는다.

| uid | phase | scene | seed | method | variant | true_goal_reached | true_goal_inference_id | first_MAP_goal_id | first_MAP_after_true_goal_id | delay_after_true_inferences | right_censored_after_true | early_negative_delay | signed_first_MAP_delay | status | censored_followup_inferences |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase57-P/H1-v2_227_MIN | Phase57-P | H1-v2 | 227 | MIN | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_227_MIN | Phase57-P | H1-v2 | 227 | MIN | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_227_MIN | Phase57-P | H1-v2 | 227 | MIN | OBS | False | — | 43 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_227_MIN | Phase57-P | H1-v2 | 227 | MIN | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_227_MIN | Phase57-P | H1-v2 | 227 | MIN | OBS+SIGN | False | — | 47 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_227_MIN+G18 | Phase57-P | H1-v2 | 227 | MIN+G18 | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_227_MIN+G18 | Phase57-P | H1-v2 | 227 | MIN+G18 | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_227_MIN+G18 | Phase57-P | H1-v2 | 227 | MIN+G18 | OBS | False | — | 35 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_227_MIN+G18 | Phase57-P | H1-v2 | 227 | MIN+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_227_MIN+G18 | Phase57-P | H1-v2 | 227 | MIN+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | HMM0 | False | — | 47 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | OBS | False | — | 39 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | HMM0 | False | — | 45 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | OBS | False | — | 39 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN+G18 | Phase57-P | SLW | 227 | MIN+G18 | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN+G18 | Phase57-P | SLW | 227 | MIN+G18 | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN+G18 | Phase57-P | SLW | 227 | MIN+G18 | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN+G18 | Phase57-P | SLW | 227 | MIN+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN+G18 | Phase57-P | SLW | 227 | MIN+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN | Phase57-P | SLW | 227 | MIN | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN | Phase57-P | SLW | 227 | MIN | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN | Phase57-P | SLW | 227 | MIN | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN | Phase57-P | SLW | 227 | MIN | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_227_MIN | Phase57-P | SLW | 227 | MIN | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_228_MIN+G18 | Phase57-P | SLW | 228 | MIN+G18 | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_228_MIN+G18 | Phase57-P | SLW | 228 | MIN+G18 | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_228_MIN+G18 | Phase57-P | SLW | 228 | MIN+G18 | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_228_MIN+G18 | Phase57-P | SLW | 228 | MIN+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase57-P/SLW_228_MIN+G18 | Phase57-P | SLW | 228 | MIN+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | HMM0 | False | — | 56 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | OBS | False | — | 45 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | OBS+SIGN | False | — | 52 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | HMM0 | False | — | 22 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | HMM0 | False | — | 62 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | OBS | False | — | 50 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | HMM0 | False | — | 40 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | OBS | False | — | 35 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CUT | Phase58-P | H1-v2 | 228 | CUT | HMM0 | True | 54 | — | — | — | True | False | — | RIGHT_CENSORED | 34 |
| Phase58-P/H1-v2_228_CUT | Phase58-P | H1-v2 | 228 | CUT | NET | True | 54 | — | — | — | True | False | — | RIGHT_CENSORED | 34 |
| Phase58-P/H1-v2_228_CUT | Phase58-P | H1-v2 | 228 | CUT | OBS | True | 54 | — | — | — | True | False | — | RIGHT_CENSORED | 34 |
| Phase58-P/H1-v2_228_CUT | Phase58-P | H1-v2 | 228 | CUT | SIGN | True | 54 | — | — | — | True | False | — | RIGHT_CENSORED | 34 |
| Phase58-P/H1-v2_228_CUT | Phase58-P | H1-v2 | 228 | CUT | OBS+SIGN | True | 54 | — | — | — | True | False | — | RIGHT_CENSORED | 34 |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | HMM0 | False | — | 44 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | SIGN | False | — | 44 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | HMM0 | False | — | 42 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | SIGN | False | — | 42 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | HMM0 | True | 45 | 45 | 45 | 0 | False | False | 0 | OBSERVED | — |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | NET | True | 45 | 45 | 45 | 0 | False | False | 0 | OBSERVED | — |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | OBS | True | 45 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | SIGN | True | 45 | 43 | 45 | 0 | False | True | -2 | OBSERVED | — |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | OBS+SIGN | True | 45 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | HMM0 | False | — | 45 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | HMM0 | True | 60 | 62 | 62 | 2 | False | False | 2 | OBSERVED | — |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | NET | True | 60 | 60 | 60 | 0 | False | False | 0 | OBSERVED | — |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | OBS | True | 60 | — | — | — | True | False | — | RIGHT_CENSORED | 2 |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | SIGN | True | 60 | 60 | 60 | 0 | False | False | 0 | OBSERVED | — |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | OBS+SIGN | True | 60 | — | — | — | True | False | — | RIGHT_CENSORED | 2 |
| Phase58-P/SLW_228_CONS | Phase58-P | SLW | 228 | CONS | HMM0 | False | — | 88 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CONS | Phase58-P | SLW | 228 | CONS | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CONS | Phase58-P | SLW | 228 | CONS | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CONS | Phase58-P | SLW | 228 | CONS | SIGN | False | — | 88 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CONS | Phase58-P | SLW | 228 | CONS | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CUT | Phase58-P | SLW | 228 | CUT | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CUT | Phase58-P | SLW | 228 | CUT | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CUT | Phase58-P | SLW | 228 | CUT | OBS | False | — | 49 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CUT | Phase58-P | SLW | 228 | CUT | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/SLW_228_CUT | Phase58-P | SLW | 228 | CUT | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CUT | Phase58-P | H2 | 227 | CUT | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CUT | Phase58-P | H2 | 227 | CUT | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CUT | Phase58-P | H2 | 227 | CUT | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CUT | Phase58-P | H2 | 227 | CUT | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CUT | Phase58-P | H2 | 227 | CUT | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | HMM0 | False | — | 54 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS | Phase58-P | H2 | 227 | CONS | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS | Phase58-P | H2 | 227 | CONS | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS | Phase58-P | H2 | 227 | CONS | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS | Phase58-P | H2 | 227 | CONS | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_227_CONS | Phase58-P | H2 | 227 | CONS | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | HMM0 | False | — | 45 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | NET | False | — | 45 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | HMM0 | True | 68 | 68 | 68 | 0 | False | False | 0 | OBSERVED | — |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | NET | True | 68 | 68 | 68 | 0 | False | False | 0 | OBSERVED | — |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | OBS | True | 68 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | SIGN | True | 68 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | OBS+SIGN | True | 68 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | HMM0 | False | — | 82 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | NET | False | — | 82 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | SIGN | False | — | 82 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | HMM0 | False | — | 47 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | NET | False | — | 47 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | HMM0 | True | 43 | 43 | 43 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | NET | True | 43 | 43 | 43 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | OBS | True | 43 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | SIGN | True | 43 | 43 | 43 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | OBS+SIGN | True | 43 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | HMM0 | False | — | 51 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | NET | False | — | 58 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | OBS | False | — | 48 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CONS+G18 | Phase59-P | H1-v2 | 228 | CONS+G18 | HMM0 | True | 77 | — | — | — | True | False | — | RIGHT_CENSORED | 12 |
| Phase59-P/H1-v2_228_CONS+G18 | Phase59-P | H1-v2 | 228 | CONS+G18 | NET | True | 77 | — | — | — | True | False | — | RIGHT_CENSORED | 12 |
| Phase59-P/H1-v2_228_CONS+G18 | Phase59-P | H1-v2 | 228 | CONS+G18 | OBS | True | 77 | — | — | — | True | False | — | RIGHT_CENSORED | 12 |
| Phase59-P/H1-v2_228_CONS+G18 | Phase59-P | H1-v2 | 228 | CONS+G18 | SIGN | True | 77 | — | — | — | True | False | — | RIGHT_CENSORED | 12 |
| Phase59-P/H1-v2_228_CONS+G18 | Phase59-P | H1-v2 | 228 | CONS+G18 | OBS+SIGN | True | 77 | — | — | — | True | False | — | RIGHT_CENSORED | 12 |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | HMM0 | False | — | 38 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | NET | False | — | 57 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | OBS | False | — | 36 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | HMM0 | False | — | 51 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | NET | False | — | 51 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | SIGN | False | — | 51 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | OBS+SIGN | False | — | 38 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | HMM0 | False | — | 75 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | NET | False | — | 75 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | SIGN | False | — | 75 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | HMM0 | True | 56 | 56 | 56 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | NET | True | 56 | 56 | 56 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | OBS | True | 56 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | SIGN | True | 56 | 56 | 56 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | OBS+SIGN | True | 56 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | HMM0 | True | 51 | 51 | 51 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | NET | True | 51 | 51 | 51 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | OBS | True | 51 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | SIGN | True | 51 | 51 | 51 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | OBS+SIGN | True | 51 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | HMM0 | True | 83 | 83 | 83 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | NET | True | 83 | 83 | 83 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | OBS | True | 83 | 83 | 83 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | SIGN | True | 83 | 83 | 83 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | OBS+SIGN | True | 83 | 83 | 83 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | HMM0 | True | 54 | 54 | 54 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | NET | True | 54 | 54 | 54 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | OBS | True | 54 | 54 | 54 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | SIGN | True | 54 | 54 | 54 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | OBS+SIGN | True | 54 | 54 | 54 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | HMM0 | False | — | 55 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | NET | False | — | 55 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | OBS | False | — | 55 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | SIGN | False | — | 55 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | HMM0 | False | — | 64 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | NET | False | — | 65 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | OBS | False | — | 65 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | SIGN | False | — | 64 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS+G18 | Phase59-P | H2 | 227 | CONS+G18 | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS+G18 | Phase59-P | H2 | 227 | CONS+G18 | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS+G18 | Phase59-P | H2 | 227 | CONS+G18 | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS+G18 | Phase59-P | H2 | 227 | CONS+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS+G18 | Phase59-P | H2 | 227 | CONS+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS | Phase59-P | H2 | 227 | CONS | HMM0 | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS | Phase59-P | H2 | 227 | CONS | NET | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS | Phase59-P | H2 | 227 | CONS | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS | Phase59-P | H2 | 227 | CONS | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_227_CONS | Phase59-P | H2 | 227 | CONS | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | HMM0 | True | 79 | 79 | 79 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | NET | True | 79 | 79 | 79 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | OBS | True | 79 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | SIGN | True | 79 | 79 | 79 | 0 | False | False | 0 | OBSERVED | — |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | OBS+SIGN | True | 79 | — | — | — | True | False | — | RIGHT_CENSORED | 0 |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | HMM0 | False | — | 46 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | NET | False | — | 50 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | HMM0 | False | — | 82 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | NET | False | — | 82 | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | OBS | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | OBS+SIGN | False | — | — | — | — | False | False | — | NO_TRUE_GOAL_OBSERVATION | — |

## 평가 phase·장면별

| phase | scene | variant | inferences | absolute_median | absolute_p95 | signed_mean | false_goal_count | false_goal_runs |
|---|---|---|---|---|---|---|---|---|
| Phase57-P | H1-v2 | HMM0 | 272 | 2 | 6 | 0.2096 | 2 | 2 |
| Phase57-P | H1-v2 | NET | 272 | 1 | 6 | -0.1838 | 0 | 0 |
| Phase57-P | H1-v2 | OBS | 272 | 3 | 10 | 2.107 | 61 | 4 |
| Phase57-P | H1-v2 | SIGN | 272 | 1 | 3 | -0.2206 | 0 | 0 |
| Phase57-P | H1-v2 | OBS+SIGN | 272 | 2 | 4 | 1.849 | 42 | 1 |
| Phase57-P | SLW | HMM0 | 265 | 1 | 2 | 0.7547 | 0 | 0 |
| Phase57-P | SLW | NET | 265 | 0 | 2 | 0.6642 | 0 | 0 |
| Phase57-P | SLW | OBS | 265 | 4 | 7 | -0.2566 | 0 | 0 |
| Phase57-P | SLW | SIGN | 265 | 0 | 2 | 0.6943 | 0 | 0 |
| Phase57-P | SLW | OBS+SIGN | 265 | 3 | 7 | -0.6566 | 0 | 0 |
| Phase58-P | H1-v2 | HMM0 | 318 | 2 | 12 | -1.472 | 4 | 4 |
| Phase58-P | H1-v2 | NET | 318 | 1 | 12 | -1.396 | 0 | 0 |
| Phase58-P | H1-v2 | OBS | 318 | 2 | 11 | -0.2893 | 20 | 3 |
| Phase58-P | H1-v2 | SIGN | 318 | 1 | 12 | -1.362 | 0 | 0 |
| Phase58-P | H1-v2 | OBS+SIGN | 318 | 1 | 9 | -0.3711 | 3 | 1 |
| Phase58-P | H2 | HMM0 | 431 | 1 | 7 | 0.2251 | 0 | 0 |
| Phase58-P | H2 | NET | 431 | 1 | 7 | 0.08121 | 0 | 0 |
| Phase58-P | H2 | OBS | 431 | 1 | 7 | 1.144 | 0 | 0 |
| Phase58-P | H2 | SIGN | 431 | 1 | 4 | 0.7146 | 0 | 0 |
| Phase58-P | H2 | OBS+SIGN | 431 | 1 | 6 | 0.9977 | 0 | 0 |
| Phase58-P | SLW | HMM0 | 376 | 1 | 4 | 0.4122 | 1 | 1 |
| Phase58-P | SLW | NET | 376 | 0 | 3 | 0.3936 | 0 | 0 |
| Phase58-P | SLW | OBS | 376 | 1 | 4 | -0.3112 | 8 | 1 |
| Phase58-P | SLW | SIGN | 376 | 0 | 4 | 0.516 | 0 | 0 |
| Phase58-P | SLW | OBS+SIGN | 376 | 1 | 3 | -0.05319 | 0 | 0 |
| Phase59-P | H1-v2 | HMM0 | 351 | 1 | 12 | -0.1054 | 6 | 2 |
| Phase59-P | H1-v2 | NET | 351 | 1 | 12 | -0.3647 | 2 | 2 |
| Phase59-P | H1-v2 | OBS | 351 | 1 | 11 | 0.8803 | 16 | 2 |
| Phase59-P | H1-v2 | SIGN | 351 | 1 | 10 | -0.1994 | 0 | 0 |
| Phase59-P | H1-v2 | OBS+SIGN | 351 | 1 | 10 | 0.8974 | 2 | 1 |
| Phase59-P | H2 | HMM0 | 459 | 1 | 7 | 0.2789 | 0 | 0 |
| Phase59-P | H2 | NET | 459 | 1 | 5 | 0.3007 | 0 | 0 |
| Phase59-P | H2 | OBS | 459 | 1 | 6 | 0.8497 | 0 | 0 |
| Phase59-P | H2 | SIGN | 459 | 1 | 3 | 0.9477 | 0 | 0 |
| Phase59-P | H2 | OBS+SIGN | 459 | 1 | 6 | 1.22 | 0 | 0 |
| Phase59-P | SLW | HMM0 | 380 | 0 | 2.05 | 0.3263 | 1 | 1 |
| Phase59-P | SLW | NET | 380 | 0 | 3 | 0.3763 | 1 | 1 |
| Phase59-P | SLW | OBS | 380 | 1 | 3 | -0.2342 | 0 | 0 |
| Phase59-P | SLW | SIGN | 380 | 0 | 2 | 0.3211 | 1 | 1 |
| Phase59-P | SLW | OBS+SIGN | 380 | 0 | 2 | -0.2868 | 0 | 0 |

## 기존 선언 시점 비교

| uid | phase | scene | seed | method | variant | original_classification | original_wrong_stop | original_success | declaration_id | declaration_s | original_stop_distance_m | replay_map | goal_node | would_declare | true_node_at_observation | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | HMM0 | WRONG_STOP | True | False | 47 | 49.08 | 4.373 | 14 | 14 | True | 1 | MATCHED |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | NET | WRONG_STOP | True | False | 47 | 49.08 | 4.373 | 13 | 14 | False | 1 | MATCHED |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | OBS | WRONG_STOP | True | False | 47 | 49.08 | 4.373 | 12 | 14 | False | 1 | MATCHED |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | SIGN | WRONG_STOP | True | False | 47 | 49.08 | 4.373 | 10 | 14 | False | 1 | MATCHED |
| Phase57-P/H1-v2_228_MIN | Phase57-P | H1-v2 | 228 | MIN | OBS+SIGN | WRONG_STOP | True | False | 47 | 49.08 | 4.373 | 11 | 14 | False | 1 | MATCHED |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | HMM0 | WRONG_STOP | True | False | 45 | 47.08 | 3.97 | 14 | 14 | True | 3 | MATCHED |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | NET | WRONG_STOP | True | False | 45 | 47.08 | 3.97 | 11 | 14 | False | 3 | MATCHED |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | OBS | WRONG_STOP | True | False | 45 | 47.08 | 3.97 | 13 | 14 | False | 3 | MATCHED |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | SIGN | WRONG_STOP | True | False | 45 | 47.08 | 3.97 | 10 | 14 | False | 3 | MATCHED |
| Phase57-P/H1-v2_228_MIN+G18 | Phase57-P | H1-v2 | 228 | MIN+G18 | OBS+SIGN | WRONG_STOP | True | False | 45 | 47.08 | 3.97 | 12 | 14 | False | 3 | MATCHED |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | HMM0 | WRONG_STOP | True | False | 56 | 58.58 | 4.029 | 14 | 14 | True | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | NET | WRONG_STOP | True | False | 56 | 58.58 | 4.029 | 11 | 14 | False | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | OBS | WRONG_STOP | True | False | 56 | 58.58 | 4.029 | 14 | 14 | True | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | SIGN | WRONG_STOP | True | False | 56 | 58.58 | 4.029 | 11 | 14 | False | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS | Phase58-P | H1-v2 | 227 | CONS | OBS+SIGN | WRONG_STOP | True | False | 56 | 58.58 | 4.029 | 14 | 14 | True | 2 | MATCHED |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | HMM0 | WRONG_STOP | True | False | 22 | 24.33 | 2.568 | 14 | 14 | True | 8 | MATCHED |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | NET | WRONG_STOP | True | False | 22 | 24.33 | 2.568 | 10 | 14 | False | 8 | MATCHED |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | OBS | WRONG_STOP | True | False | 22 | 24.33 | 2.568 | 12 | 14 | False | 8 | MATCHED |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | SIGN | WRONG_STOP | True | False | 22 | 24.33 | 2.568 | 13 | 14 | False | 8 | MATCHED |
| Phase58-P/H1-v2_227_CUT | Phase58-P | H1-v2 | 227 | CUT | OBS+SIGN | WRONG_STOP | True | False | 22 | 24.33 | 2.568 | 9 | 14 | False | 8 | MATCHED |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | HMM0 | WRONG_STOP | True | False | 62 | 63.83 | 4.174 | 14 | 14 | True | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | NET | WRONG_STOP | True | False | 62 | 63.83 | 4.174 | 13 | 14 | False | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | OBS | WRONG_STOP | True | False | 62 | 63.83 | 4.174 | 12 | 14 | False | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | SIGN | WRONG_STOP | True | False | 62 | 63.83 | 4.174 | 12 | 14 | False | 2 | MATCHED |
| Phase58-P/H1-v2_227_CONS+G18 | Phase58-P | H1-v2 | 227 | CONS+G18 | OBS+SIGN | WRONG_STOP | True | False | 62 | 63.83 | 4.174 | 12 | 14 | False | 2 | MATCHED |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | HMM0 | WRONG_STOP | True | False | 40 | 42.85 | 3.743 | 14 | 14 | True | 3 | MATCHED |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | NET | WRONG_STOP | True | False | 40 | 42.85 | 3.743 | 11 | 14 | False | 3 | MATCHED |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | OBS | WRONG_STOP | True | False | 40 | 42.85 | 3.743 | 14 | 14 | True | 3 | MATCHED |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | SIGN | WRONG_STOP | True | False | 40 | 42.85 | 3.743 | 11 | 14 | False | 3 | MATCHED |
| Phase58-P/H1-v2_228_CONS+G18 | Phase58-P | H1-v2 | 228 | CONS+G18 | OBS+SIGN | WRONG_STOP | True | False | 40 | 42.85 | 3.743 | 13 | 14 | False | 3 | MATCHED |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | HMM0 | SUCCESS | False | True | 44 | 46.83 | 0.294 | 14 | 14 | True | 13 | MATCHED |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | NET | SUCCESS | False | True | 44 | 46.83 | 0.294 | 13 | 14 | False | 13 | MATCHED |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | OBS | SUCCESS | False | True | 44 | 46.83 | 0.294 | 13 | 14 | False | 13 | MATCHED |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | SIGN | SUCCESS | False | True | 44 | 46.83 | 0.294 | 14 | 14 | True | 13 | MATCHED |
| Phase58-P/H1-v2_228_CONS | Phase58-P | H1-v2 | 228 | CONS | OBS+SIGN | SUCCESS | False | True | 44 | 46.83 | 0.294 | 13 | 14 | False | 13 | MATCHED |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | HMM0 | SUCCESS | False | True | 42 | 44.33 | 0.422 | 15 | 15 | True | 14 | MATCHED |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | NET | SUCCESS | False | True | 42 | 44.33 | 0.422 | 14 | 15 | False | 14 | MATCHED |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | OBS | SUCCESS | False | True | 42 | 44.33 | 0.422 | 14 | 15 | False | 14 | MATCHED |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | SIGN | SUCCESS | False | True | 42 | 44.33 | 0.422 | 15 | 15 | True | 14 | MATCHED |
| Phase58-P/SLW_227_CONS | Phase58-P | SLW | 227 | CONS | OBS+SIGN | SUCCESS | False | True | 42 | 44.33 | 0.422 | 14 | 15 | False | 14 | MATCHED |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | HMM0 | WRONG_STOP | True | False | 45 | 47.85 | 0.5262 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | NET | WRONG_STOP | True | False | 45 | 47.85 | 0.5262 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | OBS | WRONG_STOP | True | False | 45 | 47.85 | 0.5262 | 12 | 15 | False | 15 | MATCHED |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | SIGN | WRONG_STOP | True | False | 45 | 47.85 | 0.5262 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_227_CONS+G18 | Phase58-P | SLW | 227 | CONS+G18 | OBS+SIGN | WRONG_STOP | True | False | 45 | 47.85 | 0.5262 | 14 | 15 | False | 15 | MATCHED |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | HMM0 | WRONG_STOP | True | False | 45 | 47.58 | 2.939 | 15 | 15 | True | 6 | MATCHED |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | NET | WRONG_STOP | True | False | 45 | 47.58 | 2.939 | 12 | 15 | False | 6 | MATCHED |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | OBS | WRONG_STOP | True | False | 45 | 47.58 | 2.939 | 12 | 15 | False | 6 | MATCHED |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | SIGN | WRONG_STOP | True | False | 45 | 47.58 | 2.939 | 10 | 15 | False | 6 | MATCHED |
| Phase58-P/SLW_227_CUT | Phase58-P | SLW | 227 | CUT | OBS+SIGN | WRONG_STOP | True | False | 45 | 47.58 | 2.939 | 12 | 15 | False | 6 | MATCHED |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | HMM0 | SUCCESS | False | True | 62 | 63.85 | 0.4434 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | NET | SUCCESS | False | True | 62 | 63.85 | 0.4434 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | OBS | SUCCESS | False | True | 62 | 63.85 | 0.4434 | 14 | 15 | False | 15 | MATCHED |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | SIGN | SUCCESS | False | True | 62 | 63.85 | 0.4434 | 15 | 15 | True | 15 | MATCHED |
| Phase58-P/SLW_228_CONS+G18 | Phase58-P | SLW | 228 | CONS+G18 | OBS+SIGN | SUCCESS | False | True | 62 | 63.85 | 0.4434 | 14 | 15 | False | 15 | MATCHED |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | HMM0 | WRONG_STOP | True | False | 54 | 56.58 | 0.6949 | 20 | 20 | True | 18 | MATCHED |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | NET | WRONG_STOP | True | False | 54 | 56.58 | 0.6949 | 19 | 20 | False | 18 | MATCHED |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | OBS | WRONG_STOP | True | False | 54 | 56.58 | 0.6949 | 19 | 20 | False | 18 | MATCHED |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | SIGN | WRONG_STOP | True | False | 54 | 56.58 | 0.6949 | 19 | 20 | False | 18 | MATCHED |
| Phase58-P/H2_227_CONS+G18 | Phase58-P | H2 | 227 | CONS+G18 | OBS+SIGN | WRONG_STOP | True | False | 54 | 56.58 | 0.6949 | 19 | 20 | False | 18 | MATCHED |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | HMM0 | WRONG_STOP | True | False | 45 | 47.83 | 0.5021 | 20 | 20 | True | 19 | MATCHED |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | NET | WRONG_STOP | True | False | 45 | 47.83 | 0.5021 | 20 | 20 | True | 19 | MATCHED |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | OBS | WRONG_STOP | True | False | 45 | 47.83 | 0.5021 | 19 | 20 | False | 19 | MATCHED |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | SIGN | WRONG_STOP | True | False | 45 | 47.83 | 0.5021 | 19 | 20 | False | 19 | MATCHED |
| Phase58-P/H2_228_CUT | Phase58-P | H2 | 228 | CUT | OBS+SIGN | WRONG_STOP | True | False | 45 | 47.83 | 0.5021 | 19 | 20 | False | 19 | MATCHED |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | HMM0 | SUCCESS | False | True | 68 | 70.58 | 0.4216 | 20 | 20 | True | 20 | MATCHED |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | NET | SUCCESS | False | True | 68 | 70.58 | 0.4216 | 20 | 20 | True | 20 | MATCHED |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | OBS | SUCCESS | False | True | 68 | 70.58 | 0.4216 | 19 | 20 | False | 20 | MATCHED |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | SIGN | SUCCESS | False | True | 68 | 70.58 | 0.4216 | 19 | 20 | False | 20 | MATCHED |
| Phase58-P/H2_228_CONS | Phase58-P | H2 | 228 | CONS | OBS+SIGN | SUCCESS | False | True | 68 | 70.58 | 0.4216 | 19 | 20 | False | 20 | MATCHED |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | HMM0 | SUCCESS | False | True | 82 | 84.33 | 0.4683 | 20 | 20 | True | 19 | MATCHED |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | NET | SUCCESS | False | True | 82 | 84.33 | 0.4683 | 20 | 20 | True | 19 | MATCHED |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | OBS | SUCCESS | False | True | 82 | 84.33 | 0.4683 | 19 | 20 | False | 19 | MATCHED |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | SIGN | SUCCESS | False | True | 82 | 84.33 | 0.4683 | 20 | 20 | True | 19 | MATCHED |
| Phase58-P/H2_228_CONS+G18 | Phase58-P | H2 | 228 | CONS+G18 | OBS+SIGN | SUCCESS | False | True | 82 | 84.33 | 0.4683 | 19 | 20 | False | 19 | MATCHED |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | HMM0 | SUCCESS | False | True | 47 | 49.83 | 0.3815 | 14 | 14 | True | 13 | MATCHED |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | NET | SUCCESS | False | True | 47 | 49.83 | 0.3815 | 14 | 14 | True | 13 | MATCHED |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | OBS | SUCCESS | False | True | 47 | 49.83 | 0.3815 | 12 | 14 | False | 13 | MATCHED |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | SIGN | SUCCESS | False | True | 47 | 49.83 | 0.3815 | 12 | 14 | False | 13 | MATCHED |
| Phase59-P/H1-v2_227_CONS | Phase59-P | H1-v2 | 227 | CONS | OBS+SIGN | SUCCESS | False | True | 47 | 49.83 | 0.3815 | 12 | 14 | False | 13 | MATCHED |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | HMM0 | SUCCESS | False | True | 43 | 45.33 | 0.227 | 14 | 14 | True | 14 | MATCHED |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | NET | SUCCESS | False | True | 43 | 45.33 | 0.227 | 14 | 14 | True | 14 | MATCHED |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | OBS | SUCCESS | False | True | 43 | 45.33 | 0.227 | 13 | 14 | False | 14 | MATCHED |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | SIGN | SUCCESS | False | True | 43 | 45.33 | 0.227 | 14 | 14 | True | 14 | MATCHED |
| Phase59-P/H1-v2_227_CUT | Phase59-P | H1-v2 | 227 | CUT | OBS+SIGN | SUCCESS | False | True | 43 | 45.33 | 0.227 | 13 | 14 | False | 14 | MATCHED |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | HMM0 | WRONG_STOP | True | False | 58 | 60.85 | 4.431 | 14 | 14 | True | 1 | MATCHED |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | NET | WRONG_STOP | True | False | 58 | 60.85 | 4.431 | 14 | 14 | True | 1 | MATCHED |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | OBS | WRONG_STOP | True | False | 58 | 60.85 | 4.431 | 13 | 14 | False | 1 | MATCHED |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | SIGN | WRONG_STOP | True | False | 58 | 60.85 | 4.431 | 11 | 14 | False | 1 | MATCHED |
| Phase59-P/H1-v2_227_CONS+G18 | Phase59-P | H1-v2 | 227 | CONS+G18 | OBS+SIGN | WRONG_STOP | True | False | 58 | 60.85 | 4.431 | 12 | 14 | False | 1 | MATCHED |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | HMM0 | WRONG_STOP | True | False | 57 | 59.39 | 4.769 | 14 | 14 | True | 0 | MATCHED |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | NET | WRONG_STOP | True | False | 57 | 59.39 | 4.769 | 14 | 14 | True | 0 | MATCHED |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | OBS | WRONG_STOP | True | False | 57 | 59.39 | 4.769 | 14 | 14 | True | 0 | MATCHED |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | SIGN | WRONG_STOP | True | False | 57 | 59.39 | 4.769 | 13 | 14 | False | 0 | MATCHED |
| Phase59-P/H1-v2_228_CUT | Phase59-P | H1-v2 | 228 | CUT | OBS+SIGN | WRONG_STOP | True | False | 57 | 59.39 | 4.769 | 13 | 14 | False | 0 | MATCHED |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | HMM0 | SUCCESS | False | True | 51 | 53.83 | 0.4756 | 14 | 14 | True | 13 | MATCHED |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | NET | SUCCESS | False | True | 51 | 53.83 | 0.4756 | 14 | 14 | True | 13 | MATCHED |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | OBS | SUCCESS | False | True | 51 | 53.83 | 0.4756 | 12 | 14 | False | 13 | MATCHED |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | SIGN | SUCCESS | False | True | 51 | 53.83 | 0.4756 | 14 | 14 | True | 13 | MATCHED |
| Phase59-P/H1-v2_228_CONS | Phase59-P | H1-v2 | 228 | CONS | OBS+SIGN | SUCCESS | False | True | 51 | 53.83 | 0.4756 | 13 | 14 | False | 13 | MATCHED |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | HMM0 | WRONG_STOP | True | False | 75 | 77.58 | 3.094 | 15 | 15 | True | 5 | MATCHED |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | NET | WRONG_STOP | True | False | 75 | 77.58 | 3.094 | 15 | 15 | True | 5 | MATCHED |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | OBS | WRONG_STOP | True | False | 75 | 77.58 | 3.094 | 14 | 15 | False | 5 | MATCHED |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | SIGN | WRONG_STOP | True | False | 75 | 77.58 | 3.094 | 15 | 15 | True | 5 | MATCHED |
| Phase59-P/SLW_227_CONS | Phase59-P | SLW | 227 | CONS | OBS+SIGN | WRONG_STOP | True | False | 75 | 77.58 | 3.094 | 8 | 15 | False | 5 | MATCHED |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | HMM0 | SUCCESS | False | True | 56 | 58.33 | 0.3458 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | NET | SUCCESS | False | True | 56 | 58.33 | 0.3458 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | OBS | SUCCESS | False | True | 56 | 58.33 | 0.3458 | 12 | 15 | False | 15 | MATCHED |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | SIGN | SUCCESS | False | True | 56 | 58.33 | 0.3458 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_227_CONS+G18 | Phase59-P | SLW | 227 | CONS+G18 | OBS+SIGN | SUCCESS | False | True | 56 | 58.33 | 0.3458 | 13 | 15 | False | 15 | MATCHED |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | HMM0 | SUCCESS | False | True | 51 | 52.83 | 0.3591 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | NET | SUCCESS | False | True | 51 | 52.83 | 0.3591 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | OBS | SUCCESS | False | True | 51 | 52.83 | 0.3591 | 12 | 15 | False | 15 | MATCHED |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | SIGN | SUCCESS | False | True | 51 | 52.83 | 0.3591 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_227_CUT | Phase59-P | SLW | 227 | CUT | OBS+SIGN | SUCCESS | False | True | 51 | 52.83 | 0.3591 | 14 | 15 | False | 15 | MATCHED |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | HMM0 | SUCCESS | False | True | 83 | 85.58 | 0.3467 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | NET | SUCCESS | False | True | 83 | 85.58 | 0.3467 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | OBS | SUCCESS | False | True | 83 | 85.58 | 0.3467 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | SIGN | SUCCESS | False | True | 83 | 85.58 | 0.3467 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CONS+G18 | Phase59-P | SLW | 228 | CONS+G18 | OBS+SIGN | SUCCESS | False | True | 83 | 85.58 | 0.3467 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | HMM0 | SUCCESS | False | True | 54 | 56.42 | 0.4201 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | NET | SUCCESS | False | True | 54 | 56.42 | 0.4201 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | OBS | SUCCESS | False | True | 54 | 56.42 | 0.4201 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | SIGN | SUCCESS | False | True | 54 | 56.42 | 0.4201 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CONS | Phase59-P | SLW | 228 | CONS | OBS+SIGN | SUCCESS | False | True | 54 | 56.42 | 0.4201 | 15 | 15 | True | 15 | MATCHED |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | HMM0 | SUCCESS | False | True | 55 | 57.83 | 0.473 | 15 | 15 | True | 14 | MATCHED |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | NET | SUCCESS | False | True | 55 | 57.83 | 0.473 | 15 | 15 | True | 14 | MATCHED |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | OBS | SUCCESS | False | True | 55 | 57.83 | 0.473 | 15 | 15 | True | 14 | MATCHED |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | SIGN | SUCCESS | False | True | 55 | 57.83 | 0.473 | 15 | 15 | True | 14 | MATCHED |
| Phase59-P/SLW_228_CUT | Phase59-P | SLW | 228 | CUT | OBS+SIGN | SUCCESS | False | True | 55 | 57.83 | 0.473 | 14 | 15 | False | 14 | MATCHED |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | HMM0 | WRONG_STOP | True | False | 65 | 67.58 | 1.045 | 20 | 20 | True | 19 | MATCHED |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | NET | WRONG_STOP | True | False | 65 | 67.58 | 1.045 | 20 | 20 | True | 19 | MATCHED |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | OBS | WRONG_STOP | True | False | 65 | 67.58 | 1.045 | 20 | 20 | True | 19 | MATCHED |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | SIGN | WRONG_STOP | True | False | 65 | 67.58 | 1.045 | 20 | 20 | True | 19 | MATCHED |
| Phase59-P/H2_227_CUT | Phase59-P | H2 | 227 | CUT | OBS+SIGN | WRONG_STOP | True | False | 65 | 67.58 | 1.045 | 19 | 20 | False | 19 | MATCHED |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | HMM0 | SUCCESS | False | True | 79 | 81.33 | 0.3295 | 20 | 20 | True | 20 | MATCHED |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | NET | SUCCESS | False | True | 79 | 81.33 | 0.3295 | 20 | 20 | True | 20 | MATCHED |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | OBS | SUCCESS | False | True | 79 | 81.33 | 0.3295 | 19 | 20 | False | 20 | MATCHED |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | SIGN | SUCCESS | False | True | 79 | 81.33 | 0.3295 | 20 | 20 | True | 20 | MATCHED |
| Phase59-P/H2_228_CUT | Phase59-P | H2 | 228 | CUT | OBS+SIGN | SUCCESS | False | True | 79 | 81.33 | 0.3295 | 19 | 20 | False | 20 | MATCHED |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | HMM0 | WRONG_STOP | True | False | 50 | 52.33 | 0.7153 | 20 | 20 | True | 19 | MATCHED |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | NET | WRONG_STOP | True | False | 50 | 52.33 | 0.7153 | 20 | 20 | True | 19 | MATCHED |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | OBS | WRONG_STOP | True | False | 50 | 52.33 | 0.7153 | 18 | 20 | False | 19 | MATCHED |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | SIGN | WRONG_STOP | True | False | 50 | 52.33 | 0.7153 | 19 | 20 | False | 19 | MATCHED |
| Phase59-P/H2_228_CONS | Phase59-P | H2 | 228 | CONS | OBS+SIGN | WRONG_STOP | True | False | 50 | 52.33 | 0.7153 | 18 | 20 | False | 19 | MATCHED |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | HMM0 | SUCCESS | False | True | 82 | 83.4 | 0.4405 | 20 | 20 | True | 19 | MATCHED |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | NET | SUCCESS | False | True | 82 | 83.4 | 0.4405 | 20 | 20 | True | 19 | MATCHED |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | OBS | SUCCESS | False | True | 82 | 83.4 | 0.4405 | 19 | 20 | False | 19 | MATCHED |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | SIGN | SUCCESS | False | True | 82 | 83.4 | 0.4405 | 19 | 20 | False | 19 | MATCHED |
| Phase59-P/H2_228_CONS+G18 | Phase59-P | H2 | 228 | CONS+G18 | OBS+SIGN | SUCCESS | False | True | 82 | 83.4 | 0.4405 | 19 | 20 | False | 19 | MATCHED |

## 한계

1. OBS는 창 안 거리값들이 서로 독립이라는 가정의 곱이므로 과신할 수 있다.
2. SIGN 분산은 로그의 HMM0 MAP 접선 기준으로 보정했으므로 MAP이 틀렸던 구간의 오차가 분산에 포함된다.
