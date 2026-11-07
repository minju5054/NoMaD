1. 라벨: **PENDING_INCOMPLETE_EVIDENCE**; BEATS: {'SAFE_TE': None, 'SAFE_RTC': None, 'NOMAD_RAW': None}.
2. 도착(유효 run): OURS 3/5 / ASTAR+EC 4/5 / SAFE_TE 3/5 / SAFE_RTC 2/5 / NOMAD_RAW 1/5.
3. 충돌: OURS 0 / ASTAR+EC 0 / SAFE_TE 2 / SAFE_RTC 1 / NOMAD_RAW 2.
4. OURS−ASTAR+EC 도착시간 짝차이 중앙값: -7.527777777777779s; 완료 25/75.
5. 멈춘 단계/상태: main / RUNNING; 이유: 진행 중, 중단 없음. 본 실행은 재개 가능.

# Phase35 주요 baseline 비교

Protocol FROZEN SHA256 `30b586995197409dff38dd21f1dbf7e63e18891652e9f00d5728775cfd0e9245`. 실험 시작 예산 기준 UTC epoch 1794071828, 최대6.5시간. oracle은 원 평가기에만 사용한다. 기존 결과/방법 파일을 수정하지 않는다.

## 동결 방법

| method | source | change |
|---|---|---|
| OURS | Phase32 C0-NA+EC | storage v2 only |
| ASTAR+EC | OURS + Phase21 B4 A* R2/R3 | solver wiring only; lambda4 / smoothing0 |
| SAFE_TE | Phase27-R B1 / Phase21 SAFE TE | C0-NA departure installer only; TE steering/KEEP preserved |
| SAFE_RTC | Phase27-R B2 / Phase18 RTC-hard | C0-NA installer only |
| NOMAD_RAW | Phase27-R B0 sample0 | C0-NA installer only; no depth/filter/recovery |

공통 실행기는 Phase32 C0-NA PP/SP(lookahead0.25, v≤0.3, |ω|≤0.4, a≤0.5, B 이후 suffix 방향 >90°일 때만 정렬)이다. SAFE_TE의 기존 ensemble target 조향·K/가중치/만료/KEEP는 그대로이며 속도와 출발 정렬은 최신 chunk 기준이다. NOMAD_RAW는 sample0, depth/filter/fallback/RECOVER 없음. SAFE_RTC는 동결 RTC-hard 생성/SAFE/handoff와 RECOVER를 유지한다. OURS·ASTAR+EC는 동일한 Phase32 EC·24-R 결정/보수적 지도/certificate/넘김을 사용하며 A*는 Phase21 B4처럼 R2와 R3 양쪽 자리를 대체한다(λ4, smoothing0).

저장 v2: snapshot/repair input의 values 생략, savez_compressed, STORAGE_RETROFIT 복원. 라이브 지도 계산은 그대로다. 기존 raw retention을 유지하고 run 종료 뒤 portable/cache·pycache를 정리한다. 지연D750·90초·goal0.3m·장면·평가기·seed는 동결이다.

## 사전 판정

BEATS_X: OURS 도착>X 도착 AND 충돌≤X. Graph 판정은 순서대로 GRAPH_BETTER(도착≥A*, 충돌≤A*, 그리고 도착>A* 또는 둘 다 성공한 짝 시간차 median<0), GRAPH_EQUAL(도착 차이±1 이내·충돌 같음), 나머지 GRAPH_WORSE다. 도착시간 차이는 OURS−비교법, 둘 다 성공한 짝만 사용한다. 75회 미완료/기술 무효가 남으면 모르는 충돌을 0으로 간주하지 않고 주 판정 보류, 관측된 수치와 임시 predicate만 저장한다. McNemar exact p는 참고이며 판정에 쓰지 않는다.

| baseline | n | wins | losses | ties | both_arrived | goal_time_delta_median_s | mcnemar_exact_p |
|---|---|---|---|---|---|---|---|
| ASTAR+EC | 5 | 1 | 2 | 2 | 2 | -7.5278 | 1 |
| SAFE_TE | 5 | 2 | 2 | 1 | 1 | -0.097222 | 1 |
| SAFE_RTC | 5 | 2 | 1 | 2 | 1 | -25.736 | 1 |
| NOMAD_RAW | 5 | 2 | 0 | 3 | 1 | 2.7917 | 0.5 |

BEATS 결과: `{'SAFE_TE': None, 'SAFE_RTC': None, 'NOMAD_RAW': None}`; Graph: `None`.

