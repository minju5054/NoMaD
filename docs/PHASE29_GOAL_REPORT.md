최종 라벨: G18_NOT_SUPPORTED
완료: {'confirm': 60, 'dev': 20, 'smoke': 2} (본 실행 순차, smoke 제외)
dev G18/NA 도착 5/5, 충돌 3/3, G18 적용 317/447
멈춘 단계: confirm — All registered stages complete
수치·정책·평가기·이전 결과 보존; 확인 실험은 dev gate 통과한 경우에만 실행.

# Phase29 경로–속도 분해

| stage | scene | method | n | valid | goal | collision | goal_time_s | mean_speed_m_s | stop_fraction | minimum_clearance_m | omega_saturation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | SLW | C0 | 2 | 2 | 0 | 0 | — | 0.0588 | 0.6716 | 0.08967 | 0.5883 |
| dev | SLW | C0-NA | 2 | 2 | 0 | 1 | — | 0.09592 | 0.4107 | 0.003266 | 0.3757 |
| dev | SLW | SM | 2 | 2 | 1 | 0 | 65.44 | 0.09956 | 0.253 | 0.04689 | 0.3053 |
| dev | SLW | G18 | 2 | 2 | 0 | 2 | — | 0.09248 | 0.3758 | -0.000153 | 0.423 |
| dev | LC | C0 | 2 | 2 | 2 | 0 | 37.8 | 0.1413 | 0.2851 | 0.1534 | 0.3624 |
| dev | LC | C0-NA | 2 | 2 | 1 | 1 | 26.47 | 0.1804 | 0.1623 | 0.08792 | 0.5144 |
| dev | LC | SM | 2 | 2 | 2 | 0 | 36.86 | 0.1422 | 0.136 | 0.1658 | 0.2405 |
| dev | LC | G18 | 2 | 2 | 2 | 0 | 32.93 | 0.1623 | 0.1215 | 0.1552 | 0.3241 |
| dev | L2 | C0 | 2 | 2 | 2 | 0 | 54.09 | 0.161 | 0.2271 | 0.1368 | 0.473 |
| dev | L2 | C0-NA | 2 | 2 | 2 | 0 | 49.13 | 0.1748 | 0.1413 | 0.08028 | 0.4646 |
| dev | L2 | SM | 2 | 2 | 1 | 0 | 64.96 | 0.1279 | 0.1864 | 0.07324 | 0.3453 |
| dev | L2 | G18 | 2 | 2 | 0 | 0 | — | 0.1352 | 0.1395 | 0.07033 | 0.3142 |
| dev | H1 | C0 | 2 | 2 | 1 | 1 | 29.99 | 0.148 | 0.2974 | 0.07147 | 0.3509 |
| dev | H1 | C0-NA | 2 | 2 | 2 | 0 | 31.78 | 0.172 | 0.1521 | 0.0932 | 0.437 |
| dev | H1 | SM | 2 | 2 | 1 | 0 | 38.35 | 0.1238 | 0.1524 | 0.06148 | 0.3392 |
| dev | H1 | G18 | 2 | 2 | 1 | 1 | 34.56 | 0.1747 | 0.1233 | 0.02377 | 0.3371 |
| dev | H2 | C0 | 2 | 2 | 1 | 0 | 54.93 | 0.1491 | 0.2641 | 0.03962 | 0.4147 |
| dev | H2 | C0-NA | 2 | 2 | 0 | 1 | — | 0.1606 | 0.189 | 0.02847 | 0.4826 |
| dev | H2 | SM | 2 | 2 | 1 | 0 | 68.65 | 0.1268 | 0.1644 | 0.09736 | 0.2962 |
| dev | H2 | G18 | 2 | 2 | 2 | 0 | 62.46 | 0.1564 | 0.1338 | 0.04774 | 0.3514 |
| confirm | SLW | C0 | 3 | 3 | 2 | 0 | 55.77 | 0.1095 | 0.4282 | 0.0544 | 0.4605 |
| confirm | SLW | C0-NA | 3 | 3 | 2 | 1 | 55.51 | 0.1251 | 0.3495 | 0.008062 | 0.3016 |
| confirm | SLW | SM | 3 | 3 | 2 | 0 | 66.67 | 0.09842 | 0.2533 | 0.04097 | 0.3312 |
| confirm | SLW | G18 | 3 | 3 | 2 | 0 | 54.9 | 0.1015 | 0.3746 | 0.002667 | 0.3267 |
| confirm | LC | C0 | 3 | 3 | 2 | 0 | 53.6 | 0.1222 | 0.3262 | 0.1284 | 0.462 |
| confirm | LC | C0-NA | 3 | 3 | 2 | 0 | 29.64 | 0.1797 | 0.1274 | 0.1726 | 0.5241 |
| confirm | LC | SM | 3 | 3 | 2 | 0 | 40.3 | 0.13 | 0.1057 | 0.1327 | 0.3228 |
| confirm | LC | G18 | 3 | 3 | 3 | 0 | 29.1 | 0.1828 | 0.09928 | 0.1797 | 0.3433 |
| confirm | L2 | C0 | 3 | 3 | 2 | 0 | 54.51 | 0.1604 | 0.2579 | 0.05718 | 0.5051 |
| confirm | L2 | C0-NA | 3 | 3 | 1 | 0 | 48.86 | 0.1623 | 0.1901 | 0.02995 | 0.4556 |
| confirm | L2 | SM | 3 | 3 | 2 | 0 | 59.08 | 0.1347 | 0.1195 | 0.1098 | 0.2831 |
| confirm | L2 | G18 | 3 | 3 | 3 | 0 | 48.24 | 0.1776 | 0.1297 | 0.1367 | 0.357 |
| confirm | H1 | C0 | 3 | 3 | 3 | 0 | 34.33 | 0.1582 | 0.2296 | 0.09777 | 0.4203 |
| confirm | H1 | C0-NA | 3 | 3 | 3 | 0 | 31.49 | 0.1747 | 0.1587 | 0.04764 | 0.4905 |
| confirm | H1 | SM | 3 | 3 | 2 | 1 | 36.14 | 0.1405 | 0.1453 | 0.126 | 0.2607 |
| confirm | H1 | G18 | 3 | 3 | 3 | 0 | 35.33 | 0.1572 | 0.1757 | 0.1081 | 0.2468 |
| confirm | H2 | C0 | 3 | 3 | 2 | 1 | 58.16 | 0.1597 | 0.2414 | 0.1155 | 0.3527 |
| confirm | H2 | C0-NA | 3 | 3 | 2 | 1 | 50.86 | 0.1746 | 0.1248 | 0.03266 | 0.4944 |
| confirm | H2 | SM | 3 | 3 | 0 | 0 | — | 0.121 | 0.1765 | 0.1413 | 0.263 |
| confirm | H2 | G18 | 3 | 3 | 1 | 1 | 48.92 | 0.1689 | 0.1667 | 0.06179 | 0.437 |
| smoke | H1 | SM | 1 | 1 | 1 | 0 | 36.76 | 0.1475 | 0.1239 | 0.1461 | 0.2354 |
| smoke | H1 | G18 | 1 | 1 | 1 | 0 | 29.93 | 0.1848 | 0.1114 | 0.09703 | 0.2538 |

