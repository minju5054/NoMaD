# Phase18-RAW — 탐색적 추가 비교

| status | planned | completed | comparison | raw_goal_rule | protocol_sha256 | phase18_results_sha256 |
| --- | --- | --- | --- | --- | --- | --- |
| COMPLETE | 24 | 24 | EXPLORATORY | PHASE18_GEOMETRIC | 0b32140138b40ced900ea0ce470631c48c73e8d26ec07b452c5041cd38b43a6c | 5d6c8b8dba62e399a86c81cc808f89a37ac7e457c8b4b7443652fe41183c9c5d |

기존 Phase18 실행·결과·raw는 수정하지 않는다. 새24개 RAW와 보존된 Phase18 GRAPH-depth-CLR(OURS)·RTC-hard를 같은(scene,seed)로만 연결한다. 실행일이 다르고 사후 추가한 기준선이므로 확인 실험 판정 라벨은 부여하지 않는다.

실행기는 Phase18 PP lookahead0.25m+CURV(vmax0.3,|ω|≤0.4,기존 가속 규칙),72Hz/9Hz,1s 만료다. SP·출발 정렬·ENDPOINT latch·HMM·SAFE 필터·Graph·EC·회복은 적용하지 않는다. Depth 렌더/지도는 Phase18과 같은 부하·기록을 유지하지만 RAW 경로 선택에는 사용하지 않는다.

종료 판정은 Phase18과 동일(0.3m)

| scene | method | planned | attempted | valid | technical_failures | success | safety_failures | timeout | other_termination | arrival_n | arrival_median_s | arrival_p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW | NOMAD_RAW | 8 | 8 | 8 | 0 | 0 | 8 | 0 | 0 | 0 | — | — |
| LC | NOMAD_RAW | 8 | 8 | 8 | 0 | 6 | 1 | 1 | 0 | 6 | 34.5 | 41.431 |
| CL | NOMAD_RAW | 8 | 8 | 7 | 1 | 3 | 2 | 2 | 0 | 3 | 36.236 | 41.636 |
| ALL | NOMAD_RAW | 24 | 24 | 23 | 1 | 9 | 11 | 3 | 0 | 9 | 35.236 | 42.553 |

checkpoint는 Phase18의 저장72Hz 최초 axis>=threshold 시점 그대로다. 차이는 RAW−비교 방법(초),CI는98.33333%. seed 단위 장면 클러스터 bootstrap20,000회,seed20261030을 그대로 재사용한다. 두 방법 모두 기술 PASS이고 checkpoint가 있는 짝만 사용하며 결측은 대체하지 않는다. 도착시간은 성공 run만의 중앙값/p95다.

| scene | method | comparator | metric | n | seed_clusters | mean_difference | ci | confidence | scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NOMAD_RAW | FRESHEST-SAFE+GRAPH-depth-CLR | checkpoint_time_s | 11 | 7 | -2.4987 | [-12.228535353535353, 4.76641414141414] | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| ALL | NOMAD_RAW | FRESHEST-SAFE+RTC-hard | checkpoint_time_s | 11 | 8 | -11.432 | [-26.572731481481483, -0.7416666666666668] | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| SLW | NOMAD_RAW | FRESHEST-SAFE+GRAPH-depth-CLR | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| SLW | NOMAD_RAW | FRESHEST-SAFE+RTC-hard | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| LC | NOMAD_RAW | FRESHEST-SAFE+GRAPH-depth-CLR | checkpoint_time_s | 5 | 5 | -10.542 | [-32.477777777777774, 2.9861111111111094] | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| LC | NOMAD_RAW | FRESHEST-SAFE+RTC-hard | checkpoint_time_s | 5 | 5 | -5.2 | [-14.222222222222223, 1.1694444444444443] | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| CL | NOMAD_RAW | FRESHEST-SAFE+GRAPH-depth-CLR | checkpoint_time_s | 6 | 6 | 4.2037 | [0.36574074074073987, 7.782407407407408] | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| CL | NOMAD_RAW | FRESHEST-SAFE+RTC-hard | checkpoint_time_s | 6 | 6 | -16.625 | [-38.523148148148145, -1.9074074074074083] | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |

