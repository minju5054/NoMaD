# OLD/FRESH audit: 사전 고정 규칙

2026-10-16. 기준 `49f865cb4148fedef6c15be1e9739d5e53ba151b`. 이 문서와 `research/nomad_isaac/handoff_protocol.json`을 **pair metric 계산 전에 commit**한다. 이미 알려진 이전 run summary(충돌 없음, 목표 최근접 약 25.25 s)와 로그 schema/source만 검토했다. 아래 수치는 성공률을 맞추기 위한 tuning 값이 아니라 이번 audit의 명시적인 operational definition이다. 추가 threshold sweep은 하지 않는다.

## 데이터와 시간

- 기존 `two_obstacles_01`의 저장된 sample 0만 사용한다. 전체 연속 ID pair 목록을 만들되, 주 분석은 두 observation 및 FRESH application이 최초 goal-distance argmin 시점 이하인 pair이다. 종료 이후 pair는 `EXCLUDED_AFTER_PRIMARY_WINDOW`로만 기록하고 후보로 분석하지 않는다. 이 종료 시간만 과거 전체 실행 결과로 정한다. 미래 pose는 correspondence/entry 선택에 사용하지 않는다.
- 기존 provenance의 source SHA, 이전 video manifest에 저장된 pose/scenario hash를 확인한다. 개별 NPZ/events/planning에 과거 file hash가 없으면 현재 hash는 **새 baseline**이라고 명시한다. 사용한 모든 입력을 분석 전후 hash 비교한다. checkpoint를 읽거나 model을 import하지 않는다.
- world trajectory는 **각 observation pose**에 기존 `local_to_world`를 적용한다. B는 FRESH application simulation time의 정확한 기록 pose다. inference start/end는 wall monotonic time이고 receive simulation time은 observation time과 같다. receive 이후 controller tick 지연에 따른 실제 이동만 측정한다. FRESH를 B로 재정렬하지 않는다.

## 자동 공간 대응과 mismatch

1. native 8 XY points만 correspondence에 사용한다. 관측 원점을 추가한 첫 연결선은 기존 planning clearance와의 비교에만 사용하며 model의 tangent가 아니다. 길이 0.02 m 미만 segment의 heading은 invalid로 남긴다.
2. B yaw의 forward 축 e, left 축 n으로 OLD/FRESH를 투영한다. 두 polyline이 모두 e 방향으로 엄격히 증가(각 증가 >1e-6 m)해야 한다. 반전/self-fold는 correspondence ambiguity로 제외한다. B 앞(u>=0)의 공통 forward-station interval 길이가 0.10 m 이상이어야 한다.
3. 공통 u interval을 0.01 m 이하 간격으로 선형 보간한다. 같은 u에서 lateral revision과 유효 segment tangent 차이를 계산한다. 동일 waypoint index가 같은 물리적 점이라는 가정은 없다. 두 heading이 모두 유효한 sample 비율이 80% 미만이면 pair correspondence가 불충분하다.
4. longitudinal 변화는 같은 u 대응에서는 정의상 0이므로 그렇게 보고하지 않는다. 대신 위 공통 interval의 시작점에서 각각의 curve를 잘라, 둘 중 짧은 길이까지 **동일 arclength progress**로 resample한다. 이때 FRESH−OLD를 OLD의 유효 tangent/left-normal에 분해해 longitudinal/lateral RMS 및 signed mean, 공간 RMSE, heading 차이를 기록한다. 이는 자동 기하 registration proxy이며 물리적 landmark 대응이나 waypoint time 추정이 아니다. 공통 station 밖으로 외삽하지 않는다.

## Boundary-entry와 단순 연결

