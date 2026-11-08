# Phase38 누적 비교

**COMPLETE — 180/180회**. Protocol SHA256 `18157ad32580a9fc797108c50e77de338d6fdc7b29fec93e87c658ccf6b8f801`. 방법/배치/분석은 실행 전에 동결했다. 이전 phase 결과는 합산하지 않는다.

## 방법×장면 도착·충돌·도착시간

| scene | method | completed | valid | goal | collision | arrival_median_s | technical_failure |
|---|---|---|---|---|---|---|---|
| SLW | NOMAD_RAW | 4 | 4 | 0 | 4 | — | 0 |
| SLW | TE | 4 | 4 | 1 | 3 | 66.972 | 0 |
| SLW | RTC | 4 | 4 | 1 | 3 | 68.278 | 0 |
| SLW | ASTAR+EC | 4 | 4 | 2 | 0 | 70.806 | 0 |
| SLW | OURS | 4 | 4 | 1 | 0 | 43.375 | 0 |
| SLW | TE+EC | 4 | 4 | 2 | 1 | 51.028 | 0 |
| SLW | RTC+EC | 4 | 4 | 1 | 0 | 70.208 | 0 |
| SLW | OURS-DETOUR | 4 | 4 | 2 | 0 | 54.778 | 0 |
| SLW | CARE | 4 | 4 | 0 | 1 | — | 0 |
| LC | NOMAD_RAW | 4 | 4 | 4 | 0 | 35.854 | 0 |
| LC | TE | 4 | 4 | 3 | 0 | 28.292 | 0 |
| LC | RTC | 4 | 4 | 4 | 0 | 33.521 | 0 |
| LC | ASTAR+EC | 4 | 4 | 3 | 0 | 31.514 | 0 |
| LC | OURS | 4 | 4 | 4 | 0 | 32.91 | 0 |
| LC | TE+EC | 4 | 4 | 3 | 0 | 28.444 | 0 |
| LC | RTC+EC | 4 | 4 | 3 | 0 | 32.569 | 0 |
| LC | OURS-DETOUR | 4 | 4 | 4 | 0 | 29.507 | 0 |
| LC | CARE | 4 | 4 | 0 | 0 | — | 0 |
| L2 | NOMAD_RAW | 4 | 4 | 1 | 3 | 47.778 | 0 |
| L2 | TE | 4 | 4 | 2 | 0 | 61.896 | 0 |
| L2 | RTC | 4 | 4 | 2 | 1 | 59.507 | 0 |
| L2 | ASTAR+EC | 4 | 4 | 2 | 0 | 60.278 | 0 |
| L2 | OURS | 4 | 4 | 3 | 0 | 49.361 | 0 |
| L2 | TE+EC | 4 | 4 | 2 | 0 | 80.181 | 0 |
| L2 | RTC+EC | 4 | 4 | 3 | 0 | 58.528 | 0 |
| L2 | OURS-DETOUR | 4 | 4 | 2 | 0 | 48.062 | 0 |
| L2 | CARE | 4 | 4 | 1 | 0 | 85.778 | 0 |
| H1 | NOMAD_RAW | 4 | 4 | 2 | 2 | 29.868 | 0 |
| H1 | TE | 4 | 4 | 3 | 1 | 38.028 | 0 |
| H1 | RTC | 4 | 4 | 2 | 2 | 46.375 | 0 |
| H1 | ASTAR+EC | 4 | 4 | 2 | 1 | 30.694 | 0 |
| H1 | OURS | 4 | 4 | 2 | 0 | 31.861 | 0 |
| H1 | TE+EC | 4 | 4 | 2 | 1 | 32.417 | 0 |
| H1 | RTC+EC | 4 | 4 | 3 | 0 | 44.889 | 0 |
| H1 | OURS-DETOUR | 4 | 4 | 4 | 0 | 43.201 | 0 |
| H1 | CARE | 4 | 4 | 0 | 0 | — | 0 |
| H2 | NOMAD_RAW | 4 | 4 | 1 | 3 | 46.75 | 0 |
| H2 | TE | 4 | 4 | 1 | 2 | 52.181 | 0 |
| H2 | RTC | 4 | 4 | 0 | 1 | — | 0 |
| H2 | ASTAR+EC | 4 | 4 | 3 | 0 | 82.111 | 0 |
| H2 | OURS | 4 | 4 | 2 | 0 | 70.556 | 0 |
| H2 | TE+EC | 4 | 4 | 3 | 0 | 81.389 | 0 |
| H2 | RTC+EC | 4 | 4 | 0 | 0 | — | 0 |
| H2 | OURS-DETOUR | 4 | 4 | 3 | 0 | 48.306 | 0 |
| H2 | CARE | 4 | 4 | 0 | 0 | — | 0 |
| ALL | NOMAD_RAW | 20 | 20 | 8 | 12 | 35.854 | 0 |
| ALL | TE | 20 | 20 | 10 | 6 | 38.972 | 0 |
| ALL | RTC | 20 | 20 | 9 | 7 | 45.972 | 0 |
| ALL | ASTAR+EC | 20 | 20 | 12 | 1 | 47.417 | 0 |
| ALL | OURS | 20 | 20 | 12 | 0 | 38.882 | 0 |
| ALL | TE+EC | 20 | 20 | 12 | 2 | 48.562 | 0 |
| ALL | RTC+EC | 20 | 20 | 10 | 0 | 45.146 | 0 |
| ALL | OURS-DETOUR | 20 | 20 | 15 | 0 | 47.028 | 0 |
| ALL | CARE | 20 | 20 | 1 | 1 | 85.778 | 0 |

