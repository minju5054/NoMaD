# Phase53-P

| status | completed | planned | protocol_sha256 |
|---|---|---|---|
| COMPLETE | 40 | 40 | 1cc31fda1f431072cb8687d9ea7b1c1e70e628b05f0346067a6199fdd558f6eb |

| item | value |
|---|---|
| frozen | Phase47 HMM/official declared arrival,geometry/jitter/controller/SAFE/filter/RECOVER; no R2/R3;original1s receipt-age expiry. No Phase52 HOLD or predictedB dispatch. |
| tail | At earlier path endpoint/2s request frozen stop_command until v=0 at72Hz;omega also frozen stop_command. Swept depth footprint>=.025. Periodic continuation respects original9Hz phase (36tick checks). |
| graph | Direct nomad_phase17.graph.ClearanceGraph (Phase18 same implementation), native8SE2poses/24variables, SLSQP maxiter100 ftol1e-8 analytic Jacobians; no factor/weight/option changes;previous prior last actually installed acceptedGraph; no new init or resampling. |
| heading_curvature | Start heading SOFT sigma10deg at interpolated entry E; boundary position sigma.01m. Hard boundary tangent-circle curvature kappa_before=w/v plus Menger abs<=8. Not hard fixed B pose. v=0 undefined curvature and abs(w/v)>8 retain frozen initialization rejection and CUT fallback. |
| synchronous | One external system-Python persistent RPC, caller waits synchronously at installation actual pose; no predicted pose or delayed result reuse. RPC30s watchdog is technical error,not solver tuning. Solver compute time and wholeRPC logged. |
| install_scope | Final EC-selected native CUT chunk installation,including alternative SAFE candidates selected by unchanged fallback. On periodic replacement refine the corresponding native candidate rather than recursively refine Graph XY. EC-tail rechecks Graph with latest map;failed/no-convergence uses the same already-passed CUT candidate. |
| success | Frozen official declared stop, distance<=.5m and no collision;wrong stop>.5m; timeout without declaration unchanged. |
| heading_discontinuity | At actual installation B: wrapped direction difference between previous and installed XY suffixes projected at B,first .05m; p50/p95 degrees;undefined endpoint directions excluded/count recorded. |
| time | Actual72Hz /v/<.01 stop duration; command-state intervals include ALIGN_ROTATE;arrival median only successes. |
| graph_rate | Actually installed Graph / synchronous Graph attempts;also attempts,installations,reasons,solve p50/p95. No Graph in CUT. |
| historical | Same seed published Phase47/51/52 aggregates reused without extra analysis. Different days;Phase51 WIDE geometry differs;Phase52 HOLD differs. Historical missing fields remain empty,not zero-filled. |
| execution | 40main serial,one technical retry,global lock,resume completed runs,storagev2,cache cleanup,30GB reserve,automatic systemPython report+commit+push. One LC smoke only;no main in preparation. |

| condition | scene | method | n | valid | success | collision | wrong_stop | timeout_without_declaration | goal_time_s_median | stopped_s_median | align_rotate_s_median | heading_discontinuity_p50_deg_median | heading_discontinuity_p95_deg_median | minimum_clearance_m_median | ec_rejects_median | graph_adoption_rate_median | graph_solve_p50_s_median | graph_solve_p95_s_median |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D075 | SLW | CUT | 2 | 2 | 1 | 0 | 1 | 0 | 42.833 | 31 | 10.833 | 31.018 | 132.99 | 0.054909 | 43.5 | — | — | — |
| D075 | LC | CUT | 2 | 2 | 2 | 0 | 0 | 0 | 32.208 | 4.1667 | 0.88889 | 18.587 | 71.583 | 0.25715 | 1.5 | — | — | — |
| D075 | L2 | CUT | 2 | 2 | 1 | 0 | 1 | 0 | 41.583 | 10.333 | 4.5556 | 30.695 | 100.9 | 0.071208 | 6 | — | — | — |
| D075 | H1 | CUT | 2 | 2 | 1 | 0 | 0 | 1 | 32.583 | 12.722 | 4.3889 | 20.052 | 96.322 | 0.11374 | 11.5 | — | — | — |
| D075 | H2 | CUT | 2 | 2 | 2 | 0 | 0 | 0 | 80.333 | 6.4444 | 2.8333 | 23.056 | 109.09 | 0.070461 | 15 | — | — | — |
| D075 | ALL | CUT | 10 | 10 | 7 | 0 | 2 | 1 | 41.583 | 6.4444 | 2.5 | 23.056 | 100.56 | 0.085314 | 12.5 | — | — | — |
| D075 | SLW | GRAPH-HO | 2 | 2 | 1 | 0 | 1 | 0 | 43.833 | 8.1667 | 3.3889 | 23.509 | 129.99 | 0.094851 | 18 | 0.57222 | 0.15472 | 0.26376 |
| D075 | LC | GRAPH-HO | 2 | 2 | 2 | 0 | 0 | 0 | 29.715 | 3.1806 | 0 | 11.233 | 37.141 | 0.22422 | 0.5 | 0.96362 | 0.15534 | 0.18207 |
| D075 | L2 | GRAPH-HO | 2 | 2 | 1 | 0 | 1 | 0 | 76.333 | 11.361 | 4.0833 | 16.945 | 97.172 | 0.094585 | 12.5 | 0.81182 | 0.15605 | 0.23211 |
| D075 | H1 | GRAPH-HO | 2 | 2 | 1 | 0 | 1 | 0 | 31.833 | 6.1111 | 0.88889 | 13.674 | 51.732 | 0.087587 | 6 | 0.81842 | 0.15531 | 0.20182 |
| D075 | H2 | GRAPH-HO | 2 | 2 | 0 | 0 | 0 | 2 | — | 6.3333 | 1.2222 | 13.238 | 61.438 | 0.069816 | 15 | 0.89186 | 0.16828 | 0.23645 |
| D075 | ALL | GRAPH-HO | 10 | 10 | 5 | 0 | 3 | 2 | 31.833 | 6.3333 | 1.8333 | 14.47 | 65.817 | 0.095654 | 10 | 0.89186 | 0.15566 | 0.21319 |
| D150 | SLW | CUT | 2 | 2 | 1 | 0 | 0 | 1 | 88.833 | 41.361 | 7.9444 | 35.441 | 136.94 | 0.052318 | 30 | — | — | — |
| D150 | LC | CUT | 2 | 2 | 2 | 0 | 0 | 0 | 49.833 | 17 | 3 | 27.067 | 67.587 | 0.21811 | 9.5 | — | — | — |
| D150 | L2 | CUT | 2 | 2 | 1 | 0 | 0 | 1 | 82.083 | 33.375 | 4 | 25.093 | 102.02 | 0.064457 | 13.5 | — | — | — |
| D150 | H1 | CUT | 2 | 2 | 1 | 0 | 1 | 0 | 52.333 | 17.722 | 1.5 | 30.817 | 68.282 | 0.13551 | 16 | — | — | — |
| D150 | H2 | CUT | 2 | 2 | 0 | 0 | 0 | 2 | — | 34.944 | 5.5 | 28.494 | 102.02 | 0.086874 | 12.5 | — | — | — |
| D150 | ALL | CUT | 10 | 10 | 5 | 0 | 1 | 4 | 52.333 | 30.264 | 4 | 27.873 | 84.764 | 0.077592 | 15.5 | — | — | — |
| D150 | SLW | GRAPH-HO | 2 | 2 | 1 | 0 | 1 | 0 | 83.833 | 34.229 | 3 | 24.628 | 112.88 | 0.084704 | 40 | 0.091667 | 0.074486 | 0.15201 |
| D150 | LC | GRAPH-HO | 2 | 2 | 2 | 0 | 0 | 0 | 45.215 | 14.382 | 2 | 17.21 | 54.94 | 0.19878 | 8 | 0.094074 | 0.076246 | 0.11875 |
| D150 | L2 | GRAPH-HO | 2 | 2 | 1 | 0 | 0 | 1 | 81.889 | 35.722 | 6.6667 | 36.534 | 103.21 | 0.04159 | 26.5 | 0.021568 | 0.075238 | 0.10829 |
| D150 | H1 | GRAPH-HO | 2 | 2 | 1 | 0 | 1 | 0 | 47.139 | 15.875 | 1.5 | 21.497 | 53.292 | 0.098601 | 16.5 | 0.13793 | 0.10738 | 0.19572 |
| D150 | H2 | GRAPH-HO | 2 | 2 | 0 | 0 | 0 | 2 | — | 40.5 | 7 | 43.319 | 104.87 | 0.038713 | 13 | 0.019819 | 0.077156 | 0.12874 |
| D150 | ALL | GRAPH-HO | 10 | 10 | 5 | 0 | 2 | 3 | 47.139 | 31.139 | 3 | 32.996 | 93.884 | 0.055881 | 15 | 0.061667 | 0.075504 | 0.15201 |

