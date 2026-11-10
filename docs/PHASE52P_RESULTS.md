| status | completed | planned | protocol_sha256 |
|---|---|---|---|
| PARTIAL | 0 | 40 | 57838e8042c9d156c728313a61432c2e3eccb000530f20ef654b2045978a57c4 |

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

| group | condition | method | scene | n | valid | success | timeout | collision | wrong_stop | box_passage | box_passage_from_spawn_median_s | goal_time_s_median | mean_speed_m_s_median | stopped_s_median | minimum_clearance_m_median | tracking_error_p50_m_median | tracking_error_p95_m_median | chunk_heading_jump_p50_deg_median | chunk_heading_jump_p95_deg_median | raw_candidate_distance_mean_m_median | stop_distance_m_median | ec_rejects_median | graph_solve_p50_s_median | graph_solve_p95_s_median | graph_acceptance_rate_median | hold_after_rejection_s_median |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase47_D075 | D075 | OURS-DETOUR+HMM | SLW | 2 | 2 | 1 | 1 | 0 | 0 | 0 | — | 50.583 | 0.12406 | 13.167 | 0.045057 | 0.02635 | 0.17469 | 28.819 | 153.46 | 0.046282 | 0.34858 | 26.5 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | LC | 2 | 2 | 2 | 0 | 0 | 0 | 0 | — | 28.708 | 0.18506 | 3.3889 | 0.14702 | 0.026797 | 0.12975 | 21.357 | 52.077 | 0.041332 | 0.36225 | 0.5 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | L2 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 16.035 | 47.083 | 0.18314 | 4.3333 | 0.056457 | 0.031096 | 0.15838 | 24.248 | 86.933 | 0.048871 | 0.31648 | 0.5 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | H1 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 9.1806 | 31.833 | 0.17534 | 5.0833 | 0.053689 | 0.029991 | 0.11905 | 10.314 | 65.454 | 0.041937 | 0.31157 | 7 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | H2 | 2 | 2 | 1 | 0 | 0 | 1 | 2 | 47.667 | 48.583 | 0.15778 | 10.236 | 0.063421 | 0.029149 | 0.15776 | 25.478 | 81.301 | 0.04567 | 0.52564 | 5 | — | — | — | 0 |
| Phase47_D075 | D075 | OURS-DETOUR+HMM | ALL | 10 | 10 | 8 | 1 | 0 | 1 | 6 | 16.035 | 38.708 | 0.17093 | 5.9444 | 0.058264 | 0.030183 | 0.14784 | 23.119 | 72.964 | 0.044552 | 0.34858 | 2.5 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | SLW | 2 | 2 | 0 | 2 | 0 | 0 | 0 | — | — | 0.059992 | 47.444 | 0.037413 | 0.021071 | 0.22232 | 47.434 | 152.15 | 0.046355 | — | 36 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | LC | 2 | 2 | 2 | 0 | 0 | 0 | 0 | — | 59.208 | 0.099545 | 20.875 | 0.17771 | 0.033927 | 0.14481 | 42.451 | 117.14 | 0.047944 | 0.28855 | 7 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | L2 | 2 | 2 | 0 | 2 | 0 | 0 | 0 | — | — | 0.075039 | 36.444 | 0.14107 | 0.029905 | 0.1752 | 34.856 | 97.943 | 0.047486 | — | 8.5 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | H1 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 18.097 | 53.333 | 0.10496 | 19.944 | 0.076465 | 0.034308 | 0.13406 | 14.12 | 40.051 | 0.045748 | 0.33354 | 12.5 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | H2 | 2 | 2 | 0 | 1 | 0 | 1 | 1 | 41.361 | — | 0.09009 | 29.944 | 0.063706 | 0.0293 | 0.13348 | 32.354 | 96.392 | 0.041696 | 0.59719 | 12 | — | — | — | 0 |
| Phase51_L150 | L150 | OURS-DETOUR+HMM | ALL | 10 | 10 | 4 | 5 | 0 | 1 | 3 | 24.194 | 55.833 | 0.085683 | 30.611 | 0.054674 | 0.028827 | 0.14608 | 34.856 | 97.943 | 0.045336 | 0.31243 | 12.5 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | SLW | 2 | 2 | 1 | 0 | 0 | 1 | 0 | — | 51.833 | 0.11608 | 10.611 | 0.081658 | 0.022003 | 0.15455 | 43.11 | 141.31 | 0.041368 | 0.46975 | 16.5 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | LC | 2 | 2 | 2 | 0 | 0 | 0 | 0 | — | 28.583 | 0.1902 | 3.1111 | 0.25705 | 0.031635 | 0.12234 | 24.762 | 66.051 | 0.042025 | 0.34421 | 1 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | L2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | — | 0.11818 | 6.3333 | 0.072071 | 0.023566 | 0.11706 | 27.001 | 90.502 | 0.037063 | 6.9442 | 3 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | H1 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | — | 0.14098 | 10.944 | 0.06432 | 0.026739 | 0.11478 | 19.165 | 80.311 | 0.038499 | 2.9829 | 13 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | H2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | — | — | 0.12584 | 9.2778 | 0.16696 | 0.025948 | 0.15639 | 29.372 | 80.876 | 0.043185 | 7.209 | 6.5 | — | — | — | 0 |
| Phase51_WIDE | WIDE | OURS-DETOUR+HMM | ALL | 10 | 10 | 3 | 0 | 0 | 7 | 0 | — | 28.833 | 0.12695 | 8.6111 | 0.098123 | 0.024432 | 0.13351 | 28.125 | 84.357 | 0.040713 | 2.9829 | 5.5 | — | — | — | 0 |

