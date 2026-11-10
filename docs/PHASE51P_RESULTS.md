| status | completed | planned | protocol_sha256 | historical_execution_days_differ |
|---|---|---|---|---|
| COMPLETE | 20 | 20 | 7da31e169aee5e1fcc8f1cb06cc98f476ced82a4a6974ab10119d6f50a6b88df | True |

| item | definition |
|---|---|
| success | Phase47 success: declared arrival at distance<=0.5m AND no collision;wrong arrival>0.5m;timeout without declaration unchanged |
| delay | Same post-inference IPC hold as D750: packet received -> release,changed only to1.5s in L150;actual network inference time is additional,not normalized |
| WIDE | Only sudden-box lateral width and center/jitter change. Thickness/height/trigger/forward-surface offset frozen;H2 both boxes centered. SLW/LC have no sudden boxes and are unchanged |
| passage | At least one full geometric side gap>=0.33m;inside corridor/no static overlap. H1 inner-corner wall included;maximum multiplier<=1.5 frozen before runs |
| stop_time | Saved72Hz actual /v/<0.01,integrated by interval;includes first inference wait,recovery/alignment and other stops |
| EC_all_rejected | Logged NORMAL_NO_EC_SAFE_CANDIDATE => no available path survives frozen full-speed then0.1m/s fallback;duration held from that decision to next EC PASS INSTALL or run end,merged across repeated rejects |
| EC_scope | Available install candidates,not necessarily all8 NoMaD samples (depth-unsafe samples were already filtered). Held last-decision state,not continuous new validation;recovery time included;no runtime change |
| EC_report | Per-run total held duration and longest continuous interval;physical-stop intersection also saved. Same reconstruction on historical Phase47 logs |
| comparison | Same scene/seed Phase47-C OURS-DETOUR+HMM adjacent columns;different execution day,no claim of isolated random effect;missing/new technical failures not zero-filled |
| summary | Counts for outcomes;medians for arrival time(successes only),stop and EC durations;per-run values also reported |
| execution | Preparation only,dry-run20,zero simulation/render/inference;main serial/one technical retry/storagev2/cache cleanup/disk30GB stop,automatic report+commit+push |

| condition | scene | planned | valid | pending | technical_failure | success | phase47_success | collision | phase47_collision | wrong_stop | phase47_wrong_stop | timeout_without_declaration | phase47_timeout_without_declaration | goal_time_s | phase47_goal_time_s | stopped_s | phase47_stopped_s | ec_all_candidates_rejected_s | phase47_ec_all_candidates_rejected_s | ec_all_candidates_rejected_max_s | phase47_ec_all_candidates_rejected_max_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L150 | SLW | 2 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 2 | 1 | — | 50.583 | 47.444 | 13.167 | 0 | 1.6667 | 0 | 1.5556 |
| L150 | LC | 2 | 2 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 59.208 | 28.708 | 20.875 | 3.3889 | 0 | 0 | 0 | 0 |
| L150 | L2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 0 | — | 47.083 | 36.444 | 4.3333 | 0 | 0 | 0 | 0 |
| L150 | H1 | 2 | 2 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 53.333 | 31.833 | 19.944 | 5.0833 | 0 | 0.22222 | 0 | 0.22222 |
| L150 | H2 | 2 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | — | 48.583 | 29.944 | 10.236 | 0 | 0 | 0 | 0 |
| L150 | ALL | 10 | 10 | 0 | 0 | 4 | 8 | 0 | 0 | 1 | 1 | 5 | 1 | 55.833 | 38.708 | 30.611 | 5.9444 | 0 | 0 | 0 | 0 |
| WIDE | SLW | 2 | 2 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 51.833 | 50.583 | 10.611 | 13.167 | 0.22222 | 1.6667 | 0.22222 | 1.5556 |
| WIDE | LC | 2 | 2 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 28.583 | 28.708 | 3.1111 | 3.3889 | 0 | 0 | 0 | 0 |
| WIDE | L2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | — | 47.083 | 6.3333 | 4.3333 | 0 | 0 | 0 | 0 |
| WIDE | H1 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | — | 31.833 | 10.944 | 5.0833 | 4 | 0.22222 | 2.4444 | 0.22222 |
| WIDE | H2 | 2 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 1 | 0 | 0 | — | 48.583 | 9.2778 | 10.236 | 0 | 0 | 0 | 0 |
| WIDE | ALL | 10 | 10 | 0 | 0 | 3 | 8 | 0 | 0 | 7 | 1 | 0 | 1 | 28.833 | 38.708 | 8.6111 | 5.9444 | 0 | 0 | 0 | 0 |

