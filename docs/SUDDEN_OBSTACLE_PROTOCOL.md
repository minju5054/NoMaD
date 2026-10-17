# Sudden obstacle pilot — 실행 전 고정

기준 `8e157a73f229b2136ffb9a846baae545cd2df05c`, branch `research/isaac6-sudden-obstacle`. 새 [scenario](../research/nomad_isaac/sudden_obstacle_scenario.json)는 기존 wide-wall 설정에 DynamicObstacle만 추가한다. 추가 latency 0 ms, 실제 navigation 1회, 재시도·위치/크기/seed 조정 없음. 기존 모델·controller·geometry 함수·checkpoint·4/9/72 Hz·1초 timeout·fixed-goal adapter를 유지한다.

## 고정 geometry와 trigger

- 중심 `(2.45, -0.18)` m, 크기 `(0.35, 0.35, 0.8)` m, 바닥 위 z=0..0.8 m. 색은 magenta `(0.65,0.04,0.65)`로 정적 녹색 장애물과 구분한다.
- **Integration tick 970, simulation time 970/72 = 13.472222222 s에 출현**한다. 실제 robot pose나 request ID에 따라 trigger를 변경하지 않는다. 이전 종료 시 NOT_TRIGGERED로 기록한다.
- 기존 성공 run의 이 tick pose는 `(2.066208, .055170, -.764799 rad)`, 적용 OLD 49. 새 장애물은 local 전방 .439744 m/왼쪽 .096054 m, bearing 12.32°다. Footprint clearance .127289 m, 기존 장애물과 표면 간격 .575000/.125100 m. OLD full clearance −.09 m, prefix .037442 m. 새 장애물 아래쪽에는 벽까지 1.145 m의 빈 Y 간격이 있다. 이는 선택을 위한 baseline geometry이며 새 실행 결과나 회피 가능성의 보증이 아니다. [선정 근거](../research/results/isaac6_sudden_obstacle_20261017/selection.json).

## Render/execution clock 규칙

USD visibility를 72 timecodes/s에서 tick 970 이전 invisible, 이후 inherited로 미리 author한다. Camera는 기존처럼 4 Hz snapshot의 simulation time으로 렌더링한다. 72 Hz execution thread도 동일 integer tick 조건을 사용한다. Spawn 이전 동적 collision 계산은 비활성, spawn tick에서는 현재 pose의 zero-duration footprint만 검사하며 그 직전 interval을 소급 충돌 처리하지 않는다. 다음 tick부터 전체 swept interval을 검사한다. 정적 monitor는 모든 tick에서 기존대로 동작한다.

Render는 USD main thread, kinematic execution은 별도 thread다. 동일 **logical simulation timestamp**에서 활성 상태가 일치하도록 하고 wall-clock 동시 USD 수정이나 72 Hz RGB 생성을 주장하지 않는다. Capture 중 execution이 진행되어도 RGB는 이미 선택한 observation snapshot의 상태를 유지한다. Spawn wall/pose와 capture start/end wall을 별도로 기록하며 execution을 rendering/inference에 맞춰 정지시키지 않는다.

Semantic instance mask와 같은 render product의 RGB로 실제 visible 여부를 확인한다. DynamicObstacle instance pixels >=20을 최초 visible 조건으로 고정하며 해당 영역의 RGB magenta pixel 수를 함께 검사한다. Raw RGB/마스크/metadata를 observation별 별도 저장하고 최초 FRESH의 정확한 4-frame history와 worker input hash를 대조한다. Setup goal/start RGB에서는 새 장애물이 invisible이어야 한다. 보이지 않거나 입력 포함 근거가 없으면 FRESH evidence failure로 보고한다.

## OLD/FRESH와 판정

OLD는 spawn 직전 적용 중인 prediction, FRESH는 새 장애물이 보이는 observation을 history에 포함한 최초 accepted request다. 최초 FRESH가 switch되지 않으면 B를 만들지 않는다. 사이의 추가 pre-spawn-input prediction 적용은 별도 기록한다. 각 prediction은 자기 observation pose에 world anchor를 유지한다.

Dynamic-only와 모든 장애물 full 8-point/prefix 0→1→2 clearance를 따로 계산한다. Actual OLD 구간은 spawn부터 최초 FRESH switch/종료까지로 하되 intervening command ID를 명시한다. Actual FRESH 구간은 switch부터 다음 switch/종료까지다. 기존 clearance, correspondence, entry 및 `async_handoff_protocol.json` thresholds를 유지한다. .02 m obstacle safety margin, corridor containment >0, heading segment >=.02 m, common overlap >=.10 m를 바꾸지 않는다.

OLD prediction 위험+안전한 FRESH / 양쪽 위험 / 양쪽 안전 / 실제 OLD 실행 충돌 / FRESH 관측·적용 근거 부족을 분리한다. Safe FRESH가 있어도 B→entry 단순 staging이 안전하면 Graph 후보로 만들지 않는다. 실제 충돌, 미실행 predicted tail, 미실행 connector 위험을 분리한다. 최초 FRESH 이후 안전한 FRESH의 존재 여부는 저장 결과만 추가 집계한다. 유효 pair가 있으면 비교 그림 한 장만 만든다. Graph/Topomap/새 controller/smoothing/영상은 구현하지 않는다.
