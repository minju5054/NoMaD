# J1

**최종 결과**

| completed_seeds | completed_seed_count | final | label | protocol_sha256 | completed_runs | planned_runs | artifact_run_records | incomplete_block_records_excluded |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243] | 13 | True | 최종 결과 | 2dbe6817a6751d04971453222baeccb971a4a0f24db6fc40ed1e4a71ec701586 | 195 | 195 | 195 | 0 |

종료 판정은 Phase18과 동일(0.3m). 공식 NoMaD argmin closest/subgoal,1s 만료,관측pose world고정/현재B 투영,PP+CURV,depth V1,SDF 등록fix,ENDPOINT latch를 공통 사용한다. 회복·STOP_WAIT 특수처리·HMM/NET 없음.

J0 선별에서 LC는 통과했고 H1-v3·SLW-v2는 미달했지만 각각 돌발 장애물·좁은 통로 평가를 위해 사용자 사전 결정으로 포함했다. seed231–243,195회,seed별15회 고정RNG 섞기. 5.5h가 지난 뒤 새seed블록은 시작하지 않고 완료된 블록까지 중간 보고하며 동일 명령으로 재개한다.

52-P 대비: 제동꼬리 적분·swept certificate·설치/36tick 검사는 동일하며, controller만 공통 Phase18 PP/CURV를 전달하고 사용자 지시대로 다음후보/0.1/STOP_WAIT 대체를 제거해 설치거절은 KEEP,주기거절은 같은 경로+stop_command 감속으로 처리한다.

OURS-noEC는 J0 실행 객체를 그대로 사용한다. RAW는 Phase18-RAW에 공통 ENDPOINT latch만 추가한다. RTC-hard는 Phase18 생성/SAFE 규칙이며 공통 제거사항을 적용한다. OURS는 SAFE 원경로 설치와 비동기Graph 보정을 각각EC로 인증한다. 원경로EC거절도 SAFE후보의Graph 시도를 막지 않으며 새chunk/STALE/만료 폐기는 동결 규칙이다.

