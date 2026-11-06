# Phase28 준비 R1 — 실패 진단과 정식화 재검사

**GATE_FAIL**. 실패 조건: `['same:accepted', 'new:accepted']`. 기존 주행·Phase28 오프라인 결과·C0-NA 정의·원 protocol은 보존했다. Isaac·본 주행·NoMaD 추론·새 렌더는 실행하지 않았다. 요청한 초기화용 C0-NA72Hz 수치 전방 적분과 저장 입력 SLSQP만 수행했다. 새 튜닝·상수 변경·결과를 본 뒤 재풀이 없음.

R1 protocol SHA256 `38e112e8a4c3d93aa9304598d22aa2c1c730a8beef7c6084a1e804e3d2053c8a`. 원 protocol SHA256 `27b35e6a3f9434b2728ae03d1fb2bb10bda0ee37b612b1b3f5375bfb47e154cb`. 표본·초기화 시계·scaling·경계식·fallback/시간 규칙을 평가 전에 고정했다. 단위테스트 35개 통과.

## 1. 기존200개 실패 진단

원래 결과: 수락26, SOLVER_FAILURE172, TIMEOUT2. 원 파일에는 exit message와 반복 수만 있고 실패한 x0/x_final은 없다. 아래 exit mode는 설치된 SciPy SLSQP의 message→mode 대응(3/4/8/9)을 적용한 것으로, 원 숫자 status가 저장되어 있었다고 주장하지 않는다.

| stratum | exit_mode | message | count |
|---|---|---|---|
| ALL | 8 | Positive directional derivative for linesearch | 59 |
| ALL | 4 | Inequality constraints incompatible | 74 |
| ALL | 3 | More than 3*n iterations in LSQ subproblem | 19 |
| ALL | 9 | Iteration limit reached | 20 |
| C0_SAFE_RANDOM | 4 | Inequality constraints incompatible | 33 |
| C0_SAFE_RANDOM | 8 | Positive directional derivative for linesearch | 35 |
| C0_SAFE_RANDOM | 3 | More than 3*n iterations in LSQ subproblem | 5 |
| C0_SAFE_RANDOM | 9 | Iteration limit reached | 16 |
| ACTUAL_ALIGNMENT | 8 | Positive directional derivative for linesearch | 24 |
| ACTUAL_ALIGNMENT | 4 | Inequality constraints incompatible | 41 |
| ACTUAL_ALIGNMENT | 9 | Iteration limit reached | 4 |
| ACTUAL_ALIGNMENT | 3 | More than 3*n iterations in LSQ subproblem | 14 |

초기값은 원 B 예측값·snapshot·직전 **원래 수락 해**를 사용해200건 모두 결정적으로 복원했다. 마지막 반복은 원 SOLVER_FAILURE172건에 한해 원 정식화·상수·SLSQP 옵션·0.15s 한도로 한 번씩 **진단용 재풀이**했다. 원 message와 일치한 재풀이는 172/172건이다. CPU deadline 차이 때문에 재풀이 status가 달라질 수 있으므로, 실패율은 원 로그 기준으로 보존한다. 아래 final 수치는 원래 저장 iterate가 아니라 재풀이의 returned x 또는 timeout 직전 major callback x다. 첫 major iteration도 없으면 초기값임을 개별 JSON에 표시했다.

| original_mode | replay_mode | replay_message | count |
|---|---|---|---|
| 8 | 8 | Positive directional derivative for linesearch | 59 |
| 4 | 4 | Inequality constraints incompatible | 74 |
| 3 | 3 | More than 3*n iterations in LSQ subproblem | 19 |
| 9 | 9 | Iteration limit reached | 20 |

### 초기 제약 위반(원200개)

