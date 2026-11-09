| 항목 | 결과 |
|---|---|
| 등록 | FROZEN |
| 방법 | Phase45에서 A·R2만 OFF;B→R3 동결 |
| ALL_UNSAFE | OURS-DETOUR와 동일 fallback;별도로 B가 충족하면 B→R3는 허용 |
| 본 실행 | SLW,LC,L2,H1,H2 ×217,219,220 =15회;같은 jitter·원래 외관 |
| 비교군 | Phase43-P·45-P 같은15쌍 재사용 |
| B_ONLY_OK | 성공0.5m≥11 AND 충돌≤1 AND (Phase43대비 Graph만성공−반대)≥2 |
| 추가 분석 | 발동 component셀 중심→이미 출현한 실제상자 XY 경계 최소거리≤0.3m;oracle은 종료 후만 사용 |
| 거짓 발동 | NON_BOX 수·그 뒤 R3수락/설치/종료사유·최종 run결과;과거 지도누락은 UNMEASURED |
| 대기 시간 | 계산대기(REPAIR_WAIT+DETOUR_WAIT),STOP_WAIT,실제 정지 시간 분리 |
| 검증 | 최소테스트4개 PASS /15조합 dry-run PASS |
| 주행·추론 | 0회;smoke생략 |
| Protocol SHA256 | c6ae779218bf372e6540202807ebd94cc8eee2bcbe0c3b25d2b3135d913aab0d |