| scene | condition | seed | method | status | success | collision | wrong_stop | timeout_without_declaration | goal_time_s | stopped_s | align_rotate_s | heading_discontinuity_p50_deg | heading_discontinuity_p95_deg | minimum_clearance_m | ec_rejects | graph_adoption_rate | graph_solve_p50_s | graph_solve_p95_s | Phase47_D075_OURS-DETOUR+HMM_success | Phase47_D075_OURS-DETOUR+HMM_collision | Phase47_D075_OURS-DETOUR+HMM_wrong_stop | Phase47_D075_OURS-DETOUR+HMM_timeout_without_declaration | Phase47_D075_OURS-DETOUR+HMM_goal_time_s | Phase47_D075_OURS-DETOUR+HMM_stopped_s | Phase47_D075_OURS-DETOUR+HMM_align_rotate_s | Phase47_D075_OURS-DETOUR+HMM_heading_discontinuity_p50_deg | Phase47_D075_OURS-DETOUR+HMM_heading_discontinuity_p95_deg | Phase47_D075_OURS-DETOUR+HMM_minimum_clearance_m | Phase47_D075_OURS-DETOUR+HMM_ec_rejects | Phase47_D075_OURS-DETOUR+HMM_graph_adoption_rate | Phase47_D075_OURS-DETOUR+HMM_graph_solve_p50_s | Phase47_D075_OURS-DETOUR+HMM_graph_solve_p95_s | Phase51_L150_OURS-DETOUR+HMM_success | Phase51_L150_OURS-DETOUR+HMM_collision | Phase51_L150_OURS-DETOUR+HMM_wrong_stop | Phase51_L150_OURS-DETOUR+HMM_timeout_without_declaration | Phase51_L150_OURS-DETOUR+HMM_goal_time_s | Phase51_L150_OURS-DETOUR+HMM_stopped_s | Phase51_L150_OURS-DETOUR+HMM_align_rotate_s | Phase51_L150_OURS-DETOUR+HMM_heading_discontinuity_p50_deg | Phase51_L150_OURS-DETOUR+HMM_heading_discontinuity_p95_deg | Phase51_L150_OURS-DETOUR+HMM_minimum_clearance_m | Phase51_L150_OURS-DETOUR+HMM_ec_rejects | Phase51_L150_OURS-DETOUR+HMM_graph_adoption_rate | Phase51_L150_OURS-DETOUR+HMM_graph_solve_p50_s | Phase51_L150_OURS-DETOUR+HMM_graph_solve_p95_s | Phase51_WIDE_OURS-DETOUR+HMM_success | Phase51_WIDE_OURS-DETOUR+HMM_collision | Phase51_WIDE_OURS-DETOUR+HMM_wrong_stop | Phase51_WIDE_OURS-DETOUR+HMM_timeout_without_declaration | Phase51_WIDE_OURS-DETOUR+HMM_goal_time_s | Phase51_WIDE_OURS-DETOUR+HMM_stopped_s | Phase51_WIDE_OURS-DETOUR+HMM_align_rotate_s | Phase51_WIDE_OURS-DETOUR+HMM_heading_discontinuity_p50_deg | Phase51_WIDE_OURS-DETOUR+HMM_heading_discontinuity_p95_deg | Phase51_WIDE_OURS-DETOUR+HMM_minimum_clearance_m | Phase51_WIDE_OURS-DETOUR+HMM_ec_rejects | Phase51_WIDE_OURS-DETOUR+HMM_graph_adoption_rate | Phase51_WIDE_OURS-DETOUR+HMM_graph_solve_p50_s | Phase51_WIDE_OURS-DETOUR+HMM_graph_solve_p95_s | Phase52_D075_CUT-HOLD_success | Phase52_D075_CUT-HOLD_collision | Phase52_D075_CUT-HOLD_wrong_stop | Phase52_D075_CUT-HOLD_timeout_without_declaration | Phase52_D075_CUT-HOLD_goal_time_s | Phase52_D075_CUT-HOLD_stopped_s | Phase52_D075_CUT-HOLD_align_rotate_s | Phase52_D075_CUT-HOLD_heading_discontinuity_p50_deg | Phase52_D075_CUT-HOLD_heading_discontinuity_p95_deg | Phase52_D075_CUT-HOLD_minimum_clearance_m | Phase52_D075_CUT-HOLD_ec_rejects | Phase52_D075_CUT-HOLD_graph_adoption_rate | Phase52_D075_CUT-HOLD_graph_solve_p50_s | Phase52_D075_CUT-HOLD_graph_solve_p95_s | Phase52_D075_GRAPH-REC_success | Phase52_D075_GRAPH-REC_collision | Phase52_D075_GRAPH-REC_wrong_stop | Phase52_D075_GRAPH-REC_timeout_without_declaration | Phase52_D075_GRAPH-REC_goal_time_s | Phase52_D075_GRAPH-REC_stopped_s | Phase52_D075_GRAPH-REC_align_rotate_s | Phase52_D075_GRAPH-REC_heading_discontinuity_p50_deg | Phase52_D075_GRAPH-REC_heading_discontinuity_p95_deg | Phase52_D075_GRAPH-REC_minimum_clearance_m | Phase52_D075_GRAPH-REC_ec_rejects | Phase52_D075_GRAPH-REC_graph_adoption_rate | Phase52_D075_GRAPH-REC_graph_solve_p50_s | Phase52_D075_GRAPH-REC_graph_solve_p95_s | Phase52_D150_CUT-HOLD_success | Phase52_D150_CUT-HOLD_collision | Phase52_D150_CUT-HOLD_wrong_stop | Phase52_D150_CUT-HOLD_timeout_without_declaration | Phase52_D150_CUT-HOLD_goal_time_s | Phase52_D150_CUT-HOLD_stopped_s | Phase52_D150_CUT-HOLD_align_rotate_s | Phase52_D150_CUT-HOLD_heading_discontinuity_p50_deg | Phase52_D150_CUT-HOLD_heading_discontinuity_p95_deg | Phase52_D150_CUT-HOLD_minimum_clearance_m | Phase52_D150_CUT-HOLD_ec_rejects | Phase52_D150_CUT-HOLD_graph_adoption_rate | Phase52_D150_CUT-HOLD_graph_solve_p50_s | Phase52_D150_CUT-HOLD_graph_solve_p95_s | Phase52_D150_GRAPH-REC_success | Phase52_D150_GRAPH-REC_collision | Phase52_D150_GRAPH-REC_wrong_stop | Phase52_D150_GRAPH-REC_timeout_without_declaration | Phase52_D150_GRAPH-REC_goal_time_s | Phase52_D150_GRAPH-REC_stopped_s | Phase52_D150_GRAPH-REC_align_rotate_s | Phase52_D150_GRAPH-REC_heading_discontinuity_p50_deg | Phase52_D150_GRAPH-REC_heading_discontinuity_p95_deg | Phase52_D150_GRAPH-REC_minimum_clearance_m | Phase52_D150_GRAPH-REC_ec_rejects | Phase52_D150_GRAPH-REC_graph_adoption_rate | Phase52_D150_GRAPH-REC_graph_solve_p50_s | Phase52_D150_GRAPH-REC_graph_solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLW | D075 | 221 | CUT | PASS | False | False | True | False | — | 54.222 | 19.222 | 27.894 | 164.92 | 0.048456 | 74 | — | — | — | True | False | False | False | 50.583 | 8.5556 | 4.4444 | 27.072 | 156.63 | 0.05017 | 15 | — | — | — | False | False | False | True | — | 50.111 | 11 | 55.557 | 172.46 | 0.047617 | 43 | — | — | — | True | False | False | False | 51.833 | 11.222 | 4.6667 | 49.963 | 132.32 | 0.098375 | 10 | — | — | — | False | False | False | True | — | 22.333 | 12.667 | 28.876 | 162.11 | 0.030989 | 50 | — | — | — | False | False | True | False | — | 13.431 | 6.875 | 22.096 | 142.26 | 0.04191 | 27 | 0.15873 | 0.13287 | 0.16934 | False | False | False | True | — | 24.778 | 16.556 | 34.9 | 129.35 | 0.045217 | 58 | — | — | — | True | False | False | False | 66.375 | 19.222 | 14.333 | 40.565 | 162.1 | 0.039648 | 36 | 0.19444 | 0.13748 | 0.21053 |
| SLW | D075 | 221 | GRAPH-HO | PASS | True | False | False | False | 43.833 | 5.7778 | 1.8889 | 15.026 | 116.09 | 0.1571 | 16 | 0.7 | 0.15388 | 0.24005 | True | False | False | False | 50.583 | 8.5556 | 4.4444 | 27.072 | 156.63 | 0.05017 | 15 | — | — | — | False | False | False | True | — | 50.111 | 11 | 55.557 | 172.46 | 0.047617 | 43 | — | — | — | True | False | False | False | 51.833 | 11.222 | 4.6667 | 49.963 | 132.32 | 0.098375 | 10 | — | — | — | False | False | False | True | — | 22.333 | 12.667 | 28.876 | 162.11 | 0.030989 | 50 | — | — | — | False | False | True | False | — | 13.431 | 6.875 | 22.096 | 142.26 | 0.04191 | 27 | 0.15873 | 0.13287 | 0.16934 | False | False | False | True | — | 24.778 | 16.556 | 34.9 | 129.35 | 0.045217 | 58 | — | — | — | True | False | False | False | 66.375 | 19.222 | 14.333 | 40.565 | 162.1 | 0.039648 | 36 | 0.19444 | 0.13748 | 0.21053 |
| LC | D075 | 221 | GRAPH-HO | PASS | True | False | False | False | 29.847 | 2.8889 | 0 | 14.37 | 41.323 | 0.23473 | 1 | 0.96429 | 0.15538 | 0.17822 | True | False | False | False | 28.833 | 3.4444 | 0.44444 | 20.716 | 46.903 | 0.14534 | 0 | — | — | — | True | False | False | False | 66.083 | 23.75 | 4 | 62.068 | 154.5 | 0.054849 | 3 | — | — | — | True | False | False | False | 28.833 | 2.8889 | — | 21.956 | 82.525 | 0.30967 | 1 | — | — | — | True | False | False | False | 28.083 | 3.2222 | 0.22222 | 12.181 | 38.388 | 0.28357 | 2 | — | — | — | False | False | True | False | — | 7.2222 | 3.7778 | 26.014 | 97.331 | 0.10416 | 0 | 0.23214 | 0.13025 | 0.16673 | True | False | False | False | 35.083 | 7.5556 | 3.5556 | 26.878 | 69.227 | 0.22891 | 12 | — | — | — | True | False | False | False | 42.097 | 8.5556 | 4.4444 | 8.4623 | 44.082 | 0.15965 | 8 | 0.27273 | 0.14445 | 0.21323 |
| LC | D075 | 221 | CUT | PASS | True | False | False | False | 29.583 | 3.2222 | 0 | 14.744 | 43.118 | 0.29339 | 1 | — | — | — | True | False | False | False | 28.833 | 3.4444 | 0.44444 | 20.716 | 46.903 | 0.14534 | 0 | — | — | — | True | False | False | False | 66.083 | 23.75 | 4 | 62.068 | 154.5 | 0.054849 | 3 | — | — | — | True | False | False | False | 28.833 | 2.8889 | — | 21.956 | 82.525 | 0.30967 | 1 | — | — | — | True | False | False | False | 28.083 | 3.2222 | 0.22222 | 12.181 | 38.388 | 0.28357 | 2 | — | — | — | False | False | True | False | — | 7.2222 | 3.7778 | 26.014 | 97.331 | 0.10416 | 0 | 0.23214 | 0.13025 | 0.16673 | True | False | False | False | 35.083 | 7.5556 | 3.5556 | 26.878 | 69.227 | 0.22891 | 12 | — | — | — | True | False | False | False | 42.097 | 8.5556 | 4.4444 | 8.4623 | 44.082 | 0.15965 | 8 | 0.27273 | 0.14445 | 0.21323 |
| L2 | D075 | 221 | CUT | PASS | True | False | False | False | 41.583 | 3.7778 | 0.77778 | 18.624 | 59.392 | 0.10824 | 0 | — | — | — | True | False | False | False | 43.583 | 2.8889 | — | 24.239 | 64.453 | 0.077717 | 0 | — | — | — | False | False | False | True | — | 36.667 | 6 | 35.472 | 103.38 | 0.22765 | 3 | — | — | — | False | False | True | False | — | 6.2222 | 1.8889 | 32.586 | 99.142 | 0.081417 | 3 | — | — | — | True | False | False | False | 37.833 | 3.6667 | 0.66667 | 18.736 | 58.543 | 0.053993 | 2 | — | — | — | False | True | False | False | — | 3.6667 | 0.66667 | 12.85 | 45.55 | -1.226e-05 | 21 | 0.11765 | 0.13774 | 0.22433 | False | False | False | True | — | 69 | 5.3333 | 38.129 | 93.338 | 0.031282 | 1 | — | — | — | True | False | False | False | 52.639 | 12.889 | 8.3333 | 18.468 | 58.92 | 0.041616 | 12 | 0.10714 | 0.13462 | 0.173 |
| L2 | D075 | 221 | GRAPH-HO | PASS | True | False | False | False | 76.333 | 6.8889 | 2.6667 | 11.967 | 59.559 | 0.1437 | 0 | 0.90141 | 0.15574 | 0.20268 | True | False | False | False | 43.583 | 2.8889 | — | 24.239 | 64.453 | 0.077717 | 0 | — | — | — | False | False | False | True | — | 36.667 | 6 | 35.472 | 103.38 | 0.22765 | 3 | — | — | — | False | False | True | False | — | 6.2222 | 1.8889 | 32.586 | 99.142 | 0.081417 | 3 | — | — | — | True | False | False | False | 37.833 | 3.6667 | 0.66667 | 18.736 | 58.543 | 0.053993 | 2 | — | — | — | False | True | False | False | — | 3.6667 | 0.66667 | 12.85 | 45.55 | -1.226e-05 | 21 | 0.11765 | 0.13774 | 0.22433 | False | False | False | True | — | 69 | 5.3333 | 38.129 | 93.338 | 0.031282 | 1 | — | — | — | True | False | False | False | 52.639 | 12.889 | 8.3333 | 18.468 | 58.92 | 0.041616 | 12 | 0.10714 | 0.13462 | 0.173 |
| H1 | D075 | 221 | GRAPH-HO | PASS | False | False | True | False | — | 8.7778 | 1.7778 | 16.646 | 76.244 | 0.061361 | 5 | 0.73684 | 0.15364 | 0.22369 | True | False | False | False | 33.833 | 6.1111 | — | 14.152 | 62.629 | 0.053273 | 4 | — | — | — | True | False | False | False | 59.333 | 25.111 | 1 | 14.545 | 43.871 | 0.041029 | 9 | — | — | — | False | False | True | False | — | 13.667 | 2.4444 | 26.682 | 100.03 | 0.030769 | 7 | — | — | — | False | False | True | False | — | 3.3333 | 0.33333 | 18.858 | 89.706 | 0.035381 | 10 | — | — | — | True | False | False | False | 31.847 | 3.2222 | 0.22222 | 13.808 | 38.79 | 0.034883 | 0 | 0.13793 | 0.13187 | 0.22308 | True | False | False | False | 59.583 | 21.333 | 16.556 | 46.036 | 105.33 | 0.031883 | 7 | — | — | — | True | False | False | False | 43.861 | 7.4444 | 3.3333 | 27.236 | 123.27 | 0.13076 | 17 | 0.26087 | 0.14714 | 0.18818 |
| H1 | D075 | 221 | CUT | PASS | False | False | False | True | — | 21 | 7.5556 | 24.055 | 101.27 | 0.084193 | 18 | — | — | — | True | False | False | False | 33.833 | 6.1111 | — | 14.152 | 62.629 | 0.053273 | 4 | — | — | — | True | False | False | False | 59.333 | 25.111 | 1 | 14.545 | 43.871 | 0.041029 | 9 | — | — | — | False | False | True | False | — | 13.667 | 2.4444 | 26.682 | 100.03 | 0.030769 | 7 | — | — | — | False | False | True | False | — | 3.3333 | 0.33333 | 18.858 | 89.706 | 0.035381 | 10 | — | — | — | True | False | False | False | 31.847 | 3.2222 | 0.22222 | 13.808 | 38.79 | 0.034883 | 0 | 0.13793 | 0.13187 | 0.22308 | True | False | False | False | 59.583 | 21.333 | 16.556 | 46.036 | 105.33 | 0.031883 | 7 | — | — | — | True | False | False | False | 43.861 | 7.4444 | 3.3333 | 27.236 | 123.27 | 0.13076 | 17 | 0.26087 | 0.14714 | 0.18818 |
| H2 | D075 | 221 | CUT | PASS | True | False | False | False | 83.583 | 6 | 2.5556 | 23.538 | 95.218 | 0.054486 | 14 | — | — | — | False | False | True | False | — | 11.556 | 6.6667 | 30.531 | 77.649 | 0.062421 | 10 | — | — | — | False | False | False | True | — | 36.111 | 4 | 36.115 | 131.15 | 0.079802 | 14 | — | — | — | False | False | True | False | — | 9.5556 | 3.2222 | 30.064 | 86.19 | 0.20886 | 4 | — | — | — | False | False | False | True | — | 6.6667 | 3.4444 | 29.9 | 98.719 | 0.099346 | 3 | — | — | — | False | False | False | True | — | 6.5556 | 2.7778 | 17.168 | 66.239 | 0.051239 | 9 | 0.22727 | 0.13717 | 0.1921 | False | False | False | True | — | 28.444 | 23 | 56.076 | 120.7 | 0.063406 | 18 | — | — | — | False | False | False | True | — | 41.333 | 36.222 | 47.173 | 165.88 | 0.027397 | 160 | 0.34 | 0.15433 | 0.23505 |
| H2 | D075 | 221 | GRAPH-HO | PASS | False | False | False | True | — | 5.2222 | 1.8889 | 11.906 | 72.076 | 0.077494 | 17 | 0.9 | 0.15846 | 0.18865 | False | False | True | False | — | 11.556 | 6.6667 | 30.531 | 77.649 | 0.062421 | 10 | — | — | — | False | False | False | True | — | 36.111 | 4 | 36.115 | 131.15 | 0.079802 | 14 | — | — | — | False | False | True | False | — | 9.5556 | 3.2222 | 30.064 | 86.19 | 0.20886 | 4 | — | — | — | False | False | False | True | — | 6.6667 | 3.4444 | 29.9 | 98.719 | 0.099346 | 3 | — | — | — | False | False | False | True | — | 6.5556 | 2.7778 | 17.168 | 66.239 | 0.051239 | 9 | 0.22727 | 0.13717 | 0.1921 | False | False | False | True | — | 28.444 | 23 | 56.076 | 120.7 | 0.063406 | 18 | — | — | — | False | False | False | True | — | 41.333 | 36.222 | 47.173 | 165.88 | 0.027397 | 160 | 0.34 | 0.15433 | 0.23505 |
| SLW | D075 | 222 | GRAPH-HO | PASS | False | False | True | False | — | 10.556 | 4.8889 | 31.993 | 143.89 | 0.032598 | 20 | 0.44444 | 0.15557 | 0.28748 | False | False | False | True | — | 17.778 | 8.8889 | 30.566 | 150.3 | 0.039944 | 38 | — | — | — | False | False | False | True | — | 44.778 | 7 | 39.31 | 131.84 | 0.02721 | 29 | — | — | — | False | False | True | False | — | 10 | 5.5556 | 36.256 | 150.3 | 0.064941 | 23 | — | — | — | False | False | False | True | — | 21.111 | 16.111 | 36.422 | 136.77 | 0.027224 | 56 | — | — | — | False | False | False | True | — | 10.444 | 3.7778 | 19.285 | 105.72 | 0.067271 | 35 | 0.17045 | 0.12733 | 0.17057 | False | False | False | True | — | 24.889 | 17.778 | 76.025 | 150.41 | 0.06365 | 57 | — | — | — | True | False | False | False | 75.361 | 21.25 | 14.333 | 27.409 | 148.85 | 0.036108 | 28 | 0.26829 | 0.13707 | 0.17799 |
| SLW | D075 | 222 | CUT | PASS | True | False | False | False | 42.833 | 7.7778 | 2.4444 | 34.143 | 101.07 | 0.061362 | 13 | — | — | — | False | False | False | True | — | 17.778 | 8.8889 | 30.566 | 150.3 | 0.039944 | 38 | — | — | — | False | False | False | True | — | 44.778 | 7 | 39.31 | 131.84 | 0.02721 | 29 | — | — | — | False | False | True | False | — | 10 | 5.5556 | 36.256 | 150.3 | 0.064941 | 23 | — | — | — | False | False | False | True | — | 21.111 | 16.111 | 36.422 | 136.77 | 0.027224 | 56 | — | — | — | False | False | False | True | — | 10.444 | 3.7778 | 19.285 | 105.72 | 0.067271 | 35 | 0.17045 | 0.12733 | 0.17057 | False | False | False | True | — | 24.889 | 17.778 | 76.025 | 150.41 | 0.06365 | 57 | — | — | — | True | False | False | False | 75.361 | 21.25 | 14.333 | 27.409 | 148.85 | 0.036108 | 28 | 0.26829 | 0.13707 | 0.17799 |
| LC | D075 | 222 | CUT | PASS | True | False | False | False | 34.833 | 5.1111 | 1.7778 | 22.431 | 100.05 | 0.2209 | 2 | — | — | — | True | False | False | False | 28.583 | 3.3333 | 0.33333 | 21.998 | 57.25 | 0.14871 | 1 | — | — | — | True | False | False | False | 52.333 | 18 | 3 | 22.835 | 79.768 | 0.30057 | 11 | — | — | — | True | False | False | False | 28.333 | 3.3333 | 0.33333 | 27.568 | 49.577 | 0.20443 | 1 | — | — | — | True | False | False | False | 30.833 | 4 | 0.88889 | 17.825 | 69.451 | 0.1832 | 2 | — | — | — | True | False | False | False | 28.889 | 3.3333 | 0.33333 | 13.184 | 51.917 | 0.28307 | 2 | 0.076923 | 0.12859 | 0.1713 | False | False | True | False | — | 26.75 | 21.306 | 76.125 | 156.45 | 0.092175 | 0 | — | — | — | False | False | True | False | — | 10.333 | 5.7778 | 20.152 | 156.92 | 0.10177 | 7 | 0.22222 | 0.13374 | 0.18587 |
| LC | D075 | 222 | GRAPH-HO | PASS | True | False | False | False | 29.583 | 3.4722 | 0 | 8.095 | 32.958 | 0.21372 | 0 | 0.96296 | 0.15531 | 0.18593 | True | False | False | False | 28.583 | 3.3333 | 0.33333 | 21.998 | 57.25 | 0.14871 | 1 | — | — | — | True | False | False | False | 52.333 | 18 | 3 | 22.835 | 79.768 | 0.30057 | 11 | — | — | — | True | False | False | False | 28.333 | 3.3333 | 0.33333 | 27.568 | 49.577 | 0.20443 | 1 | — | — | — | True | False | False | False | 30.833 | 4 | 0.88889 | 17.825 | 69.451 | 0.1832 | 2 | — | — | — | True | False | False | False | 28.889 | 3.3333 | 0.33333 | 13.184 | 51.917 | 0.28307 | 2 | 0.076923 | 0.12859 | 0.1713 | False | False | True | False | — | 26.75 | 21.306 | 76.125 | 156.45 | 0.092175 | 0 | — | — | — | False | False | True | False | — | 10.333 | 5.7778 | 20.152 | 156.92 | 0.10177 | 7 | 0.22222 | 0.13374 | 0.18587 |
| L2 | D075 | 222 | GRAPH-HO | PASS | False | False | True | False | — | 15.833 | 5.5 | 21.922 | 134.79 | 0.045473 | 25 | 0.72222 | 0.15636 | 0.26155 | True | False | False | False | 50.583 | 5.7778 | 1.3333 | 24.257 | 109.41 | 0.035198 | 1 | — | — | — | False | False | False | True | — | 36.222 | 7.3333 | 34.24 | 92.507 | 0.0545 | 14 | — | — | — | False | False | True | False | — | 6.4444 | 3.1111 | 21.416 | 81.863 | 0.062725 | 3 | — | — | — | False | False | False | True | — | 10 | 6.3333 | 25.548 | 126.24 | 0.030813 | 30 | — | — | — | False | False | True | False | — | 11.667 | 7.5556 | 26.648 | 146.11 | 0.025603 | 94 | 0.27869 | 0.14053 | 0.17665 | True | False | False | False | 89.333 | 25.667 | 20.333 | 38.079 | 129.3 | 0.035685 | 4 | — | — | — | False | False | False | True | — | 25.556 | 19.667 | 39.914 | 120.88 | 0.072029 | 19 | 0.5 | 0.15024 | 0.2013 |
| L2 | D075 | 222 | CUT | PASS | False | False | True | False | — | 16.889 | 8.3333 | 42.767 | 142.4 | 0.034181 | 12 | — | — | — | True | False | False | False | 50.583 | 5.7778 | 1.3333 | 24.257 | 109.41 | 0.035198 | 1 | — | — | — | False | False | False | True | — | 36.222 | 7.3333 | 34.24 | 92.507 | 0.0545 | 14 | — | — | — | False | False | True | False | — | 6.4444 | 3.1111 | 21.416 | 81.863 | 0.062725 | 3 | — | — | — | False | False | False | True | — | 10 | 6.3333 | 25.548 | 126.24 | 0.030813 | 30 | — | — | — | False | False | True | False | — | 11.667 | 7.5556 | 26.648 | 146.11 | 0.025603 | 94 | 0.27869 | 0.14053 | 0.17665 | True | False | False | False | 89.333 | 25.667 | 20.333 | 38.079 | 129.3 | 0.035685 | 4 | — | — | — | False | False | False | True | — | 25.556 | 19.667 | 39.914 | 120.88 | 0.072029 | 19 | 0.5 | 0.15024 | 0.2013 |
| H1 | D075 | 222 | GRAPH-HO | PASS | True | False | False | False | 31.833 | 3.4444 | 0 | 10.701 | 27.221 | 0.11381 | 7 | 0.9 | 0.15697 | 0.17995 | True | False | False | False | 29.833 | 4.0556 | 0.94444 | 6.476 | 68.279 | 0.054106 | 10 | — | — | — | True | False | False | False | 47.333 | 14.778 | 2 | 13.694 | 36.231 | 0.1119 | 16 | — | — | — | False | False | True | False | — | 8.2222 | 4.8889 | 11.648 | 60.589 | 0.09787 | 19 | — | — | — | True | False | False | False | 27.833 | 3.3333 | 0.33333 | 10.37 | 58.182 | 0.12932 | 5 | — | — | — | True | False | False | False | 29.889 | 3.4444 | 0.33333 | 9.0934 | 44.125 | 0.14175 | 7 | 0.18519 | 0.131 | 0.19418 | False | False | True | False | — | 8.8611 | 4.75 | 32.863 | 44.817 | 0.1331 | 10 | — | — | — | False | False | True | False | — | 16.556 | 11.778 | 84.395 | 161.53 | 0.1698 | 8 | 0.33333 | 0.13356 | 0.16489 |
| H1 | D075 | 222 | CUT | PASS | True | False | False | False | 32.583 | 4.4444 | 1.2222 | 16.049 | 91.378 | 0.14329 | 5 | — | — | — | True | False | False | False | 29.833 | 4.0556 | 0.94444 | 6.476 | 68.279 | 0.054106 | 10 | — | — | — | True | False | False | False | 47.333 | 14.778 | 2 | 13.694 | 36.231 | 0.1119 | 16 | — | — | — | False | False | True | False | — | 8.2222 | 4.8889 | 11.648 | 60.589 | 0.09787 | 19 | — | — | — | True | False | False | False | 27.833 | 3.3333 | 0.33333 | 10.37 | 58.182 | 0.12932 | 5 | — | — | — | True | False | False | False | 29.889 | 3.4444 | 0.33333 | 9.0934 | 44.125 | 0.14175 | 7 | 0.18519 | 0.131 | 0.19418 | False | False | True | False | — | 8.8611 | 4.75 | 32.863 | 44.817 | 0.1331 | 10 | — | — | — | False | False | True | False | — | 16.556 | 11.778 | 84.395 | 161.53 | 0.1698 | 8 | 0.33333 | 0.13356 | 0.16489 |
| H2 | D075 | 222 | GRAPH-HO | PASS | False | False | False | True | — | 7.4444 | 0.55556 | 14.571 | 50.801 | 0.062137 | 13 | 0.88372 | 0.17809 | 0.28426 | True | False | False | False | 48.583 | 8.9167 | 2.3611 | 20.424 | 84.953 | 0.06442 | 0 | — | — | — | False | False | True | False | — | 23.778 | 4 | 28.594 | 61.635 | 0.047611 | 10 | — | — | — | False | False | True | False | — | 9 | 4.5556 | 28.681 | 75.563 | 0.12505 | 9 | — | — | — | False | False | True | False | — | 5 | 1.7778 | 21.402 | 82.183 | 0.078404 | 1 | — | — | — | False | False | False | True | — | 7.5556 | 3.6667 | 15.068 | 85.316 | 0.039272 | 31 | 0.45455 | 0.13691 | 0.17591 | True | False | False | False | 80.333 | 26.111 | 21 | 46.345 | 135.09 | 0.047933 | 29 | — | — | — | False | False | False | True | — | 25.111 | 19.667 | 25.791 | 140.24 | 0.046929 | 48 | 0.42 | 0.14542 | 0.21968 |
| H2 | D075 | 222 | CUT | PASS | True | False | False | False | 77.083 | 6.8889 | 3.1111 | 22.574 | 122.95 | 0.086436 | 16 | — | — | — | True | False | False | False | 48.583 | 8.9167 | 2.3611 | 20.424 | 84.953 | 0.06442 | 0 | — | — | — | False | False | True | False | — | 23.778 | 4 | 28.594 | 61.635 | 0.047611 | 10 | — | — | — | False | False | True | False | — | 9 | 4.5556 | 28.681 | 75.563 | 0.12505 | 9 | — | — | — | False | False | True | False | — | 5 | 1.7778 | 21.402 | 82.183 | 0.078404 | 1 | — | — | — | False | False | False | True | — | 7.5556 | 3.6667 | 15.068 | 85.316 | 0.039272 | 31 | 0.45455 | 0.13691 | 0.17591 | True | False | False | False | 80.333 | 26.111 | 21 | 46.345 | 135.09 | 0.047933 | 29 | — | — | — | False | False | False | True | — | 25.111 | 19.667 | 25.791 | 140.24 | 0.046929 | 48 | 0.42 | 0.14542 | 0.21968 |
| SLW | D150 | 221 | GRAPH-HO | PASS | False | False | True | False | — | 35.181 | 3 | 17.247 | 109.34 | 0.045911 | 46 | 0.1 | 0.074908 | 0.15193 | True | False | False | False | 50.583 | 8.5556 | 4.4444 | 27.072 | 156.63 | 0.05017 | 15 | — | — | — | False | False | False | True | — | 50.111 | 11 | 55.557 | 172.46 | 0.047617 | 43 | — | — | — | True | False | False | False | 51.833 | 11.222 | 4.6667 | 49.963 | 132.32 | 0.098375 | 10 | — | — | — | False | False | False | True | — | 22.333 | 12.667 | 28.876 | 162.11 | 0.030989 | 50 | — | — | — | False | False | True | False | — | 13.431 | 6.875 | 22.096 | 142.26 | 0.04191 | 27 | 0.15873 | 0.13287 | 0.16934 | False | False | False | True | — | 24.778 | 16.556 | 34.9 | 129.35 | 0.045217 | 58 | — | — | — | True | False | False | False | 66.375 | 19.222 | 14.333 | 40.565 | 162.1 | 0.039648 | 36 | 0.19444 | 0.13748 | 0.21053 |
| SLW | D150 | 221 | CUT | PASS | True | False | False | False | 88.833 | 38.5 | 7 | 28.56 | 127.41 | 0.053623 | 25 | — | — | — | True | False | False | False | 50.583 | 8.5556 | 4.4444 | 27.072 | 156.63 | 0.05017 | 15 | — | — | — | False | False | False | True | — | 50.111 | 11 | 55.557 | 172.46 | 0.047617 | 43 | — | — | — | True | False | False | False | 51.833 | 11.222 | 4.6667 | 49.963 | 132.32 | 0.098375 | 10 | — | — | — | False | False | False | True | — | 22.333 | 12.667 | 28.876 | 162.11 | 0.030989 | 50 | — | — | — | False | False | True | False | — | 13.431 | 6.875 | 22.096 | 142.26 | 0.04191 | 27 | 0.15873 | 0.13287 | 0.16934 | False | False | False | True | — | 24.778 | 16.556 | 34.9 | 129.35 | 0.045217 | 58 | — | — | — | True | False | False | False | 66.375 | 19.222 | 14.333 | 40.565 | 162.1 | 0.039648 | 36 | 0.19444 | 0.13748 | 0.21053 |
| LC | D150 | 221 | GRAPH-HO | PASS | True | False | False | False | 46.833 | 13.944 | 1 | 23.932 | 56.014 | 0.27316 | 0 | 0.04 | 0.07729 | 0.08458 | True | False | False | False | 28.833 | 3.4444 | 0.44444 | 20.716 | 46.903 | 0.14534 | 0 | — | — | — | True | False | False | False | 66.083 | 23.75 | 4 | 62.068 | 154.5 | 0.054849 | 3 | — | — | — | True | False | False | False | 28.833 | 2.8889 | — | 21.956 | 82.525 | 0.30967 | 1 | — | — | — | True | False | False | False | 28.083 | 3.2222 | 0.22222 | 12.181 | 38.388 | 0.28357 | 2 | — | — | — | False | False | True | False | — | 7.2222 | 3.7778 | 26.014 | 97.331 | 0.10416 | 0 | 0.23214 | 0.13025 | 0.16673 | True | False | False | False | 35.083 | 7.5556 | 3.5556 | 26.878 | 69.227 | 0.22891 | 12 | — | — | — | True | False | False | False | 42.097 | 8.5556 | 4.4444 | 8.4623 | 44.082 | 0.15965 | 8 | 0.27273 | 0.14445 | 0.21323 |
| LC | D150 | 221 | CUT | PASS | True | False | False | False | 48.833 | 16.167 | 3 | 28.283 | 65.687 | 0.24264 | 14 | — | — | — | True | False | False | False | 28.833 | 3.4444 | 0.44444 | 20.716 | 46.903 | 0.14534 | 0 | — | — | — | True | False | False | False | 66.083 | 23.75 | 4 | 62.068 | 154.5 | 0.054849 | 3 | — | — | — | True | False | False | False | 28.833 | 2.8889 | — | 21.956 | 82.525 | 0.30967 | 1 | — | — | — | True | False | False | False | 28.083 | 3.2222 | 0.22222 | 12.181 | 38.388 | 0.28357 | 2 | — | — | — | False | False | True | False | — | 7.2222 | 3.7778 | 26.014 | 97.331 | 0.10416 | 0 | 0.23214 | 0.13025 | 0.16673 | True | False | False | False | 35.083 | 7.5556 | 3.5556 | 26.878 | 69.227 | 0.22891 | 12 | — | — | — | True | False | False | False | 42.097 | 8.5556 | 4.4444 | 8.4623 | 44.082 | 0.15965 | 8 | 0.27273 | 0.14445 | 0.21323 |
| L2 | D150 | 221 | GRAPH-HO | PASS | True | False | False | False | 81.889 | 29 | 4 | 35.037 | 87.442 | 0.048477 | 2 | 0.022727 | 0.075051 | 0.090038 | True | False | False | False | 43.583 | 2.8889 | — | 24.239 | 64.453 | 0.077717 | 0 | — | — | — | False | False | False | True | — | 36.667 | 6 | 35.472 | 103.38 | 0.22765 | 3 | — | — | — | False | False | True | False | — | 6.2222 | 1.8889 | 32.586 | 99.142 | 0.081417 | 3 | — | — | — | True | False | False | False | 37.833 | 3.6667 | 0.66667 | 18.736 | 58.543 | 0.053993 | 2 | — | — | — | False | True | False | False | — | 3.6667 | 0.66667 | 12.85 | 45.55 | -1.226e-05 | 21 | 0.11765 | 0.13774 | 0.22433 | False | False | False | True | — | 69 | 5.3333 | 38.129 | 93.338 | 0.031282 | 1 | — | — | — | True | False | False | False | 52.639 | 12.889 | 8.3333 | 18.468 | 58.92 | 0.041616 | 12 | 0.10714 | 0.13462 | 0.173 |
| L2 | D150 | 221 | CUT | PASS | True | False | False | False | 82.083 | 31.194 | 4 | 27.463 | 121.99 | 0.073993 | 10 | — | — | — | True | False | False | False | 43.583 | 2.8889 | — | 24.239 | 64.453 | 0.077717 | 0 | — | — | — | False | False | False | True | — | 36.667 | 6 | 35.472 | 103.38 | 0.22765 | 3 | — | — | — | False | False | True | False | — | 6.2222 | 1.8889 | 32.586 | 99.142 | 0.081417 | 3 | — | — | — | True | False | False | False | 37.833 | 3.6667 | 0.66667 | 18.736 | 58.543 | 0.053993 | 2 | — | — | — | False | True | False | False | — | 3.6667 | 0.66667 | 12.85 | 45.55 | -1.226e-05 | 21 | 0.11765 | 0.13774 | 0.22433 | False | False | False | True | — | 69 | 5.3333 | 38.129 | 93.338 | 0.031282 | 1 | — | — | — | True | False | False | False | 52.639 | 12.889 | 8.3333 | 18.468 | 58.92 | 0.041616 | 12 | 0.10714 | 0.13462 | 0.173 |
| H1 | D150 | 221 | GRAPH-HO | PASS | False | False | True | False | — | 17.167 | 2 | 33.983 | 65.881 | 0.063285 | 19 | 0.10345 | 0.13919 | 0.23496 | True | False | False | False | 33.833 | 6.1111 | — | 14.152 | 62.629 | 0.053273 | 4 | — | — | — | True | False | False | False | 59.333 | 25.111 | 1 | 14.545 | 43.871 | 0.041029 | 9 | — | — | — | False | False | True | False | — | 13.667 | 2.4444 | 26.682 | 100.03 | 0.030769 | 7 | — | — | — | False | False | True | False | — | 3.3333 | 0.33333 | 18.858 | 89.706 | 0.035381 | 10 | — | — | — | True | False | False | False | 31.847 | 3.2222 | 0.22222 | 13.808 | 38.79 | 0.034883 | 0 | 0.13793 | 0.13187 | 0.22308 | True | False | False | False | 59.583 | 21.333 | 16.556 | 46.036 | 105.33 | 0.031883 | 7 | — | — | — | True | False | False | False | 43.861 | 7.4444 | 3.3333 | 27.236 | 123.27 | 0.13076 | 17 | 0.26087 | 0.14714 | 0.18818 |
| H1 | D150 | 221 | CUT | PASS | False | False | True | False | — | 19 | 1 | 34.197 | 87.488 | 0.050785 | 19 | — | — | — | True | False | False | False | 33.833 | 6.1111 | — | 14.152 | 62.629 | 0.053273 | 4 | — | — | — | True | False | False | False | 59.333 | 25.111 | 1 | 14.545 | 43.871 | 0.041029 | 9 | — | — | — | False | False | True | False | — | 13.667 | 2.4444 | 26.682 | 100.03 | 0.030769 | 7 | — | — | — | False | False | True | False | — | 3.3333 | 0.33333 | 18.858 | 89.706 | 0.035381 | 10 | — | — | — | True | False | False | False | 31.847 | 3.2222 | 0.22222 | 13.808 | 38.79 | 0.034883 | 0 | 0.13793 | 0.13187 | 0.22308 | True | False | False | False | 59.583 | 21.333 | 16.556 | 46.036 | 105.33 | 0.031883 | 7 | — | — | — | True | False | False | False | 43.861 | 7.4444 | 3.3333 | 27.236 | 123.27 | 0.13076 | 17 | 0.26087 | 0.14714 | 0.18818 |
| H2 | D150 | 221 | CUT | PASS | False | False | False | True | — | 29.333 | 5 | 23.338 | 71.638 | 0.08119 | 20 | — | — | — | False | False | True | False | — | 11.556 | 6.6667 | 30.531 | 77.649 | 0.062421 | 10 | — | — | — | False | False | False | True | — | 36.111 | 4 | 36.115 | 131.15 | 0.079802 | 14 | — | — | — | False | False | True | False | — | 9.5556 | 3.2222 | 30.064 | 86.19 | 0.20886 | 4 | — | — | — | False | False | False | True | — | 6.6667 | 3.4444 | 29.9 | 98.719 | 0.099346 | 3 | — | — | — | False | False | False | True | — | 6.5556 | 2.7778 | 17.168 | 66.239 | 0.051239 | 9 | 0.22727 | 0.13717 | 0.1921 | False | False | False | True | — | 28.444 | 23 | 56.076 | 120.7 | 0.063406 | 18 | — | — | — | False | False | False | True | — | 41.333 | 36.222 | 47.173 | 165.88 | 0.027397 | 160 | 0.34 | 0.15433 | 0.23505 |
| H2 | D150 | 221 | GRAPH-HO | PASS | False | False | False | True | — | 41.667 | 9 | 40.72 | 100.33 | 0.037792 | 14 | 0.019231 | 0.077153 | 0.17266 | False | False | True | False | — | 11.556 | 6.6667 | 30.531 | 77.649 | 0.062421 | 10 | — | — | — | False | False | False | True | — | 36.111 | 4 | 36.115 | 131.15 | 0.079802 | 14 | — | — | — | False | False | True | False | — | 9.5556 | 3.2222 | 30.064 | 86.19 | 0.20886 | 4 | — | — | — | False | False | False | True | — | 6.6667 | 3.4444 | 29.9 | 98.719 | 0.099346 | 3 | — | — | — | False | False | False | True | — | 6.5556 | 2.7778 | 17.168 | 66.239 | 0.051239 | 9 | 0.22727 | 0.13717 | 0.1921 | False | False | False | True | — | 28.444 | 23 | 56.076 | 120.7 | 0.063406 | 18 | — | — | — | False | False | False | True | — | 41.333 | 36.222 | 47.173 | 165.88 | 0.027397 | 160 | 0.34 | 0.15433 | 0.23505 |
| SLW | D150 | 222 | GRAPH-HO | PASS | True | False | False | False | 83.833 | 33.278 | 3 | 32.009 | 116.42 | 0.1235 | 34 | 0.083333 | 0.074063 | 0.15208 | False | False | False | True | — | 17.778 | 8.8889 | 30.566 | 150.3 | 0.039944 | 38 | — | — | — | False | False | False | True | — | 44.778 | 7 | 39.31 | 131.84 | 0.02721 | 29 | — | — | — | False | False | True | False | — | 10 | 5.5556 | 36.256 | 150.3 | 0.064941 | 23 | — | — | — | False | False | False | True | — | 21.111 | 16.111 | 36.422 | 136.77 | 0.027224 | 56 | — | — | — | False | False | False | True | — | 10.444 | 3.7778 | 19.285 | 105.72 | 0.067271 | 35 | 0.17045 | 0.12733 | 0.17057 | False | False | False | True | — | 24.889 | 17.778 | 76.025 | 150.41 | 0.06365 | 57 | — | — | — | True | False | False | False | 75.361 | 21.25 | 14.333 | 27.409 | 148.85 | 0.036108 | 28 | 0.26829 | 0.13707 | 0.17799 |
| SLW | D150 | 222 | CUT | PASS | False | False | False | True | — | 44.222 | 8.8889 | 42.322 | 146.46 | 0.051013 | 35 | — | — | — | False | False | False | True | — | 17.778 | 8.8889 | 30.566 | 150.3 | 0.039944 | 38 | — | — | — | False | False | False | True | — | 44.778 | 7 | 39.31 | 131.84 | 0.02721 | 29 | — | — | — | False | False | True | False | — | 10 | 5.5556 | 36.256 | 150.3 | 0.064941 | 23 | — | — | — | False | False | False | True | — | 21.111 | 16.111 | 36.422 | 136.77 | 0.027224 | 56 | — | — | — | False | False | False | True | — | 10.444 | 3.7778 | 19.285 | 105.72 | 0.067271 | 35 | 0.17045 | 0.12733 | 0.17057 | False | False | False | True | — | 24.889 | 17.778 | 76.025 | 150.41 | 0.06365 | 57 | — | — | — | True | False | False | False | 75.361 | 21.25 | 14.333 | 27.409 | 148.85 | 0.036108 | 28 | 0.26829 | 0.13707 | 0.17799 |
| LC | D150 | 222 | CUT | PASS | True | False | False | False | 50.833 | 17.833 | 3 | 25.851 | 69.486 | 0.19357 | 5 | — | — | — | True | False | False | False | 28.583 | 3.3333 | 0.33333 | 21.998 | 57.25 | 0.14871 | 1 | — | — | — | True | False | False | False | 52.333 | 18 | 3 | 22.835 | 79.768 | 0.30057 | 11 | — | — | — | True | False | False | False | 28.333 | 3.3333 | 0.33333 | 27.568 | 49.577 | 0.20443 | 1 | — | — | — | True | False | False | False | 30.833 | 4 | 0.88889 | 17.825 | 69.451 | 0.1832 | 2 | — | — | — | True | False | False | False | 28.889 | 3.3333 | 0.33333 | 13.184 | 51.917 | 0.28307 | 2 | 0.076923 | 0.12859 | 0.1713 | False | False | True | False | — | 26.75 | 21.306 | 76.125 | 156.45 | 0.092175 | 0 | — | — | — | False | False | True | False | — | 10.333 | 5.7778 | 20.152 | 156.92 | 0.10177 | 7 | 0.22222 | 0.13374 | 0.18587 |
| LC | D150 | 222 | GRAPH-HO | PASS | True | False | False | False | 43.597 | 14.819 | 3 | 10.487 | 53.866 | 0.1244 | 16 | 0.14815 | 0.075203 | 0.15291 | True | False | False | False | 28.583 | 3.3333 | 0.33333 | 21.998 | 57.25 | 0.14871 | 1 | — | — | — | True | False | False | False | 52.333 | 18 | 3 | 22.835 | 79.768 | 0.30057 | 11 | — | — | — | True | False | False | False | 28.333 | 3.3333 | 0.33333 | 27.568 | 49.577 | 0.20443 | 1 | — | — | — | True | False | False | False | 30.833 | 4 | 0.88889 | 17.825 | 69.451 | 0.1832 | 2 | — | — | — | True | False | False | False | 28.889 | 3.3333 | 0.33333 | 13.184 | 51.917 | 0.28307 | 2 | 0.076923 | 0.12859 | 0.1713 | False | False | True | False | — | 26.75 | 21.306 | 76.125 | 156.45 | 0.092175 | 0 | — | — | — | False | False | True | False | — | 10.333 | 5.7778 | 20.152 | 156.92 | 0.10177 | 7 | 0.22222 | 0.13374 | 0.18587 |
| L2 | D150 | 222 | CUT | PASS | False | False | False | True | — | 35.556 | 4 | 22.723 | 82.041 | 0.05492 | 17 | — | — | — | True | False | False | False | 50.583 | 5.7778 | 1.3333 | 24.257 | 109.41 | 0.035198 | 1 | — | — | — | False | False | False | True | — | 36.222 | 7.3333 | 34.24 | 92.507 | 0.0545 | 14 | — | — | — | False | False | True | False | — | 6.4444 | 3.1111 | 21.416 | 81.863 | 0.062725 | 3 | — | — | — | False | False | False | True | — | 10 | 6.3333 | 25.548 | 126.24 | 0.030813 | 30 | — | — | — | False | False | True | False | — | 11.667 | 7.5556 | 26.648 | 146.11 | 0.025603 | 94 | 0.27869 | 0.14053 | 0.17665 | True | False | False | False | 89.333 | 25.667 | 20.333 | 38.079 | 129.3 | 0.035685 | 4 | — | — | — | False | False | False | True | — | 25.556 | 19.667 | 39.914 | 120.88 | 0.072029 | 19 | 0.5 | 0.15024 | 0.2013 |
| L2 | D150 | 222 | GRAPH-HO | PASS | False | False | False | True | — | 42.444 | 9.3333 | 38.031 | 118.98 | 0.034703 | 51 | 0.020408 | 0.075425 | 0.12654 | True | False | False | False | 50.583 | 5.7778 | 1.3333 | 24.257 | 109.41 | 0.035198 | 1 | — | — | — | False | False | False | True | — | 36.222 | 7.3333 | 34.24 | 92.507 | 0.0545 | 14 | — | — | — | False | False | True | False | — | 6.4444 | 3.1111 | 21.416 | 81.863 | 0.062725 | 3 | — | — | — | False | False | False | True | — | 10 | 6.3333 | 25.548 | 126.24 | 0.030813 | 30 | — | — | — | False | False | True | False | — | 11.667 | 7.5556 | 26.648 | 146.11 | 0.025603 | 94 | 0.27869 | 0.14053 | 0.17665 | True | False | False | False | 89.333 | 25.667 | 20.333 | 38.079 | 129.3 | 0.035685 | 4 | — | — | — | False | False | False | True | — | 25.556 | 19.667 | 39.914 | 120.88 | 0.072029 | 19 | 0.5 | 0.15024 | 0.2013 |
| H1 | D150 | 222 | GRAPH-HO | PASS | True | False | False | False | 47.139 | 14.583 | 1 | 9.0108 | 40.702 | 0.13392 | 14 | 0.17241 | 0.075584 | 0.15647 | True | False | False | False | 29.833 | 4.0556 | 0.94444 | 6.476 | 68.279 | 0.054106 | 10 | — | — | — | True | False | False | False | 47.333 | 14.778 | 2 | 13.694 | 36.231 | 0.1119 | 16 | — | — | — | False | False | True | False | — | 8.2222 | 4.8889 | 11.648 | 60.589 | 0.09787 | 19 | — | — | — | True | False | False | False | 27.833 | 3.3333 | 0.33333 | 10.37 | 58.182 | 0.12932 | 5 | — | — | — | True | False | False | False | 29.889 | 3.4444 | 0.33333 | 9.0934 | 44.125 | 0.14175 | 7 | 0.18519 | 0.131 | 0.19418 | False | False | True | False | — | 8.8611 | 4.75 | 32.863 | 44.817 | 0.1331 | 10 | — | — | — | False | False | True | False | — | 16.556 | 11.778 | 84.395 | 161.53 | 0.1698 | 8 | 0.33333 | 0.13356 | 0.16489 |
| H1 | D150 | 222 | CUT | PASS | True | False | False | False | 52.333 | 16.444 | 2 | 27.436 | 49.077 | 0.22024 | 13 | — | — | — | True | False | False | False | 29.833 | 4.0556 | 0.94444 | 6.476 | 68.279 | 0.054106 | 10 | — | — | — | True | False | False | False | 47.333 | 14.778 | 2 | 13.694 | 36.231 | 0.1119 | 16 | — | — | — | False | False | True | False | — | 8.2222 | 4.8889 | 11.648 | 60.589 | 0.09787 | 19 | — | — | — | True | False | False | False | 27.833 | 3.3333 | 0.33333 | 10.37 | 58.182 | 0.12932 | 5 | — | — | — | True | False | False | False | 29.889 | 3.4444 | 0.33333 | 9.0934 | 44.125 | 0.14175 | 7 | 0.18519 | 0.131 | 0.19418 | False | False | True | False | — | 8.8611 | 4.75 | 32.863 | 44.817 | 0.1331 | 10 | — | — | — | False | False | True | False | — | 16.556 | 11.778 | 84.395 | 161.53 | 0.1698 | 8 | 0.33333 | 0.13356 | 0.16489 |
| H2 | D150 | 222 | CUT | PASS | False | False | False | True | — | 40.556 | 6 | 33.65 | 132.4 | 0.092557 | 5 | — | — | — | True | False | False | False | 48.583 | 8.9167 | 2.3611 | 20.424 | 84.953 | 0.06442 | 0 | — | — | — | False | False | True | False | — | 23.778 | 4 | 28.594 | 61.635 | 0.047611 | 10 | — | — | — | False | False | True | False | — | 9 | 4.5556 | 28.681 | 75.563 | 0.12505 | 9 | — | — | — | False | False | True | False | — | 5 | 1.7778 | 21.402 | 82.183 | 0.078404 | 1 | — | — | — | False | False | False | True | — | 7.5556 | 3.6667 | 15.068 | 85.316 | 0.039272 | 31 | 0.45455 | 0.13691 | 0.17591 | True | False | False | False | 80.333 | 26.111 | 21 | 46.345 | 135.09 | 0.047933 | 29 | — | — | — | False | False | False | True | — | 25.111 | 19.667 | 25.791 | 140.24 | 0.046929 | 48 | 0.42 | 0.14542 | 0.21968 |
| H2 | D150 | 222 | GRAPH-HO | PASS | False | False | False | True | — | 39.333 | 5 | 45.919 | 109.42 | 0.039635 | 12 | 0.020408 | 0.07716 | 0.08483 | True | False | False | False | 48.583 | 8.9167 | 2.3611 | 20.424 | 84.953 | 0.06442 | 0 | — | — | — | False | False | True | False | — | 23.778 | 4 | 28.594 | 61.635 | 0.047611 | 10 | — | — | — | False | False | True | False | — | 9 | 4.5556 | 28.681 | 75.563 | 0.12505 | 9 | — | — | — | False | False | True | False | — | 5 | 1.7778 | 21.402 | 82.183 | 0.078404 | 1 | — | — | — | False | False | False | True | — | 7.5556 | 3.6667 | 15.068 | 85.316 | 0.039272 | 31 | 0.45455 | 0.13691 | 0.17591 | True | False | False | False | 80.333 | 26.111 | 21 | 46.345 | 135.09 | 0.047933 | 29 | — | — | — | False | False | False | True | — | 25.111 | 19.667 | 25.791 | 140.24 | 0.046929 | 48 | 0.42 | 0.14542 | 0.21968 |

