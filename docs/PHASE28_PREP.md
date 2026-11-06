# Phase28 준비 — C0-NA / C0-H

**Isaac·smoke·본 주행은 실행하지 않았다.** 단위테스트, 고정200개 저장 사건의 단일 SLSQP 풀이, B 예측을 위한 짧은 기존 실행기72Hz 전방 적분만 수행했다. NoMaD 추론·새 depth 렌더·튜닝 없음. 기준은 Phase27-R 수정 실행기이며 C0 결과60개 중 C0 10개를 비교행으로 재사용한다.

등록 protocol SHA256 `27b35e6a3f9434b2728ae03d1fb2bb10bda0ee37b612b1b3f5375bfb47e154cb`; 표본 manifest SHA256 `4651d81a163a907f0b93350ca5d6e934fcd13ff61d7b5b25f7db60be5ee0ffd5`. 수치·표본·source hash를 첫 실제 저장 사건 solve 전에 고정했다. 단위테스트 23개 통과. 기존 결정 계층·R2/R3·depth 필터·지도·평가기 source는 변경하지 않았다.

## 방법과 plant 확인

| 방법 | 평소 주행 | 실패·우회 | 제자리 출발 정렬 |
|---|---|---|---|
| C0(재사용) | Phase27-R PP+SP | 기존 R2/R3·회복 | 정지20°/이동45° |
| C0-NA | 동일 PP+SP | 동일 R2/R3·회복 | B 이후 호길이5cm 목표 방향이 엄격히90° 초과일 때만 |
| C0-H | SAFE FRESH마다 시간 SE(2) Graph, feedforward+feedback | H 실패 시 C0-NA; R2/R3 계획·결정·회복은 동결 | H의 제자리 회전도 기준 방향90° 초과일 때만 |

실제 Phase26/27-R config의 `plant_alpha='inf'`와 AngularPlant 코드를 확인했다. **기존 유한 각가속도 한계가 없어 H 계획·추종 한계를2.0rad/s²로 고정**했다. 유한 plant가 있는 config에는 그 값을 쓰는 분기가 있다. 물리 plant 설정과 기존 R2/R3/RECOVER 코드는 바꾸지 않았다. H 시간 궤적 추종 이후 최종 명령을0≤v≤0.3, |ω|≤0.4, |Δv|≤0.5/9, |Δω|≤2/9로 다시 clip한다. fallback C0-NA·기존 우회/회복은 그 동결 실행 규칙이며 H feedback 통계와 분리한다.

## H의 고정 수식·시간 규칙

B는 dispatch 후0.15s를 지난 첫9Hz tick의 예측 상태다(정상 controller dispatch에서2/9s). 현재 실행기의 상태를 복사해 PP/SP 또는 H 추종, 기존 plant, 정확72Hz `integrate_se2`로 그 tick까지 적분한다. 별도 등속 근사나 미래 저장 pose를 B로 쓰지 않는다. 계산 동안 OLD 실행기를 유지하고, 지정 tick에서만 적용한다. 최신 FRESH나 R2/R3/회복 전환이 생기면 해당 H job은 버린다.

변수는 B 고정 pose x0와 별개인 미래10pose x1..x10,10개 dt(0.1–1.0s), 총40개다. 초기 v0·ω0는 B 예측값이다. 첫 구간은 `integrate_se2(B,v0,ω0,dt0)`와 hard equality로 연결한다. 따라서 초기 pose뿐 아니라 첫 구간 속도·yaw rate도 고정한다. 경로 chord길이 l과 Δθ에 대해 v=l/(dt·sinc(Δθ/2)), ω=Δθ/dt; 이웃 구간 중심시간 차이로 a·각가속도를 계산한다. v≤0.3, |ω|≤0.4, |a|≤0.5, |angular_accel|≤2는 hard다. 기준이 뒤쪽이 아니면 추가 `|ω|≤40v`로 v=0에서 새 회전을 허용하지 않는다.

목적함수는 다음5항의 합이다. ①참조10점 XY 제곱오차/0.05² ②TEB 방향-heading 비홀로노믹 및 역방향 hinge residual/0.03² ③2차 XY 차분/0.03² ④node+midpoint에서 max(0,0.15−d)²/0.05² ⑤0.1Σdt. d는 몸체 반경이 차감된 기존 depth SDF 값이다. node+midpoint hard d≥0.025이며, 출력 certificate는 구간당9점의 `d−h/√2−L/16≥0.025`와 정확 점유 site 거리≥0.025를 모두 검사한다. NORMAL H는 원래 선택과 같은 base depth 지도(unknown 비점유)를 쓴다. R3의 보수적 지도는 바꾸지 않는다.