| condition | scene | seed | method | status | success | collision | timeout_without_declaration | wrong_stop | box_passage | box_passage_from_spawn_s | goal_time_s | mean_speed_m_s | stopped_s | minimum_clearance_m | tracking_error_p50_m | tracking_error_p95_m | chunk_heading_jump_p50_deg | chunk_heading_jump_p95_deg | raw_candidate_distance_mean_m | stop_distance_m | ec_rejects | graph_solve_p50_s | graph_solve_p95_s | graph_acceptance_rate | hold_after_rejection_s | Phase47_D075_success | Phase47_D075_collision | Phase47_D075_goal_time_s | Phase47_D075_stopped_s | Phase47_D075_tracking_error_p95_m | Phase47_D075_box_passage | Phase47_D075_box_passage_from_spawn_s | Phase47_D075_wrong_stop | Phase51_L150_success | Phase51_L150_collision | Phase51_L150_goal_time_s | Phase51_L150_stopped_s | Phase51_L150_tracking_error_p95_m | Phase51_L150_box_passage | Phase51_L150_box_passage_from_spawn_s | Phase51_L150_wrong_stop | Phase51_WIDE_success | Phase51_WIDE_collision | Phase51_WIDE_goal_time_s | Phase51_WIDE_stopped_s | Phase51_WIDE_tracking_error_p95_m | Phase51_WIDE_box_passage | Phase51_WIDE_box_passage_from_spawn_s | Phase51_WIDE_wrong_stop |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D075 | SLW | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D075 | SLW | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D075 | LC | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D075 | LC | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D075 | L2 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D075 | L2 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D075 | H1 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D075 | H1 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D075 | H2 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D075 | H2 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D075 | SLW | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D075 | SLW | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D075 | LC | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D075 | LC | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D075 | L2 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D075 | L2 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D075 | H1 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D075 | H1 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D075 | H2 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |
| D075 | H2 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |
| D150 | SLW | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D150 | SLW | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D150 | LC | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D150 | LC | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D150 | L2 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D150 | L2 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D150 | H1 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D150 | H1 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D150 | H2 | 221 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D150 | H2 | 221 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D150 | SLW | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D150 | SLW | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D150 | LC | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D150 | LC | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D150 | L2 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D150 | L2 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D150 | H1 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D150 | H1 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D150 | H2 | 222 | CUT-HOLD | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |
| D150 | H2 | 222 | GRAPH-REC | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |

| group | condition | scene | seed | method | state | seconds |
|---|---|---|---|---|---|---|
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

| n |
|---|
| 0 |
