# Async OLD/FRESH audit — 실행 전 분석 규칙

2026-10-16. 기준 `929a9dcf2595b876656729134740df9dcadb83c4`, 성공한 `async_wide_wall_01`의 저장 기록만 분석한다. Pair metric 계산 전에 이 규칙을 commit한다. 기존 [handoff protocol](HANDOFF_AUDIT_PROTOCOL.md)의 수치 threshold 및 `correspondence`, `path_safety`, `boundary_entries`, `classify`를 그대로 재사용한다. 새 inference/navigation/graph/latency injection은 없다.

## 대상 및 무결성

- 실제 switch event의 인접 두 개를 OLD/FRESH로 정의한다. 최초 적용은 OLD가 없는 initialization이며 제외한다. 수신됐지만 switch되지 않은 ID는 별도 목록으로 기록한다. 전체 주행 종료까지 분석하며 이번에는 과거 sync run의 argmin cutoff를 사용하지 않는다.
- 이미 알려진 inventory는 95 predictions, 94 switch events다. 분석 대상은 93 handoff, terminal unswitched ID 94는 제외한다. 성공한 baseline의 goal entry 및 무충돌 사실은 유지한다.
- 지정 base commit에 저장된 `research/results/isaac6_async_wide_wall_20261016/input_hashes.json`과 summary/review를 대조한다. 사용한 모든 입력을 분석 전후 hash 비교한다. 실행 provenance source hash는 실행 Git SHA 및 현재 source와 비교한다. 과거 hash가 없는 추가 로그의 hash는 이번 분석 baseline으로 구분한다.
- Fixed-goal adapter를 유지한다. Topomap이 없으며, waypoint intrinsic time/native yaw를 만들지 않는다. 모델/checkpoint를 import/load하지 않는다.

## Clock, pose, 실제 motion

- 각 trajectory는 자신의 저장 observation pose로 world 변환한다. B는 실제 FRESH switch tick pose다. FRESH path를 B로 re-anchor하지 않는다.
- `t_obs`는 host monotonic capture-start, `observation_sim_s`는 저장 pose snapshot tick이다. Snapshot age를 기록한다. Ready는 GPU 완료 monotonic, switch는 controller tick의 monotonic/simulation이다. Host 시간끼리만 빼고, simulation tick끼리만 뺀다. Ready의 simulation pose/time을 임의로 생성하지 않는다.
- Observation snapshot→switch의 실제 pose intervals에서 path distance `sum(abs(v)*dt)`와 wrapped incremental yaw 합을 계산한다. 총 이동과 직전 적용 OLD ID의 유효 command가 만든 이동을 구분한다. 다른 ID/invalid step이 있으면 별도로 센다. Pose shift는 boundary−observation translation 및 wrapped yaw다.
- Capture-start 이후 양 끝 host timestamp가 모두 window에 포함된 OLD whole intervals도 보수적 수치로 병기한다. GPU inference start/end 안의 OLD whole intervals는 기존 `async_report.py` 정의를 재사용한다. 보간한 움직임이나 artificial latency를 실제 측정처럼 보고하지 않는다.
- FRESH 적용 tick부터 다음 실제 switch tick(마지막은 종료 tick)까지 저장된 각 72 Hz interval을 원본 command로 재검증하고 swept clearance/corridor containment를 평가한다. Original controller가 offline connector를 실행했다고 주장하지 않는다.

## 기하학과 분류

- Native points 0..7의 full path 및 points 0..2 prefix를 각각 평가한다. Observation origin을 추가한 planning full/prefix도 따로 검증한다. Whole-path safety와 실제 selected waypoint 실행 안전성을 구분한다. 원점→point 0은 native tangent로 사용하지 않는다.
- 공통 B-forward station >=0.10 m, strictly increasing station >1e−6 m, 0.01 m 이하 resampling, segment length>=0.02 m, heading validity>=80%를 유지한다. Equal-index 대응은 하지 않는다. Longitudinal/lateral revision은 공통 forward interval에서 잘라 같은 arclength progress를 비교한 proxy다. Invalid correspondence는 mismatch 분포에서 제외하고 별도 count/reason을 남긴다.
- Entry는 native 0→1→2의 유효 segment들에 대한 B projection/끝점/1 cm grid로 한정한다. Nearest 및 안전한 후보 중 nearest를 모두 저장한다. 미래 executed pose로 entry를 고르지 않는다.
- 연결은 B 제자리 회전→entry 직선→tangent 제자리 회전인 **미실행 diagnostic**이다. 원형 footprint로 제자리 회전이 가능하므로 큰 yaw 차이만으로 불가능하다고 하지 않는다. Obstacle clearance>=0.02 m, corridor>0을 요구한다.
- 원본 controller는 수신한 local point를 그대로 사용한다. Observation-anchored selected world point와 `B에서 같은 local point를 표현한 world point`의 차이를 기록한다. 후자는 controller의 순간적 body-local 의미를 보여주는 점일 뿐, FRESH trajectory를 re-anchor한 분석이나 새로운 제어 입력이 아니다. Anchored point를 B-local로 표현한 좌표도 비교한다.
- 기존 순서 유지: full FRESH unsafe→`UNSAFE_FRESH`; correspondence/entry invalid→`INSUFFICIENT_EVIDENCE`; nearest safe, distance<=0.10 m, 세 각도<=30°→`ALREADY_CONSISTENT`; 그 외 safe connector 존재→`STAGING_SUFFICIENT`; safe FRESH 및 valid evidence이지만 검사한 모든 connectors unsafe→`POTENTIAL_RECONCILIATION_CASE`.
- 큰 RMSE, steering 변화, 큰 yaw 차이만으로 candidate를 만들지 않는다. Candidate는 검사한 연결 family의 한계이며 다른 연결/Graph의 필요성 또는 우월성 증명이 아니다.
- Candidate가 있으면 기존 순위(best available obstacle clearance 오름차순, FRESH ID)로 최대 3개를 한 그림에 표시한다. 없으면 그림을 생략한다. Candidate 없음 + classifiable>=90%면 `NO_QUALIFIED_CANDIDATE`, 그보다 낮으면 `INSUFFICIENT_EVIDENCE`다.
- 장애물 구간은 기존 규칙대로 B.x 기준 expanded near/far ±0.50 m: approach/pass/departure. 미래 통과 결과로 구간이나 후보를 고르지 않는다. 두 window 중복은 허용하고 전체 pair count와 혼동하지 않는다.

Prediction마다 initial/DDPM seed가 달라 observation 변화와 sampling 영향을 분리할 수 없다. 이 audit는 한 번의 성공한 fixed-goal kinematic baseline에 대한 문제 존재성 조사다. Negative result이면 controlled latency 실험 필요성을 제안만 하고 이번에는 실행하지 않는다.
