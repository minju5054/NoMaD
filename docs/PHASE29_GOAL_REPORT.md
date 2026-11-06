최종 라벨: PARTIAL
완료: {'dev': 20, 'smoke': 2} (본 실행 순차, smoke 제외)
dev G18/NA 도착 5/5, 충돌 3/3, G18 적용 317/447
멈춘 단계: dev — dev complete; next registered stage
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

자료 없음

SM: Phase22 P3 geometry(.5 strength, three halvings,11-point resampling) on B suffix. R3-only advance/spacing/disk restrictions do not apply to normal chunks; both use Phase18 output depth-site certificate. G18: unchanged ClearanceGraph/FlagGraphV4+depth hard+CLR soft(.15/.05), previous correction prior; original 0.5s STALE and latest-id SUPERSEDED decision. RAW selected path runs until a valid correction arrives, and remains on rejection. Output XY goes to frozen NA PP/SP and >90° alignment, not CURV or timed H follower. G18 process uses parent NumPy/SciPy and CPU7, immutable shared SDF arrays. C0 confirm remains original C0; C0-NA/SM/G18 share NA.

Dev denominator: all G18 SAFE FRESH submissions including initialization failures, expired, superseded, stale and terminal-unapplied. Technical failures are final run outcomes after at most one retry; failed attempts are preserved separately. Confirmation paired goal-time medians use both-success pairs; no such pair makes that condition false. Incomplete stages yield PARTIAL, not imputed failures. Deadlines are checked between runs; an active run is allowed to finish. Previous C0/NA results are copied as descriptive rows only. No tuning or package install.