| scene | seed | method | state | seconds |
|---|---|---|---|---|
| H1_D075 | 221 | CUT | WAYPOINT_TIMEOUT | 2.8889 |
| H1_D075 | 221 | CUT | NORMAL | 64.556 |
| H1_D075 | 221 | CUT | ALIGN_BRAKE | 4.4444 |
| H1_D075 | 221 | CUT | ALIGN_ROTATE | 7.5556 |
| H1_D075 | 221 | CUT | ENDPOINT | 0.55556 |
| H1_D075 | 221 | CUT | STOP_WAIT | 3.6667 |
| H1_D075 | 221 | CUT | RECOVER_ROTATE | 5.3333 |
| H1_D075 | 221 | CUT | WAIT_FRESH | 1 |
| H1_D075 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 3 |
| H1_D075 | 221 | GRAPH-HO | NORMAL | 32.833 |
| H1_D075 | 221 | GRAPH-HO | ENDPOINT | 1 |
| H1_D075 | 221 | GRAPH-HO | STOP_WAIT | 2 |
| H1_D075 | 221 | GRAPH-HO | RECOVER_ROTATE | 1.7778 |
| H1_D075 | 221 | GRAPH-HO | WAIT_FRESH | 0.22222 |
| H1_D075 | 221 | GRAPH-HO | ALIGN_BRAKE | 0.22222 |
| H1_D075 | 221 | GRAPH-HO | ALIGN_ROTATE | 1.7778 |
| H1_D075 | 222 | CUT | WAYPOINT_TIMEOUT | 2.8889 |
| H1_D075 | 222 | CUT | NORMAL | 26.583 |
| H1_D075 | 222 | CUT | ALIGN_BRAKE | 1.7778 |
| H1_D075 | 222 | CUT | ALIGN_ROTATE | 1.2222 |
| H1_D075 | 222 | CUT | ENDPOINT | 0.11111 |
| H1_D075 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 2.8889 |
| H1_D075 | 222 | GRAPH-HO | NORMAL | 27.611 |
| H1_D075 | 222 | GRAPH-HO | ENDPOINT | 1.3333 |
| H1_D150 | 221 | CUT | WAYPOINT_TIMEOUT | 22.889 |
| H1_D150 | 221 | CUT | NORMAL | 24 |
| H1_D150 | 221 | CUT | ALIGN_ROTATE | 1 |
| H1_D150 | 221 | CUT | STOP_WAIT | 1 |
| H1_D150 | 221 | CUT | RECOVER_ROTATE | 1.7778 |
| H1_D150 | 221 | CUT | WAIT_FRESH | 1.6667 |
| H1_D150 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 22.833 |
| H1_D150 | 221 | GRAPH-HO | NORMAL | 22.889 |
| H1_D150 | 221 | GRAPH-HO | ALIGN_ROTATE | 2 |
| H1_D150 | 221 | GRAPH-HO | ENDPOINT | 0.11111 |
| H1_D150 | 221 | GRAPH-HO | STOP_WAIT | 1 |
| H1_D150 | 222 | CUT | WAYPOINT_TIMEOUT | 24.333 |
| H1_D150 | 222 | CUT | NORMAL | 26 |
| H1_D150 | 222 | CUT | ALIGN_ROTATE | 2 |
| H1_D150 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 22.139 |
| H1_D150 | 222 | GRAPH-HO | NORMAL | 23.667 |
| H1_D150 | 222 | GRAPH-HO | ALIGN_ROTATE | 1 |
| H1_D150 | 222 | GRAPH-HO | ENDPOINT | 0.33333 |
| H2_D075 | 221 | CUT | WAYPOINT_TIMEOUT | 2.8889 |
| H2_D075 | 221 | CUT | NORMAL | 75.028 |
| H2_D075 | 221 | CUT | ENDPOINT | 0.66667 |
| H2_D075 | 221 | CUT | ALIGN_BRAKE | 2.4444 |
| H2_D075 | 221 | CUT | ALIGN_ROTATE | 2.5556 |
| H2_D075 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 2.8889 |
| H2_D075 | 221 | GRAPH-HO | NORMAL | 83.111 |
| H2_D075 | 221 | GRAPH-HO | ENDPOINT | 1.2222 |
| H2_D075 | 221 | GRAPH-HO | ALIGN_BRAKE | 0.88889 |
| H2_D075 | 221 | GRAPH-HO | ALIGN_ROTATE | 1.8889 |
| H2_D075 | 222 | CUT | WAYPOINT_TIMEOUT | 2.8889 |
| H2_D075 | 222 | CUT | NORMAL | 66.972 |
| H2_D075 | 222 | CUT | ALIGN_BRAKE | 2.6667 |
| H2_D075 | 222 | CUT | ALIGN_ROTATE | 3.1111 |
| H2_D075 | 222 | CUT | KEEP_ACTIVE | 1 |
| H2_D075 | 222 | CUT | ENDPOINT | 0.44444 |
| H2_D075 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 3.1111 |
| H2_D075 | 222 | GRAPH-HO | NORMAL | 80.111 |
| H2_D075 | 222 | GRAPH-HO | ENDPOINT | 0.88889 |
| H2_D075 | 222 | GRAPH-HO | ALIGN_BRAKE | 0.55556 |
| H2_D075 | 222 | GRAPH-HO | ALIGN_ROTATE | 0.55556 |
| H2_D075 | 222 | GRAPH-HO | KEEP_ACTIVE | 1 |
| H2_D075 | 222 | GRAPH-HO | STOP_WAIT | 1.7778 |
| H2_D075 | 222 | GRAPH-HO | RECOVER_ROTATE | 1.7778 |
| H2_D075 | 222 | GRAPH-HO | WAIT_FRESH | 0.22222 |
| H2_D150 | 221 | CUT | WAYPOINT_TIMEOUT | 40.222 |
| H2_D150 | 221 | CUT | NORMAL | 43.778 |
| H2_D150 | 221 | CUT | ENDPOINT | 1 |
| H2_D150 | 221 | CUT | ALIGN_ROTATE | 5 |
| H2_D150 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 40.333 |
| H2_D150 | 221 | GRAPH-HO | NORMAL | 37.778 |
| H2_D150 | 221 | GRAPH-HO | ALIGN_ROTATE | 9 |
| H2_D150 | 221 | GRAPH-HO | STOP_WAIT | 2 |
| H2_D150 | 221 | GRAPH-HO | ENDPOINT | 0.88889 |
| H2_D150 | 222 | CUT | WAYPOINT_TIMEOUT | 39.556 |
| H2_D150 | 222 | CUT | NORMAL | 40.667 |
| H2_D150 | 222 | CUT | ALIGN_ROTATE | 6 |
| H2_D150 | 222 | CUT | STOP_WAIT | 2 |
| H2_D150 | 222 | CUT | RECOVER_ROTATE | 1.7778 |
| H2_D150 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 40.111 |
| H2_D150 | 222 | GRAPH-HO | NORMAL | 42.778 |
| H2_D150 | 222 | GRAPH-HO | ENDPOINT | 0.11111 |
| H2_D150 | 222 | GRAPH-HO | ALIGN_ROTATE | 5 |
| H2_D150 | 222 | GRAPH-HO | STOP_WAIT | 2 |
| L2_D075 | 221 | CUT | WAYPOINT_TIMEOUT | 2.8889 |
| L2_D075 | 221 | CUT | NORMAL | 37.25 |
| L2_D075 | 221 | CUT | ENDPOINT | 0.44444 |
| L2_D075 | 221 | CUT | ALIGN_BRAKE | 0.22222 |
| L2_D075 | 221 | CUT | ALIGN_ROTATE | 0.77778 |
| L2_D075 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 3 |
| L2_D075 | 221 | GRAPH-HO | NORMAL | 65.778 |
| L2_D075 | 221 | GRAPH-HO | ENDPOINT | 1.5556 |
| L2_D075 | 221 | GRAPH-HO | KEEP_ACTIVE | 2 |
| L2_D075 | 221 | GRAPH-HO | ALIGN_BRAKE | 0.33333 |
| L2_D075 | 221 | GRAPH-HO | ALIGN_ROTATE | 2.6667 |
| L2_D075 | 221 | GRAPH-HO | STOP_WAIT | 1 |
| L2_D075 | 222 | CUT | WAYPOINT_TIMEOUT | 3.1111 |
| L2_D075 | 222 | CUT | NORMAL | 54.861 |
| L2_D075 | 222 | CUT | ENDPOINT | 0.22222 |
| L2_D075 | 222 | CUT | ALIGN_BRAKE | 2.5556 |
| L2_D075 | 222 | CUT | ALIGN_ROTATE | 8.3333 |
| L2_D075 | 222 | CUT | STOP_WAIT | 2 |
| L2_D075 | 222 | CUT | RECOVER_ROTATE | 1.7778 |
| L2_D075 | 222 | CUT | WAIT_FRESH | 0.22222 |
| L2_D075 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 3 |
| L2_D075 | 222 | GRAPH-HO | NORMAL | 45.556 |
| L2_D075 | 222 | GRAPH-HO | ENDPOINT | 0.33333 |
| L2_D075 | 222 | GRAPH-HO | ALIGN_BRAKE | 0.44444 |
| L2_D075 | 222 | GRAPH-HO | ALIGN_ROTATE | 5.5 |
| L2_D075 | 222 | GRAPH-HO | STOP_WAIT | 3 |
| L2_D075 | 222 | GRAPH-HO | RECOVER_ROTATE | 3.5556 |
| L2_D075 | 222 | GRAPH-HO | WAIT_FRESH | 0.44444 |
| L2_D150 | 221 | CUT | WAYPOINT_TIMEOUT | 36.306 |
| L2_D150 | 221 | CUT | NORMAL | 37.222 |
| L2_D150 | 221 | CUT | ENDPOINT | 0.33333 |
| L2_D150 | 221 | CUT | ALIGN_ROTATE | 4 |
| L2_D150 | 221 | CUT | STOP_WAIT | 2.4444 |
| L2_D150 | 221 | CUT | RECOVER_ROTATE | 1.7778 |
| L2_D150 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 36.889 |
| L2_D150 | 221 | GRAPH-HO | NORMAL | 38.333 |
| L2_D150 | 221 | GRAPH-HO | ENDPOINT | 0.66667 |
| L2_D150 | 221 | GRAPH-HO | ALIGN_ROTATE | 4 |
| L2_D150 | 221 | GRAPH-HO | STOP_WAIT | 2 |
| L2_D150 | 222 | CUT | WAYPOINT_TIMEOUT | 39.333 |
| L2_D150 | 222 | CUT | NORMAL | 41.889 |
| L2_D150 | 222 | CUT | ALIGN_ROTATE | 4 |
| L2_D150 | 222 | CUT | STOP_WAIT | 3 |
| L2_D150 | 222 | CUT | RECOVER_ROTATE | 1.7778 |
| L2_D150 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 38.333 |
| L2_D150 | 222 | GRAPH-HO | NORMAL | 36.667 |
| L2_D150 | 222 | GRAPH-HO | ENDPOINT | 0.11111 |
| L2_D150 | 222 | GRAPH-HO | ALIGN_ROTATE | 9.3333 |
| L2_D150 | 222 | GRAPH-HO | ALIGN_BRAKE | 0.11111 |
| L2_D150 | 222 | GRAPH-HO | STOP_WAIT | 1 |
| L2_D150 | 222 | GRAPH-HO | RECOVER_ROTATE | 1.7778 |
| L2_D150 | 222 | GRAPH-HO | WAIT_FRESH | 1.6667 |
| L2_D150 | 222 | GRAPH-HO | KEEP_ACTIVE | 1 |
| LC_D075 | 221 | CUT | WAYPOINT_TIMEOUT | 2.8889 |
| LC_D075 | 221 | CUT | NORMAL | 25.917 |
| LC_D075 | 221 | CUT | ENDPOINT | 0.77778 |
| LC_D075 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 2.8889 |
| LC_D075 | 221 | GRAPH-HO | NORMAL | 26.514 |
| LC_D075 | 221 | GRAPH-HO | ENDPOINT | 0.44444 |
| LC_D075 | 222 | CUT | WAYPOINT_TIMEOUT | 2.8889 |
| LC_D075 | 222 | CUT | NORMAL | 27.611 |
| LC_D075 | 222 | CUT | ALIGN_BRAKE | 2.2222 |
| LC_D075 | 222 | CUT | ALIGN_ROTATE | 1.7778 |
| LC_D075 | 222 | CUT | ENDPOINT | 0.33333 |
| LC_D075 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 2.8889 |
| LC_D075 | 222 | GRAPH-HO | NORMAL | 25.667 |
| LC_D075 | 222 | GRAPH-HO | ENDPOINT | 1.0278 |
| LC_D150 | 221 | CUT | WAYPOINT_TIMEOUT | 22.833 |
| LC_D150 | 221 | CUT | NORMAL | 23 |
| LC_D150 | 221 | CUT | ALIGN_ROTATE | 3 |
| LC_D150 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 21.944 |
| LC_D150 | 221 | GRAPH-HO | NORMAL | 23.556 |
| LC_D150 | 221 | GRAPH-HO | ENDPOINT | 0.33333 |
| LC_D150 | 221 | GRAPH-HO | ALIGN_ROTATE | 1 |
| LC_D150 | 222 | CUT | WAYPOINT_TIMEOUT | 23.833 |
| LC_D150 | 222 | CUT | NORMAL | 23.889 |
| LC_D150 | 222 | CUT | ALIGN_ROTATE | 3 |
| LC_D150 | 222 | CUT | ENDPOINT | 0.11111 |
| LC_D150 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 20.486 |
| LC_D150 | 222 | GRAPH-HO | NORMAL | 19.667 |
| LC_D150 | 222 | GRAPH-HO | ALIGN_ROTATE | 3 |
| LC_D150 | 222 | GRAPH-HO | ENDPOINT | 0.44444 |
| SLW_D075 | 221 | CUT | WAYPOINT_TIMEOUT | 3 |
| SLW_D075 | 221 | CUT | NORMAL | 17.111 |
| SLW_D075 | 221 | CUT | ENDPOINT | 0.86111 |
| SLW_D075 | 221 | CUT | STOP_WAIT | 13.444 |
| SLW_D075 | 221 | CUT | ALIGN_BRAKE | 1.3333 |
| SLW_D075 | 221 | CUT | ALIGN_ROTATE | 19.222 |
| SLW_D075 | 221 | CUT | RECOVER_ROTATE | 16 |
| SLW_D075 | 221 | CUT | WAIT_FRESH | 2.1111 |
| SLW_D075 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 2.8889 |
| SLW_D075 | 221 | GRAPH-HO | NORMAL | 36.167 |
| SLW_D075 | 221 | GRAPH-HO | ENDPOINT | 0.77778 |
| SLW_D075 | 221 | GRAPH-HO | STOP_WAIT | 1 |
| SLW_D075 | 221 | GRAPH-HO | ALIGN_BRAKE | 1.1111 |
| SLW_D075 | 221 | GRAPH-HO | ALIGN_ROTATE | 1.8889 |
| SLW_D075 | 222 | CUT | WAYPOINT_TIMEOUT | 2.8889 |
| SLW_D075 | 222 | CUT | NORMAL | 33.833 |
| SLW_D075 | 222 | CUT | ENDPOINT | 0.11111 |
| SLW_D075 | 222 | CUT | ALIGN_BRAKE | 1.5556 |
| SLW_D075 | 222 | CUT | ALIGN_ROTATE | 2.4444 |
| SLW_D075 | 222 | CUT | STOP_WAIT | 2 |
| SLW_D075 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 3 |
| SLW_D075 | 222 | GRAPH-HO | NORMAL | 42 |
| SLW_D075 | 222 | GRAPH-HO | ENDPOINT | 1.6667 |
| SLW_D075 | 222 | GRAPH-HO | ALIGN_BRAKE | 0.88889 |
| SLW_D075 | 222 | GRAPH-HO | ALIGN_ROTATE | 4.8889 |
| SLW_D075 | 222 | GRAPH-HO | STOP_WAIT | 1.8889 |
| SLW_D150 | 221 | CUT | WAYPOINT_TIMEOUT | 39.944 |
| SLW_D150 | 221 | CUT | NORMAL | 39.889 |
| SLW_D150 | 221 | CUT | ALIGN_ROTATE | 7 |
| SLW_D150 | 221 | CUT | STOP_WAIT | 2 |
| SLW_D150 | 221 | GRAPH-HO | WAYPOINT_TIMEOUT | 37.514 |
| SLW_D150 | 221 | GRAPH-HO | NORMAL | 38.667 |
| SLW_D150 | 221 | GRAPH-HO | ENDPOINT | 0.33333 |
| SLW_D150 | 221 | GRAPH-HO | STOP_WAIT | 4.1111 |
| SLW_D150 | 221 | GRAPH-HO | RECOVER_ROTATE | 1.7778 |
| SLW_D150 | 221 | GRAPH-HO | ALIGN_ROTATE | 3 |
| SLW_D150 | 222 | CUT | WAYPOINT_TIMEOUT | 40.111 |
| SLW_D150 | 222 | CUT | NORMAL | 38.333 |
| SLW_D150 | 222 | CUT | ALIGN_ROTATE | 8.8889 |
| SLW_D150 | 222 | CUT | STOP_WAIT | 1.4444 |
| SLW_D150 | 222 | CUT | KEEP_ACTIVE | 1 |
| SLW_D150 | 222 | CUT | ENDPOINT | 0.22222 |
| SLW_D150 | 222 | GRAPH-HO | WAYPOINT_TIMEOUT | 36.944 |
| SLW_D150 | 222 | GRAPH-HO | NORMAL | 40.889 |
| SLW_D150 | 222 | GRAPH-HO | ENDPOINT | 0.22222 |
| SLW_D150 | 222 | GRAPH-HO | ALIGN_ROTATE | 3 |
| SLW_D150 | 222 | GRAPH-HO | STOP_WAIT | 1 |
| SLW_D150 | 222 | GRAPH-HO | RECOVER_ROTATE | 1.7778 |
