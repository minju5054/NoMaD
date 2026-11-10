| status | completed | planned | protocol_sha256 | audit_revision_sha256 |
|---|---|---|---|---|
| PARTIAL | 7 | 40 | 57838e8042c9d156c728313a61432c2e3eccb000530f20ef654b2045978a57c4 | fe15bfafb4bf96a5b7f997652b1e05a4d99e448decce1cd1779496030079fb09 |

| item | value |
|---|---|
| outcomes | Phase47 official stop;success=declared arrival distance<=0.5m and no collision,wrong stop>0.5m;90s limit unchanged |
| speed | Success/timeout,arrival time(success pairs only),distance/duration mean speed,actual72Hz stop duration,command-state interval totals |
| passage | Frozen box passage and spawn-to-passage duration;H2 all-box status and per-box spawn observations. Oracle remains evaluation-only |
| spawn_path | Installation before spawn tick,with active follower command state;original chunk observation time compared to spawn,missing/cleared path=>NA |
| tracking | 72Hz position cross-track to installed polyline only while NORMAL/KEEP/ALIGN/REPAIR/ENDPOINT follower states. p50/p95,count;recovery/no path excluded |
| heading | At each replacement pose:old/new projected suffix direction over next0.05m,wrapped absolute difference;p50/p95. Not physical heading jump |
| raw_distance | Mean72Hz position distance to the original selected NoMaD candidate of the currently installed path;EC alternative sample identity retained;missing/degenerate samples reported via count |
| graph | Actual applied/FRESH-dispatched rate,pool whole8-solve p50/p95,late/discard/replacement counts,prediction position+heading errors;all terminal/late results retained |
| hold | Explicit HOLD_REJECTED START/END,including recovery-independent original path continuation;total and longest episode until replacement/EC fail/endpoint |
| historical | Adjacent same scene/seed Phase47 D075,Phase51 L150 and Phase51 WIDE. Separate execution dates;WIDE different geometry,not pooled/matched causal evidence |
| wide_analysis | docs/PHASE51P_WIDE_ANALYSIS.md:214 inference-box events,1712 candidates,3 byte-identical saved RGB images;no new inference/render |
| execution | 40 serial runs,one technical retry,storagev2/cache cleanup,disk30GB stop;preparation only,no simulation or smoke |
| startup audit correction | Only pre-first-chunk missing WAYPOINT_TIMEOUT is allowed; any new_timeout or WAYPOINT_TIMEOUT after first chunk remains a technical failure. initial_wait_s ends at first control with chunk; latch time also recorded. Original frozen protocol unchanged. |