| cohort | stage | constraint | n | violated_events | dominant_events | maximum | p50 | p95 | unit |
|---|---|---|---|---|---|---|---|---|---|
| ORIGINAL_ALL200 | initial_violation | ACCELERATION | 200 | 131 | 26 | 115.13 | 1.1175 | 14.182 | m/s2 |
| ORIGINAL_ALL200 | initial_violation | ANGULAR_ACCELERATION | 200 | 180 | 52 | 279.92 | 2.8522 | 200.95 | rad/s2 |
| ORIGINAL_ALL200 | initial_violation | DT_LOWER | 200 | 0 | 0 | 0 | 0 | 0 | s |
| ORIGINAL_ALL200 | initial_violation | DT_UPPER | 200 | 0 | 0 | 0 | 0 | 0 | s |
| ORIGINAL_ALL200 | initial_violation | FIRST_TWIST_HEADING_EQUALITY | 200 | 0 | 0 | 0 | 0 | 0 | rad |
| ORIGINAL_ALL200 | initial_violation | FIRST_TWIST_POSITION_EQUALITY | 200 | 0 | 0 | 0 | 0 | 0 | m |
| ORIGINAL_ALL200 | initial_violation | NO_STATIONARY_ROTATION | 200 | 98 | 11 | 5.8897 | 0.1502 | 0.4 | rad/s |
| ORIGINAL_ALL200 | initial_violation | OMEGA | 200 | 193 | 96 | 29.533 | 1.7592 | 19.847 | rad/s |
| ORIGINAL_ALL200 | initial_violation | SDF | 200 | 28 | 2 | 0.115 | 0 | 0.11114 | m |
| ORIGINAL_ALL200 | initial_violation | SPEED | 200 | 128 | 12 | 11.725 | 0.19677 | 4.0504 | m/s |
| ORIGINAL_ALL200 | initial_violation | YAW_BOUND | 200 | 0 | 0 | 0 | 0 | 0 | rad |

### 원 실패172개: 초기값과 재풀이 마지막 반복

| cohort | stage | constraint | n | violated_events | dominant_events | maximum | p50 | p95 | unit |
|---|---|---|---|---|---|---|---|---|---|
| ORIGINAL_FAILURE172 | initial_violation | ACCELERATION | 172 | 119 | 23 | 115.13 | 1.6936 | 18.222 | m/s2 |
| ORIGINAL_FAILURE172 | initial_violation | ANGULAR_ACCELERATION | 172 | 161 | 43 | 279.92 | 3.0392 | 202.46 | rad/s2 |
| ORIGINAL_FAILURE172 | initial_violation | DT_LOWER | 172 | 0 | 0 | 0 | 0 | 0 | s |
| ORIGINAL_FAILURE172 | initial_violation | DT_UPPER | 172 | 0 | 0 | 0 | 0 | 0 | s |
| ORIGINAL_FAILURE172 | initial_violation | FIRST_TWIST_HEADING_EQUALITY | 172 | 0 | 0 | 0 | 0 | 0 | rad |
| ORIGINAL_FAILURE172 | initial_violation | FIRST_TWIST_POSITION_EQUALITY | 172 | 0 | 0 | 0 | 0 | 0 | m |
| ORIGINAL_FAILURE172 | initial_violation | NO_STATIONARY_ROTATION | 172 | 96 | 10 | 5.8897 | 0.4 | 0.4033 | rad/s |
| ORIGINAL_FAILURE172 | initial_violation | OMEGA | 172 | 169 | 82 | 29.533 | 2.0264 | 20.058 | rad/s |
| ORIGINAL_FAILURE172 | initial_violation | SDF | 172 | 28 | 2 | 0.115 | 0 | 0.11208 | m |
| ORIGINAL_FAILURE172 | initial_violation | SPEED | 172 | 119 | 12 | 11.725 | 0.34723 | 4.149 | m/s |
| ORIGINAL_FAILURE172 | initial_violation | YAW_BOUND | 172 | 0 | 0 | 0 | 0 | 0 | rad |
| ORIGINAL_FAILURE172_REPLAY | last_violation | ACCELERATION | 172 | 160 | 100 | 9.1709e+14 | 5388.2 | 2.54e+11 | m/s2 |
| ORIGINAL_FAILURE172_REPLAY | last_violation | ANGULAR_ACCELERATION | 172 | 152 | 10 | 286.42 | 1.9943 | 209.87 | rad/s2 |
| ORIGINAL_FAILURE172_REPLAY | last_violation | DT_LOWER | 172 | 0 | 0 | 2.7756e-17 | 0 | 0 | s |
| ORIGINAL_FAILURE172_REPLAY | last_violation | DT_UPPER | 172 | 0 | 0 | 0 | 0 | 0 | s |
| ORIGINAL_FAILURE172_REPLAY | last_violation | FIRST_TWIST_HEADING_EQUALITY | 172 | 99 | 0 | 0.040896 | 1.3046e-05 | 0.0063486 | rad |
| ORIGINAL_FAILURE172_REPLAY | last_violation | FIRST_TWIST_POSITION_EQUALITY | 172 | 52 | 0 | 4.5763e+11 | 0 | 16.265 | m |
| ORIGINAL_FAILURE172_REPLAY | last_violation | NO_STATIONARY_ROTATION | 172 | 84 | 0 | 0.62313 | 0.17509 | 0.40243 | rad/s |
| ORIGINAL_FAILURE172_REPLAY | last_violation | OMEGA | 172 | 149 | 6 | 28.743 | 0.96309 | 20.304 | rad/s |
| ORIGINAL_FAILURE172_REPLAY | last_violation | SDF | 172 | 129 | 47 | 4.1579e+13 | 271.92 | 3.0278e+09 | m |
| ORIGINAL_FAILURE172_REPLAY | last_violation | SPEED | 172 | 155 | 7 | 3.2344e+14 | 1439.6 | 3.1451e+10 | m/s |
| ORIGINAL_FAILURE172_REPLAY | last_violation | YAW_BOUND | 172 | 0 | 0 | 0 | 0 | 0 | rad |

