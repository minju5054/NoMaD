# Asynchronous NoMaD, 9 cm footprint radius

2026-10-16. 사용자 요청에 따라 `research/isaac6-async-execution`의 `b0ab3d274dba47ce815060dd0ec1d062eba6fe5f`에서 `research/isaac6-async-radius09`를 생성했다.

## 실행 전에 고정한 조건

- 기존 two-obstacle scenario의 `agent_radius_m`만 **0.12 → 0.09 m**로 변경한다. 9 cm는 반경(직경 18 cm)이다. 기존 scenario와 raw run은 보존한다.
- 시작 `(0,0,0)`, 목표 `(4.5,0,0)`, 두 장애물 위치·크기, seed schedule 101+2k, model/checkpoint, 10-step diffusion, sample 0/index 2, metric scaling, 원본 PD 및 속도 제한은 유지한다.
- 기존 async 실행: RGB/planning 4 Hz, control 9 Hz, integration 72 Hz, received-age 1초 timeout, real-time pacing. 안전 clearance 0.02 m, goal tolerance 0.30 m, 60 simulation s timeout과 geometric contact 즉시 중단을 유지한다.
- 새 정상 navigation은 **1회**다. 결과에 따른 조건 변경이나 성공할 때까지 재실행하지 않는다. 기존 async protocol의 pacing 판정도 유지한다.
- 종료 즉시 기록된 pose 전체를 사용하는 GUI용 animated USD를 별도 디렉터리에 저장한다. 기존 native timeline 재생기를 사용하며 새 GUI framework/MP4는 만들지 않는다. GUI의 파란 footprint 반경과 흰 방향 표식도 9 cm에 맞춘다.

예정 raw: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_radius09_01/`.
예정 GUI: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_radius09_gui_01/recorded_motion_gui.usda`.

이 문단까지는 실행 전 기록이다. 실제 결과는 종료 후 추가한다.

## 실제 결과

실행 코드 `c8fcf516d2dd35c59bfb408d88f1347ec43d4b01`, clean tree에서 정상 주행 **1회**, 기술적 재시도·성능 재시도 0회. **Async/soft real-time PASS, 전체 navigation FAIL**이다. 두 장애물은 왼쪽으로 통과했고 장애물 overlap은 없었다. 하지만 목표를 지나친 뒤 복도 끝 X 경계를 footprint가 침범하여 **37.736111 s**에 즉시 중단했다. PhysX collision이 아닌 기존 geometric monitor의 판정이다.

| 항목 | 실측 결과 |
|---|---|
| Footprint | 반경 0.09 m / 직경 0.18 m |
| 장애물 1 / 2 최소 swept clearance 하한 | **0.256990 / 0.328163 m**; 두 장애물 모두 0.02 m margin 충족 |
| 장애물 1 / 2 통과 시점 | 11.361111 / 19.347222 simulation s; 모두 +Y 왼쪽 |
| Goal entry / 최소 목표 거리 | **false / 0.650837 m**, 최근접 t=25.430556 s |
| 종료 | `corridor_footprint_stop`, t=37.736111 s |
| 최종 pose | `(5.910703, 1.382503, 1.172786 rad)` |
| 최소 corridor clearance 하한 | **−0.000704959 m**, corridor containment FAIL |
| Inference / switch / pose rows | 147 / 147 / 2,718 |
| Warm GPU inference median / p95 | **29.183 / 30.990 ms** |
| Observation→ready median / p95 | 67.116 / 124.348 ms |
| Observation→switch median / p95 | 138.330 / 166.506 ms |
| Inference 중 OLD 이동 거리 median / max | **0.002778 / 0.005556 m**, 이후 146/146 requests에서 실제 nonzero 이동 |
| Observation→switch translation median / max | 0.024999 / 0.044444 m |
| Observation→switch yaw 절댓값 median / max | 0.026848 / 0.083333 rad |
| Waypoint timeout | 0회, runtime expiry `NOT_EXERCISED` |
| Busy observation skip / missed capture slots | 1 / 0; 요청을 중복 적재하지 않음 |
| Sim / wall duration, RTF | 37.736111 / 37.736208 s, **0.999997428** |
| Pacing absolute error p95 / max | **0.154665 / 1.396211 ms**, 1 tick 초과 0회 |
| Inference wall↔sim mapping error p95 | 0.274973 ms |

기존 반경 0.12 m async run은 8.458333 s에 첫 장애물과 접촉했고 최소 목표 거리는 3.321954 m였다. 이번 경로 차이를 footprint 축소만의 효과로 해석할 수는 없다. **반경은 collision geometry에만 쓰이고 NoMaD/controller 입력이 아니다.** 두 run의 원본 scene USD hash는 같지만 goal/start RGB hash가 다르며 실제 비동기 capture/switch timing도 달라졌다. 새로운 정상 주행 1회의 관측 결과이며 성능 향상이나 안정적 회피를 입증하지 않는다.

## 저장·검증·GUI

주행 summary 저장 후 **0.962초**에 animated USD 저장을 완료하고, 저장된 파일을 기존 Isaac GUI로 열었다. 저장된 2,718개 pose 전부와 원래 101개 prim의 type/default attributes/relationships 보존을 검증했다. 최대 pose 오차 4.44e−16, 반경 0.09 m의 파란 footprint와 흰 방향 표식, 하늘색 전체 executed trail 및 주황 goal ring을 추가했다. 원래 scene/camera/obstacle/model 데이터는 수정하지 않았다. Native GUI `playing=true`, t=2.013889 s의 pose가 원본 145번 row와 1.89e−15 이내 일치하고 startup Error 0개였다. **GUI는 실제 저장 pose의 반복 재생이며 새 inference/주행이 아니다.** MP4는 생성하지 않았다.

```bash
bash /home/gpuadmin/Workspace/NoMaD/visualnav-transformer/research/nomad_isaac/open_scene.sh /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_radius09_gui_01/recorded_motion_gui.usda --play
```

기존 scheduler synthetic tests **5 passed, 0.06 s**. Offline validation은 모든 147 raw/derived 출력의 `(8,8,2)` float32 finite, normalization/cumsum/scaling/sample 선택, 원본 PD command, observation world anchor, source provenance, exact pose integration 및 radius 0.09의 swept clearance 재계산을 통과했다. 모든 source hashes 일치, 이전 async raw 주요 83개와 synchronous baseline 484개 hashes 불변이다. 모델/공식 controller/async runtime/coordinate/clearance 코드와 환경은 변경하지 않았다. 초기 shader 준비 중 renderer-step 경고/오류가 있었지만 RGB gate 이후 정상 주행이 완료됐으며 기술적 재시도는 없었다.

원본 logs/outputs는 `async_radius09_01/`, offline 검증은 `async_radius09_01_validation/`, GUI와 manifest/로그는 `async_radius09_gui_01/`에 분리했다. [작은 결과](../research/results/isaac6_async_radius09_20261016/summary.json)와 [GUI 검증](../research/results/isaac6_async_radius09_20261016/gui_validation.json)을 Git에 보존한다. 기존 validator의 raw 보고서에 있는 “GUI not added” 문구는 navigation 계측 단계에 관한 기존 문구이며, 이 후속 GUI export는 별도 manifest로 기록했다.
