# Phase B — Actual-pose recovery feasibility

범위: **Oracle geometry; offline SE(2) kinematic feasibility**. 기준 `2892c3f913ed3064253efb05798438e0109b61f9`, 동일 `research/phase0-infrastructure`에서 수행한다. 온라인 Recovery는 제자리 회전 우선·후진 비활성 상태를 유지한다.

## 사전 고정

`actual_pose_recovery_protocol.json`에 두 raw run의 spawn/final 네 상태와 B0/B1/B2 동작 집합을 고정했다. Git에 저장된 기존 summary와 raw spawn/72Hz trace/final pose가 정확히 일치하며, 사용자 제공 소수점 pose는 5e−10 절대 허용 오차로 확인한다. 탐색에는 반올림 전 raw pose/yaw 및 실제 spawn box를 사용한다. Oracle STOP의 adaptive placement 좌표를 원본 scenario에 쓰지 않고 별도 메모리 config에만 반영한다.

| 시작 상태 | Source tick / time | 시작 최소 obstacle clearance |
|---|---:|---:|
| EARLY-GRAPH spawn | 792 / 11s | 0.390553469m |
| EARLY-GRAPH final | 4320 / 60s | 0.021406126m |
| Oracle STOP spawn | 970 / 13.472222s | 0.106968936m |
| Oracle STOP final | 4320 / 60s | 0.024828902m |

모두 시작 clearance≥0.02m/corridor>0이다. 실제 동적 중심은 EARLY-GRAPH `(2.372279542,0.110674603)`, Oracle STOP `(2.35439671156368,0.07771649443348477)`m이며 크기0.35×0.35×0.8m를 유지한다. 출현 이후의 고정 geometry만 검사하므로 원래 시간에 따른 전체 navigation feasibility를 판단하지 않는다.

기존 `scenario_feasibility.search()`를 확장해 재사용한다. XY5cm/yaw64bin, primitive0.5s, heuristic weight1.5, 30,000 expansions/최대 경로60s, goal XY반경0.30m/terminal yaw 없음, radius0.09m/obstacle margin0.02m/corridor footprint clearance>0을 유지한다.

- B0: 기존 전진5개 `(v=.2,w=0/−.2/+.2/−.4/+.4)`.
- B1: B0 + 제자리 회전 `(v=0,w=−.4/+.4)`.
- B2: B1 + 후진5개 `(v=−.2,w=0/−.2/+.2/−.4/+.4)`.
- 이번 요청의 **120 process CPU seconds**를 선택형 budget으로 사용하고 wall time도 별도로 기록한다. 기존 Phase0-A의 기본120 wall seconds 설정은 변경하지 않는다.
- 모든 조건에서 side=None으로 직접 탐색한다. 기존 one-pass side gate/certificate는 호출하지 않는다. 뒤로 돌아 다른 쪽으로 우회하는 경로를 허용한다.
- 발견된 모든0.5s 연속 arc는 기존 swept/corridor 함수로 다시 검증한다. 이동 거리는 `sum(abs(v)*dt)`이며 spin 시간/각도와 reverse 구간도 보존한다.

최소 검증: 새3개+기존5개 tests PASS. Spin의 XY 고정/정확한 yaw, 후진 직선·원호 및 역적분, endpoint만 안전한 후진의 연속 충돌 검출, reverse witness의 절댓값 거리, nested 동작 집합과 기존 forward-only 기본 검증을 확인했다. 새로운 navigation/inference, parameter tuning 또는 온라인 controller 변경은 없다.

## 실행 명령

고정 코드 commit 후 새 출력 경로에서 아래 명령을 한 번만 실행한다.

```bash
bash research/python.sh -m nomad_phase0.actual_pose_recovery run --output /home/gpuadmin/Workspace/NoMaD/artifacts/phaseb/actual_pose_recovery_01
```

그림은 저장된 witness만 읽어 기존 시스템 matplotlib로 한 번 생성한다.

```bash
PYTHONPATH=research /usr/bin/python3 -m nomad_phase0.actual_pose_recovery plot --output /home/gpuadmin/Workspace/NoMaD/artifacts/phaseb/actual_pose_recovery_01
```

`NO_PATH_FOUND`는 제한된 primitive·bin pruning·예산 내 witness 미발견이다. 불가능 증명이나 후진의 수학적 필요성으로 해석하지 않는다. Weighted Hybrid A*의 첫 witness는 최단/최적 경로가 아니므로 조건별 경로 시간 차이도 최적성 비교가 아니다.

결과는 12조건 실행 후 별도로 기록한다.
