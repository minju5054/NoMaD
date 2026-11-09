| 항목 | 결과 |
|---|---|
| 등록 | FROZEN |
| 방법 | Phase41 OURS-DETOUR +42-L forward HMM |
| 본 실행 | 5장면×217,219,220=15회;Phase41 jitter 동일 |
| 후보 창 | 직전 HMM MAP 기준 공식 candidate_range(radius4),양끝포함 H−4..H+5 |
| closest / subgoal | HMM MAP /공식 거리<3이면 다음node,창끝 clamp |
| K | 42-L 동일;관측tick의72Hz누적이동거리 차이/인접node 양의간격 중앙값 |
| 동결 | 공식정지·D750·실행기·EC·회복·필터·지도·신경망/RNG |
| LOC_OK | 잘못된정지≤3/15 AND 성공0.5m≥8 |
| 비교 | Phase41·Phase38 같은15쌍,과거 실행일 |
| 노드 오차 | 영상관측 pose 최근접Topomap XY node;평가 전용 |
| 검증 | 최소테스트5개 PASS;15조합 dry-run PASS |
| 주행/추론 | 0회;smoke생략 |
| Protocol SHA256 | a9ff6b6d891026249b01b1155a761288acc399661206d7dbdb3713615fc2f4e4 |