| group | condition | method | scene | n | valid | success | timeout | collision | wrong_stop | box_passage | box_passage_from_spawn_median_s | goal_time_s_median | mean_speed_m_s_median | stopped_s_median | initial_wait_s_median | minimum_clearance_m_median | tracking_error_p50_m_median | tracking_error_p95_m_median | chunk_heading_jump_p50_deg_median | chunk_heading_jump_p95_deg_median | raw_candidate_distance_mean_m_median | stop_distance_m_median | ec_rejects_median | graph_solve_p50_s_median | graph_solve_p95_s_median | graph_acceptance_rate_median | hold_after_rejection_s_median |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase52 | D075 | CUT-HOLD | SLW | 1 | 1 | 0 | 1 | 0 | 0 | 0 | — | — | 0.10578 | 22.333 | 2.8889 | 0.030989 | 0.019714 | 0.16264 | 28.876 | 162.11 | 0.040791 | — | 50 | — | — | — | 6.2222 |
| Phase52 | D075 | CUT-HOLD | LC | 1 | 1 | 1 | 0 | 0 | 0 | 0 | — | 28.083 | 0.20397 | 3.2222 | 2.8889 | 0.28357 | 0.023635 | 0.13503 | 12.181 | 38.388 | 0.03846 | 0.24481 | 2 | — | — | — | 0 |
| Phase52 | D075 | CUT-HOLD | L2 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 10.528 | 37.833 | 0.21561 | 3.6667 | 2.8889 | 0.053993 | 0.029185 | 0.1461 | 18.736 | 58.543 | 0.045977 | 0.38029 | 2 | — | — | — | 1 |
| Phase52 | D075 | CUT-HOLD | ALL | 3 | 3 | 2 | 1 | 0 | 0 | 1 | 10.528 | 32.958 | 0.20397 | 3.6667 | 2.8889 | 0.053993 | 0.023635 | 0.1461 | 18.736 | 58.543 | 0.040791 | 0.31255 | 2 | — | — | — | 1 |
| Phase52 | D075 | GRAPH-REC | SLW | 1 | 1 | 0 | 0 | 0 | 1 | 0 | — | — | 0.10876 | 13.431 | 2.8889 | 0.04191 | 0.019973 | 0.15108 | 22.096 | 142.26 | 0.036784 | 3.0104 | 27 | 0.13287 | 0.16934 | 0.15873 | 0 |
| Phase52 | D075 | GRAPH-REC | LC | 1 | 1 | 0 | 0 | 0 | 1 | 0 | — | — | 0.14097 | 7.2222 | 2.8889 | 0.10416 | 0.024265 | 0.12447 | 26.014 | 97.331 | 0.038711 | 4.4835 | 0 | 0.13025 | 0.16673 | 0.23214 | 0 |
| Phase52 | D075 | GRAPH-REC | L2 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | — | — | 0.16904 | 3.6667 | 2.8889 | -1.226e-05 | 0.022513 | 0.15999 | 12.85 | 45.55 | 0.051152 | — | 21 | 0.13774 | 0.22433 | 0.11765 | 0.77778 |
| Phase52 | D075 | GRAPH-REC | H1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 10.194 | 31.847 | 0.18754 | 3.2222 | 2.8889 | 0.034883 | 0.037195 | 0.18736 | 13.808 | 38.79 | 0.058665 | 0.35346 | 0 | 0.13187 | 0.22308 | 0.13793 | 1.8889 |
| Phase52 | D075 | GRAPH-REC | ALL | 4 | 4 | 1 | 0 | 1 | 2 | 1 | 10.194 | 31.847 | 0.15501 | 5.4444 | 2.8889 | 0.038397 | 0.023389 | 0.15553 | 17.952 | 71.441 | 0.044932 | 3.0104 | 10.5 | 0.13237 | 0.19621 | 0.14833 | 0.38889 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | SLW | 2 | 2 | 1 | 1 | 0 | 0 | 0 | — | 50.583 | 0.12406 | 13.167 | — | 0.045057 | 0.02635 | 0.17469 | 28.819 | 153.46 | 0.046282 | 0.34858 | 26.5 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | LC | 2 | 2 | 2 | 0 | 0 | 0 | 0 | — | 28.708 | 0.18506 | 3.3889 | — | 0.14702 | 0.026797 | 0.12975 | 21.357 | 52.077 | 0.041332 | 0.36225 | 0.5 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | L2 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 16.035 | 47.083 | 0.18314 | 4.3333 | — | 0.056457 | 0.031096 | 0.15838 | 24.248 | 86.933 | 0.048871 | 0.31648 | 0.5 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | H1 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 9.1806 | 31.833 | 0.17534 | 5.0833 | — | 0.053689 | 0.029991 | 0.11905 | 10.314 | 65.454 | 0.041937 | 0.31157 | 7 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | H2 | 2 | 2 | 1 | 0 | 0 | 1 | 2 | 47.667 | 48.583 | 0.15778 | 10.236 | — | 0.063421 | 0.029149 | 0.15776 | 25.478 | 81.301 | 0.04567 | 0.52564 | 5 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | ALL | 10 | 10 | 8 | 1 | 0 | 1 | 6 | 16.035 | 38.708 | 0.17093 | 5.9444 | — | 0.058264 | 0.030183 | 0.14784 | 23.119 | 72.964 | 0.044552 | 0.34858 | 2.5 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | SLW | 2 | 2 | 0 | 2 | 0 | 0 | 0 | — | — | 0.059992 | 47.444 | — | 0.037413 | 0.021071 | 0.22232 | 47.434 | 152.15 | 0.046355 | — | 36 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | LC | 2 | 2 | 2 | 0 | 0 | 0 | 0 | — | 59.208 | 0.099545 | 20.875 | — | 0.17771 | 0.033927 | 0.14481 | 42.451 | 117.14 | 0.047944 | 0.28855 | 7 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | L2 | 2 | 2 | 0 | 2 | 0 | 0 | 0 | — | — | 0.075039 | 36.444 | — | 0.14107 | 0.029905 | 0.1752 | 34.856 | 97.943 | 0.047486 | — | 8.5 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | H1 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 18.097 | 53.333 | 0.10496 | 19.944 | — | 0.076465 | 0.034308 | 0.13406 | 14.12 | 40.051 | 0.045748 | 0.33354 | 12.5 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | H2 | 2 | 2 | 0 | 1 | 0 | 1 | 1 | 41.361 | — | 0.09009 | 29.944 | — | 0.063706 | 0.0293 | 0.13348 | 32.354 | 96.392 | 0.041696 | 0.59719 | 12 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | ALL | 10 | 10 | 4 | 5 | 0 | 1 | 3 | 24.194 | 55.833 | 0.085683 | 30.611 | — | 0.054674 | 0.028827 | 0.14608 | 34.856 | 97.943 | 0.045336 | 0.31243 | 12.5 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | SLW | 2 | 2 | 1 | 0 | 0 | 1 | 0 | — | 51.833 | 0.11608 | 10.611 | — | 0.081658 | 0.022003 | 0.15455 | 43.11 | 141.31 | 0.041368 | 0.46975 | 16.5 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | LC | 2 | 2 | 2 | 0 | 0 | 0 | 0 | — | 28.583 | 0.1902 | 3.1111 | — | 0.25705 | 0.031635 | 0.12234 | 24.762 | 66.051 | 0.042025 | 0.34421 | 1 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | L2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | — | 0.11818 | 6.3333 | — | 0.072071 | 0.023566 | 0.11706 | 27.001 | 90.502 | 0.037063 | 6.9442 | 3 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | H1 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | — | 0.14098 | 10.944 | — | 0.06432 | 0.026739 | 0.11478 | 19.165 | 80.311 | 0.038499 | 2.9829 | 13 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | H2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | — | 0.12584 | 9.2778 | — | 0.16696 | 0.025948 | 0.15639 | 29.372 | 80.876 | 0.043185 | 7.209 | 6.5 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | ALL | 10 | 10 | 3 | 0 | 0 | 7 | 0 | — | 28.833 | 0.12695 | 8.6111 | — | 0.098123 | 0.024432 | 0.13351 | 28.125 | 84.357 | 0.040713 | 2.9829 | 5.5 | — | — | — | 0 |

