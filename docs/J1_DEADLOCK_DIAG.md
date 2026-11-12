# J1 H1-v3 정지 구간 기록

대상: seed231–239 × OURS·OURS-noEC·OURS-noGRAPH =27개 완료run. 저장 artifacts만 읽었다. 시뮬레이션·추론·Graph 재풀이·SDF 재계산·원래 작업 트리 수정은0회다. 아래는 기록 수치와 로그 disposition의 집계이며 원인 판정·수정 제안은 포함하지 않는다.

정지: 저장72Hz 구간에서 |v|<1e−12m/s AND |ω|<1e−12rad/s가 연속360tick(5s) 이상. 표의 [start,end) 안 이벤트를 센다. 시작 추론 대기도 조건을 만족하면 포함한다. chunk도착=received.jsonl의 latched_sim_s(terminal_unapplied 제외),FRESH판정=application_sim_s여서 두 수는 다를 수 있다.

남은 길이/SAFE는 당시 저장된 selection 값을 사용했다. 최장 SAFE가 없으면N/A이고 전체8개 중 최장 후보도 별도로 남겼다. 전진 성분은 (후보끝점−실제B)와B heading의 내적(body) 및 +y 축 성분을 함께 표시한다. 표의 길이/전진 값은 최소/중앙/최대(m),chunk별 수치는 CSV에 있다. 새 depth 판정은 하지 않았다.

| method | runs | runs_with_stop | stop_intervals | stop_s | no_path_installed_intervals | path_installed_intervals | chunks_received | fresh_with_SAFE | fresh_without_SAFE | graph_submitted | ec_install_rejected | installed_paths |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OURS | 9 | 5 | 5 | 278.0000 | 5 | 0 | 282 | 33 | 251 | 33 | 33 | 0 |
| OURS-noEC | 9 | 5 | 6 | 245.4444 | 6 | 0 | 249 | 0 | 251 | 0 | N/A | 0 |
| OURS-noGRAPH | 9 | 2 | 3 | 73.7778 | 3 | 0 | 75 | 61 | 14 | N/A | 61 | 0 |

## 로그에 기록된 새 경로 미설치·거절 코드

FRESH_SELECTION·GRAPH_RESULT·EC_INSTALL_CHECK는 서로 다른 사건 단위다. 같은 거절이 둘 이상의 로그에 기록될 수 있으므로 출처 간 행을 더해 독립 원인 수로 해석하지 않는다. Graph 경계 곡률 항목은 저장 error에 boundary curvature undefined가 있는 INITIALIZATION_REJECTED만 묶었다.

| method | source | logged_reason | events | stop_intervals | runs |
| --- | --- | --- | --- | --- | --- |
| OURS | EC_INSTALL_CHECK | SAFE_INSTALL:DEPTH_SWEEP_UNSAFE | 33 | 2 | 2 |
| OURS | FRESH_SELECTION | EC_REJECT_KEEP_CURRENT | 33 | 2 | 2 |
| OURS | FRESH_SELECTION | NO_SAFE_KEEP_CURRENT | 251 | 5 | 5 |
| OURS | GRAPH_RESULT | BOUNDARY_CURVATURE_UNDEFINED | 32 | 2 | 2 |
| OURS-noEC | FRESH_SELECTION | NO_SAFE_KEEP_CURRENT | 251 | 6 | 5 |
| OURS-noGRAPH | EC_INSTALL_CHECK | SAFE_INSTALL:DEPTH_SWEEP_UNSAFE | 61 | 2 | 2 |
| OURS-noGRAPH | FRESH_SELECTION | EC_REJECT_KEEP_CURRENT | 61 | 2 | 2 |
| OURS-noGRAPH | FRESH_SELECTION | NO_SAFE_KEEP_CURRENT | 14 | 2 | 1 |

## 정지 구간별 chunk·SAFE·후보 수치

