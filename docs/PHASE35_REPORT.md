1. 라벨: **PENDING_INCOMPLETE_EVIDENCE**; BEATS: {'SAFE_TE': None, 'SAFE_RTC': None, 'NOMAD_RAW': None}.
2. 도착(유효 run): OURS 6/10 / ASTAR+EC 7/10 / SAFE_TE 6/10 / SAFE_RTC 7/10 / NOMAD_RAW 3/10.
3. 충돌: OURS 0 / ASTAR+EC 0 / SAFE_TE 3 / SAFE_RTC 1 / NOMAD_RAW 3.
4. OURS−ASTAR+EC 도착시간 짝차이 중앙값: -7.930555555555555s; 완료 50/75.
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
| ASTAR+EC | 10 | 2 | 3 | 5 | 4 | -7.9306 | 1 |
| SAFE_TE | 10 | 4 | 4 | 2 | 2 | 0.090278 | 1 |
| SAFE_RTC | 10 | 2 | 3 | 5 | 4 | -12.722 | 1 |
| NOMAD_RAW | 10 | 3 | 0 | 7 | 3 | -3.5972 | 0.25 |

BEATS 결과: `{'SAFE_TE': None, 'SAFE_RTC': None, 'NOMAD_RAW': None}`; Graph: `None`.

## 방법×장면

| method | scene | n | valid | goal | collision | goal_time_median_s | mean_speed_m_s | stopped_fraction | minimum_clearance_m | omega_saturation_fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| OURS | SLW | 2 | 2 | 1 | 0 | 70.792 | 0.08188 | 0.43746 | 0.064981 | 0.38689 |
| OURS | LC | 2 | 2 | 2 | 0 | 28.021 | 0.188 | 0.14539 | 0.17353 | 0.48177 |
| OURS | L2 | 2 | 2 | 1 | 0 | 54.083 | 0.16749 | 0.15339 | 0.047621 | 0.44838 |
| OURS | H1 | 2 | 2 | 2 | 0 | 30.764 | 0.17772 | 0.13574 | 0.15035 | 0.42963 |
| OURS | H2 | 2 | 2 | 0 | 0 | — | 0.14673 | 0.2321 | 0.08466 | 0.34753 |
| OURS | ALL | 10 | 10 | 6 | 0 | 30.764 | 0.16749 | 0.17118 | 0.10381 | 0.42344 |
| ASTAR+EC | SLW | 2 | 2 | 1 | 0 | 57.778 | 0.098343 | 0.28644 | 0.050283 | 0.42912 |
| ASTAR+EC | LC | 2 | 2 | 2 | 0 | 35.951 | 0.16042 | 0.17505 | 0.092688 | 0.5359 |
| ASTAR+EC | L2 | 2 | 2 | 1 | 0 | 43.917 | 0.18089 | 0.12909 | 0.040185 | 0.54911 |
| ASTAR+EC | H1 | 2 | 2 | 2 | 0 | 51.181 | 0.14666 | 0.20505 | 0.038308 | 0.33506 |
| ASTAR+EC | H2 | 2 | 2 | 1 | 0 | 44.542 | 0.16321 | 0.19864 | 0.046271 | 0.47676 |
| ASTAR+EC | ALL | 10 | 10 | 7 | 0 | 43.917 | 0.15481 | 0.18602 | 0.047637 | 0.49203 |
| SAFE_TE | SLW | 2 | 2 | 1 | 1 | 52.194 | 0.14341 | 0.29973 | 0.011265 | 0.48644 |
| SAFE_TE | LC | 2 | 2 | 2 | 0 | 27.931 | 0.19315 | 0.11125 | 0.23072 | 0.53799 |
| SAFE_TE | L2 | 2 | 2 | 1 | 0 | 73.014 | 0.15165 | 0.093471 | 0.15232 | 0.55959 |
| SAFE_TE | H1 | 2 | 2 | 0 | 2 | — | 0.15722 | 0.15959 | -0.001174 | 0.5377 |
| SAFE_TE | H2 | 2 | 2 | 2 | 0 | 60.799 | 0.17192 | 0.11238 | 0.059935 | 0.53047 |
| SAFE_TE | ALL | 10 | 10 | 6 | 3 | 48.181 | 0.17057 | 0.11491 | 0.04883 | 0.52814 |
| SAFE_RTC | SLW | 2 | 2 | 1 | 1 | 48.819 | 0.12094 | 0.30183 | 3.3159e-05 | 0.49495 |
| SAFE_RTC | LC | 2 | 2 | 1 | 0 | 28.819 | 0.15351 | 0.16167 | 0.10752 | 0.53609 |
| SAFE_RTC | L2 | 2 | 2 | 1 | 0 | 89.056 | 0.14277 | 0.19021 | 0.047297 | 0.6234 |
| SAFE_RTC | H1 | 2 | 2 | 2 | 0 | 41.938 | 0.17071 | 0.13437 | 0.046009 | 0.58458 |
| SAFE_RTC | H2 | 2 | 2 | 2 | 0 | 58.16 | 0.15548 | 0.15659 | 0.025305 | 0.56452 |
| SAFE_RTC | ALL | 10 | 10 | 7 | 1 | 53.958 | 0.14825 | 0.15659 | 0.032358 | 0.54921 |
| NOMAD_RAW | SLW | 2 | 2 | 0 | 2 | — | 0.18095 | 0.26881 | -0.00090172 | 0.47847 |
| NOMAD_RAW | LC | 2 | 2 | 1 | 1 | 33.667 | 0.12187 | 0.22753 | 0.055429 | 0.58578 |
| NOMAD_RAW | L2 | 2 | 2 | 0 | 0 | — | 0.15955 | 0.089506 | 0.14495 | 0.61049 |
| NOMAD_RAW | H1 | 2 | 2 | 2 | 0 | 31.167 | 0.17139 | 0.10979 | 0.069059 | 0.58969 |
| NOMAD_RAW | H2 | 2 | 2 | 0 | 0 | — | 0.15406 | 0.078395 | 0.099343 | 0.64074 |
| NOMAD_RAW | ALL | 10 | 10 | 3 | 3 | 33.667 | 0.16146 | 0.10365 | 0.061896 | 0.61049 |

