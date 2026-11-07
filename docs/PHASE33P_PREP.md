# Phase33-P 준비: G18X + EC

**OFFLINE_FAIL** — 실제 주행/Isaac/NoMaD 추론 실행0. 게이트는247개 전체로 계산했다. 원래300개 요청은 사전 답변에 따라 NORMAL200 + R2전체7 + R3전체40의 고유 사건247개로 고정했다.

Protocol SHA256: `ff9c96e1abc40902f0ff422073c649a0afd53777b7e74376c9e80db38c00a745` (`FROZEN_OFFLINE`). 입력 cohort SHA256: `21ae3635c287a9e53aedf5272538a48d53f69d5f3b4b9eadd1f6fd6557dab24e`.

## 고정한 변경

| 항목 | Phase32 G18+EC | G18X |
| --- | --- | --- |
| NORMAL / R2 / R3 곡률 hard 상한 | 각각 기존 상한 | 모두2.0 m⁻¹ |
| SDF hard 기준 | 기존 .025m 및 기존 R2/R3 시작 완화 | 기존 기준 + e(κ) |
| e(κ) | 없음 | R−√(R²−.25²), R=1/abs(κ), κ=0이면0 |
| 검사점 곡률 | — | 해당 선분 양 끝 Menger 곡률의 큰 절댓값. 경로 양 끝은 가까운 내부 곡률 |
| 시작 .30m | 기존 완화 | 같은 완화 기준에 e 추가 |
| soft 여유 / 목적함수 / solver / 초기화 | 동결 | 그대로 재사용 |
| EC·결정 계층·지도·필터·C0-NA·평가기 | 동결 | 변경 없음 |

기존 h/√2 + 선분 길이/16 보수적 여유와 exact certificate 알고리즘/허용오차도 유지한다. 기존 NORMAL의 이전 ω/v 초기화 검사는 새 hard 상한2에 맞춘다. e의 Jacobian은 Menger 해석적 미분을 재사용한다. 비허용 반복점 abs(κ)>2에서는 경계의 접선 연장으로 유한값을 제공한다. 허용 해 영역에서는 주어진 수식 그대로다. abs/max의 동점은 왼쪽, κ=0은0 subgradient를 사용한다. 가중치·상수 튜닝은 없다.

## 저장 정책 v2와 Phase32 변환

새 snapshot/repair input은 `savez_compressed`로 values를 저장하지 않는다. occupied·observed·origin·h·radius·기존 tick 배열과 트리거에 필수인 component ID/birth metadata를 보존한다. 복원은 STORAGE_RETROFIT 로더를 사용한다. 빈 지도의 원래 상수와 dtype/order, 원래 metadata 문자열은 저장 metadata에만 보존해 반올림 오차 없이 복원한다. 라이브 지도 update/EDT 계산은 변경하지 않는다. 기존 R3의 일시적 derived cache 전송은 동결 구현을 유지하며 오프라인 cache는 사례별 계산 후 삭제한다.

Phase32 변환: 5,140개 검사, 5,140개 변환, 건너뜀 0개; **47.071GB 절감**. 백업 생성0. 모든 배열을 임시 파일 복원 결과와 비트 비교한 후 원자 교체했다. 원래/새 SHA와 배열 digest는 [storage manifest](../research/results/phase33p/storage/roots/phase32_01/manifest.jsonl)에 있다. 기존 Phase32 코드·결과 문서는 수정하지 않았다.

## 표본·평가 정의

- seed20261108, NORMAL은 전체1,419개 중200개를 비복원 추출. R2전체7, R3전체40. 고유 사건247개이며 일부 사건은 같은 원래 Graph job의 다른 설치 시점이다. 원래 입력은 모두 저장 SUBMIT/transport에서 확보했다. NORMAL previous_xy는 이전의 실제 적용 Graph RESULT 순서로 복원했다.
- **R2 n=7**은 기술적·서술적 자료이며 독립적인 신뢰성 결론을 내리기에 작다. 상태별 표는 참고이고 게이트는247개 전체만 사용한다.
- 기준은 EC로 선별된 설치 경로가 아니라 **각 알고리즘이 같은 입력에서 내는 수치 해**다. NORMAL은 단일 해, R2/R3는 전체 후보 job이 기존 규칙으로 EC 전에 선택한 해를 검사한다. 실패/해 없음은 EC 불통과다.
- (a)는 기존 accepted/feasible 정의(optimizer 성공 + hard 제약 + certificate)를 만족해 선택 가능한 해의 비율이다. (b)는 이 해가 있을 때의 EC PASS, (c)는 전체247개 대비 solve 성공 AND EC PASS다. 게이트 비교는(c)다.
- EC에는 양쪽 모두 같은 저장 설치 시점의 CHECK pose·실제(v,ω)·depth snapshot·속도 상한을 쓴다. 실제 PATH_APPLIED 경로는 참고 열로 별도 재검사했다. 이는 고정 저장 입력에 대한 반사실이며 새 계산시간에 따른 폐루프 상태 변화·미래 FRESH·supersession을 재현하지 않는다.
- NORMAL 계산시간은 CPU7의 constructor+solve+certificate. R2(8 sample)/R3(7 초기값)는 기존4-process pool 전체 job 시간이며 SDF load/cache/I/O를 포함한다. 프로세스 시작·오프라인 cache 삭제·후속 EC 시간은 제외한다. baseline-first/X-first를 사건마다 교대하고 각 방법을1회씩 계산했다.