| segment | start_s | end_s | duration_s | chunks | FRESH | SAFE_yes | SAFE_no | longest_all_remaining | longest_SAFE_remaining |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1-v3_232_D750_OURS_S01 | 50.6667 | 90.0000 | 39.3333 | 40 | 41 | 32 | 9 | 0.1669 / 0.2357 / 0.3550 | 0.0323 / 0.1543 / 0.2511 |
| H1-v3_233_D750_OURS_S01 | 14.8889 | 90.0000 | 75.1111 | 76 | 77 | 0 | 77 | 0.3253 / 0.3593 / 0.4280 | N/A |
| H1-v3_235_D750_OURS_S01 | 26.3333 | 51.3333 | 25.0000 | 25 | 25 | 0 | 25 | 0.2410 / 0.2822 / 0.3424 | N/A |
| H1-v3_236_D750_OURS_S01 | 19.7778 | 90.0000 | 70.2222 | 72 | 72 | 1 | 71 | 0.2010 / 0.2821 / 0.3543 | 0.1577 / 0.1577 / 0.1577 |
| H1-v3_238_D750_OURS_S01 | 21.6667 | 90.0000 | 68.3333 | 69 | 69 | 0 | 69 | 0.1648 / 0.2011 / 0.2848 | N/A |
| H1-v3_231_D750_OURS-noEC_S01 | 48.1111 | 59.8889 | 11.7778 | 12 | 12 | 0 | 12 | 0.0798 / 0.3395 / 0.3995 | N/A |
| H1-v3_234_D750_OURS-noEC_S01 | 24.2222 | 31.3333 | 7.1111 | 7 | 7 | 0 | 7 | 0.1859 / 0.2562 / 0.3284 | N/A |
| H1-v3_234_D750_OURS-noEC_S02 | 32.3333 | 90.0000 | 57.6667 | 59 | 59 | 0 | 59 | 0.2395 / 0.3324 / 0.3669 | N/A |
| H1-v3_235_D750_OURS-noEC_S01 | 50.7778 | 90.0000 | 39.2222 | 40 | 40 | 0 | 40 | 0.1983 / 0.2717 / 0.2955 | N/A |
| H1-v3_237_D750_OURS-noEC_S01 | 22.6667 | 90.0000 | 67.3333 | 68 | 69 | 0 | 69 | 0.2577 / 0.3299 / 0.3825 | N/A |
| H1-v3_239_D750_OURS-noEC_S01 | 27.6667 | 90.0000 | 62.3333 | 63 | 64 | 0 | 64 | 0.3397 / 0.3556 / 0.3829 | N/A |
| H1-v3_233_D750_OURS-noGRAPH_S01 | 34.6667 | 90.0000 | 55.3333 | 56 | 57 | 57 | 0 | 0.0825 / 0.1637 / 0.3037 | 0.0825 / 0.1631 / 0.3037 |
| H1-v3_239_D750_OURS-noGRAPH_S01 | 31.6667 | 42.1111 | 10.4444 | 11 | 10 | 4 | 6 | 0.3321 / 0.3567 / 0.3715 | 0.2921 / 0.3353 / 0.3460 |
| H1-v3_239_D750_OURS-noGRAPH_S02 | 43.1111 | 51.1111 | 8.0000 | 8 | 8 | 0 | 8 | 0.1947 / 0.3496 / 0.3571 | N/A |

