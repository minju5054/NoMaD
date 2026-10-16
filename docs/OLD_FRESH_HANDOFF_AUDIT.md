# Successive OLD/FRESH geometric handoff audit

**판정: `NO_QUALIFIED_CANDIDATE`.** 주 분석 97 pair 중 94개는 고정된 기준에서 `ALREADY_CONSISTENT`, 3개는 correspondence 근거 부족이다. 공간 revision과 controller command 변화는 관측됐지만, **안전한 FRESH로 연결하는 데 장애물 때문에 reconciliation이 필요한 pair는 발견하지 못했다.** Graph의 필요성·우월성이나 비동기 reconciliation 필요성을 입증한 결과가 아니다.

## 데이터·사전 규칙·무결성

- 기준 branch/commit: `research/isaac6-two-obstacles`, `49f865cb4148fedef6c15be1e9739d5e53ba151b`. 실제 navigation 실행 commit은 `bdd0970c1f9ab988f68dc83fbb04fd5b2967ee10`이다.
- 입력: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/two_obstacles_01/`. 새 navigation/inference/sampling/Graph/영상 생성 **각 0회**. 원본 model/controller/coordinate/clearance 함수는 변경하지 않았다.
- [사전 protocol](HANDOFF_AUDIT_PROTOCOL.md)과 [수치 설정](../research/nomad_isaac/handoff_protocol.json)을 metric 계산 전에 `0f41d5e`에 commit했다. 분석 구현·synthetic tests commit `6de5bc6`; 결과를 본 뒤 기준 변경·parameter sweep·분석 재시도는 0회다.
- 총 237 predictions의 raw/derived 파일 쌍과 로그 ID가 모두 존재한다. 주 분석에 필요한 ID 0..97의 98 raw/derived 쌍, events/controller/pose/planning/scenario/geometry/provenance/worker metadata를 검증했다. 205개 입력 hash가 분석 전후 및 최종 검토 후 같았다.
- 기존에 기록된 pose/scenario SHA-256 및 실행 source SHA-256 10개가 일치했다. 개별 NPZ/events/controller/planning의 **실행 당시 file hash는 없으므로**, 이번 hash는 새 baseline이다. 과거 생성 시점의 개별 파일 무결성을 독립적으로 증명하지는 못한다. 대신 raw→cumulative→metric→selected point, planning world 좌표/clearance와 controller의 내부 일관성은 모두 일치했다. Checkpoint는 저장된 provenance만 확인하고 재로드하지 않았다.

## 분석 범위와 방법

실제 pose에서 goal 거리의 최초 최소값은 **t=25.25 s, 0.6630546 m**다. 전체 236 successive pair 중 두 observation 및 FRESH application이 이 시점 이하인 **97 pair(0→1부터 96→97)**를 분석했다. 나머지 139 pair는 후보 선정에서 제외했다. ID 98은 t=25.25에 관측됐지만 t=25.333333에 적용돼 제외된다. 첫 prediction은 history가 채워진 t=0.75에 나온다.

각 curve는 자기 observation pose로 world 변환했다. B는 FRESH가 처음 적용된 controller tick의 실제 기록 pose다. FRESH를 B로 옮기지 않았다. B yaw 방향으로 단조 증가하는 공통 forward interval(최소 0.10 m)에서 spatial station을 대응시킨 뒤, 공통 구간 시작부터 동일 arclength progress로 비교했다. Longitudinal/lateral은 OLD tangent와 left-normal 기준이다. 같은 index가 같은 물리적 지점이라는 가정, 미래 실행을 이용한 oracle correspondence, waypoint별 시간 추정은 없다.

Entry는 FRESH native point 0→1→2 구간의 고정 projection/sampling 규칙으로 정했다. 단순 연결은 원형 footprint의 **제자리 회전→직선→제자리 회전**이며 실제로 실행하지 않은 geometric diagnostic이다. 장애물 margin 0.02 m와 corridor containment를 요구한다. Native FRESH 0..7 자체의 안전성과 B→entry 연결 안전성을 분리했다. Heading은 실제 길이 0.02 m 이상 segment에서만 유도했다. 98개 prediction의 686 segments 중 14개 짧은 segment는 [invalid ledger](../research/results/handoff_audit_20261016/invalid_headings.json)에 angle=null로 남겼다.

## Pair 분류

| 분류 | Pair 수 |
|---|---:|
| `ALREADY_CONSISTENT` | 94 |
| `STAGING_SUFFICIENT` | 0 |
| `POTENTIAL_RECONCILIATION_CASE` | 0 |
| `UNSAFE_FRESH` | 0 |
| `INSUFFICIENT_EVIDENCE` | 3 |

유효 correspondence/분류 가능 비율은 **94/97=96.91%**다. 사전 규칙의 negative-verdict 조건 90%를 만족한다. 이 90%는 통계적 신뢰도가 아니다. 97개 모두 FRESH 자체와 nearest entry connector는 안전했으나, 아래 3개는 전체 경로의 진행 방향이 뒤로 꺾여 자동 대응을 확정하지 않았다. 이들을 PASS로 포함하지 않았다.

| OLD→FRESH | B 시각(s) | 제외 근거 | B→entry 거리 / clearance |
|---|---:|---|---|
| 94→95 | 24.555556 | FRESH 마지막 segment의 forward projection −0.00545 m | 0.04139 / 1.02173 m |
| 95→96 | 24.777778 | OLD와 FRESH tail이 비단조 | 0.05199 / 1.06485 m |
| 96→97 | 25.000000 | OLD와 FRESH tail이 비단조 | 0.04185 / 1.10849 m |

가장 유력한 handoff 후보는 **없음**이다. 후보용 그림도 만들지 않았다. Tail의 짧거나 역방향인 segment를 다른 correspondence로 재선정해 유리한 결론을 만들지 않았다.

## 주요 분포

아래 spatial/heading revision은 correspondence 유효 94 pair의 **pair별 RMS** 분포다. B/entry 및 command 값은 97 pair다. 각 경로의 spatial resampling 간격은 최대 0.01 m이고, heading이 invalid인 sample은 heading 및 tangent 성분 통계에서 제외했다. 누적된 waypoint에 native yaw/time을 추가한 것이 아니다.

| 측정 | Median | p95 | Max |
|---|---:|---:|---:|
| 공통 forward overlap (m) | 0.31291 | 0.39698 | 0.40556 |
| Equal-progress spatial RMSE (m) | 0.01318 | 0.03543 | 0.05895 |
| Longitudinal RMS (m) | 0.00187 | 0.00992 | 0.02624 |
| Lateral RMS (m) | 0.01287 | 0.03482 | 0.05279 |
| Tangent heading RMS (deg) | 7.09 | 19.19 | 31.07 |
| Same-forward-station lateral RMS (m) | 0.01369 | 0.04116 | 0.09276 |
| B→entry 거리 (m) | 0.05089 | 0.06457 | 0.06656 |
| B yaw↔entry tangent (deg) | 2.12 | 7.18 | 11.12 |
| 선택 local waypoint vector 변화 norm (m) | 0.01242 | 0.04600 | 0.05757 |
| 관측 pose로 변환한 선택 world point 변화 norm (m) | 0.05209 | 0.07505 | 0.09644 |
| 원본 controller Δw 절댓값 (rad/s) | 0.10510 | 0.34923 | 0.61258 |

모든 v는 0.2 m/s로 clipping돼 |Δv|=0이다. 선택 waypoint 변화는 실제 명령 입력의 변화이며 **물리적으로 대응하는 landmark의 오차가 아니다**. 97개 모두 nearest entry가 native point 0이었다. 최대 B↔connector angle 13.50°, connector↔tangent 18.79°이며, 이미 고정한 0.10 m/30° 이내다. FRESH 전체 native polyline 최소 clearance **0.14585 m**, B→entry connector 최소 **0.22144 m**, 적용 후 다음 switch/분석 종료까지 실제 command arc 최소 하한 **0.22121 m**다. 모두 주 분석 구간의 값이며 60초 전체/복귀 구간 minimum과 다르다.

## 두 장애물 구간

B.x가 expanded AABB(반경 포함)의 앞 0.50 m부터 뒤 0.50 m까지인 고정 window다. X를 가로지르는 동안의 `pass`는 geometric 구간명이며 성공 판정에 이용한 미래 label이 아니다. 장애물 1 departure와 장애물 2 approach는 일부 겹친다. 각 구간의 모든 pair가 `ALREADY_CONSISTENT`다.

| 구간 | Pair 수 / B 시각(s) | Spatial RMSE median / p95(m) | Heading RMS median / p95(deg) | 해당 장애물 FRESH 최소 clearance(m) |
|---|---|---|---|---:|
| 장애물 1 접근 | 11 / 4.778–7.333 | 0.01546 / 0.03952 | 5.57 / 12.88 | 0.14585 |
| 장애물 1 통과 | 15 / 7.556–11.000 | 0.00749 / 0.01585 | 2.89 / 15.99 | 0.23513 |
| 장애물 1 이탈 | 10 / 11.333–13.556 | 0.00857 / 0.02470 | 5.85 / 11.06 | 0.58280 |
| 장애물 2 접근 | 10 / 12.778–15.000 | 0.00679 / 0.02372 | 4.58 / 8.95 | 0.31715 |
| 장애물 2 통과 | 16 / 15.333–19.000 | 0.01456 / 0.03174 | 7.79 / 19.15 | 0.20905 |
| 장애물 2 이탈 | 11 / 19.333–21.778 | 0.01179 / 0.03347 | 9.27 / 20.04 | 0.30031 |

가장 큰 spatial RMSE는 **12→13(t=4.0 s), 0.05895 m**였지만 entry 거리 0.06504 m, yaw 차이 2.13°, connector clearance 0.56070 m였다. 큰 revision 자체가 연결 문제는 아니었다. 장애물 2 통과 중 **60→61(t=16.0 s)**에서는 w가 +0.35277→−0.25981 rad/s로 바뀌었다. 그러나 entry yaw 차이 3.05°, connector clearance 0.36493 m, 실제 다음 switch까지 clearance 하한 0.36421 m로 안전했다. Command 불연속이 곧 collision이나 Graph 필요성이라는 증거는 없다.

## Timing 및 controller 해석

Inference의 simulation time 경과는 **0 s**다. Wall-clock inference median은 29.3859 ms(초기 cold 호출 포함 98개), 첫 호출은 263.2866 ms였다. OLD가 그 wall time 동안 더 움직였다고 가정하지 않았다.

수신 이후 다음 9 Hz controller tick까지 실제 지연은 최대 **0.083333 s**, 실제 translation 최대 **0.0166667 m**, yaw 변화 최대 **1.90986°**다. 이 이동은 pose 기록과 이전 command 적분으로 일치하며, inference latency로 생긴 이동이 아니다. 원본 PD는 observation-relative XY 값을 다음 tick에도 그대로 사용한다. 이를 B frame에서 표현한 가상 world point와 observation-anchored selected point의 차이는 median 0.00588 m, 최대 0.01718 m다. 이는 adapter의 tick/좌표 의미를 드러내는 diagnostic이며, audit에서는 FRESH를 재정렬하지 않았다.

저장 controller refresh와 원본 AST controller 계산, 실제 pose 재적분을 확인했다(최대 차이 1.39e−15). 따라서 관측된 command 변화와 geometry revision은 별도로 보고한다. 목표 실패를 handoff geometry 탓으로 돌릴 근거는 이번 분석에서 얻지 못했다.

## 결과 파일·재현·한계

[Summary JSON](../research/results/handoff_audit_20261016/summary.json) · [전체 pair CSV](../research/results/handoff_audit_20261016/pairs.csv) · [무결성/수치 검증](../research/results/handoff_audit_20261016/validation.json) · [최종 검토](../research/results/handoff_audit_20261016/review.json) · [입력 hash](../research/results/handoff_audit_20261016/input_hashes.json). CSV에서 분석 제외 row의 metric은 빈 값이다. 전체 numeric details는 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/handoff_audit_01/pair_details.json`에 보존했다. Synthetic audit checks **7 passed**, 새 GPU/model 검사는 실행하지 않았다.

기존 `.venv`에서 offline 재현 가능하다. 아래 output은 기존 경로와 다른, 아직 존재하지 않는 경로여야 하며 도구는 덮어쓰기를 거부한다.

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=research /home/gpuadmin/Workspace/NoMaD/.venv/bin/python -m nomad_isaac.handoff_audit --run /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/two_obstacles_01 --output /tmp/nomad-handoff-audit-new
```

Prediction마다 initial/DDPM seed가 달라 observation 변화와 sampling stochasticity의 기여를 분리할 수 없다. 고정된 local goal adapter, 짧은 predicted horizon, 단일 synchronous 주행의 결과다. 비단조 tail 3 pair에는 유효한 자동 correspondence가 없고, 전체 경로의 연속성/시간 일관성/동역학까지 입증하지 않았다. Entry family 밖의 연결을 탐색하거나 최적화하지도 않았다. 이번 데이터는 **spatial revision의 존재**를 보여주지만, **Graph로 해결해야 하는 qualified handoff 문제**를 입증하지 않는다.
