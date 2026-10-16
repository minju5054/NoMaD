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
