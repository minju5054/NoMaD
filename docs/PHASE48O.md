| table |
|---|
| 주 결과 — 오도메트리 오차0 이상조건 상한 |

| model | runs | inferences | valid | missing | mae | p95_nodes | jumps | jump_denominator | jump_rate | virtual_stop_eligible | false_goal_events | first_virtual_stop_runs | first_virtual_wrong_runs | first_outcome_unknown_runs | estimates_outside_logged_window | truth_outside_window | solve_p50_s | solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ARGMIN | 111 | 4959 | 4959 | 0 | 2.408 | 9 | 883 | 4848 | 0.1821 | 4941 | 77 | 89 | 50 | 0 | 0 | 693 | — | — |
| FG_HARD_0ERR_UPPER_BOUND | 111 | 4959 | 4959 | 0 | 1.917 | 7 | 269 | 4848 | 0.05549 | 4941 | 52 | 61 | 24 | 0 | 33 | 693 | 0.0192 | 0.0397 |
| HMM_FORWARD | 111 | 4959 | 4959 | 0 | 1.95 | 7 | 169 | 4848 | 0.03486 | 4941 | 18 | 59 | 18 | 0 | 0 | 693 | — | — |

| table |
|---|
| 보조 — 사전 고정2% 잡음1회;실측 covariance 아님 |

| model | runs | inferences | valid | missing | mae | p95_nodes | jumps | jump_denominator | jump_rate | virtual_stop_eligible | false_goal_events | first_virtual_stop_runs | first_virtual_wrong_runs | first_outcome_unknown_runs | estimates_outside_logged_window | truth_outside_window | solve_p50_s | solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FG_2PCT_ONE_DRAW | 111 | 4959 | 4959 | 0 | 1.916 | 7 | 270 | 4848 | 0.05569 | 4941 | 53 | 61 | 24 | 0 | 32 | 693 | 0.02401 | 0.1926 |
| FG_HARD_0ERR_UPPER_BOUND | 111 | 4959 | 4959 | 0 | 1.917 | 7 | 269 | 4848 | 0.05549 | 4941 | 52 | 61 | 24 | 0 | 33 | 693 | 0.0192 | 0.0397 |

| table |
|---|
| 측정 정의와 상한 해석의 한계 |

| item | value |
|---|---|
| primary_title | 주 결과:오도메트리 오차0의 시뮬레이터 이상조건 상한; 실제 시스템 성능 보장이 아님 |
| inputs | Final recorded attempts in Phase43-P,44-P,45-P,46-P,47-C,all stored HMM and original-localization runs |
| reference | Topomap node world-pose XY polyline; continuous cumulative arclength; duplicate-node ties use smaller index |
| argmin | Minimum logged distance in the logged candidate window,not HMM-run logged closest_node |
| hmm | Frozen42-L/43 forward filter,logged candidate window; logged cumulative odometry when present,otherwise saved72Hz path length |
| main_motion | On-reference edge:s[k]-s[k-1]=project(p[k])-project(p[k-1]) exactly by variable elimination |
| off_path | Any72Hz pose between inference observations at distance>=0.5m from reference => no signed increment;only abs(delta_s)<=recorded travel length |
| noise_seed | 20261112 |
| noise | One standard-normal draw per inference interval,stable run hash substream; no tuning/repeated draws |
| noisy_on_path | measured delta=projected delta+N(0,(0.02*abs(delta))²),Gaussian factor with exactly that sigma;zero sigma stays exact |
| noisy_off_path | no direction:measured upper bound=max(0,travel+N(0,(0.02*travel)²));one-sided Gaussian excess factor with that sigma;zero travel stays exact |
| noise_scope | User-specified2% sensitivity model,not empirically calibrated wheel-odometry covariance;reference/ground-truth evaluation remains clean |
| visual | Mixture over logged node positions:weights softmax(-distance),Gaussian position kernel sigma=median positive node spacing/sqrt(12) |
| robust | Cauchy scale1 on sqrt(2 negative-log-mixture-likelihood);objective log(1+2*NLL),fixed before results |
| monotonic | Weak prior:max(0,-delta_s-0.05)/median_node_spacing,squared;hard odometry takes priority |
| lag | 5.0s causal rolling factor window;expired factors dropped,no extra boundary prior or future observations;previous states warm-start only |
| solver | SLSQP analytical objective gradient,linear constraints,maxiter100,ftol1e-8;starts=warm solution plus each current logged-node-aligned trajectory |
| acceptance | Solver success and constraint violation<=1e-7m;failures remain missing,not silently replaced by another estimator |
| node | Latest optimized s chooses nearest node arclength;truth is nearest node XY at image observation pose |
| jump | abs(delta estimated node)>=3 per consecutive inference;first/missing predecessor excluded |
| virtual_stop | Estimated node==goal at an actually delivered inference;false if recorded latch-pose goal distance>0.5m |
| virtual_counts | Candidate false events plus first-virtual-stop per run;after virtual stop remaining data are diagnostics,not a new closed-loop run |
| virtual_missing | Missing prior estimates make a first-stop outcome unknown;post-termination drained results ineligible,actual declaration result eligible |
| limitations | Logged windows only:unobserved node distances not generated.Graph kernel tails/odometry can extrapolate outside current window;count separately |
| ideal_limit | Projected increments/off-reference flags use exact simulator poses and reference geometry:upper bound.Exact on-path increments make monotonic factor constant there |
| no_driving_claim | No rerender,NoMaD inference,controller rollout,or new driving.Original windows and trajectories were produced by their original policies |
| reporting | All available estimates plus paired-common subsets;H2 and SLW explicit;Phase44 changed appearance identified separately |

| table |
|---|
| 장면별(H2·SLW 포함) — HARD는0오차 상한 |

| scene | model | runs | inferences | valid | missing | mae | p95_nodes | jumps | jump_denominator | jump_rate | virtual_stop_eligible | false_goal_events | first_virtual_stop_runs | first_virtual_wrong_runs | first_outcome_unknown_runs | estimates_outside_logged_window | truth_outside_window | solve_p50_s | solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | ARGMIN | 21 | 693 | 693 | 0 | 1.322 | 7 | 54 | 672 | 0.08036 | 693 | 10 | 20 | 9 | 0 | 0 | 53 | — | — |
| H1 | FG_2PCT_ONE_DRAW | 21 | 693 | 693 | 0 | 1.078 | 7 | 15 | 672 | 0.02232 | 693 | 3 | 14 | 3 | 0 | 2 | 53 | 0.02505 | 0.1176 |
| H1 | FG_HARD_0ERR_UPPER_BOUND | 21 | 693 | 693 | 0 | 1.078 | 7 | 15 | 672 | 0.02232 | 693 | 3 | 14 | 3 | 0 | 2 | 53 | 0.01984 | 0.03268 |
| H1 | HMM_FORWARD | 21 | 693 | 693 | 0 | 1.113 | 7 | 4 | 672 | 0.005952 | 693 | 1 | 14 | 1 | 0 | 0 | 53 | — | — |
| H2 | ARGMIN | 24 | 1358 | 1358 | 0 | 3.338 | 10 | 349 | 1334 | 0.2616 | 1352 | 36 | 18 | 16 | 0 | 0 | 285 | — | — |
| H2 | FG_2PCT_ONE_DRAW | 24 | 1358 | 1358 | 0 | 2.636 | 7 | 105 | 1334 | 0.07871 | 1352 | 27 | 11 | 10 | 0 | 9 | 285 | 0.02393 | 0.1586 |
| H2 | FG_HARD_0ERR_UPPER_BOUND | 24 | 1358 | 1358 | 0 | 2.64 | 7 | 104 | 1334 | 0.07796 | 1352 | 26 | 11 | 10 | 0 | 9 | 285 | 0.01918 | 0.03893 |
| H2 | HMM_FORWARD | 24 | 1358 | 1358 | 0 | 2.65 | 7 | 57 | 1334 | 0.04273 | 1352 | 8 | 10 | 8 | 0 | 0 | 285 | — | — |
| L2 | ARGMIN | 24 | 1134 | 1134 | 0 | 3.14 | 11 | 216 | 1110 | 0.1946 | 1130 | 19 | 20 | 15 | 0 | 0 | 226 | — | — |
| L2 | FG_2PCT_ONE_DRAW | 24 | 1134 | 1134 | 0 | 2.54 | 7 | 82 | 1110 | 0.07387 | 1130 | 5 | 11 | 5 | 0 | 11 | 226 | 0.0217 | 0.278 |
| L2 | FG_HARD_0ERR_UPPER_BOUND | 24 | 1134 | 1134 | 0 | 2.541 | 7 | 82 | 1110 | 0.07387 | 1130 | 5 | 11 | 5 | 0 | 12 | 226 | 0.01785 | 0.0508 |
| L2 | HMM_FORWARD | 24 | 1134 | 1134 | 0 | 2.728 | 8 | 61 | 1110 | 0.05495 | 1130 | 8 | 14 | 8 | 0 | 0 | 226 | — | — |
| LC | ARGMIN | 21 | 602 | 602 | 0 | 0.6694 | 2 | 35 | 581 | 0.06024 | 601 | 3 | 20 | 3 | 0 | 0 | 3 | — | — |
| LC | FG_2PCT_ONE_DRAW | 21 | 602 | 602 | 0 | 0.5 | 1 | 6 | 581 | 0.01033 | 601 | 13 | 18 | 4 | 0 | 1 | 3 | 0.0247 | 0.03597 |
| LC | FG_HARD_0ERR_UPPER_BOUND | 21 | 602 | 602 | 0 | 0.5017 | 1 | 6 | 581 | 0.01033 | 601 | 13 | 18 | 4 | 0 | 1 | 3 | 0.01939 | 0.02845 |
| LC | HMM_FORWARD | 21 | 602 | 602 | 0 | 0.4518 | 1 | 7 | 581 | 0.01205 | 601 | 0 | 15 | 0 | 0 | 0 | 3 | — | — |
| SLW | ARGMIN | 21 | 1172 | 1172 | 0 | 2.157 | 10 | 229 | 1151 | 0.199 | 1165 | 9 | 11 | 7 | 0 | 0 | 126 | — | — |
| SLW | FG_2PCT_ONE_DRAW | 21 | 1172 | 1172 | 0 | 1.701 | 9 | 62 | 1151 | 0.05387 | 1165 | 5 | 7 | 2 | 0 | 9 | 126 | 0.02446 | 0.2185 |
| SLW | FG_HARD_0ERR_UPPER_BOUND | 21 | 1172 | 1172 | 0 | 1.699 | 9 | 62 | 1151 | 0.05387 | 1165 | 5 | 7 | 2 | 0 | 9 | 126 | 0.01954 | 0.03095 |
| SLW | HMM_FORWARD | 21 | 1172 | 1172 | 0 | 1.653 | 9.45 | 40 | 1151 | 0.03475 | 1165 | 1 | 6 | 1 | 0 | 0 | 126 | — | — |

| table |
|---|
| 동일 측정가능 입력의 짝 비교 |

| scene | target | reference | paired_n | target_mae | reference_mae | mae_difference | better_events | worse_events |
|---|---|---|---|---|---|---|---|---|
| ALL | HMM_FORWARD | ARGMIN | 4959 | 1.95 | 2.408 | -0.4576 | 1236 | 330 |
| ALL | FG_HARD_0ERR_UPPER_BOUND | ARGMIN | 4959 | 1.917 | 2.408 | -0.491 | 1635 | 705 |
| ALL | FG_HARD_0ERR_UPPER_BOUND | HMM_FORWARD | 4959 | 1.917 | 1.95 | -0.03347 | 1137 | 921 |
| ALL | FG_2PCT_ONE_DRAW | FG_HARD_0ERR_UPPER_BOUND | 4959 | 1.916 | 1.917 | -0.001008 | 48 | 47 |
| H2 | HMM_FORWARD | ARGMIN | 1358 | 2.65 | 3.338 | -0.6878 | 500 | 137 |
| H2 | FG_HARD_0ERR_UPPER_BOUND | ARGMIN | 1358 | 2.64 | 3.338 | -0.6981 | 556 | 217 |
| H2 | FG_HARD_0ERR_UPPER_BOUND | HMM_FORWARD | 1358 | 2.64 | 2.65 | -0.01031 | 366 | 332 |
| H2 | FG_2PCT_ONE_DRAW | FG_HARD_0ERR_UPPER_BOUND | 1358 | 2.636 | 2.64 | -0.003682 | 19 | 17 |
| SLW | HMM_FORWARD | ARGMIN | 1172 | 1.653 | 2.157 | -0.5043 | 212 | 44 |
| SLW | FG_HARD_0ERR_UPPER_BOUND | ARGMIN | 1172 | 1.699 | 2.157 | -0.4582 | 342 | 129 |
| SLW | FG_HARD_0ERR_UPPER_BOUND | HMM_FORWARD | 1172 | 1.699 | 1.653 | 0.04608 | 243 | 165 |
| SLW | FG_2PCT_ONE_DRAW | FG_HARD_0ERR_UPPER_BOUND | 1172 | 1.701 | 1.699 | 0.001706 | 5 | 7 |
| L2 | HMM_FORWARD | ARGMIN | 1134 | 2.728 | 3.14 | -0.4127 | 340 | 124 |
| L2 | FG_HARD_0ERR_UPPER_BOUND | ARGMIN | 1134 | 2.541 | 3.14 | -0.5996 | 425 | 184 |
| L2 | FG_HARD_0ERR_UPPER_BOUND | HMM_FORWARD | 1134 | 2.541 | 2.728 | -0.1869 | 302 | 214 |
| L2 | FG_2PCT_ONE_DRAW | FG_HARD_0ERR_UPPER_BOUND | 1134 | 2.54 | 2.541 | -0.0008818 | 17 | 17 |
| LC | HMM_FORWARD | ARGMIN | 602 | 0.4518 | 0.6694 | -0.2176 | 84 | 8 |
| LC | FG_HARD_0ERR_UPPER_BOUND | ARGMIN | 602 | 0.5017 | 0.6694 | -0.1678 | 135 | 80 |
| LC | FG_HARD_0ERR_UPPER_BOUND | HMM_FORWARD | 602 | 0.5017 | 0.4518 | 0.04983 | 97 | 98 |
| LC | FG_2PCT_ONE_DRAW | FG_HARD_0ERR_UPPER_BOUND | 602 | 0.5 | 0.5017 | -0.001661 | 2 | 1 |
| H1 | HMM_FORWARD | ARGMIN | 693 | 1.113 | 1.322 | -0.2092 | 100 | 17 |
| H1 | FG_HARD_0ERR_UPPER_BOUND | ARGMIN | 693 | 1.078 | 1.322 | -0.2439 | 177 | 95 |
| H1 | FG_HARD_0ERR_UPPER_BOUND | HMM_FORWARD | 693 | 1.078 | 1.113 | -0.03463 | 129 | 112 |
| H1 | FG_2PCT_ONE_DRAW | FG_HARD_0ERR_UPPER_BOUND | 693 | 1.078 | 1.078 | 0 | 5 | 5 |

| table |
|---|
| HMM/원래 위치추정·외관별 원 run 코호트 |