도착시간은 성공 run만의 중앙값, 속도/정지/여유/포화는 run별 값의 중앙값이다. 최소여유는 참고이며 주 판정에 사용하지 않는다.

## 15개 scene×seed 짝

| scene | index | comparison | baseline | ours_goal | other_goal | ours_collision | other_collision | goal_difference | goal_time_difference_s |
|---|---|---|---|---|---|---|---|---|---|
| SLW | 212 | OURS - ASTAR+EC | ASTAR+EC | True | False | False | False | 1 | — |
| SLW | 212 | OURS - SAFE_TE | SAFE_TE | True | False | False | True | 1 | — |
| SLW | 212 | OURS - SAFE_RTC | SAFE_RTC | True | False | False | True | 1 | — |
| SLW | 212 | OURS - NOMAD_RAW | NOMAD_RAW | True | False | False | True | 1 | — |
| SLW | 213 | OURS - ASTAR+EC | ASTAR+EC | False | True | False | False | -1 | — |
| SLW | 213 | OURS - SAFE_TE | SAFE_TE | False | True | False | False | -1 | — |
| SLW | 213 | OURS - SAFE_RTC | SAFE_RTC | False | True | False | False | -1 | — |
| SLW | 213 | OURS - NOMAD_RAW | NOMAD_RAW | False | False | False | True | 0 | — |
| LC | 212 | OURS - ASTAR+EC | ASTAR+EC | True | True | False | False | 0 | -16 |
| LC | 212 | OURS - SAFE_TE | SAFE_TE | True | True | False | False | 0 | -0.097222 |
| LC | 212 | OURS - SAFE_RTC | SAFE_RTC | True | False | False | False | 1 | — |
| LC | 212 | OURS - NOMAD_RAW | NOMAD_RAW | True | False | False | True | 1 | — |
| LC | 213 | OURS - ASTAR+EC | ASTAR+EC | True | True | False | False | 0 | 0.13889 |
| LC | 213 | OURS - SAFE_TE | SAFE_TE | True | True | False | False | 0 | 0.27778 |
| LC | 213 | OURS - SAFE_RTC | SAFE_RTC | True | True | False | False | 0 | 0.29167 |
| LC | 213 | OURS - NOMAD_RAW | NOMAD_RAW | True | True | False | False | 0 | -4.5556 |
| L2 | 212 | OURS - ASTAR+EC | ASTAR+EC | False | True | False | False | -1 | — |
| L2 | 212 | OURS - SAFE_TE | SAFE_TE | False | True | False | False | -1 | — |
| L2 | 212 | OURS - SAFE_RTC | SAFE_RTC | False | False | False | False | 0 | — |
| L2 | 212 | OURS - NOMAD_RAW | NOMAD_RAW | False | False | False | False | 0 | — |
| L2 | 213 | OURS - ASTAR+EC | ASTAR+EC | True | False | False | False | 1 | — |
| L2 | 213 | OURS - SAFE_TE | SAFE_TE | True | False | False | False | 1 | — |
| L2 | 213 | OURS - SAFE_RTC | SAFE_RTC | True | True | False | False | 0 | -34.972 |
| L2 | 213 | OURS - NOMAD_RAW | NOMAD_RAW | True | False | False | False | 1 | — |
| H1 | 212 | OURS - ASTAR+EC | ASTAR+EC | True | True | False | False | 0 | 0.94444 |
| H1 | 212 | OURS - SAFE_TE | SAFE_TE | True | False | False | True | 1 | — |
| H1 | 212 | OURS - SAFE_RTC | SAFE_RTC | True | True | False | False | 0 | -25.736 |
| H1 | 212 | OURS - NOMAD_RAW | NOMAD_RAW | True | True | False | False | 0 | 2.7917 |
| H1 | 213 | OURS - ASTAR+EC | ASTAR+EC | True | True | False | False | 0 | -41.778 |
| H1 | 213 | OURS - SAFE_TE | SAFE_TE | True | False | False | True | 1 | — |
| H1 | 213 | OURS - SAFE_RTC | SAFE_RTC | True | True | False | False | 0 | 3.3889 |
| H1 | 213 | OURS - NOMAD_RAW | NOMAD_RAW | True | True | False | False | 0 | -3.5972 |
| H2 | 212 | OURS - ASTAR+EC | ASTAR+EC | False | True | False | False | -1 | — |
| H2 | 212 | OURS - SAFE_TE | SAFE_TE | False | True | False | False | -1 | — |
| H2 | 212 | OURS - SAFE_RTC | SAFE_RTC | False | True | False | False | -1 | — |
| H2 | 212 | OURS - NOMAD_RAW | NOMAD_RAW | False | False | False | False | 0 | — |
| H2 | 213 | OURS - ASTAR+EC | ASTAR+EC | False | False | False | False | 0 | — |
| H2 | 213 | OURS - SAFE_TE | SAFE_TE | False | True | False | False | -1 | — |
| H2 | 213 | OURS - SAFE_RTC | SAFE_RTC | False | True | False | False | -1 | — |
| H2 | 213 | OURS - NOMAD_RAW | NOMAD_RAW | False | False | False | False | 0 | — |

