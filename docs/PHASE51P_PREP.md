# Phase51-P 준비

| status | method | conditions | scenes | seeds | runs |
|---|---|---|---|---|---|
| FROZEN_PREPARED_NOT_RUN | OURS-DETOUR+HMM | L150/WIDE | SLW,LC,L2,H1,H2 | 221,222 | 20 |

| scene | applies | reason |
|---|---|---|
| SLW | False | NO_SUDDEN_BOX_STATIC_SCENE_UNCHANGED |
| LC | False | NO_SUDDEN_BOX_STATIC_SCENE_UNCHANGED |
| L2 | True | — |
| H1 | True | — |
| H2 | True | — |

| item | value |
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

| passed | tests | dry_run | simulations_started | renders | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|
| True | 6 | 20 | 0 | 0 | 7da31e169aee5e1fcc8f1cb06cc98f476ced82a4a6974ab10119d6f50a6b88df | 1137470779392 |

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase51p.campaign --status`

실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase51p.campaign > ../artifacts/isaac6/phase51p_01.log 2>&1 < /dev/null &`
