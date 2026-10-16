# Async NoMaD: second obstacle against the left wall

2026-10-16. 사용자 요청: 첫 장애물은 왼쪽, 두 번째 장애물은 오른쪽으로 회피하는 상황을 기대하며, 두 번째 장애물을 왼쪽 벽에 붙여 한 번 실행한다. 기준 `12c8fc3fc997b52d0ceaf8251fabc1b35765fbc9`, 새 branch `research/isaac6-async-wall-obstacle`.

## 실행 전 고정

- 기존 `two_obstacles_radius09_scenario.json`을 복사해 **두 번째 장애물 중심 Y만 0.35 → 1.20 m**로 변경한다. 중심 `(3.0,1.2)`, 크기 `(0.5,0.6,1.0)` m, XY AABB `[2.75,0.9]..[3.25,1.5]`다. 첫 장애물은 중심 `(1.5,0)`, 크기 `(0.4,0.5,0.8)` 그대로다.
- 왼쪽은 최초 진행 방향 +X 기준 world +Y다. 왼쪽 벽 안쪽 경계 `y=1.5`에 두 번째 장애물의 +Y 면을 붙여 **왼쪽 gap=0 m**로 고정한다. 9 cm 원형 footprint는 왼쪽으로 통과할 수 없다. 장애물 오른쪽에서는 0.02 m clearance를 위해 center y<=0.79 m가 필요하며, 첫 장애물 왼쪽에서는 center y>=0.36 m가 필요하다. 두 조건은 기하학적으로 양립한다.
- Footprint 반경 0.09 m, margin 0.02 m, start `(0,0,0)`, goal `(4.5,0,0)`, tolerance 0.30 m, timeout 60 simulation s 유지. Model/checkpoint, diffusion 10 steps, sample 0/waypoint index 2, normalization/scaling, PD/속도, seed schedule 101+2k 유지.
- 기존 async 4/9/72 Hz 실행 및 1초 waypoint timeout, pacing protocol, contact/corridor 즉시 중단 유지. 원본 policy에 원하는 방향을 강제하는 planner/heuristic은 추가하지 않는다. 기대 방향은 결과가 아니며 실제 passage로 판정한다.
- 정상 주행 1회만 실행하고 navigation 실패에 따른 조건 변경·재시도는 하지 않는다. 원본 RGB/raw/derived를 새 경로에 저장한다. 종료 직후 기존 native GUI exporter로 모든 pose를 저장하고 반복 재생한다.
- Raw: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_wall_obstacle_01/`. GUI: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_wall_obstacle_gui_01/recorded_motion_gui.usda`.

위 조건은 실행 전에 기록했다. 실제 결과는 종료 후 추가한다.

## 실제 결과: 왼쪽 → 오른쪽 통과 및 goal entry 성공

실행 commit `b6ecb8449de29f4ce5b89d16cb5e369134c500e4`, clean tree. 정상 주행 **1회**, 기술적/성능 재시도 **0회**. 모델 출력이나 controller를 변경하지 않고 기대한 순서가 실제로 관측됐다. **Async/soft real-time PASS, obstacle safety/corridor/goal PASS**다.

| 측정 | 실제 결과 |
|---|---|
| 장애물 1 통과 | **왼쪽**, t=10.958333 s, pose XY `(1.791994, 0.421637)` |
| 장애물 2 통과 | **오른쪽**, t=18.777778 s, pose XY `(3.342400, 0.381494)` |
| 장애물 1 / 2 최소 swept clearance 하한 | **0.101514 / 0.429708 m**, 두 장애물 모두 0.02 m margin 충족 |
| Obstacle overlap / corridor 침범 | **없음 / 없음**, corridor 최소 clearance 하한 0.861478 m |
| Goal entry | **true**, t=23.958333 s, 거리 **0.299932 m** <= tolerance 0.30 m |
| 최종 pose | `(4.371940, 0.271219, −0.020233 rad)` |
| Inference / receive / switch / pose | 92 / 92 / 92 / 1,726 |
| Warm GPU latency median / p95 | **30.233 / 33.046 ms** |
| Observation→ready median / p95 | 69.215 / 105.292 ms |
| Observation→switch median / p95 | 138.130 / 166.520 ms |
| Inference 동안 OLD 거리 median / max | **0.002778 / 0.005556 m**, 이후 91/91 inference에서 실제 nonzero 이동 |
| Observation→switch translation median / max | 0.027776 / 0.044444 m |
| Observation→switch yaw 절댓값 median / max | 0.013362 / 0.072222 rad |
| Waypoint timeout / busy skip / missed capture slots | 0 / 1 / 0 |
| Sim / wall duration | 23.958333 / 23.958468 s |
| RTF / pacing absolute error p95·max | **0.999994371 / 0.153655·4.958789 ms** |
| Inference wall↔sim mapping error p95 | 0.212380 ms |