## 방법×장면

| method | scene | n | valid | goal | collision | goal_time_median_s | mean_speed_m_s | stopped_fraction | minimum_clearance_m | omega_saturation_fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| OURS | SLW | 1 | 1 | 1 | 0 | 70.792 | 0.09564 | 0.36257 | 0.060453 | 0.44909 |
| OURS | LC | 1 | 1 | 1 | 0 | 26.931 | 0.19713 | 0.1114 | 0.20122 | 0.51315 |
| OURS | L2 | 1 | 1 | 0 | 0 | — | 0.16271 | 0.16296 | 0.049371 | 0.39136 |
| OURS | H1 | 1 | 1 | 1 | 0 | 31.361 | 0.17481 | 0.12046 | 0.14556 | 0.46147 |
| OURS | H2 | 1 | 1 | 0 | 0 | — | 0.14644 | 0.24938 | 0.031204 | 0.32963 |
| OURS | ALL | 5 | 5 | 3 | 0 | 31.361 | 0.16271 | 0.16296 | 0.060453 | 0.44909 |
| ASTAR+EC | SLW | 1 | 1 | 0 | 0 | — | 0.086172 | 0.33827 | 0.045028 | 0.40247 |
| ASTAR+EC | LC | 1 | 1 | 1 | 0 | 42.931 | 0.13799 | 0.1967 | 0.057055 | 0.54351 |
| ASTAR+EC | L2 | 1 | 1 | 1 | 0 | 43.917 | 0.19016 | 0.10879 | 0.050247 | 0.56736 |
| ASTAR+EC | H1 | 1 | 1 | 1 | 0 | 30.417 | 0.17222 | 0.17534 | 0.039699 | 0.27397 |
| ASTAR+EC | H2 | 1 | 1 | 1 | 0 | 44.542 | 0.1912 | 0.097287 | 0.053823 | 0.55847 |
| ASTAR+EC | ALL | 5 | 5 | 4 | 0 | 43.424 | 0.17222 | 0.17534 | 0.050247 | 0.54351 |
| SAFE_TE | SLW | 1 | 1 | 0 | 1 | — | 0.16531 | 0.33548 | -0.00032023 | 0.47527 |
| SAFE_TE | LC | 1 | 1 | 1 | 0 | 27.028 | 0.20183 | 0.10689 | 0.24826 | 0.49024 |
| SAFE_TE | L2 | 1 | 1 | 1 | 0 | 73.014 | 0.17583 | 0.09435 | 0.26391 | 0.55868 |
| SAFE_TE | H1 | 1 | 1 | 0 | 1 | — | 0.13052 | 0.20497 | -0.0023434 | 0.58061 |
| SAFE_TE | H2 | 1 | 1 | 1 | 0 | 44.167 | 0.18678 | 0.10566 | 0.056935 | 0.57736 |
| SAFE_TE | ALL | 5 | 5 | 3 | 2 | 44.167 | 0.17583 | 0.10689 | 0.056935 | 0.55868 |
| SAFE_RTC | SLW | 1 | 1 | 0 | 1 | — | 0.10763 | 0.30323 | -0.0021449 | 0.54069 |
| SAFE_RTC | LC | 1 | 1 | 0 | 0 | — | 0.12202 | 0.13827 | 0.1561 | 0.55556 |
| SAFE_RTC | L2 | 1 | 1 | 0 | 0 | — | 0.12547 | 0.24568 | 0.02072 | 0.60988 |
| SAFE_RTC | H1 | 1 | 1 | 1 | 0 | 57.097 | 0.1433 | 0.14011 | 0.029347 | 0.64218 |
| SAFE_RTC | H2 | 1 | 1 | 1 | 0 | 53.958 | 0.15776 | 0.16885 | 0.035368 | 0.54286 |
| SAFE_RTC | ALL | 5 | 5 | 2 | 1 | 55.528 | 0.12547 | 0.16885 | 0.029347 | 0.55556 |
| NOMAD_RAW | SLW | 1 | 1 | 0 | 1 | — | 0.18906 | 0.30365 | -0.0015794 | 0.38102 |
| NOMAD_RAW | LC | 1 | 1 | 0 | 1 | — | 0.085424 | 0.35936 | -0.00017686 | 0.73262 |
| NOMAD_RAW | L2 | 1 | 1 | 0 | 0 | — | 0.16263 | 0.10617 | 0.061567 | 0.6284 |
| NOMAD_RAW | H1 | 1 | 1 | 1 | 0 | 28.569 | 0.18249 | 0.10112 | 0.034011 | 0.64998 |
| NOMAD_RAW | H2 | 1 | 1 | 0 | 0 | — | 0.16569 | 0.076543 | 0.062225 | 0.6284 |
| NOMAD_RAW | ALL | 5 | 5 | 1 | 2 | 28.569 | 0.16569 | 0.10617 | 0.034011 | 0.6284 |