| segment | longest_all_forward_body | longest_all_forward_plus_y | longest_SAFE_forward_body | longest_SAFE_forward_plus_y |
| --- | --- | --- | --- | --- |
| H1-v3_232_D750_OURS_S01 | -0.1403 / -0.0517 / 0.1107 | -0.1094 / 0.0527 / 0.1407 | -0.0931 / -0.0344 / 0.0454 | -0.0457 / 0.0341 / 0.0929 |
| H1-v3_233_D750_OURS_S01 | 0.3611 / 0.3993 / 0.4707 | 0.1900 / 0.2308 / 0.2952 | N/A | N/A |
| H1-v3_235_D750_OURS_S01 | 0.0021 / 0.0530 / 0.3335 | -0.2769 / -0.1879 / 0.0698 | N/A | N/A |
| H1-v3_236_D750_OURS_S01 | 0.0470 / 0.3247 / 0.4012 | 0.0668 / 0.1974 / 0.2917 | -0.1328 / -0.1328 / -0.1328 | 0.0149 / 0.0149 / 0.0149 |
| H1-v3_238_D750_OURS_S01 | 0.1993 / 0.2370 / 0.3158 | 0.0826 / 0.1493 / 0.1934 | N/A | N/A |
| H1-v3_231_D750_OURS-noEC_S01 | 0.0401 / 0.2049 / 0.2758 | 0.0755 / 0.3286 / 0.3781 | N/A | N/A |
| H1-v3_234_D750_OURS-noEC_S01 | 0.0147 / 0.1283 / 0.2527 | -0.0229 / 0.2012 / 0.2302 | N/A | N/A |
| H1-v3_234_D750_OURS-noEC_S02 | 0.2285 / 0.3309 / 0.4059 | 0.1453 / 0.2272 / 0.3263 | N/A | N/A |
| H1-v3_235_D750_OURS-noEC_S01 | 0.1975 / 0.3132 / 0.3372 | 0.1944 / 0.3043 / 0.3317 | N/A | N/A |
| H1-v3_237_D750_OURS-noEC_S01 | 0.2297 / 0.3312 / 0.3745 | 0.1389 / 0.2626 / 0.3496 | N/A | N/A |
| H1-v3_239_D750_OURS-noEC_S01 | 0.3045 / 0.4040 / 0.4341 | 0.2950 / 0.3147 / 0.3392 | N/A | N/A |
| H1-v3_233_D750_OURS-noGRAPH_S01 | -0.1714 / -0.0386 / 0.0479 | -0.0726 / 0.0242 / 0.1599 | -0.1714 / -0.0394 / 0.0305 | -0.0460 / 0.0277 / 0.1599 |
| H1-v3_239_D750_OURS-noGRAPH_S01 | 0.3561 / 0.4088 / 0.4248 | 0.3477 / 0.3944 / 0.4125 | 0.3144 / 0.3842 / 0.3960 | 0.3079 / 0.3774 / 0.3902 |
| H1-v3_239_D750_OURS-noGRAPH_S02 | 0.1932 / 0.4014 / 0.4089 | 0.1870 / 0.3936 / 0.4040 | N/A | N/A |

## 정지 구간별 Graph·EC 기록

Graph_attempts와 outcomes는 구간 안에서 제출한 job cohort이며 그 job의 최종 저장 결과를 연결했다(result_after_stop 별도). solver_evaluated는 solver 결과 flag가 존재하는 수다. converged·constraints_false·certificate_false는 독립 집계로 서로 배타적이지 않다. 주기EC거절은 설치거절과 별도 열이다. 기능 없는 방법은N/A다.

| method | attempts | solver_evaluated | ACCEPTED | NONCONVERGED | CONSTRAINT_FAILED | BOUNDARY_CURVATURE_UNDEFINED | INITIALIZATION_REJECTED | STALE | SUPERSEDED | WAYPOINT_EXPIRED | EXEC_CERT_REJECT | TERMINAL_UNAPPLIED_NO_RESULT | NO_RESULT_LOG |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OURS | 33 | 0 | 0 | 0 | 0 | 32 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| OURS-noEC | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| OURS-noGRAPH | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

