# J1

**중간 결과, 판정 보류**

| completed_seeds | completed_seed_count | final | label | protocol_sha256 | completed_runs | planned_runs |
| --- | --- | --- | --- | --- | --- | --- |
| [231, 232, 233, 234, 235, 236, 237, 238, 239] | 9 | False | 중간 결과, 판정 보류 | 2dbe6817a6751d04971453222baeccb971a4a0f24db6fc40ed1e4a71ec701586 | 135 | 195 |

종료 판정은 Phase18과 동일(0.3m). 공식 NoMaD argmin closest/subgoal,1s 만료,관측pose world고정/현재B 투영,PP+CURV,depth V1,SDF 등록fix,ENDPOINT latch를 공통 사용한다. 회복·STOP_WAIT 특수처리·HMM/NET 없음.

J0 선별에서 LC는 통과했고 H1-v3·SLW-v2는 미달했지만 각각 돌발 장애물·좁은 통로 평가를 위해 사용자 사전 결정으로 포함했다. seed231–243,195회,seed별15회 고정RNG 섞기. 5.5h가 지난 뒤 새seed블록은 시작하지 않고 완료된 블록까지 중간 보고하며 동일 명령으로 재개한다.

52-P 대비: 제동꼬리 적분·swept certificate·설치/36tick 검사는 동일하며, controller만 공통 Phase18 PP/CURV를 전달하고 사용자 지시대로 다음후보/0.1/STOP_WAIT 대체를 제거해 설치거절은 KEEP,주기거절은 같은 경로+stop_command 감속으로 처리한다.

OURS-noEC는 J0 실행 객체를 그대로 사용한다. RAW는 Phase18-RAW에 공통 ENDPOINT latch만 추가한다. RTC-hard는 Phase18 생성/SAFE 규칙이며 공통 제거사항을 적용한다. OURS는 SAFE 원경로 설치와 비동기Graph 보정을 각각EC로 인증한다. 원경로EC거절도 SAFE후보의Graph 시도를 막지 않으며 새chunk/STALE/만료 폐기는 동결 규칙이다.