`violated_events`는 해당 제약을 하나라도1e−7보다 더 위반한 사건 수다. maximum/p50/p95는 표에 적힌 물리 단위다. dominant_events는 사건마다 정규화 위반이 가장 큰 제약 한 종류를 센다(SDF/.025, v/.3, ω/.4, a/.5, 각가속도/α, dt하한/.1·상한/1, 첫 위치 equality/.05, 첫 yaw equality/.4). 다른 단위를 raw 값으로 직접 비교하지 않는다. 모든 값이 허용오차 안이면 NONE_FEASIBLE로 별도 집계되므로 dominant 합이 전체 수보다 작을 수 있다. 원 실패군의 초기값과 마지막 상태는 별도 CSV/JSON으로 보존했다.

## 2. 승인된 개정만 적용

- 초기화: B 예측 상태에서 동결 C0-NA를72Hz 적분한다. 10개 미래 pose와 dt의 시계는 원 H cold 초기값의 dt 또는 직전 수락 해의 dt 그대로다. 따라서 지평선은 기존Σdt(1–10s)이며 새 상수는 없다. 이전 해의 공간 초기값만 NA 궤적으로 대체하고 시간 warm start는 유지한다. 경로 끝에 도달하면 도달 pose에서 정지해 남은 시계를 채운다(끝점으로 순간이동하지 않음). 이 endpoint padding은 가속도 위반을 만들 수 있으므로 INIT_ONLY 전에 전부 검사한다.
- 첫 구간 integrate_se2 equality를 제거했다. x0=B pose는 계속 고정이다. 첫 구간 대표 속도는 그 구간 중심에 있으므로 초기 가속도는 `(v_first−v0)/(dt0/2)`, 각가속도도 같은 식으로 hard 제한한다. 내부 구간 rate는 원 식 그대로다. 실행 시간 보간에는 t=0의 v0/ω0 anchor만 추가한다. feedback gain·최종 clip·90° 규칙은 변경하지 않는다.
- scaling: `x=S·z`, S는 위치0.3m·각도0.4rad·dt1s(기존1초 속도 한계에서 정한 값). 목적·제약 Jacobian과 bounds에 같은 chain rule을 적용한다. **목적함수 자체와 원래 제약 행은 수치적으로 동일함을 테스트**했다.
- 출력: 수렴·제약·certificate·0.15s를 모두 만족하면 OPTIMIZED. 수렴/제약/certificate 실패 시, 미리 계산한 NA 초기값이 모든 제약·bounds·같은 certificate를 만족하고 시간 안에 반환되면 INIT_ONLY. 아니면 FALLBACK. 원래 시간 제한 정책은 유지하여 TIMEOUT은 INIT_ONLY로 늦게 수락하지 않는다.