| segment | Graph_attempts | outcomes | solver_evaluated | converged | constraints_false | certificate_false | result_after_stop | EC_install_rejects | EC_install_reasons | periodic_rejects |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1-v3_232_D750_OURS_S01 | 32 | {"BOUNDARY_CURVATURE_UNDEFINED": 31, "TERMINAL_UNAPPLIED_NO_RESULT": 1} | 0 | 0 | 0 | 0 | 0 | 32 | {"SAFE_INSTALL:DEPTH_SWEEP_UNSAFE": 32} | 1 |
| H1-v3_233_D750_OURS_S01 | 0 | {} | 0 | 0 | 0 | 0 | 0 | 0 | {} | 0 |
| H1-v3_235_D750_OURS_S01 | 0 | {} | 0 | 0 | 0 | 0 | 0 | 0 | {} | 0 |
| H1-v3_236_D750_OURS_S01 | 1 | {"BOUNDARY_CURVATURE_UNDEFINED": 1} | 0 | 0 | 0 | 0 | 0 | 1 | {"SAFE_INSTALL:DEPTH_SWEEP_UNSAFE": 1} | 0 |
| H1-v3_238_D750_OURS_S01 | 0 | {} | 0 | 0 | 0 | 0 | 0 | 0 | {} | 0 |
| H1-v3_231_D750_OURS-noEC_S01 | 0 | {} | 0 | 0 | 0 | 0 | 0 | N/A | N/A | N/A |
| H1-v3_234_D750_OURS-noEC_S01 | 0 | {} | 0 | 0 | 0 | 0 | 0 | N/A | N/A | N/A |
| H1-v3_234_D750_OURS-noEC_S02 | 0 | {} | 0 | 0 | 0 | 0 | 0 | N/A | N/A | N/A |
| H1-v3_235_D750_OURS-noEC_S01 | 0 | {} | 0 | 0 | 0 | 0 | 0 | N/A | N/A | N/A |
| H1-v3_237_D750_OURS-noEC_S01 | 0 | {} | 0 | 0 | 0 | 0 | 0 | N/A | N/A | N/A |
| H1-v3_239_D750_OURS-noEC_S01 | 0 | {} | 0 | 0 | 0 | 0 | 0 | N/A | N/A | N/A |
| H1-v3_233_D750_OURS-noGRAPH_S01 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 57 | {"SAFE_INSTALL:DEPTH_SWEEP_UNSAFE": 57} | 1 |
| H1-v3_239_D750_OURS-noGRAPH_S01 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 4 | {"SAFE_INSTALL:DEPTH_SWEEP_UNSAFE": 4} | 0 |
| H1-v3_239_D750_OURS-noGRAPH_S02 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 | {} | 0 |

## 설치 경로 길이

installed는 정지 구간 내 실제 j_applications 기록 수다. active_at_stop은 시작 직전/동일tick 마지막 설치 경로를 정지 시작 pose에 투영한 값이다. 경로가 바뀌지 않았으면 installed_length는N/A이고 기존 경로 길이를 별도로 표시한다.

| segment | installed | kinds | installed_length_m | installed_suffix_m | active_at_stop_length_m | active_at_stop_suffix_m |
| --- | --- | --- | --- | --- | --- | --- |
| H1-v3_232_D750_OURS_S01 | 0 | {} | N/A | N/A | 0.2208 | 0.1711 |
| H1-v3_233_D750_OURS_S01 | 0 | {} | N/A | N/A | 0.3262 | 0.1618 |
| H1-v3_235_D750_OURS_S01 | 0 | {} | N/A | N/A | 0.1098 | 0.0253 |
| H1-v3_236_D750_OURS_S01 | 0 | {} | N/A | N/A | 0.1775 | 0.0000 |
| H1-v3_238_D750_OURS_S01 | 0 | {} | N/A | N/A | 0.1240 | 0.0672 |
| H1-v3_231_D750_OURS-noEC_S01 | 0 | {} | N/A | N/A | 0.0686 | 0.0609 |
| H1-v3_234_D750_OURS-noEC_S01 | 0 | {} | N/A | N/A | 0.1166 | 0.0021 |
| H1-v3_234_D750_OURS-noEC_S02 | 0 | {} | N/A | N/A | 0.0650 | 0.0360 |
| H1-v3_235_D750_OURS-noEC_S01 | 0 | {} | N/A | N/A | 0.3064 | 0.0060 |
| H1-v3_237_D750_OURS-noEC_S01 | 0 | {} | N/A | N/A | 0.0858 | 0.0571 |
| H1-v3_239_D750_OURS-noEC_S01 | 0 | {} | N/A | N/A | 0.3644 | 0.3267 |
| H1-v3_233_D750_OURS-noGRAPH_S01 | 0 | {} | N/A | N/A | 0.3423 | 0.2578 |
| H1-v3_239_D750_OURS-noGRAPH_S01 | 0 | {} | N/A | N/A | 0.4420 | 0.1974 |
| H1-v3_239_D750_OURS-noGRAPH_S02 | 0 | {} | N/A | N/A | 0.3389 | 0.1635 |

