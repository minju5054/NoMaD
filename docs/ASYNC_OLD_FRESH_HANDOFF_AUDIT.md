# Async OLD/FRESH handoff: Graph 필요성 audit

**판정: `NO_QUALIFIED_CANDIDATE`.** 실제 비동기 handoff에서 공간 revision과 stale local-point의 world 위치 차이는 측정됐지만, **안전한 FRESH에 연결하지 못하고 검사한 단순 staging도 불충분한 사례는 0개**다. 현재 성공한 baseline은 Graph가 해결해야 하는 연결 실패에 대한 **negative evidence**다. Graph가 모든 조건에서 불필요하다는 증명이나 성능 비교는 아니다.

## 대상과 판정

기준 `929a9dcf2595b876656729134740df9dcadb83c4`, branch `research/isaac6-async-handoff-audit`. 입력은 저장된 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_wide_wall_01/`뿐이다. 0.5×1.5×1.0 m 두 번째 장애물, 9 cm radius 및 모든 실행 조건을 보존했다. **Fixed-goal adapter**이며 Topomap은 도입하지 않았다. 성공한 baseline의 24.583333 s goal entry, 무충돌·corridor containment 사실은 그대로다.

95 predictions 중 94개가 실제 적용됐다. 최초 ID 0은 OLD 없는 initialization이므로 **실제 handoff는 93개(0→1부터 92→93)**다. ID 94는 수신 후 다음 controller tick 전에 주행이 종료돼 switch=null로 별도 보존했으며 성공 handoff에 포함하지 않았다.

[사전 protocol](ASYNC_HANDOFF_AUDIT_PROTOCOL.md)을 **`dc6c69d`**에 고정한 뒤 분석 코드를 **`1c34d6f`**의 clean 상태에서 실행했다. 기존 `handoff_audit.py`의 correspondence/entry/classify와 모든 threshold를 유지했다. 유효한 spatial correspondence는 **87/93**, 불충분한 6개는 분포에서 제외했다. 분류 가능한 비율 **93.55%**가 기존 negative verdict 기준 90%를 넘는다.

| 분류 | Pair 수 |
|---|---:|
| `ALREADY_CONSISTENT` | **85** |
| `STAGING_SUFFICIENT` | **1** |
| `UNSAFE_FRESH` | **1** |
| `POTENTIAL_RECONCILIATION_CASE` | **0** |
| `INSUFFICIENT_EVIDENCE` | **6** |

최대 3개를 선정할 qualified candidate가 **없으므로 candidate 그림도 생성하지 않았다**. 6개를 임의로 consistent로 간주하지 않았다: 26→27, 27→28은 B-forward station 비단조, 79→80부터 82→83은 짧은 segment로 유효 tangent 비율이 80% 미만이다.

## 주요 측정

Position revision은 동일 waypoint index가 아니라 공통 forward 공간을 자른 뒤 동일 arclength progress에서 비교한다. Heading은 길이 0.02 m 이상의 trajectory segment tangent로만 파생했다. 첫 네 행은 유효 pair 87개, 나머지는 실제 handoff 93개다.

| 측정 | Median | p95 | Max |
|---|---:|---:|---:|
| Equal-progress position RMSE (m) | **0.01356** | **0.04510** | **0.05745** |
| Longitudinal revision RMS (m) | 0.00144 | 0.01290 | 0.02106 |
| Lateral revision RMS (m) | 0.01350 | 0.04343 | 0.05385 |
| Tangent heading revision RMS (°) | **6.62** | **19.78** | **22.38** |
| Observation pose→switch OLD 실행 거리 (m) | **0.02778** | **0.03611** | **0.04444** |
| 같은 구간 실제 robot yaw 변화 절댓값 (°) | **1.15** | **3.84** | **5.09** |
| Capture-start→switch delay, host (ms) | 138.28 | 166.49 | 221.76 |
| B→nearest valid entry 거리 (m) | 0.02947 | 0.04484 | 0.04866 |
| B yaw↔entry tangent 차이 (°) | 1.50 | 6.28 | 16.48 |
| Controller local point의 world 위치−observation-anchored point 거리 (m) | **0.02774** | **0.03711** | **0.04492** |
| 실제 switch 전후 `abs(Δw)` (rad/s) | 0.07888 | 0.26477 | 0.45770 |

Robot motion은 저장된 72 Hz incoming command와 pose intervals를 합한 값이다. 모든 93 window에서 직전 적용 OLD의 유효 command가 전체 이동을 만들었으며, 다른 ID/invalid interval은 0개다. Observation pose는 capture-start 직전 snapshot이고 age median/max는 **0.965/14.992 ms**다. Capture-start 이후 양 끝 host timestamp가 모두 포함되는 OLD 완전 intervals만 세면 거리 median/max는 **0.02500/0.04167 m**다. GPU inference window 내부만 세면 **0.002778/0.005556 m**다. Host clock과 simulation clock을 직접 빼지 않았고 움직임 보간이나 가상 latency를 만들지 않았다.

선택점의 world 위치 차이는 실제 의미 차이다: FRESH path는 observation pose로 고정하고, 원본 PD가 그대로 받은 local point를 B에서 표현한 **한 점**과 비교했다. FRESH path 전체를 switch pose로 re-anchor하거나 command를 변경하지 않았다. 이 offset과 최대 steering jump만으로 Graph 필요성을 판단하지 않는다.

## 연결·prediction·실행 안전성 구분

모든 93 pair에 대해 nearest entry의 단순 연결은 안전했다. Connector 최소 obstacle clearance는 **0.07165 m**, corridor clearance는 **0.78086 m**다. B 회전→entry 직선→tangent 회전은 **실행하지 않은 geometric diagnostic**이며 실제 원본 PD 경로라는 주장은 하지 않는다. 실제 switch 이후 다음 handoff/종료까지의 93개 실행 구간도 모두 안전했고, 최소 obstacle/corridor clearance는 **0.06963/0.79039 m**다.

- **28→29, `UNSAFE_FRESH`:** FRESH의 마지막 native segment 6→7이 첫 장애물과 **−0.00703 m** clearance로 overlap한다. 하지만 native 0→2 prefix는 **0.25139 m**, 실제 다음 handoff까지의 실행은 **0.26790 m**로 안전했다. 이는 8-point prediction tail의 문제이며 안전한 FRESH와 B 사이 연결 실패가 아니다. 이후 29→30은 `ALREADY_CONSISTENT`다.
- **83→84, `STAGING_SUFFICIENT`:** nearest entry는 B에서 **0.001146 m** 떨어져 있고 connector bearing은 B yaw 대비 94.18°지만 tangent 차이는 4.18°다. 짧은 측면 연결의 방향각 때문에 기존 30° consistent 기준을 넘었다. 검사한 entry 12개 모두 안전하고 단순 제자리 회전 staging이 가능하다. Connector/실제 실행 clearance는 **0.43347/0.43390 m**다. 이 label은 실제 controller 변경이 필요했다는 증거가 아니다.

## 두 번째 장애물 구간

미래 주행 결과 대신 기존 규칙의 B.x로 구간을 고정했다: expanded near/far `2.66/3.34 m`, 앞뒤 0.50 m. 접근·통과 **24개 전부 `ALREADY_CONSISTENT`**이며 safe FRESH 연결 문제는 없다.

| 구간 / FRESH IDs | Pair 수 | Position RMSE median/p95/max (m) | Heading RMS median/p95/max (°) |
|---|---:|---|---|
| 접근 52..62 | 11 | 0.02222 / 0.04487 / 0.05108 | 9.12 / 18.82 / 19.53 |
| 통과 63..75 | 13 | 0.01041 / 0.01709 / 0.01729 | 4.66 / 11.68 / 12.18 |
| 이탈 76..85 | 10 (correspondence 유효 6) | 0.00851 / 0.01708 / 0.01840 | 4.97 / 9.80 / 10.76 |

접근·통과에서 변화가 가장 컸던 **53→54**도 RMSE 0.05108 m, heading RMS 19.53°, Δw 0.28219 rad/s였지만 connector **0.37512 m**, 실제 실행 **0.35481 m** clearance로 안전했다. 두 번째 장애물에 대한 FRESH full-path 최소 clearance는 접근 **0.04398 m**, 통과 **0.08224 m**; prefix는 각각 **0.07977/0.08224 m**다. 실제 접근·통과 최소 clearance는 **0.08284 m**다. 이탈 구간은 consistent 5, staging 1, insufficient 4이며 candidate는 0이다.

## 검증·보존 및 다음 단계

기존 synthetic tests 7개와 새 적용-ID/clock-window/selected-point 좌표 검증 3개, 합계 **10 passed (0.08 s)**. 모든 95 raw/derived의 normalization/cumsum/scaling/shape/finite, 원본 PD, observation world anchor, pose 적분(최대 오차 0)과 실제 swept clearance를 재검증했다. 기존 async timing report의 4개 지표를 93 handoff별로 대조해 일치했다. 기준 commit에 저장된 **203개 input hash** 및 실행 source 17개 hash와 일치하고, 사용한 **205개 파일의 분석 전후 hash 불변**이다. 추가 clearance/geometry 2개 hash는 이번 분석 baseline이며 과거 hash라고 주장하지 않았다.

전체 numeric details는 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_handoff_audit_01/`, [작은 summary](../research/results/isaac6_async_handoff_20261016/summary.json), [pair CSV](../research/results/isaac6_async_handoff_20261016/pairs.csv), [검증](../research/results/isaac6_async_handoff_20261016/validation.json)을 보존했다. 새 navigation/inference/latency injection/Graph/영상은 **모두 0회**다.

제한: 서로 다른 diffusion seeds와 observation 변화가 섞여 있으며 대응은 oracle이 아닌 자동 공간 proxy다. Fixed-goal·kinematic·단일 성공 run, 유한 entry/connector family, 6개 correspondence 보류라는 범위가 있다. **현재 데이터로 Graph 도입 필요성이나 우월성은 입증되지 않았다.** 더 큰 OLD 이동에서 문제가 발생하는지 계속 조사하려면 다음 단계로 사전 고정한 controlled latency 실험을 검토하는 것이 타당하다. 이는 후속 제안이며 이번에는 실행하지 않았다.