도착시간은 도착 run만의 중앙값이다. 기술 실패는 아래 표에 보존하고 짝 분석에서 어느 한쪽이 실패하면 해당 비교의 scene×seed 짝을 제외한다. 미관측 충돌을0으로 대체하지 않는다.

## 짝 McNemar exact 및 Holm

| left | right | metric | n | left_only | right_only | p_exact | excluded_pairs | estimable | p_holm | holm_family_size |
|---|---|---|---|---|---|---|---|---|---|---|
| OURS | NOMAD_RAW | success | 20 | 4 | 0 | 0.125 | 0 | True | 1 | 16 |
| OURS | NOMAD_RAW | collision | 20 | 0 | 12 | 0.00048828 | 0 | True | 0.0078125 | 16 |
| OURS | TE | success | 20 | 5 | 3 | 0.72656 | 0 | True | 1 | 16 |
| OURS | TE | collision | 20 | 0 | 6 | 0.03125 | 0 | True | 0.375 | 16 |
| OURS | RTC | success | 20 | 3 | 0 | 0.25 | 0 | True | 1 | 16 |
| OURS | RTC | collision | 20 | 0 | 7 | 0.015625 | 0 | True | 0.21875 | 16 |
| OURS | CARE | success | 20 | 11 | 0 | 0.00097656 | 0 | True | 0.014648 | 16 |
| OURS | CARE | collision | 20 | 0 | 1 | 1 | 0 | True | 1 | 16 |
| TE | TE+EC | success | 20 | 4 | 6 | 0.75391 | 0 | True | 1 | 16 |
| TE | TE+EC | collision | 20 | 6 | 2 | 0.28906 | 0 | True | 1 | 16 |
| RTC | RTC+EC | success | 20 | 2 | 3 | 1 | 0 | True | 1 | 16 |
| RTC | RTC+EC | collision | 20 | 7 | 0 | 0.015625 | 0 | True | 0.21875 | 16 |
| OURS-DETOUR | OURS | success | 20 | 6 | 3 | 0.50781 | 0 | True | 1 | 16 |
| OURS-DETOUR | OURS | collision | 20 | 0 | 0 | 1 | 0 | True | 1 | 16 |
| ASTAR+EC | OURS | success | 20 | 4 | 4 | 1 | 0 | True | 1 | 16 |
| ASTAR+EC | OURS | collision | 20 | 1 | 0 | 1 | 0 | True | 1 | 16 |

두 결과(도착/충돌)×8비교=16검정을 한 family로 Holm 보정한다. left_only/right_only는 해당 결과가 왼쪽/오른쪽에만 있는 짝 수다. 밤1은 중간 기술 통계이며, 밤2는 누적 분석이다. 각 누적 report의 Holm 보정은 반복 열람 전체의 순차검정 오류율을 보장하지 않는다.

## 도착 비열등성: OURS−상대

| left | right | n | goal_delta_pp | ci95_low_pp | ci95_high_pp | margin_pp | label | excluded_pairs |
|---|---|---|---|---|---|---|---|---|
| OURS | NOMAD_RAW | 20 | 20 | 5 | 35 | -10 | NONINFERIOR | 0 |
| OURS | TE | 20 | 10 | -15 | 35 | -10 | INCONCLUSIVE | 0 |
| OURS | RTC | 20 | 15 | 5 | 30 | -10 | NONINFERIOR | 0 |
| OURS | ASTAR+EC | 20 | 0 | -25 | 25 | -10 | INCONCLUSIVE | 0 |
| OURS | TE+EC | 20 | 0 | -30 | 35 | -10 | INCONCLUSIVE | 0 |
| OURS | RTC+EC | 20 | 10 | -10 | 30 | -10 | NONINFERIOR | 0 |
| OURS | OURS-DETOUR | 20 | -15 | -40 | 10 | -10 | INCONCLUSIVE | 0 |
| OURS | CARE | 20 | 55 | 35 | 75 | -10 | NONINFERIOR | 0 |

짝 scene×seed를 장면 내 복원 추출하는20,000회 paired bootstrap(seed20261111), percentile95% CI다. CI 하한≥−10%p이면 NONINFERIOR, 상한<−10%p이면 INFERIOR, 그 외 INCONCLUSIVE. 적은 seed 수의 탐색적 비교로 해석한다. 비열등성 CI는 보정하지 않은 별도 요약이다.

## 짝 차이와 기술 실패

짝별 도착/충돌과 둘 다 도착한 경우 도착시간 차이는 `research/results/phase38/paired.csv`에 있다.

자료 없음

방법 차이·CARE/RTC 원문 차이와 동결 규칙은 [준비 문서](PHASE38_PREP.md)를 따른다. 저장v2,cache정리,30GB 중단,기술실패1회 재시도다.