## 우회·EC·계산시간

| method | n | detour_triggers | detour_applied | detour_path_total_m | detour_execution_s | compute_n | compute_p50_s | compute_p95_s | ec_by_state | fallback_routes |
|---|---|---|---|---|---|---|---|---|---|---|
| OURS | 10 | 82 | 23 | 32.571 | 39.667 | 113 | 0.33066 | 0.62274 | {'NORMAL': {'checks': 1329, 'rejects': 96, 'reject_fraction': 0.07223476297968397}, 'R2': {'checks': 29, 'rejects': 9, 'reject_fraction': 0.3103448275862069}, 'R3': {'checks': 160, 'rejects': 1, 'reject_fraction': 0.00625}} | {'NEXT_SAFE_FULL': 27, 'R2_TO_R3': 9, 'R3_FAILURE': 1, 'SAFE_SLOW': 5, 'STOP_WAIT': 3} |
| ASTAR+EC | 10 | 67 | 13 | 18.096 | 22.444 | 79 | 0.29218 | 0.60281 | {'NORMAL': {'checks': 1475, 'rejects': 116, 'reject_fraction': 0.07864406779661016}, 'R2': {'checks': 12, 'rejects': 5, 'reject_fraction': 0.4166666666666667}, 'R3': {'checks': 54, 'rejects': 0, 'reject_fraction': 0.0}} | {'SAFE_SLOW': 7, 'NEXT_SAFE_FULL': 27, 'STOP_WAIT': 3, 'R2_TO_R3': 5} |
| SAFE_TE | 10 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |
| SAFE_RTC | 10 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |
| NOMAD_RAW | 10 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |

우회 경로 길이는 실제 설치된 DETOUR polyline 길이 합, 실행시간은 APPLIED→END(종료 시 활성 구간 포함) 합이다. 계산시간은 R2/R3 4-process pool 전체 job 시간이며 inference/EC 시간과 다르다. EC는 상태별 CHECK 수/REJECT 수를 보고한다. 미사용 방법은 해당 없음이며 거절률0으로 해석하지 않는다.

## SAFE_RTC chunk 이어받기 지연·정지

| scene | index | chunk_delay_p50_s | chunk_delay_p95_s | inference_p50_s | inference_p95_s | stopped_fraction | command_state_seconds |
|---|---|---|---|---|---|---|---|
| H1 | 212 | 0.90278 | 1.0139 | 0.076 | 0.093683 | 0.14011 | {'WAYPOINT_TIMEOUT': 3.333333333333332, 'NORMAL': 47.444444444444436, 'ENDPOINT': 0.22222222222222587, 'ALIGN_BRAKE': 1.4305555555555607, 'ALIGN_ROTATE': 3.6666666666666643, 'STOP_WAIT': 1.0} |
| H1 | 213 | 0.90278 | 1.0139 | 0.074328 | 0.1141 | 0.12863 | {'WAYPOINT_TIMEOUT': 3.5555555555555536, 'NORMAL': 22.0, 'ENDPOINT': 0.22222222222222232, 'ALIGN_BRAKE': 0.5555555555555554, 'ALIGN_ROTATE': 0.44444444444444464} |
| H2 | 212 | 0.90278 | 1.0139 | 0.074941 | 0.095857 | 0.16885 | {'WAYPOINT_TIMEOUT': 3.222222222222225, 'NORMAL': 42.06944444444444, 'ENDPOINT': 0.6666666666666687, 'ALIGN_BRAKE': 1.7777777777777786, 'ALIGN_ROTATE': 4.222222222222221, 'STOP_WAIT': 2.0} |
| H2 | 213 | 0.90278 | 1.0139 | 0.078997 | 0.096051 | 0.14432 | {'WAYPOINT_TIMEOUT': 3.666666666666675, 'NORMAL': 50.80555555555556, 'ALIGN_BRAKE': 3.0000000000000036, 'ALIGN_ROTATE': 3.888888888888882, 'STOP_WAIT': 1.0} |
| L2 | 212 | 0.90278 | 1.0139 | 0.074758 | 0.089 | 0.24568 | {'WAYPOINT_TIMEOUT': 3.777777777777775, 'NORMAL': 64.55555555555554, 'ENDPOINT': 1.0000000000000009, 'ALIGN_BRAKE': 2.777777777777784, 'ALIGN_ROTATE': 12.888888888888891, 'STOP_WAIT': 2.0, 'RECOVER_ROTATE': 1.7777777777777786, 'WAIT_FRESH': 0.22222222222222143, 'KEEP_ACTIVE': 1.0} |
| L2 | 213 | 0.90278 | 1.0139 | 0.075599 | 0.087753 | 0.13475 | {'WAYPOINT_TIMEOUT': 3.3333333333333393, 'NORMAL': 73.72222222222223, 'ENDPOINT': 0.11111111111111072, 'ALIGN_BRAKE': 3.6666666666666767, 'ALIGN_ROTATE': 7.2222222222222054, 'STOP_WAIT': 1.0} |
| LC | 212 | 0.90278 | 1.009 | 0.075958 | 0.095381 | 0.13827 | {'WAYPOINT_TIMEOUT': 3.555555555555568, 'NORMAL': 75.0, 'ENDPOINT': 0.4444444444444393, 'ALIGN_BRAKE': 2.5555555555555785, 'ALIGN_ROTATE': 8.444444444444418} |
| LC | 213 | 0.90278 | 1.0139 | 0.074291 | 0.11903 | 0.18506 | {'WAYPOINT_TIMEOUT': 3.2222222222222214, 'NORMAL': 22.15277777777778, 'ALIGN_BRAKE': 0.7777777777777768, 'ALIGN_ROTATE': 2.222222222222223, 'ENDPOINT': 0.44444444444444287} |
| SLW | 212 | 0.90278 | 1.0139 | 0.071874 | 0.1231 | 0.30323 | {'WAYPOINT_TIMEOUT': 3.2222222222222214, 'NORMAL': 13.583333333333336, 'ALIGN_BRAKE': 1.888888888888884, 'ALIGN_ROTATE': 3.111111111111116, 'STOP_WAIT': 1.0, 'KEEP_ACTIVE': 2.0, 'ENDPOINT': 0.11111111111111072} |
| SLW | 213 | 0.93056 | 1.0139 | 0.074981 | 0.10567 | 0.30043 | {'WAYPOINT_TIMEOUT': 3.2222222222222214, 'NORMAL': 31.444444444444443, 'ALIGN_BRAKE': 2.5972222222222303, 'ALIGN_ROTATE': 5.555555555555548, 'STOP_WAIT': 2.0, 'RECOVER_ROTATE': 3.5555555555555554, 'WAIT_FRESH': 0.2222222222222232, 'ENDPOINT': 0.22222222222222143} |