| condition | scene | seed | method | status | success | collision | timeout_without_declaration | wrong_stop | box_passage | box_passage_from_spawn_s | goal_time_s | mean_speed_m_s | stopped_s | initial_wait_s | minimum_clearance_m | tracking_error_p50_m | tracking_error_p95_m | chunk_heading_jump_p50_deg | chunk_heading_jump_p95_deg | raw_candidate_distance_mean_m | stop_distance_m | ec_rejects | graph_solve_p50_s | graph_solve_p95_s | graph_acceptance_rate | hold_after_rejection_s | Phase47_D075_success | Phase47_D075_collision | Phase47_D075_goal_time_s | Phase47_D075_stopped_s | Phase47_D075_tracking_error_p95_m | Phase47_D075_box_passage | Phase47_D075_box_passage_from_spawn_s | Phase47_D075_wrong_stop | Phase51_L150_success | Phase51_L150_collision | Phase51_L150_goal_time_s | Phase51_L150_stopped_s | Phase51_L150_tracking_error_p95_m | Phase51_L150_box_passage | Phase51_L150_box_passage_from_spawn_s | Phase51_L150_wrong_stop | Phase51_WIDE_success | Phase51_WIDE_collision | Phase51_WIDE_goal_time_s | Phase51_WIDE_stopped_s | Phase51_WIDE_tracking_error_p95_m | Phase51_WIDE_box_passage | Phase51_WIDE_box_passage_from_spawn_s | Phase51_WIDE_wrong_stop |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D075 | SLW | 221 | CUT-HOLD | PASS | False | False | True | False | False | — | — | 0.10578 | 22.333 | 2.8889 | 0.030989 | 0.019714 | 0.16264 | 28.876 | 162.11 | 0.040791 | — | 50 | — | — | — | 6.2222 | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D075 | SLW | 221 | GRAPH-REC | PASS | False | False | False | True | False | — | — | 0.10876 | 13.431 | 2.8889 | 0.04191 | 0.019973 | 0.15108 | 22.096 | 142.26 | 0.036784 | 3.0104 | 27 | 0.13287 | 0.16934 | 0.15873 | 0 | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D075 | LC | 221 | GRAPH-REC | PASS | False | False | False | True | False | — | — | 0.14097 | 7.2222 | 2.8889 | 0.10416 | 0.024265 | 0.12447 | 26.014 | 97.331 | 0.038711 | 4.4835 | 0 | 0.13025 | 0.16673 | 0.23214 | 0 | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D075 | LC | 221 | CUT-HOLD | PASS | True | False | False | False | False | — | 28.083 | 0.20397 | 3.2222 | 2.8889 | 0.28357 | 0.023635 | 0.13503 | 12.181 | 38.388 | 0.03846 | 0.24481 | 2 | — | — | — | 0 | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D075 | L2 | 221 | CUT-HOLD | PASS | True | False | False | False | True | 10.528 | 37.833 | 0.21561 | 3.6667 | 2.8889 | 0.053993 | 0.029185 | 0.1461 | 18.736 | 58.543 | 0.045977 | 0.38029 | 2 | — | — | — | 1 | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D075 | L2 | 221 | GRAPH-REC | PASS | False | True | False | False | False | — | — | 0.16904 | 3.6667 | 2.8889 | -1.226e-05 | 0.022513 | 0.15999 | 12.85 | 45.55 | 0.051152 | — | 21 | 0.13774 | 0.22433 | 0.11765 | 0.77778 | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D075 | H1 | 221 | GRAPH-REC | PASS | True | False | False | False | True | 10.194 | 31.847 | 0.18754 | 3.2222 | 2.8889 | 0.034883 | 0.037195 | 0.18736 | 13.808 | 38.79 | 0.058665 | 0.35346 | 0 | 0.13187 | 0.22308 | 0.13793 | 1.8889 | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D075 | H1 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D075 | H2 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D075 | H2 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D075 | SLW | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D075 | SLW | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D075 | LC | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D075 | LC | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D075 | L2 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D075 | L2 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D075 | H1 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D075 | H1 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D075 | H2 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |
| D075 | H2 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |
| D150 | SLW | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D150 | SLW | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D150 | LC | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D150 | LC | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D150 | L2 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D150 | L2 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D150 | H1 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D150 | H1 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D150 | H2 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D150 | H2 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D150 | SLW | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D150 | SLW | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D150 | LC | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D150 | LC | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D150 | L2 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D150 | L2 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D150 | H1 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D150 | H1 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D150 | H2 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |
| D150 | H2 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |

| scene | seed | method | initial_wait_s | first_chunk_received_s | first_chunk_control_s | startup_missing_timeout_rows | new_timeout_count | post_chunk_waypoint_timeout_rows | selected_attempt |
|---|---|---|---|---|---|---|---|---|---|
| H1_D075 | 221 | GRAPH-REC | 2.8889 | 2.8611 | 2.8889 | 26 | 0 | 0 | 1 |
| L2_D075 | 221 | CUT-HOLD | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | 1 |
| L2_D075 | 221 | GRAPH-REC | 2.8889 | 2.8472 | 2.8889 | 26 | 0 | 0 | 1 |
| LC_D075 | 221 | CUT-HOLD | 2.8889 | 2.8472 | 2.8889 | 26 | 0 | 0 | 1 |
| LC_D075 | 221 | GRAPH-REC | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | 1 |
| SLW_D075 | 221 | CUT-HOLD | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | 1 |
| SLW_D075 | 221 | GRAPH-REC | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | 1 |

