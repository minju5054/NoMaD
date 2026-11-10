| status | completed | planned | protocol_sha256 |
|---|---|---|---|
| COMPLETE | 12 | 12 | e2dc1f876327ebe8079bbe736ced947e5ac0a3acfd95cad6513a181be1117109 |

| item | definition |
|---|---|
| success | Declared arrival with actual distance<=0.5m AND no person/static/wall collision;Phase47 stop unchanged |
| distance | Report robot-person center distance and surface clearance=center distance-0.09-0.20;only while person exists;N/A if not spawned |
| collision | Frozen static/wall evaluation,plus certified relative-motion circle sweep at72Hz;conservative contact stops distinguished from witnessed overlap |
| stop_s | Time-weighted actual /v/<0.01m/s;full run and person-present interval |
| slow_s | Time-weighted actual 0.01<=v<0.3m/s;separately decreasing-v duration and EC0.1 cap duration;not a causal attribution |
| EC | All EC records in [first contact-2s,first contact],including CHECK result and periodic application;no invented record if no check |
| removal | One crossing;surface within0.05m of opposite wall,then hidden and removed from collision monitor;exact removal time/position/robot distance |
| ghosts | Per retained live publication after removal through+5s: occupied cells intersecting removed disk and swept capsule;also exclude pre-spawn occupied baseline;no map writes |
| ghost_time | Bin by depth capture simulation time;log sampling and publication times. If run ends early or no map is available,report coverage/missing,never zero-fill |
| ghost_attribution | Geometric residual-occupancy counts,not semantic proof of person cells;noise/mapping remain frozen |
| scope | 12 descriptive runs;no hypothesis gate,smoke,simulation,inference or render during preparation;static geometry/materials and reference hashes frozen |

| condition | n | valid | technical_failure | success_0p5 | collision | person_collision | wrong_stop | person_spawned | min_person_center_distance_m | min_person_surface_clearance_m | stopped_median_s | slow_moving_median_s | decelerating_median_s | ec_slow_cap_median_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1_V050 | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 3 | 1.6756 | 1.3856 | 4.2222 | 15.722 | 0.95833 | 0 |
| H1_V100 | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 3 | 1.8032 | 1.5132 | 3.4444 | 15.056 | 0.73611 | 0 |
| L2_V050 | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 3 | 1.2909 | 1.0009 | 3.3333 | 18.056 | 1.2083 | 0 |
| L2_V100 | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 3 | 1.5588 | 1.2688 | 3.3333 | 18.583 | 1.2639 | 0 |

