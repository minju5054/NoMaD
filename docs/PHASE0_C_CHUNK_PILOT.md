# Phase 0-C — Pure Pursuit chunk execution PILOT

기준 `ab466f9`, 같은 `research/phase0-infrastructure`에서 단일 S0 navigation을 수행한다. 과학적 성능 실험이나 영구 주 실행기 교체 결정이 아니다.

## 실행 전 고정

- 기존 2초/14-node Topomap, S0, seed101+2×request ID, 4/9/72Hz, 추가 지연0, 기존 수신 후1초 timeout.
- Phase0-B `PurePursuit` 코드와 설정 그대로: lookahead .25m, v .2m/s, w ±.4rad/s clipping, endpoint1cm 정지. 결과에 따른 tuning/재시도 없음.
- 각 sample0의 8점만 observation pose로 world 변환한다. Origin 추가, 이전 chunk 연결, switch reanchor, 미래 연장, native yaw/timestamp 생성 없음. 새 FRESH switch에서만 progress 초기화; 동일 chunk의 progress는 비감소한다.
- 중복점은 기존 follower의 인접 중복 제거만 적용한다. 유효 segment가 없으면 해당 chunk 동안 정지한다. 짧은 유효 chunk는 마지막 점으로 target을 clamp한다.
- `--pure-pursuit`는 고정 S0+Topomap의 비동기/추가 지연0에서만 허용한다. 기존 worker/Topomap/PD/follower/geometry 코드는 보존한다.
- 원래 timing core는 유효성·ID·switch를 관리한다. 계산된 index2 PD는 참고 로그만 남기고 적분 명령을 PP로 교체한다. `controller/events`의 `v_m_s,w_rad_s`는 **실행되지 않은 원본 PD 참고값**이고 `applied_v_m_s,applied_w_rad_s` 및 72Hz trace가 **실제 PP 명령**이다.
- 경로 tangent 진단은 동일 B에서 OLD/FRESH 각각의 nearest projection에 해당하는 outgoing segment(끝에서는 incoming)를 사용한다. 20mm 미만은 invalid. 이는 물리적 correspondence나 로봇 yaw 변화가 아니다. 제어에는 사용하지 않는다.
- Geometry는 이미 실행된 구간 평가 및 기존 collision/corridor 종료에만 사용한다. 2cm 위반은 시간 누적하며 명령을 바꾸지 않는다. 새로운 safety/recovery/planner 없음.

고정 설정: `research/nomad_phase0/chunk_pilot_protocol.json`. 사전 최소11 tests PASS. 기존 baseline·14node map·checkpoint·공식 코드·Phase0-B 등343파일 hash를 `artifacts/isaac6/phase0c_preflight_01.json`에 저장했다. Topomap RGB/pose/source hash 검증 PASS. GPU 접근 확인, 새로운 inference/navigation은 아직 미실행이다.

출력은 새 `artifacts/isaac6/phase0c_pure_pursuit_01/`에 보존한다. 동일 seed여도 다른 실제 경로의 RGB와 prediction이 달라지므로 저장된 `topomap_static_2s_01`과는 비paired 참고 비교다.

이번 PILOT에서 후진 recovery는 비활성, 안전 정보는 oracle geometry의 사후 평가, upstream은 NoMaD navigation policy로 고정한다. 영구 주 실행기 선택과 전체 연구 정책을 이번 단일 실행으로 결정하지 않는다.
