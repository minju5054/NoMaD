# J1

**중간 결과, 판정 보류**

| completed_seeds | completed_seed_count | final | label | protocol_sha256 | completed_runs | planned_runs | artifact_run_records | incomplete_block_records_excluded |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [231, 232, 233, 234, 235, 236, 237, 238, 239] | 9 | False | 중간 결과, 판정 보류 | 2dbe6817a6751d04971453222baeccb971a4a0f24db6fc40ed1e4a71ec701586 | 135 | 195 | 135 | 0 |

종료 판정은 Phase18과 동일(0.3m). 공식 NoMaD argmin closest/subgoal,1s 만료,관측pose world고정/현재B 투영,PP+CURV,depth V1,SDF 등록fix,ENDPOINT latch를 공통 사용한다. 회복·STOP_WAIT 특수처리·HMM/NET 없음.

J0 선별에서 LC는 통과했고 H1-v3·SLW-v2는 미달했지만 각각 돌발 장애물·좁은 통로 평가를 위해 사용자 사전 결정으로 포함했다. seed231–243,195회,seed별15회 고정RNG 섞기. 5.5h가 지난 뒤 새seed블록은 시작하지 않고 완료된 블록까지 중간 보고하며 동일 명령으로 재개한다.

52-P 대비: 제동꼬리 적분·swept certificate·설치/36tick 검사는 동일하며, controller만 공통 Phase18 PP/CURV를 전달하고 사용자 지시대로 다음후보/0.1/STOP_WAIT 대체를 제거해 설치거절은 KEEP,주기거절은 같은 경로+stop_command 감속으로 처리한다.

OURS-noEC는 J0 실행 객체를 그대로 사용한다. RAW는 Phase18-RAW에 공통 ENDPOINT latch만 추가한다. RTC-hard는 Phase18 생성/SAFE 규칙이며 공통 제거사항을 적용한다. OURS는 SAFE 원경로 설치와 비동기Graph 보정을 각각EC로 인증한다. 원경로EC거절도 SAFE후보의Graph 시도를 막지 않으며 새chunk/STALE/만료 폐기는 동결 규칙이다.