| condition | seed | technical_validation | success | collision | person_collision | wrong_stop | stop_distance_m | minimum_person_center_distance_m | minimum_person_clearance_m | goal_time_s | stopped_s | slow_moving_s | decelerating_s | ec_slow_cap_s | ec_reject_stopped_s | ec_checks | ec_rejects | person_spawned | spawn_reference_remaining_m | post_removal_5s_available | ghost_last_offset_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1_V050 | 221 | PASS | True | False | False | False | 0.25345 | 1.6756 | 1.3856 | 27.833 | 4.2222 | 12.389 | 0.55556 | 0 | 0 | 73 | 0 | True | 2.031 | True | 4.8572 |
| H1_V050 | 222 | PASS | True | False | False | False | 0.24714 | 1.3279 | 1.0379 | 30.833 | 4.2222 | 19.167 | 1.2778 | 0 | 0 | 85 | 2 | True | 1.8453 | True | 4.9304 |
| H1_V050 | 223 | PASS | True | False | False | False | 0.34443 | 1.9939 | 1.7039 | 29.389 | 4.4444 | 15.722 | 0.95833 | 0 | 0 | 80 | 2 | True | 2.0918 | True | 4.8185 |
| H1_V100 | 221 | PASS | True | False | False | False | 0.33573 | 1.8032 | 1.5132 | 28.833 | 3.5556 | 15.056 | 0.73611 | 0.44444 | 0 | 84 | 10 | True | 2.0294 | True | 4.873 |
| H1_V100 | 222 | PASS | True | False | False | False | 0.37315 | 1.4643 | 1.1743 | 25.583 | 3.2222 | 11.806 | 0.63889 | 0 | 0 | 68 | 1 | True | 1.8756 | True | 4.986 |
| H1_V100 | 223 | PASS | True | False | False | False | 0.42417 | 1.955 | 1.665 | 30.583 | 3.4444 | 18.917 | 0.97222 | 0 | 0 | 82 | 0 | True | 2.0914 | True | 4.8537 |
| L2_V050 | 221 | PASS | True | False | False | False | 0.32787 | 1.3339 | 1.0439 | 34.833 | 2.8889 | 14.389 | 0.83333 | 0 | 0 | 94 | 0 | True | 2.3585 | True | 4.8584 |
| L2_V050 | 222 | PASS | True | False | False | False | 0.44321 | 1.2909 | 1.0009 | 38.583 | 4.3333 | 20.25 | 1.375 | 0 | 0 | 106 | 0 | True | 1.8083 | True | 4.9871 |
| L2_V050 | 223 | PASS | True | False | False | False | 0.34434 | 1.0474 | 0.75738 | 35.833 | 3.3333 | 18.056 | 1.2083 | 0 | 0 | 97 | 0 | True | 1.6725 | True | 4.8607 |
| L2_V100 | 221 | PASS | True | False | False | False | 0.36513 | 1.9324 | 1.6424 | 35.889 | 3.4444 | 16.222 | 1.0556 | 0 | 0 | 98 | 0 | True | 2.3605 | True | 4.9848 |
| L2_V100 | 222 | PASS | True | False | False | False | 0.44818 | 1.5588 | 1.2688 | 37.833 | 3.3333 | 18.722 | 1.375 | 0 | 0 | 104 | 0 | True | 1.8063 | True | 4.9033 |
| L2_V100 | 223 | PASS | True | False | False | False | 0.42424 | 1.3198 | 1.0298 | 35.583 | 2.8889 | 18.583 | 1.2639 | 0 | 0 | 97 | 0 | True | 1.6741 | True | 4.8679 |

| condition | seed | removed | simulation_time_s | recorded_at_tick | person_center_xy_m | robot_pose | center_distance_m | footprint_clearance_m | surface_wall_gap_m | reason | one_crossing |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1_V050 | 221 | True | 20.879 | 1504 | [3.95, 2.7] | [2.8708584917970694, 1.3977380975059015, 1.5855195455289355] | 1.6913 | 1.4013 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| H1_V050 | 222 | True | 20.806 | 1499 | [2.65, 2.7] | [2.9469956446349532, 1.37590788311963, 1.499956710975975] | 1.357 | 1.067 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| H1_V050 | 223 | True | 18.918 | 1363 | [3.95, 2.7] | [2.803164022511102, 0.7907430142874827, 1.135942651619109] | 2.2272 | 1.9372 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| H1_V100 | 221 | True | 18.863 | 1359 | [3.95, 2.7] | [2.6920416186236538, 1.1861089005850225, 1.5616827882636386] | 1.9683 | 1.6783 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| H1_V100 | 222 | True | 18.25 | 1315 | [2.65, 2.7] | [2.809180085193372, 1.2443332284232904, 1.5596981785600796] | 1.4643 | 1.1743 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| H1_V100 | 223 | True | 20.882 | 1504 | [3.95, 2.7] | [2.7477321289310352, 0.9853264507570973, 1.2011056772332136] | 2.0942 | 1.8042 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| L2_V050 | 221 | True | 11.878 | 856 | [3.5, 1.25] | [2.5439422339285, 0.2761142125721039, 0.2881072928198529] | 1.3647 | 1.0747 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| L2_V050 | 222 | True | 14.249 | 1026 | [3.5, -1.25] | [2.455519201816624, 0.1879837386913229, 0.13159985276951724] | 1.7773 | 1.4873 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| L2_V050 | 223 | True | 14.375 | 1036 | [3.5, 1.25] | [2.965245340617885, 0.07671401231496876, 0.05361569505441688] | 1.2894 | 0.9994 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| L2_V100 | 221 | True | 9.5013 | 685 | [3.5, 1.25] | [1.8122712520240494, 0.13140555672853466, 0.0201778350385311] | 2.0248 | 1.7348 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| L2_V100 | 222 | True | 11.833 | 852 | [3.5, -1.25] | [2.235349745724099, 0.14103294108494993, -0.10070710359790169] | 1.88 | 1.59 | 0.05 | OPPOSITE_EDGE_0P05M | True |
| L2_V100 | 223 | True | 11.868 | 855 | [3.5, 1.25] | [2.4116162659192035, 0.07665613729377867, 0.05044019193539384] | 1.6004 | 1.3104 | 0.05 | OPPOSITE_EDGE_0P05M | True |