원래 추종σ0.05, 비홀로노믹σ0.03, smoothingσ0.03, 여유0.15/0.05, 시간0.1Σdt, v0.3·ω0.4·a0.5·각가속도2.0, dt0.1–1.0, SLSQP100/1e−8,0.15s 한도는 그대로다. R2/R3·지도·필터·평가·C0-NA 파일은 수정하지 않았다.

## 3. 같은200개와 새200개 재검사

same은 원 manifest의 정확히 같은200개다. 예측B·속도를 원 저장값과1e−12 이내로 검산했다. new는 seed20261107, 동일한 C0 SAFE 무작위100/실제 정렬 SAFE FRESH100 규칙이며 **원200개를 제외한 풀에서** 뽑았다. 표본 내부·두 표본 사이 중복은0이다. RAW B0는 depth가 없어 두 번째 층에서도 제외하며 기존 층화 정의와 동일하다. 각 표본의 시간순·run별로 직전 수락 해의 dt만 이어간다. 선택되지 않은 사건은 풀지 않았다.

| sample | stratum | n | optimized | init_only | fallback | optimized_fraction | accepted_fraction | p50_s | p95_s | over_015_fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| same | ALL | 200 | 160 | 11 | 29 | 0.8 | 0.855 | 0.061269 | 0.086638 | 0.005 |
| same | C0_SAFE_RANDOM | 100 | 74 | 6 | 20 | 0.74 | 0.8 | 0.064121 | 0.086638 | 0 |
| same | ACTUAL_ALIGNMENT | 100 | 86 | 5 | 9 | 0.86 | 0.91 | 0.056247 | 0.085651 | 0.01 |
| new | ALL | 200 | 153 | 20 | 27 | 0.765 | 0.865 | 0.05778 | 0.088489 | 0 |
| new | C0_SAFE_RANDOM | 100 | 71 | 14 | 15 | 0.71 | 0.85 | 0.060712 | 0.092565 | 0 |
| new | ACTUAL_ALIGNMENT | 100 | 82 | 6 | 12 | 0.82 | 0.88 | 0.055033 | 0.083126 | 0 |

p50/p95·0.15s 초과 비율은 각 층100개 전체를 분모로 한다. 시간은 B 예측, NA 초기 적분, solver, 제약·certificate, 진단 bookkeeping까지 포함한 전체 호출이다. npz 로딩과 JSON 저장은 제외한다. planning-only와 bookkeeping 시간도 사건별로 남겼다. 지연 초과로 수락을 허용하거나 계산시간을0.15로 잘라 보고하지 않았다.

### 수락 해의 제한·시작 상태

| sample | stratum | accepted | max_w | max_a | max_angular_acceleration | max_start_pose_error | max_start_time_v_error | max_start_time_w_error | max_first_midpoint_dv | max_first_midpoint_dw | max_first_command_dv | max_first_command_dw |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| same | C0_SAFE_RANDOM | 80 | 0.4 | 0.5 | 2 | 0 | 0 | 0 | 0.25 | 0.8 | 0 | 0.22222 |
| same | ACTUAL_ALIGNMENT | 91 | 0.4 | 0.5 | 2 | 0 | 0 | 0 | 0.25 | 0.8 | 0 | 0.22222 |
| new | C0_SAFE_RANDOM | 85 | 0.4 | 0.5 | 2 | 0 | 0 | 0 | 0.25 | 0.8 | 0 | 0.22222 |
| new | ACTUAL_ALIGNMENT | 88 | 0.4 | 0.5 | 2 | 0 | 0 | 0 | 0.25 | 0.8 | 0 | 0.22222 |

`max_start_time_*`는 시간 보간 궤적의 t=0 anchor 오차다. 새 경계식은 첫 구간 평균속도가 v0와 같도록 요구하지 않으므로 `max_first_midpoint_dv/dw`를 별도로 보고한다. 이를 순간적인 t=0 jump와 혼동하지 않는다. 실제 첫9Hz 명령의 변화 `max_first_command_dv/dw`도 병기한다. 이는 동결 feedback·clip·기존 각속도의 감속을 포함하며, 연속시간 곡선 anchor 오차와는 다른 지표다. 최대a·각가속도에는 새 초기 boundary rate도 포함한다.