도착시간은 성공 run만의 중앙값, 속도/정지/여유/포화는 run별 값의 중앙값이다. 최소여유는 참고이며 주 판정에 사용하지 않는다.

## 15개 scene×seed 짝

| scene | index | comparison | baseline | ours_goal | other_goal | ours_collision | other_collision | goal_difference | goal_time_difference_s |
|---|---|---|---|---|---|---|---|---|---|
| SLW | 212 | OURS - ASTAR+EC | ASTAR+EC | True | False | False | False | 1 | — |
| SLW | 212 | OURS - SAFE_TE | SAFE_TE | True | False | False | True | 1 | — |
| SLW | 212 | OURS - SAFE_RTC | SAFE_RTC | True | False | False | True | 1 | — |
| SLW | 212 | OURS - NOMAD_RAW | NOMAD_RAW | True | False | False | True | 1 | — |
| LC | 212 | OURS - ASTAR+EC | ASTAR+EC | True | True | False | False | 0 | -16 |
| LC | 212 | OURS - SAFE_TE | SAFE_TE | True | True | False | False | 0 | -0.097222 |
| LC | 212 | OURS - SAFE_RTC | SAFE_RTC | True | False | False | False | 1 | — |
| LC | 212 | OURS - NOMAD_RAW | NOMAD_RAW | True | False | False | True | 1 | — |
| L2 | 212 | OURS - ASTAR+EC | ASTAR+EC | False | True | False | False | -1 | — |
| L2 | 212 | OURS - SAFE_TE | SAFE_TE | False | True | False | False | -1 | — |
| L2 | 212 | OURS - SAFE_RTC | SAFE_RTC | False | False | False | False | 0 | — |
| L2 | 212 | OURS - NOMAD_RAW | NOMAD_RAW | False | False | False | False | 0 | — |
| H1 | 212 | OURS - ASTAR+EC | ASTAR+EC | True | True | False | False | 0 | 0.94444 |
| H1 | 212 | OURS - SAFE_TE | SAFE_TE | True | False | False | True | 1 | — |
| H1 | 212 | OURS - SAFE_RTC | SAFE_RTC | True | True | False | False | 0 | -25.736 |
| H1 | 212 | OURS - NOMAD_RAW | NOMAD_RAW | True | True | False | False | 0 | 2.7917 |
| H2 | 212 | OURS - ASTAR+EC | ASTAR+EC | False | True | False | False | -1 | — |
| H2 | 212 | OURS - SAFE_TE | SAFE_TE | False | True | False | False | -1 | — |
| H2 | 212 | OURS - SAFE_RTC | SAFE_RTC | False | True | False | False | -1 | — |
| H2 | 212 | OURS - NOMAD_RAW | NOMAD_RAW | False | False | False | False | 0 | — |

## 우회·EC·계산시간

| method | n | detour_triggers | detour_applied | detour_path_total_m | detour_execution_s | compute_n | compute_p50_s | compute_p95_s | ec_by_state | fallback_routes |
|---|---|---|---|---|---|---|---|---|---|---|
| OURS | 5 | 40 | 13 | 19.189 | 23.889 | 57 | 0.33066 | 0.65661 | {'NORMAL': {'checks': 682, 'rejects': 60, 'reject_fraction': 0.08797653958944282}, 'R2': {'checks': 22, 'rejects': 5, 'reject_fraction': 0.22727272727272727}, 'R3': {'checks': 91, 'rejects': 1, 'reject_fraction': 0.01098901098901099}} | {'NEXT_SAFE_FULL': 13, 'R2_TO_R3': 5, 'R3_FAILURE': 1, 'SAFE_SLOW': 4} |
| ASTAR+EC | 5 | 28 | 6 | 8.8732 | 10.222 | 34 | 0.28166 | 0.39306 | {'NORMAL': {'checks': 620, 'rejects': 42, 'reject_fraction': 0.06774193548387097}, 'R2': {'checks': 7, 'rejects': 4, 'reject_fraction': 0.5714285714285714}, 'R3': {'checks': 23, 'rejects': 0, 'reject_fraction': 0.0}} | {'SAFE_SLOW': 6, 'NEXT_SAFE_FULL': 7, 'R2_TO_R3': 4} |
| SAFE_TE | 5 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |
| SAFE_RTC | 5 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |
| NOMAD_RAW | 5 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |

