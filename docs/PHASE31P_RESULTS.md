# Phase31-P 동결 방법 비교

**HOLD** — Phase31-P seed206/207만 판정에 사용. protocol SHA256 `67d16e7c5a2f7fadb10b0cb96e58d669ddd799a22a3f165a22fe2e10785e8417`.

| method | n | goal | collision |
|---|---|---|---|
| G18-R | 10 | 4 | 4 |
| C0 | 10 | 5 | 1 |
| C0-NA | 10 | 6 | 2 |

{
  "label": "HOLD",
  "evidence_valid": true,
  "checks": {
    "goal_gt_na": false,
    "collision_le_na": false,
    "goal_ge_c0": false,
    "collision_le_c0": false
  },
  "phase31p_only_counts": {
    "G18-R": {
      "n": 10,
      "goal": 4,
      "collision": 4
    },
    "C0": {
      "n": 10,
      "goal": 5,
      "collision": 1
    },
    "C0-NA": {
      "n": 10,
      "goal": 6,
      "collision": 2
    }
  },
  "complete_blocks": 10,
  "reason": "Registered conditions not all satisfied",
  "historical_used": false,
  "auxiliary_metrics_used": false
}

## 주 실험

| scope | scene | method | n | valid | goal | collision | goal_time_s | mean_speed_m_s | stopped_fraction | minimum_clearance_m |
|---|---|---|---|---|---|---|---|---|---|---|
| Phase31-P primary | SLW | G18-R | 2 | 2 | 1 | 0 | 58.889 | 0.081793 | 0.44754 | 0.0045914 |
| Phase31-P primary | SLW | C0 | 2 | 2 | 0 | 0 | — | 0.069926 | 0.59383 | 0.010547 |
| Phase31-P primary | SLW | C0-NA | 2 | 2 | 0 | 1 | — | 0.084521 | 0.50658 | -1.7301e-06 |
| Phase31-P primary | LC | G18-R | 2 | 2 | 2 | 0 | 31.604 | 0.17252 | 0.095099 | 0.15573 |
| Phase31-P primary | LC | C0 | 2 | 2 | 2 | 0 | 34.611 | 0.15694 | 0.18974 | 0.192 |
| Phase31-P primary | LC | C0-NA | 2 | 2 | 2 | 0 | 30.951 | 0.17817 | 0.14156 | 0.17866 |
| Phase31-P primary | L2 | G18-R | 2 | 2 | 0 | 2 | — | 0.13711 | 0.28852 | -0.00046973 |
| Phase31-P primary | L2 | C0 | 2 | 2 | 0 | 0 | — | 0.14801 | 0.28889 | 0.041246 |
| Phase31-P primary | L2 | C0-NA | 2 | 2 | 2 | 0 | 66.34 | 0.16687 | 0.12122 | 0.067847 |
| Phase31-P primary | H1 | G18-R | 2 | 2 | 1 | 0 | 36.611 | 0.11177 | 0.31222 | 0.063328 |
| Phase31-P primary | H1 | C0 | 2 | 2 | 2 | 0 | 37.146 | 0.14867 | 0.22442 | 0.080505 |
| Phase31-P primary | H1 | C0-NA | 2 | 2 | 2 | 0 | 32.653 | 0.17075 | 0.14365 | 0.056081 |
| Phase31-P primary | H2 | G18-R | 2 | 2 | 0 | 2 | — | 0.17339 | 0.15668 | -0.0009327 |
| Phase31-P primary | H2 | C0 | 2 | 2 | 1 | 1 | 65.639 | 0.16884 | 0.26107 | 0.0084711 |
| Phase31-P primary | H2 | C0-NA | 2 | 2 | 0 | 1 | — | 0.16337 | 0.22345 | 0.012828 |
| Phase31-P primary | ALL | G18-R | 10 | 10 | 4 | 4 | 34.785 | 0.15505 | 0.21491 | 0.0015659 |
| Phase31-P primary | ALL | C0 | 10 | 10 | 5 | 1 | 35.583 | 0.1471 | 0.26389 | 0.032823 |
| Phase31-P primary | ALL | C0-NA | 10 | 10 | 6 | 2 | 32.91 | 0.16687 | 0.16033 | 0.029484 |