### OPTIMIZED만: 같은 사건의 C0-NA 대비 예상 시간

| sample | stratum | optimized | optimized_delta_time_median_s | optimized_delta_time_p95_s |
|---|---|---|---|---|
| same | C0_SAFE_RANDOM | 74 | 0.8908 | 3.5064 |
| same | ACTUAL_ALIGNMENT | 86 | 1.3682 | 3.5081 |
| new | C0_SAFE_RANDOM | 71 | 0.68688 | 3.1668 |
| new | ACTUAL_ALIGNMENT | 82 | 1.2031 | 3.1608 |

차이는 H Σdt − C0-NA의 동결 SP 일정 적분(+필요 시 이상적 출발 정렬/감속시간)이다. 같은 B 기준이며 계산 대기·미래 FRESH·PP 추종 오차·goal 성공을 포함하지 않는다. INIT_ONLY를 이 비교에 섞지 않았다. 실제 주행 도착 시간으로 해석하지 않는다.

### R1 FALLBACK 이유

| sample | reason | count |
|---|---|---|
| same | SOLVER_FAILURE | 28 |
| same | TIMEOUT | 1 |
| new | SOLVER_FAILURE | 27 |

R1 초기·마지막 위반 상세는 `r1_constraint_violations.csv`, 개별 x0/last_x와 certificate는 `same/`, `new/`에 있다. 원 실패 진단은 `diagnosis/`에 분리해 원 결과를 덮어쓰지 않았다.


### 남은 FALLBACK에서 초기값을 사용할 수 없었던 이유

| 표본 | FALLBACK 수 | 초기 최대 정규화 위반 | 사건 수 |
|---|---|---|---|
| same | 29 | ACCELERATION | 2 |
| same | 29 | INITIAL_ANGULAR_ACCELERATION | 18 |
| same | 29 | SDF | 2 |
| same | 29 | INITIAL_ACCELERATION | 6 |
| same | 29 | NONE_FEASIBLE | 1 |
| new | 27 | INITIAL_ANGULAR_ACCELERATION | 15 |
| new | 27 | INITIAL_ACCELERATION | 4 |
| new | 27 | ACCELERATION | 4 |
| new | 27 | ANGULAR_ACCELERATION | 1 |
| new | 27 | SDF | 3 |

기존 표본29건·새 표본27건의 FALLBACK 모두 NA 초기값 수락 검증을 통과하지 못했다. 특히 초기 각가속도가 최대 정규화 위반인 경우가18/29건,15/27건이다. C0-NA에는 H의2rad/s² 제한이 없으므로 NA 실행 궤적이라고 H 제약을 자동으로 만족하지 않는다. 기존 표본의 NONE_FEASIBLE1건은 점 제약은 통과했지만9점 여유 certificate가 실패했다. 이 표는 저장된 initial_violation과 initial_certificate의 사후 집계이며 새 풀이가 아니다.

## 4. 주행 준비 게이트

각 **200개 표본 전체**에서 OPTIMIZED≥70%, OPTIMIZED+INIT_ONLY≥90%, p95≤0.15s를 모두 만족해야 한다. 두 층은 각각 보고하되 요청한 게이트 분모는200이다.

| sample | n | optimized | accepted | optimized_fraction | accepted_fraction | p95_s | optimized_ok | accepted_ok | timing_ok | passed |
|---|---|---|---|---|---|---|---|---|---|---|
| same | 200 | 160 | 171 | 0.8 | 0.855 | 0.086638 | True | False | True | False |
| new | 200 | 153 | 173 | 0.765 | 0.865 | 0.088489 | True | False | True | False |

최종: **GATE_FAIL**. 미충족 항목: same:accepted, new:accepted. 주행 명령을 제공하지 않고 중단한다. 수치나 구조를 추가 조정하지 않았다.

재현: `/usr/bin/python3`, `PYTHONPATH=research`. 저장 입력 기반 오프라인 계산만 수행했고 venv에 패키지를 설치하지 않았다. 기존 결과·원 protocol·C0-NA hash 보존을 확인했다.