- FRESH 진입 구간은 native point 0→1→2 prefix다. 유효 heading segment마다 B의 직교 projection(끝점 clamp), 양 끝점, 최대 0.01 m 간격의 점을 entry 후보로 만든다. 각 entry의 tangent는 해당 실제 segment 방향이다. 거리→progress→segment 순으로 결정론적 정렬한다. 가까운 invalid-heading segment를 유효 segment로 꾸미지 않는다.
- `nearest entry`는 위 후보 중 B에 가장 가까운 것. `chosen entry`는 안전한 단순 연결이 있으면 그중 가장 가까운 것, 없으면 nearest다. 장애물 geometry는 현재 알려진 고정값만 사용한다. OLD/FRESH 이후의 실제 주행은 선택 기준에 사용하지 않는다.
- 단순 연결은 원형 footprint로 B에서 제자리 회전 → entry까지 직선 → tangent 방향 제자리 회전이다. 기존 agent는 v=0, |w|<=0.4로 제자리 회전 가능하므로 yaw mismatch만으로 연결 불가능하다고 하지 않는다. 이 연결은 **미실행 diagnostic**이며 새 controller/planner가 아니다. 기존 `segment_clearance`로 모든 장애물과 margin >=0.02 m를 요구하고, corridor footprint containment도 요구한다. 원형 footprint라 제자리 회전의 clearance는 변하지 않는다. 동역학/곡률/최적 연결을 증명하지 않는다.
- FRESH 자체 안전성은 native point 0..7 전체 polyline의 footprint clearance로 평가한다. 원점→point 0을 포함한 기존 planning 값도 별도 보존·검증한다. corridor 침범도 unsafe다. OLD도 동일하게 평가한다.
- 실제 control은 저장된 selected point에 대한 원본 `(v,w)`를 재계산·대조한다. 적용 직후 실제 다음 switch(또는 분석 종료)까지의 command/pose clearance는 별도 execution diagnostic이다. geometry staging가 가능하다는 판단은 원본 PD가 그것을 실행했다는 주장이 아니다.

## 판정 순서

입력/pose/time 검증이 안 되면 `INSUFFICIENT_EVIDENCE`.

1. FRESH 전체 native polyline이 obstacle margin 미달 또는 corridor 밖이면 `UNSAFE_FRESH`.
2. 공통 overlap/heading 또는 유효 prefix entry가 없으면 `INSUFFICIENT_EVIDENCE`.
3. nearest entry의 단순 연결이 안전하고, 거리 <=0.10 m, B yaw↔entry tangent / B yaw↔connector / connector↔entry tangent 각도 모두 <=30°면 `ALREADY_CONSISTENT`. 1e-9 m 이하 connector는 회전각을 B↔tangent로 처리한다.
4. 그 외 안전한 entry connector가 하나라도 있으면 `STAGING_SUFFICIENT`.
5. FRESH 자체가 안전하고 correspondence/heading은 유효하지만 고정 prefix entry 후보들의 단순 연결이 전부 unsafe면 `POTENTIAL_RECONCILIATION_CASE`. 이는 검사한 연결 family의 실패이며 다른 entry/연결의 불가능성이나 Graph 필요성의 증명이 아니다.

RMSE/command jump가 크다는 이유만으로 5번으로 분류하지 않는다. 5번 중 최대 3개를 best available connector의 clearance가 낮은 순, 동률이면 이른 ID 순으로 고른다. 각 선택 pair의 OLD/FRESH/B/entry/장애물/connector를 한 static figure에 표시한다. 없으면 candidate 그림을 만들지 않는다.

종합 판정: 5번이 있으면 `GEOMETRIC_CANDIDATE_FOUND`; 없고 주 분석 pair 중 90% 이상이 분류 가능하면 `NO_QUALIFIED_CANDIDATE`; 나머지는 `INSUFFICIENT_EVIDENCE`. 주 분석 밖은 분모에서 제외한다.

두 장애물 구간은 B world x 기준, expanded AABB near/far face(반경 포함)의 앞뒤 0.50 m로 사전 정의한다. approach는 near−0.50<=B.x<near, pass는 near<=B.x<=far, departure는 far<B.x<=far+0.50이다. 두 window가 겹치면 양쪽 descriptive summary에 포함할 수 있다. 미래 통과 성공 여부로 pair를 고르지 않는다.

## 제한

Prediction마다 initial/DDPM seed가 다르므로 revision에 observation 변화와 sampling noise가 섞여 있다. Native yaw/time/covariance는 없다. 자동 station/progress 대응은 oracle correspondence가 아니다. Synchronous 기록만으로 비동기 OLD 이동, reconciliation 필요성, Graph의 우월성 또는 일반적 안전성을 증명할 수 없다. 새 inference/navigation, optimization, replay/video, parameter tuning은 수행하지 않는다.
