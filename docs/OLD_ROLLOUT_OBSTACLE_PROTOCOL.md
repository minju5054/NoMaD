# Actual OLD rollout obstacle — 실행 전 고정

기준 `research/isaac6-sudden-obstacle` / `9792056`, 새 branch `research/isaac6-old-rollout-obstacle`. [새 scenario](../research/nomad_isaac/old_rollout_obstacle_scenario.json)는 이전 sudden scenario의 이름과 dynamic 위치 결정 방식만 바꾼다. 기존 정적 geometry, dynamic 크기 (.35,.35,.8) m, tick 970, radius .09 m, margin .02 m, 모델·PD·seed schedule·4/9/72 Hz·1초 timeout을 유지한다. 추가 latency 0 ms, 실제 navigation **1회**, 기술적 실패 포함 재실행 없음.

## 결정적 배치 규칙

Tick 970에서 integration을 마친 **실제 pose**, 그 interval에 적용된 OLD ID와 `(v,w)`, 마지막 controller validity 및 **그 OLD의 실제 receive host time**을 읽는다. 더 최신 packet이 대기 중이어도 OLD의 receive clock으로 age/remaining=1−age를 계산한다. NEW/FRESH output, native prediction 좌표, 이후 pose/goal 결과는 배치 입력으로 사용하지 않는다.

현재 유효 OLD, 남은 timeout>0, v>=.05 m/s가 필요하다. 순서가 고정된 arc length **[.42,.45,.48] m**에 대해 `integrate_se2(pose,v,w,s/v)`의 XY를 후보 중심으로 한다. 중심까지 constant-command lookahead는 3초 이하이며, 이는 **counterfactual**이다. 실제 실행 또는 native 8-point trajectory와 동일시하지 않는다.

최초로 아래 모든 조건을 만족하는 후보 하나만 선택한다.

1. 출현 pose의 원형 footprint clearance >= **.10 m**.
2. 기존 swept 함수로 처음 **.55 s**의 OLD continuation 전체가 새 장애물에 대해 >=.02 m clearance. 이는 .25 s 다음 관측 + .10 s capture + .08 s GPU/IPC + 1/9 s controller + reserve를 위한 사전 budget이다. 인위적 지연이나 실측 보장은 아니며 실제 first-visible/switch delay와 비교한다.
3. **남은 OLD timeout 이내** constant-command arc에서 geometric overlap의 witness가 존재해야 한다. Timeout 뒤까지 가정해야만 생기는 충돌은 채택하지 않는다. 따라서 OLD 명령 유지 가정 자체의 위험을 검사하며 controller timeout을 늘리지 않는다.
4. 같은 remaining-time OLD arc가 기존 정적 장애물에는 >=.02 m clearance이고 corridor 안에 있어야 한다.
5. 중심은 agent 전방(+x)에 있고 absolute bearing <= **35°**. 현재 XY→중심 선분이 정적 장애물에 가리지 않아야 한다. 실제 RGB 포함 여부는 별도 관측 검증이다.
6. 새 box는 복도 안에 완전히 포함되고 기존 box/벽과 **.02 m 이상** 떨어져야 한다.
7. 새 AABB의 네 변 옆 중 적어도 하나에 폭 **.22 m = 2×(.09+.02)**, 양 끝 연장 .11 m의 비어 있는 직사각형 strip이 있어야 한다. Strip 전체가 복도 안에 있고 기존 box와 겹치지 않아야 한다. 이는 국소적 footprint 통과 공간의 기하학적 근거이며, 시작→목표 경로 또는 PD로 실행 가능한 회피의 보증/새 planner가 아니다. Strip이나 배치 rollout은 실제 controller에 전달하지 않는다.

실패 원인을 후보별로 저장한다. 유효 후보가 없거나 OLD가 무효면 **PLACEMENT_INFEASIBLE**로 남기고 장애물 비활성 상태로 종료한다. 위치·tick·seed를 조정하거나 재시도하지 않는다. 관측 전에 새 위치를 찾기 위해 실제 미래 데이터를 참조하지 않는다.

## Thread / scene 일치

72 Hz thread가 tick 970에서 한 번만 결정하고 동일 immutable geometry를 collision monitor와 snapshot message에 게시한다. 이 tick의 state는 배치 결정 후 게시하므로 main thread가 새 tick과 미결 geometry를 함께 읽지 않는다. Execution은 main-thread USD/render/GPU inference를 기다리지 않는다. 배치 계산의 wall time과 pacing 오차를 별도 기록한다.

Main thread는 다음 RGB snapshot 전에 message의 중심을 USD에 반영하고 visibility를 source tick 970부터 활성화한다. Logical simulation timestamp를 기준으로 collision과 rendering 상태가 일치한다. Render update host time과 snapshot tick, 실제 USD AABB를 별도 기록한다. 과거 snapshot은 출현 이전 상태를 유지한다. 초기 hidden placeholder는 배치 후보가 아니며 실제 geometry가 결정되기 전 충돌 검사에 쓰이지 않는다. Initial scene과 resolved scene은 다른 파일로 저장한다.

이번에는 instance annotator를 사용하지 않는다. 원본 RGB의 `R>1.5G, B>1.5G, R>40, B>40`, **20 pixels**를 최초 visible 기준으로 고정하고 RGB 검출 mask임을 명시한다. 모든 출현 전 RGB 검출 수 0, 실제 4-frame history/worker input hash를 확인한다. 이전 instance mask 오류는 수정하지 않는다.

## 분석과 판정

OLD는 출현 직전 실제 applied ID. FRESH는 장애물이 보인 RGB를 history에 포함한 최초 accepted result이며, 실제 적용되지 않으면 B를 만들지 않는다. Native OLD/FRESH는 자기 observation pose로 world 변환한다. Whole/prefix/actual PD execution을 구분하고 seed 차이를 명시한다. OLD continuation은 spawn pose와 원본 command의 timeout-clipped arc이며 actual trajectory와 분리한다.

OLD의 위험 여부는 **controller rollout**을 우선하며 native full/prefix는 별도 보고한다. 실제 FRESH switch 이전 OLD 실행에 충돌이 있으면 `OLD_EXECUTION_COLLISION`; 근거가 유효하면 `UNSAFE_OLD_SAFE_FRESH`, `UNSAFE_OLD_UNSAFE_FRESH`, `OLD_SAFE_FRESH_SAFE`를 구분하고 나머지는 `INSUFFICIENT_EVIDENCE`로 둔다. 후속 FRESH가 안전해졌는지도 기록하되 최초 FRESH를 교체 선정하지 않는다.

기존 `async_handoff_protocol.json`의 correspondence/entry/heading/clearance thresholds를 그대로 사용한다. 안전한 FRESH + 실제 switch + 검사한 entry들의 연결 문제만 Graph 후보의 근거가 된다. Unsafe FRESH, 큰 RMSE, 단순 steering 변화, OLD rollout 충돌만으로 Graph 필요성을 주장하지 않는다. 실제 실행 구간, 관측 기준 prediction, 미실행 connector를 분리한다.

원본 raw와 이전 결과를 보존하며 한 장의 XY 비교 그림만 만든다. Graph/Topomap/smoothing/latency injection/영상/GUI/추가 benchmark는 이번 실행 범위에 없다.