| group | condition | scene | seed | method | state | seconds |
|---|---|---|---|---|---|---|
| Phase52 | D075 | H1 | 221 | GRAPH-REC | NORMAL | 26.069 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | ALIGN_BRAKE | 0.66667 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | ALIGN_ROTATE | 0.22222 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | KEEP_ACTIVE | 1.8889 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | ENDPOINT | 0.11111 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | NORMAL | 32.278 |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | ENDPOINT | 0.66667 |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | ALIGN_BRAKE | 0.33333 |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | ALIGN_ROTATE | 0.66667 |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | KEEP_ACTIVE | 1 |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | NORMAL | 13.778 |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | ENDPOINT | 0.44444 |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | ALIGN_BRAKE | 0.33333 |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | ALIGN_ROTATE | 0.66667 |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | KEEP_ACTIVE | 0.77778 |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | STOP_WAIT | 0.13889 |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | NORMAL | 23.75 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | ENDPOINT | 0.55556 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | ALIGN_BRAKE | 0.66667 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | ALIGN_ROTATE | 0.22222 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | NORMAL | 50.292 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | ALIGN_BRAKE | 1.8889 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | ALIGN_ROTATE | 3.7778 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | SLW | 221 | CUT-HOLD | NORMAL | 60.889 |
| Phase52 | D075 | SLW | 221 | CUT-HOLD | ENDPOINT | 5.3333 |
| Phase52 | D075 | SLW | 221 | CUT-HOLD | KEEP_ACTIVE | 5.1111 |
| Phase52 | D075 | SLW | 221 | CUT-HOLD | ALIGN_BRAKE | 2.6667 |
| Phase52 | D075 | SLW | 221 | CUT-HOLD | ALIGN_ROTATE | 12.667 |
| Phase52 | D075 | SLW | 221 | CUT-HOLD | STOP_WAIT | 0.44444 |
| Phase52 | D075 | SLW | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | NORMAL | 50 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | ENDPOINT | 0.33333 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | STOP_WAIT | 0.55556 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | RECOVER_ROTATE | 1.7778 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | WAIT_FRESH | 0.77778 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | ALIGN_BRAKE | 2.6667 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | ALIGN_ROTATE | 6.875 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase47_D075 | D075 | H1 | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 2.8889 |
| Phase47_D075 | D075 | H1 | 221 | OURS-DETOUR+HMM | NORMAL | 27.389 |
| Phase47_D075 | D075 | H1 | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.11111 |
| Phase47_D075 | D075 | H1 | 221 | OURS-DETOUR+HMM | STOP_WAIT | 1.4444 |
| Phase47_D075 | D075 | H1 | 221 | OURS-DETOUR+HMM | RECOVER_ROTATE | 1.7778 |
| Phase47_D075 | D075 | H1 | 221 | OURS-DETOUR+HMM | WAIT_FRESH | 0.22222 |
| Phase47_D075 | D075 | H1 | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 2.8889 |
| Phase47_D075 | D075 | H1 | 222 | OURS-DETOUR+HMM | NORMAL | 24.889 |
| Phase47_D075 | D075 | H1 | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 1 |
| Phase47_D075 | D075 | H1 | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 0.94444 |
| Phase47_D075 | D075 | H1 | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.11111 |
| Phase47_D075 | D075 | H2 | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3 |
| Phase47_D075 | D075 | H2 | 221 | OURS-DETOUR+HMM | NORMAL | 66.889 |
| Phase47_D075 | D075 | H2 | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.44444 |
| Phase47_D075 | D075 | H2 | 221 | OURS-DETOUR+HMM | ALIGN_BRAKE | 5.3333 |
| Phase47_D075 | D075 | H2 | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 6.6667 |
| Phase47_D075 | D075 | H2 | 221 | OURS-DETOUR+HMM | STOP_WAIT | 1 |
| Phase47_D075 | D075 | H2 | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3.1111 |
| Phase47_D075 | D075 | H2 | 222 | OURS-DETOUR+HMM | NORMAL | 37.333 |
| Phase47_D075 | D075 | H2 | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.44444 |
| Phase47_D075 | D075 | H2 | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 2.5556 |
| Phase47_D075 | D075 | H2 | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 2.3611 |
| Phase47_D075 | D075 | H2 | 222 | OURS-DETOUR+HMM | STOP_WAIT | 1 |
| Phase47_D075 | D075 | H2 | 222 | OURS-DETOUR+HMM | RECOVER_ROTATE | 1.7778 |
| Phase47_D075 | D075 | L2 | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3 |
| Phase47_D075 | D075 | L2 | 221 | OURS-DETOUR+HMM | NORMAL | 39.139 |
| Phase47_D075 | D075 | L2 | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.66667 |
| Phase47_D075 | D075 | L2 | 221 | OURS-DETOUR+HMM | KEEP_ACTIVE | 0.77778 |
| Phase47_D075 | D075 | L2 | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3 |
| Phase47_D075 | D075 | L2 | 222 | OURS-DETOUR+HMM | NORMAL | 42.25 |
| Phase47_D075 | D075 | L2 | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.44444 |
| Phase47_D075 | D075 | L2 | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 1.6667 |
| Phase47_D075 | D075 | L2 | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 1.3333 |
| Phase47_D075 | D075 | L2 | 222 | OURS-DETOUR+HMM | STOP_WAIT | 1.8889 |
| Phase47_D075 | D075 | LC | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 2.8889 |
| Phase47_D075 | D075 | LC | 221 | OURS-DETOUR+HMM | NORMAL | 24.833 |
| Phase47_D075 | D075 | LC | 221 | OURS-DETOUR+HMM | ALIGN_BRAKE | 0.55556 |
| Phase47_D075 | D075 | LC | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 0.44444 |
| Phase47_D075 | D075 | LC | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.11111 |
| Phase47_D075 | D075 | LC | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 2.8889 |
| Phase47_D075 | D075 | LC | 222 | OURS-DETOUR+HMM | NORMAL | 24.472 |
| Phase47_D075 | D075 | LC | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 0.66667 |
| Phase47_D075 | D075 | LC | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 0.33333 |
| Phase47_D075 | D075 | LC | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.22222 |
| Phase47_D075 | D075 | SLW | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 2.8889 |
| Phase47_D075 | D075 | SLW | 221 | OURS-DETOUR+HMM | NORMAL | 39.139 |
| Phase47_D075 | D075 | SLW | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.55556 |
| Phase47_D075 | D075 | SLW | 221 | OURS-DETOUR+HMM | STOP_WAIT | 1 |
| Phase47_D075 | D075 | SLW | 221 | OURS-DETOUR+HMM | ALIGN_BRAKE | 2.5556 |
| Phase47_D075 | D075 | SLW | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 4.4444 |
| Phase47_D075 | D075 | SLW | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3.4444 |
| Phase47_D075 | D075 | SLW | 222 | OURS-DETOUR+HMM | NORMAL | 68.778 |
| Phase47_D075 | D075 | SLW | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.66667 |
| Phase47_D075 | D075 | SLW | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 2.8889 |
| Phase47_D075 | D075 | SLW | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 8.8889 |
| Phase47_D075 | D075 | SLW | 222 | OURS-DETOUR+HMM | STOP_WAIT | 2.3333 |
| Phase47_D075 | D075 | SLW | 222 | OURS-DETOUR+HMM | RECOVER_ROTATE | 1.7778 |
| Phase47_D075 | D075 | SLW | 222 | OURS-DETOUR+HMM | WAIT_FRESH | 0.22222 |
| Phase47_D075 | D075 | SLW | 222 | OURS-DETOUR+HMM | KEEP_ACTIVE | 1 |
| Phase51_L150 | L150 | H1 | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 25.889 |
| Phase51_L150 | L150 | H1 | 221 | OURS-DETOUR+HMM | NORMAL | 24.889 |
| Phase51_L150 | L150 | H1 | 221 | OURS-DETOUR+HMM | ENDPOINT | 1.1111 |
| Phase51_L150 | L150 | H1 | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 1 |
| Phase51_L150 | L150 | H1 | 221 | OURS-DETOUR+HMM | STOP_WAIT | 3 |
| Phase51_L150 | L150 | H1 | 221 | OURS-DETOUR+HMM | RECOVER_ROTATE | 1.7778 |
| Phase51_L150 | L150 | H1 | 221 | OURS-DETOUR+HMM | WAIT_FRESH | 1.6667 |
| Phase51_L150 | L150 | H1 | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 22.333 |
| Phase51_L150 | L150 | H1 | 222 | OURS-DETOUR+HMM | NORMAL | 22.889 |
| Phase51_L150 | L150 | H1 | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 2 |
| Phase51_L150 | L150 | H1 | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.11111 |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 2.8889 |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | NORMAL | 36.389 |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.44444 |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | ALIGN_BRAKE | 1.5556 |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 2.4444 |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | STOP_WAIT | 3.8889 |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | RECOVER_ROTATE | 3.5556 |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | WAIT_FRESH | 0.55556 |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | KEEP_ACTIVE | 1.1111 |
| Phase51_WIDE | WIDE | H1 | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3 |
| Phase51_WIDE | WIDE | H1 | 222 | OURS-DETOUR+HMM | NORMAL | 33.25 |
| Phase51_WIDE | WIDE | H1 | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 1 |
| Phase51_WIDE | WIDE | H1 | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 4.8889 |
| Phase51_WIDE | WIDE | H1 | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.44444 |
| Phase51_L150 | L150 | H2 | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 40 |
| Phase51_L150 | L150 | H2 | 221 | OURS-DETOUR+HMM | NORMAL | 44.667 |
| Phase51_L150 | L150 | H2 | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.33333 |
| Phase51_L150 | L150 | H2 | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 4 |
| Phase51_L150 | L150 | H2 | 221 | OURS-DETOUR+HMM | STOP_WAIT | 1 |
| Phase51_L150 | L150 | H2 | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 33.333 |
| Phase51_L150 | L150 | H2 | 222 | OURS-DETOUR+HMM | NORMAL | 35 |
| Phase51_L150 | L150 | H2 | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 4 |
| Phase51_L150 | L150 | H2 | 222 | OURS-DETOUR+HMM | KEEP_ACTIVE | 1 |
| Phase51_WIDE | WIDE | H2 | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3 |
| Phase51_WIDE | WIDE | H2 | 221 | OURS-DETOUR+HMM | NORMAL | 53.139 |
| Phase51_WIDE | WIDE | H2 | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.44444 |
| Phase51_WIDE | WIDE | H2 | 221 | OURS-DETOUR+HMM | ALIGN_BRAKE | 2.7778 |
| Phase51_WIDE | WIDE | H2 | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 3.2222 |
| Phase51_WIDE | WIDE | H2 | 221 | OURS-DETOUR+HMM | STOP_WAIT | 1 |
| Phase51_WIDE | WIDE | H2 | 221 | OURS-DETOUR+HMM | RECOVER_ROTATE | 1.7778 |
| Phase51_WIDE | WIDE | H2 | 221 | OURS-DETOUR+HMM | WAIT_FRESH | 0.22222 |
| Phase51_WIDE | WIDE | H2 | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3.2222 |
| Phase51_WIDE | WIDE | H2 | 222 | OURS-DETOUR+HMM | NORMAL | 71.056 |
| Phase51_WIDE | WIDE | H2 | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.55556 |
| Phase51_WIDE | WIDE | H2 | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 3.4444 |
| Phase51_WIDE | WIDE | H2 | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 4.5556 |
| Phase51_WIDE | WIDE | H2 | 222 | OURS-DETOUR+HMM | STOP_WAIT | 1 |
| Phase51_WIDE | WIDE | H2 | 222 | OURS-DETOUR+HMM | KEEP_ACTIVE | 1 |
| Phase51_L150 | L150 | L2 | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 40 |
| Phase51_L150 | L150 | L2 | 221 | OURS-DETOUR+HMM | NORMAL | 42.667 |
| Phase51_L150 | L150 | L2 | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.33333 |
| Phase51_L150 | L150 | L2 | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 6 |
| Phase51_L150 | L150 | L2 | 221 | OURS-DETOUR+HMM | KEEP_ACTIVE | 1 |
| Phase51_L150 | L150 | L2 | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 39.889 |
| Phase51_L150 | L150 | L2 | 222 | OURS-DETOUR+HMM | NORMAL | 42.444 |
| Phase51_L150 | L150 | L2 | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.22222 |
| Phase51_L150 | L150 | L2 | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 7.3333 |
| Phase51_L150 | L150 | L2 | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 0.11111 |
| Phase51_WIDE | WIDE | L2 | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3 |
| Phase51_WIDE | WIDE | L2 | 221 | OURS-DETOUR+HMM | NORMAL | 71.361 |
| Phase51_WIDE | WIDE | L2 | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.22222 |
| Phase51_WIDE | WIDE | L2 | 221 | OURS-DETOUR+HMM | ALIGN_BRAKE | 1.1111 |
| Phase51_WIDE | WIDE | L2 | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 1.8889 |
| Phase51_WIDE | WIDE | L2 | 221 | OURS-DETOUR+HMM | STOP_WAIT | 1 |
| Phase51_WIDE | WIDE | L2 | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 2.8889 |
| Phase51_WIDE | WIDE | L2 | 222 | OURS-DETOUR+HMM | NORMAL | 55.583 |
| Phase51_WIDE | WIDE | L2 | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.11111 |
| Phase51_WIDE | WIDE | L2 | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 1.8889 |
| Phase51_WIDE | WIDE | L2 | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 3.1111 |
| Phase51_L150 | L150 | LC | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 30.083 |
| Phase51_L150 | L150 | LC | 221 | OURS-DETOUR+HMM | NORMAL | 31.778 |
| Phase51_L150 | L150 | LC | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 4 |
| Phase51_L150 | L150 | LC | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.22222 |
| Phase51_L150 | L150 | LC | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 24.333 |
| Phase51_L150 | L150 | LC | 222 | OURS-DETOUR+HMM | NORMAL | 24.889 |
| Phase51_L150 | L150 | LC | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 3 |
| Phase51_L150 | L150 | LC | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.11111 |
| Phase51_WIDE | WIDE | LC | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3 |
| Phase51_WIDE | WIDE | LC | 221 | OURS-DETOUR+HMM | NORMAL | 25.722 |
| Phase51_WIDE | WIDE | LC | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.11111 |
| Phase51_WIDE | WIDE | LC | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 2.8889 |
| Phase51_WIDE | WIDE | LC | 222 | OURS-DETOUR+HMM | NORMAL | 24.222 |
| Phase51_WIDE | WIDE | LC | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 0.66667 |
| Phase51_WIDE | WIDE | LC | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 0.33333 |
| Phase51_WIDE | WIDE | LC | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.22222 |
| Phase51_L150 | L150 | SLW | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 39.333 |
| Phase51_L150 | L150 | SLW | 221 | OURS-DETOUR+HMM | NORMAL | 33.889 |
| Phase51_L150 | L150 | SLW | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 11 |
| Phase51_L150 | L150 | SLW | 221 | OURS-DETOUR+HMM | ENDPOINT | 1 |
| Phase51_L150 | L150 | SLW | 221 | OURS-DETOUR+HMM | STOP_WAIT | 3 |
| Phase51_L150 | L150 | SLW | 221 | OURS-DETOUR+HMM | RECOVER_ROTATE | 1.7778 |
| Phase51_L150 | L150 | SLW | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 38.444 |
| Phase51_L150 | L150 | SLW | 222 | OURS-DETOUR+HMM | NORMAL | 35.556 |
| Phase51_L150 | L150 | SLW | 222 | OURS-DETOUR+HMM | STOP_WAIT | 5 |
| Phase51_L150 | L150 | SLW | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 7 |
| Phase51_L150 | L150 | SLW | 222 | OURS-DETOUR+HMM | RECOVER_ROTATE | 3.5556 |
| Phase51_L150 | L150 | SLW | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.44444 |
| Phase51_WIDE | WIDE | SLW | 221 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3 |
| Phase51_WIDE | WIDE | SLW | 221 | OURS-DETOUR+HMM | NORMAL | 37.611 |
| Phase51_WIDE | WIDE | SLW | 221 | OURS-DETOUR+HMM | ENDPOINT | 0.22222 |
| Phase51_WIDE | WIDE | SLW | 221 | OURS-DETOUR+HMM | STOP_WAIT | 1 |
| Phase51_WIDE | WIDE | SLW | 221 | OURS-DETOUR+HMM | RECOVER_ROTATE | 1.7778 |
| Phase51_WIDE | WIDE | SLW | 221 | OURS-DETOUR+HMM | WAIT_FRESH | 0.22222 |
| Phase51_WIDE | WIDE | SLW | 221 | OURS-DETOUR+HMM | ALIGN_BRAKE | 3.3333 |
| Phase51_WIDE | WIDE | SLW | 221 | OURS-DETOUR+HMM | ALIGN_ROTATE | 4.6667 |
| Phase51_WIDE | WIDE | SLW | 222 | OURS-DETOUR+HMM | WAYPOINT_TIMEOUT | 3 |
| Phase51_WIDE | WIDE | SLW | 222 | OURS-DETOUR+HMM | NORMAL | 45.417 |
| Phase51_WIDE | WIDE | SLW | 222 | OURS-DETOUR+HMM | ENDPOINT | 0.77778 |
| Phase51_WIDE | WIDE | SLW | 222 | OURS-DETOUR+HMM | STOP_WAIT | 0.44444 |
| Phase51_WIDE | WIDE | SLW | 222 | OURS-DETOUR+HMM | ALIGN_ROTATE | 5.5556 |
| Phase51_WIDE | WIDE | SLW | 222 | OURS-DETOUR+HMM | ALIGN_BRAKE | 1.8889 |

