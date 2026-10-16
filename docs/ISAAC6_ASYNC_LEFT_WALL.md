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
