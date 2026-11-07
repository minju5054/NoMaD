1. 라벨: **AWAITING_TECHNICAL_FIX**; BEATS: {'SAFE_TE': None, 'SAFE_RTC': None, 'NOMAD_RAW': None}.
2. 도착(유효 run): OURS 0/0 / ASTAR+EC 0/0 / SAFE_TE 0/0 / SAFE_RTC 0/0 / NOMAD_RAW 0/0.
3. 충돌: OURS 0 / ASTAR+EC 0 / SAFE_TE 0 / SAFE_RTC 0 / NOMAD_RAW 0.
4. OURS−ASTAR+EC 도착시간 짝차이 중앙값: 미측정s; 완료 0/75.
5. 멈춘 단계/상태: smoke / AWAITING_TECHNICAL_FIX; 이유: Inspect first smoke error before one retry: AssertionError('Executor threshold differs'). 본 실행은 재개 가능.

# Phase35 주요 baseline 비교

Protocol FROZEN SHA256 `4055fbbc90bc5381a2219236a4ba03fb46c38667c058d94cf782674c6e9fc984`. 실험 시작 예산 기준 UTC epoch 1794071828, 최대6.5시간. oracle은 원 평가기에만 사용한다. 기존 결과/방법 파일을 수정하지 않는다.

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
| ASTAR+EC | 0 | 0 | 0 | 0 | 0 | — | 1 |
| SAFE_TE | 0 | 0 | 0 | 0 | 0 | — | 1 |
| SAFE_RTC | 0 | 0 | 0 | 0 | 0 | — | 1 |
| NOMAD_RAW | 0 | 0 | 0 | 0 | 0 | — | 1 |

BEATS 결과: `{'SAFE_TE': None, 'SAFE_RTC': None, 'NOMAD_RAW': None}`; Graph: `None`.

## 방법×장면

| method | scene | n | valid | goal | collision | goal_time_median_s | mean_speed_m_s | stopped_fraction | minimum_clearance_m | omega_saturation_fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| OURS | SLW | 0 | 0 | 0 | 0 | — | — | — | — | — |
| OURS | LC | 0 | 0 | 0 | 0 | — | — | — | — | — |
| OURS | L2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| OURS | H1 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| OURS | H2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| OURS | ALL | 0 | 0 | 0 | 0 | — | — | — | — | — |
| ASTAR+EC | SLW | 0 | 0 | 0 | 0 | — | — | — | — | — |
| ASTAR+EC | LC | 0 | 0 | 0 | 0 | — | — | — | — | — |
| ASTAR+EC | L2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| ASTAR+EC | H1 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| ASTAR+EC | H2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| ASTAR+EC | ALL | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_TE | SLW | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_TE | LC | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_TE | L2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_TE | H1 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_TE | H2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_TE | ALL | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_RTC | SLW | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_RTC | LC | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_RTC | L2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_RTC | H1 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_RTC | H2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SAFE_RTC | ALL | 0 | 0 | 0 | 0 | — | — | — | — | — |
| NOMAD_RAW | SLW | 0 | 0 | 0 | 0 | — | — | — | — | — |
| NOMAD_RAW | LC | 0 | 0 | 0 | 0 | — | — | — | — | — |
| NOMAD_RAW | L2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| NOMAD_RAW | H1 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| NOMAD_RAW | H2 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| NOMAD_RAW | ALL | 0 | 0 | 0 | 0 | — | — | — | — | — |

도착시간은 성공 run만의 중앙값, 속도/정지/여유/포화는 run별 값의 중앙값이다. 최소여유는 참고이며 주 판정에 사용하지 않는다.

## 15개 scene×seed 짝

자료 없음

## 우회·EC·계산시간

| method | n | detour_triggers | detour_applied | detour_path_total_m | detour_execution_s | compute_n | compute_p50_s | compute_p95_s | ec_by_state | fallback_routes |
|---|---|---|---|---|---|---|---|---|---|---|
| OURS | 0 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |
| ASTAR+EC | 0 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |
| SAFE_TE | 0 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |
| SAFE_RTC | 0 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |
| NOMAD_RAW | 0 | 0 | 0 | 0 | 0 | 0 | — | — | {'NORMAL': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R2': {'checks': 0, 'rejects': 0, 'reject_fraction': None}, 'R3': {'checks': 0, 'rejects': 0, 'reject_fraction': None}} | {} |

우회 경로 길이는 실제 설치된 DETOUR polyline 길이 합, 실행시간은 APPLIED→END(종료 시 활성 구간 포함) 합이다. 계산시간은 R2/R3 4-process pool 전체 job 시간이며 inference/EC 시간과 다르다. EC는 상태별 CHECK 수/REJECT 수를 보고한다. 미사용 방법은 해당 없음이며 거절률0으로 해석하지 않는다.

## SAFE_RTC chunk 이어받기 지연·정지

자료 없음

Chunk 지연=application_sim_s−observation_sim_s(D750·추론 포함); received→apply 원자료도 runs.json에 기록했다. 정지는 실제72Hz |v|<0.01 비율, command_state_seconds는9Hz 명령 유지시간 합이다.

## 실패 분해(Phase31-D 그대로)

우선순위: 기술 실패 OTHER(성능 통계 제외); box contact→BOX_COLLISION(InnerCorner 등 구조벽은 WALL); 외곽 overlap/corridor stop→WALL_COLLISION; 목표≤0.6m→NEAR_GOAL_HOVER; 모든 돌발 상자 통과→POST_PASSAGE_TIMEOUT; SLW/LC 마지막10초 목표거리 감소<0.2m→STATIC_NARROW_STUCK; 상자 출현·미통과→DETOUR_FAIL; 미출현 또는 시작 최대변위<0.5m→EARLY_STUCK; 나머지OTHER. WALL_COLLISION 분해에는 margin 정지도 포함되나 주 판정 충돌은 원 evaluator 실제 overlap 값 그대로다.

자료 없음

## Smoke와 기술 실패

Smoke는 기술검증 전용이며 본 결과에서 제외하고 성능 해석하지 않는다.

| scene | index | method | technical_validation | launcher_wall_s | attempt_count | output |
|---|---|---|---|---|---|---|
| H1 | 95 | ASTAR+EC | PASS | 137.53 | 1 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/smoke/H1_095_ASTAR+EC/attempt1 |
| H1 | 95 | SAFE_RTC | PASS | 181.55 | 1 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/smoke/H1_095_SAFE_RTC/attempt1 |
| H1 | 95 | SAFE_TE | PASS | 195.9 | 1 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase35_01/smoke/H1_095_SAFE_TE/attempt1 |

본 결과 기술 실패 없음(아직 미완료인 run을 성공으로 세지 않음).

순차 실행, 기술실패1회 재시도, smoke 같은 오류2회면 STOP_BLOCKED. 매 attempt 전30GB 미만이면 STOP_BLOCKED;6.5시간 만료 시 진행 중 run만 끝내고 PARTIAL. 완료 블록5개마다 중간 보고서를 commit·push하며 매 단계 동일하게 보존한다.

재개: `env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase35.campaign --stage main`

상태: `PYTHONPATH=research /usr/bin/python3 -m nomad_phase35.campaign --status`