| scene | index | comparison | g_goal | baseline_goal | goal_difference | collision_difference | goal_time_difference_s | mean_speed_m_s_difference | stopped_fraction_difference | minimum_clearance_m_difference |
|---|---|---|---|---|---|---|---|---|---|---|
| SLW | 206 | G18-R minus C0 | False | False | 0 | 0 | — | -0.0030216 | -0.049383 | -0.018945 |
| SLW | 206 | G18-R minus C0-NA | False | False | 0 | 0 | — | -0.026986 | 0.044444 | -0.0011117 |
| SLW | 207 | G18-R minus C0 | True | False | 1 | 0 | — | 0.026755 | -0.24319 | 0.0070338 |
| SLW | 207 | G18-R minus C0-NA | True | False | 1 | -1 | — | 0.021529 | -0.16252 | 0.010298 |
| LC | 206 | G18-R minus C0 | True | True | 0 | 0 | -2.625 | 0.01489 | -0.086962 | -0.075524 |
| LC | 206 | G18-R minus C0-NA | True | True | 0 | 0 | 2.4306 | -0.013925 | -0.032725 | -0.010554 |
| LC | 207 | G18-R minus C0 | True | True | 0 | 0 | -3.3889 | 0.016266 | -0.10231 | 0.0029854 |
| LC | 207 | G18-R minus C0-NA | True | True | 0 | 0 | -1.125 | 0.0026118 | -0.060189 | -0.035299 |
| L2 | 206 | G18-R minus C0 | False | False | 0 | 1 | — | 0.0080976 | -0.027584 | -0.019358 |
| L2 | 206 | G18-R minus C0-NA | False | True | -1 | 1 | — | 0.0027173 | 0.12715 | -0.10296 |
| L2 | 207 | G18-R minus C0 | False | False | 0 | 1 | — | -0.029895 | 0.026838 | -0.064073 |
| L2 | 207 | G18-R minus C0-NA | False | True | -1 | 1 | — | -0.062235 | 0.20745 | -0.03367 |
| H1 | 206 | G18-R minus C0 | True | True | 0 | 0 | 1.625 | -0.0051882 | -0.075648 | 0.0092155 |
| H1 | 206 | G18-R minus C0-NA | True | True | 0 | 0 | 5.75 | -0.026314 | -0.0015816 | 0.036209 |
| H1 | 207 | G18-R minus C0 | False | True | -1 | 0 | — | -0.068624 | 0.25124 | -0.043569 |
| H1 | 207 | G18-R minus C0-NA | False | True | -1 | 0 | — | -0.091645 | 0.33871 | -0.021715 |
| H2 | 206 | G18-R minus C0 | False | False | 0 | 0 | — | -0.039087 | -0.10616 | 0.00053829 |
| H2 | 206 | G18-R minus C0-NA | False | False | 0 | 1 | — | 0.0076152 | -0.06132 | -0.025956 |
| H2 | 207 | G18-R minus C0 | False | True | -1 | 1 | — | 0.048194 | -0.10261 | -0.019346 |
| H2 | 207 | G18-R minus C0-NA | False | False | 0 | 0 | — | 0.012424 | -0.072215 | -0.001565 |

## 보조 지표 — 판정 미사용

| c0_both_success_pairs | c0_goal_time_difference_median_s |
|---|---|
| 3 | -2.625 |