Chunk 지연=application_sim_s−observation_sim_s(D750·추론 포함); received→apply 원자료도 runs.json에 기록했다. 정지는 실제72Hz |v|<0.01 비율, command_state_seconds는9Hz 명령 유지시간 합이다.

## 실패 분해(Phase31-D 그대로)

우선순위: 기술 실패 OTHER(성능 통계 제외); box contact→BOX_COLLISION(InnerCorner 등 구조벽은 WALL); 외곽 overlap/corridor stop→WALL_COLLISION; 목표≤0.6m→NEAR_GOAL_HOVER; 모든 돌발 상자 통과→POST_PASSAGE_TIMEOUT; SLW/LC 마지막10초 목표거리 감소<0.2m→STATIC_NARROW_STUCK; 상자 출현·미통과→DETOUR_FAIL; 미출현 또는 시작 최대변위<0.5m→EARLY_STUCK; 나머지OTHER. WALL_COLLISION 분해에는 margin 정지도 포함되나 주 판정 충돌은 원 evaluator 실제 overlap 값 그대로다.

| scene | index | method | primary_cause | minimum_goal_distance_m | last10_goal_progress_m | maximum_start_displacement_m | structural_contact | output |
|---|---|---|---|---|---|---|---|---|
| H2 | 212 | OURS | NEAR_GOAL_HOVER | 0.37664 | -1.0979 | 8.495 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H2_212_OURS/attempt1 |
| H2 | 213 | OURS | POST_PASSAGE_TIMEOUT | 0.76428 | 1.1406 | 7.5419 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H2_213_OURS/attempt1 |
| L2 | 212 | OURS | NEAR_GOAL_HOVER | 0.30214 | -1.7496 | 8.5615 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/L2_212_OURS/attempt1 |
| SLW | 213 | OURS | STATIC_NARROW_STUCK | 2.6446 | 0 | 2.4505 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_213_OURS/attempt1 |
| H2 | 213 | ASTAR+EC | DETOUR_FAIL | 2.4803 | 1.5203 | 5.5306 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H2_213_ASTAR+EC/attempt1 |
| L2 | 213 | ASTAR+EC | NEAR_GOAL_HOVER | 0.30984 | -1.2828 | 8.5788 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/L2_213_ASTAR+EC/attempt1 |
| SLW | 212 | ASTAR+EC | STATIC_NARROW_STUCK | 1.2363 | -0.42444 | 3.7872 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_212_ASTAR+EC/attempt1 |
| H1 | 212 | SAFE_TE | BOX_COLLISION | 1.5923 | 0.6402 | 3.8621 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H1_212_SAFE_TE/attempt1 |
| H1 | 213 | SAFE_TE | BOX_COLLISION | 0.87095 | 1.764 | 3.8365 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H1_213_SAFE_TE/attempt1 |
| L2 | 213 | SAFE_TE | POST_PASSAGE_TIMEOUT | 3.6786 | 2.0306 | 4.3774 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/L2_213_SAFE_TE/attempt1 |
| SLW | 212 | SAFE_TE | WALL_COLLISION | 3.1725 | 1.826 | 2.0958 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_212_SAFE_TE/attempt1 |
| L2 | 212 | SAFE_RTC | NEAR_GOAL_HOVER | 0.55462 | 0.081748 | 8.6389 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/L2_212_SAFE_RTC/attempt1 |
| LC | 212 | SAFE_RTC | OTHER | 2.2704 | 0.73638 | 3.2885 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/LC_212_SAFE_RTC/attempt1 |
| SLW | 212 | SAFE_RTC | BOX_COLLISION | 2.6978 | 0.72484 | 2.5298 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_212_SAFE_RTC/attempt1 |
| H2 | 212 | NOMAD_RAW | DETOUR_FAIL | 2.1641 | 1.7878 | 5.8369 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H2_212_NOMAD_RAW/attempt1 |
| H2 | 213 | NOMAD_RAW | DETOUR_FAIL | 2.1438 | 0.45807 | 5.8701 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/H2_213_NOMAD_RAW/attempt1 |
| L2 | 212 | NOMAD_RAW | NEAR_GOAL_HOVER | 0.33365 | -2.0101 | 8.3437 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/L2_212_NOMAD_RAW/attempt1 |
| L2 | 213 | NOMAD_RAW | NEAR_GOAL_HOVER | 0.31699 | 0.61322 | 7.8307 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/L2_213_NOMAD_RAW/attempt1 |
| LC | 212 | NOMAD_RAW | BOX_COLLISION | 1.6383 | 0.11089 | 4.031 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/LC_212_NOMAD_RAW/attempt1 |
| SLW | 212 | NOMAD_RAW | WALL_COLLISION | 3.5147 | 1.4853 | 1.7765 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_212_NOMAD_RAW/attempt1 |
| SLW | 213 | NOMAD_RAW | WALL_COLLISION | 3.1548 | 1.8452 | 2.1126 | False | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/main/SLW_213_NOMAD_RAW/attempt1 |

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
