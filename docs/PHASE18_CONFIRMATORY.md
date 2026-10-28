# 사전 등록 확인 실험 — Phase 18

Protocol SHA256: `a49ed0492b7cd646747784e436cc4e48a7db4075e6d09950d01be16d2bb0bbfa`  
실행 Git SHA: `c4b7c4541aa6f86e97f92d0f8f32c2248fafc3e8`

SLW·LC·CL의 Phase17 scene/reference/Topomap 및 성공한 게이트 6회를 hash 검증 후 재사용했다. 새로운 게이트/Topomap 주행은 없다. 여섯 방법 모두 동일 depth 선택·fallback·회복을 사용한다. NoMaD 입력은 RGB이며 depth는 noisy V1 지도에만 사용한다. 시뮬레이터 pose 사용으로 odometry 오차가 없다고 가정한다. Oracle은 사후 평가에만 사용한다. SE(2) kinematic Isaac Sim 결과이며 실제 로봇/PhysX 동역학 검증이 아니다.

## 주 판정

| comparator | n | seed_clusters | mean_difference | ci | H1 | CLR_success | comparator_success | CLR_safety_failures | comparator_safety_failures | H2 | safety | combined |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FRESHEST-SAFE+HERMITE | 12 | 8 | -0.93634 | [-2.756944444444444, 0.6060125830959173] | INCONCLUSIVE | 14 | 16 | 8 | 7 | NONINFERIOR | SAFETY_OK | PARTIAL |
| FRESHEST-SAFE+TEMPORAL-ENSEMBLE | 11 | 8 | 2.6225 | [-4.131944444444443, 13.449990503323903] | INSUFFICIENT_PAIRS | 14 | 16 | 8 | 3 | NONINFERIOR | SAFETY_NOT_OK | NOT_CONFIRMED |
| FRESHEST-SAFE+RTC-hard | 13 | 8 | -9.6731 | [-19.211805555555554, -2.6474358974358956] | FASTER | 14 | 15 | 8 | 7 | NONINFERIOR | SAFETY_OK | CONFIRMED |

20,000회 paired seed-cluster bootstrap, seed 20261030. 같은 seed의 scene들을 함께 재표집한다. 세 비교에 Bonferroni α=.05/3, 정확한 CI 수준 98.333333%를 적용한다. checkpoint 결측은 대체하지 않고 양쪽 유효 checkpoint가 있는 쌍만 사용한다. FASTER/SLOWER에는 n≥12가 필요하다. H2는 사용자 고정 count 기준(성공 −3, 안전 실패 +1)이며 통계적 비열등성 검정으로 확대 해석하지 않는다.

기술 실패 처리: `INCONCLUSIVE`. 기술 실패를 장애물 충돌·벽 침범으로 세지 않는다.

## 보조 판정 (95% CI, 무보정)

| comparator | metric | n | mean_difference | ci | label |
| --- | --- | --- | --- | --- | --- |
| FRESHEST-SAFE+GRAPH-depth | minimum_oracle_clearance_m | 24 | 0.016918 | [-0.02118562668972268, 0.05028390623102705] | NOT_SHOWN |
| FRESHEST-SAFE+GRAPH-depth | checkpoint_time_s | 13 | 1.5491 | [-0.4976851851851851, 4.298933531746005] | DESCRIPTIVE |
| FRESHEST-SAFE | checkpoint_time_s | 14 | 2.5367 | [-2.118055555555555, 9.783119658119658] | DESCRIPTIVE |

| method | planned | valid | technical_failures | success | safety_failures | collision | corridor | timeout | no_detour_success | goal_time_s | checkpoint_time_s | minimum_oracle_clearance_m | minimum_obstacle_clearance_m | recovery_count | stop_wait_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FRESHEST-SAFE | 24 | 24 | 0 | 18 | 5 | 3 | 2 | 1 | 18 | {'n': 18, 'median': 34.583333333333336, 'p95': 51.88472222222221} | {'n': 18, 'median': 30.041666666666664, 'p95': 50.07569444444444} | {'n': 24, 'median': 0.10835051058198336, 'p95': 0.2982334869127273} | {'n': 24, 'median': 0.13068542879511266, 'p95': 0.3134872838850103} | 11 | 30 |
| FRESHEST-SAFE+HERMITE | 24 | 24 | 0 | 16 | 7 | 4 | 3 | 1 | 16 | {'n': 16, 'median': 34.36805555555556, 'p95': 63.08680555555556} | {'n': 16, 'median': 30.61111111111111, 'p95': 60.24652777777778} | {'n': 24, 'median': 0.07972574366042903, 'p95': 0.1840190327614521} | {'n': 24, 'median': 0.13835328500588367, 'p95': 0.2704679748451819} | 16 | 42 |
| FRESHEST-SAFE+TEMPORAL-ENSEMBLE | 24 | 24 | 0 | 16 | 3 | 1 | 2 | 5 | 15 | {'n': 16, 'median': 36.70833333333333, 'p95': 67.46527777777777} | {'n': 16, 'median': 32.74305555555556, 'p95': 63.22916666666667} | {'n': 24, 'median': 0.04710056446217517, 'p95': 0.20341666750674356} | {'n': 24, 'median': 0.09506084224351524, 'p95': 0.21030538797313109} | 24 | 63 |
| FRESHEST-SAFE+RTC-hard | 24 | 24 | 0 | 15 | 7 | 1 | 6 | 2 | 13 | {'n': 15, 'median': 41.34722222222222, 'p95': 65.99027777777775} | {'n': 17, 'median': 34.791666666666664, 'p95': 78.41944444444444} | {'n': 24, 'median': 0.0507200301390192, 'p95': 0.1971892821758471} | {'n': 24, 'median': 0.1053875234781496, 'p95': 0.22446430723783703} | 7 | 23 |
| FRESHEST-SAFE+GRAPH-depth | 24 | 24 | 0 | 15 | 7 | 3 | 4 | 2 | 15 | {'n': 15, 'median': 31.51388888888889, 'p95': 38.590277777777764} | {'n': 15, 'median': 28.48611111111111, 'p95': 35.034722222222214} | {'n': 24, 'median': 0.09119428242611957, 'p95': 0.15639010853763435} | {'n': 24, 'median': 0.1048647146967111, 'p95': 0.16277684325937947} | 14 | 32 |
| FRESHEST-SAFE+GRAPH-depth-CLR | 24 | 24 | 0 | 14 | 8 | 2 | 6 | 2 | 13 | {'n': 14, 'median': 31.555555555555557, 'p95': 57.25833333333332} | {'n': 14, 'median': 29.42361111111111, 'p95': 54.33402777777776} | {'n': 24, 'median': 0.08627461071334924, 'p95': 0.24070160221715398} | {'n': 24, 'median': 0.15844807397420319, 'p95': 0.24070160221715398} | 15 | 42 |

