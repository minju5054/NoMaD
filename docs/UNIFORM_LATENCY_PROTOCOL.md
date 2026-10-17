# Full-run uniform latency — 실행 전 고정

2026-10-17. 기준 `6eedeebf29482a9ada617a3ad774521983d2a8a7`, 새 branch `research/isaac6-uniform-latency`. [기계 판독 protocol](../research/nomad_isaac/uniform_latency_protocol.json).

기존 `two_obstacles_wide_wall_scenario.json`, model/checkpoint/diffusion/seed schedule, sample 0/index 2, 원본 PD, coordinate/clearance 함수, 9 cm footprint/2 cm safety margin, 4/9/72 Hz, 1초 timeout, fixed-goal adapter를 유지한다. 기존 성공 `async_wide_wall_01`을 **D0 참고 baseline**으로 재사용하며 새로 실행하지 않는다.

**D250→D500→D750 순서로 각각 1회** 정상 주행한다. 출력은 `../artifacts/isaac6/uniform_d250_01/`, `uniform_d500_01/`, `uniform_d750_01/`이며 존재하면 덮어쓰지 않는다. 조건·seed·장애물은 결과를 본 뒤 바꾸지 않는다. Navigation 실패/trigger 미도달과 무관하게 해당 조건을 반복하지 않는다. 기술적 실행 실패도 보존하고 자동 재시도하지 않는다.

Uniform mode는 최초부터 종료 후 drain되는 terminal-unapplied result까지 **모든 accepted inference result**에 설정 d를 적용한다. GPU inference와 packet 수신을 완료한 뒤 IPC thread만 packet+ d monotonic deadline까지 기다린다. 72 Hz execution/9 Hz controller는 계속 실행하고 busy 상태의 4 Hz observation은 history만 최신화한다. Pending FRESH는 OLD 수신 시각을 갱신하지 않는다. `received_monotonic_ns`는 실제 release의 alias이고 FRESH의 1초 validity는 release부터다. 기존 single-trigger option은 별도로 유지하며 두 옵션 동시 사용은 금지한다.

모든 실제 switch를 이전 actual switch와 pair로 만들고 초기 적용은 제외한다. Goal 실패 후에도 종료까지 기록된 pair를 분석한다. 수신됐지만 적용되지 않은 result는 기다리는 동안의 OLD 안전성을 별도 기록하고 B를 만들지 않는다. 모든 path는 자기 observation pose에 고정한다.

`async_report.validate`의 기존 runtime 검증 및 `async_handoff_audit`의 motion/selected-point helpers, 기존 correspondence/entry/path safety/classify와 numeric thresholds를 재사용한다. Native full 8-point, native prefix 0→1→2, observation-origin prefix를 구분한다. Actual FRESH 실행은 switch→다음 switch/종료의 swept interval로 평가한다.

**OLD_EXECUTION_RISK**는 observation부터 result release/주행 종료까지 실제 OLD-associated interval의 swept clearance <0.02 m 또는 corridor clearance<=0인 경우다. Window 경계를 걸치는 interval은 보수적으로 포함하고 incoming FRESH interval은 제외한다. Timeout으로 zero command가 된 OLD-associated interval도 안전성 검사에는 포함한다. 움직임은 유효 OLD command만 합한다. Actual wait 전체, GPU inference 완전 intervals, packet→release 완전 intervals를 따로 기록한다. Release 후 switch 전의 OLD interval 안전성도 따로 보존한다.

Observed OLD risk와 geometric class는 별개 필드이며 combined class에서는 OLD risk를 우선한다. FRESH가 직접 unsafe인 판정은 correspondence와 무관한 footprint geometry 근거다. Safe FRESH인데 correspondence/heading 근거가 부족하면 `INSUFFICIENT_EVIDENCE`; 이를 consistent/staging/candidate로 바꾸지 않는다. 기존 `ALREADY_CONSISTENT`, `STAGING_SUFFICIENT`, `UNSAFE_FRESH`, `POTENTIAL_RECONCILIATION_CASE` 기준을 유지한다. 큰 mismatch나 실제 충돌만으로 Graph 후보를 만들지 않는다.

Candidate가 없고 기존 classifiable fraction 기준 90%를 충족하면 `NO_QUALIFIED_CANDIDATE`, 근거가 더 부족하면 `INSUFFICIENT_EVIDENCE`로 보류한다. Candidate가 있을 때도 실제 OLD collision, unsafe prediction 및 미실행 connector의 위험을 구분한다. 동일 run 내에서 실행된 RAW PD만 실측이며 staging/Graph closed-loop 비교는 하지 않는다.

최소 synthetic uniform delay 검증 후 clean commit에서 3회 실행한다. Pacing의 기존 p95<=1/72 s, max<=4/72 s, RTF error<=2% 기준을 유지한다. CSV/JSON/간결한 비교 보고서만 추가하고 GUI/영상/추가 figure/Graph/Topomap은 만들지 않는다. D0와 신규 run의 RGB·관측 시점·sampling 대응·코드 차이를 인정하며 단일 시행 간 성능 차이를 paired causal effect로 주장하지 않는다.