| condition | seed | after_removal_bin_s | snapshots | observation_available_s | endpoint_occupied_cells_median | endpoint_occupied_cells_max | endpoint_occupied_cells_last | endpoint_new_occupied_cells_median | endpoint_new_occupied_cells_max | endpoint_new_occupied_cells_last | swept_trail_occupied_cells_median | swept_trail_occupied_cells_max | swept_trail_occupied_cells_last | swept_trail_new_occupied_cells_median | swept_trail_new_occupied_cells_max | swept_trail_new_occupied_cells_last |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1_V050 | 221 | 0-1 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 17 | 3 | 3 | 17 | 3 |
| H1_V050 | 221 | 1-2 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2.5 | 3 | 0 | 2.5 | 3 | 0 |
| H1_V050 | 221 | 2-3 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 221 | 3-4 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 221 | 4-5 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 222 | 0-1 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 6.5 | 20 | 0 | 6.5 | 20 | 0 |
| H1_V050 | 222 | 1-2 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 222 | 2-3 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 222 | 3-4 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 222 | 4-5 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 223 | 0-1 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1.5 | 20 | 0 | 1.5 | 20 | 0 |
| H1_V050 | 223 | 1-2 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 223 | 2-3 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 223 | 3-4 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V050 | 223 | 4-5 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 221 | 0-1 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 7 | 0 | 2 | 7 | 0 |
| H1_V100 | 221 | 1-2 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 221 | 2-3 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 221 | 3-4 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 221 | 4-5 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 222 | 0-1 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 222 | 1-2 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 222 | 2-3 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 222 | 3-4 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 222 | 4-5 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 223 | 0-1 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 223 | 1-2 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 223 | 2-3 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 223 | 3-4 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H1_V100 | 223 | 4-5 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L2_V050 | 221 | 0-1 | 4 | 1 | 9 | 9 | 9 | 4 | 4 | 4 | 15 | 20 | 15 | 10 | 15 | 10 |
| L2_V050 | 221 | 1-2 | 4 | 1 | 9 | 9 | 9 | 4 | 4 | 4 | 15 | 15 | 15 | 10 | 10 | 10 |
| L2_V050 | 221 | 2-3 | 4 | 1 | 9 | 9 | 9 | 4 | 4 | 4 | 15 | 15 | 15 | 10 | 10 | 10 |
| L2_V050 | 221 | 3-4 | 4 | 1 | 9 | 9 | 9 | 4 | 4 | 4 | 15 | 15 | 15 | 10 | 10 | 10 |
| L2_V050 | 221 | 4-5 | 4 | 1 | 9 | 9 | 9 | 4 | 4 | 4 | 15 | 15 | 15 | 10 | 10 | 10 |
| L2_V050 | 222 | 0-1 | 4 | 1 | 39 | 39 | 39 | 10 | 10 | 10 | 39.5 | 41 | 39 | 10.5 | 12 | 10 |
| L2_V050 | 222 | 1-2 | 4 | 1 | 39 | 39 | 39 | 10 | 10 | 10 | 39 | 39 | 39 | 10 | 10 | 10 |
| L2_V050 | 222 | 2-3 | 4 | 1 | 39 | 39 | 39 | 10 | 10 | 10 | 39 | 39 | 39 | 10 | 10 | 10 |
| L2_V050 | 222 | 3-4 | 4 | 1 | 39 | 39 | 39 | 10 | 10 | 10 | 39 | 39 | 39 | 10 | 10 | 10 |
| L2_V050 | 222 | 4-5 | 4 | 1 | 39 | 39 | 39 | 10 | 10 | 10 | 39 | 39 | 39 | 10 | 10 | 10 |
| L2_V050 | 223 | 0-1 | 4 | 1 | 22 | 22 | 22 | 0 | 0 | 0 | 23 | 23 | 23 | 1 | 1 | 1 |
| L2_V050 | 223 | 1-2 | 4 | 1 | 21 | 22 | 20 | 0 | 0 | 0 | 21 | 22 | 20 | 0 | 0 | 0 |
| L2_V050 | 223 | 2-3 | 4 | 1 | 20 | 20 | 20 | 0 | 0 | 0 | 20 | 20 | 20 | 0 | 0 | 0 |
| L2_V050 | 223 | 3-4 | 4 | 1 | 20 | 20 | 20 | 0 | 0 | 0 | 20 | 20 | 20 | 0 | 0 | 0 |
| L2_V050 | 223 | 4-5 | 4 | 1 | 20 | 20 | 20 | 0 | 0 | 0 | 20 | 20 | 20 | 0 | 0 | 0 |
| L2_V100 | 221 | 0-1 | 4 | 1 | 19 | 21 | 18 | 9.5 | 11 | 9 | 19 | 21 | 18 | 9.5 | 11 | 9 |
| L2_V100 | 221 | 1-2 | 4 | 1 | 18 | 18 | 18 | 9 | 9 | 9 | 18 | 18 | 18 | 9 | 9 | 9 |
| L2_V100 | 221 | 2-3 | 4 | 1 | 17.5 | 19 | 18 | 9 | 11 | 10 | 17.5 | 19 | 18 | 9 | 11 | 10 |
| L2_V100 | 221 | 3-4 | 4 | 1 | 15.5 | 16 | 13 | 8 | 8 | 6 | 15.5 | 16 | 13 | 8 | 8 | 6 |
| L2_V100 | 221 | 4-5 | 4 | 1 | 12 | 13 | 12 | 5 | 6 | 5 | 12 | 13 | 12 | 5 | 6 | 5 |
| L2_V100 | 222 | 0-1 | 4 | 1 | 38 | 38 | 38 | 7 | 7 | 7 | 38 | 38 | 38 | 7 | 7 | 7 |
| L2_V100 | 222 | 1-2 | 4 | 1 | 38 | 38 | 38 | 7 | 7 | 7 | 38 | 38 | 38 | 7 | 7 | 7 |
| L2_V100 | 222 | 2-3 | 4 | 1 | 38 | 38 | 38 | 7 | 7 | 7 | 38 | 38 | 38 | 7 | 7 | 7 |
| L2_V100 | 222 | 3-4 | 4 | 1 | 38 | 38 | 38 | 7 | 7 | 7 | 38 | 38 | 38 | 7 | 7 | 7 |
| L2_V100 | 222 | 4-5 | 4 | 1 | 38 | 38 | 38 | 7 | 7 | 7 | 38 | 38 | 38 | 7 | 7 | 7 |
| L2_V100 | 223 | 0-1 | 4 | 1 | 26 | 26 | 26 | 1 | 1 | 1 | 26 | 26 | 26 | 1 | 1 | 1 |
| L2_V100 | 223 | 1-2 | 4 | 1 | 26 | 26 | 26 | 1 | 1 | 1 | 26 | 26 | 26 | 1 | 1 | 1 |
| L2_V100 | 223 | 2-3 | 4 | 1 | 26 | 26 | 25 | 1 | 1 | 1 | 26 | 26 | 25 | 1 | 1 | 1 |
| L2_V100 | 223 | 3-4 | 4 | 1 | 24 | 24 | 24 | 1 | 1 | 1 | 24 | 24 | 24 | 1 | 1 | 1 |
| L2_V100 | 223 | 4-5 | 4 | 1 | 24 | 24 | 24 | 1 | 1 | 1 | 24 | 24 | 24 | 1 | 1 | 1 |

| n |
|---|
| 0 |