우회 경로 길이는 실제 설치된 DETOUR polyline 길이 합, 실행시간은 APPLIED→END(종료 시 활성 구간 포함) 합이다. 계산시간은 R2/R3 4-process pool 전체 job 시간이며 inference/EC 시간과 다르다. EC는 상태별 CHECK 수/REJECT 수를 보고한다. 미사용 방법은 해당 없음이며 거절률0으로 해석하지 않는다.

## SAFE_RTC chunk 이어받기 지연·정지

| scene | index | chunk_delay_p50_s | chunk_delay_p95_s | inference_p50_s | inference_p95_s | stopped_fraction | command_state_seconds |
|---|---|---|---|---|---|---|---|
| H1 | 212 | 0.90278 | 1.0139 | 0.076 | 0.093683 | 0.14011 | {'WAYPOINT_TIMEOUT': 3.333333333333332, 'NORMAL': 47.444444444444436, 'ENDPOINT': 0.22222222222222587, 'ALIGN_BRAKE': 1.4305555555555607, 'ALIGN_ROTATE': 3.6666666666666643, 'STOP_WAIT': 1.0} |
| H2 | 212 | 0.90278 | 1.0139 | 0.074941 | 0.095857 | 0.16885 | {'WAYPOINT_TIMEOUT': 3.222222222222225, 'NORMAL': 42.06944444444444, 'ENDPOINT': 0.6666666666666687, 'ALIGN_BRAKE': 1.7777777777777786, 'ALIGN_ROTATE': 4.222222222222221, 'STOP_WAIT': 2.0} |
| L2 | 212 | 0.90278 | 1.0139 | 0.074758 | 0.089 | 0.24568 | {'WAYPOINT_TIMEOUT': 3.777777777777775, 'NORMAL': 64.55555555555554, 'ENDPOINT': 1.0000000000000009, 'ALIGN_BRAKE': 2.777777777777784, 'ALIGN_ROTATE': 12.888888888888891, 'STOP_WAIT': 2.0, 'RECOVER_ROTATE': 1.7777777777777786, 'WAIT_FRESH': 0.22222222222222143, 'KEEP_ACTIVE': 1.0} |
| LC | 212 | 0.90278 | 1.009 | 0.075958 | 0.095381 | 0.13827 | {'WAYPOINT_TIMEOUT': 3.555555555555568, 'NORMAL': 75.0, 'ENDPOINT': 0.4444444444444393, 'ALIGN_BRAKE': 2.5555555555555785, 'ALIGN_ROTATE': 8.444444444444418} |
| SLW | 212 | 0.90278 | 1.0139 | 0.071874 | 0.1231 | 0.30323 | {'WAYPOINT_TIMEOUT': 3.2222222222222214, 'NORMAL': 13.583333333333336, 'ALIGN_BRAKE': 1.888888888888884, 'ALIGN_ROTATE': 3.111111111111116, 'STOP_WAIT': 1.0, 'KEEP_ACTIVE': 2.0, 'ENDPOINT': 0.11111111111111072} |

Chunk 지연=application_sim_s−observation_sim_s(D750·추론 포함); received→apply 원자료도 runs.json에 기록했다. 정지는 실제72Hz |v|<0.01 비율, command_state_seconds는9Hz 명령 유지시간 합이다.

## 실패 분해(Phase31-D 그대로)

우선순위: 기술 실패 OTHER(성능 통계 제외); box contact→BOX_COLLISION(InnerCorner 등 구조벽은 WALL); 외곽 overlap/corridor stop→WALL_COLLISION; 목표≤0.6m→NEAR_GOAL_HOVER; 모든 돌발 상자 통과→POST_PASSAGE_TIMEOUT; SLW/LC 마지막10초 목표거리 감소<0.2m→STATIC_NARROW_STUCK; 상자 출현·미통과→DETOUR_FAIL; 미출현 또는 시작 최대변위<0.5m→EARLY_STUCK; 나머지OTHER. WALL_COLLISION 분해에는 margin 정지도 포함되나 주 판정 충돌은 원 evaluator 실제 overlap 값 그대로다.

