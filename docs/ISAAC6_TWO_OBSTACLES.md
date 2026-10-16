# Isaac Sim 6: 두 정적 장애물과 늘어난 시작 거리

2026-10-16. 사용자의 새 요청에 따라 기존 단일 장애물 실험 이후 **새 조건 한 번의 bounded navigation**을 수행한다. 이전 실패를 성공할 때까지 반복하는 실험이 아니다. 기존 결과를 보존하며 별도 `research/isaac6-two-obstacles` branch를 사용한다. 기준 commit은 `45b6026`이다.

## 실행 전에 고정한 조건

| 항목 | 새 값 |
|---|---|
| 시작 pose | `(0,0,0)`; m, rad |
| 장애물 1 | `StaticObstacle1`, 중심 `(1.50,0.00)`, 크기 X/Y/Z `(0.40,0.50,0.80)` m |
| 장애물 2 | `StaticObstacle2`, 중심 `(3.00,0.35)`, 크기 `(0.50,0.60,1.00)` m |
| 목표 pose | 두 장애물 뒤 `(4.50,0,0)` |
| 목표 tolerance | 기존 0.30 m |
| Timeout | simulation 60 s; navigation wall 180 s; process 600 s |
| 첫 장애물 앞면까지 거리 | 시작 center에서 1.30 m; footprint 기준 gap 1.18 m |
| 이전 실험의 동일 거리 | 0.60 m / 0.48 m |
| Collision proxy / safety margin | 반경 0.12 m 원형 footprint / 0.02 m |

두 장애물은 기존과 같은 녹색이다. 복도·RGB camera·goal-conditioned 원본 checkpoint, observation 4 Hz/controller 9 Hz/integration 72 Hz, max v=0.2 m/s/max w=0.4 rad/s, 원본 controller DT=0.25 s, sample 0/point index 2, 10 diffusion steps, 8 samples×8 points, seed schedule 101+2i/102+2i, normalization/scaling과 synchronous 동작을 유지한다. Goal image는 새 목표 pose에서 실제 렌더링한다. 이 요청에서는 목표가 두 장애물 뒤에 있어야 하므로 goal과 timeout도 실행 전에 변경했다. 크기·거리·goal이 함께 바뀌므로 개별 효과를 분리한 대조 실험은 아니다.

성공 조건은 두 장애물 모두와 접촉 없이 clearance 기준 및 corridor containment를 지키고 goal tolerance에 진입하는 것이다. 어느 장애물이든 최초 geometric contact 검출 tick에서 멈춘다. 보수적 하한만 contact를 가리키는 경우는 별도 conservative contact stop으로 구분한다. NoMaD waypoint를 수정하거나 planner/safety steering/smoothing을 추가하지 않는다. Kinematic geometry 평가이며 PhysX collision 실험이 아니다.

## 코드 변경과 실행 전 검증

- 기존 `ObstacleMonitor`의 단일 AABB/원호 geometry를 각 장애물에 적용한다. Root에는 두 장애물 최소값을 기록하고 `obstacles/<id>/`에는 각각의 geometry/clearance/planning log를 저장한다. 전체 선택 trajectory의 clearance는 실행 결과와 별도 diagnostic이다.
- 기존 단일 scenario와 파일 형식을 보존한다. Scene builder는 명시된 장애물 목록을 렌더링하며 각 USD world AABB를 입력 geometry와 비교한다.
- 초기 goal 거리의 고정값 1.5를 실제 시작·목표 거리로 계산하도록 기록 버그를 수정했다. Controller/integration 계산은 그대로다.
- 영상은 조기 종료가 24 fps sampling grid에 맞지 않아도 마지막 실제 pose를 보존한다. 이때 마지막 frame만 다음 video slot에 배치하며 timestamp 차이를 manifest에 기록한다. GUI yaw는 같은 회전의 unwrapped 표현으로 저장해 ±π 경계에서 역회전하는 보간을 피한다. Raw yaw/pose는 바꾸지 않는다.
- 실행 전 `.venv` GPU/checkpoint/controller/IPC/geometry tests **25 passed, 0 skipped**, 2.09 s, 기존 Transformer warning 1개. 기존 Isaac Python/NumPy에서도 adapter/geometry **16개 통과**. 최초 sandbox 검사 중 socket 송신 1개는 permission 제한으로 실패했고 실제 host 검사에서 통과했다. Model/controller source 변경 없음.

## 실행 결과

아직 실행하지 않음. 조건과 검증된 코드를 먼저 commit한 후 단일 run을 실행하고 실제 결과로 갱신한다.
