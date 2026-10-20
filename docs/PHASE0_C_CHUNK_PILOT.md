# Phase 0-C — Pure Pursuit chunk execution PILOT

기준 `ab466f9`, 같은 `research/phase0-infrastructure`에서 단일 S0 navigation을 수행했다. **PILOT: SAFE_GOAL_SUCCESS**, 실제 PP chunk 추종 및 후속 RGB→NoMaD feedback 검증 PASS. 과학적 성능 실험이나 영구 주 실행기 교체 결정이 아니다.

## 실행 전 고정

- 기존 2초/14-node Topomap, S0, seed101+2×request ID, 4/9/72Hz, 추가 지연0, 기존 수신 후1초 timeout.
- Phase0-B `PurePursuit` 코드와 설정 그대로: lookahead .25m, v .2m/s, w ±.4rad/s clipping, endpoint1cm 정지. 결과에 따른 tuning/재시도 없음.
- 각 sample0의 8점만 observation pose로 world 변환한다. Origin 추가, 이전 chunk 연결, switch reanchor, 미래 연장, native yaw/timestamp 생성 없음. 새 FRESH switch에서만 progress 초기화; 동일 chunk의 progress는 비감소한다.
- 중복점은 기존 follower의 인접 중복 제거만 적용한다. 유효 segment가 없으면 해당 chunk 동안 정지한다. 짧은 유효 chunk는 마지막 점으로 target을 clamp한다.
- `--pure-pursuit`는 고정 S0+Topomap의 비동기/추가 지연0에서만 허용한다. 기존 worker/Topomap/PD/follower/geometry 코드는 보존한다.
- 원래 timing core는 유효성·ID·switch를 관리한다. 계산된 index2 PD는 참고 로그만 남기고 적분 명령을 PP로 교체한다. `controller/events`의 `v_m_s,w_rad_s`는 **실행되지 않은 원본 PD 참고값**이고 `applied_v_m_s,applied_w_rad_s` 및 72Hz trace가 **실제 PP 명령**이다.
- 경로 tangent 진단은 동일 B에서 OLD/FRESH 각각의 nearest projection에 해당하는 outgoing segment(끝에서는 incoming)를 사용한다. 20mm 미만은 invalid. 이는 물리적 correspondence나 로봇 yaw 변화가 아니다. 제어에는 사용하지 않는다.
- Geometry는 이미 실행된 구간 평가 및 기존 collision/corridor 종료에만 사용한다. 2cm 위반은 시간 누적하며 명령을 바꾸지 않는다. 새로운 safety/recovery/planner 없음.

고정 설정: `research/nomad_phase0/chunk_pilot_protocol.json`. 사전 최소11 tests PASS. 기존 baseline·14node map·checkpoint·공식 코드·Phase0-B 등343파일 hash를 `artifacts/isaac6/phase0c_preflight_01.json`에 저장했다. Topomap RGB/pose/source hash 검증 PASS 후 코드·protocol을 `3f2fac5`에 commit하고 clean 상태에서 실행했다.

출력은 새 `artifacts/isaac6/phase0c_pure_pursuit_01/`에 보존했다. 동일 seed여도 다른 실제 경로의 RGB와 prediction이 달라지므로 저장된 `topomap_static_2s_01`과는 비paired 참고 비교다.

이번 PILOT에서 후진 recovery는 비활성, 안전 정보는 oracle geometry의 사후 평가, upstream은 NoMaD navigation policy로 고정한다. 영구 주 실행기 선택과 전체 연구 정책을 이번 단일 실행으로 결정하지 않는다.

## 실제 결과

2026-10-20, navigation 1회, 재시도/parameter 변경0회. 기존 RTX5060Ti, torch2.7.0+cu128, diffusers0.11.1, Isaac6.0.1-rc.7 사용. 정적 장면에서 실제 RGB를 입력해 GPU NoMaD가 생성한93개 FRESH를 모두 switch했다. 실제 PP 명령218회, pose1742개. 새 pose의 RGB가 후속 inference에 포함된92개 사례를 검증했다(첫 사례 FRESH0 실행 후24.998mm 이동→RGB5→FRESH1).

| 지표 | PP PILOT | 저장된 original PD 참고 |
|---|---:|---:|
| 판정 | SAFE_GOAL_SUCCESS | SAFE_GOAL_SUCCESS |
| Goal entry / simulation 종료 | 24.180556s | 25.305556s |
| 최종 goal 거리 | .299838m | .297394m |
| 이동 거리 | 4.613887m | 4.776191m |
| 초기 명령 대기 정지 | 1.111111s | 1.111111s |
| 장애물1 최소 swept clearance | .123676m | .279149m |
| 장애물2 최소 swept clearance | .072557m | .074423m |
| 2cm 위반 interval 누적 시간 | 0s | 0s |
| Geometric overlap / corridor 침범 | 없음 / 없음 | 없음 / 없음 |
| Warm inference median / p95 | 35.602 / 43.999ms | 35.182 / 46.586ms |
| Observation→switch median / p95 | 138.163 / 177.426ms | 138.242 / 166.411ms |
| Receive / switch | 93 / 93 | 98 / 97 |