| scene | method | planned | completed | technical_failures | success | collision | wall_intrusion | timeout | arrival_n | arrival_median_s | arrival_p95_s | checkpoint_n | checkpoint_median_s | checkpoint_p95_s | graph_applied | ec_checks | ec_rejected | solve_median_s | solve_p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | NOMAD_RAW | 13 | 13 | 0 | 7 | 1 | 5 | 0 | 7 | 53.569 | 62.411 | 7 | 52.722 | 58.028 | 0 | 0 | 0 | N/A | N/A |
| SLW-v2 | RTC-hard | 13 | 13 | 0 | 8 | 3 | 1 | 1 | 8 | 54.333 | 64.006 | 9 | 51.431 | 61.806 | 0 | 0 | 0 | N/A | N/A |
| SLW-v2 | OURS | 13 | 13 | 0 | 12 | 0 | 0 | 1 | 12 | 45.549 | 51.933 | 12 | 43.181 | 49.828 | 413 | 1794 | 26 | 0.075692 | 0.15815 |
| SLW-v2 | OURS-noGRAPH | 13 | 13 | 0 | 7 | 0 | 0 | 6 | 7 | 52.681 | 55.711 | 7 | 50.639 | 52.406 | 0 | 2203 | 123 | N/A | N/A |
| SLW-v2 | OURS-noEC | 13 | 13 | 0 | 9 | 1 | 1 | 2 | 9 | 46.639 | 57.564 | 9 | 45.569 | 52.653 | 365 | 0 | 0 | 0.076349 | 0.18145 |
| H1-v3 | NOMAD_RAW | 13 | 13 | 0 | 1 | 9 | 3 | 0 | 1 | 42.028 | 42.028 | 2 | 45.326 | 57.27 | 0 | 0 | 0 | N/A | N/A |
| H1-v3 | RTC-hard | 13 | 13 | 0 | 3 | 5 | 2 | 3 | 3 | 50.847 | 57.935 | 4 | 40.924 | 49.639 | 0 | 0 | 0 | N/A | N/A |
| H1-v3 | OURS | 13 | 13 | 0 | 5 | 0 | 0 | 8 | 5 | 47.125 | 56.467 | 5 | 38.25 | 43.3 | 365 | 2318 | 56 | 0.075867 | 0.19229 |
| H1-v3 | OURS-noGRAPH | 13 | 13 | 0 | 8 | 0 | 0 | 5 | 8 | 50.229 | 70.201 | 8 | 40.34 | 56.66 | 0 | 2148 | 139 | N/A | N/A |
| H1-v3 | OURS-noEC | 13 | 13 | 0 | 6 | 0 | 2 | 5 | 6 | 43.535 | 66.312 | 7 | 35.556 | 46.943 | 356 | 0 | 0 | 0.075831 | 0.19291 |
| LC | NOMAD_RAW | 13 | 13 | 0 | 12 | 0 | 0 | 1 | 12 | 36.458 | 67.435 | 12 | 30.167 | 62.826 | 0 | 0 | 0 | N/A | N/A |
| LC | RTC-hard | 13 | 13 | 0 | 10 | 0 | 3 | 0 | 10 | 44.049 | 63.597 | 10 | 32.382 | 57.591 | 0 | 0 | 0 | N/A | N/A |
| LC | OURS | 13 | 13 | 0 | 11 | 0 | 0 | 2 | 11 | 31.875 | 34.41 | 11 | 26.417 | 29.431 | 390 | 1480 | 3 | 0.075352 | 0.14922 |
| LC | OURS-noGRAPH | 13 | 13 | 0 | 13 | 0 | 0 | 0 | 13 | 33.694 | 49.797 | 13 | 28.667 | 44.622 | 0 | 1277 | 6 | N/A | N/A |
| LC | OURS-noEC | 13 | 13 | 0 | 13 | 0 | 0 | 0 | 13 | 31.319 | 46.022 | 13 | 26.597 | 40.956 | 333 | 0 | 0 | 0.074997 | 0.10229 |
| ALL | NOMAD_RAW | 39 | 39 | 0 | 20 | 10 | 8 | 1 | 20 | 39.965 | 64.913 | 21 | 32.056 | 60.194 | 0 | 0 | 0 | N/A | N/A |
| ALL | RTC-hard | 39 | 39 | 0 | 21 | 8 | 6 | 4 | 21 | 50.903 | 65.528 | 23 | 45.694 | 63.21 | 0 | 0 | 0 | N/A | N/A |
| ALL | OURS | 39 | 39 | 0 | 28 | 0 | 0 | 11 | 28 | 42.958 | 52.589 | 28 | 38.083 | 46.825 | 1168 | 5592 | 85 | 0.075638 | 0.16683 |
| ALL | OURS-noGRAPH | 39 | 39 | 0 | 28 | 0 | 0 | 11 | 28 | 38.84 | 67.917 | 28 | 30.382 | 56.66 | 0 | 5628 | 268 | N/A | N/A |
| ALL | OURS-noEC | 39 | 39 | 0 | 28 | 1 | 3 | 7 | 28 | 41.896 | 58.264 | 29 | 35.556 | 48.597 | 1054 | 0 | 0 | 0.07573 | 0.17271 |

| comparison | metric | pairs | seed_clusters | mean_difference_s | ci95_s | OURS_only_failure | noEC_only_failure | p_raw | p_holm | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OURS − RTC-hard | checkpoint_time_s | 17 | 10 | -9.8652 | [-15.01157711988304, -5.216112557870374] | N/A | N/A | 9.9995e-05 | 0.00019999 | REJECT_H0 |
| OURS vs OURS-noEC | collision OR wall intrusion | 39 | N/A | N/A | N/A | 0 | 4 | 0.125 | 0.125 | NOT_REJECTED |

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
| SLW-v2 | NOMAD_RAW | 13 | 7 | 0.12873 | 0.77534 | 4.4444 | 6.7869 |
| SLW-v2 | RTC-hard | 13 | 9 | 0.13808 | 0.73734 | 4.7778 | 7.0909 |
| SLW-v2 | OURS | 13 | 12 | 0.15363 | 0.65129 | 4.9444 | 6.834 |
| SLW-v2 | OURS-noGRAPH | 13 | 7 | 0.13314 | 0.74723 | 5.7778 | 6.7969 |
| SLW-v2 | OURS-noEC | 13 | 9 | 0.15026 | 0.66928 | 5 | 6.7024 |
| H1-v3 | NOMAD_RAW | 13 | 2 | 0.11906 | 0.81941 | 3.2778 | 5.2752 |
| H1-v3 | RTC-hard | 13 | 4 | 0.12059 | 0.78864 | 4.3889 | 4.9503 |
| H1-v3 | OURS | 13 | 5 | 0.12839 | 0.71318 | 4.7778 | 4.7297 |
| H1-v3 | OURS-noGRAPH | 13 | 8 | 0.12638 | 0.77362 | 5.2778 | 4.7347 |
| H1-v3 | OURS-noEC | 13 | 7 | 0.13236 | 0.7381 | 3.7778 | 4.3844 |
| LC | NOMAD_RAW | 13 | 12 | 0.1527 | 0.67945 | 3.6667 | 4.6706 |
| LC | RTC-hard | 13 | 10 | 0.14879 | 0.70371 | 4.1111 | 4.8456 |
| LC | OURS | 13 | 11 | 0.17753 | 0.58404 | 3.3333 | 4.7014 |
| LC | OURS-noGRAPH | 13 | 13 | 0.16466 | 0.66376 | 3.5556 | 4.6826 |
| LC | OURS-noEC | 13 | 13 | 0.17642 | 0.62332 | 3.3333 | 4.7524 |
| ALL | NOMAD_RAW | 39 | 21 | 0.13489 | 0.74479 | 3.8889 | 4.8531 |
| ALL | RTC-hard | 39 | 23 | 0.13808 | 0.7244 | 4.5556 | 6.4452 |
| ALL | OURS | 39 | 28 | 0.15994 | 0.63718 | 4.2222 | 4.9178 |
| ALL | OURS-noGRAPH | 39 | 28 | 0.14546 | 0.69261 | 4.3333 | 4.7954 |
| ALL | OURS-noEC | 39 | 29 | 0.15153 | 0.66239 | 3.7778 | 4.9005 |

