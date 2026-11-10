| status | completed | planned | protocol_sha256 | audit_revision_sha256 |
|---|---|---|---|---|
| COMPLETE | 40 | 40 | 57838e8042c9d156c728313a61432c2e3eccb000530f20ef654b2045978a57c4 | 8777f1e1fdc492c58c1338111e05855b37a8c2439660d76ba07e55d81f7e0172 |

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
| Phase52 | D075 | CUT-HOLD | SLW | 2 | 2 | 0 | 2 | 0 | 0 | 0 | — | — | 0.10425 | 21.722 | 2.8889 | 0.029106 | 0.023604 | 0.14837 | 32.649 | 149.44 | 0.042856 | — | 53 | — | — | — | 7.6111 |
| Phase52 | D075 | CUT-HOLD | LC | 2 | 2 | 2 | 0 | 0 | 0 | 0 | — | 29.458 | 0.18613 | 3.6111 | 2.8889 | 0.23339 | 0.025898 | 0.1346 | 15.003 | 53.92 | 0.040048 | 0.30432 | 2 | — | — | — | 0 |
| Phase52 | D075 | CUT-HOLD | L2 | 2 | 2 | 1 | 1 | 0 | 0 | 1 | 10.528 | 37.833 | 0.16633 | 6.8333 | 2.8889 | 0.042403 | 0.026248 | 0.15068 | 22.142 | 92.393 | 0.044092 | 0.38029 | 16 | — | — | — | 1.5 |
| Phase52 | D075 | CUT-HOLD | H1 | 2 | 2 | 1 | 0 | 0 | 1 | 2 | 6.7569 | 27.833 | 0.19738 | 3.3333 | 2.8889 | 0.082349 | 0.040145 | 0.19005 | 14.614 | 73.944 | 0.058396 | 0.42251 | 7.5 | — | — | — | 0.77778 |
| Phase52 | D075 | CUT-HOLD | H2 | 2 | 2 | 0 | 1 | 0 | 1 | 1 | 27.556 | — | 0.16064 | 5.8333 | 2.8889 | 0.088875 | 0.024665 | 0.12149 | 25.651 | 90.451 | 0.039025 | 0.53716 | 2 | — | — | — | 0.94444 |
| Phase52 | D075 | CUT-HOLD | ALL | 10 | 10 | 4 | 4 | 0 | 2 | 4 | 8.9306 | 29.458 | 0.17763 | 4.5 | 2.8889 | 0.066199 | 0.026607 | 0.14003 | 20.13 | 85.944 | 0.041921 | 0.37206 | 4 | — | — | — | 1 |
| Phase52 | D075 | GRAPH-REC | SLW | 2 | 2 | 0 | 1 | 0 | 1 | 0 | — | — | 0.11423 | 11.937 | 2.8889 | 0.05459 | 0.021518 | 0.14325 | 20.691 | 123.99 | 0.037102 | 3.0104 | 31 | 0.1301 | 0.16996 | 0.16459 | 1.8889 |
| Phase52 | D075 | GRAPH-REC | LC | 2 | 2 | 1 | 0 | 0 | 1 | 0 | — | 28.889 | 0.16384 | 5.2778 | 2.8889 | 0.19361 | 0.027945 | 0.12456 | 19.599 | 74.624 | 0.041875 | 2.4057 | 1 | 0.12942 | 0.16902 | 0.15453 | 0 |
| Phase52 | D075 | GRAPH-REC | L2 | 2 | 2 | 0 | 0 | 1 | 1 | 0 | — | — | 0.13788 | 7.6667 | 2.8889 | 0.012795 | 0.022447 | 0.15243 | 19.749 | 95.829 | 0.045775 | 7.852 | 57.5 | 0.13914 | 0.20049 | 0.19817 | 1.8333 |
| Phase52 | D075 | GRAPH-REC | H1 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 8.6597 | 30.868 | 0.18307 | 3.3333 | 2.8889 | 0.088318 | 0.029884 | 0.15594 | 11.451 | 41.458 | 0.04797 | 0.37967 | 3.5 | 0.13143 | 0.20863 | 0.16156 | 0.94444 |
| Phase52 | D075 | GRAPH-REC | H2 | 2 | 2 | 0 | 2 | 0 | 0 | 0 | — | — | 0.14869 | 7.0556 | 2.8889 | 0.045255 | 0.025695 | 0.14933 | 16.118 | 75.778 | 0.042398 | — | 20 | 0.13704 | 0.184 | 0.34091 | 0.38889 |
| Phase52 | D075 | GRAPH-REC | ALL | 10 | 10 | 3 | 3 | 1 | 3 | 2 | 8.6597 | 29.889 | 0.1529 | 6.8889 | 2.8889 | 0.046574 | 0.023597 | 0.14394 | 16.118 | 75.778 | 0.041382 | 1.7082 | 15 | 0.13237 | 0.17628 | 0.17782 | 0.38889 |
| Phase52 | D150 | CUT-HOLD | SLW | 2 | 2 | 0 | 2 | 0 | 0 | 0 | — | — | 0.095315 | 24.833 | 3.6667 | 0.054433 | 0.057707 | 0.3927 | 55.462 | 139.88 | 0.10662 | — | 57.5 | — | — | — | 2.6111 |
| Phase52 | D150 | CUT-HOLD | LC | 2 | 2 | 1 | 0 | 0 | 1 | 0 | — | 35.083 | 0.13159 | 17.153 | 3.6667 | 0.16054 | 0.10431 | 0.38267 | 51.501 | 112.84 | 0.12603 | 0.58472 | 6 | — | — | — | 0 |
| Phase52 | D150 | CUT-HOLD | L2 | 2 | 2 | 1 | 1 | 0 | 0 | 2 | 62.868 | 89.333 | 0.090912 | 47.333 | 3.6667 | 0.033484 | 0.044764 | 0.33348 | 38.104 | 111.32 | 0.097759 | 0.33641 | 2.5 | — | — | — | 1.2222 |
| Phase52 | D150 | CUT-HOLD | H1 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 24.847 | 59.583 | 0.13043 | 15.097 | 3.6667 | 0.082494 | 0.053779 | 0.36546 | 39.449 | 75.075 | 0.11369 | 0.62497 | 8.5 | — | — | — | 2.4444 |
| Phase52 | D150 | CUT-HOLD | H2 | 2 | 2 | 1 | 1 | 0 | 0 | 1 | 52.319 | 80.333 | 0.10306 | 27.278 | 3.6667 | 0.05567 | 0.063024 | 0.37585 | 51.21 | 127.89 | 0.10577 | 0.4107 | 23.5 | — | — | — | 3.2222 |
| Phase52 | D150 | CUT-HOLD | ALL | 10 | 10 | 4 | 4 | 0 | 2 | 4 | 50.771 | 69.958 | 0.10855 | 25.278 | 3.6667 | 0.05567 | 0.060329 | 0.37585 | 42.083 | 125 | 0.11369 | 0.43401 | 11 | — | — | — | 1.7778 |
| Phase52 | D150 | GRAPH-REC | SLW | 2 | 2 | 2 | 0 | 0 | 0 | 0 | — | 70.868 | 0.10677 | 20.236 | 3.6667 | 0.037878 | 0.05174 | 0.43778 | 33.987 | 155.48 | 0.12225 | 0.44142 | 32 | 0.13727 | 0.19426 | 0.23137 | 1.1667 |
| Phase52 | D150 | GRAPH-REC | LC | 2 | 2 | 1 | 0 | 0 | 1 | 0 | — | 42.097 | 0.15107 | 9.4444 | 3.6667 | 0.13071 | 0.090186 | 0.44165 | 14.307 | 100.5 | 0.1437 | 0.33965 | 7.5 | 0.1391 | 0.19955 | 0.24747 | 0 |
| Phase52 | D150 | GRAPH-REC | L2 | 2 | 2 | 1 | 1 | 0 | 0 | 1 | 10.181 | 52.639 | 0.13391 | 19.222 | 3.6667 | 0.056822 | 0.082432 | 0.44546 | 29.191 | 89.898 | 0.14105 | 0.27656 | 15.5 | 0.14243 | 0.18715 | 0.30357 | 0.77778 |
| Phase52 | D150 | GRAPH-REC | H1 | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 11.958 | 43.861 | 0.11445 | 12 | 3.6667 | 0.15028 | 0.061416 | 0.35309 | 55.816 | 142.4 | 0.11192 | 1.3475 | 12.5 | 0.14035 | 0.17653 | 0.2971 | 0.88889 |
| Phase52 | D150 | GRAPH-REC | H2 | 2 | 2 | 0 | 2 | 0 | 0 | 0 | — | — | 0.096878 | 33.222 | 3.6667 | 0.037163 | 0.027877 | 0.43768 | 36.482 | 153.06 | 0.1086 | — | 104 | 0.14988 | 0.22736 | 0.38 | 6 |
| Phase52 | D150 | GRAPH-REC | ALL | 10 | 10 | 5 | 3 | 0 | 2 | 2 | 11.069 | 52.639 | 0.11558 | 17.889 | 3.6667 | 0.059479 | 0.05174 | 0.40585 | 27.323 | 144.55 | 0.12956 | 0.41882 | 18 | 0.14097 | 0.19474 | 0.27051 | 1.1667 |
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
| D075 | H1 | 221 | CUT-HOLD | PASS | False | False | False | True | True | 7.3333 | — | 0.20146 | 3.3333 | 2.8889 | 0.035381 | 0.0423 | 0.23505 | 18.858 | 89.706 | 0.06432 | 0.5589 | 10 | — | — | — | 1.5556 | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D075 | H2 | 221 | CUT-HOLD | PASS | False | False | True | False | False | — | — | 0.13429 | 6.6667 | 2.8889 | 0.099346 | 0.02572 | 0.10929 | 29.9 | 98.719 | 0.037129 | — | 3 | — | — | — | 1 | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D075 | H2 | 221 | GRAPH-REC | PASS | False | False | True | False | False | — | — | 0.16484 | 6.5556 | 2.8889 | 0.051239 | 0.027258 | 0.14301 | 17.168 | 66.239 | 0.042366 | — | 9 | 0.13717 | 0.1921 | 0.22727 | 0 | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D075 | SLW | 222 | GRAPH-REC | PASS | False | False | True | False | False | — | — | 0.11969 | 10.444 | 2.8889 | 0.067271 | 0.023063 | 0.13541 | 19.285 | 105.72 | 0.037421 | — | 35 | 0.12733 | 0.17057 | 0.17045 | 3.7778 | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D075 | SLW | 222 | CUT-HOLD | PASS | False | False | True | False | False | — | — | 0.10272 | 21.111 | 2.8889 | 0.027224 | 0.027494 | 0.13409 | 36.422 | 136.77 | 0.044921 | — | 56 | — | — | — | 9 | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D075 | LC | 222 | CUT-HOLD | PASS | True | False | False | False | False | — | 30.833 | 0.16828 | 4 | 2.8889 | 0.1832 | 0.028162 | 0.13417 | 17.825 | 69.451 | 0.041636 | 0.36383 | 2 | — | — | — | 0 | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D075 | LC | 222 | GRAPH-REC | PASS | True | False | False | False | False | — | 28.889 | 0.18671 | 3.3333 | 2.8889 | 0.28307 | 0.031626 | 0.12465 | 13.184 | 51.917 | 0.045038 | 0.32796 | 2 | 0.12859 | 0.1713 | 0.076923 | 0 | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D075 | L2 | 222 | GRAPH-REC | PASS | False | False | False | True | False | — | — | 0.10672 | 11.667 | 2.8889 | 0.025603 | 0.022382 | 0.14487 | 26.648 | 146.11 | 0.040399 | 7.852 | 94 | 0.14053 | 0.17665 | 0.27869 | 2.8889 | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D075 | L2 | 222 | CUT-HOLD | PASS | False | False | True | False | False | — | — | 0.11705 | 10 | 2.8889 | 0.030813 | 0.023311 | 0.15526 | 25.548 | 126.24 | 0.042206 | — | 30 | — | — | — | 2 | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D075 | H1 | 222 | GRAPH-REC | PASS | True | False | False | False | True | 7.125 | 29.889 | 0.17861 | 3.4444 | 2.8889 | 0.14175 | 0.022574 | 0.12451 | 9.0934 | 44.125 | 0.037275 | 0.40588 | 7 | 0.131 | 0.19418 | 0.18519 | 0 | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D075 | H1 | 222 | CUT-HOLD | PASS | True | False | False | False | True | 6.1806 | 27.833 | 0.1933 | 3.3333 | 2.8889 | 0.12932 | 0.037989 | 0.14504 | 10.37 | 58.182 | 0.052473 | 0.28612 | 5 | — | — | — | 0 | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D075 | H2 | 222 | GRAPH-REC | PASS | False | False | True | False | False | — | — | 0.13255 | 7.5556 | 2.8889 | 0.039272 | 0.024132 | 0.15565 | 15.068 | 85.316 | 0.042431 | — | 31 | 0.13691 | 0.17591 | 0.45455 | 0.77778 | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |
| D075 | H2 | 222 | CUT-HOLD | PASS | False | False | False | True | True | 27.556 | — | 0.18698 | 5 | 2.8889 | 0.078404 | 0.02361 | 0.13369 | 21.402 | 82.183 | 0.04092 | 0.53716 | 1 | — | — | — | 0.88889 | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |
| D150 | SLW | 221 | GRAPH-REC | PASS | True | False | False | False | False | — | 66.375 | 0.11355 | 19.222 | 3.6667 | 0.039648 | 0.050579 | 0.49133 | 40.565 | 162.1 | 0.13485 | 0.46401 | 36 | 0.13748 | 0.21053 | 0.19444 | 1.5556 | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D150 | SLW | 221 | CUT-HOLD | PASS | False | False | True | False | False | — | — | 0.10433 | 24.778 | 3.6667 | 0.045217 | 0.060517 | 0.49415 | 34.9 | 129.35 | 0.12509 | — | 58 | — | — | — | 3.4444 | True | False | 50.583 | 8.5556 | 0.19527 | False | — | False | False | False | — | 50.111 | 0.24755 | False | — | False | True | False | 51.833 | 11.222 | 0.17673 | False | — | False |
| D150 | LC | 221 | GRAPH-REC | PASS | True | False | False | False | False | — | 42.097 | 0.15953 | 8.5556 | 3.6667 | 0.15965 | 0.099596 | 0.4973 | 8.4623 | 44.082 | 0.16084 | 0.13506 | 8 | 0.14445 | 0.21323 | 0.27273 | 0 | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D150 | LC | 221 | CUT-HOLD | PASS | True | False | False | False | False | — | 35.083 | 0.17161 | 7.5556 | 3.6667 | 0.22891 | 0.15815 | 0.43515 | 26.878 | 69.227 | 0.16259 | 0.32751 | 12 | — | — | — | 0 | True | False | 28.833 | 3.4444 | 0.11947 | False | — | False | True | False | 66.083 | 23.75 | 0.15128 | False | — | False | True | False | 28.833 | 2.8889 | 0.12752 | False | — | False |
| D150 | L2 | 221 | GRAPH-REC | PASS | True | False | False | False | True | 10.181 | 52.639 | 0.16697 | 12.889 | 3.6667 | 0.041616 | 0.12293 | 0.48105 | 18.468 | 58.92 | 0.16002 | 0.27656 | 12 | 0.13462 | 0.173 | 0.10714 | 0 | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D150 | L2 | 221 | CUT-HOLD | PASS | False | False | True | False | True | 76.514 | — | 0.045412 | 69 | 3.6667 | 0.031282 | 0.00072483 | 0.19898 | 38.129 | 93.338 | 0.04012 | — | 1 | — | — | — | 0.66667 | True | False | 43.583 | 2.8889 | 0.15508 | True | 13.292 | False | False | False | — | 36.667 | 0.13625 | False | — | False | False | False | — | 6.2222 | 0.096295 | False | — | True |
| D150 | H1 | 221 | GRAPH-REC | PASS | True | False | False | False | True | 11.958 | 43.861 | 0.14511 | 7.4444 | 3.6667 | 0.13076 | 0.076234 | 0.3798 | 27.236 | 123.27 | 0.13882 | 0.27552 | 17 | 0.14714 | 0.18818 | 0.26087 | 1.7778 | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D150 | H1 | 221 | CUT-HOLD | PASS | True | False | False | False | True | 24.847 | 59.583 | 0.11277 | 21.333 | 3.6667 | 0.031883 | 0.039078 | 0.4027 | 46.036 | 105.33 | 0.11627 | 0.45732 | 7 | — | — | — | 4.8889 | True | False | 33.833 | 6.1111 | 0.13443 | True | 11.556 | False | True | False | 59.333 | 25.111 | 0.12718 | True | 24.194 | False | False | False | — | 13.667 | 0.13464 | False | — | True |
| D150 | H2 | 221 | CUT-HOLD | PASS | False | False | True | False | False | — | — | 0.091271 | 28.444 | 3.6667 | 0.063406 | 0.060141 | 0.36568 | 56.076 | 120.7 | 0.094612 | — | 18 | — | — | — | 3.4444 | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D150 | H2 | 221 | GRAPH-REC | PASS | False | False | True | False | False | — | — | 0.076149 | 41.333 | 3.6667 | 0.027397 | 0.016584 | 0.40183 | 47.173 | 165.88 | 0.084637 | — | 160 | 0.15433 | 0.23505 | 0.34 | 8.5556 | False | False | — | 11.556 | 0.14156 | True | 65.208 | True | False | False | — | 36.111 | 0.15123 | False | — | False | False | False | — | 9.5556 | 0.15431 | False | — | True |
| D150 | SLW | 222 | GRAPH-REC | PASS | True | False | False | False | False | — | 75.361 | 0.09999 | 21.25 | 3.6667 | 0.036108 | 0.052901 | 0.38423 | 27.409 | 148.85 | 0.10965 | 0.41882 | 28 | 0.13707 | 0.17799 | 0.26829 | 0.77778 | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D150 | SLW | 222 | CUT-HOLD | PASS | False | False | True | False | False | — | — | 0.0863 | 24.889 | 3.6667 | 0.06365 | 0.054897 | 0.29125 | 76.025 | 150.41 | 0.088137 | — | 57 | — | — | — | 1.7778 | False | False | — | 17.778 | 0.15411 | False | — | False | False | False | — | 44.778 | 0.19708 | False | — | False | False | False | — | 10 | 0.13238 | False | — | True |
| D150 | LC | 222 | CUT-HOLD | PASS | False | False | False | True | False | — | — | 0.091569 | 26.75 | 3.6667 | 0.092175 | 0.050475 | 0.3302 | 76.125 | 156.45 | 0.089466 | 0.84192 | 0 | — | — | — | 0 | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D150 | LC | 222 | GRAPH-REC | PASS | False | False | False | True | False | — | — | 0.14262 | 10.333 | 3.6667 | 0.10177 | 0.080775 | 0.386 | 20.152 | 156.92 | 0.12657 | 0.54423 | 7 | 0.13374 | 0.18587 | 0.22222 | 0 | True | False | 28.583 | 3.3333 | 0.14003 | False | — | False | True | False | 52.333 | 18 | 0.13833 | False | — | False | True | False | 28.333 | 3.3333 | 0.11717 | False | — | False |
| D150 | L2 | 222 | CUT-HOLD | PASS | True | False | False | False | True | 49.222 | 89.333 | 0.13641 | 25.667 | 3.6667 | 0.035685 | 0.088803 | 0.46798 | 38.079 | 129.3 | 0.1554 | 0.33641 | 4 | — | — | — | 1.7778 | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D150 | L2 | 222 | GRAPH-REC | PASS | False | False | True | False | False | — | — | 0.10084 | 25.556 | 3.6667 | 0.072029 | 0.041934 | 0.40987 | 39.914 | 120.88 | 0.12208 | — | 19 | 0.15024 | 0.2013 | 0.5 | 1.5556 | True | False | 50.583 | 5.7778 | 0.16169 | True | 18.778 | False | False | False | — | 36.222 | 0.21416 | False | — | False | False | False | — | 6.4444 | 0.13782 | False | — | True |
| D150 | H1 | 222 | GRAPH-REC | PASS | False | False | False | True | False | — | — | 0.083792 | 16.556 | 3.6667 | 0.1698 | 0.046598 | 0.32638 | 84.395 | 161.53 | 0.085026 | 2.4195 | 8 | 0.13356 | 0.16489 | 0.33333 | 0 | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D150 | H1 | 222 | CUT-HOLD | PASS | False | False | False | True | False | — | — | 0.1481 | 8.8611 | 3.6667 | 0.1331 | 0.06848 | 0.32822 | 32.863 | 44.817 | 0.11111 | 0.79262 | 10 | — | — | — | 0 | True | False | 29.833 | 4.0556 | 0.10367 | True | 6.8056 | False | True | False | 47.333 | 14.778 | 0.14094 | True | 12 | False | False | False | — | 8.2222 | 0.094914 | False | — | True |
| D150 | H2 | 222 | CUT-HOLD | PASS | True | False | False | False | True | 52.319 | 80.333 | 0.11486 | 26.111 | 3.6667 | 0.047933 | 0.065907 | 0.38601 | 46.345 | 135.09 | 0.11693 | 0.4107 | 29 | — | — | — | 3 | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |
| D150 | H2 | 222 | GRAPH-REC | PASS | False | False | True | False | False | — | — | 0.11761 | 25.111 | 3.6667 | 0.046929 | 0.03917 | 0.47354 | 25.791 | 140.24 | 0.13255 | — | 48 | 0.14542 | 0.21968 | 0.42 | 3.4444 | True | False | 48.583 | 8.9167 | 0.17396 | True | 30.125 | False | False | False | — | 23.778 | 0.11573 | True | 41.361 | True | False | False | — | 9 | 0.15848 | False | — | True |