| phase | method | scene | model | runs | inferences | valid | missing | mae | p95_nodes | jumps | jump_denominator | jump_rate | virtual_stop_eligible | false_goal_events | first_virtual_stop_runs | first_virtual_wrong_runs | first_outcome_unknown_runs | estimates_outside_logged_window | truth_outside_window | solve_p50_s | solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| phase43p | OURS-DETOUR+HMM | H1 | ARGMIN | 3 | 119 | 119 | 0 | 1.134 | 4 | 12 | 116 | 0.1034 | 119 | 4 | 3 | 3 | 0 | 0 | 0 | — | — |
| phase43p | OURS-DETOUR+HMM | H1 | FG_2PCT_ONE_DRAW | 3 | 119 | 119 | 0 | 0.8571 | 3 | 3 | 116 | 0.02586 | 119 | 0 | 2 | 0 | 0 | 0 | 0 | 0.02344 | 0.1134 |
| phase43p | OURS-DETOUR+HMM | H1 | FG_HARD_0ERR_UPPER_BOUND | 3 | 119 | 119 | 0 | 0.8739 | 3 | 3 | 116 | 0.02586 | 119 | 0 | 2 | 0 | 0 | 0 | 0 | 0.0189 | 0.0341 |
| phase43p | OURS-DETOUR+HMM | H1 | HMM_FORWARD | 3 | 119 | 119 | 0 | 0.7563 | 3 | 0 | 116 | 0 | 119 | 1 | 3 | 1 | 0 | 0 | 0 | — | — |
| phase43p | OURS-DETOUR+HMM | H2 | ARGMIN | 3 | 248 | 248 | 0 | 2.222 | 7 | 65 | 245 | 0.2653 | 247 | 2 | 2 | 1 | 0 | 0 | 26 | — | — |
| phase43p | OURS-DETOUR+HMM | H2 | FG_2PCT_ONE_DRAW | 3 | 248 | 248 | 0 | 1.895 | 7 | 14 | 245 | 0.05714 | 247 | 1 | 2 | 1 | 0 | 0 | 26 | 0.0261 | 0.1322 |
| phase43p | OURS-DETOUR+HMM | H2 | FG_HARD_0ERR_UPPER_BOUND | 3 | 248 | 248 | 0 | 1.891 | 7 | 15 | 245 | 0.06122 | 247 | 1 | 2 | 1 | 0 | 0 | 26 | 0.02088 | 0.03706 |
| phase43p | OURS-DETOUR+HMM | H2 | HMM_FORWARD | 3 | 248 | 248 | 0 | 1.875 | 7 | 9 | 245 | 0.03673 | 247 | 1 | 2 | 1 | 0 | 0 | 26 | — | — |
| phase43p | OURS-DETOUR+HMM | L2 | ARGMIN | 3 | 191 | 191 | 0 | 3.906 | 16 | 28 | 188 | 0.1489 | 190 | 5 | 2 | 2 | 0 | 0 | 43 | — | — |
| phase43p | OURS-DETOUR+HMM | L2 | FG_2PCT_ONE_DRAW | 3 | 191 | 191 | 0 | 3.356 | 16 | 13 | 188 | 0.06915 | 190 | 1 | 1 | 1 | 0 | 0 | 43 | 0.02142 | 0.2565 |
| phase43p | OURS-DETOUR+HMM | L2 | FG_HARD_0ERR_UPPER_BOUND | 3 | 191 | 191 | 0 | 3.356 | 16 | 13 | 188 | 0.06915 | 190 | 1 | 1 | 1 | 0 | 0 | 43 | 0.01657 | 0.04895 |
| phase43p | OURS-DETOUR+HMM | L2 | HMM_FORWARD | 3 | 191 | 191 | 0 | 3.602 | 15.5 | 8 | 188 | 0.04255 | 190 | 2 | 2 | 2 | 0 | 0 | 43 | — | — |
| phase43p | OURS-DETOUR+HMM | LC | ARGMIN | 3 | 89 | 89 | 0 | 0.809 | 5 | 10 | 86 | 0.1163 | 89 | 1 | 3 | 1 | 0 | 0 | 0 | — | — |
| phase43p | OURS-DETOUR+HMM | LC | FG_2PCT_ONE_DRAW | 3 | 89 | 89 | 0 | 0.4382 | 1 | 2 | 86 | 0.02326 | 89 | 0 | 3 | 0 | 0 | 0 | 0 | 0.02435 | 0.03299 |
| phase43p | OURS-DETOUR+HMM | LC | FG_HARD_0ERR_UPPER_BOUND | 3 | 89 | 89 | 0 | 0.4382 | 1 | 2 | 86 | 0.02326 | 89 | 0 | 3 | 0 | 0 | 0 | 0 | 0.01946 | 0.0267 |
| phase43p | OURS-DETOUR+HMM | LC | HMM_FORWARD | 3 | 89 | 89 | 0 | 0.382 | 1 | 0 | 86 | 0 | 89 | 0 | 3 | 0 | 0 | 0 | 0 | — | — |
| phase43p | OURS-DETOUR+HMM | SLW | ARGMIN | 3 | 193 | 193 | 0 | 0.8653 | 4 | 35 | 190 | 0.1842 | 193 | 1 | 3 | 1 | 0 | 0 | 0 | — | — |
| phase43p | OURS-DETOUR+HMM | SLW | FG_2PCT_ONE_DRAW | 3 | 193 | 193 | 0 | 0.3834 | 1 | 3 | 190 | 0.01579 | 193 | 0 | 3 | 0 | 0 | 0 | 0 | 0.02483 | 0.03098 |
| phase43p | OURS-DETOUR+HMM | SLW | FG_HARD_0ERR_UPPER_BOUND | 3 | 193 | 193 | 0 | 0.3782 | 1 | 3 | 190 | 0.01579 | 193 | 0 | 3 | 0 | 0 | 0 | 0 | 0.01967 | 0.0244 |
| phase43p | OURS-DETOUR+HMM | SLW | HMM_FORWARD | 3 | 193 | 193 | 0 | 0.4301 | 1 | 2 | 190 | 0.01053 | 193 | 0 | 3 | 0 | 0 | 0 | 0 | — | — |
| phase44p | OURS-DETOUR+HMM | H2 | ARGMIN | 3 | 224 | 224 | 0 | 4.147 | 7 | 32 | 221 | 0.1448 | 223 | 9 | 2 | 2 | 0 | 0 | 107 | — | — |
| phase44p | OURS-DETOUR+HMM | H2 | FG_2PCT_ONE_DRAW | 3 | 224 | 224 | 0 | 3.549 | 7 | 6 | 221 | 0.02715 | 223 | 7 | 2 | 2 | 0 | 0 | 107 | 0.01026 | 0.03269 |
| phase44p | OURS-DETOUR+HMM | H2 | FG_HARD_0ERR_UPPER_BOUND | 3 | 224 | 224 | 0 | 3.554 | 7 | 6 | 221 | 0.02715 | 223 | 6 | 2 | 2 | 0 | 0 | 107 | 0.008658 | 0.02468 |
| phase44p | OURS-DETOUR+HMM | H2 | HMM_FORWARD | 3 | 224 | 224 | 0 | 4 | 6 | 4 | 221 | 0.0181 | 223 | 2 | 2 | 2 | 0 | 0 | 107 | — | — |
| phase44p | OURS-DETOUR+HMM | L2 | ARGMIN | 3 | 252 | 252 | 0 | 3.246 | 7 | 32 | 249 | 0.1285 | 250 | 0 | 1 | 0 | 0 | 0 | 67 | — | — |
| phase44p | OURS-DETOUR+HMM | L2 | FG_2PCT_ONE_DRAW | 3 | 252 | 252 | 0 | 2.786 | 6 | 6 | 249 | 0.0241 | 250 | 0 | 1 | 0 | 0 | 0 | 67 | 0.01632 | 0.1128 |
| phase44p | OURS-DETOUR+HMM | L2 | FG_HARD_0ERR_UPPER_BOUND | 3 | 252 | 252 | 0 | 2.77 | 6 | 6 | 249 | 0.0241 | 250 | 0 | 1 | 0 | 0 | 0 | 67 | 0.01387 | 0.033 |
| phase44p | OURS-DETOUR+HMM | L2 | HMM_FORWARD | 3 | 252 | 252 | 0 | 3.139 | 6 | 2 | 249 | 0.008032 | 250 | 0 | 1 | 0 | 0 | 0 | 67 | — | — |
| phase45p | OURS+HMM | H1 | ARGMIN | 3 | 146 | 146 | 0 | 3.493 | 10.75 | 26 | 143 | 0.1818 | 146 | 0 | 2 | 0 | 0 | 0 | 47 | — | — |
| phase45p | OURS+HMM | H1 | FG_2PCT_ONE_DRAW | 3 | 146 | 146 | 0 | 3.274 | 9.75 | 7 | 143 | 0.04895 | 146 | 0 | 2 | 0 | 0 | 0 | 47 | 0.02722 | 0.2547 |
| phase45p | OURS+HMM | H1 | FG_HARD_0ERR_UPPER_BOUND | 3 | 146 | 146 | 0 | 3.26 | 9.75 | 7 | 143 | 0.04895 | 146 | 0 | 2 | 0 | 0 | 0 | 47 | 0.02149 | 0.04057 |
| phase45p | OURS+HMM | H1 | HMM_FORWARD | 3 | 146 | 146 | 0 | 3.527 | 9.75 | 3 | 143 | 0.02098 | 146 | 0 | 2 | 0 | 0 | 0 | 47 | — | — |
| phase45p | OURS+HMM | H2 | ARGMIN | 3 | 225 | 225 | 0 | 3.52 | 12.6 | 75 | 222 | 0.3378 | 224 | 13 | 3 | 3 | 0 | 0 | 41 | — | — |
| phase45p | OURS+HMM | H2 | FG_2PCT_ONE_DRAW | 3 | 225 | 225 | 0 | 2.867 | 9 | 30 | 222 | 0.1351 | 224 | 11 | 3 | 3 | 0 | 0 | 41 | 0.02713 | 0.1681 |
| phase45p | OURS+HMM | H2 | FG_HARD_0ERR_UPPER_BOUND | 3 | 225 | 225 | 0 | 2.853 | 9 | 29 | 222 | 0.1306 | 224 | 11 | 3 | 3 | 0 | 0 | 41 | 0.02134 | 0.03942 |
| phase45p | OURS+HMM | H2 | HMM_FORWARD | 3 | 225 | 225 | 0 | 2.836 | 10.8 | 12 | 222 | 0.05405 | 224 | 2 | 2 | 2 | 0 | 0 | 41 | — | — |
| phase45p | OURS+HMM | L2 | ARGMIN | 3 | 163 | 163 | 0 | 2.515 | 7 | 38 | 160 | 0.2375 | 163 | 2 | 3 | 1 | 0 | 0 | 35 | — | — |
| phase45p | OURS+HMM | L2 | FG_2PCT_ONE_DRAW | 3 | 163 | 163 | 0 | 2.411 | 7 | 21 | 160 | 0.1313 | 163 | 1 | 3 | 1 | 0 | 0 | 35 | 0.02858 | 0.2609 |
| phase45p | OURS+HMM | L2 | FG_HARD_0ERR_UPPER_BOUND | 3 | 163 | 163 | 0 | 2.448 | 7 | 20 | 160 | 0.125 | 163 | 1 | 3 | 1 | 0 | 0 | 35 | 0.02248 | 0.0516 |
| phase45p | OURS+HMM | L2 | HMM_FORWARD | 3 | 163 | 163 | 0 | 2.558 | 8 | 12 | 160 | 0.075 | 163 | 1 | 3 | 1 | 0 | 0 | 35 | — | — |
| phase45p | OURS+HMM | LC | ARGMIN | 3 | 84 | 84 | 0 | 0.5357 | 2 | 1 | 81 | 0.01235 | 84 | 0 | 3 | 0 | 0 | 0 | 0 | — | — |
| phase45p | OURS+HMM | LC | FG_2PCT_ONE_DRAW | 3 | 84 | 84 | 0 | 0.3929 | 1 | 0 | 81 | 0 | 84 | 2 | 3 | 1 | 0 | 0 | 0 | 0.02388 | 0.03405 |
| phase45p | OURS+HMM | LC | FG_HARD_0ERR_UPPER_BOUND | 3 | 84 | 84 | 0 | 0.3929 | 1 | 0 | 81 | 0 | 84 | 2 | 3 | 1 | 0 | 0 | 0 | 0.01862 | 0.02718 |
| phase45p | OURS+HMM | LC | HMM_FORWARD | 3 | 84 | 84 | 0 | 0.4405 | 1 | 0 | 81 | 0 | 84 | 0 | 3 | 0 | 0 | 0 | 0 | — | — |
| phase45p | OURS+HMM | SLW | ARGMIN | 3 | 265 | 265 | 0 | 2.985 | 10 | 55 | 262 | 0.2099 | 264 | 0 | 0 | 0 | 0 | 0 | 40 | — | — |
| phase45p | OURS+HMM | SLW | FG_2PCT_ONE_DRAW | 3 | 265 | 265 | 0 | 2.585 | 9 | 22 | 262 | 0.08397 | 264 | 0 | 0 | 0 | 0 | 3 | 40 | 0.01897 | 0.2072 |
| phase45p | OURS+HMM | SLW | FG_HARD_0ERR_UPPER_BOUND | 3 | 265 | 265 | 0 | 2.581 | 9 | 22 | 262 | 0.08397 | 264 | 0 | 0 | 0 | 0 | 3 | 40 | 0.01708 | 0.02765 |
| phase45p | OURS+HMM | SLW | HMM_FORWARD | 3 | 265 | 265 | 0 | 2.215 | 10 | 13 | 262 | 0.04962 | 264 | 0 | 0 | 0 | 0 | 0 | 40 | — | — |
| phase46p | OURS-B-ONLY+HMM | H1 | ARGMIN | 3 | 92 | 92 | 0 | 0.4891 | 1.45 | 1 | 89 | 0.01124 | 92 | 1 | 3 | 1 | 0 | 0 | 0 | — | — |
| phase46p | OURS-B-ONLY+HMM | H1 | FG_2PCT_ONE_DRAW | 3 | 92 | 92 | 0 | 0.3152 | 1 | 0 | 89 | 0 | 92 | 0 | 2 | 0 | 0 | 0 | 0 | 0.02475 | 0.0328 |
| phase46p | OURS-B-ONLY+HMM | H1 | FG_HARD_0ERR_UPPER_BOUND | 3 | 92 | 92 | 0 | 0.3152 | 1 | 0 | 89 | 0 | 92 | 0 | 2 | 0 | 0 | 0 | 0 | 0.01975 | 0.02546 |
| phase46p | OURS-B-ONLY+HMM | H1 | HMM_FORWARD | 3 | 92 | 92 | 0 | 0.337 | 1 | 0 | 89 | 0 | 92 | 0 | 3 | 0 | 0 | 0 | 0 | — | — |
| phase46p | OURS-B-ONLY+HMM | H2 | ARGMIN | 3 | 265 | 265 | 0 | 3.279 | 7.8 | 72 | 262 | 0.2748 | 263 | 1 | 1 | 1 | 0 | 0 | 36 | — | — |
| phase46p | OURS-B-ONLY+HMM | H2 | FG_2PCT_ONE_DRAW | 3 | 265 | 265 | 0 | 2.687 | 7 | 27 | 262 | 0.1031 | 263 | 5 | 1 | 1 | 0 | 0 | 36 | 0.0247 | 0.1532 |
| phase46p | OURS-B-ONLY+HMM | H2 | FG_HARD_0ERR_UPPER_BOUND | 3 | 265 | 265 | 0 | 2.687 | 7 | 26 | 262 | 0.09924 | 263 | 5 | 1 | 1 | 0 | 0 | 36 | 0.01964 | 0.03531 |
| phase46p | OURS-B-ONLY+HMM | H2 | HMM_FORWARD | 3 | 265 | 265 | 0 | 2.536 | 7 | 13 | 262 | 0.04962 | 263 | 0 | 0 | 0 | 0 | 0 | 36 | — | — |
| phase46p | OURS-B-ONLY+HMM | L2 | ARGMIN | 3 | 167 | 167 | 0 | 2.204 | 6 | 40 | 164 | 0.2439 | 166 | 2 | 2 | 2 | 0 | 0 | 11 | — | — |
| phase46p | OURS-B-ONLY+HMM | L2 | FG_2PCT_ONE_DRAW | 3 | 167 | 167 | 0 | 1.868 | 6 | 16 | 164 | 0.09756 | 166 | 2 | 2 | 2 | 0 | 0 | 11 | 0.02809 | 0.311 |
| phase46p | OURS-B-ONLY+HMM | L2 | FG_HARD_0ERR_UPPER_BOUND | 3 | 167 | 167 | 0 | 1.85 | 6 | 16 | 164 | 0.09756 | 166 | 2 | 2 | 2 | 0 | 0 | 11 | 0.0241 | 0.05724 |
| phase46p | OURS-B-ONLY+HMM | L2 | HMM_FORWARD | 3 | 167 | 167 | 0 | 1.725 | 5.7 | 15 | 164 | 0.09146 | 166 | 2 | 2 | 2 | 0 | 0 | 11 | — | — |
| phase46p | OURS-B-ONLY+HMM | LC | ARGMIN | 3 | 91 | 91 | 0 | 0.6484 | 2 | 3 | 88 | 0.03409 | 91 | 0 | 3 | 0 | 0 | 0 | 0 | — | — |
| phase46p | OURS-B-ONLY+HMM | LC | FG_2PCT_ONE_DRAW | 3 | 91 | 91 | 0 | 0.3846 | 1 | 0 | 88 | 0 | 91 | 0 | 3 | 0 | 0 | 0 | 0 | 0.02449 | 0.03189 |
| phase46p | OURS-B-ONLY+HMM | LC | FG_HARD_0ERR_UPPER_BOUND | 3 | 91 | 91 | 0 | 0.3846 | 1 | 0 | 88 | 0 | 91 | 0 | 3 | 0 | 0 | 0 | 0 | 0.01943 | 0.02511 |
| phase46p | OURS-B-ONLY+HMM | LC | HMM_FORWARD | 3 | 91 | 91 | 0 | 0.4835 | 2 | 2 | 88 | 0.02273 | 91 | 0 | 3 | 0 | 0 | 0 | 0 | — | — |
| phase46p | OURS-B-ONLY+HMM | SLW | ARGMIN | 3 | 225 | 225 | 0 | 2.649 | 11.8 | 46 | 222 | 0.2072 | 225 | 4 | 2 | 2 | 0 | 0 | 30 | — | — |
| phase46p | OURS-B-ONLY+HMM | SLW | FG_2PCT_ONE_DRAW | 3 | 225 | 225 | 0 | 2.271 | 11.8 | 16 | 222 | 0.07207 | 225 | 5 | 2 | 2 | 0 | 2 | 30 | 0.02542 | 0.3268 |
| phase46p | OURS-B-ONLY+HMM | SLW | FG_HARD_0ERR_UPPER_BOUND | 3 | 225 | 225 | 0 | 2.276 | 11.8 | 16 | 222 | 0.07207 | 225 | 5 | 2 | 2 | 0 | 2 | 30 | 0.02009 | 0.03807 |
| phase46p | OURS-B-ONLY+HMM | SLW | HMM_FORWARD | 3 | 225 | 225 | 0 | 2.32 | 11.8 | 12 | 222 | 0.05405 | 225 | 1 | 1 | 1 | 0 | 0 | 30 | — | — |
| phase47c | NOMAD_RAW | H1 | ARGMIN | 4 | 115 | 115 | 0 | 0.7478 | 4 | 6 | 111 | 0.05405 | 115 | 2 | 4 | 2 | 0 | 0 | 2 | — | — |
| phase47c | NOMAD_RAW | H1 | FG_2PCT_ONE_DRAW | 4 | 115 | 115 | 0 | 0.5217 | 1 | 4 | 111 | 0.03604 | 115 | 2 | 3 | 2 | 0 | 0 | 2 | 0.02494 | 0.03462 |
| phase47c | NOMAD_RAW | H1 | FG_HARD_0ERR_UPPER_BOUND | 4 | 115 | 115 | 0 | 0.5217 | 1 | 4 | 111 | 0.03604 | 115 | 2 | 3 | 2 | 0 | 0 | 2 | 0.01946 | 0.02818 |
| phase47c | NOMAD_RAW | H1 | HMM_FORWARD | 4 | 115 | 115 | 0 | 0.4087 | 1 | 1 | 111 | 0.009009 | 115 | 0 | 1 | 0 | 0 | 0 | 2 | — | — |
| phase47c | NOMAD_RAW | H2 | ARGMIN | 4 | 61 | 61 | 0 | 3.328 | 10 | 14 | 57 | 0.2456 | 60 | 2 | 2 | 2 | 0 | 0 | 16 | — | — |
| phase47c | NOMAD_RAW | H2 | FG_2PCT_ONE_DRAW | 4 | 61 | 61 | 0 | 1.361 | 7 | 5 | 57 | 0.08772 | 60 | 0 | 0 | 0 | 0 | 5 | 16 | 0.02004 | 0.03306 |
| phase47c | NOMAD_RAW | H2 | FG_HARD_0ERR_UPPER_BOUND | 4 | 61 | 61 | 0 | 1.344 | 7 | 6 | 57 | 0.1053 | 60 | 0 | 0 | 0 | 0 | 5 | 16 | 0.01423 | 0.02541 |
| phase47c | NOMAD_RAW | H2 | HMM_FORWARD | 4 | 61 | 61 | 0 | 1.787 | 6 | 4 | 57 | 0.07018 | 60 | 0 | 0 | 0 | 0 | 0 | 16 | — | — |
| phase47c | NOMAD_RAW | L2 | ARGMIN | 4 | 89 | 89 | 0 | 2.663 | 10.6 | 21 | 85 | 0.2471 | 89 | 4 | 4 | 4 | 0 | 0 | 17 | — | — |
| phase47c | NOMAD_RAW | L2 | FG_2PCT_ONE_DRAW | 4 | 89 | 89 | 0 | 1.303 | 6 | 6 | 85 | 0.07059 | 89 | 1 | 1 | 1 | 0 | 2 | 17 | 0.022 | 0.3199 |
| phase47c | NOMAD_RAW | L2 | FG_HARD_0ERR_UPPER_BOUND | 4 | 89 | 89 | 0 | 1.303 | 6 | 6 | 85 | 0.07059 | 89 | 1 | 1 | 1 | 0 | 2 | 17 | 0.01791 | 0.05333 |
| phase47c | NOMAD_RAW | L2 | HMM_FORWARD | 4 | 89 | 89 | 0 | 1.652 | 6 | 9 | 85 | 0.1059 | 89 | 1 | 1 | 1 | 0 | 0 | 17 | — | — |
| phase47c | NOMAD_RAW | LC | ARGMIN | 4 | 130 | 130 | 0 | 0.9308 | 4 | 15 | 126 | 0.119 | 129 | 0 | 3 | 0 | 0 | 0 | 3 | — | — |
| phase47c | NOMAD_RAW | LC | FG_2PCT_ONE_DRAW | 4 | 130 | 130 | 0 | 0.7769 | 5 | 4 | 126 | 0.03175 | 129 | 10 | 3 | 2 | 0 | 1 | 3 | 0.02499 | 0.2902 |
| phase47c | NOMAD_RAW | LC | FG_HARD_0ERR_UPPER_BOUND | 4 | 130 | 130 | 0 | 0.7846 | 5 | 4 | 126 | 0.03175 | 129 | 10 | 3 | 2 | 0 | 1 | 3 | 0.01914 | 0.03187 |
| phase47c | NOMAD_RAW | LC | HMM_FORWARD | 4 | 130 | 130 | 0 | 0.6 | 3.55 | 5 | 126 | 0.03968 | 129 | 0 | 2 | 0 | 0 | 0 | 3 | — | — |
| phase47c | NOMAD_RAW | SLW | ARGMIN | 4 | 62 | 62 | 0 | 1.145 | 5.95 | 10 | 58 | 0.1724 | 59 | 1 | 1 | 1 | 0 | 0 | 3 | — | — |
| phase47c | NOMAD_RAW | SLW | FG_2PCT_ONE_DRAW | 4 | 62 | 62 | 0 | 0.4355 | 2.9 | 1 | 58 | 0.01724 | 59 | 0 | 0 | 0 | 0 | 2 | 3 | 0.01923 | 0.03374 |
| phase47c | NOMAD_RAW | SLW | FG_HARD_0ERR_UPPER_BOUND | 4 | 62 | 62 | 0 | 0.4355 | 2.9 | 1 | 58 | 0.01724 | 59 | 0 | 0 | 0 | 0 | 2 | 3 | 0.0149 | 0.02555 |
| phase47c | NOMAD_RAW | SLW | HMM_FORWARD | 4 | 62 | 62 | 0 | 0.6129 | 2.95 | 2 | 58 | 0.03448 | 59 | 0 | 0 | 0 | 0 | 0 | 3 | — | — |
| phase47c | OURS-DETOUR | H1 | ARGMIN | 4 | 103 | 103 | 0 | 0.7087 | 2 | 2 | 99 | 0.0202 | 103 | 2 | 4 | 2 | 0 | 0 | 4 | — | — |
| phase47c | OURS-DETOUR | H1 | FG_2PCT_ONE_DRAW | 4 | 103 | 103 | 0 | 0.3981 | 1 | 1 | 99 | 0.0101 | 103 | 1 | 2 | 1 | 0 | 2 | 4 | 0.02482 | 0.03467 |
| phase47c | OURS-DETOUR | H1 | FG_HARD_0ERR_UPPER_BOUND | 4 | 103 | 103 | 0 | 0.4078 | 1 | 1 | 99 | 0.0101 | 103 | 1 | 2 | 1 | 0 | 2 | 4 | 0.01964 | 0.02917 |
| phase47c | OURS-DETOUR | H1 | HMM_FORWARD | 4 | 103 | 103 | 0 | 0.4466 | 1 | 0 | 99 | 0 | 103 | 0 | 1 | 0 | 0 | 0 | 4 | — | — |
| phase47c | OURS-DETOUR | H2 | ARGMIN | 4 | 76 | 76 | 0 | 4.395 | 13 | 27 | 72 | 0.375 | 76 | 4 | 4 | 4 | 0 | 0 | 24 | — | — |
| phase47c | OURS-DETOUR | H2 | FG_2PCT_ONE_DRAW | 4 | 76 | 76 | 0 | 2.408 | 11.25 | 7 | 72 | 0.09722 | 76 | 0 | 0 | 0 | 0 | 4 | 24 | 0.02307 | 0.2065 |
| phase47c | OURS-DETOUR | H2 | FG_HARD_0ERR_UPPER_BOUND | 4 | 76 | 76 | 0 | 2.474 | 12.25 | 8 | 72 | 0.1111 | 76 | 0 | 0 | 0 | 0 | 4 | 24 | 0.01886 | 0.03452 |
| phase47c | OURS-DETOUR | H2 | HMM_FORWARD | 4 | 76 | 76 | 0 | 2.526 | 12 | 6 | 72 | 0.08333 | 76 | 0 | 0 | 0 | 0 | 0 | 24 | — | — |
| phase47c | OURS-DETOUR | L2 | ARGMIN | 4 | 66 | 66 | 0 | 3.455 | 13 | 18 | 62 | 0.2903 | 66 | 4 | 4 | 4 | 0 | 0 | 15 | — | — |
| phase47c | OURS-DETOUR | L2 | FG_2PCT_ONE_DRAW | 4 | 66 | 66 | 0 | 1.061 | 4 | 5 | 62 | 0.08065 | 66 | 0 | 0 | 0 | 0 | 8 | 15 | 0.01806 | 0.03069 |
| phase47c | OURS-DETOUR | L2 | FG_HARD_0ERR_UPPER_BOUND | 4 | 66 | 66 | 0 | 1.061 | 4 | 5 | 62 | 0.08065 | 66 | 0 | 0 | 0 | 0 | 9 | 15 | 0.01425 | 0.02453 |
| phase47c | OURS-DETOUR | L2 | HMM_FORWARD | 4 | 66 | 66 | 0 | 1.742 | 7 | 8 | 62 | 0.129 | 66 | 1 | 1 | 1 | 0 | 0 | 15 | — | — |
| phase47c | OURS-DETOUR | LC | ARGMIN | 4 | 99 | 99 | 0 | 0.4747 | 1 | 2 | 95 | 0.02105 | 99 | 2 | 4 | 2 | 0 | 0 | 0 | — | — |
| phase47c | OURS-DETOUR | LC | FG_2PCT_ONE_DRAW | 4 | 99 | 99 | 0 | 0.4646 | 1 | 0 | 95 | 0 | 99 | 0 | 2 | 0 | 0 | 0 | 0 | 0.02507 | 0.03483 |
| phase47c | OURS-DETOUR | LC | FG_HARD_0ERR_UPPER_BOUND | 4 | 99 | 99 | 0 | 0.4646 | 1 | 0 | 95 | 0 | 99 | 0 | 2 | 0 | 0 | 0 | 0 | 0.01965 | 0.02825 |
| phase47c | OURS-DETOUR | LC | HMM_FORWARD | 4 | 99 | 99 | 0 | 0.3333 | 1 | 0 | 95 | 0 | 99 | 0 | 0 | 0 | 0 | 0 | 0 | — | — |
| phase47c | OURS-DETOUR | SLW | ARGMIN | 4 | 141 | 141 | 0 | 1.404 | 4 | 23 | 137 | 0.1679 | 140 | 3 | 3 | 3 | 0 | 0 | 3 | — | — |
| phase47c | OURS-DETOUR | SLW | FG_2PCT_ONE_DRAW | 4 | 141 | 141 | 0 | 0.766 | 4 | 5 | 137 | 0.0365 | 140 | 0 | 0 | 0 | 0 | 1 | 3 | 0.02454 | 0.032 |
| phase47c | OURS-DETOUR | SLW | FG_HARD_0ERR_UPPER_BOUND | 4 | 141 | 141 | 0 | 0.7518 | 4 | 5 | 137 | 0.0365 | 140 | 0 | 0 | 0 | 0 | 1 | 3 | 0.01903 | 0.02668 |
| phase47c | OURS-DETOUR | SLW | HMM_FORWARD | 4 | 141 | 141 | 0 | 0.5603 | 2 | 4 | 137 | 0.0292 | 140 | 0 | 0 | 0 | 0 | 0 | 3 | — | — |
| phase47c | OURS-DETOUR+HMM | H1 | ARGMIN | 4 | 118 | 118 | 0 | 0.5678 | 2 | 7 | 114 | 0.0614 | 118 | 1 | 4 | 1 | 0 | 0 | 0 | — | — |
| phase47c | OURS-DETOUR+HMM | H1 | FG_2PCT_ONE_DRAW | 4 | 118 | 118 | 0 | 0.3136 | 1 | 0 | 114 | 0 | 118 | 0 | 3 | 0 | 0 | 0 | 0 | 0.02526 | 0.03455 |
| phase47c | OURS-DETOUR+HMM | H1 | FG_HARD_0ERR_UPPER_BOUND | 4 | 118 | 118 | 0 | 0.3051 | 1 | 0 | 114 | 0 | 118 | 0 | 3 | 0 | 0 | 0 | 0 | 0.01948 | 0.02868 |
| phase47c | OURS-DETOUR+HMM | H1 | HMM_FORWARD | 4 | 118 | 118 | 0 | 0.3559 | 1 | 0 | 114 | 0 | 118 | 0 | 4 | 0 | 0 | 0 | 0 | — | — |
| phase47c | OURS-DETOUR+HMM | H2 | ARGMIN | 4 | 259 | 259 | 0 | 3.301 | 14.1 | 64 | 255 | 0.251 | 259 | 5 | 4 | 3 | 0 | 0 | 35 | — | — |
| phase47c | OURS-DETOUR+HMM | H2 | FG_2PCT_ONE_DRAW | 4 | 259 | 259 | 0 | 2.672 | 12 | 16 | 255 | 0.06275 | 259 | 3 | 3 | 3 | 0 | 0 | 35 | 0.02762 | 0.2134 |
| phase47c | OURS-DETOUR+HMM | H2 | FG_HARD_0ERR_UPPER_BOUND | 4 | 259 | 259 | 0 | 2.687 | 12 | 14 | 255 | 0.0549 | 259 | 3 | 3 | 3 | 0 | 0 | 35 | 0.02204 | 0.04545 |
| phase47c | OURS-DETOUR+HMM | H2 | HMM_FORWARD | 4 | 259 | 259 | 0 | 2.421 | 14.1 | 9 | 255 | 0.03529 | 259 | 3 | 4 | 3 | 0 | 0 | 35 | — | — |
| phase47c | OURS-DETOUR+HMM | L2 | ARGMIN | 4 | 206 | 206 | 0 | 3.66 | 16 | 39 | 202 | 0.1931 | 206 | 2 | 4 | 2 | 0 | 0 | 38 | — | — |
| phase47c | OURS-DETOUR+HMM | L2 | FG_2PCT_ONE_DRAW | 4 | 206 | 206 | 0 | 3.136 | 16 | 15 | 202 | 0.07426 | 206 | 0 | 3 | 0 | 0 | 1 | 38 | 0.02392 | 0.326 |
| phase47c | OURS-DETOUR+HMM | L2 | FG_HARD_0ERR_UPPER_BOUND | 4 | 206 | 206 | 0 | 3.146 | 16 | 16 | 202 | 0.07921 | 206 | 0 | 3 | 0 | 0 | 1 | 38 | 0.01949 | 0.05038 |
| phase47c | OURS-DETOUR+HMM | L2 | HMM_FORWARD | 4 | 206 | 206 | 0 | 3.141 | 16 | 7 | 202 | 0.03465 | 206 | 1 | 4 | 1 | 0 | 0 | 38 | — | — |
| phase47c | OURS-DETOUR+HMM | LC | ARGMIN | 4 | 109 | 109 | 0 | 0.5413 | 2 | 4 | 105 | 0.0381 | 109 | 0 | 4 | 0 | 0 | 0 | 0 | — | — |
| phase47c | OURS-DETOUR+HMM | LC | FG_2PCT_ONE_DRAW | 4 | 109 | 109 | 0 | 0.4312 | 1 | 0 | 105 | 0 | 109 | 1 | 4 | 1 | 0 | 0 | 0 | 0.02522 | 0.03483 |
| phase47c | OURS-DETOUR+HMM | LC | FG_HARD_0ERR_UPPER_BOUND | 4 | 109 | 109 | 0 | 0.4312 | 1 | 0 | 105 | 0 | 109 | 1 | 4 | 1 | 0 | 0 | 0 | 0.01984 | 0.02815 |
| phase47c | OURS-DETOUR+HMM | LC | HMM_FORWARD | 4 | 109 | 109 | 0 | 0.422 | 1 | 0 | 105 | 0 | 109 | 0 | 4 | 0 | 0 | 0 | 0 | — | — |
| phase47c | OURS-DETOUR+HMM | SLW | ARGMIN | 4 | 286 | 286 | 0 | 2.465 | 11 | 60 | 282 | 0.2128 | 284 | 0 | 2 | 0 | 0 | 0 | 50 | — | — |
| phase47c | OURS-DETOUR+HMM | SLW | FG_2PCT_ONE_DRAW | 4 | 286 | 286 | 0 | 2.056 | 11 | 15 | 282 | 0.05319 | 284 | 0 | 2 | 0 | 0 | 1 | 50 | 0.0266 | 0.2902 |
| phase47c | OURS-DETOUR+HMM | SLW | FG_HARD_0ERR_UPPER_BOUND | 4 | 286 | 286 | 0 | 2.059 | 11 | 15 | 282 | 0.05319 | 284 | 0 | 2 | 0 | 0 | 1 | 50 | 0.02096 | 0.03659 |
| phase47c | OURS-DETOUR+HMM | SLW | HMM_FORWARD | 4 | 286 | 286 | 0 | 2.196 | 11 | 7 | 282 | 0.02482 | 284 | 0 | 2 | 0 | 0 | 0 | 50 | — | — |

