# Phase28-T smoke_02 검토

**GATE_PASS · 기술 PASS. 실제 H 적용 32/38 = 84.21%** (DETOUR_STARTED 제외 0건). 전체 계산 p50/p95 **79.77/123.23 ms**, 최대 137.02 ms. worker core 고정 `True`, 실제 `[7]`; driver는 CPU 7 및 SMT sibling 15를 제외했다. H1 seed201은 도착 성공·충돌 0, 최소 여유 0.0891m, 도착 42.250s, 상자 생성→통과 14.944s다. 아래는 같은 seed의 재사용 C0(Phase27-R)·C0-NA(Phase28) 비교다.

| method | success | collision | minimum_clearance_m | goal_time_s | passage_from_spawn_s | mean_speed_m_s | stop_fraction | alignment_rotation_s | alignment_brake_s | detour_execution_s | detour_wait_s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C0 | True | False | 0.14352 | 29.986 | 6.1528 | 0.17845 | 0.21491 | 3 | 1.6667 | 2 | 0.66667 |
| C0-NA | True | False | 0.15209 | 30.667 | 6.9444 | 0.17821 | 0.15217 | 0.66667 | 0.33333 | 2.3333 | 0.77778 |
| C0-H | True | False | 0.089061 | 42.25 | 14.944 | 0.12547 | 0.21565 | 1 | 0 | 0.33333 | 1.1111 |

단계별 시간(ms, 각 단계의 관측값 기준; 중첩 단계를 더하지 않는다):

| stage | n | p50_ms | p95_ms |
|---|---|---|---|
| total | 38 | 79.773 | 123.23 |
| worker_inclusive | 38 | 78.192 | 121.28 |
| B_prediction | 38 | 1.4781 | 1.6824 |
| transport_thread_queue | 38 | 0.49065 | 0.9665 |
| SDF_copy | 38 | 5.1918 | 6.882 |
| send_to_worker_receive | 38 | 0.51829 | 0.96922 |
| field_attach | 38 | 0.17119 | 0.3641 |
| submit_to_solver_enter | 38 | 6.4334 | 8.98 |
| worker_result_to_parent_receive | 38 | 0.23267 | 0.49756 |
| parent_decode | 38 | 0.1894 | 0.23912 |
| graph_construct | 38 | 0.40198 | 0.66857 |
| na_initial_72hz | 38 | 2.5664 | 4.509 |
| initialization_total | 38 | 2.8234 | 4.7226 |
| slsqp | 38 | 64.463 | 107.98 |
| optimized_certificate | 32 | 0.48327 | 0.92821 |
| initial_certificate | 5 | 0.33729 | 0.71864 |
| application_certificate | 32 | 0.65698 | 1.1405 |

smoke_01 기술 실패는 `docs/PHASE28T_SMOKE_01.md`, `research/results/phase28t/smoke_01/` 및 원 raw에 보존했다. 이 문서와 canonical `smoke/`는 완료된 smoke_02를 가리킨다. smoke는 본 비교에서 제외하며, 같은 seed라도 실행 시점/실시간 inference·snapshot 이력이 달라 아래 차이는 단일 run의 서술이다. evaluator·수치·정책·게이트 변경 없음.

## Feedback clip 133건

H COMMAND 257개 중 133개(51.75%). 기록된 raw command와 직전 실제 v/ω로 최종 clip을 재계산해 모든 명령과 1e−9 이내 일치를 확인했다. 각 행은 raw가 해당 제한을 위반하면서 해당 축이 실제 clip된 경우다. 하나의 명령에서 여러 제한이 겹치므로 원인별 합은 133보다 클 수 있다. 가속도는 ±0.5/9 m/s, 각가속도는 ±2/9 rad/s의 tick당 변화다.

| cause | count | planned_v_at_upper |
|---|---|---|
| v_upper | 17 | 14 |
| v_lower | 5 | 0 |
| omega | 56 | 0 |
| acceleration | 62 | 0 |
| angular_acceleration | 33 | 2 |

중복 없는 원인 조합(합계 133):

| causes | count |
|---|---|
| acceleration | 29 |
| v_upper | 14 |
| v_upper+angular_acceleration | 3 |
| acceleration+angular_acceleration | 15 |
| omega+acceleration | 17 |
| omega | 37 |
| v_lower+angular_acceleration | 2 |
| v_lower | 3 |
| omega+acceleration+angular_acceleration | 1 |
| angular_acceleration | 11 |
| omega+angular_acceleration | 1 |

clip 시 feedforward 계획 속도가 이미 상한인 경우는 **14/133**이다(상한 판정 0.3−1e−7, solver 수치오차 고려; 제어 한계 변경 아님). `clip_commands.csv`에 모든 명령의 계획·raw·최종 속도와 원인 플래그가 있다. 정지/곡선에서 가속도·각속도 제한에 걸리는 clip도 있으므로 전부 vmax feedback 포화로 해석하지 않는다.

## 계획 대비 실제 추종

H 실행 구간 72Hz 2050개 pose를 해당 APPLIED의 시간 매개 궤적과 비교했다. target XY는 knot 시간 선형 보간, heading은 unwrap 후 보간하고 오차는 wrap한다(실제 follower와 동일). 정지/우회 모드 등 H controller가 호출되지 않은 구간은 제외한다. 위치 오차 p50/p95 **0.01448/0.05874m**, heading **1.136/10.864°**. 미래 계획 전체의 off-policy rollout 수치가 아니다. C0-NA는 pose·dt 계획을 출력하지 않아 동일한 시간축 heading/위치 오차는 정의되지 않는다.

