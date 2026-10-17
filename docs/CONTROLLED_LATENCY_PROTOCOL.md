# Controlled result-delivery latency — 실행 전 protocol

2026-10-17, 기준 `671ea9732125be10d38b04d31d5ad03fe1723e85`, 새 branch `research/isaac6-controlled-latency`. [기계 판독 protocol](../research/nomad_isaac/controlled_latency_protocol.json).

기존 `two_obstacles_wide_wall_scenario.json`을 그대로 사용한다. Start/goal, 두 장애물, 9 cm footprint/2 cm clearance, seed schedule, fixed-goal adapter, 4/9/72 Hz, 1초 timeout, sample 0/index 2, model/checkpoint/diffusion/원본 PD를 변경하지 않는다. `async_wide_wall_01`은 저장 baseline으로만 사용한다. 새 bounded navigation은 **1회**, 출력은 `../artifacts/isaac6/controlled_latency_01/`이다. 조건 미도달·navigation 실패를 이유로 재시도하지 않는다.

첫 **accepted request** 중 observation pose의 world X가 **[2.1, 2.4] m (양 끝 포함)**, 저장된 `old_valid_at_observation=true`, `old_id_at_observation>=0`, 아직 trigger되지 않은 요청 한 개만 선택한다. 이는 request ID 조건이 아니다. Busy 중 history만 갱신한 observation은 trigger를 소비하지 않는다. 유효 여부는 실제 controller가 현재 실행 중인 command 상태이며 미래 결과를 사용하지 않는다.

GPU inference/출력 저장/packet 수신을 완료한 뒤 IPC thread에서만 `packet_received_monotonic_ns + 500,000,000 ns`까지 기다린다. 실행 및 controller thread는 기다리지 않는다. Single outstanding 상태는 전달·소비까지 유지한다. `t_packet_received`와 `t_release`를 분리하며 기존 controller가 사용하는 `received_monotonic_ns`는 controller 쪽 inbox에 공개되는 **release 시각의 alias**다. OLD의 수신/만료 시각은 변경하지 않고, FRESH는 release부터 1초 유효하다. 지연은 **post-inference result-delivery latency**이며 GPU inference latency가 아니다. 지연 옵션이 없으면 기존 동작을 보존한다.

**B0**는 추가 지연 이전 packet 수신 직후 첫 실제 controller refresh의 기록 pose다. 그 tick의 OLD가 유효해야 하며 불충분하면 판정을 보류한다. **B_delay**는 해당 FRESH의 실제 최초 적용 pose다. B0는 동일 run의 OLD 실행 기록이며, B0에서 FRESH로 전환한 가상 주행을 생성하지 않는다. 실제 switch가 없으면 B_delay=null이며 미적용을 적용 성공으로 세지 않는다.

기존 `async_handoff_protocol.json` 수치와 `handoff_audit.py`의 correspondence, boundary entries, path safety, classify를 그대로 쓴다. 각 OLD/FRESH는 자신의 observation pose에 고정하고, 동일 pair에 대해 B0/B_delay 각각 기존 규칙을 평가한다. 같은 waypoint index 대응, native yaw/timestamp, switch re-anchor는 도입하지 않는다. Boundary에 따라 forward overlap의 범위가 달라질 수 있음을 기록한다.

OLD 실행은 packet 수신부터 실제 delayed switch/종료까지 기존 swept clearance로 평가한다. Window 경계를 걸치는 실제 integration interval도 보수적으로 포함한다. Clearance <0.02 m 또는 corridor clearance<=0이면 **OLD_EXECUTION_RISK**를 우선 보고하며, 별도로 B0/B_delay geometric class와 FRESH full/native prefix(0→1→2)/observation-origin prefix 안전성을 모두 보존한다. Actual OLD 위험을 safe FRESH 연결 실패나 Graph의 해결 가능성으로 바꾸어 주장하지 않는다. FRESH 적용 후 다음 handoff/종료까지 실제 실행도 따로 검사한다.

기존 class는 `ALREADY_CONSISTENT`, `STAGING_SUFFICIENT`, `UNSAFE_FRESH`, `POTENTIAL_RECONCILIATION_CASE`, `INSUFFICIENT_EVIDENCE`다. 큰 RMSE/heading만으로 후보를 만들지 않는다. Graph 후보 판정은 safe FRESH와 충분한 correspondence가 있으나 검사한 entry/connector 모두 안전하지 않은 경우로 제한한다. 유한 staging family 실패가 Graph 성능이나 일반적 feasibility 증명은 아니다.

Synthetic trigger/deadline/OLD timeout/queue ordering 검증 후 clean commit으로 한 번 실행한다. 기존 pacing threshold(p95<=1/72 s, max<=4/72 s, RTF error<=2%)도 유지한다. Injection, 실제 OLD 이동, B0/B_delay, 원본 계산·raw 보존과 pacing을 검증하고 결과를 CSV/JSON 및 비교 그림 **1장**으로 저장한다. 새 GUI/영상/Graph/Topomap/latency sweep은 없다. Baseline과의 전체 주행 차이는 RGB·sampling 차이가 섞이므로 지연만의 인과 효과로 주장하지 않는다.