## Scene별 서술용 판정 지표

| scene | comparator | n | mean_difference | ci | CLR_counts | comparator_counts |
| --- | --- | --- | --- | --- | --- | --- |
| SLW | FRESHEST-SAFE+HERMITE | 0 | — | — | {'method': 'FRESHEST-SAFE+GRAPH-depth-CLR', 'scene': 'SLW', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 0, 'safety_failures': 6, 'collision': 1, 'corridor': 5, 'timeout': 2} | {'method': 'FRESHEST-SAFE+HERMITE', 'scene': 'SLW', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 2, 'safety_failures': 5, 'collision': 4, 'corridor': 1, 'timeout': 1} |
| SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | 0 | — | — | {'method': 'FRESHEST-SAFE+GRAPH-depth-CLR', 'scene': 'SLW', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 0, 'safety_failures': 6, 'collision': 1, 'corridor': 5, 'timeout': 2} | {'method': 'FRESHEST-SAFE+TEMPORAL-ENSEMBLE', 'scene': 'SLW', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 3, 'safety_failures': 3, 'collision': 1, 'corridor': 2, 'timeout': 2} |
| SLW | FRESHEST-SAFE+RTC-hard | 0 | — | — | {'method': 'FRESHEST-SAFE+GRAPH-depth-CLR', 'scene': 'SLW', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 0, 'safety_failures': 6, 'collision': 1, 'corridor': 5, 'timeout': 2} | {'method': 'FRESHEST-SAFE+RTC-hard', 'scene': 'SLW', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 2, 'safety_failures': 6, 'collision': 1, 'corridor': 5, 'timeout': 0} |
| LC | FRESHEST-SAFE+HERMITE | 4 | 3.3438 | [-3.0590277777777777, 12.409722222222225] | {'method': 'FRESHEST-SAFE+GRAPH-depth-CLR', 'scene': 'LC', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 6, 'safety_failures': 2, 'collision': 1, 'corridor': 1, 'timeout': 0} | {'method': 'FRESHEST-SAFE+HERMITE', 'scene': 'LC', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 6, 'safety_failures': 2, 'collision': 0, 'corridor': 2, 'timeout': 0} |
| LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | 3 | 20.495 | [-2.125, 47.97222222222222] | {'method': 'FRESHEST-SAFE+GRAPH-depth-CLR', 'scene': 'LC', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 6, 'safety_failures': 2, 'collision': 1, 'corridor': 1, 'timeout': 0} | {'method': 'FRESHEST-SAFE+TEMPORAL-ENSEMBLE', 'scene': 'LC', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 5, 'safety_failures': 0, 'collision': 0, 'corridor': 0, 'timeout': 3} |
| LC | FRESHEST-SAFE+RTC-hard | 5 | 3.2528 | [-6.266666666666667, 18.249999999999996] | {'method': 'FRESHEST-SAFE+GRAPH-depth-CLR', 'scene': 'LC', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 6, 'safety_failures': 2, 'collision': 1, 'corridor': 1, 'timeout': 0} | {'method': 'FRESHEST-SAFE+RTC-hard', 'scene': 'LC', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 6, 'safety_failures': 1, 'collision': 0, 'corridor': 1, 'timeout': 1} |
| CL | FRESHEST-SAFE+HERMITE | 8 | -3.0764 | [-6.701432291666667, -1.1267361111111103] | {'method': 'FRESHEST-SAFE+GRAPH-depth-CLR', 'scene': 'CL', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 8, 'safety_failures': 0, 'collision': 0, 'corridor': 0, 'timeout': 0} | {'method': 'FRESHEST-SAFE+HERMITE', 'scene': 'CL', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 8, 'safety_failures': 0, 'collision': 0, 'corridor': 0, 'timeout': 0} |
| CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | 8 | -4.0799 | [-7.675940393518518, -1.284722222222221] | {'method': 'FRESHEST-SAFE+GRAPH-depth-CLR', 'scene': 'CL', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 8, 'safety_failures': 0, 'collision': 0, 'corridor': 0, 'timeout': 0} | {'method': 'FRESHEST-SAFE+TEMPORAL-ENSEMBLE', 'scene': 'CL', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 8, 'safety_failures': 0, 'collision': 0, 'corridor': 0, 'timeout': 0} |
| CL | FRESHEST-SAFE+RTC-hard | 8 | -17.752 | [-35.23454861111111, -5.059027777777777] | {'method': 'FRESHEST-SAFE+GRAPH-depth-CLR', 'scene': 'CL', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 8, 'safety_failures': 0, 'collision': 0, 'corridor': 0, 'timeout': 0} | {'method': 'FRESHEST-SAFE+RTC-hard', 'scene': 'CL', 'planned': 8, 'attempted': 8, 'valid': 8, 'technical_failures': 0, 'success': 7, 'safety_failures': 0, 'collision': 0, 'corridor': 0, 'timeout': 1} |