| group | condition | scene | seed | method | box_number | spawn_s | path_id | observation_s | observed_before_spawn | installed_path_available | command_source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase52 | D075 | H1 | 221 | GRAPH-REC | 1 | 19.25 | 16 | 17.986 | True | True | NORMAL |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | 1 | 10 | 7 | 8.9861 | True | True | NORMAL |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | 1 | 10.069 | 7 | 8.9861 | True | True | NORMAL |
| Phase47_D075 | D075 | H1 | 221 | OURS-DETOUR+HMM | 1 | 19.319 | 16 | 17.986 | True | True | NORMAL |
| Phase47_D075 | D075 | H1 | 222 | OURS-DETOUR+HMM | 1 | 21.056 | 18 | 19.986 | True | True | NORMAL |
| Phase47_D075 | D075 | H2 | 221 | OURS-DETOUR+HMM | 1 | 9.9722 | 7 | 8.75 | True | True | NORMAL |
| Phase47_D075 | D075 | H2 | 221 | OURS-DETOUR+HMM | 2 | 58.611 | 55 | 56.736 | True | True | NORMAL |
| Phase47_D075 | D075 | H2 | 222 | OURS-DETOUR+HMM | 1 | 10.917 | 8 | 9.9861 | True | True | NORMAL |
| Phase47_D075 | D075 | H2 | 222 | OURS-DETOUR+HMM | 2 | 34.5 | 31 | 32.736 | True | True | ENDPOINT |
| Phase47_D075 | D075 | L2 | 221 | OURS-DETOUR+HMM | 1 | 10.069 | 7 | 8.9861 | True | True | NORMAL |
| Phase47_D075 | D075 | L2 | 222 | OURS-DETOUR+HMM | 1 | 11.458 | 8 | 9.9861 | True | True | NORMAL |
| Phase51_L150 | L150 | H1 | 221 | OURS-DETOUR+HMM | 1 | 30.431 | 15 | 27.986 | True | True | NORMAL |
| Phase51_L150 | L150 | H1 | 222 | OURS-DETOUR+HMM | 1 | 31 | — | — | — | False | WAYPOINT_TIMEOUT |
| Phase51_WIDE | WIDE | H1 | 221 | OURS-DETOUR+HMM | 1 | 19.222 | 16 | 17.986 | True | True | NORMAL |
| Phase51_WIDE | WIDE | H1 | 222 | OURS-DETOUR+HMM | 1 | 21.75 | 18 | 19.986 | True | True | NORMAL |
| Phase51_L150 | L150 | H2 | 221 | OURS-DETOUR+HMM | 1 | 15.181 | — | — | — | False | WAYPOINT_TIMEOUT |
| Phase51_L150 | L150 | H2 | 222 | OURS-DETOUR+HMM | 1 | 16.931 | — | — | — | False | WAYPOINT_TIMEOUT |
| Phase51_L150 | L150 | H2 | 222 | OURS-DETOUR+HMM | 2 | 46.806 | — | — | — | False | WAYPOINT_TIMEOUT |
| Phase51_WIDE | WIDE | H2 | 221 | OURS-DETOUR+HMM | 1 | 10.083 | 7 | 9 | True | True | NORMAL |
| Phase51_WIDE | WIDE | H2 | 222 | OURS-DETOUR+HMM | 1 | 11.458 | 8 | 9.9861 | True | True | NORMAL |
| Phase51_L150 | L150 | L2 | 221 | OURS-DETOUR+HMM | 1 | 15.153 | — | — | — | False | WAYPOINT_TIMEOUT |
| Phase51_L150 | L150 | L2 | 222 | OURS-DETOUR+HMM | 1 | 16.639 | 7 | 14.236 | True | True | NORMAL |
| Phase51_WIDE | WIDE | L2 | 221 | OURS-DETOUR+HMM | 1 | 10.014 | 7 | 9 | True | True | NORMAL |
| Phase51_WIDE | WIDE | L2 | 222 | OURS-DETOUR+HMM | 1 | 11.903 | 9 | 10.986 | True | True | NORMAL |

