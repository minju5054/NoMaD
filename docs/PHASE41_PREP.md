| 항목 | 결과 |
|---|---|
| 등록 | FROZEN |
| 본 실행 | OURS-DETOUR ×SLW,LC,L2,H1,H2 ×217,219,220 =15회 |
| smoke | 생략 |
| 공통 옵션 | nomad_goal_stop: closest_node==goal_node 수신 시 v=ω=0,즉시종료 |
| 시점 | D750 유지;결과 수신 첫72Hz tick,9Hz 제어까지 기다리지 않음 |
| 기존 거리 종료 | 옵션ON에서만 비활성;목표거리 평가 전용 |
| 주 성공 | declared arrival AND 목표거리≤0.5m AND 충돌없음 |
| 보조 | 0.3m/1.0m 성공,잘못된정지>0.5m,선언없이시간초과 |
| 비교 | 같은15쌍의 Phase38 OURS-DETOUR,기존0.3m규칙·다른실행일 |
| 검증 | 테스트4개 PASS /15조합 dry-run PASS |
| 실행횟수 | 0 |
| 여유공간 | 1150.5GB |
| Protocol SHA256 | 3bd94c578cb18be8fb1095046763ad42e19082d21c84ce54356e78117707df4c |