| scene | method | valid | success | safety_failures | timeout | goal_time_s | checkpoint_time_s | minimum_oracle_clearance_m |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW | FRESHEST-SAFE | 8 | 3 | 4 | 1 | {'n': 3, 'median': 50.513888888888886, 'p95': 58.73888888888889} | {'n': 3, 'median': 49.02777777777778, 'p95': 55.31527777777777} | {'n': 8, 'median': 0.007293330916886581, 'p95': 0.11016357788127475} |
| SLW | FRESHEST-SAFE+HERMITE | 8 | 2 | 5 | 1 | {'n': 2, 'median': 68.25694444444444, 'p95': 77.56319444444445} | {'n': 2, 'median': 65.07638888888889, 'p95': 73.7701388888889} | {'n': 8, 'median': -4.72264380009241e-05, 'p95': 0.03386303848178295} |
| SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | 8 | 3 | 3 | 2 | {'n': 3, 'median': 49.111111111111114, 'p95': 59.57361111111111} | {'n': 3, 'median': 48.708333333333336, 'p95': 56.333333333333336} | {'n': 8, 'median': 0.017585961273411083, 'p95': 0.04221727775812446} |
| SLW | FRESHEST-SAFE+RTC-hard | 8 | 2 | 6 | 0 | {'n': 2, 'median': 51.38194444444444, 'p95': 54.388194444444444} | {'n': 2, 'median': 48.479166666666664, 'p95': 50.87291666666666} | {'n': 8, 'median': -0.0005237714936038656, 'p95': 0.055165339037283566} |
| SLW | FRESHEST-SAFE+GRAPH-depth | 8 | 1 | 6 | 1 | {'n': 1, 'median': 44.47222222222222, 'p95': 44.47222222222222} | {'n': 1, 'median': 39.65277777777778, 'p95': 39.65277777777778} | {'n': 8, 'median': -0.00024536888048848023, 'p95': 0.029106663485543898} |
| SLW | FRESHEST-SAFE+GRAPH-depth-CLR | 8 | 0 | 6 | 2 | {'n': 0, 'median': None, 'p95': None} | {'n': 0, 'median': None, 'p95': None} | {'n': 8, 'median': -0.00039226945486706133, 'p95': 0.021388131697423332} |
| LC | FRESHEST-SAFE | 8 | 7 | 1 | 0 | {'n': 7, 'median': 34.19444444444444, 'p95': 37.52083333333333} | {'n': 7, 'median': 29.430555555555557, 'p95': 30.74861111111111} | {'n': 8, 'median': 0.17724484071927607, 'p95': 0.3187440348297589} |
| LC | FRESHEST-SAFE+HERMITE | 8 | 6 | 2 | 0 | {'n': 6, 'median': 33.0, 'p95': 34.72569444444444} | {'n': 6, 'median': 26.97222222222222, 'p95': 29.006944444444443} | {'n': 8, 'median': 0.15853980195647838, 'p95': 0.24219361578233983} |
| LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | 8 | 5 | 0 | 3 | {'n': 5, 'median': 34.27777777777778, 'p95': 77.06666666666665} | {'n': 5, 'median': 28.27777777777778, 'p95': 70.81944444444443} | {'n': 8, 'median': 0.16430016771310763, 'p95': 0.20904705009834354} |
| LC | FRESHEST-SAFE+RTC-hard | 8 | 6 | 1 | 1 | {'n': 6, 'median': 40.09027777777778, 'p95': 55.576388888888886} | {'n': 7, 'median': 31.61111111111111, 'p95': 46.26944444444443} | {'n': 8, 'median': 0.1352996229910935, 'p95': 0.21901823560450995} |
| LC | FRESHEST-SAFE+GRAPH-depth | 8 | 6 | 1 | 1 | {'n': 6, 'median': 31.34722222222222, 'p95': 33.00347222222222} | {'n': 6, 'median': 25.944444444444443, 'p95': 28.052083333333336} | {'n': 8, 'median': 0.10688748151159314, 'p95': 0.2260031773746807} |
| LC | FRESHEST-SAFE+GRAPH-depth-CLR | 8 | 6 | 2 | 0 | {'n': 6, 'median': 33.22222222222222, 'p95': 71.45833333333333} | {'n': 6, 'median': 27.86111111111111, 'p95': 68.01736111111111} | {'n': 8, 'median': 0.14273692363138588, 'p95': 0.28162163364903614} |
| CL | FRESHEST-SAFE | 8 | 8 | 0 | 0 | {'n': 8, 'median': 33.91666666666667, 'p95': 37.425} | {'n': 8, 'median': 30.625, 'p95': 33.99236111111111} | {'n': 8, 'median': 0.13068542879511266, 'p95': 0.1561770956815458} |
| CL | FRESHEST-SAFE+HERMITE | 8 | 8 | 0 | 0 | {'n': 8, 'median': 35.173611111111114, 'p95': 41.14861111111111} | {'n': 8, 'median': 32.00694444444444, 'p95': 36.757638888888884} | {'n': 8, 'median': 0.11267395977526298, 'p95': 0.13232798196813267} |
| CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | 8 | 8 | 0 | 0 | {'n': 8, 'median': 36.70833333333333, 'p95': 42.59236111111111} | {'n': 8, 'median': 32.74305555555556, 'p95': 37.53680555555555} | {'n': 8, 'median': 0.07629135246577332, 'p95': 0.14332135667544724} |
| CL | FRESHEST-SAFE+RTC-hard | 8 | 7 | 0 | 1 | {'n': 7, 'median': 41.34722222222222, 'p95': 73.45694444444442} | {'n': 8, 'median': 37.75694444444444, 'p95': 80.73819444444445} | {'n': 8, 'median': 0.057753354856638475, 'p95': 0.11317565992938841} |
| CL | FRESHEST-SAFE+GRAPH-depth | 8 | 8 | 0 | 0 | {'n': 8, 'median': 32.75694444444444, 'p95': 35.418055555555554} | {'n': 8, 'median': 28.979166666666668, 'p95': 32.34097222222222} | {'n': 8, 'median': 0.1086151010203566, 'p95': 0.15457917753957864} |
| CL | FRESHEST-SAFE+GRAPH-depth-CLR | 8 | 8 | 0 | 0 | {'n': 8, 'median': 31.555555555555557, 'p95': 35.41041666666666} | {'n': 8, 'median': 29.520833333333336, 'p95': 31.085416666666667} | {'n': 8, 'median': 0.13661605162670526, 'p95': 0.18823924735785053} |