| scene | index | technical | jobs | applied | application_rate | rejections |
|---|---|---|---|---|---|---|
| H1 | 206 | PASS | 33 | 28 | 0.84848 | {'INITIALIZATION_REJECTED': 3, 'ACCEPTED': 28, 'NONCONVERGED': 2} |
| H1 | 207 | PASS | 45 | 30 | 0.66667 | {'INITIALIZATION_REJECTED': 8, 'ACCEPTED': 30, 'NONCONVERGED': 7} |
| H2 | 206 | PASS | 65 | 50 | 0.76923 | {'INITIALIZATION_REJECTED': 10, 'ACCEPTED': 50, 'NONCONVERGED': 5} |
| H2 | 207 | PASS | 13 | 12 | 0.92308 | {'INITIALIZATION_REJECTED': 1, 'ACCEPTED': 12} |
| L2 | 206 | PASS | 15 | 12 | 0.8 | {'INITIALIZATION_REJECTED': 2, 'ACCEPTED': 12, 'NONCONVERGED': 1} |
| L2 | 207 | PASS | 23 | 14 | 0.6087 | {'INITIALIZATION_REJECTED': 6, 'ACCEPTED': 14, 'NONCONVERGED': 3} |
| LC | 206 | PASS | 29 | 26 | 0.89655 | {'INITIALIZATION_REJECTED': 1, 'ACCEPTED': 26, 'NONCONVERGED': 1, 'TERMINAL_UNAPPLIED': 1} |
| LC | 207 | PASS | 25 | 23 | 0.92 | {'INITIALIZATION_REJECTED': 2, 'ACCEPTED': 23} |
| SLW | 206 | PASS | 45 | 16 | 0.35556 | {'INITIALIZATION_REJECTED': 19, 'ACCEPTED': 16, 'NONCONVERGED': 10} |
| SLW | 207 | PASS | 41 | 24 | 0.58537 | {'INITIALIZATION_REJECTED': 10, 'ACCEPTED': 24, 'NONCONVERGED': 7} |

도착시간 짝 차이는 둘 다 도착한 동일 scene×seed만 사용한다. 평균속도·정지비율·최소여유는 기술 유효 run 전체이며 최소여유는 참고다. G18-R 적용은 동결 실행기의 경로 설치 사건이며, 거절 사유는 기존 로그 정의를 따른다. 기술 실패는1회 재시도 후에도 유효하지 않으면 원 자료를 보존하고 HOLD(근거 불완전)로 보고한다.

## 과거 자료를 합친 표 — 판정 미사용

Phase29의 실제 confirm C0/C0-NA만 사용하고 그 파일에 중복 저장된 reused/dev/smoke 행은 제외했다. Phase30-R에서는 실제 G18-R 행만 사용했다. Phase29 G18(0.15m)은 다른 방법이므로 합치지 않는다. seed·실행 시점·방법별 n이 달라 아래 표는 서술용이며 EXPAND/HOLD 계산 함수에 전달하지 않는다.

