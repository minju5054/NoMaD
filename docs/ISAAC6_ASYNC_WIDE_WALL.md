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
