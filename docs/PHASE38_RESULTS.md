# Phase38 누적 비교

**NIGHT1_INTERIM — 90/180회**. Protocol SHA256 `18157ad32580a9fc797108c50e77de338d6fdc7b29fec93e87c658ccf6b8f801`. 방법/배치/분석은 실행 전에 동결했다. 이전 phase 결과는 합산하지 않는다.

## 방법×장면 도착·충돌·도착시간

| scene | method | completed | valid | goal | collision | arrival_median_s | technical_failure |
|---|---|---|---|---|---|---|---|
| SLW | NOMAD_RAW | 2 | 2 | 0 | 2 | — | 0 |
| SLW | TE | 2 | 2 | 0 | 2 | — | 0 |
| SLW | RTC | 2 | 2 | 0 | 2 | — | 0 |
| SLW | ASTAR+EC | 2 | 2 | 1 | 0 | 63.153 | 0 |
| SLW | OURS | 2 | 2 | 0 | 0 | — | 0 |
| SLW | TE+EC | 2 | 2 | 1 | 0 | 43.569 | 0 |
| SLW | RTC+EC | 2 | 2 | 0 | 0 | — | 0 |
| SLW | OURS-DETOUR | 2 | 2 | 2 | 0 | 54.778 | 0 |
| SLW | CARE | 2 | 2 | 0 | 1 | — | 0 |
| LC | NOMAD_RAW | 2 | 2 | 2 | 0 | 35.854 | 0 |
| LC | TE | 2 | 2 | 2 | 0 | 28.25 | 0 |
| LC | RTC | 2 | 2 | 2 | 0 | 35.285 | 0 |
| LC | ASTAR+EC | 2 | 2 | 2 | 0 | 30.965 | 0 |
| LC | OURS | 2 | 2 | 2 | 0 | 33.611 | 0 |
| LC | TE+EC | 2 | 2 | 1 | 0 | 28.444 | 0 |
| LC | RTC+EC | 2 | 2 | 2 | 0 | 34.417 | 0 |
| LC | OURS-DETOUR | 2 | 2 | 2 | 0 | 29.854 | 0 |
| LC | CARE | 2 | 2 | 0 | 0 | — | 0 |
| L2 | NOMAD_RAW | 2 | 2 | 0 | 2 | — | 0 |
| L2 | TE | 2 | 2 | 1 | 0 | 73.458 | 0 |
| L2 | RTC | 2 | 2 | 1 | 1 | 66 | 0 |
| L2 | ASTAR+EC | 2 | 2 | 1 | 0 | 72.514 | 0 |
| L2 | OURS | 2 | 2 | 1 | 0 | 81.042 | 0 |
| L2 | TE+EC | 2 | 2 | 1 | 0 | 74.931 | 0 |
| L2 | RTC+EC | 2 | 2 | 1 | 0 | 45.403 | 0 |
| L2 | OURS-DETOUR | 2 | 2 | 2 | 0 | 48.062 | 0 |
| L2 | CARE | 2 | 2 | 0 | 0 | — | 0 |
| H1 | NOMAD_RAW | 2 | 2 | 0 | 2 | — | 0 |
| H1 | TE | 2 | 2 | 2 | 0 | 38.972 | 0 |
| H1 | RTC | 2 | 2 | 0 | 2 | — | 0 |
| H1 | ASTAR+EC | 2 | 2 | 0 | 1 | — | 0 |
| H1 | OURS | 2 | 2 | 0 | 0 | — | 0 |
| H1 | TE+EC | 2 | 2 | 1 | 1 | 33.861 | 0 |
| H1 | RTC+EC | 2 | 2 | 1 | 0 | 44.889 | 0 |
| H1 | OURS-DETOUR | 2 | 2 | 2 | 0 | 43.201 | 0 |
| H1 | CARE | 2 | 2 | 0 | 0 | — | 0 |
| H2 | NOMAD_RAW | 2 | 2 | 1 | 1 | 46.75 | 0 |
| H2 | TE | 2 | 2 | 1 | 0 | 52.181 | 0 |
| H2 | RTC | 2 | 2 | 0 | 0 | — | 0 |
| H2 | ASTAR+EC | 2 | 2 | 2 | 0 | 64.451 | 0 |
| H2 | OURS | 2 | 2 | 1 | 0 | 69.903 | 0 |
| H2 | TE+EC | 2 | 2 | 2 | 0 | 67.472 | 0 |
| H2 | RTC+EC | 2 | 2 | 0 | 0 | — | 0 |
| H2 | OURS-DETOUR | 2 | 2 | 2 | 0 | 50.438 | 0 |
| H2 | CARE | 2 | 2 | 0 | 0 | — | 0 |
| ALL | NOMAD_RAW | 10 | 10 | 3 | 7 | 36.236 | 0 |
| ALL | TE | 10 | 10 | 6 | 2 | 38.972 | 0 |
| ALL | RTC | 10 | 10 | 3 | 5 | 37.486 | 0 |
| ALL | ASTAR+EC | 10 | 10 | 6 | 1 | 54.972 | 0 |
| ALL | OURS | 10 | 10 | 4 | 0 | 52.146 | 0 |
| ALL | TE+EC | 10 | 10 | 6 | 1 | 48.562 | 0 |
| ALL | RTC+EC | 10 | 10 | 4 | 0 | 40.576 | 0 |
| ALL | OURS-DETOUR | 10 | 10 | 10 | 0 | 48.701 | 0 |
| ALL | CARE | 10 | 10 | 0 | 1 | — | 0 |