| scene | seed | method | initial_wait_s | first_chunk_received_s | first_chunk_control_s | startup_missing_timeout_rows | new_timeout_count | post_chunk_waypoint_timeout_rows | selected_attempt |
|---|---|---|---|---|---|---|---|---|---|
| H1_D075 | 221 | CUT-HOLD | 2.8889 | 2.8472 | 2.8889 | 26 | 0 | 0 | — |
| H1_D075 | 221 | GRAPH-REC | 2.8889 | 2.8611 | 2.8889 | 26 | 0 | 0 | 1 |
| H1_D075 | 222 | CUT-HOLD | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| H1_D075 | 222 | GRAPH-REC | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| H1_D150 | 221 | CUT-HOLD | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| H1_D150 | 221 | GRAPH-REC | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| H1_D150 | 222 | CUT-HOLD | 3.6667 | 3.5972 | 3.6667 | 33 | 0 | 0 | — |
| H1_D150 | 222 | GRAPH-REC | 3.6667 | 3.6111 | 3.6667 | 33 | 0 | 0 | — |
| H2_D075 | 221 | CUT-HOLD | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| H2_D075 | 221 | GRAPH-REC | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| H2_D075 | 222 | CUT-HOLD | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| H2_D075 | 222 | GRAPH-REC | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| H2_D150 | 221 | CUT-HOLD | 3.6667 | 3.5972 | 3.6667 | 33 | 0 | 0 | — |
| H2_D150 | 221 | GRAPH-REC | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| H2_D150 | 222 | CUT-HOLD | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| H2_D150 | 222 | GRAPH-REC | 3.6667 | 3.5972 | 3.6667 | 33 | 0 | 0 | — |
| L2_D075 | 221 | CUT-HOLD | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | 1 |
| L2_D075 | 221 | GRAPH-REC | 2.8889 | 2.8472 | 2.8889 | 26 | 0 | 0 | 1 |
| L2_D075 | 222 | CUT-HOLD | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| L2_D075 | 222 | GRAPH-REC | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| L2_D150 | 221 | CUT-HOLD | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| L2_D150 | 221 | GRAPH-REC | 3.6667 | 3.5972 | 3.6667 | 33 | 0 | 0 | — |
| L2_D150 | 222 | CUT-HOLD | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| L2_D150 | 222 | GRAPH-REC | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| LC_D075 | 221 | CUT-HOLD | 2.8889 | 2.8472 | 2.8889 | 26 | 0 | 0 | 1 |
| LC_D075 | 221 | GRAPH-REC | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | 1 |
| LC_D075 | 222 | CUT-HOLD | 2.8889 | 2.8472 | 2.8889 | 26 | 0 | 0 | — |
| LC_D075 | 222 | GRAPH-REC | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| LC_D150 | 221 | CUT-HOLD | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| LC_D150 | 221 | GRAPH-REC | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| LC_D150 | 222 | CUT-HOLD | 3.6667 | 3.5972 | 3.6667 | 33 | 0 | 0 | — |
| LC_D150 | 222 | GRAPH-REC | 3.6667 | 3.5972 | 3.6667 | 33 | 0 | 0 | — |
| SLW_D075 | 221 | CUT-HOLD | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | 1 |
| SLW_D075 | 221 | GRAPH-REC | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | 1 |
| SLW_D075 | 222 | CUT-HOLD | 2.8889 | 2.8333 | 2.8889 | 26 | 0 | 0 | — |
| SLW_D075 | 222 | GRAPH-REC | 2.8889 | 2.8472 | 2.8889 | 26 | 0 | 0 | — |
| SLW_D150 | 221 | CUT-HOLD | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| SLW_D150 | 221 | GRAPH-REC | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |
| SLW_D150 | 222 | CUT-HOLD | 3.6667 | 3.5972 | 3.6667 | 33 | 0 | 0 | — |
| SLW_D150 | 222 | GRAPH-REC | 3.6667 | 3.5833 | 3.6667 | 33 | 0 | 0 | — |