| table |
|---|
| 이탈 구간 수와 로그 가용 범위 |

| run | phase | scene | seed | method | records | off_path_intervals | off_path_episodes | projected_intervals | projection_abs_delta_exceeds_travel | median_node_spacing_m | noise_base_seed | noise_run_word | hmm_logged_checks | source_localization | virtual_eligible_inferences | window_limited |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| phase43p/H1/217/OURS-DETOUR+HMM | phase43p | H1 | 217 | OURS-DETOUR+HMM | 34 | 0 | 0 | 33 | 3 | 0.3995 | 20261112 | 394816773 | 34 | HMM | 34 | 34 |
| phase43p/H1/219/OURS-DETOUR+HMM | phase43p | H1 | 219 | OURS-DETOUR+HMM | 57 | 32 | 1 | 24 | 2 | 0.3995 | 20261112 | 1147953966 | 57 | HMM | 57 | 57 |
| phase43p/H1/220/OURS-DETOUR+HMM | phase43p | H1 | 220 | OURS-DETOUR+HMM | 28 | 0 | 0 | 27 | 4 | 0.3995 | 20261112 | 670315783 | 28 | HMM | 28 | 28 |
| phase43p/H2/217/OURS-DETOUR+HMM | phase43p | H2 | 217 | OURS-DETOUR+HMM | 74 | 24 | 2 | 49 | 0 | 0.4 | 20261112 | 1694528586 | 74 | HMM | 74 | 74 |
| phase43p/H2/219/OURS-DETOUR+HMM | phase43p | H2 | 219 | OURS-DETOUR+HMM | 86 | 33 | 2 | 52 | 0 | 0.4 | 20261112 | 586731273 | 86 | HMM | 86 | 86 |
| phase43p/H2/220/OURS-DETOUR+HMM | phase43p | H2 | 220 | OURS-DETOUR+HMM | 88 | 51 | 3 | 36 | 0 | 0.4 | 20261112 | 1240224020 | 88 | HMM | 87 | 88 |
| phase43p/L2/217/OURS-DETOUR+HMM | phase43p | L2 | 217 | OURS-DETOUR+HMM | 89 | 26 | 2 | 62 | 0 | 0.4 | 20261112 | 3387644361 | 89 | HMM | 88 | 89 |
| phase43p/L2/219/OURS-DETOUR+HMM | phase43p | L2 | 219 | OURS-DETOUR+HMM | 56 | 0 | 0 | 55 | 0 | 0.4 | 20261112 | 2951859771 | 56 | HMM | 56 | 56 |
| phase43p/L2/220/OURS-DETOUR+HMM | phase43p | L2 | 220 | OURS-DETOUR+HMM | 46 | 23 | 1 | 22 | 0 | 0.4 | 20261112 | 3436006436 | 46 | HMM | 46 | 46 |
| phase43p/LC/217/OURS-DETOUR+HMM | phase43p | LC | 217 | OURS-DETOUR+HMM | 37 | 0 | 0 | 36 | 4 | 0.3995 | 20261112 | 2853931459 | 37 | HMM | 37 | 37 |
| phase43p/LC/219/OURS-DETOUR+HMM | phase43p | LC | 219 | OURS-DETOUR+HMM | 26 | 0 | 0 | 25 | 5 | 0.3995 | 20261112 | 3952498262 | 26 | HMM | 26 | 26 |
| phase43p/LC/220/OURS-DETOUR+HMM | phase43p | LC | 220 | OURS-DETOUR+HMM | 26 | 0 | 0 | 25 | 5 | 0.3995 | 20261112 | 3884863987 | 26 | HMM | 26 | 26 |
| phase43p/SLW/217/OURS-DETOUR+HMM | phase43p | SLW | 217 | OURS-DETOUR+HMM | 59 | 0 | 0 | 58 | 6 | 0.3963 | 20261112 | 2435628282 | 59 | HMM | 59 | 59 |
| phase43p/SLW/219/OURS-DETOUR+HMM | phase43p | SLW | 219 | OURS-DETOUR+HMM | 73 | 0 | 0 | 72 | 4 | 0.3963 | 20261112 | 1316760221 | 73 | HMM | 73 | 73 |
| phase43p/SLW/220/OURS-DETOUR+HMM | phase43p | SLW | 220 | OURS-DETOUR+HMM | 61 | 0 | 0 | 60 | 5 | 0.3963 | 20261112 | 3646771081 | 61 | HMM | 61 | 61 |
| phase44p/H2/217/OURS-DETOUR+HMM | phase44p | H2 | 217 | OURS-DETOUR+HMM | 62 | 10 | 1 | 51 | 0 | 0.4 | 20261112 | 3759945941 | 62 | HMM | 62 | 62 |
| phase44p/H2/219/OURS-DETOUR+HMM | phase44p | H2 | 219 | OURS-DETOUR+HMM | 73 | 12 | 1 | 60 | 0 | 0.4 | 20261112 | 2988899603 | 73 | HMM | 73 | 73 |
| phase44p/H2/220/OURS-DETOUR+HMM | phase44p | H2 | 220 | OURS-DETOUR+HMM | 89 | 0 | 0 | 88 | 0 | 0.4 | 20261112 | 3916061559 | 89 | HMM | 88 | 89 |
| phase44p/L2/217/OURS-DETOUR+HMM | phase44p | L2 | 217 | OURS-DETOUR+HMM | 89 | 23 | 3 | 65 | 0 | 0.4 | 20261112 | 1241785463 | 89 | HMM | 88 | 89 |
| phase44p/L2/219/OURS-DETOUR+HMM | phase44p | L2 | 219 | OURS-DETOUR+HMM | 74 | 27 | 2 | 46 | 0 | 0.4 | 20261112 | 2230083392 | 74 | HMM | 74 | 74 |
| phase44p/L2/220/OURS-DETOUR+HMM | phase44p | L2 | 220 | OURS-DETOUR+HMM | 89 | 47 | 2 | 41 | 0 | 0.4 | 20261112 | 2577975012 | 89 | HMM | 88 | 89 |
| phase45p/H1/217/OURS+HMM | phase45p | H1 | 217 | OURS+HMM | 30 | 0 | 0 | 29 | 5 | 0.3995 | 20261112 | 3704839856 | 30 | HMM | 30 | 30 |
| phase45p/H1/219/OURS+HMM | phase45p | H1 | 219 | OURS+HMM | 89 | 49 | 2 | 39 | 3 | 0.3995 | 20261112 | 1357236953 | 89 | HMM | 89 | 89 |
| phase45p/H1/220/OURS+HMM | phase45p | H1 | 220 | OURS+HMM | 27 | 0 | 0 | 26 | 5 | 0.3995 | 20261112 | 3306178448 | 27 | HMM | 27 | 27 |
| phase45p/H2/217/OURS+HMM | phase45p | H2 | 217 | OURS+HMM | 87 | 38 | 2 | 48 | 0 | 0.4 | 20261112 | 35227285 | 87 | HMM | 87 | 87 |
| phase45p/H2/219/OURS+HMM | phase45p | H2 | 219 | OURS+HMM | 89 | 42 | 3 | 46 | 0 | 0.4 | 20261112 | 1758493403 | 89 | HMM | 88 | 89 |
| phase45p/H2/220/OURS+HMM | phase45p | H2 | 220 | OURS+HMM | 49 | 8 | 1 | 40 | 0 | 0.4 | 20261112 | 3089664558 | 49 | HMM | 49 | 49 |
| phase45p/L2/217/OURS+HMM | phase45p | L2 | 217 | OURS+HMM | 78 | 30 | 2 | 47 | 0 | 0.4 | 20261112 | 4249267319 | 78 | HMM | 78 | 78 |
| phase45p/L2/219/OURS+HMM | phase45p | L2 | 219 | OURS+HMM | 39 | 17 | 1 | 21 | 0 | 0.4 | 20261112 | 3480939264 | 39 | HMM | 39 | 39 |
| phase45p/L2/220/OURS+HMM | phase45p | L2 | 220 | OURS+HMM | 46 | 32 | 1 | 13 | 0 | 0.4 | 20261112 | 3134001541 | 46 | HMM | 46 | 46 |
| phase45p/LC/217/OURS+HMM | phase45p | LC | 217 | OURS+HMM | 30 | 0 | 0 | 29 | 4 | 0.3995 | 20261112 | 3980100638 | 30 | HMM | 30 | 30 |
| phase45p/LC/219/OURS+HMM | phase45p | LC | 219 | OURS+HMM | 25 | 0 | 0 | 24 | 3 | 0.3995 | 20261112 | 1063594788 | 25 | HMM | 25 | 25 |
| phase45p/LC/220/OURS+HMM | phase45p | LC | 220 | OURS+HMM | 29 | 0 | 0 | 28 | 6 | 0.3995 | 20261112 | 2550303339 | 29 | HMM | 29 | 29 |
| phase45p/SLW/217/OURS+HMM | phase45p | SLW | 217 | OURS+HMM | 88 | 0 | 0 | 87 | 3 | 0.3963 | 20261112 | 3518683289 | 88 | HMM | 88 | 88 |
| phase45p/SLW/219/OURS+HMM | phase45p | SLW | 219 | OURS+HMM | 88 | 70 | 1 | 17 | 2 | 0.3963 | 20261112 | 75442849 | 88 | HMM | 88 | 88 |
| phase45p/SLW/220/OURS+HMM | phase45p | SLW | 220 | OURS+HMM | 89 | 6 | 1 | 82 | 3 | 0.3963 | 20261112 | 3255827474 | 89 | HMM | 88 | 89 |
| phase46p/H1/217/OURS-B-ONLY+HMM | phase46p | H1 | 217 | OURS-B-ONLY+HMM | 37 | 0 | 0 | 36 | 2 | 0.3995 | 20261112 | 3571671885 | 37 | HMM | 37 | 37 |
| phase46p/H1/219/OURS-B-ONLY+HMM | phase46p | H1 | 219 | OURS-B-ONLY+HMM | 26 | 0 | 0 | 25 | 5 | 0.3995 | 20261112 | 1923981261 | 26 | HMM | 26 | 26 |
| phase46p/H1/220/OURS-B-ONLY+HMM | phase46p | H1 | 220 | OURS-B-ONLY+HMM | 29 | 0 | 0 | 28 | 5 | 0.3995 | 20261112 | 969005099 | 29 | HMM | 29 | 29 |
| phase46p/H2/217/OURS-B-ONLY+HMM | phase46p | H2 | 217 | OURS-B-ONLY+HMM | 88 | 25 | 2 | 62 | 0 | 0.4 | 20261112 | 1580379143 | 88 | HMM | 87 | 88 |
| phase46p/H2/219/OURS-B-ONLY+HMM | phase46p | H2 | 219 | OURS-B-ONLY+HMM | 89 | 29 | 2 | 59 | 0 | 0.4 | 20261112 | 409434248 | 89 | HMM | 88 | 89 |
| phase46p/H2/220/OURS-B-ONLY+HMM | phase46p | H2 | 220 | OURS-B-ONLY+HMM | 88 | 23 | 2 | 64 | 0 | 0.4 | 20261112 | 1382733478 | 88 | HMM | 88 | 88 |
| phase46p/L2/217/OURS-B-ONLY+HMM | phase46p | L2 | 217 | OURS-B-ONLY+HMM | 90 | 47 | 2 | 42 | 0 | 0.4 | 20261112 | 2819679707 | 90 | HMM | 89 | 90 |
| phase46p/L2/219/OURS-B-ONLY+HMM | phase46p | L2 | 219 | OURS-B-ONLY+HMM | 38 | 22 | 1 | 15 | 0 | 0.4 | 20261112 | 2505056799 | 38 | HMM | 38 | 38 |
| phase46p/L2/220/OURS-B-ONLY+HMM | phase46p | L2 | 220 | OURS-B-ONLY+HMM | 39 | 20 | 1 | 18 | 0 | 0.4 | 20261112 | 270019478 | 39 | HMM | 39 | 39 |
| phase46p/LC/217/OURS-B-ONLY+HMM | phase46p | LC | 217 | OURS-B-ONLY+HMM | 30 | 0 | 0 | 29 | 4 | 0.3995 | 20261112 | 1298208234 | 30 | HMM | 30 | 30 |
| phase46p/LC/219/OURS-B-ONLY+HMM | phase46p | LC | 219 | OURS-B-ONLY+HMM | 33 | 0 | 0 | 32 | 4 | 0.3995 | 20261112 | 3657215809 | 33 | HMM | 33 | 33 |
| phase46p/LC/220/OURS-B-ONLY+HMM | phase46p | LC | 220 | OURS-B-ONLY+HMM | 28 | 0 | 0 | 27 | 7 | 0.3995 | 20261112 | 3811021769 | 28 | HMM | 28 | 28 |
| phase46p/SLW/217/OURS-B-ONLY+HMM | phase46p | SLW | 217 | OURS-B-ONLY+HMM | 88 | 22 | 2 | 65 | 3 | 0.3963 | 20261112 | 1168281901 | 88 | HMM | 88 | 88 |
| phase46p/SLW/219/OURS-B-ONLY+HMM | phase46p | SLW | 219 | OURS-B-ONLY+HMM | 82 | 24 | 1 | 57 | 3 | 0.3963 | 20261112 | 447176678 | 82 | HMM | 82 | 82 |
| phase46p/SLW/220/OURS-B-ONLY+HMM | phase46p | SLW | 220 | OURS-B-ONLY+HMM | 55 | 0 | 0 | 54 | 6 | 0.3963 | 20261112 | 4171118457 | 55 | HMM | 55 | 55 |
| phase47c/H1/221/NOMAD_RAW | phase47c | H1 | 221 | NOMAD_RAW | 25 | 0 | 0 | 24 | 4 | 0.3995 | 20261112 | 999733666 | 0 | ARGMIN | 25 | 25 |
| phase47c/H1/221/OURS-DETOUR+HMM | phase47c | H1 | 221 | OURS-DETOUR+HMM | 32 | 0 | 0 | 31 | 2 | 0.3995 | 20261112 | 1326609649 | 32 | HMM | 32 | 32 |
| phase47c/H1/221/OURS-DETOUR | phase47c | H1 | 221 | OURS-DETOUR | 29 | 0 | 0 | 28 | 1 | 0.3995 | 20261112 | 1746725809 | 0 | ARGMIN | 29 | 29 |
| phase47c/H1/222/NOMAD_RAW | phase47c | H1 | 222 | NOMAD_RAW | 29 | 0 | 0 | 28 | 6 | 0.3995 | 20261112 | 2885578801 | 0 | ARGMIN | 29 | 29 |
| phase47c/H1/222/OURS-DETOUR+HMM | phase47c | H1 | 222 | OURS-DETOUR+HMM | 28 | 0 | 0 | 27 | 3 | 0.3995 | 20261112 | 1269325823 | 28 | HMM | 28 | 28 |
| phase47c/H1/222/OURS-DETOUR | phase47c | H1 | 222 | OURS-DETOUR | 29 | 0 | 0 | 28 | 4 | 0.3995 | 20261112 | 3229060516 | 0 | ARGMIN | 29 | 29 |
| phase47c/H1/223/NOMAD_RAW | phase47c | H1 | 223 | NOMAD_RAW | 35 | 0 | 0 | 34 | 5 | 0.3995 | 20261112 | 2863367158 | 0 | ARGMIN | 35 | 35 |
| phase47c/H1/223/OURS-DETOUR+HMM | phase47c | H1 | 223 | OURS-DETOUR+HMM | 30 | 0 | 0 | 29 | 1 | 0.3995 | 20261112 | 3373894043 | 30 | HMM | 30 | 30 |
| phase47c/H1/223/OURS-DETOUR | phase47c | H1 | 223 | OURS-DETOUR | 26 | 0 | 0 | 25 | 2 | 0.3995 | 20261112 | 977376951 | 0 | ARGMIN | 26 | 26 |
| phase47c/H1/224/NOMAD_RAW | phase47c | H1 | 224 | NOMAD_RAW | 26 | 0 | 0 | 25 | 3 | 0.3995 | 20261112 | 3844684523 | 0 | ARGMIN | 26 | 26 |
| phase47c/H1/224/OURS-DETOUR+HMM | phase47c | H1 | 224 | OURS-DETOUR+HMM | 28 | 0 | 0 | 27 | 5 | 0.3995 | 20261112 | 3011138993 | 28 | HMM | 28 | 28 |
| phase47c/H1/224/OURS-DETOUR | phase47c | H1 | 224 | OURS-DETOUR | 19 | 0 | 0 | 18 | 1 | 0.3995 | 20261112 | 986818238 | 0 | ARGMIN | 19 | 19 |
| phase47c/H2/221/NOMAD_RAW | phase47c | H2 | 221 | NOMAD_RAW | 17 | 1 | 1 | 15 | 0 | 0.4 | 20261112 | 2335237400 | 0 | ARGMIN | 16 | 17 |
| phase47c/H2/221/OURS-DETOUR+HMM | phase47c | H2 | 221 | OURS-DETOUR+HMM | 82 | 34 | 3 | 47 | 0 | 0.4 | 20261112 | 1900449343 | 82 | HMM | 82 | 82 |
| phase47c/H2/221/OURS-DETOUR | phase47c | H2 | 221 | OURS-DETOUR | 14 | 0 | 0 | 13 | 0 | 0.4 | 20261112 | 307581355 | 0 | ARGMIN | 14 | 14 |
| phase47c/H2/222/NOMAD_RAW | phase47c | H2 | 222 | NOMAD_RAW | 17 | 0 | 0 | 16 | 0 | 0.4 | 20261112 | 723468235 | 0 | ARGMIN | 17 | 17 |
| phase47c/H2/222/OURS-DETOUR+HMM | phase47c | H2 | 222 | OURS-DETOUR+HMM | 47 | 26 | 1 | 20 | 0 | 0.4 | 20261112 | 363485255 | 47 | HMM | 47 | 47 |
| phase47c/H2/222/OURS-DETOUR | phase47c | H2 | 222 | OURS-DETOUR | 19 | 0 | 0 | 18 | 0 | 0.4 | 20261112 | 10344342 | 0 | ARGMIN | 19 | 19 |
| phase47c/H2/223/NOMAD_RAW | phase47c | H2 | 223 | NOMAD_RAW | 13 | 0 | 0 | 12 | 0 | 0.4 | 20261112 | 4032993552 | 0 | ARGMIN | 13 | 13 |
| phase47c/H2/223/OURS-DETOUR+HMM | phase47c | H2 | 223 | OURS-DETOUR+HMM | 45 | 8 | 1 | 36 | 0 | 0.4 | 20261112 | 3148120679 | 45 | HMM | 45 | 45 |
| phase47c/H2/223/OURS-DETOUR | phase47c | H2 | 223 | OURS-DETOUR | 18 | 0 | 0 | 17 | 0 | 0.4 | 20261112 | 3559265645 | 0 | ARGMIN | 18 | 18 |
| phase47c/H2/224/NOMAD_RAW | phase47c | H2 | 224 | NOMAD_RAW | 14 | 1 | 1 | 12 | 0 | 0.4 | 20261112 | 185606811 | 0 | ARGMIN | 14 | 14 |
| phase47c/H2/224/OURS-DETOUR+HMM | phase47c | H2 | 224 | OURS-DETOUR+HMM | 85 | 24 | 3 | 60 | 0 | 0.4 | 20261112 | 2862116857 | 85 | HMM | 85 | 85 |
| phase47c/H2/224/OURS-DETOUR | phase47c | H2 | 224 | OURS-DETOUR | 25 | 8 | 1 | 16 | 0 | 0.4 | 20261112 | 3976940360 | 0 | ARGMIN | 25 | 25 |
| phase47c/L2/221/NOMAD_RAW | phase47c | L2 | 221 | NOMAD_RAW | 18 | 0 | 0 | 17 | 0 | 0.4 | 20261112 | 3688904153 | 0 | ARGMIN | 18 | 18 |
| phase47c/L2/221/OURS-DETOUR+HMM | phase47c | L2 | 221 | OURS-DETOUR+HMM | 42 | 20 | 1 | 21 | 0 | 0.4 | 20261112 | 4012727216 | 42 | HMM | 42 | 42 |
| phase47c/L2/221/OURS-DETOUR | phase47c | L2 | 221 | OURS-DETOUR | 20 | 0 | 0 | 19 | 0 | 0.4 | 20261112 | 1153695244 | 0 | ARGMIN | 20 | 20 |
| phase47c/L2/222/NOMAD_RAW | phase47c | L2 | 222 | NOMAD_RAW | 43 | 26 | 2 | 16 | 0 | 0.4 | 20261112 | 1512256819 | 0 | ARGMIN | 43 | 43 |
| phase47c/L2/222/OURS-DETOUR+HMM | phase47c | L2 | 222 | OURS-DETOUR+HMM | 49 | 24 | 1 | 24 | 0 | 0.4 | 20261112 | 3782281966 | 49 | HMM | 49 | 49 |
| phase47c/L2/222/OURS-DETOUR | phase47c | L2 | 222 | OURS-DETOUR | 16 | 0 | 0 | 15 | 0 | 0.4 | 20261112 | 435524254 | 0 | ARGMIN | 16 | 16 |
| phase47c/L2/223/NOMAD_RAW | phase47c | L2 | 223 | NOMAD_RAW | 13 | 0 | 0 | 12 | 0 | 0.4 | 20261112 | 2906758095 | 0 | ARGMIN | 13 | 13 |
| phase47c/L2/223/OURS-DETOUR+HMM | phase47c | L2 | 223 | OURS-DETOUR+HMM | 64 | 0 | 0 | 63 | 0 | 0.4 | 20261112 | 2305563041 | 64 | HMM | 64 | 64 |
| phase47c/L2/223/OURS-DETOUR | phase47c | L2 | 223 | OURS-DETOUR | 17 | 0 | 0 | 16 | 0 | 0.4 | 20261112 | 2925514439 | 0 | ARGMIN | 17 | 17 |
| phase47c/L2/224/NOMAD_RAW | phase47c | L2 | 224 | NOMAD_RAW | 15 | 0 | 0 | 14 | 0 | 0.4 | 20261112 | 3404983897 | 0 | ARGMIN | 15 | 15 |
| phase47c/L2/224/OURS-DETOUR+HMM | phase47c | L2 | 224 | OURS-DETOUR+HMM | 51 | 12 | 2 | 38 | 0 | 0.4 | 20261112 | 3461135497 | 51 | HMM | 51 | 51 |
| phase47c/L2/224/OURS-DETOUR | phase47c | L2 | 224 | OURS-DETOUR | 13 | 0 | 0 | 12 | 0 | 0.4 | 20261112 | 2428659277 | 0 | ARGMIN | 13 | 13 |
| phase47c/LC/221/NOMAD_RAW | phase47c | LC | 221 | NOMAD_RAW | 40 | 4 | 1 | 35 | 6 | 0.3995 | 20261112 | 1545026203 | 0 | ARGMIN | 40 | 40 |
| phase47c/LC/221/OURS-DETOUR+HMM | phase47c | LC | 221 | OURS-DETOUR+HMM | 27 | 0 | 0 | 26 | 5 | 0.3995 | 20261112 | 2416691234 | 27 | HMM | 27 | 27 |
| phase47c/LC/221/OURS-DETOUR | phase47c | LC | 221 | OURS-DETOUR | 24 | 0 | 0 | 23 | 4 | 0.3995 | 20261112 | 1588322298 | 0 | ARGMIN | 24 | 24 |
| phase47c/LC/222/NOMAD_RAW | phase47c | LC | 222 | NOMAD_RAW | 27 | 0 | 0 | 26 | 5 | 0.3995 | 20261112 | 1762989386 | 0 | ARGMIN | 27 | 27 |
| phase47c/LC/222/OURS-DETOUR+HMM | phase47c | LC | 222 | OURS-DETOUR+HMM | 27 | 0 | 0 | 26 | 4 | 0.3995 | 20261112 | 48645591 | 27 | HMM | 27 | 27 |
| phase47c/LC/222/OURS-DETOUR | phase47c | LC | 222 | OURS-DETOUR | 24 | 0 | 0 | 23 | 4 | 0.3995 | 20261112 | 3620345770 | 0 | ARGMIN | 24 | 24 |
| phase47c/LC/223/NOMAD_RAW | phase47c | LC | 223 | NOMAD_RAW | 35 | 5 | 1 | 29 | 2 | 0.3995 | 20261112 | 4046341198 | 0 | ARGMIN | 34 | 35 |
| phase47c/LC/223/OURS-DETOUR+HMM | phase47c | LC | 223 | OURS-DETOUR+HMM | 28 | 0 | 0 | 27 | 3 | 0.3995 | 20261112 | 3210506847 | 28 | HMM | 28 | 28 |
| phase47c/LC/223/OURS-DETOUR | phase47c | LC | 223 | OURS-DETOUR | 26 | 0 | 0 | 25 | 3 | 0.3995 | 20261112 | 3216577663 | 0 | ARGMIN | 26 | 26 |
| phase47c/LC/224/NOMAD_RAW | phase47c | LC | 224 | NOMAD_RAW | 28 | 0 | 0 | 27 | 6 | 0.3995 | 20261112 | 131827590 | 0 | ARGMIN | 28 | 28 |
| phase47c/LC/224/OURS-DETOUR+HMM | phase47c | LC | 224 | OURS-DETOUR+HMM | 27 | 0 | 0 | 26 | 4 | 0.3995 | 20261112 | 2395388149 | 27 | HMM | 27 | 27 |
| phase47c/LC/224/OURS-DETOUR | phase47c | LC | 224 | OURS-DETOUR | 25 | 0 | 0 | 24 | 4 | 0.3995 | 20261112 | 963115576 | 0 | ARGMIN | 25 | 25 |
| phase47c/SLW/221/NOMAD_RAW | phase47c | SLW | 221 | NOMAD_RAW | 24 | 0 | 0 | 23 | 2 | 0.3963 | 20261112 | 365849337 | 0 | ARGMIN | 24 | 24 |
| phase47c/SLW/221/OURS-DETOUR+HMM | phase47c | SLW | 221 | OURS-DETOUR+HMM | 49 | 0 | 0 | 48 | 6 | 0.3963 | 20261112 | 2895973329 | 49 | HMM | 49 | 49 |
| phase47c/SLW/221/OURS-DETOUR | phase47c | SLW | 221 | OURS-DETOUR | 10 | 0 | 0 | 9 | 1 | 0.3963 | 20261112 | 1442768938 | 0 | ARGMIN | 10 | 10 |
| phase47c/SLW/222/NOMAD_RAW | phase47c | SLW | 222 | NOMAD_RAW | 10 | 0 | 0 | 9 | 1 | 0.3963 | 20261112 | 1879864887 | 0 | ARGMIN | 9 | 10 |
| phase47c/SLW/222/OURS-DETOUR+HMM | phase47c | SLW | 222 | OURS-DETOUR+HMM | 90 | 13 | 2 | 76 | 5 | 0.3963 | 20261112 | 2244742880 | 90 | HMM | 89 | 90 |
| phase47c/SLW/222/OURS-DETOUR | phase47c | SLW | 222 | OURS-DETOUR | 27 | 0 | 0 | 26 | 1 | 0.3963 | 20261112 | 1836260405 | 0 | ARGMIN | 27 | 27 |
| phase47c/SLW/223/NOMAD_RAW | phase47c | SLW | 223 | NOMAD_RAW | 19 | 2 | 1 | 16 | 2 | 0.3963 | 20261112 | 272332798 | 0 | ARGMIN | 18 | 19 |
| phase47c/SLW/223/OURS-DETOUR+HMM | phase47c | SLW | 223 | OURS-DETOUR+HMM | 89 | 19 | 2 | 69 | 3 | 0.3963 | 20261112 | 3123956978 | 89 | HMM | 88 | 89 |
| phase47c/SLW/223/OURS-DETOUR | phase47c | SLW | 223 | OURS-DETOUR | 15 | 0 | 0 | 14 | 3 | 0.3963 | 20261112 | 3462701150 | 0 | ARGMIN | 15 | 15 |
| phase47c/SLW/224/NOMAD_RAW | phase47c | SLW | 224 | NOMAD_RAW | 9 | 0 | 0 | 8 | 1 | 0.3963 | 20261112 | 2120438739 | 0 | ARGMIN | 8 | 9 |
| phase47c/SLW/224/OURS-DETOUR+HMM | phase47c | SLW | 224 | OURS-DETOUR+HMM | 58 | 0 | 0 | 57 | 5 | 0.3963 | 20261112 | 1727979758 | 58 | HMM | 58 | 58 |
| phase47c/SLW/224/OURS-DETOUR | phase47c | SLW | 224 | OURS-DETOUR | 89 | 0 | 0 | 88 | 4 | 0.3963 | 20261112 | 3383830656 | 0 | ARGMIN | 88 | 89 |