첫 장애물은11.027778s에 +Y(왼쪽), 두 번째는19.777778s에 −Y(오른쪽)로 통과했다. Corridor clearance 하한 .816244m. 안전 정보로 PP 명령을 조절한 적은 없다. 더 빠른 도착이나 경로 차이를 follower의 우월성 또는 paired 인과 효과로 해석하지 않는다.

## Chunk 및 전환 진단

- Native8점의7segment 길이 min/median/p95/max: **.136397 / .382659 / .446983 / .456262m**. .25m 미만8/93개(8.60%, ID5·76·77·78·82·86·87·88). 이번 run의 switch projection은 모두 경로 시작점이어서 당시 remaining length도 전체 길이와 같았다.
- Endpoint clamp: switch8/93회, 유효 path 제어20/208tick(**9.62%**). 퇴화 chunk, endpoint 정지, timeout 정지는 모두0회. 초기 missing10tick만 정지했다. Natural timeout은 `NOT_EXERCISED`; 정확한1초 경계는 synthetic test로 검증했다.
- OLD/FRESH tangent92pair 모두20mm 기준을 통과했다. 절대 heading 변화 median/p95/max **2.588° / 7.210° / 12.013°**. 이는 같은 B에서 각각 projection한 path tangent의 변화이며 로봇 yaw나 native yaw가 아니다.
- 실제 switch Δv는 모두0. |Δw| median/p95/max **.109232 / .435684 / .726350rad/s**. 각속도 부호 전환27회. 최대는89→90(23.666667s)의 **+.326350→−.4rad/s**, 당시 tangent 차이는+.734°였다. Tangent 변화와 PP target에 따른 제어 변화는 서로 다른 지표다. 부호 전환만으로 잘못된 회피 방향이라고 판정하지 않는다.
- Strict clipping: v0/218, w19/218(**8.72%**); 유효 path tick만 보면 w19/208(**9.13%**). v=.2 상한 점유95.41%는 clipping과 구분한다.

72Hz real-time factor .999996079, pacing 절대오차 p95/max .151/1.271ms, inference clock mapping p95 .051ms. 기존 async 검증 PASS. Busy skip1, missed capture0, timeout episode0. NoMaD가 계산되는 동안 이전 chunk의 PP 실행이 유지됐다.

## 검증 및 보존

Observation world anchor, normalization/cumsum/scaling, sample0 및 원본index2PD 참고 계산, Topomap 공식 후보/선택, 모든 RGB/worker history hash 일치. 실제 PP 재계산 최대 명령 오차7.22e−16, 실제명령↔72Hz적분 pose오차0, corridor오차0. 각 장애물 swept clearance도 기존 함수로 재계산해 일치했다. 기존343파일 및 새raw/derived 등199 input hash 검증 PASS.

Isaac startup renderer stepping 오류5건은 원본 로그에 보존했다. 같은 시도의 기존 RGB 초기화 절차 안에서 회복해 camera/RGB gate를 통과했으며 별도 navigation 재시도는 없었다. 첫 offline `analysis_01`은 NumPy 환경 간5.55e−17m 차이에 대한 완전일치 assertion에서 중단했다. 원본 결과를 보존하고 분석기만 절대허용오차1e−12로 수정한 `analysis_02`가 통과했다. 실행 코드·파라미터는 바꾸지 않았다.

작은 결과: [summary JSON](../research/results/phase0c_chunk_pilot_20261020/summary.json), [switch CSV](../research/results/phase0c_chunk_pilot_20261020/chunk_switches.csv), [검증 provenance](../research/results/phase0c_chunk_pilot_20261020/verification.json), [XY 그림](../research/results/phase0c_chunk_pilot_20261020/trajectory.png). 전체93개 raw/derived, RGB, 72Hz pose 및9Hz command는 위 artifact 경로에만 보존했다.

수정 범위: 새 `chunk_execution.py`, 고정 protocol, offline report, 최소3개 tests; 기존 launch/simulator/async runtime에는 선택형 hook, async validator에는 actual-command override 허용만 추가했다. 기존 `pure_pursuit.py`, NoMaD/Topomap/공식PD/Graph/geometry/scenario는 변경하지 않았다.

## N≥10 이전 판단

이번 S0 PILOT에서는 필수 adapter 버그나 parameter 변경 필요성이 확인되지 않았다. 다만 최대 .726rad/s switch 명령 jump와 짧은 endpoint target의 민감성은 남아 있으며, Phase0-B의 좁은 reference 여유에서는 이미 추종 margin 실패가 있었다. 본 실행 전에 이 진단·안전 판정 기준과 실행기 선택을 명시적으로 확정해야 한다. 이번 단일 성공으로 일반 안전성, PP 우월성 또는 영구 실행기 교체를 결정하지 않는다. 추가 tuning/실험/batch는 진행하지 않았다.
