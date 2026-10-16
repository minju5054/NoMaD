# Async NoMaD: second obstacle 0.5 × 1.5 × 1.0 m

2026-10-16. 사용자 요청에 따라 두 번째 장애물을 `(X,Y,Z)=(0.5,1.5,1.0)` m로 키워 한 번 다시 실행한다. 기준 `54cac316c5d7417843f3b0ca2c20049c40cf8970`, 새 branch `research/isaac6-async-wide-wall`.

## 실행 전 고정

- 이전 왼쪽 벽 부착 조건을 유지한다. 두 번째 장애물 Y 크기 **0.6→1.5 m**, 중심 Y **1.20→0.75 m**. 중심 `(3.0,0.75)`, AABB `[2.75,0,0]..[3.25,1.5,1]`, +Y 면이 왼쪽 벽 안쪽 `y=1.5`에 닿는다. X 크기/위치와 높이는 유지한다.
- 왼쪽 gap 0 m, 오른쪽 벽과의 물리적 gap 1.5 m. 반경 0.09 m agent가 장애물과 0.02 m clearance를 유지하며 오른쪽을 통과하려면 center y<=−0.11 m여야 한다. 첫 장애물 왼쪽 통과 후 두 번째 오른쪽 통과가 계속 관찰 대상이며, 방향을 강제하지 않는다.
- 첫 장애물, start/goal, footprint 반경 9 cm, safety margin 2 cm, goal tolerance 0.30 m, timeout 60 simulation s, seed schedule 101+2k, NoMaD/checkpoint/10-step sampling/sample 0/index 2, preprocessing/scaling/원본 PD/속도 유지.
- Async observation/planning 4 Hz, controller 9 Hz, integration 72 Hz, 1초 waypoint timeout, 기존 real-time protocol 및 contact/corridor 즉시 중단 유지. 새 model/controller/회피 logic/Graph/latency injection은 추가하지 않는다.
- 정상 navigation 1회, 결과를 보고 조건을 바꾸거나 성공할 때까지 반복하지 않는다. 종료 직후 실제 기록 pose의 GUI USD를 저장하고 기존 Isaac GUI에서 재생한다. 기존 raw/결과/환경을 보존한다.
- Raw: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_wide_wall_01/`. GUI: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_wide_wall_gui_01/recorded_motion_gui.usda`.

위 조건은 실행 전 기록이다. 실측 결과는 종료 후 추가한다.

## 결과: 왼쪽 → 오른쪽 통과 및 goal entry 성공

실행 commit `fb9bf2253044be477873aa113a19899f479af248`, clean tree. 정상 navigation **1회**, 기술적/성능 재시도 **0회**. **Async/soft real-time 및 obstacle safety/corridor/goal 모두 PASS**다. 모델이나 controller에 회피 방향을 강제하지 않았다.

| 항목 | 실측 |
|---|---|
| 첫 장애물 | **왼쪽 통과**, t=11.319444 s, XY `(1.791272, 0.385653)` |
| 두 번째 장애물 | **오른쪽 통과**, t=20.138889 s, XY `(3.341212, −0.213487)` |
| 첫 / 두 번째 최소 swept clearance 하한 | **0.069630 / 0.082836 m**, 0.02 m 기준 충족 |
| Obstacle overlap / corridor 침범 | 없음 / 없음; corridor clearance 하한 0.790389 m |
| Goal entry | **true**, t=24.583333 s, 거리 **0.297708 m** |
| 최종 pose | `(4.221782, −0.105947, 0.149875 rad)` |
| GPU inference / receive / switch / pose | 95 / 95 / 94 / 1,771 |
| Warm GPU median / p95 | **29.187 / 31.903 ms** |
| Observation→ready median / p95 | 67.489 / 127.727 ms |
| Observation→switch median / p95 | 138.283 / 176.113 ms, 적용된 94개 |
| Inference 중 OLD 이동 median / max | **0.002778 / 0.005556 m**, 이후 94/94 inference에서 nonzero 실제 이동 |
| Observation→switch translation median / max | 0.027775 / 0.044444 m |
| Observation→switch yaw 절댓값 median / max | 0.019956 / 0.088889 rad |
| Waypoint timeout / busy skip / missed capture | 0 / 1 / 0 |
| Simulation / wall duration | 24.583333 / 24.583434 s |
| RTF / pacing error p95·max | **0.999995888 / 0.154592·1.198826 ms** |
| Inference wall↔sim mapping error p95 | 0.067599 ms |