## OURS seed233: 정지 시작 전3초 사건

해당run의 첫 주행 후 5s이상 정지 구간을 선택했다(없으면 첫 초기 정지). simulation 시각 순이며, 동일tick 행의 내부 순서는 주장하지 않는다. 저장monotonic 필드에 제어tick 입력 시각과 이벤트 시각이 혼재하므로 이를 실제 명령 적용 순서로 해석하지 않는다.

| time_s | relative_to_stop_s | event | id | detail |
| --- | --- | --- | --- | --- |
| 11.8889 | -3.0000 | FRESH_SELECTION | 9 | SAFE=8; SAFE_SELECTED; longest_SAFE_remaining=0.35976179577102063; forward_body=0.18157174853212144; forward_+y=-0.0033829481547699436 |
| 11.8889 | -3.0000 | GRAPH_SUBMIT | 9 | chunk=9; v=0.2413582343059806 |
| 11.8889 | -3.0000 | EC_SAFE_INSTALL | 27 | pass=True; PASS; clearance=0.30791618207835536 |
| 11.8889 | -3.0000 | PATH_INSTALL | 9 | SAFE; graph_job=None; length=0.4624; remaining=0.3598 |
| 11.8889 | -3.0000 | COMMAND_SOURCE | 9 | GRAPH_RAW; v=0.185803; w=-0.400000 |
| 12.0000 | -2.8889 | GRAPH_RESULT | 9 | ACCEPTED; converged=True; constraints=True; message=Optimization terminated successfully |
| 12.0000 | -2.8889 | EC_GRAPH_INSTALL | 28 | pass=True; PASS; clearance=0.2614768404613178 |
| 12.0000 | -2.8889 | PATH_INSTALL | 9 | GRAPH; graph_job=9; length=0.4539; remaining=0.3511 |
| 12.0000 | -2.8889 | COMMAND_SOURCE | 9 | GRAPH_GRAPH; v=0.130247; w=-0.400000 |
| 12.5000 | -2.3889 | EC_PERIODIC | 29 | pass=True; PASS; clearance=0.20966323330860634 |
| 12.8333 | -2.0556 | CHUNK_RECEIVED | 10 |  |
| 12.8889 | -2.0000 | FRESH_SELECTION | 10 | SAFE=7; EC_REJECT_KEEP_CURRENT; longest_SAFE_remaining=0.36862004470696375; forward_body=0.3600562908532379; forward_+y=0.22401234041939144 |
| 12.8889 | -2.0000 | GRAPH_SUBMIT | 10 | chunk=10; v=0.08986372071390797 |
| 12.8889 | -2.0000 | EC_SAFE_INSTALL | 30 | pass=False; DEPTH_SWEEP_UNSAFE; clearance=-0.021328722536134284 |
| 12.8889 | -2.0000 | COMMAND_SOURCE | 10 | expired; v=0.000000; w=0.000000 |
| 13.0000 | -1.8889 | GRAPH_RESULT | 10 | ACCEPTED; converged=True; constraints=True; message=Optimization terminated successfully |
| 13.0000 | -1.8889 | EC_PERIODIC | 31 | pass=True; PASS; clearance=0.18666892917562042 |
| 13.0000 | -1.8889 | EC_GRAPH_INSTALL | 32 | pass=True; PASS; clearance=0.06720246695958842 |
| 13.0000 | -1.8889 | PATH_INSTALL | 10 | GRAPH; graph_job=10; length=0.3585; remaining=0.3494 |
| 13.0000 | -1.8889 | COMMAND_SOURCE | 10 | GRAPH_GRAPH; v=0.055556; w=0.114892 |
| 13.5000 | -1.3889 | EC_PERIODIC | 33 | pass=True; PASS; clearance=0.06720246695958842 |
| 13.8333 | -1.0556 | CHUNK_RECEIVED | 11 |  |
| 13.8889 | -1.0000 | FRESH_SELECTION | 11 | SAFE=2; SAFE_SELECTED; longest_SAFE_remaining=0.2137540546934134; forward_body=0.04663305035232518; forward_+y=-0.10336156427945575 |
| 13.8889 | -1.0000 | GRAPH_SUBMIT | 11 | chunk=11; v=0.3 |
| 13.8889 | -1.0000 | EC_SAFE_INSTALL | 34 | pass=True; PASS; clearance=0.07578610980067352 |
| 13.8889 | -1.0000 | PATH_INSTALL | 11 | SAFE; graph_job=None; length=0.3262; remaining=0.2138 |
| 13.8889 | -1.0000 | COMMAND_SOURCE | 11 | GRAPH_RAW; v=0.244444; w=-0.400000 |
| 14.1111 | -0.7778 | GRAPH_RESULT | 11 | NONCONVERGED; converged=False; constraints=False; message=Positive directional derivative for linesearch |
| 14.3889 | -0.5000 | EC_PERIODIC | 35 | pass=True; PASS; clearance=0.0485706254879151 |
| 14.8333 | -0.0556 | CHUNK_RECEIVED | 12 |  |
| 14.8889 | 0.0000 | FRESH_SELECTION | 12 | SAFE=0; NO_SAFE_KEEP_CURRENT; longest_SAFE_remaining=None; forward_body=None; forward_+y=None |
| 14.8889 | 0.0000 | EC_PERIODIC | 36 | pass=True; PASS; clearance=0.029234511958006512 |
| 14.8889 | 0.0000 | COMMAND_SOURCE | 12 | expired; v=0.000000; w=0.000000 |
| 14.8889 | 0.0000 | STOP_INTERVAL_START | N/A | duration=75.111111; pose=(2.2669784340414822,0.4826585558998131,0.5134138496938867) |

