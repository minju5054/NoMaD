최종 라벨: PARTIAL
완료: {'smoke': 2} (본 실행 순차, smoke 제외)
dev G18/NA 도착 0/5, 충돌 0/3, G18 적용 0/0
멈춘 단계: smoke — smoke complete; next registered stage
수치·정책·평가기·이전 결과 보존; 확인 실험은 dev gate 통과한 경우에만 실행.

# Phase29 경로–속도 분해

| stage | scene | method | n | valid | goal | collision | goal_time_s | mean_speed_m_s | stop_fraction | minimum_clearance_m | omega_saturation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | SLW | C0 | 2 | 2 | 0 | 0 | — | 0.0588 | 0.6716 | 0.08967 | 0.5883 |
| dev | SLW | C0-NA | 2 | 2 | 0 | 1 | — | 0.09592 | 0.4107 | 0.003266 | 0.3757 |
| dev | LC | C0 | 2 | 2 | 2 | 0 | 37.8 | 0.1413 | 0.2851 | 0.1534 | 0.3624 |
| dev | LC | C0-NA | 2 | 2 | 1 | 1 | 26.47 | 0.1804 | 0.1623 | 0.08792 | 0.5144 |
| dev | L2 | C0 | 2 | 2 | 2 | 0 | 54.09 | 0.161 | 0.2271 | 0.1368 | 0.473 |
| dev | L2 | C0-NA | 2 | 2 | 2 | 0 | 49.13 | 0.1748 | 0.1413 | 0.08028 | 0.4646 |
| dev | H1 | C0 | 2 | 2 | 1 | 1 | 29.99 | 0.148 | 0.2974 | 0.07147 | 0.3509 |
| dev | H1 | C0-NA | 2 | 2 | 2 | 0 | 31.78 | 0.172 | 0.1521 | 0.0932 | 0.437 |
| dev | H2 | C0 | 2 | 2 | 1 | 0 | 54.93 | 0.1491 | 0.2641 | 0.03962 | 0.4147 |
| dev | H2 | C0-NA | 2 | 2 | 0 | 1 | — | 0.1606 | 0.189 | 0.02847 | 0.4826 |
| smoke | H1 | SM | 1 | 1 | 1 | 0 | 36.76 | 0.1475 | 0.1239 | 0.1461 | 0.2354 |
| smoke | H1 | G18 | 1 | 1 | 1 | 0 | 29.93 | 0.1848 | 0.1114 | 0.09703 | 0.2538 |

## Dev gate

{
  "passed": false,
  "checks": {
    "complete": false,
    "collision": true,
    "goal": false,
    "application": false,
    "technical": true
  },
  "g18_goal": 0,
  "na_goal": 5,
  "g18_collision": 0,
  "na_collision": 3,
  "g18_calls": 0,
  "g18_applied": 0,
  "application_rate": null
}

## G18 적용/거절/계산

| stage | scene | index | calls | applied | reasons | compute_p50_s | compute_p95_s |
|---|---|---|---|---|---|---|---|
| smoke | H1 | 201 | 28 | 23 | {'INITIALIZATION_REJECTED': 3, 'ACCEPTED': 23, 'NONCONVERGED': 1, 'TERMINAL_UNAPPLIED': 1} | 0.08177 | 0.09676 |

## 짝 차이

자료 없음

SM: Phase22 P3 geometry(.5 strength, three halvings,11-point resampling) on B suffix. R3-only advance/spacing/disk restrictions do not apply to normal chunks; both use Phase18 output depth-site certificate. G18: unchanged ClearanceGraph/FlagGraphV4+depth hard+CLR soft(.15/.05), previous correction prior; original 0.5s STALE and latest-id SUPERSEDED decision. RAW selected path runs until a valid correction arrives, and remains on rejection. Output XY goes to frozen NA PP/SP and >90° alignment, not CURV or timed H follower. G18 process uses parent NumPy/SciPy and CPU7, immutable shared SDF arrays. C0 confirm remains original C0; C0-NA/SM/G18 share NA.

Dev denominator: all G18 SAFE FRESH submissions including initialization failures, expired, superseded, stale and terminal-unapplied. Technical failures are final run outcomes after at most one retry; failed attempts are preserved separately. Confirmation paired goal-time medians use both-success pairs; no such pair makes that condition false. Incomplete stages yield PARTIAL, not imputed failures. Deadlines are checked between runs; an active run is allowed to finish. Previous C0/NA results are copied as descriptive rows only. No tuning or package install.