| scene | method | planned | completed | technical_failures | success | collision | wall_intrusion | timeout | arrival_n | arrival_median_s | arrival_p95_s | checkpoint_n | checkpoint_median_s | checkpoint_p95_s | graph_applied | ec_checks | ec_rejected | solve_median_s | solve_p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | NOMAD_RAW | 13 | 9 | 0 | 5 | 1 | 3 | 0 | 5 | 57.903 | 62.908 | 5 | 56.931 | 58.125 | 0 | 0 | 0 | N/A | N/A |
| SLW-v2 | RTC-hard | 13 | 9 | 0 | 6 | 2 | 0 | 1 | 6 | 56.889 | 64.441 | 6 | 53.465 | 62.608 | 0 | 0 | 0 | N/A | N/A |
| SLW-v2 | OURS | 13 | 9 | 0 | 8 | 0 | 0 | 1 | 8 | 43.764 | 52.589 | 8 | 42.444 | 51.042 | 276 | 1258 | 18 | 0.076031 | 0.16134 |
| SLW-v2 | OURS-noGRAPH | 13 | 9 | 0 | 5 | 0 | 0 | 4 | 5 | 52.681 | 55.956 | 5 | 51.083 | 52.428 | 0 | 1531 | 101 | N/A | N/A |
| SLW-v2 | OURS-noEC | 13 | 9 | 0 | 5 | 1 | 1 | 2 | 5 | 45.917 | 59.081 | 5 | 42.931 | 54.572 | 229 | 0 | 0 | 0.076437 | 0.19527 |
| H1-v3 | NOMAD_RAW | 13 | 9 | 0 | 1 | 6 | 2 | 0 | 1 | 42.028 | 42.028 | 2 | 45.326 | 57.27 | 0 | 0 | 0 | N/A | N/A |
| H1-v3 | RTC-hard | 13 | 9 | 0 | 3 | 1 | 2 | 3 | 3 | 50.847 | 57.935 | 3 | 36.931 | 44.118 | 0 | 0 | 0 | N/A | N/A |
| H1-v3 | OURS | 13 | 9 | 0 | 3 | 0 | 0 | 6 | 3 | 46.139 | 49.914 | 3 | 36.958 | 40.796 | 251 | 1612 | 51 | 0.075704 | 0.19797 |
| H1-v3 | OURS-noGRAPH | 13 | 9 | 0 | 6 | 0 | 0 | 3 | 6 | 57.104 | 70.913 | 6 | 47.993 | 57.007 | 0 | 1545 | 83 | N/A | N/A |
| H1-v3 | OURS-noEC | 13 | 9 | 0 | 3 | 0 | 1 | 5 | 3 | 44.167 | 69.779 | 4 | 39.319 | 47.77 | 254 | 0 | 0 | 0.076587 | 0.20069 |
| LC | NOMAD_RAW | 13 | 9 | 0 | 9 | 0 | 0 | 0 | 9 | 36.806 | 68.381 | 9 | 30.403 | 63.703 | 0 | 0 | 0 | N/A | N/A |
| LC | RTC-hard | 13 | 9 | 0 | 6 | 0 | 3 | 0 | 6 | 39.799 | 64.108 | 6 | 31.556 | 55.889 | 0 | 0 | 0 | N/A | N/A |
| LC | OURS | 13 | 9 | 0 | 8 | 0 | 0 | 1 | 8 | 31.799 | 34.308 | 8 | 26.285 | 28.898 | 251 | 943 | 2 | 0.075072 | 0.14004 |
| LC | OURS-noGRAPH | 13 | 9 | 0 | 9 | 0 | 0 | 0 | 9 | 33.722 | 36.453 | 9 | 28.667 | 30.4 | 0 | 823 | 5 | N/A | N/A |
| LC | OURS-noEC | 13 | 9 | 0 | 9 | 0 | 0 | 0 | 9 | 31.319 | 47.392 | 9 | 27.472 | 42.475 | 235 | 0 | 0 | 0.075258 | 0.097502 |
| ALL | NOMAD_RAW | 39 | 27 | 0 | 15 | 7 | 5 | 0 | 15 | 42.028 | 66.489 | 16 | 40.576 | 61.656 | 0 | 0 | 0 | N/A | N/A |
| ALL | RTC-hard | 39 | 27 | 0 | 15 | 3 | 5 | 4 | 15 | 50.847 | 66.786 | 15 | 44.917 | 63.789 | 0 | 0 | 0 | N/A | N/A |
| ALL | OURS | 39 | 27 | 0 | 19 | 0 | 0 | 8 | 19 | 39.653 | 50.786 | 19 | 36.958 | 47.704 | 778 | 3813 | 71 | 0.075653 | 0.17461 |
| ALL | OURS-noGRAPH | 39 | 27 | 0 | 20 | 0 | 0 | 7 | 20 | 38 | 65.926 | 20 | 30.382 | 54.576 | 0 | 3899 | 189 | N/A | N/A |
| ALL | OURS-noEC | 39 | 27 | 0 | 17 | 1 | 2 | 7 | 17 | 42.903 | 63.003 | 18 | 34.424 | 49.814 | 718 | 0 | 0 | 0.076052 | 0.17738 |

| comparison | metric | pairs | seed_clusters | mean_difference_s | ci95_s | OURS_only_failure | noEC_only_failure | p_raw | p_holm | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OURS − RTC-hard | checkpoint_time_s | 11 | 7 | -9.1364 | [-16.886574074074073, -2.583333333333335] | N/A | N/A | 0.010099 | 0.020199 | 판정 보류 |
| OURS vs OURS-noEC | collision OR wall intrusion | 27 | N/A | N/A | N/A | 0 | 3 | 0.25 | 0.25 | 판정 보류 |

주 비교는 완료seed블록의 기술PASS·관측된 짝만 사용한다. checkpoint 결측은 대체하지 않으며 n을 표시한다. 차이=OURS−RTC,seed cluster bootstrap20,000회(seed20261030),양측95% CI,귀무가설 중심화 bootstrap p=(1+|boot−mean|≥|mean| 횟수)/(B+1). 안전실패=충돌OR벽침범,정확McNemar 양측검정. 두 p의 가족에Holm α=.05. 중간값은 탐색적으로 제시하며 전체13seed 완료 전 판정은 보류한다.

| scene | axis | direction | box_id | dynamic | threshold_m | formula |
| --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | 0 | 1 | Slalom3 | False | 4.6 | last box +x far face +0.30; identical to SLW |
| H1-v3 | 1 | 1 | DynamicObstacle | False | 1.2 | box center along +y + projected half extent + 0.30 |
| LC | 1 | 1 | AfterCorner | False | 2.4 | box center along axis + projected half extent + 0.30 |

RTC-hard의 hard-mask 검증은 전체 OLD suffix(H_old)가 아닌 앞 d개만 양쪽에서 비교한다. d=0 prefix 오차와 미정의 solve/비율은 N/A다. 공통 성공·안전실패·timeout·checkpoint 계산식과 주 비교 함수는 변경하지 않았다.

