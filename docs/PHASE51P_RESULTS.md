| status | completed | planned | protocol_sha256 | historical_execution_days_differ |
|---|---|---|---|---|
| PARTIAL | 0 | 20 | 7da31e169aee5e1fcc8f1cb06cc98f476ced82a4a6974ab10119d6f50a6b88df | True |

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
| L150 | SLW | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | — | 50.583 | — | 13.167 | — | 1.6667 | — | 1.5556 |
| L150 | LC | 2 | 0 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | 28.708 | — | 3.3889 | — | 0 | — | 0 |
| L150 | L2 | 2 | 0 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | 47.083 | — | 4.3333 | — | 0 | — | 0 |
| L150 | H1 | 2 | 0 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | 31.833 | — | 5.0833 | — | 0.22222 | — | 0.22222 |
| L150 | H2 | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | — | 48.583 | — | 10.236 | — | 0 | — | 0 |
| L150 | ALL | 10 | 0 | 10 | 0 | 0 | 8 | 0 | 0 | 0 | 1 | 0 | 1 | — | 38.708 | — | 5.9444 | — | 0 | — | 0 |
| WIDE | SLW | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | — | 50.583 | — | 13.167 | — | 1.6667 | — | 1.5556 |
| WIDE | LC | 2 | 0 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | 28.708 | — | 3.3889 | — | 0 | — | 0 |
| WIDE | L2 | 2 | 0 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | 47.083 | — | 4.3333 | — | 0 | — | 0 |
| WIDE | H1 | 2 | 0 | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | 31.833 | — | 5.0833 | — | 0.22222 | — | 0.22222 |
| WIDE | H2 | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | — | 48.583 | — | 10.236 | — | 0 | — | 0 |
| WIDE | ALL | 10 | 0 | 10 | 0 | 0 | 8 | 0 | 0 | 0 | 1 | 0 | 1 | — | 38.708 | — | 5.9444 | — | 0 | — | 0 |

| condition | scene | seed | status | baseline_output | success | phase47_success | collision | phase47_collision | wrong_stop | phase47_wrong_stop | timeout_without_declaration | phase47_timeout_without_declaration | goal_time_s | phase47_goal_time_s | goal_time_s_delta | stopped_s | phase47_stopped_s | stopped_s_delta | ec_all_candidates_rejected_s | phase47_ec_all_candidates_rejected_s | ec_all_candidates_rejected_s_delta | ec_all_candidates_rejected_max_s | phase47_ec_all_candidates_rejected_max_s | ec_all_candidates_rejected_max_s_delta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WIDE | SLW | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/SLW_221_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 50.583 | — | — | 8.5556 | — | — | 0 | — | — | 0 | — |
| L150 | SLW | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/SLW_221_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 50.583 | — | — | 8.5556 | — | — | 0 | — | — | 0 | — |
| WIDE | LC | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/LC_221_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 28.833 | — | — | 3.4444 | — | — | 0 | — | — | 0 | — |
| L150 | LC | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/LC_221_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 28.833 | — | — | 3.4444 | — | — | 0 | — | — | 0 | — |
| L150 | L2 | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/L2_221_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 43.583 | — | — | 2.8889 | — | — | 0 | — | — | 0 | — |
| WIDE | L2 | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/L2_221_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 43.583 | — | — | 2.8889 | — | — | 0 | — | — | 0 | — |
| WIDE | H1 | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H1_221_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 33.833 | — | — | 6.1111 | — | — | 0.44444 | — | — | 0.44444 | — |
| L150 | H1 | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H1_221_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 33.833 | — | — | 6.1111 | — | — | 0.44444 | — | — | 0.44444 | — |
| L150 | H2 | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H2_221_OURS-DETOUR+HMM/attempt1 | — | False | — | False | — | True | — | False | — | — | — | — | 11.556 | — | — | 0 | — | — | 0 | — |
| WIDE | H2 | 221 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H2_221_OURS-DETOUR+HMM/attempt1 | — | False | — | False | — | True | — | False | — | — | — | — | 11.556 | — | — | 0 | — | — | 0 | — |
| WIDE | SLW | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/SLW_222_OURS-DETOUR+HMM/attempt1 | — | False | — | False | — | False | — | True | — | — | — | — | 17.778 | — | — | 3.3333 | — | — | 3.1111 | — |
| L150 | SLW | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/SLW_222_OURS-DETOUR+HMM/attempt1 | — | False | — | False | — | False | — | True | — | — | — | — | 17.778 | — | — | 3.3333 | — | — | 3.1111 | — |
| L150 | LC | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/LC_222_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 28.583 | — | — | 3.3333 | — | — | 0 | — | — | 0 | — |
| WIDE | LC | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/LC_222_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 28.583 | — | — | 3.3333 | — | — | 0 | — | — | 0 | — |
| WIDE | L2 | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/L2_222_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 50.583 | — | — | 5.7778 | — | — | 0 | — | — | 0 | — |
| L150 | L2 | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/L2_222_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 50.583 | — | — | 5.7778 | — | — | 0 | — | — | 0 | — |
| L150 | H1 | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H1_222_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 29.833 | — | — | 4.0556 | — | — | 0 | — | — | 0 | — |
| WIDE | H1 | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H1_222_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 29.833 | — | — | 4.0556 | — | — | 0 | — | — | 0 | — |
| WIDE | H2 | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H2_222_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 48.583 | — | — | 8.9167 | — | — | 0 | — | — | 0 | — |
| L150 | H2 | 222 | NOT_RUN | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase47c_01/main/H2_222_OURS-DETOUR+HMM/attempt1 | — | True | — | False | — | False | — | False | — | 48.583 | — | — | 8.9167 | — | — | 0 | — | — | 0 | — |

| n |
|---|
| 0 |