여기서 왼쪽/오른쪽은 각 장애물의 +Y/−Y **쪽**을 뜻한다. 두 번째 통과 pose의 world Y도 양수지만, 장애물의 아래쪽 Y 면 0.9 m보다 작으므로 오른쪽 통과다. 기존 log의 `right_negative_y` label을 world Y<0이라는 뜻으로 해석하지 않는다. Radius를 포함한 장애물 X 범위에서 실제 center Y는 첫 장애물 0.422504..0.548521 m, 두 번째 0.353801..0.381638 m로 각각 왼쪽/오른쪽에 있었다. 안전 판정은 이 pose 표본뿐 아니라 기존 swept arc clearance 재계산으로 확인했다.

## Geometry·출력·보존 검증

실제 저장 USD에서 두 번째 AABB가 `[2.75,0.9,0]..[3.25,1.5,1]`인 것을 확인했다. Wall float32 크기 표현 때문에 실측 gap은 −7.45e−10 m(수치적으로 맞닿음), nominal gap은 0 m다. 0.18 m 직경의 agent가 왼쪽 틈으로 통과할 수 없다. 반대쪽 통과 공간과 첫 장애물 geometry는 유지했다. [USD geometry 검증](../research/results/isaac6_async_left_wall_20261016/geometry.json).

92개 raw/derived 모두 `(8,8,2)` float32 finite이며 raw normalization/cumsum/metric/sample 0/index 2, 원본 PD command, observation world anchor, 모든 SE(2) pose integration 및 swept clearance 검증을 통과했다. 첫 waypoint 전 정지, 다음 controller tick 전환, single outstanding ordering, 실제 OLD 이동 및 사전 real-time 기준을 확인했다. Waypoint expiry는 자연 발생하지 않아 `NOT_EXERCISED`다. 별도 새 model/controller test나 inference를 추가하지 않고 기존 offline validator를 실행했다.

이전 9 cm run의 주요 **321개 파일**, 기존 synchronous baseline **484개 파일**의 hash 불변을 확인했다. 실행 source hash/clean commit 일치, 기존 모델·controller·async runtime·clearance·좌표·GUI exporter 및 환경 변경 없음. 초기 shader 준비 때 renderer-step 오류가 있었지만 RGB gate 이후 정상 주행을 완료했고 기술적 재시도는 없었다. 단일 배치/seed schedule에서의 성공이며 일반적인 회피 성능이나 Graph 필요성은 검증하지 않았다.

## GUI 저장 및 재생

주행 summary 생성 후 **0.978초**에 GUI용 USD를 저장했다. 원본 **1,726개 pose**, **101개 prim** 보존 검사 통과, pose 최대 오차 4.44e−16. 기존 GUI에서 native timeline 반복 재생을 열었고 `playing=true`, 원본 row 145의 pose 일치(<1e−10), startup Error 0개를 확인했다. 실제 기록을 재생하며 새로운 inference/navigation/MP4는 만들지 않는다.

```bash
bash /home/gpuadmin/Workspace/NoMaD/visualnav-transformer/research/nomad_isaac/open_scene.sh /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_wall_obstacle_gui_01/recorded_motion_gui.usda --play
```

Raw와 GUI 경로는 위 실행 전 기록과 같다. Offline 전체 검증은 `../artifacts/isaac6/async_wall_obstacle_01_validation/`, 작은 Git 결과는 [summary](../research/results/isaac6_async_left_wall_20261016/summary.json)와 [review](../research/results/isaac6_async_left_wall_20261016/review.json)에 보존했다. 기존 validator raw 보고서의 GUI 미구현 문구는 navigation 계측 단계의 기존 문구이며 후속 GUI export는 별도 manifest로 검증했다.