## 검증 재판정 기록

| completed_seed_blocks | RTC_reassessed | RTC_PASS | non_RTC_metrics_unchanged | protocol_unchanged | original_failure_archive |
| --- | --- | --- | --- | --- | --- |
| [231, 232, 233, 234, 235, 236, 237, 238, 239] | 27 | 27 | True | True | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/j1_01/audit_revisions/RTC_PREFIX_D_AND_INTERIM_REPORT_V1/original_metrics |

원 실패 canonical metrics와 모든 attempt_metrics는 보존했다. 같은 저장 artifacts에 검증만 다시 적용했으며 재주행·추론·solver 실행은 없다. 재개 후 RTC run도 수정된 같은 audit를 호출한다.

## 탐색적 분석 — 주 판정과 분리

아래는 저장 로그의 서술적 비교이며 주 가설·Holm 판정에 사용하지 않는다. 평균속도는 주행거리/경과시간(정지 포함), 정지는 |실제v|<1e−12의72Hz 구간이다. 곡률 감속은 활성 PP 중 0<v_target<0.3인 시간 비율이며 가속 제한만으로 낮은 명령과 EC_BRAKE는 제외한다. 먼저 checkpoint까지, 이어서 미도달 run도 포함하는 전체 주행을 별도 제시한다. 각 칸은 run별 값의 중앙값이며 미관측은 N/A다.

| scene | method | valid_runs | checkpoint_runs | checkpoint_mean_speed_m_s_median | checkpoint_curvature_slow_fraction_active_median | checkpoint_stop_s_median | checkpoint_distance_m_median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | NOMAD_RAW | 9 | 5 | 0.12634 | 0.78345 | 4.4444 | 6.9207 |
| SLW-v2 | RTC-hard | 9 | 6 | 0.13465 | 0.75275 | 4.6667 | 7.1561 |
| SLW-v2 | OURS | 9 | 8 | 0.15588 | 0.63718 | 5.6111 | 6.8303 |
| SLW-v2 | OURS-noGRAPH | 9 | 5 | 0.13305 | 0.74723 | 5.7778 | 6.7969 |
| SLW-v2 | OURS-noEC | 9 | 5 | 0.15213 | 0.66239 | 5.5556 | 6.555 |
| H1-v3 | NOMAD_RAW | 9 | 2 | 0.11906 | 0.81941 | 3.2778 | 5.2752 |
| H1-v3 | RTC-hard | 9 | 3 | 0.11927 | 0.78334 | 4.8889 | 4.2714 |
| H1-v3 | OURS | 9 | 3 | 0.13692 | 0.6961 | 4.7778 | 4.608 |
| H1-v3 | OURS-noGRAPH | 9 | 6 | 0.12405 | 0.80991 | 5.5 | 5.1294 |
| H1-v3 | OURS-noEC | 9 | 4 | 0.13139 | 0.72356 | 3.9444 | 5.3546 |
| LC | NOMAD_RAW | 9 | 9 | 0.15343 | 0.69329 | 3.6667 | 4.6764 |
| LC | RTC-hard | 9 | 6 | 0.15239 | 0.69378 | 3.7778 | 4.7635 |
| LC | OURS | 9 | 8 | 0.17926 | 0.57292 | 3.3889 | 4.7065 |
| LC | OURS-noGRAPH | 9 | 9 | 0.16384 | 0.66376 | 3.5556 | 4.6808 |
| LC | OURS-noEC | 9 | 9 | 0.17642 | 0.64136 | 3.2222 | 4.7524 |
| ALL | NOMAD_RAW | 27 | 16 | 0.1322 | 0.76731 | 3.7778 | 5.6471 |
| ALL | RTC-hard | 27 | 15 | 0.13808 | 0.74187 | 4.5556 | 5.6293 |
| ALL | OURS | 27 | 19 | 0.16172 | 0.62773 | 4.4444 | 4.76 |
| ALL | OURS-noGRAPH | 27 | 20 | 0.14788 | 0.69261 | 4.3333 | 4.7752 |
| ALL | OURS-noEC | 27 | 18 | 0.15801 | 0.65427 | 3.7222 | 4.9953 |