| scene | method | valid_runs | full_mean_speed_m_s_median | full_curvature_slow_fraction_active_median | full_stop_s_median | full_distance_m_median |
| --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | NOMAD_RAW | 13 | 0.12952 | 0.76751 | 4.3333 | 6.7998 |
| SLW-v2 | RTC-hard | 13 | 0.13261 | 0.73602 | 4.7778 | 6.9033 |
| SLW-v2 | OURS | 13 | 0.15254 | 0.66793 | 5 | 7.1324 |
| SLW-v2 | OURS-noGRAPH | 13 | 0.12898 | 0.79462 | 7.7778 | 7.0527 |
| SLW-v2 | OURS-noEC | 13 | 0.14864 | 0.66989 | 5.4444 | 6.9837 |
| H1-v3 | NOMAD_RAW | 13 | 0.12926 | 0.73506 | 3.4444 | 3.1292 |
| H1-v3 | RTC-hard | 13 | 0.12414 | 0.75702 | 4.6667 | 4.6174 |
| H1-v3 | OURS | 13 | 0.091431 | 0.73684 | 32.778 | 5.9733 |
| H1-v3 | OURS-noGRAPH | 13 | 0.13154 | 0.75105 | 6.4444 | 6.5571 |
| H1-v3 | OURS-noEC | 13 | 0.12887 | 0.73265 | 5.3333 | 5.9468 |
| LC | NOMAD_RAW | 13 | 0.14664 | 0.71233 | 4 | 5.3905 |
| LC | RTC-hard | 13 | 0.13192 | 0.76426 | 4.1111 | 5.4192 |
| LC | OURS | 13 | 0.16695 | 0.63655 | 3.5556 | 5.3411 |
| LC | OURS-noGRAPH | 13 | 0.156 | 0.68548 | 3.7778 | 5.3091 |
| LC | OURS-noEC | 13 | 0.17131 | 0.61258 | 3.7778 | 5.3791 |
| ALL | NOMAD_RAW | 39 | 0.13077 | 0.73941 | 3.7778 | 5.3094 |
| ALL | RTC-hard | 39 | 0.12993 | 0.75423 | 4.5556 | 6.0521 |
| ALL | OURS | 39 | 0.14998 | 0.65217 | 4.7778 | 6.4562 |
| ALL | OURS-noGRAPH | 39 | 0.13586 | 0.74223 | 5.4444 | 5.9349 |
| ALL | OURS-noEC | 39 | 0.1464 | 0.68262 | 4.8889 | 5.8394 |

OURS−비교법의 같은scene·seed 짝 차이(추가 p검정 없음):

