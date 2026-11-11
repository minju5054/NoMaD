# Phase18-RAW — 탐색적 추가 비교

| status | planned | completed | comparison | raw_goal_rule | protocol_sha256 | phase18_results_sha256 |
| --- | --- | --- | --- | --- | --- | --- |
| PREPARED_NOT_RUN | 24 | 0 | EXPLORATORY | PHASE18_GEOMETRIC | ba70b619885c4c5e66c560d4dcc29925c30974f18e2782ee644bad6df31bf056 | 5d6c8b8dba62e399a86c81cc808f89a37ac7e457c8b4b7443652fe41183c9c5d |

기존 Phase18 실행·결과·raw는 수정하지 않는다. 새24개 RAW와 보존된 Phase18 GRAPH-depth-CLR(OURS)·RTC-hard를 같은(scene,seed)로만 연결한다. 실행일이 다르고 사후 추가한 기준선이므로 확인 실험 판정 라벨은 부여하지 않는다.

실행기는 Phase18 PP lookahead0.25m+CURV(vmax0.3,|ω|≤0.4,기존 가속 규칙),72Hz/9Hz,1s 만료다. SP·출발 정렬·ENDPOINT latch·HMM·SAFE 필터·Graph·EC·회복은 적용하지 않는다. Depth 렌더/지도는 Phase18과 같은 부하·기록을 유지하지만 RAW 경로 선택에는 사용하지 않는다.

종료 판정은 Phase18과 동일(0.3m)

| scene | method | planned | attempted | valid | technical_failures | success | safety_failures | timeout | other_termination | arrival_n | arrival_median_s | arrival_p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW | NOMAD_RAW | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — |
| LC | NOMAD_RAW | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — |
| CL | NOMAD_RAW | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — |
| ALL | NOMAD_RAW | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — |

checkpoint는 Phase18의 저장72Hz 최초 axis>=threshold 시점 그대로다. 차이는 RAW−비교 방법(초),CI는98.33333%. seed 단위 장면 클러스터 bootstrap20,000회,seed20261030을 그대로 재사용한다. 두 방법 모두 기술 PASS이고 checkpoint가 있는 짝만 사용하며 결측은 대체하지 않는다. 도착시간은 성공 run만의 중앙값/p95다.

| scene | method | comparator | metric | n | seed_clusters | mean_difference | ci | confidence | scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NOMAD_RAW | FRESHEST-SAFE+GRAPH-depth-CLR | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| ALL | NOMAD_RAW | FRESHEST-SAFE+RTC-hard | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| SLW | NOMAD_RAW | FRESHEST-SAFE+GRAPH-depth-CLR | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| SLW | NOMAD_RAW | FRESHEST-SAFE+RTC-hard | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| LC | NOMAD_RAW | FRESHEST-SAFE+GRAPH-depth-CLR | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| LC | NOMAD_RAW | FRESHEST-SAFE+RTC-hard | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| CL | NOMAD_RAW | FRESHEST-SAFE+GRAPH-depth-CLR | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |
| CL | NOMAD_RAW | FRESHEST-SAFE+RTC-hard | checkpoint_time_s | 0 | 0 | — | — | 0.98333 | EXPLORATORY different-day same-seed comparison;no confirmatory label |

| index | scene | method | status | classification | success | collision | corridor | stuck | goal_time_s | checkpoint_time_s | OURS_CLR_checkpoint_s | RAW_minus_OURS_CLR_checkpoint_s | RTC_HARD_checkpoint_s | RAW_minus_RTC_HARD_checkpoint_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 66 | SLW | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | 45.819 | — |
| 66 | LC | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 29.569 | — | — | — |
| 66 | CL | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 30.306 | — | 31.153 | — |
| 67 | SLW | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — |
| 67 | LC | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | 31.111 | — |
| 67 | CL | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 28.278 | — | 37.153 | — |
| 68 | SLW | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — |
| 68 | LC | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 42.361 | — | 32.347 | — |
| 68 | CL | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 26.889 | — | 34.694 | — |
| 69 | SLW | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — |
| 69 | LC | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 25.278 | — | 31.361 | — |
| 69 | CL | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 31.236 | — | 34.792 | — |
| 70 | SLW | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | 51.139 | — |
| 70 | LC | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 76.569 | — | 52.236 | — |
| 70 | CL | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 29.764 | — | 77.389 | — |
| 71 | SLW | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — |
| 71 | LC | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 25.333 | — | 31.875 | — |
| 71 | CL | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 29.278 | — | 82.542 | — |
| 72 | SLW | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — |
| 72 | LC | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 26.153 | — | 31.611 | — |
| 72 | CL | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 27.556 | — | 38.361 | — |
| 73 | SLW | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — |
| 73 | LC | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | 27.222 | — |
| 73 | CL | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | 30.806 | — | 40.042 | — |