| scene | method | valid_runs | full_mean_speed_m_s_median | full_curvature_slow_fraction_active_median | full_stop_s_median | full_distance_m_median |
| --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | NOMAD_RAW | 9 | 0.12402 | 0.79612 | 4.5556 | 6.8966 |
| SLW-v2 | RTC-hard | 9 | 0.12907 | 0.75837 | 4.7778 | 6.9033 |
| SLW-v2 | OURS | 9 | 0.15395 | 0.65217 | 5.8889 | 7.0301 |
| SLW-v2 | OURS-noGRAPH | 9 | 0.13219 | 0.79462 | 7.7778 | 7.0527 |
| SLW-v2 | OURS-noEC | 9 | 0.14489 | 0.66989 | 6.2222 | 6.7903 |
| H1-v3 | NOMAD_RAW | 9 | 0.13564 | 0.72203 | 3.4444 | 3.1292 |
| H1-v3 | RTC-hard | 9 | 0.12358 | 0.75745 | 5.3333 | 5.7726 |
| H1-v3 | OURS | 9 | 0.091431 | 0.73373 | 32.778 | 5.9733 |
| H1-v3 | OURS-noGRAPH | 9 | 0.13154 | 0.7601 | 5.7778 | 7.203 |
| H1-v3 | OURS-noEC | 9 | 0.10586 | 0.73265 | 17.889 | 6.1368 |
| LC | NOMAD_RAW | 9 | 0.14891 | 0.71233 | 3.6667 | 5.4046 |
| LC | RTC-hard | 9 | 0.13192 | 0.77511 | 3.7778 | 5.3933 |
| LC | OURS | 9 | 0.16807 | 0.63655 | 3.5556 | 5.341 |
| LC | OURS-noGRAPH | 9 | 0.15598 | 0.68548 | 3.7778 | 5.2849 |
| LC | OURS-noEC | 9 | 0.17131 | 0.65217 | 3.7778 | 5.3287 |
| ALL | NOMAD_RAW | 27 | 0.13077 | 0.73941 | 3.6667 | 5.4046 |
| ALL | RTC-hard | 27 | 0.12907 | 0.76426 | 4.5556 | 5.9305 |
| ALL | OURS | 27 | 0.15064 | 0.64923 | 5.1111 | 6.3814 |
| ALL | OURS-noGRAPH | 27 | 0.13764 | 0.74223 | 5.4444 | 5.9349 |
| ALL | OURS-noEC | 27 | 0.14327 | 0.68774 | 5.3333 | 5.3847 |

OURS−비교법의 같은scene·seed 짝 차이(추가 p검정 없음):

| scene | comparator | pairs | OURS_only_success | other_only_success | success_difference | OURS_only_safety_failure | other_only_safety_failure | safety_difference | checkpoint_pairs | checkpoint_mean_difference_s | checkpoint_median_difference_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | OURS-noGRAPH | 9 | 4 | 1 | 3 | 0 | 0 | 0 | 4 | -7.9861 | -8.7431 |
| SLW-v2 | NOMAD_RAW | 9 | 3 | 0 | 3 | 0 | 4 | -4 | 5 | -10.808 | -10.222 |
| H1-v3 | OURS-noGRAPH | 9 | 0 | 3 | -3 | 0 | 0 | 0 | 3 | -2.8611 | -0.40278 |
| H1-v3 | NOMAD_RAW | 9 | 2 | 0 | 2 | 0 | 8 | -8 | 1 | 9.1667 | 9.1667 |
| LC | OURS-noGRAPH | 9 | 0 | 1 | -1 | 0 | 0 | 0 | 8 | -1.5799 | -1.8611 |
| LC | NOMAD_RAW | 9 | 0 | 1 | -1 | 0 | 0 | 0 | 8 | -7.1701 | -3.6528 |
| ALL | OURS-noGRAPH | 27 | 4 | 5 | -1 | 0 | 0 | 0 | 15 | -3.5444 | -2.9306 |
| ALL | NOMAD_RAW | 27 | 5 | 1 | 4 | 0 | 12 | -12 | 14 | -7.3026 | -4.9861 |

OURS EC 검사·거절(scope별; 주 판정 미사용):

