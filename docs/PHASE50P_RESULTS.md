| status | completed | planned | protocol_sha256 |
|---|---|---|---|
| PARTIAL | 0 | 12 | e2dc1f876327ebe8079bbe736ced947e5ac0a3acfd95cad6513a181be1117109 |

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
| H1_V050 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — | — |
| H1_V100 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — | — |
| L2_V050 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — | — |
| L2_V100 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — | — |

| n |
|---|
| 0 |

| n |
|---|
| 0 |

| n |
|---|
| 0 |

| n |
|---|
| 0 |