| scope | scene | method | n | valid | goal | collision | goal_time_s | mean_speed_m_s | stopped_fraction | minimum_clearance_m |
|---|---|---|---|---|---|---|---|---|---|---|
| Phase29 confirm descriptive | SLW | C0 | 3 | 3 | 2 | 0 | 55.771 | 0.10949 | 0.42815 | 0.054402 |
| Phase29 confirm descriptive | SLW | C0-NA | 3 | 3 | 2 | 1 | 55.514 | 0.12507 | 0.34951 | 0.0080621 |
| Phase29 confirm descriptive | LC | C0 | 3 | 3 | 2 | 0 | 53.604 | 0.12222 | 0.32616 | 0.12842 |
| Phase29 confirm descriptive | LC | C0-NA | 3 | 3 | 2 | 0 | 29.639 | 0.17969 | 0.1274 | 0.17256 |
| Phase29 confirm descriptive | L2 | C0 | 3 | 3 | 2 | 0 | 54.507 | 0.16036 | 0.25793 | 0.057175 |
| Phase29 confirm descriptive | L2 | C0-NA | 3 | 3 | 1 | 0 | 48.861 | 0.16228 | 0.19012 | 0.029952 |
| Phase29 confirm descriptive | H1 | C0 | 3 | 3 | 3 | 0 | 34.333 | 0.15819 | 0.22957 | 0.09777 |
| Phase29 confirm descriptive | H1 | C0-NA | 3 | 3 | 3 | 0 | 31.486 | 0.17466 | 0.15868 | 0.047639 |
| Phase29 confirm descriptive | H2 | C0 | 3 | 3 | 2 | 1 | 58.16 | 0.15968 | 0.24136 | 0.11548 |
| Phase29 confirm descriptive | H2 | C0-NA | 3 | 3 | 2 | 1 | 50.861 | 0.17457 | 0.12484 | 0.032661 |
| Phase29 confirm descriptive | ALL | C0 | 15 | 15 | 11 | 1 | 54.708 | 0.15169 | 0.252 | 0.09777 |
| Phase29 confirm descriptive | ALL | C0-NA | 15 | 15 | 10 | 2 | 39.056 | 0.17457 | 0.17644 | 0.032661 |
| Phase30-R descriptive | SLW | G18-R | 2 | 2 | 2 | 0 | 66.174 | 0.10881 | 0.25228 | 0.030747 |
| Phase30-R descriptive | LC | G18-R | 2 | 2 | 2 | 0 | 49.785 | 0.15717 | 0.14377 | 0.082575 |
| Phase30-R descriptive | L2 | G18-R | 2 | 2 | 1 | 0 | 74.333 | 0.15601 | 0.17055 | 0.012469 |
| Phase30-R descriptive | H1 | G18-R | 2 | 2 | 1 | 0 | 34.083 | 0.10783 | 0.38975 | 0.059309 |
| Phase30-R descriptive | H2 | G18-R | 2 | 2 | 1 | 0 | 54.819 | 0.14885 | 0.13374 | 0.013576 |
| Phase30-R descriptive | ALL | G18-R | 10 | 10 | 7 | 0 | 56.306 | 0.14037 | 0.17055 | 0.030747 |
| Phase31-P descriptive | SLW | G18-R | 2 | 2 | 1 | 0 | 58.889 | 0.081793 | 0.44754 | 0.0045914 |
| Phase31-P descriptive | SLW | C0 | 2 | 2 | 0 | 0 | — | 0.069926 | 0.59383 | 0.010547 |
| Phase31-P descriptive | SLW | C0-NA | 2 | 2 | 0 | 1 | — | 0.084521 | 0.50658 | -1.7301e-06 |
| Phase31-P descriptive | LC | G18-R | 2 | 2 | 2 | 0 | 31.604 | 0.17252 | 0.095099 | 0.15573 |
| Phase31-P descriptive | LC | C0 | 2 | 2 | 2 | 0 | 34.611 | 0.15694 | 0.18974 | 0.192 |
| Phase31-P descriptive | LC | C0-NA | 2 | 2 | 2 | 0 | 30.951 | 0.17817 | 0.14156 | 0.17866 |
| Phase31-P descriptive | L2 | G18-R | 2 | 2 | 0 | 2 | — | 0.13711 | 0.28852 | -0.00046973 |
| Phase31-P descriptive | L2 | C0 | 2 | 2 | 0 | 0 | — | 0.14801 | 0.28889 | 0.041246 |
| Phase31-P descriptive | L2 | C0-NA | 2 | 2 | 2 | 0 | 66.34 | 0.16687 | 0.12122 | 0.067847 |
| Phase31-P descriptive | H1 | G18-R | 2 | 2 | 1 | 0 | 36.611 | 0.11177 | 0.31222 | 0.063328 |
| Phase31-P descriptive | H1 | C0 | 2 | 2 | 2 | 0 | 37.146 | 0.14867 | 0.22442 | 0.080505 |
| Phase31-P descriptive | H1 | C0-NA | 2 | 2 | 2 | 0 | 32.653 | 0.17075 | 0.14365 | 0.056081 |
| Phase31-P descriptive | H2 | G18-R | 2 | 2 | 0 | 2 | — | 0.17339 | 0.15668 | -0.0009327 |
| Phase31-P descriptive | H2 | C0 | 2 | 2 | 1 | 1 | 65.639 | 0.16884 | 0.26107 | 0.0084711 |
| Phase31-P descriptive | H2 | C0-NA | 2 | 2 | 0 | 1 | — | 0.16337 | 0.22345 | 0.012828 |
| Phase31-P descriptive | ALL | G18-R | 10 | 10 | 4 | 4 | 34.785 | 0.15505 | 0.21491 | 0.0015659 |
| Phase31-P descriptive | ALL | C0 | 10 | 10 | 5 | 1 | 35.583 | 0.1471 | 0.26389 | 0.032823 |
| Phase31-P descriptive | ALL | C0-NA | 10 | 10 | 6 | 2 | 32.91 | 0.16687 | 0.16033 | 0.029484 |