## 오프라인 결과

| 대상 | 방법 | n | (a) solve 성공 | (b) 해 존재 시 EC PASS | (c) 전체 solve+EC | 계산 p50/p95 (s) | 실제 설치 경로 EC(참고) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | G18 | 247 | 218/247 (88.3%) | 99.5% | 217/247 (87.9%) | 0.079627 / 0.330183 | 247/247 |
| ALL | G18X | 247 | 139/247 (56.3%) | 99.3% | 138/247 (55.9%) | 0.095453 / 0.433632 | 247/247 |
| NORMAL | G18 | 200 | 171/200 (85.5%) | 99.4% | 170/200 (85.0%) | 0.078099 / 0.112059 | 200/200 |
| NORMAL | G18X | 200 | 99/200 (49.5%) | 99.0% | 98/200 (49.0%) | 0.084025 / 0.173939 | 200/200 |
| R2 | G18 | 7 | 7/7 (100.0%) | 100.0% | 7/7 (100.0%) | 0.143888 / 0.190859 | 7/7 |
| R2 | G18X | 7 | 4/7 (57.1%) | 100.0% | 4/7 (57.1%) | 0.158338 / 0.292346 | 7/7 |
| R3 | G18 | 40 | 40/40 (100.0%) | 100.0% | 40/40 (100.0%) | 0.295249 / 0.409608 | 40/40 |
| R3 | G18X | 40 | 36/40 (90.0%) | 100.0% | 36/40 (90.0%) | 0.366622 / 0.535369 | 40/40 |

| 게이트 조건 | 충족 |
| --- | --- |
| solve_success_at_least_80_percent | False |
| compute_p95_at_most_150ms | False |
| overall_solve_and_ec_strictly_better | False |

기준: solve 성공≥80%, 계산 p95≤0.15s, (c)가 G18보다 엄격히 큼. 판정: **OFFLINE_FAIL**.

## 실패 사유

아래 R2/R3 수는 job 내부의 sample/초기값별 실패 수이며, 위 사건 분모와 다르다.

| variant | state | reason | count |
| --- | --- | --- | --- |
| G18X | NORMAL | INITIALIZATION_OR_SDF_REJECTED | 90 |
| G18 | NORMAL | INITIALIZATION_OR_SDF_REJECTED | 19 |
| G18 | NORMAL | NONCONVERGED | 10 |
| G18X | NORMAL | NONCONVERGED | 11 |
| G18 | R2 | NONCONVERGED | 13 |
| G18X | R2 | NONCONVERGED | 33 |
| G18X | R2 | SHORT_REMAINING | 7 |
| G18 | R2 | SHORT_REMAINING | 7 |
| G18X | R3 | NONCONVERGED | 137 |
| G18 | R3 | NONCONVERGED | 113 |
| G18 | R3 | INSUFFICIENT_PROGRESS | 4 |

## 실행 준비 상태

게이트 미충족이므로 사용자 지시에 따라 **실행 준비를 중단**한다. 본 campaign/20-run launcher/dry-run/nohup 명령을 생성하거나 실행하지 않았다. 조건부20개 블록 순열·판정은 protocol에 명시돼 있지만 실행 승인은 없다. 실패한 조건: solve_success_at_least_80_percent, compute_p95_at_most_150ms, overall_solve_and_ec_strictly_better.

결과 원자료: [offline.csv](../research/results/phase33p/offline.csv), [summary.csv](../research/results/phase33p/summary.csv), [decision.json](../research/results/phase33p/decision.json).

## 검증 및 주요 원인

단위 테스트30개 통과. 세 Graph의 해석적 Jacobian, 변경하지 않은 목적함수·초기값·bounds, 시작 완화+e, storage v1/v2 모든 배열 비트 일치, 프로세스 오류 중단을 확인했다. 동결 source와 평가 입력 hash는 평가 후에도 일치한다. 실제 주행0.

| G18X NORMAL 초기화 거부 사유 | 건수 |
| --- | --- |
| ValueError('Previous curvature exceeds Phase33 hard limit 2 m^-1') | 71 |
| ValueError('Previous speed is zero: boundary curvature undefined') | 19 |

기존 이전 곡률 검사도 새 hard 상한2를 사용하므로 이전 ω/v가2를 넘는71건이 이 초기화 검사에서 거부됐다. 이 검사를 우회하거나 상수를 조정하지 않았다. G18X의 R2는7개 중4개, R3는40개 중36개에서 선택 가능한 해가 나왔다. 기존 전체 pool 시간 정의에 따른 G18 p95도0.330초이며 G18X는0.434초다. 조건부 EC 통과율이 높은 것과 전체 사건에서 쓸 수 있는 해가 많은 것은 구분해야 한다.

재생성: `PYTHONPATH=research /usr/bin/python3 -m nomad_phase33p.finalize` (오프라인 결과만 사용, 주행 없음).