## 시간 손실 분해

C0-H − C0-NA 도착시간은 **11.583s**. 정지(|v|<0.01m/s, 기존 evaluator 정의)는 9.111s(21.56%) vs 4.667s(15.22%). 정렬 회전은 1.000 vs 0.667s, 감속은 0.000 vs 0.333s다. STOP 비율은 아래 상태 분류와 겹치는 별도 속도 기준이다.

| state | C0 | C0-NA | C0-H | H_minus_NA_s |
|---|---|---|---|---|
| ALIGN_BRAKE | 1.6667 | 0.33333 | 0 | -0.33333 |
| ALIGN_ROTATE | 3 | 0.66667 | 1 | 0.33333 |
| DETOUR_MOVING | 2 | 2.3333 | 0.33333 | -2 |
| DETOUR_WAIT | 0.66667 | 0.77778 | 1.1111 | 0.33333 |
| FIRST_INFERENCE_WAIT | 2.8889 | 2.8889 | 2.8889 | 0 |
| H_MOVING | 0 | 0 | 25.806 | 25.806 |
| H_STOPPED | 0 | 0 | 1.6667 | 1.6667 |
| NA_MOVING | 18.875 | 22.333 | 6.1111 | -16.222 |
| OTHER_STOP | 0 | 0 | 1.3333 | 1.3333 |
| STOP_WAIT | 0.88889 | 1.3333 | 2 | 0.66667 |

위 표는 72Hz 시간 구간을 우선순위(최초 대기→정렬/회복→계산대기/STOP_WAIT→우회→H→NA)로 배타 분류하므로 각 방법 열은 총 주행시간과 일치한다. H는 평소 이동 구간에서 H_MOVING과 NA_MOVING을 합쳐 비교해야 한다. 새 H 계산 중에는 OLD를 계속 실행하므로 H 계산시간 합을 정지시간에 가산하지 않는다.

| method | before_spawn_s | spawn_to_passage_s | passage_to_goal_s |
|---|---|---|---|
| C0 | 20.097 | 6.1528 | 3.7361 |
| C0-NA | 20.514 | 6.9444 | 3.2083 |
| C0-H | 22 | 14.944 | 5.3056 |

손실의 대부분은 상자 생성→통과 구간 차이(8.000s)에 나타난다. H의 실제 수락 우회 실행은 더 짧고 정렬 회전 차이는 작다. 추가 STOP_WAIT/계산 대기와 평소 경로 추종 시간 증가가 함께 관측된다. clip·경로 차이·새 관측 이력 중 하나를 독립 원인으로 단정할 수 없다.

| method | paths | completed | sum_full_plan_s | sum_active_execution_s |
|---|---|---|---|---|
| C0 | 26 | 2 | 45.909 | 27.097 |
| C0-NA | 26 | 2 | 52.34 | 27.778 |
| C0-H | 39 | 1 | 67.944 | 36.028 |

H 적용 계획 32개의 전체 Σdt 합은 57.002s, 그 controller가 실제 호출된 구간 합은 28.472s다. 31/32는 전체 계획시간보다 일찍 교체/중단됐고, completed=True로 끝난 H 계획은 0개다. 따라서 Σdt 합과 실제 도착시간을 빼서 추종 지연이라고 부를 수 없다. `path_schedules.csv`에는 계획별 Σdt, 실제 보유/추종 시간, 교체 검열 여부를 기록했다. NA의 비교 계획시간은 동결 SP 호길이/속도 적분+이상적 정렬시간이며 실제 가감속/미래 FRESH를 완전히 표현하지 않는다.

## 게이트 통과 후 10회 준비

C0-H만 SLW/LC/L2/H1/H2 × seed201/202 = 10회, 새 root `../artifacts/isaac6/phase28t_main_01`. C0 10개는 Phase27-R, C0-NA 10개는 Phase28에서 재사용한다. smoke_02는 이 10회에 포함하지 않는다. 기존 Phase28 순서에서 H만 취하고, 재개·잠금·short socket 검사·디스크 검사·기술실패 1회 재시도·재실패 scene×seed 제외를 그대로 사용한다. seed201 원본/seed202 축소 저장과 run 종료 cache cleanup 유지. 새 성능 라벨은 만들지 않는다. gate는 준비 자격 기준이며 성능 우위를 뜻하지 않는다.

본 report는 방법별 연속 지표와 같은 seed 차이, clip 원인·추종 오차·시간예산·계획시간 비교를 자동 생성한다. 명령은 문서에만 기록했으며 실행하지 않았다.

FROZEN main protocol SHA256 `564e9fd8e8ab21dbd7192a668778f89233fc0ccc54d9c33c54ef73f837de1f75`. 단위테스트 7개와 실제 base launcher 10개 조합 인자 검증/dry-run 통과, 새 run 시작 0. 여유 공간 194.60GB, 보수적 필요량 55.04GB(20GB reserve 포함). 과거 launcher 시간 기반 예상 28.0분, 30% 여유 포함 약 36.4분; 기술 재시도는 추가. 매 run 전 여유 공간을 다시 검사한다.

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase28t.campaign --run-root ../artifacts/isaac6/phase28t_main_01 > ../artifacts/isaac6/phase28t_main_01.log 2>&1 < /dev/null &
```

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase28t.campaign --run-root ../artifacts/isaac6/phase28t_main_01 --status
```

보고서 재생성: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase28t.review --smoke-root ../artifacts/isaac6/phase28t_smoke_02`