| scene | comparator | pairs | OURS_only_success | other_only_success | success_difference | OURS_only_safety_failure | other_only_safety_failure | safety_difference | checkpoint_pairs | checkpoint_mean_difference_s | checkpoint_median_difference_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW-v2 | OURS-noGRAPH | 13 | 6 | 1 | 5 | 0 | 0 | 0 | 6 | -6.4514 | -6.5069 |
| SLW-v2 | NOMAD_RAW | 13 | 5 | 0 | 5 | 0 | 6 | -6 | 7 | -8.744 | -8.0972 |
| H1-v3 | OURS-noGRAPH | 13 | 1 | 4 | -3 | 0 | 0 | 0 | 4 | 1.4167 | 6.1667 |
| H1-v3 | NOMAD_RAW | 13 | 4 | 0 | 4 | 0 | 12 | -12 | 1 | 9.1667 | 9.1667 |
| LC | OURS-noGRAPH | 13 | 0 | 2 | -2 | 0 | 0 | 0 | 11 | -1.202 | -1.4722 |
| LC | NOMAD_RAW | 13 | 1 | 2 | -1 | 0 | 0 | 0 | 10 | -5.9097 | -2.3264 |
| ALL | OURS-noGRAPH | 39 | 7 | 7 | 0 | 0 | 0 | 0 | 21 | -2.203 | -2.4444 |
| ALL | NOMAD_RAW | 39 | 10 | 2 | 8 | 0 | 18 | -18 | 18 | -6.1744 | -3.7639 |

OURS EC 검사·거절(scope별; 주 판정 미사용):

| scene | scope | checks | rejected | reject_fraction |
| --- | --- | --- | --- | --- |
| SLW-v2 | SAFE_INSTALL | 585 | 5 | 0.008547 |
| SLW-v2 | GRAPH_INSTALL | 421 | 8 | 0.019002 |
| SLW-v2 | PERIODIC | 788 | 13 | 0.016497 |
| SLW-v2 | ALL | 1794 | 26 | 0.014493 |
| H1-v3 | SAFE_INSTALL | 564 | 41 | 0.072695 |
| H1-v3 | GRAPH_INSTALL | 366 | 1 | 0.0027322 |
| H1-v3 | PERIODIC | 1388 | 14 | 0.010086 |
| H1-v3 | ALL | 2318 | 56 | 0.024159 |
| LC | SAFE_INSTALL | 504 | 1 | 0.0019841 |
| LC | GRAPH_INSTALL | 390 | 0 | 0 |
| LC | PERIODIC | 586 | 2 | 0.003413 |
| LC | ALL | 1480 | 3 | 0.002027 |
| ALL | SAFE_INSTALL | 1653 | 47 | 0.028433 |
| ALL | GRAPH_INSTALL | 1177 | 9 | 0.0076466 |
| ALL | PERIODIC | 2762 | 29 | 0.0105 |
| ALL | ALL | 5592 | 85 | 0.0152 |

H1-v3 OURS timeout의 종료 위치와 마지막 정지 위치(종료 때 움직였으면 stationary_at_end=False):

| index | key | final_x_m | final_y_m | final_goal_distance_m | stationary_at_end | last_stop_x_m | last_stop_y_m | last_stop_start_s | last_stop_end_s | total_stop_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 232 | H1-v3_232_D750_OURS | 4.0723 | -0.80464 | 4.0784 | True | 4.0723 | -0.80464 | 50.681 | 90 | 47.667 |
| 233 | H1-v3_233_D750_OURS | 2.267 | 0.48266 | 2.9071 | True | 2.267 | 0.48266 | 14.903 | 90 | 78.111 |
| 235 | H1-v3_235_D750_OURS | -0.045314 | -0.0813 | 4.6859 | False | 0.56549 | -0.077231 | 84.569 | 84.667 | 32.778 |
| 236 | H1-v3_236_D750_OURS | 2.9608 | 0.33274 | 2.8873 | True | 2.9608 | 0.33274 | 19.792 | 90 | 73.556 |
| 238 | H1-v3_238_D750_OURS | 2.8683 | 0.33284 | 2.8995 | True | 2.8683 | 0.33284 | 21.681 | 90 | 71.222 |
| 239 | H1-v3_239_D750_OURS | 2.8777 | -0.028192 | 3.2557 | False | 2.4717 | -0.49528 | 86.903 | 87 | 3.6667 |
| 240 | H1-v3_240_D750_OURS | 3.0423 | 0.3382 | 2.8734 | True | 3.0423 | 0.3382 | 34.347 | 90 | 63.889 |
| 241 | H1-v3_241_D750_OURS | 3.063 | -0.83812 | 4.0451 | True | 3.063 | -0.83812 | 38.681 | 90 | 56.889 |

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