| scene | index | method | primary_cause | minimum_goal_distance_m | last10_goal_progress_m | maximum_start_displacement_m | structural_contact | output |
|---|---|---|---|---|---|---|---|---|
| H2 | 212 | OURS | NEAR_GOAL_HOVER | 0.37664 | -1.0979 | 8.495 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H2_212_OURS/attempt1 |
| L2 | 212 | OURS | NEAR_GOAL_HOVER | 0.30214 | -1.7496 | 8.5615 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/L2_212_OURS/attempt1 |
| SLW | 212 | ASTAR+EC | STATIC_NARROW_STUCK | 1.2363 | -0.42444 | 3.7872 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_212_ASTAR+EC/attempt1 |
| H1 | 212 | SAFE_TE | BOX_COLLISION | 1.5923 | 0.6402 | 3.8621 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H1_212_SAFE_TE/attempt1 |
| SLW | 212 | SAFE_TE | WALL_COLLISION | 3.1725 | 1.826 | 2.0958 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_212_SAFE_TE/attempt1 |
| L2 | 212 | SAFE_RTC | NEAR_GOAL_HOVER | 0.55462 | 0.081748 | 8.6389 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/L2_212_SAFE_RTC/attempt1 |
| LC | 212 | SAFE_RTC | OTHER | 2.2704 | 0.73638 | 3.2885 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/LC_212_SAFE_RTC/attempt1 |
| SLW | 212 | SAFE_RTC | BOX_COLLISION | 2.6978 | 0.72484 | 2.5298 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_212_SAFE_RTC/attempt1 |
| H2 | 212 | NOMAD_RAW | DETOUR_FAIL | 2.1641 | 1.7878 | 5.8369 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H2_212_NOMAD_RAW/attempt1 |
| L2 | 212 | NOMAD_RAW | NEAR_GOAL_HOVER | 0.33365 | -2.0101 | 8.3437 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/L2_212_NOMAD_RAW/attempt1 |
| LC | 212 | NOMAD_RAW | BOX_COLLISION | 1.6383 | 0.11089 | 4.031 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/LC_212_NOMAD_RAW/attempt1 |
| SLW | 212 | NOMAD_RAW | WALL_COLLISION | 3.5147 | 1.4853 | 1.7765 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_212_NOMAD_RAW/attempt1 |

## Smoke와 기술 실패

Smoke는 기술검증 전용이며 본 결과에서 제외하고 성능 해석하지 않는다.

| scene | index | method | technical_validation | launcher_wall_s | attempt_count | output |
|---|---|---|---|---|---|---|
| H1 | 95 | ASTAR+EC | PASS | 137.53 | 1 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/smoke/H1_095_ASTAR+EC/attempt1 |
| H1 | 95 | NOMAD_RAW | PASS | 139.67 | 2 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/smoke/H1_095_NOMAD_RAW/attempt2 |
| H1 | 95 | SAFE_RTC | PASS | 181.55 | 1 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/smoke/H1_095_SAFE_RTC/attempt1 |
| H1 | 95 | SAFE_TE | PASS | 195.9 | 1 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/smoke/H1_095_SAFE_TE/attempt1 |

본 결과 기술 실패 없음(아직 미완료인 run을 성공으로 세지 않음).

보존한 smoke 기술 실패:

| scene | index | method | attempt | error | output |
|---|---|---|---|---|---|
| H1 | 95 | NOMAD_RAW | 1 | AssertionError('Executor threshold differs') | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/smoke/H1_095_NOMAD_RAW/attempt1 |

NOMAD_RAW 첫 시도는 depth 없는 원 factory를 통해 이전20°/45° 실행기로 연결되어90° 기술 검사를 통과하지 못했다. 본 실행 전 Phase35의 RGB-only factory 연결만 수정했다. 방법 수치·판정·기존 파일은 변경하지 않았으며 첫 시도를 본 결과에서 제외하고 한 번만 재시도했다.

순차 실행, 기술실패1회 재시도, smoke 같은 오류2회면 STOP_BLOCKED. 매 attempt 전30GB 미만이면 STOP_BLOCKED;6.5시간 만료 시 진행 중 run만 끝내고 PARTIAL. 완료 블록5개마다 중간 보고서를 commit·push하며 매 단계 동일하게 보존한다.

재개: `env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase35.campaign --stage main`

상태: `PYTHONPATH=research /usr/bin/python3 -m nomad_phase35.campaign --status`
