| 항목 | 결과 |
|---|---|
| 등록 | FROZEN / 확인 실험 |
| 본 실행 | NOMAD_RAW,OURS-DETOUR,OURS-DETOUR+HMM ×5장면×221–224 =60회 |
| 공통정지 | Phase41 closest_node==goal_node 선언 시 v=ω=0;성공은 거리≤0.5m AND 충돌없음 |
| 위치추정 | 방법1·2 원래 argmin;방법3 Phase43-P HMM 동결 |
| jitter | Phase38 생성식/SeedSequence20261111에 새 seed221–224;블록3방법 동일 배치 |
| 순서 | seed→scene;블록내3방법 RNG20261111 무작위 순열 |
| 주1 | 3 vs2 성공 exact 양측 McNemar |
| 주2 | 2 vs1 충돌 exact 양측 McNemar |
| 통계 | 원 p+주2검정 Holm 보정 p,α0.05;방향/discordant표;20유효짝에서만 기각표시;합성결론 없음 |
| 기술 실패 | 1회 재시도 후 해당 비교의 짝만 제외,대체값 없음 |
| 보조 | 잘못된정지,정지거리,관측pose 기준 추론별노드오차 |
| 기타 | 원래 외관/Topomap·D750·C0-NA·90s·저장v2 유지;첫seed221 전체프레임,cache정리,30GB 중단 |
| 검증 | 최소테스트3개 PASS /60조합 dry-run PASS |
| 실행 | 주행·추론0회;smoke생략 |
| Protocol SHA256 | f9169693c79d561c056bfca150c697459bbc9375dbe9b3f03f79c16c240f8064 |