## Dev gate

{
  "passed": true,
  "checks": {
    "complete": true,
    "collision": true,
    "goal": true,
    "application": true,
    "technical": true
  },
  "g18_goal": 5,
  "na_goal": 5,
  "g18_collision": 3,
  "na_collision": 3,
  "g18_calls": 447,
  "g18_applied": 317,
  "application_rate": 0.70917225950783
}

## G18 적용/거절/계산

| stage | scene | index | calls | applied | reasons | compute_p50_s | compute_p95_s |
|---|---|---|---|---|---|---|---|
| confirm | H1 | 203 | 31 | 24 | {'INITIALIZATION_REJECTED': 5, 'ACCEPTED': 24, 'NONCONVERGED': 2} | 0.08174 | 0.1188 |
| confirm | H1 | 204 | 32 | 24 | {'INITIALIZATION_REJECTED': 6, 'ACCEPTED': 24, 'NON_NORMAL_MODE': 1, 'NONCONVERGED': 1} | 0.08078 | 0.09394 |
| confirm | H1 | 205 | 32 | 28 | {'INITIALIZATION_REJECTED': 3, 'ACCEPTED': 28, 'NONCONVERGED': 1} | 0.08165 | 0.08802 |
| confirm | H2 | 203 | 12 | 10 | {'INITIALIZATION_REJECTED': 1, 'ACCEPTED': 10, 'NONCONVERGED': 1} | 0.08196 | 0.08991 |
| confirm | H2 | 204 | 80 | 60 | {'INITIALIZATION_REJECTED': 13, 'ACCEPTED': 60, 'NONCONVERGED': 6, 'NON_NORMAL_MODE': 1} | 0.08146 | 0.1519 |
| confirm | H2 | 205 | 40 | 34 | {'INITIALIZATION_REJECTED': 4, 'ACCEPTED': 34, 'NONCONVERGED': 2} | 0.08221 | 0.1049 |
| confirm | L2 | 203 | 40 | 32 | {'INITIALIZATION_REJECTED': 4, 'ACCEPTED': 32, 'NONCONVERGED': 4} | 0.0827 | 0.182 |
| confirm | L2 | 204 | 44 | 35 | {'INITIALIZATION_REJECTED': 6, 'ACCEPTED': 35, 'NONCONVERGED': 2, 'NON_NORMAL_MODE': 1} | 0.08204 | 0.09511 |
| confirm | L2 | 205 | 43 | 36 | {'INITIALIZATION_REJECTED': 5, 'ACCEPTED': 36, 'NONCONVERGED': 2} | 0.08186 | 0.1224 |
| confirm | LC | 203 | 25 | 24 | {'INITIALIZATION_REJECTED': 1, 'ACCEPTED': 24} | 0.08076 | 0.08966 |
| confirm | LC | 204 | 25 | 21 | {'INITIALIZATION_REJECTED': 1, 'ACCEPTED': 21, 'NONCONVERGED': 3} | 0.08257 | 0.2058 |
| confirm | LC | 205 | 26 | 24 | {'INITIALIZATION_REJECTED': 2, 'ACCEPTED': 24} | 0.08052 | 0.08765 |
| confirm | SLW | 203 | 43 | 20 | {'INITIALIZATION_REJECTED': 15, 'ACCEPTED': 20, 'NONCONVERGED': 7, 'NON_NORMAL_MODE': 1} | 0.08033 | 0.2077 |
| confirm | SLW | 204 | 33 | 27 | {'INITIALIZATION_REJECTED': 3, 'ACCEPTED': 27, 'NONCONVERGED': 3} | 0.08352 | 0.2175 |
| confirm | SLW | 205 | 45 | 25 | {'INITIALIZATION_REJECTED': 11, 'ACCEPTED': 25, 'NONCONVERGED': 8, 'TERMINAL_UNAPPLIED': 1} | 0.07928 | 0.1568 |
| dev | H1 | 201 | 19 | 18 | {'INITIALIZATION_REJECTED': 1, 'ACCEPTED': 18} | 0.0842 | 0.09151 |
| dev | H1 | 202 | 31 | 25 | {'INITIALIZATION_REJECTED': 4, 'ACCEPTED': 25, 'NONCONVERGED': 2} | 0.08322 | 0.1308 |
| dev | H2 | 201 | 50 | 40 | {'INITIALIZATION_REJECTED': 6, 'ACCEPTED': 40, 'NONCONVERGED': 4} | 0.08297 | 0.1571 |
| dev | H2 | 202 | 56 | 43 | {'INITIALIZATION_REJECTED': 9, 'ACCEPTED': 43, 'NON_NORMAL_MODE': 1, 'NONCONVERGED': 3} | 0.08279 | 0.1048 |
| dev | L2 | 201 | 75 | 55 | {'INITIALIZATION_REJECTED': 14, 'ACCEPTED': 55, 'NONCONVERGED': 5, 'NON_NORMAL_MODE': 1} | 0.08282 | 0.154 |
| dev | L2 | 202 | 83 | 64 | {'INITIALIZATION_REJECTED': 12, 'ACCEPTED': 64, 'NONCONVERGED': 7} | 0.08098 | 0.139 |
| dev | LC | 201 | 27 | 24 | {'INITIALIZATION_REJECTED': 3, 'ACCEPTED': 24} | 0.08252 | 0.09043 |
| dev | LC | 202 | 29 | 25 | {'INITIALIZATION_REJECTED': 4, 'ACCEPTED': 25} | 0.08065 | 0.09263 |
| dev | SLW | 201 | 37 | 13 | {'INITIALIZATION_REJECTED': 13, 'ACCEPTED': 13, 'NONCONVERGED': 11} | 0.07835 | 0.2418 |
| dev | SLW | 202 | 40 | 10 | {'INITIALIZATION_REJECTED': 17, 'ACCEPTED': 10, 'NONCONVERGED': 12, 'NON_NORMAL_MODE': 1} | 0.07937 | 0.1636 |
| smoke | H1 | 201 | 28 | 23 | {'INITIALIZATION_REJECTED': 3, 'ACCEPTED': 23, 'NONCONVERGED': 1, 'TERMINAL_UNAPPLIED': 1} | 0.08177 | 0.09676 |