| index | scene | method | status | classification | success | collision | corridor | stuck | goal_time_s | checkpoint_time_s | OURS_CLR_checkpoint_s | RAW_minus_OURS_CLR_checkpoint_s | RTC_HARD_checkpoint_s | RAW_minus_RTC_HARD_checkpoint_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 66 | SLW | NOMAD_RAW | PASS | SAFETY_FAILURE | False | False | True | False | — | — | — | — | 45.819 | — |
| 66 | LC | NOMAD_RAW | PASS | SUCCESS | True | False | False | False | 31.264 | 29.042 | 29.569 | -0.52778 | — | — |
| 66 | CL | NOMAD_RAW | PASS | STUCK | False | False | False | True | — | 28.958 | 30.306 | -1.3472 | 31.153 | -2.1944 |
| 67 | SLW | NOMAD_RAW | PASS | SAFETY_FAILURE | False | False | True | False | — | — | — | — | — | — |
| 67 | LC | NOMAD_RAW | PASS | SAFETY_FAILURE | False | True | False | False | — | — | — | — | 31.111 | — |
| 67 | CL | NOMAD_RAW | PASS | SAFETY_FAILURE | False | False | True | False | — | 35.083 | 28.278 | 6.8056 | 37.153 | -2.0694 |
| 68 | SLW | NOMAD_RAW | PASS | SAFETY_FAILURE | False | False | True | False | — | — | — | — | — | — |
| 68 | LC | NOMAD_RAW | PASS | SUCCESS | True | False | False | False | 33.736 | 30.208 | 42.361 | -12.153 | 32.347 | -2.1389 |
| 68 | CL | NOMAD_RAW | PASS | SAFETY_FAILURE | False | True | False | False | — | — | 26.889 | — | 34.694 | — |
| 69 | SLW | NOMAD_RAW | PASS | SAFETY_FAILURE | False | False | True | False | — | — | — | — | — | — |
| 69 | LC | NOMAD_RAW | PASS | SUCCESS | True | False | False | False | 35.236 | 28.347 | 25.278 | 3.0694 | 31.361 | -3.0139 |
| 69 | CL | NOMAD_RAW | PASS | SUCCESS | True | False | False | False | 33.153 | 30.597 | 31.236 | -0.63889 | 34.792 | -4.1944 |
| 70 | SLW | NOMAD_RAW | PASS | SAFETY_FAILURE | False | False | True | False | — | — | — | — | 51.139 | — |
| 70 | LC | NOMAD_RAW | PASS | SUCCESS | True | False | False | False | 42.764 | 30.542 | 76.569 | -46.028 | 52.236 | -21.694 |
| 70 | CL | NOMAD_RAW | PASS | STUCK | False | False | False | True | — | 36.958 | 29.764 | 7.1944 | 77.389 | -40.431 |
| 71 | SLW | NOMAD_RAW | PASS | SAFETY_FAILURE | False | False | True | False | — | — | — | — | — | — |
| 71 | LC | NOMAD_RAW | PASS | STUCK | False | False | False | True | — | — | 25.333 | — | 31.875 | — |
| 71 | CL | NOMAD_RAW | PASS | SUCCESS | True | False | False | False | 36.236 | 33.139 | 29.278 | 3.8611 | 82.542 | -49.403 |
| 72 | SLW | NOMAD_RAW | PASS | SAFETY_FAILURE | False | False | True | False | — | — | — | — | — | — |
| 72 | LC | NOMAD_RAW | PASS | SUCCESS | True | False | False | False | 33.764 | 29.083 | 26.153 | 2.9306 | 31.611 | -2.5278 |
| 72 | CL | NOMAD_RAW | PASS | SUCCESS | True | False | False | False | 42.236 | 36.903 | 27.556 | 9.3472 | 38.361 | -1.4583 |
| 73 | SLW | NOMAD_RAW | PASS | SAFETY_FAILURE | False | False | True | False | — | — | — | — | — | — |
| 73 | LC | NOMAD_RAW | PASS | SUCCESS | True | False | False | False | 37.431 | 30.597 | — | — | 27.222 | 3.375 |
| 73 | CL | NOMAD_RAW | FAIL | TECHNICAL_FAILURE | False | — | — | — | — | — | 30.806 | — | 40.042 | — |