| table |
|---|
| 첫 가상 정지 run별 결과 |

| run | phase | scene | seed | method | model | first_virtual_goal | first_outcome_known | first_virtual_wrong | first_stop_inference_id | stop_distance_m | first_stop_s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| phase43p/H1/217/OURS-DETOUR+HMM | phase43p | H1 | 217 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 29 | 0.793 | 31.39 |
| phase43p/H1/217/OURS-DETOUR+HMM | phase43p | H1 | 217 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 33 | 0.4227 | 35.33 |
| phase43p/H1/217/OURS-DETOUR+HMM | phase43p | H1 | 217 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 32 | 0.4765 | 34.33 |
| phase43p/H1/217/OURS-DETOUR+HMM | phase43p | H1 | 217 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 32 | 0.4765 | 34.33 |
| phase43p/H1/219/OURS-DETOUR+HMM | phase43p | H1 | 219 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 56 | 1.614 | 58.58 |
| phase43p/H1/219/OURS-DETOUR+HMM | phase43p | H1 | 219 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 56 | 1.614 | 58.58 |
| phase43p/H1/219/OURS-DETOUR+HMM | phase43p | H1 | 219 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase43p/H1/219/OURS-DETOUR+HMM | phase43p | H1 | 219 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase43p/H1/220/OURS-DETOUR+HMM | phase43p | H1 | 220 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 22 | 1.108 | 24.58 |
| phase43p/H1/220/OURS-DETOUR+HMM | phase43p | H1 | 220 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 27 | 0.3027 | 29.58 |
| phase43p/H1/220/OURS-DETOUR+HMM | phase43p | H1 | 220 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 26 | 0.3845 | 28.58 |
| phase43p/H1/220/OURS-DETOUR+HMM | phase43p | H1 | 220 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 26 | 0.3845 | 28.58 |
| phase43p/H2/217/OURS-DETOUR+HMM | phase43p | H2 | 217 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 57 | 2.189 | 59.83 |
| phase43p/H2/217/OURS-DETOUR+HMM | phase43p | H2 | 217 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 73 | 0.7512 | 76.08 |
| phase43p/H2/217/OURS-DETOUR+HMM | phase43p | H2 | 217 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 73 | 0.7512 | 76.08 |
| phase43p/H2/217/OURS-DETOUR+HMM | phase43p | H2 | 217 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | True | 73 | 0.7512 | 76.08 |
| phase43p/H2/219/OURS-DETOUR+HMM | phase43p | H2 | 219 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 85 | 0.4824 | 87.33 |
| phase43p/H2/219/OURS-DETOUR+HMM | phase43p | H2 | 219 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 85 | 0.4824 | 87.33 |
| phase43p/H2/219/OURS-DETOUR+HMM | phase43p | H2 | 219 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 85 | 0.4824 | 87.33 |
| phase43p/H2/219/OURS-DETOUR+HMM | phase43p | H2 | 219 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 85 | 0.4824 | 87.33 |
| phase43p/H2/220/OURS-DETOUR+HMM | phase43p | H2 | 220 | OURS-DETOUR+HMM | ARGMIN | False | True | — | — | — | — |
| phase43p/H2/220/OURS-DETOUR+HMM | phase43p | H2 | 220 | OURS-DETOUR+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase43p/H2/220/OURS-DETOUR+HMM | phase43p | H2 | 220 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase43p/H2/220/OURS-DETOUR+HMM | phase43p | H2 | 220 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase43p/L2/217/OURS-DETOUR+HMM | phase43p | L2 | 217 | OURS-DETOUR+HMM | ARGMIN | False | True | — | — | — | — |
| phase43p/L2/217/OURS-DETOUR+HMM | phase43p | L2 | 217 | OURS-DETOUR+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase43p/L2/217/OURS-DETOUR+HMM | phase43p | L2 | 217 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase43p/L2/217/OURS-DETOUR+HMM | phase43p | L2 | 217 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase43p/L2/219/OURS-DETOUR+HMM | phase43p | L2 | 219 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 51 | 7.46 | 53.58 |
| phase43p/L2/219/OURS-DETOUR+HMM | phase43p | L2 | 219 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 55 | 7.608 | 57.58 |
| phase43p/L2/219/OURS-DETOUR+HMM | phase43p | L2 | 219 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase43p/L2/219/OURS-DETOUR+HMM | phase43p | L2 | 219 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase43p/L2/220/OURS-DETOUR+HMM | phase43p | L2 | 220 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 45 | 0.5394 | 47.83 |
| phase43p/L2/220/OURS-DETOUR+HMM | phase43p | L2 | 220 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 45 | 0.5394 | 47.83 |
| phase43p/L2/220/OURS-DETOUR+HMM | phase43p | L2 | 220 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 45 | 0.5394 | 47.83 |
| phase43p/L2/220/OURS-DETOUR+HMM | phase43p | L2 | 220 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | True | 45 | 0.5394 | 47.83 |
| phase43p/LC/217/OURS-DETOUR+HMM | phase43p | LC | 217 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 36 | 0.2832 | 38.58 |
| phase43p/LC/217/OURS-DETOUR+HMM | phase43p | LC | 217 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 36 | 0.2832 | 38.58 |
| phase43p/LC/217/OURS-DETOUR+HMM | phase43p | LC | 217 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 36 | 0.2832 | 38.58 |
| phase43p/LC/217/OURS-DETOUR+HMM | phase43p | LC | 217 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 36 | 0.2832 | 38.58 |
| phase43p/LC/219/OURS-DETOUR+HMM | phase43p | LC | 219 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 23 | 0.4612 | 25.83 |
| phase43p/LC/219/OURS-DETOUR+HMM | phase43p | LC | 219 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 25 | 0.108 | 27.83 |
| phase43p/LC/219/OURS-DETOUR+HMM | phase43p | LC | 219 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 24 | 0.1985 | 26.83 |
| phase43p/LC/219/OURS-DETOUR+HMM | phase43p | LC | 219 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 24 | 0.1985 | 26.83 |
| phase43p/LC/220/OURS-DETOUR+HMM | phase43p | LC | 220 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 22 | 0.7389 | 24.58 |
| phase43p/LC/220/OURS-DETOUR+HMM | phase43p | LC | 220 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 25 | 0.3826 | 27.58 |
| phase43p/LC/220/OURS-DETOUR+HMM | phase43p | LC | 220 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 25 | 0.3826 | 27.58 |
| phase43p/LC/220/OURS-DETOUR+HMM | phase43p | LC | 220 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 25 | 0.3826 | 27.58 |
| phase43p/SLW/217/OURS-DETOUR+HMM | phase43p | SLW | 217 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 58 | 0.3203 | 60.08 |
| phase43p/SLW/217/OURS-DETOUR+HMM | phase43p | SLW | 217 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 58 | 0.3203 | 60.08 |
| phase43p/SLW/217/OURS-DETOUR+HMM | phase43p | SLW | 217 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 58 | 0.3203 | 60.08 |
| phase43p/SLW/217/OURS-DETOUR+HMM | phase43p | SLW | 217 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 58 | 0.3203 | 60.08 |
| phase43p/SLW/219/OURS-DETOUR+HMM | phase43p | SLW | 219 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 51 | 1.456 | 53.83 |
| phase43p/SLW/219/OURS-DETOUR+HMM | phase43p | SLW | 219 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 72 | 0.3867 | 74.58 |
| phase43p/SLW/219/OURS-DETOUR+HMM | phase43p | SLW | 219 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 72 | 0.3867 | 74.58 |
| phase43p/SLW/219/OURS-DETOUR+HMM | phase43p | SLW | 219 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 72 | 0.3867 | 74.58 |
| phase43p/SLW/220/OURS-DETOUR+HMM | phase43p | SLW | 220 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 60 | 0.3048 | 61.83 |
| phase43p/SLW/220/OURS-DETOUR+HMM | phase43p | SLW | 220 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 60 | 0.3048 | 61.83 |
| phase43p/SLW/220/OURS-DETOUR+HMM | phase43p | SLW | 220 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 60 | 0.3048 | 61.83 |
| phase43p/SLW/220/OURS-DETOUR+HMM | phase43p | SLW | 220 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 60 | 0.3048 | 61.83 |
| phase44p/H2/217/OURS-DETOUR+HMM | phase44p | H2 | 217 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 59 | 2.144 | 60.86 |
| phase44p/H2/217/OURS-DETOUR+HMM | phase44p | H2 | 217 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 61 | 2.145 | 62.83 |
| phase44p/H2/217/OURS-DETOUR+HMM | phase44p | H2 | 217 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 60 | 2.124 | 61.83 |
| phase44p/H2/217/OURS-DETOUR+HMM | phase44p | H2 | 217 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | True | 60 | 2.124 | 61.83 |
| phase44p/H2/219/OURS-DETOUR+HMM | phase44p | H2 | 219 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 67 | 2.044 | 69.36 |
| phase44p/H2/219/OURS-DETOUR+HMM | phase44p | H2 | 219 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 72 | 2.044 | 74.35 |
| phase44p/H2/219/OURS-DETOUR+HMM | phase44p | H2 | 219 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 69 | 2.044 | 71.36 |
| phase44p/H2/219/OURS-DETOUR+HMM | phase44p | H2 | 219 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | True | 68 | 2.044 | 70.32 |
| phase44p/H2/220/OURS-DETOUR+HMM | phase44p | H2 | 220 | OURS-DETOUR+HMM | ARGMIN | False | True | — | — | — | — |
| phase44p/H2/220/OURS-DETOUR+HMM | phase44p | H2 | 220 | OURS-DETOUR+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase44p/H2/220/OURS-DETOUR+HMM | phase44p | H2 | 220 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase44p/H2/220/OURS-DETOUR+HMM | phase44p | H2 | 220 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase44p/L2/217/OURS-DETOUR+HMM | phase44p | L2 | 217 | OURS-DETOUR+HMM | ARGMIN | False | True | — | — | — | — |
| phase44p/L2/217/OURS-DETOUR+HMM | phase44p | L2 | 217 | OURS-DETOUR+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase44p/L2/217/OURS-DETOUR+HMM | phase44p | L2 | 217 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase44p/L2/217/OURS-DETOUR+HMM | phase44p | L2 | 217 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase44p/L2/219/OURS-DETOUR+HMM | phase44p | L2 | 219 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 73 | 0.123 | 75.83 |
| phase44p/L2/219/OURS-DETOUR+HMM | phase44p | L2 | 219 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 73 | 0.123 | 75.83 |
| phase44p/L2/219/OURS-DETOUR+HMM | phase44p | L2 | 219 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 72 | 0.3167 | 74.83 |
| phase44p/L2/219/OURS-DETOUR+HMM | phase44p | L2 | 219 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 72 | 0.3167 | 74.83 |
| phase44p/L2/220/OURS-DETOUR+HMM | phase44p | L2 | 220 | OURS-DETOUR+HMM | ARGMIN | False | True | — | — | — | — |
| phase44p/L2/220/OURS-DETOUR+HMM | phase44p | L2 | 220 | OURS-DETOUR+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase44p/L2/220/OURS-DETOUR+HMM | phase44p | L2 | 220 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase44p/L2/220/OURS-DETOUR+HMM | phase44p | L2 | 220 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase45p/H1/217/OURS+HMM | phase45p | H1 | 217 | OURS+HMM | ARGMIN | True | True | False | 26 | 0.4904 | 28.83 |
| phase45p/H1/217/OURS+HMM | phase45p | H1 | 217 | OURS+HMM | HMM_FORWARD | True | True | False | 29 | 0.3667 | 31.83 |
| phase45p/H1/217/OURS+HMM | phase45p | H1 | 217 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 26 | 0.4904 | 28.83 |
| phase45p/H1/217/OURS+HMM | phase45p | H1 | 217 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | False | 26 | 0.4904 | 28.83 |
| phase45p/H1/219/OURS+HMM | phase45p | H1 | 219 | OURS+HMM | ARGMIN | False | True | — | — | — | — |
| phase45p/H1/219/OURS+HMM | phase45p | H1 | 219 | OURS+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase45p/H1/219/OURS+HMM | phase45p | H1 | 219 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase45p/H1/219/OURS+HMM | phase45p | H1 | 219 | OURS+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase45p/H1/220/OURS+HMM | phase45p | H1 | 220 | OURS+HMM | ARGMIN | True | True | False | 26 | 0.2851 | 28.83 |
| phase45p/H1/220/OURS+HMM | phase45p | H1 | 220 | OURS+HMM | HMM_FORWARD | True | True | False | 26 | 0.2851 | 28.83 |
| phase45p/H1/220/OURS+HMM | phase45p | H1 | 220 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 26 | 0.2851 | 28.83 |
| phase45p/H1/220/OURS+HMM | phase45p | H1 | 220 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | False | 26 | 0.2851 | 28.83 |
| phase45p/H2/217/OURS+HMM | phase45p | H2 | 217 | OURS+HMM | ARGMIN | True | True | True | 66 | 2.135 | 68.79 |
| phase45p/H2/217/OURS+HMM | phase45p | H2 | 217 | OURS+HMM | HMM_FORWARD | True | True | True | 86 | 0.6474 | 88.83 |
| phase45p/H2/217/OURS+HMM | phase45p | H2 | 217 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 83 | 0.8327 | 85.83 |
| phase45p/H2/217/OURS+HMM | phase45p | H2 | 217 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | True | 83 | 0.8327 | 85.83 |
| phase45p/H2/219/OURS+HMM | phase45p | H2 | 219 | OURS+HMM | ARGMIN | True | True | True | 77 | 2.421 | 79.33 |
| phase45p/H2/219/OURS+HMM | phase45p | H2 | 219 | OURS+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase45p/H2/219/OURS+HMM | phase45p | H2 | 219 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 81 | 2.312 | 83.14 |
| phase45p/H2/219/OURS+HMM | phase45p | H2 | 219 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | True | 81 | 2.312 | 83.14 |
| phase45p/H2/220/OURS+HMM | phase45p | H2 | 220 | OURS+HMM | ARGMIN | True | True | True | 38 | 6.293 | 40.6 |
| phase45p/H2/220/OURS+HMM | phase45p | H2 | 220 | OURS+HMM | HMM_FORWARD | True | True | True | 48 | 6.432 | 50.57 |
| phase45p/H2/220/OURS+HMM | phase45p | H2 | 220 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 41 | 6.27 | 43.58 |
| phase45p/H2/220/OURS+HMM | phase45p | H2 | 220 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | True | 41 | 6.27 | 43.58 |
| phase45p/L2/217/OURS+HMM | phase45p | L2 | 217 | OURS+HMM | ARGMIN | True | True | False | 77 | 0.4663 | 79.57 |
| phase45p/L2/217/OURS+HMM | phase45p | L2 | 217 | OURS+HMM | HMM_FORWARD | True | True | False | 77 | 0.4663 | 79.57 |
| phase45p/L2/217/OURS+HMM | phase45p | L2 | 217 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 74 | 0.4722 | 76.58 |
| phase45p/L2/217/OURS+HMM | phase45p | L2 | 217 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | False | 74 | 0.4722 | 76.58 |
| phase45p/L2/219/OURS+HMM | phase45p | L2 | 219 | OURS+HMM | ARGMIN | True | True | False | 38 | 0.2667 | 40.33 |
| phase45p/L2/219/OURS+HMM | phase45p | L2 | 219 | OURS+HMM | HMM_FORWARD | True | True | False | 38 | 0.2667 | 40.33 |
| phase45p/L2/219/OURS+HMM | phase45p | L2 | 219 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 37 | 0.3681 | 39.33 |
| phase45p/L2/219/OURS+HMM | phase45p | L2 | 219 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | False | 37 | 0.3681 | 39.33 |
| phase45p/L2/220/OURS+HMM | phase45p | L2 | 220 | OURS+HMM | ARGMIN | True | True | True | 43 | 0.8738 | 45.83 |
| phase45p/L2/220/OURS+HMM | phase45p | L2 | 220 | OURS+HMM | HMM_FORWARD | True | True | True | 45 | 0.7209 | 47.83 |
| phase45p/L2/220/OURS+HMM | phase45p | L2 | 220 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 45 | 0.7209 | 47.83 |
| phase45p/L2/220/OURS+HMM | phase45p | L2 | 220 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | True | 45 | 0.7209 | 47.83 |
| phase45p/LC/217/OURS+HMM | phase45p | LC | 217 | OURS+HMM | ARGMIN | True | True | False | 29 | 0.466 | 31.83 |
| phase45p/LC/217/OURS+HMM | phase45p | LC | 217 | OURS+HMM | HMM_FORWARD | True | True | False | 29 | 0.466 | 31.83 |
| phase45p/LC/217/OURS+HMM | phase45p | LC | 217 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 27 | 0.5615 | 29.83 |
| phase45p/LC/217/OURS+HMM | phase45p | LC | 217 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | True | 27 | 0.5615 | 29.83 |
| phase45p/LC/219/OURS+HMM | phase45p | LC | 219 | OURS+HMM | ARGMIN | True | True | False | 24 | 0.4849 | 26.83 |
| phase45p/LC/219/OURS+HMM | phase45p | LC | 219 | OURS+HMM | HMM_FORWARD | True | True | False | 24 | 0.4849 | 26.83 |
| phase45p/LC/219/OURS+HMM | phase45p | LC | 219 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 24 | 0.4849 | 26.83 |
| phase45p/LC/219/OURS+HMM | phase45p | LC | 219 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | False | 24 | 0.4849 | 26.83 |
| phase45p/LC/220/OURS+HMM | phase45p | LC | 220 | OURS+HMM | ARGMIN | True | True | False | 28 | 0.3174 | 30.64 |
| phase45p/LC/220/OURS+HMM | phase45p | LC | 220 | OURS+HMM | HMM_FORWARD | True | True | False | 28 | 0.3174 | 30.64 |
| phase45p/LC/220/OURS+HMM | phase45p | LC | 220 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 27 | 0.3297 | 29.85 |
| phase45p/LC/220/OURS+HMM | phase45p | LC | 220 | OURS+HMM | FG_2PCT_ONE_DRAW | True | True | False | 27 | 0.3297 | 29.85 |
| phase45p/SLW/217/OURS+HMM | phase45p | SLW | 217 | OURS+HMM | ARGMIN | False | True | — | — | — | — |
| phase45p/SLW/217/OURS+HMM | phase45p | SLW | 217 | OURS+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase45p/SLW/217/OURS+HMM | phase45p | SLW | 217 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase45p/SLW/217/OURS+HMM | phase45p | SLW | 217 | OURS+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase45p/SLW/219/OURS+HMM | phase45p | SLW | 219 | OURS+HMM | ARGMIN | False | True | — | — | — | — |
| phase45p/SLW/219/OURS+HMM | phase45p | SLW | 219 | OURS+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase45p/SLW/219/OURS+HMM | phase45p | SLW | 219 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase45p/SLW/219/OURS+HMM | phase45p | SLW | 219 | OURS+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase45p/SLW/220/OURS+HMM | phase45p | SLW | 220 | OURS+HMM | ARGMIN | False | True | — | — | — | — |
| phase45p/SLW/220/OURS+HMM | phase45p | SLW | 220 | OURS+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase45p/SLW/220/OURS+HMM | phase45p | SLW | 220 | OURS+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase45p/SLW/220/OURS+HMM | phase45p | SLW | 220 | OURS+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase46p/H1/217/OURS-B-ONLY+HMM | phase46p | H1 | 217 | OURS-B-ONLY+HMM | ARGMIN | True | True | True | 33 | 0.6313 | 35.58 |
| phase46p/H1/217/OURS-B-ONLY+HMM | phase46p | H1 | 217 | OURS-B-ONLY+HMM | HMM_FORWARD | True | True | False | 36 | 0.3492 | 38.33 |
| phase46p/H1/217/OURS-B-ONLY+HMM | phase46p | H1 | 217 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 35 | 0.4246 | 37.4 |
| phase46p/H1/217/OURS-B-ONLY+HMM | phase46p | H1 | 217 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | False | 35 | 0.4246 | 37.4 |
| phase46p/H1/219/OURS-B-ONLY+HMM | phase46p | H1 | 219 | OURS-B-ONLY+HMM | ARGMIN | True | True | False | 25 | 0.2041 | 27.83 |
| phase46p/H1/219/OURS-B-ONLY+HMM | phase46p | H1 | 219 | OURS-B-ONLY+HMM | HMM_FORWARD | True | True | False | 25 | 0.2041 | 27.83 |
| phase46p/H1/219/OURS-B-ONLY+HMM | phase46p | H1 | 219 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 25 | 0.2041 | 27.83 |
| phase46p/H1/219/OURS-B-ONLY+HMM | phase46p | H1 | 219 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | False | 25 | 0.2041 | 27.83 |
| phase46p/H1/220/OURS-B-ONLY+HMM | phase46p | H1 | 220 | OURS-B-ONLY+HMM | ARGMIN | True | True | False | 28 | 0.3787 | 30.83 |
| phase46p/H1/220/OURS-B-ONLY+HMM | phase46p | H1 | 220 | OURS-B-ONLY+HMM | HMM_FORWARD | True | True | False | 28 | 0.3787 | 30.83 |
| phase46p/H1/220/OURS-B-ONLY+HMM | phase46p | H1 | 220 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase46p/H1/220/OURS-B-ONLY+HMM | phase46p | H1 | 220 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase46p/H2/217/OURS-B-ONLY+HMM | phase46p | H2 | 217 | OURS-B-ONLY+HMM | ARGMIN | False | True | — | — | — | — |
| phase46p/H2/217/OURS-B-ONLY+HMM | phase46p | H2 | 217 | OURS-B-ONLY+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase46p/H2/217/OURS-B-ONLY+HMM | phase46p | H2 | 217 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase46p/H2/217/OURS-B-ONLY+HMM | phase46p | H2 | 217 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase46p/H2/219/OURS-B-ONLY+HMM | phase46p | H2 | 219 | OURS-B-ONLY+HMM | ARGMIN | True | True | True | 71 | 2.323 | 73.83 |
| phase46p/H2/219/OURS-B-ONLY+HMM | phase46p | H2 | 219 | OURS-B-ONLY+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase46p/H2/219/OURS-B-ONLY+HMM | phase46p | H2 | 219 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 68 | 2.355 | 70.83 |
| phase46p/H2/219/OURS-B-ONLY+HMM | phase46p | H2 | 219 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | True | 68 | 2.355 | 70.83 |
| phase46p/H2/220/OURS-B-ONLY+HMM | phase46p | H2 | 220 | OURS-B-ONLY+HMM | ARGMIN | False | True | — | — | — | — |
| phase46p/H2/220/OURS-B-ONLY+HMM | phase46p | H2 | 220 | OURS-B-ONLY+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase46p/H2/220/OURS-B-ONLY+HMM | phase46p | H2 | 220 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase46p/H2/220/OURS-B-ONLY+HMM | phase46p | H2 | 220 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase46p/L2/217/OURS-B-ONLY+HMM | phase46p | L2 | 217 | OURS-B-ONLY+HMM | ARGMIN | False | True | — | — | — | — |
| phase46p/L2/217/OURS-B-ONLY+HMM | phase46p | L2 | 217 | OURS-B-ONLY+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase46p/L2/217/OURS-B-ONLY+HMM | phase46p | L2 | 217 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase46p/L2/217/OURS-B-ONLY+HMM | phase46p | L2 | 217 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase46p/L2/219/OURS-B-ONLY+HMM | phase46p | L2 | 219 | OURS-B-ONLY+HMM | ARGMIN | True | True | True | 37 | 0.6856 | 39.6 |
| phase46p/L2/219/OURS-B-ONLY+HMM | phase46p | L2 | 219 | OURS-B-ONLY+HMM | HMM_FORWARD | True | True | True | 37 | 0.6856 | 39.6 |
| phase46p/L2/219/OURS-B-ONLY+HMM | phase46p | L2 | 219 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 37 | 0.6856 | 39.6 |
| phase46p/L2/219/OURS-B-ONLY+HMM | phase46p | L2 | 219 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | True | 37 | 0.6856 | 39.6 |
| phase46p/L2/220/OURS-B-ONLY+HMM | phase46p | L2 | 220 | OURS-B-ONLY+HMM | ARGMIN | True | True | True | 38 | 0.585 | 40.58 |
| phase46p/L2/220/OURS-B-ONLY+HMM | phase46p | L2 | 220 | OURS-B-ONLY+HMM | HMM_FORWARD | True | True | True | 38 | 0.585 | 40.58 |
| phase46p/L2/220/OURS-B-ONLY+HMM | phase46p | L2 | 220 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 38 | 0.585 | 40.58 |
| phase46p/L2/220/OURS-B-ONLY+HMM | phase46p | L2 | 220 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | True | 38 | 0.585 | 40.58 |
| phase46p/LC/217/OURS-B-ONLY+HMM | phase46p | LC | 217 | OURS-B-ONLY+HMM | ARGMIN | True | True | False | 28 | 0.4009 | 30.58 |
| phase46p/LC/217/OURS-B-ONLY+HMM | phase46p | LC | 217 | OURS-B-ONLY+HMM | HMM_FORWARD | True | True | False | 29 | 0.3573 | 31.58 |
| phase46p/LC/217/OURS-B-ONLY+HMM | phase46p | LC | 217 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 27 | 0.4628 | 29.57 |
| phase46p/LC/217/OURS-B-ONLY+HMM | phase46p | LC | 217 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | False | 27 | 0.4628 | 29.57 |
| phase46p/LC/219/OURS-B-ONLY+HMM | phase46p | LC | 219 | OURS-B-ONLY+HMM | ARGMIN | True | True | False | 32 | 0.4736 | 34.83 |
| phase46p/LC/219/OURS-B-ONLY+HMM | phase46p | LC | 219 | OURS-B-ONLY+HMM | HMM_FORWARD | True | True | False | 32 | 0.4736 | 34.83 |
| phase46p/LC/219/OURS-B-ONLY+HMM | phase46p | LC | 219 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 32 | 0.4736 | 34.83 |
| phase46p/LC/219/OURS-B-ONLY+HMM | phase46p | LC | 219 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | False | 32 | 0.4736 | 34.83 |
| phase46p/LC/220/OURS-B-ONLY+HMM | phase46p | LC | 220 | OURS-B-ONLY+HMM | ARGMIN | True | True | False | 27 | 0.3642 | 29.83 |
| phase46p/LC/220/OURS-B-ONLY+HMM | phase46p | LC | 220 | OURS-B-ONLY+HMM | HMM_FORWARD | True | True | False | 27 | 0.3642 | 29.83 |
| phase46p/LC/220/OURS-B-ONLY+HMM | phase46p | LC | 220 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 27 | 0.3642 | 29.83 |
| phase46p/LC/220/OURS-B-ONLY+HMM | phase46p | LC | 220 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | False | 27 | 0.3642 | 29.83 |
| phase46p/SLW/217/OURS-B-ONLY+HMM | phase46p | SLW | 217 | OURS-B-ONLY+HMM | ARGMIN | False | True | — | — | — | — |
| phase46p/SLW/217/OURS-B-ONLY+HMM | phase46p | SLW | 217 | OURS-B-ONLY+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase46p/SLW/217/OURS-B-ONLY+HMM | phase46p | SLW | 217 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase46p/SLW/217/OURS-B-ONLY+HMM | phase46p | SLW | 217 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase46p/SLW/219/OURS-B-ONLY+HMM | phase46p | SLW | 219 | OURS-B-ONLY+HMM | ARGMIN | True | True | True | 40 | 2.726 | 42.88 |
| phase46p/SLW/219/OURS-B-ONLY+HMM | phase46p | SLW | 219 | OURS-B-ONLY+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase46p/SLW/219/OURS-B-ONLY+HMM | phase46p | SLW | 219 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 62 | 2.773 | 64.82 |
| phase46p/SLW/219/OURS-B-ONLY+HMM | phase46p | SLW | 219 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | True | 62 | 2.773 | 64.82 |
| phase46p/SLW/220/OURS-B-ONLY+HMM | phase46p | SLW | 220 | OURS-B-ONLY+HMM | ARGMIN | True | True | True | 47 | 1.435 | 49.6 |
| phase46p/SLW/220/OURS-B-ONLY+HMM | phase46p | SLW | 220 | OURS-B-ONLY+HMM | HMM_FORWARD | True | True | True | 54 | 1.836 | 56.57 |
| phase46p/SLW/220/OURS-B-ONLY+HMM | phase46p | SLW | 220 | OURS-B-ONLY+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 50 | 1.522 | 52.56 |
| phase46p/SLW/220/OURS-B-ONLY+HMM | phase46p | SLW | 220 | OURS-B-ONLY+HMM | FG_2PCT_ONE_DRAW | True | True | True | 50 | 1.522 | 52.56 |
| phase47c/H1/221/NOMAD_RAW | phase47c | H1 | 221 | NOMAD_RAW | ARGMIN | True | True | True | 24 | 2.111 | 26.83 |
| phase47c/H1/221/NOMAD_RAW | phase47c | H1 | 221 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H1/221/NOMAD_RAW | phase47c | H1 | 221 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 24 | 2.111 | 26.83 |
| phase47c/H1/221/NOMAD_RAW | phase47c | H1 | 221 | NOMAD_RAW | FG_2PCT_ONE_DRAW | True | True | True | 24 | 2.111 | 26.83 |
| phase47c/H1/221/OURS-DETOUR+HMM | phase47c | H1 | 221 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 29 | 0.4415 | 31.83 |
| phase47c/H1/221/OURS-DETOUR+HMM | phase47c | H1 | 221 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 31 | 0.2829 | 33.83 |
| phase47c/H1/221/OURS-DETOUR+HMM | phase47c | H1 | 221 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 31 | 0.2829 | 33.83 |
| phase47c/H1/221/OURS-DETOUR+HMM | phase47c | H1 | 221 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 31 | 0.2829 | 33.83 |
| phase47c/H1/221/OURS-DETOUR | phase47c | H1 | 221 | OURS-DETOUR | ARGMIN | True | True | True | 28 | 0.5523 | 30.58 |
| phase47c/H1/221/OURS-DETOUR | phase47c | H1 | 221 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H1/221/OURS-DETOUR | phase47c | H1 | 221 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H1/221/OURS-DETOUR | phase47c | H1 | 221 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H1/222/NOMAD_RAW | phase47c | H1 | 222 | NOMAD_RAW | ARGMIN | True | True | False | 28 | 0.3012 | 30.58 |
| phase47c/H1/222/NOMAD_RAW | phase47c | H1 | 222 | NOMAD_RAW | HMM_FORWARD | True | True | False | 28 | 0.3012 | 30.58 |
| phase47c/H1/222/NOMAD_RAW | phase47c | H1 | 222 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 27 | 0.3508 | 29.58 |
| phase47c/H1/222/NOMAD_RAW | phase47c | H1 | 222 | NOMAD_RAW | FG_2PCT_ONE_DRAW | True | True | False | 27 | 0.3508 | 29.58 |
| phase47c/H1/222/OURS-DETOUR+HMM | phase47c | H1 | 222 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 27 | 0.3402 | 29.83 |
| phase47c/H1/222/OURS-DETOUR+HMM | phase47c | H1 | 222 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 27 | 0.3402 | 29.83 |
| phase47c/H1/222/OURS-DETOUR+HMM | phase47c | H1 | 222 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H1/222/OURS-DETOUR+HMM | phase47c | H1 | 222 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H1/222/OURS-DETOUR | phase47c | H1 | 222 | OURS-DETOUR | ARGMIN | True | True | False | 28 | 0.3164 | 30.58 |
| phase47c/H1/222/OURS-DETOUR | phase47c | H1 | 222 | OURS-DETOUR | HMM_FORWARD | True | True | False | 28 | 0.3164 | 30.58 |
| phase47c/H1/222/OURS-DETOUR | phase47c | H1 | 222 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 28 | 0.3164 | 30.58 |
| phase47c/H1/222/OURS-DETOUR | phase47c | H1 | 222 | OURS-DETOUR | FG_2PCT_ONE_DRAW | True | True | False | 28 | 0.3164 | 30.58 |
| phase47c/H1/223/NOMAD_RAW | phase47c | H1 | 223 | NOMAD_RAW | ARGMIN | True | True | False | 34 | 0.4042 | 36.58 |
| phase47c/H1/223/NOMAD_RAW | phase47c | H1 | 223 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H1/223/NOMAD_RAW | phase47c | H1 | 223 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H1/223/NOMAD_RAW | phase47c | H1 | 223 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H1/223/OURS-DETOUR+HMM | phase47c | H1 | 223 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 29 | 0.3307 | 31.58 |
| phase47c/H1/223/OURS-DETOUR+HMM | phase47c | H1 | 223 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 29 | 0.3307 | 31.58 |
| phase47c/H1/223/OURS-DETOUR+HMM | phase47c | H1 | 223 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 29 | 0.3307 | 31.58 |
| phase47c/H1/223/OURS-DETOUR+HMM | phase47c | H1 | 223 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 29 | 0.3307 | 31.58 |
| phase47c/H1/223/OURS-DETOUR | phase47c | H1 | 223 | OURS-DETOUR | ARGMIN | True | True | False | 25 | 0.4649 | 27.83 |
| phase47c/H1/223/OURS-DETOUR | phase47c | H1 | 223 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H1/223/OURS-DETOUR | phase47c | H1 | 223 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H1/223/OURS-DETOUR | phase47c | H1 | 223 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H1/224/NOMAD_RAW | phase47c | H1 | 224 | NOMAD_RAW | ARGMIN | True | True | True | 25 | 0.5257 | 27.85 |
| phase47c/H1/224/NOMAD_RAW | phase47c | H1 | 224 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H1/224/NOMAD_RAW | phase47c | H1 | 224 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 25 | 0.5257 | 27.85 |
| phase47c/H1/224/NOMAD_RAW | phase47c | H1 | 224 | NOMAD_RAW | FG_2PCT_ONE_DRAW | True | True | True | 25 | 0.5257 | 27.85 |
| phase47c/H1/224/OURS-DETOUR+HMM | phase47c | H1 | 224 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 24 | 0.6592 | 26.39 |
| phase47c/H1/224/OURS-DETOUR+HMM | phase47c | H1 | 224 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 27 | 0.3078 | 29.33 |
| phase47c/H1/224/OURS-DETOUR+HMM | phase47c | H1 | 224 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 26 | 0.3639 | 28.33 |
| phase47c/H1/224/OURS-DETOUR+HMM | phase47c | H1 | 224 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 26 | 0.3639 | 28.33 |
| phase47c/H1/224/OURS-DETOUR | phase47c | H1 | 224 | OURS-DETOUR | ARGMIN | True | True | True | 18 | 2.611 | 20.83 |
| phase47c/H1/224/OURS-DETOUR | phase47c | H1 | 224 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H1/224/OURS-DETOUR | phase47c | H1 | 224 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 18 | 2.611 | 20.83 |
| phase47c/H1/224/OURS-DETOUR | phase47c | H1 | 224 | OURS-DETOUR | FG_2PCT_ONE_DRAW | True | True | True | 18 | 2.611 | 20.83 |
| phase47c/H2/221/NOMAD_RAW | phase47c | H2 | 221 | NOMAD_RAW | ARGMIN | False | True | — | — | — | — |
| phase47c/H2/221/NOMAD_RAW | phase47c | H2 | 221 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H2/221/NOMAD_RAW | phase47c | H2 | 221 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H2/221/NOMAD_RAW | phase47c | H2 | 221 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H2/221/OURS-DETOUR+HMM | phase47c | H2 | 221 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 81 | 0.5624 | 83.33 |
| phase47c/H2/221/OURS-DETOUR+HMM | phase47c | H2 | 221 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 81 | 0.5624 | 83.33 |
| phase47c/H2/221/OURS-DETOUR+HMM | phase47c | H2 | 221 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 81 | 0.5624 | 83.33 |
| phase47c/H2/221/OURS-DETOUR+HMM | phase47c | H2 | 221 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | True | 81 | 0.5624 | 83.33 |
| phase47c/H2/221/OURS-DETOUR | phase47c | H2 | 221 | OURS-DETOUR | ARGMIN | True | True | True | 13 | 5.405 | 15.83 |
| phase47c/H2/221/OURS-DETOUR | phase47c | H2 | 221 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H2/221/OURS-DETOUR | phase47c | H2 | 221 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H2/221/OURS-DETOUR | phase47c | H2 | 221 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H2/222/NOMAD_RAW | phase47c | H2 | 222 | NOMAD_RAW | ARGMIN | True | True | True | 16 | 5.354 | 18.64 |
| phase47c/H2/222/NOMAD_RAW | phase47c | H2 | 222 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H2/222/NOMAD_RAW | phase47c | H2 | 222 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H2/222/NOMAD_RAW | phase47c | H2 | 222 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H2/222/OURS-DETOUR+HMM | phase47c | H2 | 222 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 46 | 0.4889 | 48.58 |
| phase47c/H2/222/OURS-DETOUR+HMM | phase47c | H2 | 222 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 46 | 0.4889 | 48.58 |
| phase47c/H2/222/OURS-DETOUR+HMM | phase47c | H2 | 222 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 44 | 0.6096 | 46.58 |
| phase47c/H2/222/OURS-DETOUR+HMM | phase47c | H2 | 222 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | True | 44 | 0.6096 | 46.58 |
| phase47c/H2/222/OURS-DETOUR | phase47c | H2 | 222 | OURS-DETOUR | ARGMIN | True | True | True | 18 | 5.192 | 20.42 |
| phase47c/H2/222/OURS-DETOUR | phase47c | H2 | 222 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H2/222/OURS-DETOUR | phase47c | H2 | 222 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H2/222/OURS-DETOUR | phase47c | H2 | 222 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H2/223/NOMAD_RAW | phase47c | H2 | 223 | NOMAD_RAW | ARGMIN | True | True | True | 12 | 5.705 | 14.58 |
| phase47c/H2/223/NOMAD_RAW | phase47c | H2 | 223 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H2/223/NOMAD_RAW | phase47c | H2 | 223 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H2/223/NOMAD_RAW | phase47c | H2 | 223 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H2/223/OURS-DETOUR+HMM | phase47c | H2 | 223 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 42 | 7.525 | 44.08 |
| phase47c/H2/223/OURS-DETOUR+HMM | phase47c | H2 | 223 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 44 | 7.625 | 46.08 |
| phase47c/H2/223/OURS-DETOUR+HMM | phase47c | H2 | 223 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H2/223/OURS-DETOUR+HMM | phase47c | H2 | 223 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H2/223/OURS-DETOUR | phase47c | H2 | 223 | OURS-DETOUR | ARGMIN | True | True | True | 17 | 5.17 | 19.58 |
| phase47c/H2/223/OURS-DETOUR | phase47c | H2 | 223 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H2/223/OURS-DETOUR | phase47c | H2 | 223 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H2/223/OURS-DETOUR | phase47c | H2 | 223 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H2/224/NOMAD_RAW | phase47c | H2 | 224 | NOMAD_RAW | ARGMIN | False | True | — | — | — | — |
| phase47c/H2/224/NOMAD_RAW | phase47c | H2 | 224 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H2/224/NOMAD_RAW | phase47c | H2 | 224 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H2/224/NOMAD_RAW | phase47c | H2 | 224 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/H2/224/OURS-DETOUR+HMM | phase47c | H2 | 224 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 77 | 1.093 | 79.08 |
| phase47c/H2/224/OURS-DETOUR+HMM | phase47c | H2 | 224 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 84 | 0.5086 | 85.83 |
| phase47c/H2/224/OURS-DETOUR+HMM | phase47c | H2 | 224 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 84 | 0.5086 | 85.83 |
| phase47c/H2/224/OURS-DETOUR+HMM | phase47c | H2 | 224 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | True | 84 | 0.5086 | 85.83 |
| phase47c/H2/224/OURS-DETOUR | phase47c | H2 | 224 | OURS-DETOUR | ARGMIN | True | True | True | 24 | 6.624 | 26.33 |
| phase47c/H2/224/OURS-DETOUR | phase47c | H2 | 224 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/H2/224/OURS-DETOUR | phase47c | H2 | 224 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/H2/224/OURS-DETOUR | phase47c | H2 | 224 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/L2/221/NOMAD_RAW | phase47c | L2 | 221 | NOMAD_RAW | ARGMIN | True | True | True | 17 | 5.126 | 19.83 |
| phase47c/L2/221/NOMAD_RAW | phase47c | L2 | 221 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/L2/221/NOMAD_RAW | phase47c | L2 | 221 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/L2/221/NOMAD_RAW | phase47c | L2 | 221 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/L2/221/OURS-DETOUR+HMM | phase47c | L2 | 221 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 40 | 0.3655 | 42.58 |
| phase47c/L2/221/OURS-DETOUR+HMM | phase47c | L2 | 221 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 41 | 0.4061 | 43.58 |
| phase47c/L2/221/OURS-DETOUR+HMM | phase47c | L2 | 221 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 39 | 0.4255 | 41.58 |
| phase47c/L2/221/OURS-DETOUR+HMM | phase47c | L2 | 221 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 39 | 0.4255 | 41.58 |
| phase47c/L2/221/OURS-DETOUR | phase47c | L2 | 221 | OURS-DETOUR | ARGMIN | True | True | True | 19 | 5.345 | 21.83 |
| phase47c/L2/221/OURS-DETOUR | phase47c | L2 | 221 | OURS-DETOUR | HMM_FORWARD | True | True | True | 19 | 5.345 | 21.83 |
| phase47c/L2/221/OURS-DETOUR | phase47c | L2 | 221 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/L2/221/OURS-DETOUR | phase47c | L2 | 221 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/L2/222/NOMAD_RAW | phase47c | L2 | 222 | NOMAD_RAW | ARGMIN | True | True | True | 42 | 0.6857 | 44.83 |
| phase47c/L2/222/NOMAD_RAW | phase47c | L2 | 222 | NOMAD_RAW | HMM_FORWARD | True | True | True | 42 | 0.6857 | 44.83 |
| phase47c/L2/222/NOMAD_RAW | phase47c | L2 | 222 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 42 | 0.6857 | 44.83 |
| phase47c/L2/222/NOMAD_RAW | phase47c | L2 | 222 | NOMAD_RAW | FG_2PCT_ONE_DRAW | True | True | True | 42 | 0.6857 | 44.83 |
| phase47c/L2/222/OURS-DETOUR+HMM | phase47c | L2 | 222 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 46 | 0.5989 | 48.58 |
| phase47c/L2/222/OURS-DETOUR+HMM | phase47c | L2 | 222 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 48 | 0.2269 | 50.58 |
| phase47c/L2/222/OURS-DETOUR+HMM | phase47c | L2 | 222 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 48 | 0.2269 | 50.58 |
| phase47c/L2/222/OURS-DETOUR+HMM | phase47c | L2 | 222 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 48 | 0.2269 | 50.58 |
| phase47c/L2/222/OURS-DETOUR | phase47c | L2 | 222 | OURS-DETOUR | ARGMIN | True | True | True | 15 | 5.333 | 17.86 |
| phase47c/L2/222/OURS-DETOUR | phase47c | L2 | 222 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/L2/222/OURS-DETOUR | phase47c | L2 | 222 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/L2/222/OURS-DETOUR | phase47c | L2 | 222 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/L2/223/NOMAD_RAW | phase47c | L2 | 223 | NOMAD_RAW | ARGMIN | True | True | True | 12 | 5.609 | 14.83 |
| phase47c/L2/223/NOMAD_RAW | phase47c | L2 | 223 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/L2/223/NOMAD_RAW | phase47c | L2 | 223 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/L2/223/NOMAD_RAW | phase47c | L2 | 223 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/L2/223/OURS-DETOUR+HMM | phase47c | L2 | 223 | OURS-DETOUR+HMM | ARGMIN | True | True | True | 63 | 7.505 | 65.83 |
| phase47c/L2/223/OURS-DETOUR+HMM | phase47c | L2 | 223 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | True | 63 | 7.505 | 65.83 |
| phase47c/L2/223/OURS-DETOUR+HMM | phase47c | L2 | 223 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/L2/223/OURS-DETOUR+HMM | phase47c | L2 | 223 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/L2/223/OURS-DETOUR | phase47c | L2 | 223 | OURS-DETOUR | ARGMIN | True | True | True | 16 | 5.558 | 18.83 |
| phase47c/L2/223/OURS-DETOUR | phase47c | L2 | 223 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/L2/223/OURS-DETOUR | phase47c | L2 | 223 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/L2/223/OURS-DETOUR | phase47c | L2 | 223 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/L2/224/NOMAD_RAW | phase47c | L2 | 224 | NOMAD_RAW | ARGMIN | True | True | True | 14 | 5.34 | 16.58 |
| phase47c/L2/224/NOMAD_RAW | phase47c | L2 | 224 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/L2/224/NOMAD_RAW | phase47c | L2 | 224 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/L2/224/NOMAD_RAW | phase47c | L2 | 224 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/L2/224/OURS-DETOUR+HMM | phase47c | L2 | 224 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 50 | 0.3068 | 52.58 |
| phase47c/L2/224/OURS-DETOUR+HMM | phase47c | L2 | 224 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 50 | 0.3068 | 52.58 |
| phase47c/L2/224/OURS-DETOUR+HMM | phase47c | L2 | 224 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 49 | 0.4076 | 51.58 |
| phase47c/L2/224/OURS-DETOUR+HMM | phase47c | L2 | 224 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 49 | 0.4076 | 51.58 |
| phase47c/L2/224/OURS-DETOUR | phase47c | L2 | 224 | OURS-DETOUR | ARGMIN | True | True | True | 12 | 5.792 | 14.83 |
| phase47c/L2/224/OURS-DETOUR | phase47c | L2 | 224 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/L2/224/OURS-DETOUR | phase47c | L2 | 224 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/L2/224/OURS-DETOUR | phase47c | L2 | 224 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/LC/221/NOMAD_RAW | phase47c | LC | 221 | NOMAD_RAW | ARGMIN | True | True | False | 39 | 0.4736 | 41.58 |
| phase47c/LC/221/NOMAD_RAW | phase47c | LC | 221 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/LC/221/NOMAD_RAW | phase47c | LC | 221 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 25 | 2.151 | 27.58 |
| phase47c/LC/221/NOMAD_RAW | phase47c | LC | 221 | NOMAD_RAW | FG_2PCT_ONE_DRAW | True | True | True | 25 | 2.151 | 27.58 |
| phase47c/LC/221/OURS-DETOUR+HMM | phase47c | LC | 221 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 26 | 0.2661 | 28.83 |
| phase47c/LC/221/OURS-DETOUR+HMM | phase47c | LC | 221 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 26 | 0.2661 | 28.83 |
| phase47c/LC/221/OURS-DETOUR+HMM | phase47c | LC | 221 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 26 | 0.2661 | 28.83 |
| phase47c/LC/221/OURS-DETOUR+HMM | phase47c | LC | 221 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 26 | 0.2661 | 28.83 |
| phase47c/LC/221/OURS-DETOUR | phase47c | LC | 221 | OURS-DETOUR | ARGMIN | True | True | True | 23 | 0.6551 | 25.83 |
| phase47c/LC/221/OURS-DETOUR | phase47c | LC | 221 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/LC/221/OURS-DETOUR | phase47c | LC | 221 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/LC/221/OURS-DETOUR | phase47c | LC | 221 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/LC/222/NOMAD_RAW | phase47c | LC | 222 | NOMAD_RAW | ARGMIN | True | True | False | 26 | 0.4797 | 28.83 |
| phase47c/LC/222/NOMAD_RAW | phase47c | LC | 222 | NOMAD_RAW | HMM_FORWARD | True | True | False | 26 | 0.4797 | 28.83 |
| phase47c/LC/222/NOMAD_RAW | phase47c | LC | 222 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/LC/222/NOMAD_RAW | phase47c | LC | 222 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/LC/222/OURS-DETOUR+HMM | phase47c | LC | 222 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 26 | 0.4584 | 28.58 |
| phase47c/LC/222/OURS-DETOUR+HMM | phase47c | LC | 222 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 26 | 0.4584 | 28.58 |
| phase47c/LC/222/OURS-DETOUR+HMM | phase47c | LC | 222 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 25 | 0.5965 | 27.58 |
| phase47c/LC/222/OURS-DETOUR+HMM | phase47c | LC | 222 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | True | 25 | 0.5965 | 27.58 |
| phase47c/LC/222/OURS-DETOUR | phase47c | LC | 222 | OURS-DETOUR | ARGMIN | True | True | False | 23 | 0.467 | 25.83 |
| phase47c/LC/222/OURS-DETOUR | phase47c | LC | 222 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/LC/222/OURS-DETOUR | phase47c | LC | 222 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 23 | 0.467 | 25.83 |
| phase47c/LC/222/OURS-DETOUR | phase47c | LC | 222 | OURS-DETOUR | FG_2PCT_ONE_DRAW | True | True | False | 23 | 0.467 | 25.83 |
| phase47c/LC/223/NOMAD_RAW | phase47c | LC | 223 | NOMAD_RAW | ARGMIN | False | True | — | — | — | — |
| phase47c/LC/223/NOMAD_RAW | phase47c | LC | 223 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/LC/223/NOMAD_RAW | phase47c | LC | 223 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | True | True | True | 20 | 2.24 | 22.83 |
| phase47c/LC/223/NOMAD_RAW | phase47c | LC | 223 | NOMAD_RAW | FG_2PCT_ONE_DRAW | True | True | True | 20 | 2.24 | 22.83 |
| phase47c/LC/223/OURS-DETOUR+HMM | phase47c | LC | 223 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 25 | 0.4706 | 27.58 |
| phase47c/LC/223/OURS-DETOUR+HMM | phase47c | LC | 223 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 27 | 0.336 | 29.58 |
| phase47c/LC/223/OURS-DETOUR+HMM | phase47c | LC | 223 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 25 | 0.4706 | 27.58 |
| phase47c/LC/223/OURS-DETOUR+HMM | phase47c | LC | 223 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 25 | 0.4706 | 27.58 |
| phase47c/LC/223/OURS-DETOUR | phase47c | LC | 223 | OURS-DETOUR | ARGMIN | True | True | False | 25 | 0.3184 | 27.58 |
| phase47c/LC/223/OURS-DETOUR | phase47c | LC | 223 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/LC/223/OURS-DETOUR | phase47c | LC | 223 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 25 | 0.3184 | 27.58 |
| phase47c/LC/223/OURS-DETOUR | phase47c | LC | 223 | OURS-DETOUR | FG_2PCT_ONE_DRAW | True | True | False | 25 | 0.3184 | 27.58 |
| phase47c/LC/224/NOMAD_RAW | phase47c | LC | 224 | NOMAD_RAW | ARGMIN | True | True | False | 27 | 0.319 | 29.82 |
| phase47c/LC/224/NOMAD_RAW | phase47c | LC | 224 | NOMAD_RAW | HMM_FORWARD | True | True | False | 27 | 0.319 | 29.82 |
| phase47c/LC/224/NOMAD_RAW | phase47c | LC | 224 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 27 | 0.319 | 29.82 |
| phase47c/LC/224/NOMAD_RAW | phase47c | LC | 224 | NOMAD_RAW | FG_2PCT_ONE_DRAW | True | True | False | 27 | 0.319 | 29.82 |
| phase47c/LC/224/OURS-DETOUR+HMM | phase47c | LC | 224 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 24 | 0.3758 | 26.83 |
| phase47c/LC/224/OURS-DETOUR+HMM | phase47c | LC | 224 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 26 | 0.2263 | 28.83 |
| phase47c/LC/224/OURS-DETOUR+HMM | phase47c | LC | 224 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 25 | 0.2756 | 27.83 |
| phase47c/LC/224/OURS-DETOUR+HMM | phase47c | LC | 224 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 25 | 0.2756 | 27.83 |
| phase47c/LC/224/OURS-DETOUR | phase47c | LC | 224 | OURS-DETOUR | ARGMIN | True | True | True | 24 | 0.5295 | 26.83 |
| phase47c/LC/224/OURS-DETOUR | phase47c | LC | 224 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/LC/224/OURS-DETOUR | phase47c | LC | 224 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/LC/224/OURS-DETOUR | phase47c | LC | 224 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/221/NOMAD_RAW | phase47c | SLW | 221 | NOMAD_RAW | ARGMIN | True | True | True | 23 | 3.107 | 25.83 |
| phase47c/SLW/221/NOMAD_RAW | phase47c | SLW | 221 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/221/NOMAD_RAW | phase47c | SLW | 221 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/221/NOMAD_RAW | phase47c | SLW | 221 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/221/OURS-DETOUR+HMM | phase47c | SLW | 221 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 48 | 0.3486 | 50.58 |
| phase47c/SLW/221/OURS-DETOUR+HMM | phase47c | SLW | 221 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 48 | 0.3486 | 50.58 |
| phase47c/SLW/221/OURS-DETOUR+HMM | phase47c | SLW | 221 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 48 | 0.3486 | 50.58 |
| phase47c/SLW/221/OURS-DETOUR+HMM | phase47c | SLW | 221 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 48 | 0.3486 | 50.58 |
| phase47c/SLW/221/OURS-DETOUR | phase47c | SLW | 221 | OURS-DETOUR | ARGMIN | True | True | True | 9 | 3.643 | 11.57 |
| phase47c/SLW/221/OURS-DETOUR | phase47c | SLW | 221 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/221/OURS-DETOUR | phase47c | SLW | 221 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/221/OURS-DETOUR | phase47c | SLW | 221 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/222/NOMAD_RAW | phase47c | SLW | 222 | NOMAD_RAW | ARGMIN | False | True | — | — | — | — |
| phase47c/SLW/222/NOMAD_RAW | phase47c | SLW | 222 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/222/NOMAD_RAW | phase47c | SLW | 222 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/222/NOMAD_RAW | phase47c | SLW | 222 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/222/OURS-DETOUR+HMM | phase47c | SLW | 222 | OURS-DETOUR+HMM | ARGMIN | False | True | — | — | — | — |
| phase47c/SLW/222/OURS-DETOUR+HMM | phase47c | SLW | 222 | OURS-DETOUR+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/222/OURS-DETOUR+HMM | phase47c | SLW | 222 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/222/OURS-DETOUR+HMM | phase47c | SLW | 222 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/222/OURS-DETOUR | phase47c | SLW | 222 | OURS-DETOUR | ARGMIN | True | True | True | 26 | 2.99 | 28.82 |
| phase47c/SLW/222/OURS-DETOUR | phase47c | SLW | 222 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/222/OURS-DETOUR | phase47c | SLW | 222 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/222/OURS-DETOUR | phase47c | SLW | 222 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/223/NOMAD_RAW | phase47c | SLW | 223 | NOMAD_RAW | ARGMIN | False | True | — | — | — | — |
| phase47c/SLW/223/NOMAD_RAW | phase47c | SLW | 223 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/223/NOMAD_RAW | phase47c | SLW | 223 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/223/NOMAD_RAW | phase47c | SLW | 223 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/223/OURS-DETOUR+HMM | phase47c | SLW | 223 | OURS-DETOUR+HMM | ARGMIN | False | True | — | — | — | — |
| phase47c/SLW/223/OURS-DETOUR+HMM | phase47c | SLW | 223 | OURS-DETOUR+HMM | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/223/OURS-DETOUR+HMM | phase47c | SLW | 223 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/223/OURS-DETOUR+HMM | phase47c | SLW | 223 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/223/OURS-DETOUR | phase47c | SLW | 223 | OURS-DETOUR | ARGMIN | True | True | True | 14 | 2.766 | 16.85 |
| phase47c/SLW/223/OURS-DETOUR | phase47c | SLW | 223 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/223/OURS-DETOUR | phase47c | SLW | 223 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/223/OURS-DETOUR | phase47c | SLW | 223 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/224/NOMAD_RAW | phase47c | SLW | 224 | NOMAD_RAW | ARGMIN | False | True | — | — | — | — |
| phase47c/SLW/224/NOMAD_RAW | phase47c | SLW | 224 | NOMAD_RAW | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/224/NOMAD_RAW | phase47c | SLW | 224 | NOMAD_RAW | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/224/NOMAD_RAW | phase47c | SLW | 224 | NOMAD_RAW | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |
| phase47c/SLW/224/OURS-DETOUR+HMM | phase47c | SLW | 224 | OURS-DETOUR+HMM | ARGMIN | True | True | False | 57 | 0.4657 | 58.83 |
| phase47c/SLW/224/OURS-DETOUR+HMM | phase47c | SLW | 224 | OURS-DETOUR+HMM | HMM_FORWARD | True | True | False | 57 | 0.4657 | 58.83 |
| phase47c/SLW/224/OURS-DETOUR+HMM | phase47c | SLW | 224 | OURS-DETOUR+HMM | FG_HARD_0ERR_UPPER_BOUND | True | True | False | 57 | 0.4657 | 58.83 |
| phase47c/SLW/224/OURS-DETOUR+HMM | phase47c | SLW | 224 | OURS-DETOUR+HMM | FG_2PCT_ONE_DRAW | True | True | False | 57 | 0.4657 | 58.83 |
| phase47c/SLW/224/OURS-DETOUR | phase47c | SLW | 224 | OURS-DETOUR | ARGMIN | False | True | — | — | — | — |
| phase47c/SLW/224/OURS-DETOUR | phase47c | SLW | 224 | OURS-DETOUR | HMM_FORWARD | False | True | — | — | — | — |
| phase47c/SLW/224/OURS-DETOUR | phase47c | SLW | 224 | OURS-DETOUR | FG_HARD_0ERR_UPPER_BOUND | False | True | — | — | — | — |
| phase47c/SLW/224/OURS-DETOUR | phase47c | SLW | 224 | OURS-DETOUR | FG_2PCT_ONE_DRAW | False | True | — | — | — | — |