도착시간은 도착 run만의 중앙값이다. 기술 실패는 아래 표에 보존하고 짝 분석에서 어느 한쪽이 실패하면 해당 비교의 scene×seed 짝을 제외한다. 미관측 충돌을0으로 대체하지 않는다.

## 짝 McNemar exact 및 Holm

| left | right | metric | n | left_only | right_only | p_exact | excluded_pairs | estimable | p_holm | holm_family_size |
|---|---|---|---|---|---|---|---|---|---|---|
| OURS | NOMAD_RAW | success | 10 | 1 | 0 | 1 | 0 | True | 1 | 16 |
| OURS | NOMAD_RAW | collision | 10 | 0 | 7 | 0.015625 | 0 | True | 0.25 | 16 |
| OURS | TE | success | 10 | 1 | 3 | 0.625 | 0 | True | 1 | 16 |
| OURS | TE | collision | 10 | 0 | 2 | 0.5 | 0 | True | 1 | 16 |
| OURS | RTC | success | 10 | 1 | 0 | 1 | 0 | True | 1 | 16 |
| OURS | RTC | collision | 10 | 0 | 5 | 0.0625 | 0 | True | 0.875 | 16 |
| OURS | CARE | success | 10 | 4 | 0 | 0.125 | 0 | True | 1 | 16 |
| OURS | CARE | collision | 10 | 0 | 1 | 1 | 0 | True | 1 | 16 |
| TE | TE+EC | success | 10 | 3 | 3 | 1 | 0 | True | 1 | 16 |
| TE | TE+EC | collision | 10 | 2 | 1 | 1 | 0 | True | 1 | 16 |
| RTC | RTC+EC | success | 10 | 0 | 1 | 1 | 0 | True | 1 | 16 |
| RTC | RTC+EC | collision | 10 | 5 | 0 | 0.0625 | 0 | True | 0.875 | 16 |
| OURS-DETOUR | OURS | success | 10 | 6 | 0 | 0.03125 | 0 | True | 0.46875 | 16 |
| OURS-DETOUR | OURS | collision | 10 | 0 | 0 | 1 | 0 | True | 1 | 16 |
| ASTAR+EC | OURS | success | 10 | 3 | 1 | 0.625 | 0 | True | 1 | 16 |
| ASTAR+EC | OURS | collision | 10 | 1 | 0 | 1 | 0 | True | 1 | 16 |

두 결과(도착/충돌)×8비교=16검정을 한 family로 Holm 보정한다. left_only/right_only는 해당 결과가 왼쪽/오른쪽에만 있는 짝 수다. 밤1은 중간 기술 통계이며, 밤2는 누적 분석이다. 각 누적 report의 Holm 보정은 반복 열람 전체의 순차검정 오류율을 보장하지 않는다.

## 도착 비열등성: OURS−상대

| left | right | n | goal_delta_pp | ci95_low_pp | ci95_high_pp | margin_pp | label | excluded_pairs |
|---|---|---|---|---|---|---|---|---|
| OURS | NOMAD_RAW | 10 | 10 | 0 | 20 | -10 | NONINFERIOR | 0 |
| OURS | TE | 10 | -20 | -40 | 0 | -10 | INCONCLUSIVE | 0 |
| OURS | RTC | 10 | 10 | 0 | 20 | -10 | NONINFERIOR | 0 |
| OURS | ASTAR+EC | 10 | -20 | -50 | 10 | -10 | INCONCLUSIVE | 0 |
| OURS | TE+EC | 10 | -20 | -60 | 20 | -10 | INCONCLUSIVE | 0 |
| OURS | RTC+EC | 10 | 0 | -20 | 20 | -10 | INCONCLUSIVE | 0 |
| OURS | OURS-DETOUR | 10 | -60 | -80 | -40 | -10 | INFERIOR | 0 |
| OURS | CARE | 10 | 40 | 20 | 60 | -10 | NONINFERIOR | 0 |

짝 scene×seed를 장면 내 복원 추출하는20,000회 paired bootstrap(seed20261111), percentile95% CI다. CI 하한≥−10%p이면 NONINFERIOR, 상한<−10%p이면 INFERIOR, 그 외 INCONCLUSIVE. 적은 seed 수의 탐색적 비교로 해석한다. 비열등성 CI는 보정하지 않은 별도 요약이다.

## 짝 차이와 기술 실패

짝별 도착/충돌과 둘 다 도착한 경우 도착시간 차이는 `research/results/phase38/paired.csv`에 있다.

자료 없음

방법 차이·CARE/RTC 원문 차이와 동결 규칙은 [준비 문서](PHASE38_PREP.md)를 따른다. 저장v2,cache정리,30GB 중단,기술실패1회 재시도다.