| condition | scene | seed | status | baseline_output | success | phase47_success | collision | phase47_collision | wrong_stop | phase47_wrong_stop | timeout_without_declaration | phase47_timeout_without_declaration | goal_time_s | phase47_goal_time_s | goal_time_s_delta | stopped_s | phase47_stopped_s | stopped_s_delta | ec_all_candidates_rejected_s | phase47_ec_all_candidates_rejected_s | ec_all_candidates_rejected_s_delta | ec_all_candidates_rejected_max_s | phase47_ec_all_candidates_rejected_max_s | ec_all_candidates_rejected_max_s_delta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WIDE | SLW | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/SLW_221_OURS-DETOUR+HMM/attempt1 | True | True | False | False | False | False | False | False | 51.833 | 50.583 | 1.25 | 11.222 | 8.5556 | 2.6667 | 0 | 0 | 0 | 0 | 0 | 0 |
| L150 | SLW | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/SLW_221_OURS-DETOUR+HMM/attempt1 | False | True | False | False | False | False | True | False | — | 50.583 | — | 50.111 | 8.5556 | 41.556 | 0 | 0 | 0 | 0 | 0 | 0 |
| WIDE | LC | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/LC_221_OURS-DETOUR+HMM/attempt1 | True | True | False | False | False | False | False | False | 28.833 | 28.833 | 0 | 2.8889 | 3.4444 | -0.55556 | 0 | 0 | 0 | 0 | 0 | 0 |
| L150 | LC | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/LC_221_OURS-DETOUR+HMM/attempt1 | True | True | False | False | False | False | False | False | 66.083 | 28.833 | 37.25 | 23.75 | 3.4444 | 20.306 | 0 | 0 | 0 | 0 | 0 | 0 |
| L150 | L2 | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/L2_221_OURS-DETOUR+HMM/attempt1 | False | True | False | False | False | False | True | False | — | 43.583 | — | 36.667 | 2.8889 | 33.778 | 0 | 0 | 0 | 0 | 0 | 0 |
| WIDE | L2 | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/L2_221_OURS-DETOUR+HMM/attempt1 | False | True | False | False | True | False | False | False | — | 43.583 | — | 6.2222 | 2.8889 | 3.3333 | 0 | 0 | 0 | 0 | 0 | 0 |
| WIDE | H1 | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H1_221_OURS-DETOUR+HMM/attempt1 | False | True | False | False | True | False | False | False | — | 33.833 | — | 13.667 | 6.1111 | 7.5556 | 8 | 0.44444 | 7.5556 | 4.8889 | 0.44444 | 4.4444 |
| L150 | H1 | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H1_221_OURS-DETOUR+HMM/attempt1 | True | True | False | False | False | False | False | False | 59.333 | 33.833 | 25.5 | 25.111 | 6.1111 | 19 | 0 | 0.44444 | -0.44444 | 0 | 0.44444 | -0.44444 |
| L150 | H2 | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H2_221_OURS-DETOUR+HMM/attempt1 | False | False | False | False | False | True | True | False | — | — | — | 36.111 | 11.556 | 24.556 | 0 | 0 | 0 | 0 | 0 | 0 |
| WIDE | H2 | 221 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H2_221_OURS-DETOUR+HMM/attempt1 | False | False | False | False | True | True | False | False | — | — | — | 9.5556 | 11.556 | -2 | 0 | 0 | 0 | 0 | 0 | 0 |
| WIDE | SLW | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/SLW_222_OURS-DETOUR+HMM/attempt1 | False | False | False | False | True | False | False | True | — | — | — | 10 | 17.778 | -7.7778 | 0.44444 | 3.3333 | -2.8889 | 0.44444 | 3.1111 | -2.6667 |
| L150 | SLW | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/SLW_222_OURS-DETOUR+HMM/attempt1 | False | False | False | False | False | False | True | True | — | — | — | 44.778 | 17.778 | 27 | 0 | 3.3333 | -3.3333 | 0 | 3.1111 | -3.1111 |
| L150 | LC | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/LC_222_OURS-DETOUR+HMM/attempt1 | True | True | False | False | False | False | False | False | 52.333 | 28.583 | 23.75 | 18 | 3.3333 | 14.667 | 0 | 0 | 0 | 0 | 0 | 0 |
| WIDE | LC | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/LC_222_OURS-DETOUR+HMM/attempt1 | True | True | False | False | False | False | False | False | 28.333 | 28.583 | -0.25 | 3.3333 | 3.3333 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| WIDE | L2 | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/L2_222_OURS-DETOUR+HMM/attempt1 | False | True | False | False | True | False | False | False | — | 50.583 | — | 6.4444 | 5.7778 | 0.66667 | 0 | 0 | 0 | 0 | 0 | 0 |
| L150 | L2 | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/L2_222_OURS-DETOUR+HMM/attempt1 | False | True | False | False | False | False | True | False | — | 50.583 | — | 36.222 | 5.7778 | 30.444 | 0 | 0 | 0 | 0 | 0 | 0 |
| L150 | H1 | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H1_222_OURS-DETOUR+HMM/attempt1 | True | True | False | False | False | False | False | False | 47.333 | 29.833 | 17.5 | 14.778 | 4.0556 | 10.722 | 0 | 0 | 0 | 0 | 0 | 0 |
| WIDE | H1 | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H1_222_OURS-DETOUR+HMM/attempt1 | False | True | False | False | True | False | False | False | — | 29.833 | — | 8.2222 | 4.0556 | 4.1667 | 0 | 0 | 0 | 0 | 0 | 0 |
| WIDE | H2 | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H2_222_OURS-DETOUR+HMM/attempt1 | False | True | False | False | True | False | False | False | — | 48.583 | — | 9 | 8.9167 | 0.083333 | 0 | 0 | 0 | 0 | 0 | 0 |
| L150 | H2 | 222 | PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H2_222_OURS-DETOUR+HMM/attempt1 | False | True | False | False | True | False | False | False | — | 48.583 | — | 23.778 | 8.9167 | 14.861 | 0 | 0 | 0 | 0 | 0 | 0 |

| condition | scene | seed | start_s | end_s | duration_s | end_reason |
|---|---|---|---|---|---|---|
| WIDE | H1 | 221 | 23.889 | 27 | 3.1111 | EC_PASS_INSTALLED |
| WIDE | H1 | 221 | 29 | 33.889 | 4.8889 | EC_PASS_INSTALLED |
| WIDE | SLW | 222 | 11.444 | 11.889 | 0.44444 | EC_PASS_INSTALLED |
