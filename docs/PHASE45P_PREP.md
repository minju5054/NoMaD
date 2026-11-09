| 항목 | 결과 |
|---|---|
| 등록 | FROZEN |
| 방법 | Phase38 OURS +Phase43-P HMM·공식정지;OURS+HMM |
| 동결 | Phase38 R2/R3·기다림·EC·트리거·지도·실행기;Phase43 HMM·정지 그대로 |
| 장면 | 원래 외관·Topomap;SLW,LC,L2,H1,H2 ×217,219,220 =15회 |
| 배치 | Phase43 같은 seed·jitter |
| 성공 | declared arrival 목표거리≤0.5m AND 충돌없음 |
| 보고 | Phase43 같은15쌍 대비 성공·잘못된정지·충돌·짝차이·R2/R3 설치 |
| 우회 후 오차 | 실제 적용된 R3 종료 뒤10초;설치 뒤10초 별도;관측시점 기준;중복구간은 inference ID 합집합 |
| 미측정 | 관측없음/종료미발생은 n0·NA;진행중 종료 건수 기록 |
| 검증 | 최소테스트3개 PASS /15조합 dry-run PASS |
| 주행·추론 | 0회;smoke생략 |
| Protocol SHA256 | 47c83820cb37b7fac9761ae9861af0bf4a9e3f61945d810ab7d2ea947f9de2a2 |