| group | condition | scene | seed | method | state | seconds |
|---|---|---|---|---|---|---|
| Phase52 | D075 | H1 | 221 | CUT-HOLD | NORMAL | 21.944 |
| Phase52 | D075 | H1 | 221 | CUT-HOLD | ALIGN_BRAKE | 0.66667 |
| Phase52 | D075 | H1 | 221 | CUT-HOLD | ALIGN_ROTATE | 0.33333 |
| Phase52 | D075 | H1 | 221 | CUT-HOLD | KEEP_ACTIVE | 1.5556 |
| Phase52 | D075 | H1 | 221 | CUT-HOLD | STOP_WAIT | 0.44444 |
| Phase52 | D075 | H1 | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | NORMAL | 26.069 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | ALIGN_BRAKE | 0.66667 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | ALIGN_ROTATE | 0.22222 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | KEEP_ACTIVE | 1.8889 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | ENDPOINT | 0.11111 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | H1 | 222 | CUT-HOLD | NORMAL | 23.833 |
| Phase52 | D075 | H1 | 222 | CUT-HOLD | ALIGN_BRAKE | 0.66667 |
| Phase52 | D075 | H1 | 222 | CUT-HOLD | ALIGN_ROTATE | 0.33333 |
| Phase52 | D075 | H1 | 222 | CUT-HOLD | ENDPOINT | 0.11111 |
| Phase52 | D075 | H1 | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | H1 | 222 | GRAPH-REC | NORMAL | 25.889 |
| Phase52 | D075 | H1 | 222 | GRAPH-REC | ENDPOINT | 0.22222 |
| Phase52 | D075 | H1 | 222 | GRAPH-REC | ALIGN_BRAKE | 0.55556 |
| Phase52 | D075 | H1 | 222 | GRAPH-REC | ALIGN_ROTATE | 0.33333 |
| Phase52 | D075 | H1 | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D150 | H1 | 221 | CUT-HOLD | NORMAL | 33.139 |
| Phase52 | D150 | H1 | 221 | CUT-HOLD | ALIGN_BRAKE | 3.4444 |
| Phase52 | D150 | H1 | 221 | CUT-HOLD | ALIGN_ROTATE | 16.556 |
| Phase52 | D150 | H1 | 221 | CUT-HOLD | KEEP_ACTIVE | 2.5556 |
| Phase52 | D150 | H1 | 221 | CUT-HOLD | ENDPOINT | 0.22222 |
| Phase52 | D150 | H1 | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | H1 | 221 | GRAPH-REC | NORMAL | 33.306 |
| Phase52 | D150 | H1 | 221 | GRAPH-REC | ALIGN_BRAKE | 1.7778 |
| Phase52 | D150 | H1 | 221 | GRAPH-REC | ALIGN_ROTATE | 3.3333 |
| Phase52 | D150 | H1 | 221 | GRAPH-REC | KEEP_ACTIVE | 1.7778 |
| Phase52 | D150 | H1 | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | H1 | 222 | CUT-HOLD | NORMAL | 22.111 |
| Phase52 | D150 | H1 | 222 | CUT-HOLD | ALIGN_BRAKE | 2.4444 |
| Phase52 | D150 | H1 | 222 | CUT-HOLD | ALIGN_ROTATE | 4.75 |
| Phase52 | D150 | H1 | 222 | CUT-HOLD | ENDPOINT | 0.11111 |
| Phase52 | D150 | H1 | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | H1 | 222 | GRAPH-REC | NORMAL | 27.722 |
| Phase52 | D150 | H1 | 222 | GRAPH-REC | ALIGN_BRAKE | 2.1111 |
| Phase52 | D150 | H1 | 222 | GRAPH-REC | ALIGN_ROTATE | 11.778 |
| Phase52 | D150 | H1 | 222 | GRAPH-REC | ENDPOINT | 0.11111 |
| Phase52 | D150 | H1 | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D075 | H2 | 221 | CUT-HOLD | NORMAL | 82.778 |
| Phase52 | D075 | H2 | 221 | CUT-HOLD | ENDPOINT | 0.33333 |
| Phase52 | D075 | H2 | 221 | CUT-HOLD | ALIGN_BRAKE | 0.55556 |
| Phase52 | D075 | H2 | 221 | CUT-HOLD | ALIGN_ROTATE | 3.4444 |
| Phase52 | D075 | H2 | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | H2 | 221 | GRAPH-REC | NORMAL | 80.111 |
| Phase52 | D075 | H2 | 221 | GRAPH-REC | ENDPOINT | 0.55556 |
| Phase52 | D075 | H2 | 221 | GRAPH-REC | ALIGN_BRAKE | 3.6667 |
| Phase52 | D075 | H2 | 221 | GRAPH-REC | ALIGN_ROTATE | 2.7778 |
| Phase52 | D075 | H2 | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | H2 | 222 | CUT-HOLD | NORMAL | 37.111 |
| Phase52 | D075 | H2 | 222 | CUT-HOLD | ENDPOINT | 0.44444 |
| Phase52 | D075 | H2 | 222 | CUT-HOLD | ALIGN_BRAKE | 1.2222 |
| Phase52 | D075 | H2 | 222 | CUT-HOLD | ALIGN_ROTATE | 1.7778 |
| Phase52 | D075 | H2 | 222 | CUT-HOLD | KEEP_ACTIVE | 0.88889 |
| Phase52 | D075 | H2 | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | H2 | 222 | GRAPH-REC | NORMAL | 79 |
| Phase52 | D075 | H2 | 222 | GRAPH-REC | ALIGN_BRAKE | 3.4444 |
| Phase52 | D075 | H2 | 222 | GRAPH-REC | KEEP_ACTIVE | 0.77778 |
| Phase52 | D075 | H2 | 222 | GRAPH-REC | ALIGN_ROTATE | 3.6667 |
| Phase52 | D075 | H2 | 222 | GRAPH-REC | ENDPOINT | 0.22222 |
| Phase52 | D075 | H2 | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D150 | H2 | 221 | CUT-HOLD | NORMAL | 57.556 |
| Phase52 | D150 | H2 | 221 | CUT-HOLD | ENDPOINT | 0.22222 |
| Phase52 | D150 | H2 | 221 | CUT-HOLD | ALIGN_BRAKE | 5.5556 |
| Phase52 | D150 | H2 | 221 | CUT-HOLD | ALIGN_ROTATE | 23 |
| Phase52 | D150 | H2 | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | H2 | 221 | GRAPH-REC | NORMAL | 44.667 |
| Phase52 | D150 | H2 | 221 | GRAPH-REC | ENDPOINT | 0.11111 |
| Phase52 | D150 | H2 | 221 | GRAPH-REC | ALIGN_BRAKE | 5.3333 |
| Phase52 | D150 | H2 | 221 | GRAPH-REC | ALIGN_ROTATE | 36.222 |
| Phase52 | D150 | H2 | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | H2 | 222 | CUT-HOLD | NORMAL | 49.333 |
| Phase52 | D150 | H2 | 222 | CUT-HOLD | ALIGN_BRAKE | 4.6667 |
| Phase52 | D150 | H2 | 222 | CUT-HOLD | ALIGN_ROTATE | 21 |
| Phase52 | D150 | H2 | 222 | CUT-HOLD | KEEP_ACTIVE | 1.2222 |
| Phase52 | D150 | H2 | 222 | CUT-HOLD | STOP_WAIT | 0.44444 |
| Phase52 | D150 | H2 | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | H2 | 222 | GRAPH-REC | NORMAL | 59 |
| Phase52 | D150 | H2 | 222 | GRAPH-REC | ALIGN_BRAKE | 5.8889 |
| Phase52 | D150 | H2 | 222 | GRAPH-REC | ALIGN_ROTATE | 19.667 |
| Phase52 | D150 | H2 | 222 | GRAPH-REC | ENDPOINT | 0.11111 |
| Phase52 | D150 | H2 | 222 | GRAPH-REC | KEEP_ACTIVE | 1.6667 |
| Phase52 | D150 | H2 | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
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
| Phase52 | D075 | L2 | 222 | CUT-HOLD | NORMAL | 76.444 |
| Phase52 | D075 | L2 | 222 | CUT-HOLD | ENDPOINT | 0.33333 |
| Phase52 | D075 | L2 | 222 | CUT-HOLD | ALIGN_BRAKE | 4 |
| Phase52 | D075 | L2 | 222 | CUT-HOLD | ALIGN_ROTATE | 6.3333 |
| Phase52 | D075 | L2 | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | L2 | 222 | GRAPH-REC | NORMAL | 49.875 |
| Phase52 | D075 | L2 | 222 | GRAPH-REC | ENDPOINT | 0.11111 |
| Phase52 | D075 | L2 | 222 | GRAPH-REC | ALIGN_BRAKE | 2.1111 |
| Phase52 | D075 | L2 | 222 | GRAPH-REC | ALIGN_ROTATE | 7.5556 |
| Phase52 | D075 | L2 | 222 | GRAPH-REC | STOP_WAIT | 0.44444 |
| Phase52 | D075 | L2 | 222 | GRAPH-REC | KEEP_ACTIVE | 0.88889 |
| Phase52 | D075 | L2 | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D150 | L2 | 221 | CUT-HOLD | NORMAL | 18.778 |
| Phase52 | D150 | L2 | 221 | CUT-HOLD | ENDPOINT | 59.889 |
| Phase52 | D150 | L2 | 221 | CUT-HOLD | ALIGN_BRAKE | 1.6667 |
| Phase52 | D150 | L2 | 221 | CUT-HOLD | ALIGN_ROTATE | 5.3333 |
| Phase52 | D150 | L2 | 221 | CUT-HOLD | KEEP_ACTIVE | 0.66667 |
| Phase52 | D150 | L2 | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | L2 | 221 | GRAPH-REC | NORMAL | 36.528 |
| Phase52 | D150 | L2 | 221 | GRAPH-REC | ENDPOINT | 0.22222 |
| Phase52 | D150 | L2 | 221 | GRAPH-REC | ALIGN_BRAKE | 3.8889 |
| Phase52 | D150 | L2 | 221 | GRAPH-REC | ALIGN_ROTATE | 8.3333 |
| Phase52 | D150 | L2 | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | L2 | 222 | CUT-HOLD | NORMAL | 57.111 |
| Phase52 | D150 | L2 | 222 | CUT-HOLD | ENDPOINT | 0.22222 |
| Phase52 | D150 | L2 | 222 | CUT-HOLD | ALIGN_BRAKE | 8 |
| Phase52 | D150 | L2 | 222 | CUT-HOLD | ALIGN_ROTATE | 20.333 |
| Phase52 | D150 | L2 | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | L2 | 222 | GRAPH-REC | NORMAL | 58 |
| Phase52 | D150 | L2 | 222 | GRAPH-REC | ALIGN_BRAKE | 6.7778 |
| Phase52 | D150 | L2 | 222 | GRAPH-REC | ALIGN_ROTATE | 19.667 |
| Phase52 | D150 | L2 | 222 | GRAPH-REC | KEEP_ACTIVE | 1.5556 |
| Phase52 | D150 | L2 | 222 | GRAPH-REC | ENDPOINT | 0.33333 |
| Phase52 | D150 | L2 | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | NORMAL | 23.75 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | ENDPOINT | 0.55556 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | ALIGN_BRAKE | 0.66667 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | ALIGN_ROTATE | 0.22222 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | NORMAL | 50.292 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | ALIGN_BRAKE | 1.8889 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | ALIGN_ROTATE | 3.7778 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | LC | 222 | CUT-HOLD | NORMAL | 25.944 |
| Phase52 | D075 | LC | 222 | CUT-HOLD | ALIGN_BRAKE | 1.1111 |
| Phase52 | D075 | LC | 222 | CUT-HOLD | ALIGN_ROTATE | 0.88889 |
| Phase52 | D075 | LC | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | LC | 222 | GRAPH-REC | NORMAL | 24.667 |
| Phase52 | D075 | LC | 222 | GRAPH-REC | ENDPOINT | 0.33333 |
| Phase52 | D075 | LC | 222 | GRAPH-REC | ALIGN_BRAKE | 0.66667 |
| Phase52 | D075 | LC | 222 | GRAPH-REC | ALIGN_ROTATE | 0.33333 |
| Phase52 | D075 | LC | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D150 | LC | 221 | CUT-HOLD | NORMAL | 26.083 |
| Phase52 | D150 | LC | 221 | CUT-HOLD | ALIGN_BRAKE | 1.6667 |
| Phase52 | D150 | LC | 221 | CUT-HOLD | ALIGN_ROTATE | 3.5556 |
| Phase52 | D150 | LC | 221 | CUT-HOLD | ENDPOINT | 0.11111 |
| Phase52 | D150 | LC | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | LC | 221 | GRAPH-REC | NORMAL | 31.319 |
| Phase52 | D150 | LC | 221 | GRAPH-REC | ALIGN_BRAKE | 2.4444 |
| Phase52 | D150 | LC | 221 | GRAPH-REC | ALIGN_ROTATE | 4.4444 |
| Phase52 | D150 | LC | 221 | GRAPH-REC | ENDPOINT | 0.22222 |
| Phase52 | D150 | LC | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | LC | 222 | CUT-HOLD | NORMAL | 55.556 |
| Phase52 | D150 | LC | 222 | CUT-HOLD | ALIGN_BRAKE | 4.5556 |
| Phase52 | D150 | LC | 222 | CUT-HOLD | ALIGN_ROTATE | 21.306 |
| Phase52 | D150 | LC | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | LC | 222 | GRAPH-REC | NORMAL | 22.542 |
| Phase52 | D150 | LC | 222 | GRAPH-REC | ALIGN_BRAKE | 3 |
| Phase52 | D150 | LC | 222 | GRAPH-REC | ALIGN_ROTATE | 5.7778 |
| Phase52 | D150 | LC | 222 | GRAPH-REC | ENDPOINT | 0.11111 |
| Phase52 | D150 | LC | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
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
| Phase52 | D075 | SLW | 222 | CUT-HOLD | NORMAL | 64.778 |
| Phase52 | D075 | SLW | 222 | CUT-HOLD | KEEP_ACTIVE | 2 |
| Phase52 | D075 | SLW | 222 | CUT-HOLD | ALIGN_BRAKE | 3.2222 |
| Phase52 | D075 | SLW | 222 | CUT-HOLD | ALIGN_ROTATE | 16.111 |
| Phase52 | D075 | SLW | 222 | CUT-HOLD | ENDPOINT | 1 |
| Phase52 | D075 | SLW | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | NORMAL | 72.333 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | ENDPOINT | 0.88889 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | KEEP_ACTIVE | 3.7778 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | STOP_WAIT | 1.3333 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | RECOVER_ROTATE | 2.2222 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | WAIT_FRESH | 0.55556 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | ALIGN_BRAKE | 2.2222 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | ALIGN_ROTATE | 3.7778 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 2.8889 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | NORMAL | 59.333 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | ENDPOINT | 0.66667 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | ALIGN_BRAKE | 2.7778 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | ALIGN_ROTATE | 16.556 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | KEEP_ACTIVE | 3.4444 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | STOP_WAIT | 0.55556 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | RECOVER_ROTATE | 1.7778 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | WAIT_FRESH | 1.2222 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | SLW | 221 | GRAPH-REC | NORMAL | 43.708 |
| Phase52 | D150 | SLW | 221 | GRAPH-REC | ENDPOINT | 0.66667 |
| Phase52 | D150 | SLW | 221 | GRAPH-REC | KEEP_ACTIVE | 1.5556 |
| Phase52 | D150 | SLW | 221 | GRAPH-REC | ALIGN_BRAKE | 2.4444 |
| Phase52 | D150 | SLW | 221 | GRAPH-REC | ALIGN_ROTATE | 14.333 |
| Phase52 | D150 | SLW | 221 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | SLW | 222 | CUT-HOLD | NORMAL | 62.333 |
| Phase52 | D150 | SLW | 222 | CUT-HOLD | ALIGN_BRAKE | 3.3333 |
| Phase52 | D150 | SLW | 222 | CUT-HOLD | STOP_WAIT | 1.2222 |
| Phase52 | D150 | SLW | 222 | CUT-HOLD | ENDPOINT | 1.6667 |
| Phase52 | D150 | SLW | 222 | CUT-HOLD | ALIGN_ROTATE | 17.778 |
| Phase52 | D150 | SLW | 222 | CUT-HOLD | INITIAL_CHUNK_WAIT | 3.6667 |
| Phase52 | D150 | SLW | 222 | GRAPH-REC | NORMAL | 51.111 |
| Phase52 | D150 | SLW | 222 | GRAPH-REC | ENDPOINT | 0.91667 |
| Phase52 | D150 | SLW | 222 | GRAPH-REC | ALIGN_BRAKE | 3.3333 |
| Phase52 | D150 | SLW | 222 | GRAPH-REC | ALIGN_ROTATE | 14.333 |
| Phase52 | D150 | SLW | 222 | GRAPH-REC | STOP_WAIT | 1.2222 |
| Phase52 | D150 | SLW | 222 | GRAPH-REC | KEEP_ACTIVE | 0.77778 |
| Phase52 | D150 | SLW | 222 | GRAPH-REC | INITIAL_CHUNK_WAIT | 3.6667 |
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
| Phase52 | D075 | H1 | 221 | CUT-HOLD | 1 | 19.417 | 16 | 17.986 | True | True | NORMAL |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | 1 | 19.25 | 16 | 17.986 | True | True | NORMAL |
| Phase52 | D075 | H1 | 222 | CUT-HOLD | 1 | 19.931 | 17 | 18.986 | True | True | NORMAL |
| Phase52 | D075 | H1 | 222 | GRAPH-REC | 1 | 20.889 | 17 | 18.986 | True | True | NORMAL |
| Phase52 | D150 | H1 | 221 | CUT-HOLD | 1 | 32.792 | 16 | 29.986 | True | True | NORMAL |
| Phase52 | D150 | H1 | 221 | GRAPH-REC | 1 | 28.917 | 14 | 26.486 | True | True | NORMAL |
| Phase52 | D150 | H1 | 222 | CUT-HOLD | 1 | 26.222 | 12 | 22.986 | True | True | NORMAL |
| Phase52 | D075 | H2 | 221 | CUT-HOLD | 1 | 10 | 7 | 9 | True | True | NORMAL |
| Phase52 | D075 | H2 | 221 | GRAPH-REC | 1 | 10.083 | 7 | 8.9861 | True | True | NORMAL |
| Phase52 | D075 | H2 | 221 | GRAPH-REC | 2 | 49.764 | 46 | 47.986 | True | True | NORMAL |
| Phase52 | D075 | H2 | 222 | CUT-HOLD | 1 | 10.236 | 7 | 8.7361 | True | True | NORMAL |
| Phase52 | D075 | H2 | 222 | CUT-HOLD | 2 | 30.403 | 28 | 29.486 | True | True | NORMAL |
| Phase52 | D075 | H2 | 222 | GRAPH-REC | 1 | 10.958 | 8 | 9.9861 | True | True | NORMAL |
| Phase52 | D150 | H2 | 221 | CUT-HOLD | 1 | 12.778 | 5 | 10.736 | True | True | NORMAL |
| Phase52 | D150 | H2 | 221 | GRAPH-REC | 1 | 12.736 | 5 | 10.736 | True | True | NORMAL |
| Phase52 | D150 | H2 | 222 | CUT-HOLD | 1 | 13.458 | 5 | 10.736 | True | True | NORMAL |
| Phase52 | D150 | H2 | 222 | CUT-HOLD | 2 | 52.417 | 27 | 49.236 | True | True | NORMAL |
| Phase52 | D150 | H2 | 222 | GRAPH-REC | 1 | 10.75 | 4 | 8.9861 | True | True | NORMAL |
| Phase52 | D150 | H2 | 222 | GRAPH-REC | 2 | 80.931 | 44 | 78.986 | True | True | NORMAL |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | 1 | 10 | 7 | 8.9861 | True | True | NORMAL |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | 1 | 10.069 | 7 | 8.9861 | True | True | NORMAL |
| Phase52 | D075 | L2 | 222 | CUT-HOLD | 1 | 11.125 | 8 | 9.9861 | True | True | NORMAL |
| Phase52 | D075 | L2 | 222 | GRAPH-REC | 1 | 11.236 | 8 | 9.9861 | True | True | NORMAL |
| Phase52 | D150 | L2 | 221 | CUT-HOLD | 1 | 12.792 | 5 | 10.736 | True | True | NORMAL |
| Phase52 | D150 | L2 | 221 | GRAPH-REC | 1 | 12.736 | 5 | 10.736 | True | True | NORMAL |
| Phase52 | D150 | L2 | 222 | CUT-HOLD | 1 | 14.125 | 6 | 12.486 | True | True | NORMAL |
| Phase52 | D150 | L2 | 222 | GRAPH-REC | 1 | 10.736 | 4 | 8.9861 | True | True | NORMAL |
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
| Phase52 | D075 | H1 | 221 | CUT-HOLD | 1.5556 | 1.5556 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | H1 | 221 | GRAPH-REC | 1.8889 | 1.8889 | 29 | 4 | 0.13793 | 0.13187 | 0.22308 | [0.318530736, 0.21563084, 0.15537196, 0.228038282, 0.133878122, 0.131214009, 0.132284302, 0.143157565, 0.130544835, 0.126097318, 0.131768963, 0.145407383, 0.12978032, 0.137726977, 0.127321709, 0.13292267, 0.131181638, 0.131868199, 0.125630675, 0.129466738, 0.129876651, 0.167086531, 0.186574677, 0.141260431, 0.130423419, 0.118424027, 0.131561793, 0.134686759, 0.116604868] | {'ACCEPTED': 4, 'REJECTED': 25} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.027160493827159918, 0.0] | 0 | 0 |
| Phase52 | D075 | H1 | 222 | CUT-HOLD | 0 | 0 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | H1 | 222 | GRAPH-REC | 0 | 0 | 27 | 5 | 0.18519 | 0.131 | 0.19418 | [0.169541863, 0.291143501, 0.161290145, 0.201550708, 0.128416596, 0.12953464, 0.124189039, 0.130431072, 0.159460745, 0.130800017, 0.176973724, 0.133823874, 0.127211149, 0.149426506, 0.144963009, 0.138698555, 0.141229104, 0.115344571, 0.128325286, 0.140557616, 0.127903585, 0.135529266, 0.125780331, 0.124670786, 0.126635814, 0.122458991, 0.131000938] | {'ACCEPTED': 5, 'REJECTED': 22} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.006653504602153677, 0.0, 0.017684771017089554, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D150 | H1 | 221 | CUT-HOLD | 4.8889 | 3.4444 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | H1 | 221 | GRAPH-REC | 1.7778 | 1.7778 | 23 | 6 | 0.26087 | 0.14714 | 0.18818 | [0.178495817, 0.224047353, 0.171512042, 0.18884262, 0.166805863, 0.147138825, 0.120956476, 0.166828083, 0.119740125, 0.182166925, 0.140838658, 0.139079209, 0.136347337, 0.128055674, 0.135564034, 0.125185881, 0.13118552, 0.159267753, 0.168961985, 0.16582054, 0.168203745, 0.13705371, 0.125918104] | {'ACCEPTED': 6, 'REJECTED': 17} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.016864784292073297, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D150 | H1 | 222 | CUT-HOLD | 0 | 0 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | H1 | 222 | GRAPH-REC | 0 | 0 | 24 | 8 | 0.33333 | 0.13356 | 0.16489 | [0.17943776, 0.143621461, 0.147803702, 0.132761762, 0.13328514, 0.132904382, 0.118161388, 0.132940125, 0.12400014, 0.133865728, 0.129416803, 0.116108834, 0.152250149, 0.120711439, 0.134324003, 0.151924606, 0.134456885, 0.167029867, 0.112776637, 0.13382924, 0.119256752, 0.152777366, 0.129381014, 0.152499361] | {'ACCEPTED': 8, 'REJECTED': 16} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.018512930534686462, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D075 | H2 | 221 | CUT-HOLD | 1 | 1 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | H2 | 221 | GRAPH-REC | 0 | 0 | 88 | 20 | 0.22727 | 0.13717 | 0.1921 | [0.251719983, 0.271670637, 0.158780505, 0.135446572, 0.121920367, 0.132134098, 0.127891275, 0.130865578, 0.128611976, 0.120269282, 0.177284606, 0.137705489, 0.166769354, 0.123279605, 0.133104187, 0.178130698, 0.122920183, 0.126641837, 0.14231237, 0.167214926, 0.130611843, 0.167602174, 0.128112334, 0.131677141, 0.119004006, 0.13720112, 0.14796136, 0.15932678, 0.132782654, 0.116390982, 0.20440289, 0.159196857, 0.125648709, 0.169390922, 0.172165767, 0.211513139, 0.16447929, 0.121477974, 0.127708366, 0.126602735, 0.12971429, 0.138376473, 0.128426513, 0.134153278, 0.130277292, 0.120190652, 0.128433198, 0.134967778, 0.137133094, 0.126858497, 0.14262848, 0.126627188, 0.132049885, 0.179974141, 0.135726394, 0.185090477, 0.16671297, 0.147685706, 0.159732834, 0.131926064, 0.12942478, 0.131553426, 0.13057632, 0.118050694, 0.119697785, 0.174730004, 0.139238917, 0.162765905, 0.18175108, 0.170777705, 0.133260176, 0.19549197, 0.137639861, 0.137378976, 0.139115687, 0.134734491, 0.130693421, 0.129768052, 0.141228255, 0.148498384, 0.140398168, 0.18580202, 0.179417275, 0.169315755, 0.140632686, 0.166331344, 0.136646751, 0.141084908] | {'REJECTED': 67, 'ACCEPTED': 20} | [0.0, 0.060493827051973766, 0.19334040883322037, 0.0, 0.0, 0.0, 0.060493824378008716, 0.0, 0.019142475781739356, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 1 | 0 |
| Phase52 | D075 | H2 | 222 | CUT-HOLD | 0.88889 | 0.88889 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | H2 | 222 | GRAPH-REC | 0.77778 | 0.77778 | 88 | 40 | 0.45455 | 0.13691 | 0.17591 | [0.138496209, 0.136203005, 0.13261028, 0.125026748, 0.123879569, 0.121534525, 0.121103334, 0.125301879, 0.122085177, 0.113008554, 0.136366427, 0.123419037, 0.125700143, 0.209502953, 0.124262192, 0.184123554, 0.149599629, 0.157013779, 0.161212322, 0.141102596, 0.151809479, 0.135370896, 0.125561765, 0.158847239, 0.128945118, 0.185826127, 0.160711165, 0.173830527, 0.11985226, 0.147332304, 0.130299851, 0.172904504, 0.114164593, 0.141463526, 0.129034999, 0.17239367, 0.13699818, 0.168104124, 0.132998022, 0.15234041, 0.171069538, 0.169576264, 0.161171968, 0.133384515, 0.162268301, 0.14353458, 0.151178809, 0.125797875, 0.13435035, 0.132328781, 0.147296232, 0.137430888, 0.113906046, 0.136822143, 0.140454646, 0.177740424, 0.163195441, 0.115656673, 0.163798535, 0.115744278, 0.121436481, 0.129875738, 0.127194179, 0.156156608, 0.130127385, 0.119354298, 0.13655474, 0.174093707, 0.120031394, 0.164875717, 0.147095588, 0.130968818, 0.176882004, 0.146582474, 0.134749181, 0.13838009, 0.141541736, 0.113882926, 0.121758236, 0.139465968, 0.135140781, 0.16553777, 0.126769001, 0.152611913, 0.1342862, 0.168447725, 0.136130953, 0.139271259] | {'REJECTED': 47, 'ACCEPTED': 40} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.01914247578173739, 0.018157382679623565, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 1 | 0 |
| Phase52 | D150 | H2 | 221 | CUT-HOLD | 3.4444 | 3.4444 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | H2 | 221 | GRAPH-REC | 8.5556 | 2.5556 | 50 | 17 | 0.34 | 0.15433 | 0.23505 | [0.139064986, 0.275281328, 0.14439262, 0.131571524, 0.1299794, 0.127193956, 0.139600205, 0.121867578, 0.14963047, 0.14608778, 0.223654523, 0.210150888, 0.244367664, 0.165233056, 0.207725876, 0.189492344, 0.166033656, 0.18234792, 0.275405644, 0.172967732, 0.178116685, 0.151095028, 0.178418492, 0.154942247, 0.189777923, 0.181216219, 0.1396178, 0.136487412, 0.163966063, 0.143310651, 0.184792702, 0.144323773, 0.1755628, 0.133987573, 0.125523136, 0.154181559, 0.154482281, 0.143229586, 0.132540582, 0.125680617, 0.134311041, 0.171303321, 0.121531548, 0.16316283, 0.131761492, 0.143279576, 0.163479007, 0.174998314, 0.127312671, 0.171297896] | {'REJECTED': 20, 'ACCEPTED': 17, 'EXEC_CERT_REJECT': 12} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 1 | 0 |
| Phase52 | D150 | H2 | 222 | CUT-HOLD | 3 | 1.7778 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | H2 | 222 | GRAPH-REC | 3.4444 | 1.7778 | 50 | 21 | 0.42 | 0.14542 | 0.21968 | [0.18208841, 0.163934717, 0.130614264, 0.13229942, 0.120873479, 0.122309385, 0.159883502, 0.125910636, 0.12736733, 0.121037445, 0.155305467, 0.14187116, 0.179161384, 0.147254491, 0.14413164, 0.141828371, 0.162358939, 0.1339724, 0.156773347, 0.121199473, 0.191428554, 0.126375337, 0.146482986, 0.167299938, 0.136015204, 0.188735221, 0.121214929, 0.135605413, 0.120608679, 0.14474594, 0.165334605, 0.158256109, 0.216970724, 0.22188801, 0.23150686, 0.138064148, 0.205636621, 0.150122104, 0.340145616, 0.115839589, 0.137923707, 0.179812012, 0.137448537, 0.129084055, 0.177623844, 0.134544708, 0.161145185, 0.131342337, 0.146098364, 0.146094246] | {'REJECTED': 25, 'ACCEPTED': 21, 'EXEC_CERT_REJECT': 3} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0036236341893544953, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 1 | 0 |
| Phase52 | D075 | L2 | 221 | CUT-HOLD | 1 | 1 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | L2 | 221 | GRAPH-REC | 0.77778 | 0.77778 | 17 | 2 | 0.11765 | 0.13774 | 0.22433 | [0.242028878, 0.219901523, 0.148419345, 0.137739926, 0.125906137, 0.130348896, 0.124662169, 0.130204865, 0.137992979, 0.135973721, 0.150399676, 0.128556961, 0.124264441, 0.132244592, 0.144815771, 0.158711888, 0.141693004] | {'REJECTED': 13, 'ACCEPTED': 2, 'EXEC_CERT_REJECT': 1} | [0.0, 0.06049382692643623, 0.19334040883322062, 0.0, 0.0, 0.0, 0.06049380652907654, 0.0, 0.01914247578173889, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 1 | 0 |
| Phase52 | D075 | L2 | 222 | CUT-HOLD | 2 | 1 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | L2 | 222 | GRAPH-REC | 2.8889 | 1 | 61 | 17 | 0.27869 | 0.14053 | 0.17665 | [0.136652325, 0.133592723, 0.211364439, 0.12025277, 0.122612283, 0.121902925, 0.118024593, 0.125496913, 0.125573625, 0.116805509, 0.122277087, 0.137217142, 0.125153347, 0.173186794, 0.116260514, 0.141480011, 0.153814313, 0.160464869, 0.158136752, 0.121883785, 0.146977621, 0.162851243, 0.157231404, 0.195858931, 0.176651579, 0.15162293, 0.162354959, 0.152746828, 0.134861474, 0.160969447, 0.133415477, 0.170659878, 0.159482539, 0.166558255, 0.126984244, 0.133743888, 0.140365682, 0.154939211, 0.142403055, 0.174394899, 0.144310477, 0.162399135, 0.164100743, 0.165213687, 0.190789312, 0.150439827, 0.158788453, 0.165697781, 0.152939249, 0.129026545, 0.128715995, 0.137253566, 0.118326303, 0.11881719, 0.128983235, 0.131983527, 0.12980627, 0.140534204, 0.136149849, 0.132537273, 0.129533872] | {'REJECTED': 37, 'ACCEPTED': 17, 'EXEC_CERT_REJECT': 7} | [0.0, 0.0, 0.0, 0.012525174215424519, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.01447684793587636, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.01110889911304388, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D150 | L2 | 221 | CUT-HOLD | 0.66667 | 0.44444 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | L2 | 221 | GRAPH-REC | 0 | 0 | 28 | 3 | 0.10714 | 0.13462 | 0.173 | [0.145455519, 0.199953367, 0.142851601, 0.127451955, 0.120927534, 0.131415769, 0.127547758, 0.128061502, 0.152282924, 0.125548002, 0.169583493, 0.139102692, 0.174834762, 0.133497478, 0.139510301, 0.137004902, 0.13891739, 0.162519441, 0.122596669, 0.13618155, 0.125594524, 0.132388743, 0.135487377, 0.133346609, 0.130199436, 0.139905097, 0.125530178, 0.133745659] | {'REJECTED': 25, 'ACCEPTED': 3} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.01851178091475453, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D150 | L2 | 222 | CUT-HOLD | 1.7778 | 1.7778 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | L2 | 222 | GRAPH-REC | 1.5556 | 0.77778 | 50 | 25 | 0.5 | 0.15024 | 0.2013 | [0.138149717, 0.247223599, 0.129984394, 0.120251638, 0.135911285, 0.126880933, 0.171557224, 0.119727043, 0.174974743, 0.174614336, 0.21164956, 0.175479131, 0.193759117, 0.195347766, 0.187753728, 0.206178084, 0.14206397, 0.148351715, 0.183527482, 0.171507909, 0.176479971, 0.125951301, 0.173507421, 0.126683009, 0.145004331, 0.173996466, 0.168645697, 0.134581491, 0.187770293, 0.137867945, 0.131531289, 0.132833642, 0.125437965, 0.143981435, 0.116687148, 0.122092862, 0.173303281, 0.179465109, 0.1446585, 0.147306056, 0.152128209, 0.147968827, 0.124840621, 0.174178915, 0.137731893, 0.136542232, 0.160999155, 0.18160371, 0.166886012, 0.152914386] | {'REJECTED': 24, 'ACCEPTED': 25} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 1 | 0 |
| Phase52 | D075 | LC | 221 | CUT-HOLD | 0 | 0 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | LC | 221 | GRAPH-REC | 0 | 0 | 56 | 13 | 0.23214 | 0.13025 | 0.16673 | [0.219337065, 0.181322011, 0.124776247, 0.161862866, 0.128355123, 0.13465932, 0.119347366, 0.128278683, 0.130152017, 0.123570196, 0.129223984, 0.122676439, 0.13350093, 0.146060529, 0.114405876, 0.133590118, 0.148581644, 0.131443075, 0.145845962, 0.123493058, 0.13582444, 0.159751983, 0.127806873, 0.137195036, 0.13722846, 0.129284956, 0.124524731, 0.115866687, 0.128542559, 0.118313941, 0.158503756, 0.159655565, 0.139475041, 0.151177846, 0.128651852, 0.129733477, 0.13244558, 0.13922103, 0.188413936, 0.119488846, 0.124377525, 0.127165304, 0.135781254, 0.125650867, 0.128552072, 0.129102557, 0.130729698, 0.134533225, 0.128375199, 0.131649911, 0.130342652, 0.118590553, 0.145293364, 0.133669272, 0.129475875, 0.120694766] | {'ACCEPTED': 13, 'REJECTED': 43} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D075 | LC | 222 | CUT-HOLD | 0 | 0 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | LC | 222 | GRAPH-REC | 0 | 0 | 26 | 2 | 0.076923 | 0.12859 | 0.1713 | [0.165529236, 0.363255826, 0.143889666, 0.1317442, 0.137623874, 0.134305968, 0.120948086, 0.124280621, 0.173227379, 0.12834743, 0.129936766, 0.119363082, 0.119980739, 0.128836446, 0.129938319, 0.126283667, 0.125920638, 0.123860785, 0.131538786, 0.122646172, 0.121105914, 0.121903382, 0.135238623, 0.130630522, 0.118640371, 0.123361553] | {'ACCEPTED': 2, 'REJECTED': 24} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.027160493827161312, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.056836514047033264, 0.0] | 0 | 0 |
| Phase52 | D150 | LC | 221 | CUT-HOLD | 0 | 0 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | LC | 221 | GRAPH-REC | 0 | 0 | 22 | 6 | 0.27273 | 0.14445 | 0.21323 | [0.183860235, 0.241493184, 0.171139166, 0.194430223, 0.214214697, 0.15185185, 0.144625416, 0.163131349, 0.133547849, 0.186854151, 0.143704335, 0.132165977, 0.133600986, 0.12769262, 0.14428235, 0.124521118, 0.122607139, 0.134827683, 0.163163958, 0.12155506, 0.159662473, 0.132916896] | {'ACCEPTED': 6, 'REJECTED': 16} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D150 | LC | 222 | CUT-HOLD | 0 | 0 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | LC | 222 | GRAPH-REC | 0 | 0 | 18 | 4 | 0.22222 | 0.13374 | 0.18587 | [0.18064816, 0.187524591, 0.142549592, 0.18557952, 0.149624972, 0.134852561, 0.161890507, 0.132165142, 0.130851865, 0.135337445, 0.131324904, 0.138019842, 0.132628897, 0.119926739, 0.126649168, 0.128757115, 0.130681222, 0.128867477] | {'ACCEPTED': 4, 'REJECTED': 14} | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D075 | SLW | 221 | CUT-HOLD | 6.2222 | 2.1111 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | SLW | 221 | GRAPH-REC | 0 | 0 | 63 | 10 | 0.15873 | 0.13287 | 0.16934 | [0.320167115, 0.198386133, 0.130049043, 0.167126312, 0.121935849, 0.133214734, 0.119236406, 0.139583705, 0.163057946, 0.151637777, 0.140008586, 0.134007807, 0.117931216, 0.135735004, 0.117536723, 0.120377814, 0.125515339, 0.121211453, 0.131324595, 0.1475422, 0.123869428, 0.158299708, 0.127012046, 0.128549079, 0.129670282, 0.153984262, 0.123911859, 0.117439043, 0.121899366, 0.130935114, 0.121858424, 0.154846897, 0.13325053, 0.126234421, 0.124706361, 0.132865504, 0.128487937, 0.211699008, 0.112346947, 0.153062218, 0.125714849, 0.152826491, 0.133280909, 0.135480515, 0.124710531, 0.124095428, 0.130182966, 0.143633418, 0.148624118, 0.168786991, 0.144061565, 0.126306036, 0.169405593, 0.124748569, 0.142270415, 0.134888835, 0.119228625, 0.135213355, 0.126461762, 0.118964663, 0.143198546, 0.153035369, 0.138513678] | {'ACCEPTED': 10, 'REJECTED': 51, 'RECOVERY_ACTIVE': 2} | [0.0, 0.0, 0.0, 0.0, 0.02463885957755361, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.011107453493409827, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D075 | SLW | 222 | CUT-HOLD | 9 | 5 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D075 | SLW | 222 | GRAPH-REC | 3.7778 | 1 | 88 | 15 | 0.17045 | 0.12733 | 0.17057 | [0.173689157, 0.27433492, 0.129724766, 0.19475033, 0.140179722, 0.126479086, 0.121542902, 0.123837806, 0.125824363, 0.12802197, 0.136527943, 0.127903987, 0.125575531, 0.120310171, 0.122819493, 0.121921355, 0.125912413, 0.126575705, 0.115740225, 0.126822715, 0.113064829, 0.117179683, 0.127578643, 0.1113714, 0.125826452, 0.133247763, 0.127090406, 0.133608359, 0.124145649, 0.15083925, 0.167776192, 0.141525003, 0.116198441, 0.153035788, 0.121368652, 0.136987477, 0.123573945, 0.14364757, 0.126761376, 0.115718972, 0.16207643, 0.163499777, 0.170825185, 0.165253191, 0.153273505, 0.132867819, 0.126423677, 0.114668587, 0.124434285, 0.134079845, 0.134843547, 0.123249895, 0.119155741, 0.123003186, 0.122263931, 0.131255367, 0.128430777, 0.127659371, 0.126581431, 0.128302113, 0.118888806, 0.128607896, 0.149322331, 0.145410544, 0.121719079, 0.12268774, 0.120981797, 0.133207313, 0.122172683, 0.121949358, 0.117590451, 0.123035564, 0.128340902, 0.127575116, 0.123505389, 0.120885157, 0.121175178, 0.123315157, 0.128827879, 0.167877878, 0.155312758, 0.170093904, 0.138111904, 0.145480595, 0.141512881, 0.174970869, 0.122517606, 0.135645342] | {'ACCEPTED': 15, 'REJECTED': 72} | [0.0, 0.0, 0.0, 0.01851293053468655, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.007668453930107693, 0.0, 0.0, 0.0, 0.0, 0.0013119491957095705, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.009423888869170689, 0.02032870579968804, 0.0, 0.0, 0.027160493827160972, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.008495458520444359, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.02716049382716053, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 1 | 0 |
| Phase52 | D150 | SLW | 221 | CUT-HOLD | 3.4444 | 1.7778 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | SLW | 221 | GRAPH-REC | 1.5556 | 1.5556 | 36 | 7 | 0.19444 | 0.13748 | 0.21053 | [0.180143529, 0.243240393, 0.140651343, 0.170605163, 0.136409868, 0.122178731, 0.136612102, 0.124695508, 0.129741471, 0.126305163, 0.131069426, 0.141189887, 0.138286572, 0.131463294, 0.138953368, 0.115713053, 0.121301166, 0.125498999, 0.145786974, 0.121141705, 0.209213059, 0.125892557, 0.184900887, 0.121834717, 0.142746745, 0.132817008, 0.214462865, 0.161629835, 0.134131434, 0.153290778, 0.13871692, 0.154244414, 0.154534107, 0.141129523, 0.122726488, 0.136667207] | {'ACCEPTED': 7, 'REJECTED': 28, 'EXEC_CERT_REJECT': 1} | [0.0, 0.0, 0.0185129305346872, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0002755032451620072, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
| Phase52 | D150 | SLW | 222 | CUT-HOLD | 1.7778 | 1.7778 | 0 | 0 | — | — | — | [] | {} | [] | 0 | 0 |
| Phase52 | D150 | SLW | 222 | GRAPH-REC | 0.77778 | 0.77778 | 41 | 11 | 0.26829 | 0.13707 | 0.17799 | [0.177993816, 0.186533752, 0.136270062, 0.159762939, 0.148437332, 0.137256137, 0.137072085, 0.119878049, 0.143918003, 0.154271486, 0.153777829, 0.150821718, 0.124195243, 0.123851528, 0.122086617, 0.124348253, 0.169946521, 0.133979327, 0.116961961, 0.167341634, 0.175177284, 0.137474546, 0.165660475, 0.120850404, 0.140817334, 0.130416296, 0.117493513, 0.129268103, 0.141437031, 0.122030586, 0.132999596, 0.184092166, 0.14035344, 0.135969771, 0.129034649, 0.129658781, 0.130937622, 0.151563455, 0.123406998, 0.13004169, 0.14121016] | {'ACCEPTED': 11, 'REJECTED': 29, 'EXEC_CERT_REJECT': 1} | [0.0, 0.0, 0.0, 0.0, 0.02716049382715968, 0.0, 0.0, 0.0, 0.0, 0.011107814052193713, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | 0 | 0 |