| group | condition | scene | seed | method | hold_after_rejection_s | hold_after_rejection_max_s | graph_dispatches | graph_applied | graph_acceptance_rate | graph_solve_p50_s | graph_solve_p95_s | graph_pool_times_s | graph_dispositions | graph_prediction_errors_m | graph_terminal_unapplied | graph_late_results |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase52 | D075 | H1 | 221 | GRAPH-REC | 1.8889 | 1.8889 | 29 | 4 | 0.13793 | 0.13187 | 0.22308 | [0.318530736, 0.21563084, 0.15537196, 0.228038282, 0.133878122, 0.131214009, 0.132284302, 0.143157565, 0.130544835, 0.126097318, 0.131768963, 0.145407383, 0.12978032, 0.137726977, 0.127321709, 0.13292267, 0.131181638, 0.131868199, 0.125630675, 0.129466738, 0.129876651, 0.167086531, 0.186574677, 0.141260431, 0.130423419, 0.118424027, 0.131561793, 0.134686759, 0.116604868] | {'ACCEPTED': 4, 'REJECTED': 25} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.027160493827159918, 0.0] | 0 | 0 |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | 1 | 1 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | 0.77778 | 0.77778 | 17 | 2 | 0.11765 | 0.13774 | 0.22433 | [0.242028878, 0.219901523, 0.148419345, 0.137739926, 0.125906137, 0.130348896, 0.124662169, 0.130204865, 0.137992979, 0.135973721, 0.150399676, 0.128556961, 0.124264441, 0.132244592, 0.144815771, 0.158711888, 0.141693004] | {'REJECTED': 13, 'ACCEPTED': 2, 'EXEC_CERT_REJECT': 1} | [0.0, 0.06049382692643623, 0.19334040883322062, 0.0, 0.0, 0.0, 0.06049380652907654, 0.0, 0.01914247578173889, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 1 | 0 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | 0 | 0 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | 0 | 0 | 56 | 13 | 0.23214 | 0.13025 | 0.16673 | [0.219337065, 0.181322011, 0.124776247, 0.161862866, 0.128355123, 0.13465932, 0.119347366, 0.128278683, 0.130152017, 0.123570196, 0.129223984, 0.122676439, 0.13350093, 0.146060529, 0.114405876, 0.133590118, 0.148581644, 0.131443075, 0.145845962, 0.123493058, 0.13582444, 0.159751983, 0.127806873, 0.137195036, 0.13722846, 0.129284956, 0.124524731, 0.115866687, 0.128542559, 0.118313941, 0.158503756, 0.159655565, 0.139475041, 0.151177846, 0.128651852, 0.129733477, 0.13244558, 0.13922103, 0.188413936, 0.119488846, 0.124377525, 0.127165304, 0.135781254, 0.125650867, 0.128552072, 0.129102557, 0.130729698, 0.134533225, 0.128375199, 0.131649911, 0.130342652, 0.118590553, 0.145293364, 0.133669272, 0.129475875, 0.120694766] | {'ACCEPTED': 13, 'REJECTED': 43} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D075 | SLW | 221 | CUT-HOLD | 6.2222 | 2.1111 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | 0 | 0 | 63 | 10 | 0.15873 | 0.13287 | 0.16934 | [0.320167115, 0.198386133, 0.130049043, 0.167126312, 0.121935849, 0.133214734, 0.119236406, 0.139583705, 0.163057946, 0.151637777, 0.140008586, 0.134007807, 0.117931216, 0.135735004, 0.117536723, 0.120377814, 0.125515339, 0.121211453, 0.131324595, 0.1475422, 0.123869428, 0.158299708, 0.127012046, 0.128549079, 0.129670282, 0.153984262, 0.123911859, 0.117439043, 0.121899366, 0.130935114, 0.121858424, 0.154846897, 0.13325053, 0.126234421, 0.124706361, 0.132865504, 0.128487937, 0.211699008, 0.112346947, 0.153062218, 0.125714849, 0.152826491, 0.133280909, 0.135480515, 0.124710531, 0.124095428, 0.130182966, 0.143633418, 0.148624118, 0.168786991, 0.144061565, 0.126306036, 0.169405593, 0.124748569, 0.142270415, 0.134888835, 0.119228625, 0.135213355, 0.126461762, 0.118964663, 0.143198546, 0.153035369, 0.138513678] | {'ACCEPTED': 10, 'REJECTED': 51, 'RECOVERY_ACTIVE': 2} | [0.0, 0.0, 0.0, 0.0, 0.02463885957755361, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.011107453493409827, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