## 짝 차이

| scene | index | comparison | clearance_difference_m | goal_time_difference_s |
|---|---|---|---|---|
| H1 | 203 | G18-C0 | 0.02744 | 4.833 |
| H1 | 204 | G18-C0 | -0.03532 | -0.1806 |
| H1 | 205 | G18-C0 | 0.01032 | 1.597 |
| H2 | 203 | G18-C0 | -0.001184 | — |
| H2 | 204 | G18-C0 | -0.1195 | — |
| H2 | 205 | G18-C0 | 0.03414 | -8.167 |
| L2 | 203 | G18-C0 | -0.003992 | -3.847 |
| L2 | 204 | G18-C0 | 0.09503 | — |
| L2 | 205 | G18-C0 | -0.002686 | -9.083 |
| LC | 203 | G18-C0 | 0.1236 | — |
| LC | 204 | G18-C0 | 0.03625 | -5.208 |
| LC | 205 | G18-C0 | 0.02931 | -41.4 |
| SLW | 203 | G18-C0 | -0.1012 | 10.5 |
| SLW | 204 | G18-C0 | 0.01995 | -12.25 |
| SLW | 205 | G18-C0 | -0.05286 | — |
| H1 | 203 | G18-C0-NA | -0.005687 | 6.069 |
| H1 | 204 | G18-C0-NA | 0.06846 | 3.931 |
| H1 | 205 | G18-C0-NA | 0.007291 | 3.847 |
| H2 | 203 | G18-C0-NA | 0.0002831 | — |
| H2 | 204 | G18-C0-NA | -0.01528 | — |
| H2 | 205 | G18-C0-NA | 0.117 | 4.417 |
| L2 | 203 | G18-C0-NA | 0.1119 | -1.014 |
| L2 | 204 | G18-C0-NA | 0.07219 | — |
| L2 | 205 | G18-C0-NA | 0.04744 | — |
| LC | 203 | G18-C0-NA | -0.01892 | -0.7222 |
| LC | 204 | G18-C0-NA | 0.1628 | — |
| LC | 205 | G18-C0-NA | -0.01482 | 1.875 |
| SLW | 203 | G18-C0-NA | 0.004768 | — |
| SLW | 204 | G18-C0-NA | 0.02988 | -11.14 |
| SLW | 205 | G18-C0-NA | -0.006516 | — |
| H1 | 203 | G18-SM | -0.09047 | 4.931 |
| H1 | 204 | G18-SM | 0.1164 | — |
| H1 | 205 | G18-SM | -0.01865 | -2.194 |
| H2 | 203 | G18-SM | -0.1426 | — |
| H2 | 204 | G18-SM | -0.08055 | — |
| H2 | 205 | G18-SM | 0.1189 | — |
| L2 | 203 | G18-SM | 0.03205 | -18.18 |
| L2 | 204 | G18-SM | 0.04373 | — |
| L2 | 205 | G18-SM | -0.06212 | -3.903 |
| LC | 203 | G18-SM | 0.1021 | -11.74 |
| LC | 204 | G18-SM | 0.04705 | -10.83 |
| LC | 205 | G18-SM | -0.04527 | — |
| SLW | 203 | G18-SM | -0.01237 | — |
| SLW | 204 | G18-SM | -0.0166 | -12.81 |
| SLW | 205 | G18-SM | -0.03942 | — |

SM: Phase22 P3 geometry(.5 strength, three halvings,11-point resampling) on B suffix. R3-only advance/spacing/disk restrictions do not apply to normal chunks; both use Phase18 output depth-site certificate. G18: unchanged ClearanceGraph/FlagGraphV4+depth hard+CLR soft(.15/.05), previous correction prior; original 0.5s STALE and latest-id SUPERSEDED decision. RAW selected path runs until a valid correction arrives, and remains on rejection. Output XY goes to frozen NA PP/SP and >90° alignment, not CURV or timed H follower. G18 process uses parent NumPy/SciPy and CPU7, immutable shared SDF arrays. C0 confirm remains original C0; C0-NA/SM/G18 share NA.

Dev denominator: all G18 SAFE FRESH submissions including initialization failures, expired, superseded, stale and terminal-unapplied. Technical failures are final run outcomes after at most one retry; failed attempts are preserved separately. Confirmation paired goal-time medians use both-success pairs; no such pair makes that condition false. Incomplete stages yield PARTIAL, not imputed failures. Deadlines are checked between runs; an active run is allowed to finish. Previous C0/NA results are copied as descriptive rows only. No tuning or package install.