| scene | scope | checks | rejected | reject_fraction |
| --- | --- | --- | --- | --- |
| SLW-v2 | SAFE_INSTALL | 404 | 5 | 0.012376 |
| SLW-v2 | GRAPH_INSTALL | 281 | 5 | 0.017794 |
| SLW-v2 | PERIODIC | 573 | 8 | 0.013962 |
| SLW-v2 | ALL | 1258 | 18 | 0.014308 |
| H1-v3 | SAFE_INSTALL | 403 | 39 | 0.096774 |
| H1-v3 | GRAPH_INSTALL | 252 | 1 | 0.0039683 |
| H1-v3 | PERIODIC | 957 | 11 | 0.011494 |
| H1-v3 | ALL | 1612 | 51 | 0.031638 |
| LC | SAFE_INSTALL | 322 | 1 | 0.0031056 |
| LC | GRAPH_INSTALL | 251 | 0 | 0 |
| LC | PERIODIC | 370 | 1 | 0.0027027 |
| LC | ALL | 943 | 2 | 0.0021209 |
| ALL | SAFE_INSTALL | 1129 | 45 | 0.039858 |
| ALL | GRAPH_INSTALL | 784 | 6 | 0.0076531 |
| ALL | PERIODIC | 1900 | 20 | 0.010526 |
| ALL | ALL | 3813 | 71 | 0.018621 |

H1-v3 OURS timeout의 종료 위치와 마지막 정지 위치(종료 때 움직였으면 stationary_at_end=False):

| index | key | final_x_m | final_y_m | final_goal_distance_m | stationary_at_end | last_stop_x_m | last_stop_y_m | last_stop_start_s | last_stop_end_s | total_stop_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 232 | H1-v3_232_D750_OURS | 4.0723 | -0.80464 | 4.0784 | True | 4.0723 | -0.80464 | 50.681 | 90 | 47.667 |
| 233 | H1-v3_233_D750_OURS | 2.267 | 0.48266 | 2.9071 | True | 2.267 | 0.48266 | 14.903 | 90 | 78.111 |
| 235 | H1-v3_235_D750_OURS | -0.045314 | -0.0813 | 4.6859 | False | 0.56549 | -0.077231 | 84.569 | 84.667 | 32.778 |
| 236 | H1-v3_236_D750_OURS | 2.9608 | 0.33274 | 2.8873 | True | 2.9608 | 0.33274 | 19.792 | 90 | 73.556 |
| 238 | H1-v3_238_D750_OURS | 2.8683 | 0.33284 | 2.8995 | True | 2.8683 | 0.33284 | 21.681 | 90 | 71.222 |
| 239 | H1-v3_239_D750_OURS | 2.8777 | -0.028192 | 3.2557 | False | 2.4717 | -0.49528 | 86.903 | 87 | 3.6667 |

H1-v3 top-down 그림은 사전 요청 범위 seed231–238의 OURS·OURS-noGRAPH·NOMAD_RAW만 표시한다.

![saved trajectory](figures/j1_interim/H1-v3_231_NOMAD_RAW.png)

![saved trajectory](figures/j1_interim/H1-v3_231_OURS-noGRAPH.png)

![saved trajectory](figures/j1_interim/H1-v3_231_OURS.png)

![saved trajectory](figures/j1_interim/H1-v3_232_NOMAD_RAW.png)

![saved trajectory](figures/j1_interim/H1-v3_232_OURS-noGRAPH.png)

![saved trajectory](figures/j1_interim/H1-v3_232_OURS.png)

![saved trajectory](figures/j1_interim/H1-v3_233_NOMAD_RAW.png)

![saved trajectory](figures/j1_interim/H1-v3_233_OURS-noGRAPH.png)

![saved trajectory](figures/j1_interim/H1-v3_233_OURS.png)

![saved trajectory](figures/j1_interim/H1-v3_234_NOMAD_RAW.png)

![saved trajectory](figures/j1_interim/H1-v3_234_OURS-noGRAPH.png)

![saved trajectory](figures/j1_interim/H1-v3_234_OURS.png)

![saved trajectory](figures/j1_interim/H1-v3_235_NOMAD_RAW.png)

![saved trajectory](figures/j1_interim/H1-v3_235_OURS-noGRAPH.png)

![saved trajectory](figures/j1_interim/H1-v3_235_OURS.png)

![saved trajectory](figures/j1_interim/H1-v3_236_NOMAD_RAW.png)

![saved trajectory](figures/j1_interim/H1-v3_236_OURS-noGRAPH.png)

![saved trajectory](figures/j1_interim/H1-v3_236_OURS.png)

![saved trajectory](figures/j1_interim/H1-v3_237_NOMAD_RAW.png)

![saved trajectory](figures/j1_interim/H1-v3_237_OURS-noGRAPH.png)

![saved trajectory](figures/j1_interim/H1-v3_237_OURS.png)

![saved trajectory](figures/j1_interim/H1-v3_238_NOMAD_RAW.png)

![saved trajectory](figures/j1_interim/H1-v3_238_OURS-noGRAPH.png)

![saved trajectory](figures/j1_interim/H1-v3_238_OURS.png)