| scope | scene | method | n | valid | goal | collision | goal_time_s | mean_speed_m_s | stopped_fraction | minimum_clearance_m |
|---|---|---|---|---|---|---|---|---|---|---|
| Pooled historical+Phase31-P descriptive ONLY | SLW | G18-R | 4 | 4 | 3 | 0 | 58.889 | 0.10818 | 0.27278 | 0.017891 |
| Pooled historical+Phase31-P descriptive ONLY | SLW | C0 | 5 | 5 | 2 | 0 | 55.771 | 0.089195 | 0.5 | 0.036685 |
| Pooled historical+Phase31-P descriptive ONLY | SLW | C0-NA | 5 | 5 | 2 | 2 | 55.514 | 0.12406 | 0.38114 | 0.0015259 |
| Pooled historical+Phase31-P descriptive ONLY | LC | G18-R | 4 | 4 | 4 | 0 | 31.604 | 0.17252 | 0.10049 | 0.11689 |
| Pooled historical+Phase31-P descriptive ONLY | LC | C0 | 5 | 5 | 4 | 0 | 34.944 | 0.15169 | 0.22996 | 0.14346 |
| Pooled historical+Phase31-P descriptive ONLY | LC | C0-NA | 5 | 5 | 4 | 0 | 30.09 | 0.17969 | 0.1274 | 0.17256 |
| Pooled historical+Phase31-P descriptive ONLY | L2 | G18-R | 4 | 4 | 1 | 2 | 74.333 | 0.15583 | 0.2154 | 0.0041278 |
| Pooled historical+Phase31-P descriptive ONLY | L2 | C0 | 5 | 5 | 2 | 0 | 54.507 | 0.15999 | 0.27901 | 0.057175 |
| Pooled historical+Phase31-P descriptive ONLY | L2 | C0-NA | 5 | 5 | 3 | 0 | 52.75 | 0.16537 | 0.12428 | 0.03307 |
| Pooled historical+Phase31-P descriptive ONLY | H1 | G18-R | 4 | 4 | 2 | 0 | 35.347 | 0.11177 | 0.32987 | 0.059309 |
| Pooled historical+Phase31-P descriptive ONLY | H1 | C0 | 5 | 5 | 5 | 0 | 34.847 | 0.15819 | 0.22957 | 0.09777 |
| Pooled historical+Phase31-P descriptive ONLY | H1 | C0-NA | 5 | 5 | 5 | 0 | 31.486 | 0.17466 | 0.15868 | 0.047639 |
| Pooled historical+Phase31-P descriptive ONLY | H2 | G18-R | 4 | 4 | 1 | 2 | 54.819 | 0.15851 | 0.1465 | 0.0042447 |
| Pooled historical+Phase31-P descriptive ONLY | H2 | C0 | 5 | 5 | 3 | 2 | 59.236 | 0.15968 | 0.24136 | 0.017537 |
| Pooled historical+Phase31-P descriptive ONLY | H2 | C0-NA | 5 | 5 | 2 | 2 | 50.861 | 0.17457 | 0.1963 | 0.025899 |
| Pooled historical+Phase31-P descriptive ONLY | ALL | G18-R | 20 | 20 | 11 | 4 | 54.819 | 0.1486 | 0.17888 | 0.017474 |
| Pooled historical+Phase31-P descriptive ONLY | ALL | C0 | 25 | 25 | 16 | 2 | 45.5 | 0.15169 | 0.252 | 0.063473 |
| Pooled historical+Phase31-P descriptive ONLY | ALL | C0-NA | 25 | 25 | 16 | 4 | 34.028 | 0.16837 | 0.16129 | 0.032661 |

## 기술 실패

자료 없음