SLSQP(maxiter100, ftol1e−8), 해석적 목적·제약 Jacobian, 단일 시작점, 직전 실제 적용 H 해의 잔여를 warm start로 쓴다. 0.15s에는 B 예측·초기화·풀이·certificate를 포함하며 npz 로딩은 제외한다. 해가 수렴해도 제약/certificate/시간한도를 통과하지 못하면 수락하지 않는다. 실패 사유별 로그를 남기고 같은 선택 경로를 C0-NA로 적용한다. 새로운 파라미터 탐색·재시도는 없다.

추종은 시간 축으로 pose와 구간 중심 속도를 보간한다. body 좌표 오차로 Δv=0.5e_x, Δω=1.0e_y+0.5e_θ를 더한 뒤 최종 제한을 적용하고 clip 비율을 기록한다. 목표 경과 후에는 같은 제한 안에서 정지한다. 미래 reference pose의 선형 보간과 feedforward의 속도 보간은 근사 정합이며, 실행 오차는 feedback과 최종 제한으로 제어한다. 이번 오프라인 수치는 주행 안전/성공 보장이 아니다.

Phase12–18에서 사용한 PurePursuit/XYPath, depth Snapshot·SDF 인터페이스, v4 norm/구간 certificate 식을 재사용했다. frozen Phase18D SP는 NA 및 OLD 예측에 재사용한다. 기존 graph/solver 파일은 수정하지 않았다.

## 두 층의 표본과 결과

seed20261106으로 첫100개는 C0 SAFE FRESH 전체에서 무작위 추출했다. 둘째100개는 전체 Phase27-R depth 사용 방법의 **실제 정렬=True인 SAFE FRESH** 중 첫 층과 중복되지 않게 추출했다. B0는 depth를 저장하지 않아 H 입력을 구성할 수 없으므로 제외하며, R2/R3 적용은 FRESH handoff가 아니므로 제외했다. 원래 사건 인덱스와 SDF hash를 먼저 저장했다. 각 층100개, 총200개를 한 번씩만 풀었다. 두 번째 층은 정렬 사건을 풍부하게 포함한 진단 층이므로 전체 run으로 외삽하지 않는다.

표본 구성: `{('C0_SAFE_RANDOM', 'C0'): 100, ('ACTUAL_ALIGNMENT', 'B4_ASTAR'): 15, ('ACTUAL_ALIGNMENT', 'B1_SAFE_TE'): 22, ('ACTUAL_ALIGNMENT', 'B2_SAFE_RTC'): 29, ('ACTUAL_ALIGNMENT', 'B3_SAFE_ROTATE'): 25, ('ACTUAL_ALIGNMENT', 'C0'): 9}`. 각 run 안에서 시간순으로 계산하고, 선택된 사건 중 직전 수락 결과만 warm start로 썼다. 선택되지 않은 중간 사건은 풀지 않았으므로 온라인 warm-start 이력과 같지 않다. TE의 OLD 예측은 저장된 chunk 추가/KEEP 기록·progress를 복원해 원래 TE 조향 코드를 쓴다.

| stratum | n | solver_success | solver_success_fraction | accepted | acceptance_fraction | wall_p50_s | wall_p95_s | over_015_fraction | accepted_max_w | accepted_max_a | accepted_max_angular_acceleration | accepted_max_start_pose_error | accepted_max_start_v_error | accepted_max_start_w_error | expected_time_difference_median_s | expected_time_difference_p95_s | planned_zero_error_clip_fraction_median | converged_max_abs_w | converged_max_abs_a | converged_max_abs_angular_acceleration | converged_start_pose_error | converged_start_speed_error | converged_start_omega_error | converged_time_difference_median_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C0_SAFE_RANDOM | 100 | 11 | 0.11 | 11 | 0.11 | 0.05392 | 0.1219 | 0 | 0.4 | 0.5 | 2 | 0 | 2.62e-11 | 9.329e-11 | 1.259 | 3.309 | 0.1429 | 0.4 | 0.5 | 2 | 0 | 2.62e-11 | 9.329e-11 | 1.259 |
| ACTUAL_ALIGNMENT | 100 | 15 | 0.15 | 15 | 0.15 | 0.03544 | 0.09451 | 0.02 | 0.4 | 0.5 | 2 | 0 | 3.314e-10 | 7.634e-10 | 1.799 | 2.792 | 0.2917 | 0.4 | 0.5 | 2 | 0 | 3.314e-10 | 7.634e-10 | 1.799 |