## Seed × scene × 방법

| index | scene | method | classification | checkpoint_time_s | goal_time_s | minimum_oracle_clearance_m |
| --- | --- | --- | --- | --- | --- | --- |
| 66 | CL | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 30.306 | 32.194 | 0.076908 |
| 66 | CL | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 31.014 | 33.903 | 0.054685 |
| 66 | CL | FRESHEST-SAFE+HERMITE | SUCCESS | 32.181 | 35.472 | 0.064897 |
| 66 | CL | FRESHEST-SAFE+RTC-hard | SUCCESS | 31.153 | 32.903 | 0.08401 |
| 66 | CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 32.028 | 34.458 | 0.061614 |
| 66 | CL | FRESHEST-SAFE | SUCCESS | 31.153 | 33.028 | 0.14542 |
| 67 | CL | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 28.278 | 30.917 | 0.1226 |
| 67 | CL | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 29.403 | 31.292 | 0.10434 |
| 67 | CL | FRESHEST-SAFE+HERMITE | SUCCESS | 29.431 | 30.819 | 0.13007 |
| 67 | CL | FRESHEST-SAFE+RTC-hard | SUCCESS | 37.153 | 39.917 | 0.093368 |
| 67 | CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 34.681 | 38.417 | 0.047561 |
| 67 | CL | FRESHEST-SAFE | SUCCESS | 31.458 | 36.125 | 0.098227 |
| 68 | CL | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 26.889 | 28.222 | 0.18844 |
| 68 | CL | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 26.958 | 29.153 | 0.15014 |
| 68 | CL | FRESHEST-SAFE+HERMITE | SUCCESS | 38.931 | 43.083 | 0.077175 |
| 68 | CL | FRESHEST-SAFE+RTC-hard | SUCCESS | 34.694 | 38.875 | 0.01612 |
| 68 | CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 39 | 44.056 | 0.025787 |
| 68 | CL | FRESHEST-SAFE | SUCCESS | 33.875 | 36.069 | 0.041582 |
| 69 | CL | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 31.236 | 34.083 | 0.18786 |
| 69 | CL | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 29.153 | 34.208 | 0.15697 |
| 69 | CL | FRESHEST-SAFE+HERMITE | SUCCESS | 32.722 | 34.875 | 0.09926 |
| 69 | CL | FRESHEST-SAFE+RTC-hard | SUCCESS | 34.792 | 41.347 | 0.11974 |
| 69 | CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 32.417 | 35 | 0.14184 |
| 69 | CL | FRESHEST-SAFE | SUCCESS | 34.056 | 38.125 | 0.063423 |
| 70 | CL | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 29.764 | 36.125 | 0.18212 |
| 70 | CL | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 27.208 | 32.403 | 0.11289 |
| 70 | CL | FRESHEST-SAFE+HERMITE | SUCCESS | 31.069 | 33.181 | 0.082277 |
| 70 | CL | FRESHEST-SAFE+RTC-hard | STUCK | 77.389 | — | 0.026967 |
| 70 | CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 29.819 | 34.792 | 0.090969 |
| 70 | CL | FRESHEST-SAFE | SUCCESS | 29.986 | 34.806 | 0.1231 |
| 71 | CL | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 29.278 | 30.792 | 0.095641 |
| 71 | CL | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 28.486 | 29.611 | 0.069151 |
| 71 | CL | FRESHEST-SAFE+HERMITE | SUCCESS | 30.153 | 32.278 | 0.12802 |
| 71 | CL | FRESHEST-SAFE+RTC-hard | SUCCESS | 82.542 | 84.278 | 0.0094111 |
| 71 | CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 30.917 | 34.903 | 0.099153 |
| 71 | CL | FRESHEST-SAFE | SUCCESS | 30.097 | 32.764 | 0.16151 |
| 72 | CL | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 27.556 | 29.222 | 0.11471 |
| 72 | CL | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 28.806 | 33.111 | 0.10086 |
| 72 | CL | FRESHEST-SAFE+HERMITE | SUCCESS | 32.403 | 37.556 | 0.13354 |
| 72 | CL | FRESHEST-SAFE+RTC-hard | SUCCESS | 38.361 | 48.208 | 0.031496 |
| 72 | CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 34.819 | 39.875 | 0.14412 |
| 72 | CL | FRESHEST-SAFE | SUCCESS | 29.847 | 31.208 | 0.13827 |
| 73 | CL | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 30.806 | 33.597 | 0.15063 |
| 73 | CL | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 33.056 | 36.069 | 0.12985 |
| 73 | CL | FRESHEST-SAFE+HERMITE | SUCCESS | 31.833 | 36.181 | 0.12609 |
| 73 | CL | FRESHEST-SAFE+RTC-hard | SUCCESS | 40.042 | 44.681 | 0.10099 |
| 73 | CL | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 33.069 | 39.236 | 0.04664 |
| 73 | CL | FRESHEST-SAFE | SUCCESS | 29.292 | 32.889 | 0.14628 |
| 66 | LC | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 29.569 | 35.694 | 0.30193 |
| 66 | LC | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 25.736 | 31.292 | 0.10539 |
| 66 | LC | FRESHEST-SAFE+HERMITE | SUCCESS | 26.097 | 33.861 | 0.17113 |
| 66 | LC | FRESHEST-SAFE+RTC-hard | STUCK | — | — | 0.10978 |
| 66 | LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | STUCK | — | — | 0.002089 |
| 66 | LC | FRESHEST-SAFE | SUCCESS | 26.167 | 31.972 | 0.11921 |
| 67 | LC | FRESHEST-SAFE+GRAPH-depth-CLR | SAFETY_FAILURE | — | — | -0.00052032 |
| 67 | LC | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 28.528 | 33.5 | 0.26526 |
| 67 | LC | FRESHEST-SAFE+HERMITE | SUCCESS | 26.972 | 30.361 | 0.18629 |
| 67 | LC | FRESHEST-SAFE+RTC-hard | SAFETY_FAILURE | 31.111 | — | -0.0014083 |
| 67 | LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 28.167 | 32.833 | 0.17966 |
| 67 | LC | FRESHEST-SAFE | SUCCESS | 29.431 | 34.361 | 0.31514 |
| 68 | LC | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 42.361 | 44.833 | 0.060332 |
| 68 | LC | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 24.333 | 28.139 | 0.098331 |
| 68 | LC | FRESHEST-SAFE+HERMITE | SUCCESS | 26.972 | 32.681 | 0.16731 |
| 68 | LC | FRESHEST-SAFE+RTC-hard | SUCCESS | 32.347 | 47.847 | 0.098647 |
| 68 | LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 26.722 | 34.278 | 0.14894 |
| 68 | LC | FRESHEST-SAFE | SUCCESS | 31.111 | 33.181 | 0.32069 |
| 69 | LC | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 25.278 | 28.611 | 0.22256 |
| 69 | LC | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 25.736 | 31.403 | 0.10838 |
| 69 | LC | FRESHEST-SAFE+HERMITE | SAFETY_FAILURE | — | — | -0.00034409 |
| 69 | LC | FRESHEST-SAFE+RTC-hard | SUCCESS | 31.361 | 40.931 | 0.17372 |
| 69 | LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | STUCK | — | — | 0.0044723 |
| 69 | LC | FRESHEST-SAFE | SUCCESS | 28.458 | 34.194 | 0.20244 |
| 70 | LC | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 76.569 | 80.333 | 0.14566 |
| 70 | LC | FRESHEST-SAFE+GRAPH-depth | SAFETY_FAILURE | — | — | -0.0011161 |
| 70 | LC | FRESHEST-SAFE+HERMITE | SAFETY_FAILURE | — | — | -1.3828e-05 |
| 70 | LC | FRESHEST-SAFE+RTC-hard | SUCCESS | 52.236 | 58.153 | 0.15708 |
| 70 | LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 28.597 | 31.764 | 0.12228 |
| 70 | LC | FRESHEST-SAFE | SUCCESS | 29.903 | 38.417 | 0.15422 |
| 71 | LC | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 25.333 | 30.75 | 0.2439 |
| 71 | LC | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 26.153 | 31.514 | 0.12212 |
| 71 | LC | FRESHEST-SAFE+HERMITE | SUCCESS | 27.444 | 33.319 | 0.14976 |
| 71 | LC | FRESHEST-SAFE+RTC-hard | SUCCESS | 31.875 | 39.25 | 0.20133 |
| 71 | LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | STUCK | — | — | 0.21125 |
| 71 | LC | FRESHEST-SAFE | SUCCESS | 28.597 | 33.569 | 0.081128 |
| 72 | LC | FRESHEST-SAFE+GRAPH-depth-CLR | SUCCESS | 26.153 | 30.389 | 0.13982 |
| 72 | LC | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 26.625 | 29.5 | 0.084057 |
| 72 | LC | FRESHEST-SAFE+HERMITE | SUCCESS | 29.528 | 35.014 | 0.14664 |
| 72 | LC | FRESHEST-SAFE+RTC-hard | SUCCESS | 31.611 | 37.764 | 0.22854 |
| 72 | LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 28.278 | 34.722 | 0.20496 |
| 72 | LC | FRESHEST-SAFE | SUCCESS | 29.861 | 35.431 | 0.20027 |
| 73 | LC | FRESHEST-SAFE+GRAPH-depth-CLR | SAFETY_FAILURE | — | — | -0.00036082 |
| 73 | LC | FRESHEST-SAFE+GRAPH-depth | STUCK | — | — | 0.1531 |
| 73 | LC | FRESHEST-SAFE+HERMITE | SUCCESS | 25.181 | 28.875 | 0.27229 |
| 73 | LC | FRESHEST-SAFE+RTC-hard | SUCCESS | 27.222 | 36.375 | 0.11352 |
| 73 | LC | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 81.375 | 87.653 | 0.19469 |
| 73 | LC | FRESHEST-SAFE | SAFETY_FAILURE | — | — | -0.00028997 |
| 66 | SLW | FRESHEST-SAFE+GRAPH-depth-CLR | SAFETY_FAILURE | — | — | -0.0017076 |
| 66 | SLW | FRESHEST-SAFE+GRAPH-depth | SAFETY_FAILURE | — | — | -0.00033781 |
| 66 | SLW | FRESHEST-SAFE+HERMITE | SAFETY_FAILURE | — | — | -0.0010136 |
| 66 | SLW | FRESHEST-SAFE+RTC-hard | SUCCESS | 45.819 | 48.042 | 0.065538 |
| 66 | SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SAFETY_FAILURE | — | — | -0.00043558 |
| 66 | SLW | FRESHEST-SAFE | SUCCESS | 49.028 | 50.514 | 0.10231 |
| 67 | SLW | FRESHEST-SAFE+GRAPH-depth-CLR | SAFETY_FAILURE | — | — | -0.0013485 |
| 67 | SLW | FRESHEST-SAFE+GRAPH-depth | SAFETY_FAILURE | — | — | -0.00051493 |
| 67 | SLW | FRESHEST-SAFE+HERMITE | SAFETY_FAILURE | — | — | -0.00044653 |
| 67 | SLW | FRESHEST-SAFE+RTC-hard | SAFETY_FAILURE | — | — | -0.00053912 |
| 67 | SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 48.708 | 49.111 | 0.043074 |
| 67 | SLW | FRESHEST-SAFE | SUCCESS | 45.153 | 46.764 | 0.046759 |
| 68 | SLW | FRESHEST-SAFE+GRAPH-depth-CLR | SAFETY_FAILURE | — | — | -0.00044135 |
| 68 | SLW | FRESHEST-SAFE+GRAPH-depth | SAFETY_FAILURE | — | — | -0.00015293 |
| 68 | SLW | FRESHEST-SAFE+HERMITE | STUCK | — | — | 0.028753 |
| 68 | SLW | FRESHEST-SAFE+RTC-hard | SAFETY_FAILURE | — | — | -0.00050843 |
| 68 | SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 57.181 | 60.736 | 0.02301 |
| 68 | SLW | FRESHEST-SAFE | SAFETY_FAILURE | — | — | -0.00046556 |
| 69 | SLW | FRESHEST-SAFE+GRAPH-depth-CLR | STUCK | — | — | 0.02304 |
| 69 | SLW | FRESHEST-SAFE+GRAPH-depth | SAFETY_FAILURE | — | — | -0.00010174 |
| 69 | SLW | FRESHEST-SAFE+HERMITE | SAFETY_FAILURE | — | — | -3.8379e-05 |
| 69 | SLW | FRESHEST-SAFE+RTC-hard | SAFETY_FAILURE | — | — | -0.00047827 |
| 69 | SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | STUCK | — | — | 0.035643 |
| 69 | SLW | FRESHEST-SAFE | SUCCESS | 56.014 | 59.653 | 0.11439 |
| 70 | SLW | FRESHEST-SAFE+GRAPH-depth-CLR | SAFETY_FAILURE | — | — | -5.2649e-05 |
| 70 | SLW | FRESHEST-SAFE+GRAPH-depth | STUCK | — | — | 0.01341 |
| 70 | SLW | FRESHEST-SAFE+HERMITE | SUCCESS | 55.417 | 57.917 | 0.036615 |
| 70 | SLW | FRESHEST-SAFE+RTC-hard | SUCCESS | 51.139 | 54.722 | 0.035902 |
| 70 | SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SUCCESS | 41.819 | 45.403 | 0.040626 |
| 70 | SLW | FRESHEST-SAFE | SAFETY_FAILURE | — | — | -0.0019716 |
| 71 | SLW | FRESHEST-SAFE+GRAPH-depth-CLR | SAFETY_FAILURE | — | — | -0.00046749 |
| 71 | SLW | FRESHEST-SAFE+GRAPH-depth | SUCCESS | 39.653 | 44.472 | 0.037559 |
| 71 | SLW | FRESHEST-SAFE+HERMITE | SAFETY_FAILURE | — | — | -5.6074e-05 |
| 71 | SLW | FRESHEST-SAFE+RTC-hard | SAFETY_FAILURE | — | — | -0.0014541 |
| 71 | SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | STUCK | — | — | 0.012162 |
| 71 | SLW | FRESHEST-SAFE | SAFETY_FAILURE | — | — | -0.0001829 |
| 72 | SLW | FRESHEST-SAFE+GRAPH-depth-CLR | STUCK | — | — | 0.01832 |
| 72 | SLW | FRESHEST-SAFE+GRAPH-depth | SAFETY_FAILURE | — | — | -0.00049425 |
| 72 | SLW | FRESHEST-SAFE+HERMITE | SAFETY_FAILURE | — | — | -0.00020232 |
| 72 | SLW | FRESHEST-SAFE+RTC-hard | SAFETY_FAILURE | — | — | -0.0026459 |
| 72 | SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SAFETY_FAILURE | — | — | -0.00038375 |
| 72 | SLW | FRESHEST-SAFE | STUCK | — | — | 0.01477 |
| 73 | SLW | FRESHEST-SAFE+GRAPH-depth-CLR | SAFETY_FAILURE | — | — | -0.00034319 |
| 73 | SLW | FRESHEST-SAFE+GRAPH-depth | SAFETY_FAILURE | — | — | -0.00056413 |
| 73 | SLW | FRESHEST-SAFE+HERMITE | SUCCESS | 74.736 | 78.597 | 0.0036607 |
| 73 | SLW | FRESHEST-SAFE+RTC-hard | SAFETY_FAILURE | — | — | -0.00056992 |
| 73 | SLW | FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SAFETY_FAILURE | — | — | -0.0034431 |
| 73 | SLW | FRESHEST-SAFE | SAFETY_FAILURE | — | — | -0.00043455 |