## OURS seed236: 정지 시작 전3초 사건

해당run의 첫 주행 후 5s이상 정지 구간을 선택했다(없으면 첫 초기 정지). simulation 시각 순이며, 동일tick 행의 내부 순서는 주장하지 않는다. 저장monotonic 필드에 제어tick 입력 시각과 이벤트 시각이 혼재하므로 이를 실제 명령 적용 순서로 해석하지 않는다.

| time_s | relative_to_stop_s | event | id | detail |
| --- | --- | --- | --- | --- |
| 16.8472 | -2.9306 | CHUNK_RECEIVED | 14 |  |
| 16.8889 | -2.8889 | FRESH_SELECTION | 14 | SAFE=8; SAFE_SELECTED; longest_SAFE_remaining=0.21465361899826707; forward_body=0.17806529199182425; forward_+y=0.120571099527047 |
| 16.8889 | -2.8889 | GRAPH_SUBMIT | 14 | chunk=14; v=0.05077460750143575 |
| 16.8889 | -2.8889 | EC_SAFE_INSTALL | 42 | pass=True; PASS; clearance=0.1844615185744077 |
| 16.8889 | -2.8889 | PATH_INSTALL | 14 | SAFE; graph_job=None; length=0.2147; remaining=0.2147 |
| 16.8889 | -2.8889 | COMMAND_SOURCE | 14 | GRAPH_RAW; v=0.075031; w=-0.400000 |
| 17.1111 | -2.6667 | GRAPH_RESULT | 14 | ACCEPTED; converged=True; constraints=True; message=Optimization terminated successfully |
| 17.1111 | -2.6667 | EC_GRAPH_INSTALL | 43 | pass=True; PASS; clearance=0.13492058269973564 |
| 17.1111 | -2.6667 | PATH_INSTALL | 14 | GRAPH; graph_job=14; length=0.1986; remaining=0.1986 |
| 17.1111 | -2.6667 | COMMAND_SOURCE | 14 | GRAPH_GRAPH; v=0.114668; w=-0.400000 |
| 17.6111 | -2.1667 | EC_PERIODIC | 44 | pass=True; PASS; clearance=0.13492058269973564 |
| 17.8889 | -1.8889 | CHUNK_RECEIVED | 15 |  |
| 17.8889 | -1.8889 | FRESH_SELECTION | 15 | SAFE=8; SAFE_SELECTED; longest_SAFE_remaining=0.21648766972193156; forward_body=0.20664122641084112; forward_+y=0.10408177137173075 |
| 17.8889 | -1.8889 | GRAPH_SUBMIT | 15 | chunk=15; v=0.11466818786464754 |
| 17.8889 | -1.8889 | EC_SAFE_INSTALL | 45 | pass=True; PASS; clearance=0.09528313496880439 |
| 17.8889 | -1.8889 | PATH_INSTALL | 15 | SAFE; graph_job=None; length=0.2920; remaining=0.2165 |
| 17.8889 | -1.8889 | COMMAND_SOURCE | 15 | GRAPH_RAW; v=0.144081; w=-0.400000 |
| 18.0000 | -1.7778 | GRAPH_RESULT | 15 | ACCEPTED; converged=True; constraints=True; message=Optimization terminated successfully |
| 18.0000 | -1.7778 | EC_GRAPH_INSTALL | 46 | pass=True; PASS; clearance=0.12500797798259683 |
| 18.0000 | -1.7778 | PATH_INSTALL | 15 | GRAPH; graph_job=15; length=0.2794; remaining=0.2082 |
| 18.0000 | -1.7778 | COMMAND_SOURCE | 15 | GRAPH_GRAPH; v=0.095852; w=-0.400000 |
| 18.5000 | -1.2778 | EC_PERIODIC | 47 | pass=True; PASS; clearance=0.12500797798259683 |
| 18.8333 | -0.9444 | CHUNK_RECEIVED | 16 |  |
| 18.8889 | -0.8889 | FRESH_SELECTION | 16 | SAFE=4; SAFE_SELECTED; longest_SAFE_remaining=0.14568281780328823; forward_body=0.13326930836765474; forward_+y=0.07373078883172285 |
| 18.8889 | -0.8889 | GRAPH_SUBMIT | 16 | chunk=16; v=0.09585200385862896 |
| 18.8889 | -0.8889 | EC_SAFE_INSTALL | 48 | pass=True; PASS; clearance=0.05560405998557097 |
| 18.8889 | -0.8889 | PATH_INSTALL | 16 | SAFE; graph_job=None; length=0.1775; remaining=0.1457 |
| 18.8889 | -0.8889 | COMMAND_SOURCE | 16 | GRAPH_RAW; v=0.151408; w=0.379165 |
| 19.2222 | -0.5556 | GRAPH_RESULT | 16 | NONCONVERGED; converged=False; constraints=False; message=Positive directional derivative for linesearch |
| 19.3889 | -0.3889 | EC_PERIODIC | 49 | pass=True; PASS; clearance=0.06494270406164154 |
| 19.7778 | 0.0000 | COMMAND_SOURCE | 16 | ENDPOINT; v=0.000000; w=0.000000 |
| 19.7778 | 0.0000 | STOP_INTERVAL_START | N/A | duration=70.222222; pose=(2.9607595539697127,0.3327352341641832,0.7598030782436815) |

## 기록 파일

`research/results/j1_deadlock/`: segments.csv(구간),chunks.csv(도착chunk별 SAFE/길이/전진),selections.csv(FRESH별),graph_jobs.csv(job별 status·message·flag),ec_checks.csv,installed_paths.csv,rejection_summary.csv,examples.csv. analysis.json에 원 입력 SHA256을 포함하며 분석 후 전부 재확인했다.