최대ω·a·각가속도와 시작 불연속은 **수락 해** 기준이다. 사건 단위 CSV에는 수렴했으나 거절된 해의 값도 보존했다. 성공률은 solver 수렴률과 certificate까지 통과한 수락률을 분리한다. p50/p95·초과율의 분모는 각 층 전체100개다. NA 대비 시간 차이는 같은 예측 B에서 H의Σdt − NA의SP 호길이/속도 적분(+90°초과 정렬의 이상적 회전·감속시간)이다. 계산 대기2/9s, 실제 PP 추종 오차·앞으로의 FRESH·목표 도착은 포함하지 않는다. NA 초기 가속 transient도 완전한 rollout으로 재현한 값이 아니므로 **궤적 일정의 기대시간 비교**일 뿐이다.

offline clip 비율은 수락 궤적의 계획 pose에서 추종기를 조회한 **오차0 조건**이다. 로봇 궤적은 적분하지 않았다. 실제 feedback clip 비율은 본 주행 후 보고한다.

### 수렴 해 비용 기여 비율 중앙값

| stratum | converged | terms_available | tracking | nonholonomic | smoothing | clearance | time |
|---|---|---|---|---|---|---|---|
| C0_SAFE_RANDOM | 11 | 11 | 0.4127 | 0.09063 | 0.1729 | 0 | 0.04706 |
| ACTUAL_ALIGNMENT | 15 | 15 | 0.4182 | 0.07613 | 0.2179 | 0 | 0.08132 |

각 값은 해당 해의5항 합 대비 비율의 중앙값이다. 항별 중앙값의 합은1일 필요가 없다. `terms_available`은 timeout 전에 비용 분해가 확보된 수렴 해 수다.

### 실패·수락 사유

| stratum | reason | count |
|---|---|---|
| C0_SAFE_RANDOM | ACCEPTED | 11 |
| C0_SAFE_RANDOM | SOLVER_FAILURE | 89 |
| ACTUAL_ALIGNMENT | SOLVER_FAILURE | 83 |
| ACTUAL_ALIGNMENT | ACCEPTED | 15 |
| ACTUAL_ALIGNMENT | TIMEOUT | 2 |

##20회 실행 준비·report 틀

C0-NA/C0-H × SLW/LC/L2/H1/H2 × seed201/202 =20회. C0는 Phase27-R의10개 결과만 재사용한다. 순서는 기존 Phase26 순서에서 C0의 scene×seed 순서를 취하고 각 위치에서 NA→H로 고정했다. 기술 실패 동일 seed1회 재시도, 최종 실패 scene×seed는 paired 분석에서 제외하고 원 기록을 남긴다. 기존 평가기·장면·벽 검증·checkpoint·Topomap·NoMaD seed·depth 설정은 동결이다.

완료 후 report 틀: scene×방법의 n/도착/충돌/도착시간/평균속도/정지비율/정렬 회전·감속비율/최소 여유 표, 같은 seed의 C0 대비 연속 지표 차이, H 수락·사유별fallback·계산시간·최종 feedback clip 비율. 이번 요청에는 성능 판정 임계값이 없으므로 새 승패 라벨이나 통계 판정을 만들지 않는다. C0 재사용 run과 새 두 방법의 실행 시점이 다름을 표기한다.

run-root `../artifacts/isaac6/phase28_pilot_01`, 결과 `research/results/phase28/`, 실행 후 문서 `docs/PHASE28_RESULTS.md`. simulator/worker가 모두 끝난 뒤 정확한 allowlist `portable/cache`, `pycache`만 삭제하는 옵션을 켰다. RGB/depth·로그·snapshot·평가 자료는 삭제하지 않는다. 기존 원본 보관 정책(seed201 전체/202 축소)과 run 전 용량 검사는 유지한다.

디스크: 여유 234.85GB, 삭제 효과를 미리 빼지 않은 보수적 필요량 90.09GB(20GB reserve 포함), 충분 여부 `True`. 새 주행 시간은 측정하지 않았으며 이전 C0 launcher 시간으로 약1.3시간 규모다. smoke를 실행했다고 주장하지 않는다.

사용자 실행 명령(실행하지 않음):

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase28.campaign --run-root ../artifacts/isaac6/phase28_pilot_01 > ../artifacts/isaac6/phase28_pilot_01.log 2>&1 < /dev/null &
```

진행 확인:

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase28.campaign --run-root ../artifacts/isaac6/phase28_pilot_01 --status
```

report는 `/usr/bin/python3`, `PYTHONPATH=research`를 사용하며 campaign 마지막 단계에서 결과 commit·push까지 수행한다. venv 설치 없음.