## RTC·회복·fallback·Graph

| method | inference_ms | rtc_inference_count | rtc_d0_count | rtc_prefix_run_median_m | rtc_prefix_max_m | recovery_count | recovery_limit_runs | recovery_time_fraction | recovery_safe_outcomes | recovery_observed_outcomes | keep_active_count | keep_active_fraction | stop_wait_count | stop_wait_fraction | graph_calls | graph_acceptance | graph_initialization_rejected | graph_solve_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FRESHEST-SAFE | {'n': 884, 'median': 36.8550515, 'p95': 55.276426349999994} | 0 | 0 | {'n': 0, 'median': None, 'p95': None} | — | 11 | 0 | {'n': 24, 'median': 0.0, 'p95': 0.15247164461247628} | 5 | 11 | 1 | {'n': 24, 'median': 0.0, 'p95': 0.0} | 30 | {'n': 24, 'median': 0.0, 'p95': 0.09553829685471564} | 0 | — | 0 | {'n': 0, 'median': None, 'p95': None} |
| FRESHEST-SAFE+HERMITE | {'n': 917, 'median': 36.972657, 'p95': 54.782455199999994} | 0 | 0 | {'n': 0, 'median': None, 'p95': None} | — | 16 | 0 | {'n': 24, 'median': 0.0, 'p95': 0.09875938782639071} | 4 | 16 | 3 | {'n': 24, 'median': 0.0, 'p95': 0.02228696285506185} | 42 | {'n': 24, 'median': 0.0, 'p95': 0.08746375815646001} | 0 | — | 0 | {'n': 0, 'median': None, 'p95': None} |
| FRESHEST-SAFE+TEMPORAL-ENSEMBLE | {'n': 1189, 'median': 36.42046, 'p95': 54.195071199999994} | 0 | 0 | {'n': 0, 'median': None, 'p95': None} | — | 24 | 0 | {'n': 24, 'median': 0.0, 'p95': 0.09560481616993163} | 8 | 24 | 1 | {'n': 24, 'median': 0.0, 'p95': 0.0} | 63 | {'n': 24, 'median': 0.011012542061792597, 'p95': 0.06557112871555283} | 0 | — | 0 | {'n': 0, 'median': None, 'p95': None} |
| FRESHEST-SAFE+RTC-hard | {'n': 1077, 'median': 71.994073, 'p95': 108.26236159999998} | 1077 | 199 | {'n': 24, 'median': 8.252513485638904e-09, 'p95': 9.294446799223242e-09} | 1.1073e-07 | 7 | 0 | {'n': 24, 'median': 0.0, 'p95': 0.051023206751054824} | 5 | 7 | 1 | {'n': 24, 'median': 0.0, 'p95': 0.0} | 23 | {'n': 24, 'median': 0.0, 'p95': 0.05592405173471124} | 0 | — | 0 | {'n': 0, 'median': None, 'p95': None} |
| FRESHEST-SAFE+GRAPH-depth | {'n': 887, 'median': 36.832825, 'p95': 55.0067994} | 0 | 0 | {'n': 0, 'median': None, 'p95': None} | — | 14 | 0 | {'n': 24, 'median': 0.0, 'p95': 0.08964244507618552} | 7 | 14 | 2 | {'n': 24, 'median': 0.0, 'p95': 0.0016441005802707305} | 32 | {'n': 24, 'median': 0.0, 'p95': 0.07479424464017263} | 818 | 0.72861 | 150 | {'n': 665, 'median': 0.06772270100191236, 'p95': 0.13443056340329348} |
| FRESHEST-SAFE+GRAPH-depth-CLR | {'n': 898, 'median': 36.7853715, 'p95': 55.062891} | 0 | 0 | {'n': 0, 'median': None, 'p95': None} | — | 15 | 0 | {'n': 24, 'median': 0.0, 'p95': 0.1224228175309519} | 2 | 15 | 1 | {'n': 24, 'median': 0.0, 'p95': 0.0} | 42 | {'n': 24, 'median': 0.0, 'p95': 0.09475061728395069} | 819 | 0.68864 | 147 | {'n': 665, 'median': 0.07370555799570866, 'p95': 0.18799595701275393} |