마지막 result ID 94는 t=24.569444 s snapshot에 수신됐지만 다음 9 Hz controller tick 전 t=24.583333 s에 goal entry로 종료됐다. 따라서 결과와 raw/derived는 보존하고 switch는 없다. 미적용 결과를 적용했다고 보고하지 않으며, waypoint 유실이나 실행 오류가 아니다.

반경을 더한 장애물 X 범위의 executed center Y는 첫 장애물 **0.387646..0.619595 m**, 두 번째 **−0.240280..−0.154262 m**다. 이전 폭 0.6 m run에서는 두 번째를 world Y>0에서 통과했지만, 이번에는 확대된 장애물의 오른쪽인 **world Y<0**으로 실제 이동했다. 안전 판정은 pose 표본만이 아니라 전체 실행 구간의 기존 swept arc 검사로 확인했다.

## 검증·보존·GUI

실제 USD world bounds에서 두 번째 크기가 정확히 **`(0.5,1.5,1.0)` m**, AABB `[2.75,0,0]..[3.25,1.5,1]`임을 확인했다. 왼쪽 gap은 nominal 0 m, wall float32 표현에 따른 실측 −7.45e−10 m(수치적으로 맞닿음)다. GUI footprint 반경도 0.09 m다. [Geometry 검증](../research/results/isaac6_async_wide_wall_20261016/geometry.json).

기존 offline validator로 모든 95 raw/derived의 `(8,8,2)` float32 finite, normalization/cumsum/scaling/sample 0/index 2, 원본 PD command, observation world anchor, 실제 SE(2) pose integration, swept clearance, request/receive/switch ordering과 첫 waypoint 전 정지를 검증했다. Source provenance/clean commit 일치, 이전 run 주요 **208개 파일**과 synchronous baseline **484개 파일** hash 불변. 새 source logic 없이 scenario/doc/results만 추가했으며 모델·controller·async runtime·clearance·GUI exporter·환경을 바꾸지 않았다. 자연 waypoint timeout은 0회로 `NOT_EXERCISED`다. 초기 shader 준비의 renderer-step 오류 뒤 RGB gate를 통과했으며 기술적 재시도는 없었다.

주행 summary 후 **0.965초**에 GUI용 USD를 저장했다. 원본 **1,771개 pose**, **101개 prim** 보존 검사 통과, 최대 pose 오차 4.44e−16. 기존 GUI에서 반복 재생을 열어 `playing=true`, t=2.013889 s의 pose가 원본 row 145와 <1e−10 이내 일치함을 확인했다. Startup Error 0개. **저장된 실제 주행의 재생이며 새 inference/navigation이나 MP4가 아니다.**

```bash
bash /home/gpuadmin/Workspace/NoMaD/visualnav-transformer/research/nomad_isaac/open_scene.sh /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_wide_wall_gui_01/recorded_motion_gui.usda --play
```

Raw/GUI 경로는 실행 전 기록과 같다. Offline 세부 검증은 `../artifacts/isaac6/async_wide_wall_01_validation/`, [작은 summary](../research/results/isaac6_async_wide_wall_20261016/summary.json)와 [review](../research/results/isaac6_async_wide_wall_20261016/review.json)는 Git에 저장했다. 기존 validator raw 보고서의 GUI 미구현 문구는 navigation 계측 단계의 기존 문구이며 후속 GUI는 별도 manifest로 검증했다. 단일 scenario/seed schedule의 성공이므로 일반적 회피 성능·안전 보장이나 Graph 필요성은 입증하지 않았다.