| scene | method | planned | completed | technical_failures | success | collision | wall_intrusion | timeout | arrival_n | arrival_median_s | arrival_p95_s | checkpoint_n | checkpoint_median_s | checkpoint_p95_s | graph_applied | ec_checks | ec_rejected | solve_median_s | solve_p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | NOMAD_RAW | 13 | 9 | 0 | 5 | 1 | 3 | 0 | 5 | 57.903 | 62.908 | 5 | 56.931 | 58.125 | 0 | 0 | 0 | — | — |
| SLW-v2 | RTC-hard | 13 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | — | — | 0 | 0 | 0 | — | — |
| SLW-v2 | OURS | 13 | 9 | 0 | 8 | 0 | 0 | 1 | 8 | 43.764 | 52.589 | 8 | 42.444 | 51.042 | 276 | 1258 | 18 | 0.076031 | 0.16134 |
| SLW-v2 | OURS-noGRAPH | 13 | 9 | 0 | 5 | 0 | 0 | 4 | 5 | 52.681 | 55.956 | 5 | 51.083 | 52.428 | 0 | 1531 | 101 | — | — |
| SLW-v2 | OURS-noEC | 13 | 9 | 0 | 5 | 1 | 1 | 2 | 5 | 45.917 | 59.081 | 5 | 42.931 | 54.572 | 229 | 0 | 0 | 0.076437 | 0.19527 |
| H1-v3 | NOMAD_RAW | 13 | 9 | 0 | 1 | 6 | 2 | 0 | 1 | 42.028 | 42.028 | 2 | 45.326 | 57.27 | 0 | 0 | 0 | — | — |
| H1-v3 | RTC-hard | 13 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | — | — | 0 | 0 | 0 | — | — |
| H1-v3 | OURS | 13 | 9 | 0 | 3 | 0 | 0 | 6 | 3 | 46.139 | 49.914 | 3 | 36.958 | 40.796 | 251 | 1612 | 51 | 0.075704 | 0.19797 |
| H1-v3 | OURS-noGRAPH | 13 | 9 | 0 | 6 | 0 | 0 | 3 | 6 | 57.104 | 70.913 | 6 | 47.993 | 57.007 | 0 | 1545 | 83 | — | — |
| H1-v3 | OURS-noEC | 13 | 9 | 0 | 3 | 0 | 1 | 5 | 3 | 44.167 | 69.779 | 4 | 39.319 | 47.77 | 254 | 0 | 0 | 0.076587 | 0.20069 |
| LC | NOMAD_RAW | 13 | 9 | 0 | 9 | 0 | 0 | 0 | 9 | 36.806 | 68.381 | 9 | 30.403 | 63.703 | 0 | 0 | 0 | — | — |
| LC | RTC-hard | 13 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | — | — | 0 | 0 | 0 | — | — |
| LC | OURS | 13 | 9 | 0 | 8 | 0 | 0 | 1 | 8 | 31.799 | 34.308 | 8 | 26.285 | 28.898 | 251 | 943 | 2 | 0.075072 | 0.14004 |
| LC | OURS-noGRAPH | 13 | 9 | 0 | 9 | 0 | 0 | 0 | 9 | 33.722 | 36.453 | 9 | 28.667 | 30.4 | 0 | 823 | 5 | — | — |
| LC | OURS-noEC | 13 | 9 | 0 | 9 | 0 | 0 | 0 | 9 | 31.319 | 47.392 | 9 | 27.472 | 42.475 | 235 | 0 | 0 | 0.075258 | 0.097502 |
| ALL | NOMAD_RAW | 39 | 27 | 0 | 15 | 7 | 5 | 0 | 15 | 42.028 | 66.489 | 16 | 40.576 | 61.656 | 0 | 0 | 0 | — | — |
| ALL | RTC-hard | 39 | 27 | 27 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | — | — | 0 | 0 | 0 | — | — |
| ALL | OURS | 39 | 27 | 0 | 19 | 0 | 0 | 8 | 19 | 39.653 | 50.786 | 19 | 36.958 | 47.704 | 778 | 3813 | 71 | 0.075653 | 0.17461 |
| ALL | OURS-noGRAPH | 39 | 27 | 0 | 20 | 0 | 0 | 7 | 20 | 38 | 65.926 | 20 | 30.382 | 54.576 | 0 | 3899 | 189 | — | — |
| ALL | OURS-noEC | 39 | 27 | 0 | 17 | 1 | 2 | 7 | 17 | 42.903 | 63.003 | 18 | 34.424 | 49.814 | 718 | 0 | 0 | 0.076052 | 0.17738 |

| comparison | metric | pairs | mean_difference_s | ci95_s | p_raw | p_holm | decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OURS − RTC-hard | checkpoint_time_s | 0 | — | — | — | — | 판정 보류 |
| OURS vs OURS-noEC | collision OR wall intrusion | 27 | — | — | 0.25 | 0.5 | 판정 보류 |

주 비교는 완료seed블록의 기술PASS·관측된 짝만 사용한다. checkpoint 결측은 대체하지 않으며 n을 표시한다. 차이=OURS−RTC,seed cluster bootstrap20,000회(seed20261030),양측95% CI,귀무가설 중심화 bootstrap p=(1+|boot−mean|≥|mean| 횟수)/(B+1). 안전실패=충돌OR벽침범,정확McNemar 양측검정. 두 p의 가족에Holm α=.05. 중간값은 탐색적으로 제시하며 전체13seed 완료 전 판정은 보류한다.

| scene | axis | direction | box_id | dynamic | threshold_m | formula |
| --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | 0 | 1 | Slalom3 | False | 4.6 | last box +x far face +0.30; identical to SLW |
| H1-v3 | 1 | 1 | DynamicObstacle | False | 1.2 | box center along +y + projected half extent + 0.30 |
| LC | 1 | 1 | AfterCorner | False | 2.4 | box center along axis + projected half extent + 0.30 |