RTC는 **RTC hard-masking ablation (DDPM adaptation)**: 보호된 Phase8 β=5/RePaint 코드 그대로이며 원 논문의 flow-policy RTC와 동일한 구현이라고 주장하지 않는다. 관측 순간 active OLD로 Y를 구성하고 T_est=0.888536777s 규칙을 유지했다. d=0은 기존 soft-guidance(W≠0) 또는 무-guidance(W=0) 분기를 그대로 따른다. 추론 추가 비용을 빼거나 보정하지 않았다. RTC prefix error는 모든 sample의 d-prefix point와 Y local point의 위치 오차이며 기존 rtc_prefix_error 정의를 유지한다.

최소 oracle clearance는 상자와 외곽 벽의 footprint clearance 최솟값이며 상자만의 값도 별도 기록한다. 안전 실패는 충돌 또는 벽 침범 run의 합집합이다. 중단 run의 최소 거리는 실행된 구간만 평가하므로 경로 길이가 다를 수 있다. Scene별 지표는 서술용이며 추가 주 가설 검정을 만들지 않는다.

## 기술 실패

None.

![checkpoint_by_method](../research/results/phase18/checkpoint_by_method.png)

![clearance_by_method](../research/results/phase18/clearance_by_method.png)

![failure_CL_FRESHEST-SAFE+RTC-hard_70](../research/results/phase18/failure_CL_FRESHEST-SAFE+RTC-hard_70.png)