| table |
|---|
| 실행 정보 |

| saved_runs | inferences | elapsed_s | workers | simulations_started | new_nomad_inferences | noise_realizations | noise_seed | rules_sha256 | source_sha256 |
|---|---|---|---|---|---|---|---|---|---|
| 111 | 4959 | 83.04 | 4 | 0 | 0 | 1 | 20261112 | a2932ba67b5eff867fd9d278acf1fb00fae704bd0ed58e732f12a17058eb2fbe | {'research/nomad_phase48o/__init__.py': '299180235591bcd7a7bbd47fc4bbc4bf1aa74cb1d24b05ce5df299ccf76adea1', 'research/nomad_phase48o/graph.py': '1068178970a9a645b9e1f1a33d391c67ee4780b00bbd1ed266f2953749c7f0b0', 'research/nomad_phase48o/test_graph.py': '46b7d727941a14fb4a9ab7a94e55fe62ef7f00c584913123c91a41107aea0049', 'research/nomad_phase48o/data.py': '0d3586a9d1b1acce5cadb055ab225d4fb257a927215bc25498f1ac1fdaeb08a5', 'research/nomad_phase48o/analyze.py': '2ba142aafe535a830c4bc1fffb838d97cddc019a1d8e0ccc667381ddde2c16a3'} |