![failure_LC_FRESHEST-SAFE+GRAPH-depth-CLR_67](../research/results/phase18/failure_LC_FRESHEST-SAFE+GRAPH-depth-CLR_67.png)

![failure_LC_FRESHEST-SAFE+GRAPH-depth-CLR_73](../research/results/phase18/failure_LC_FRESHEST-SAFE+GRAPH-depth-CLR_73.png)

![failure_LC_FRESHEST-SAFE+GRAPH-depth_70](../research/results/phase18/failure_LC_FRESHEST-SAFE+GRAPH-depth_70.png)

![failure_LC_FRESHEST-SAFE+GRAPH-depth_73](../research/results/phase18/failure_LC_FRESHEST-SAFE+GRAPH-depth_73.png)

![failure_LC_FRESHEST-SAFE+HERMITE_69](../research/results/phase18/failure_LC_FRESHEST-SAFE+HERMITE_69.png)

![failure_LC_FRESHEST-SAFE+HERMITE_70](../research/results/phase18/failure_LC_FRESHEST-SAFE+HERMITE_70.png)

![failure_LC_FRESHEST-SAFE+RTC-hard_66](../research/results/phase18/failure_LC_FRESHEST-SAFE+RTC-hard_66.png)

![failure_LC_FRESHEST-SAFE+RTC-hard_67](../research/results/phase18/failure_LC_FRESHEST-SAFE+RTC-hard_67.png)

![failure_LC_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_66](../research/results/phase18/failure_LC_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_66.png)

![failure_LC_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_69](../research/results/phase18/failure_LC_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_69.png)

![failure_LC_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_71](../research/results/phase18/failure_LC_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_71.png)

![failure_LC_FRESHEST-SAFE_73](../research/results/phase18/failure_LC_FRESHEST-SAFE_73.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_66](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_66.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_67](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_67.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_68](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_68.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_69](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_69.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_70](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_70.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_71](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_71.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_72](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_72.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_73](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth-CLR_73.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth_66](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth_66.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth_67](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth_67.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth_68](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth_68.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth_69](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth_69.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth_70](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth_70.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth_72](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth_72.png)

![failure_SLW_FRESHEST-SAFE+GRAPH-depth_73](../research/results/phase18/failure_SLW_FRESHEST-SAFE+GRAPH-depth_73.png)

![failure_SLW_FRESHEST-SAFE+HERMITE_66](../research/results/phase18/failure_SLW_FRESHEST-SAFE+HERMITE_66.png)

![failure_SLW_FRESHEST-SAFE+HERMITE_67](../research/results/phase18/failure_SLW_FRESHEST-SAFE+HERMITE_67.png)

![failure_SLW_FRESHEST-SAFE+HERMITE_68](../research/results/phase18/failure_SLW_FRESHEST-SAFE+HERMITE_68.png)

![failure_SLW_FRESHEST-SAFE+HERMITE_69](../research/results/phase18/failure_SLW_FRESHEST-SAFE+HERMITE_69.png)

![failure_SLW_FRESHEST-SAFE+HERMITE_71](../research/results/phase18/failure_SLW_FRESHEST-SAFE+HERMITE_71.png)

![failure_SLW_FRESHEST-SAFE+HERMITE_72](../research/results/phase18/failure_SLW_FRESHEST-SAFE+HERMITE_72.png)

![failure_SLW_FRESHEST-SAFE+RTC-hard_67](../research/results/phase18/failure_SLW_FRESHEST-SAFE+RTC-hard_67.png)

![failure_SLW_FRESHEST-SAFE+RTC-hard_68](../research/results/phase18/failure_SLW_FRESHEST-SAFE+RTC-hard_68.png)

![failure_SLW_FRESHEST-SAFE+RTC-hard_69](../research/results/phase18/failure_SLW_FRESHEST-SAFE+RTC-hard_69.png)

![failure_SLW_FRESHEST-SAFE+RTC-hard_71](../research/results/phase18/failure_SLW_FRESHEST-SAFE+RTC-hard_71.png)

![failure_SLW_FRESHEST-SAFE+RTC-hard_72](../research/results/phase18/failure_SLW_FRESHEST-SAFE+RTC-hard_72.png)

![failure_SLW_FRESHEST-SAFE+RTC-hard_73](../research/results/phase18/failure_SLW_FRESHEST-SAFE+RTC-hard_73.png)

![failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_66](../research/results/phase18/failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_66.png)

![failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_69](../research/results/phase18/failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_69.png)

![failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_71](../research/results/phase18/failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_71.png)

![failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_72](../research/results/phase18/failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_72.png)

![failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_73](../research/results/phase18/failure_SLW_FRESHEST-SAFE+TEMPORAL-ENSEMBLE_73.png)

![failure_SLW_FRESHEST-SAFE_68](../research/results/phase18/failure_SLW_FRESHEST-SAFE_68.png)

![failure_SLW_FRESHEST-SAFE_70](../research/results/phase18/failure_SLW_FRESHEST-SAFE_70.png)

![failure_SLW_FRESHEST-SAFE_71](../research/results/phase18/failure_SLW_FRESHEST-SAFE_71.png)

![failure_SLW_FRESHEST-SAFE_72](../research/results/phase18/failure_SLW_FRESHEST-SAFE_72.png)

![failure_SLW_FRESHEST-SAFE_73](../research/results/phase18/failure_SLW_FRESHEST-SAFE_73.png)

![paired_diff](../research/results/phase18/paired_diff.png)

![paths_CL](../research/results/phase18/paths_CL.png)

![paths_LC](../research/results/phase18/paths_LC.png)

![paths_SLW](../research/results/phase18/paths_SLW.png)

