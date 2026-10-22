# Phase 2 — S1-v2 exploratory closed-loop comparison

Base `8b019e8`, same phase0 infrastructure branch. NoMaD, 21-node Topomap, original PurePursuit/PD, Graph v4 source and protocol, integration, uniform-delay framing and checkpoint are protected by SHA-256. This is exploratory N=4, with N=2 delay-only reference runs, not a confirmatory performance claim.

## Frozen revised protocol

`research/nomad_phase2/protocol.json` records the user's revised stages, seed mapping and implementation choices. S1-v2 gets a separate 90s scenario; original 60s scene remains unchanged. Dynamic trigger is first actual72Hz X in[2.0,2.1]. AABB center uses current world X+.09+d+.175 and clipped current world Y in[-.925,.925]. No heading, prediction, command or future outcome is used in placement. Exact d, clipping and wall gaps are logged.

M0 uses sample0 and original PP. M3/M5 preserve the exact same constant-speed PP while executing unchanged sample0, including ALL_UNSAFE fallback. Only replacement samples or accepted Graph corrections use the previously fixed variable-speed rule. Selection examines all native segments using only public geometry; it cannot inspect future rollout success. Dynamic geometry becomes available only after the capture following first visible RGB finishes. Existing corridor geometry is public from the start; it is possible for a corridor-unsafe native prediction to trigger selection even before spawn, and such events are retained.

M5 uses an isolated `/usr/bin/python3` CPU process importing GraphV4 unchanged. One solve per unsafe-sample0 FRESH, initialized from M3 selection, no tuning/restart. Graph B is actual pose at controller-tick dispatch; worker start and dispatch/IPC age are separately recorded, rather than claiming zero scheduling delay. Previous actual `(v,w)` fixes the initial curvature. A previous corrected path is passed only when the immediately preceding actual FRESH was an accepted correction. Missing public obstacles or undefined previous speed remain initialization rejections of the unchanged graph, with M3 fallback; no invented geometry/curvature.

During solve, the actual OLD command is held while its original release-time1s validity remains. Expiry preserves timeout stop. Incoming FRESH messages remain FIFO and are never substituted as Graph inputs mid-solve. One actual switch per controller tick; expired queued requests are recorded unapplied. Result arrival after .5s from dispatch is GRAPH_STALE, with M3 fallback once returned. This conservative deadline includes CPU/field/init/certificate/IPC; solver-only time is logged separately. The solver is not retuned or restarted at its deadline. Corrected world XY is not reanchored at result/application pose; PP uses the actual current pose.

Stage0: three pilots M0/M3/M5, D=.5,d=.8,offset0. Stage1: M0 D=.25,.5 x indices1,2. Stage2a: M0 d=.8,1 x D=.25,.5 x indices1..4. Offset=10000*index, inference seed101+offset+2*request ID and DDPM+1. Stage2a contains16 runs. Any SAFETY_FAILURE/STUCK selects2b (same16 pairs, M3 thenM5,32 runs). Otherwise2c runs8 hard M0 d=.6,D=.5,.75 and only its failed M0 pairs get M3/M5. Maximum55 attempts in2b or47 in2c. No retries, threshold changes or extra pilots. Technical audit failure stops the campaign. Stage0 outcomes are not performance evidence.

B0/B1 are the existing Phase B bounded searches, evaluated after each run at saved actual spawn and first obstacle-visible FRESH's actual switch B. They use actual appeared geometry, without online control access, and do not block or perturb the72Hz execution or Graph worker. No actual switch means no invented B. NO_PATH_FOUND is not mathematical unrescuability; both-no-witness cases are flagged separately without silently dropping navigation failures. Initially unsafe starts are separately INVALID_START.

Success is goal entry without geometric overlap/corridor intrusion. Margin violation is separately measured. Conservative contact termination is separately identified and never labelled confirmed overlap. Paired categories retain incomplete pairs, technical/placement failures and successful M0 harmed by another method. M3 failure/M5 success is a Graph-associated candidate requiring actual intervention inspection, not proof of necessity. In2c, unrun M3/M5 for the16 original2a cases stay NOT_RUN; the hard failed-M0 subset is explicitly outcome-selected.

## Preflight

50 minimum/new and existing integration tests passed: placement/gate, conditional PP equivalence, speed formula equality, stale/timeout behavior, seed/counts, old async/latency/Topomap mode restrictions. External CPU worker import/start passed without a solve. Existing map RGB hashes and21 nodes, checkpoint and protected sources verified. Free disk approximately1.4TB. No navigation had started when this protocol was committed.

Actual command/pose, native anchoring/selection, RGB history hashes, Topomap selection, delay, oracle reveal and swept geometry will be independently replayed after each attempt. Runtime records include every request/received/actual switch, decision, worker submission/result, and full raw/model output. Small results will be tracked; large artifacts remain outside Git.

## Stage0 M0 audit repair (no navigation retry)

The one M0 navigation finished and preserved all data. The initial audit rejected an observation-world anchor equality for a float64 difference of8.67e-19m between Isaac NumPy2.3 and offline NumPy1.26. The check now uses the same absolute1e-12 tolerance as the other coordinate/integration validators. This is a postprocessing correction only; controller/scenario/protocol thresholds are unchanged. A new `reaudit_M0_01` directory preserves the successful saved-data audit, while the original failed metric remains immutable. Exact PP command replay and72Hz pose integration both have error0. RGB/history, placement/USD, oracle reveal, all21 delivery packets and B0/B1 saved-pose checks passed. No pilot performance inference is made.

A restricted `continue-pilots` entry point launches only the two never-attempted M3/M5 jobs after checking the M0 audit amendment. It refuses existing output directories and retains the original failed audit in the journal. No M0 rerun or new seed is permitted.

## Stage0 completion and main-stage freeze

All three planned pilots completed exactly once. Actual PP command replay,72Hz pose integration and held-command trace error were0 in all three. Placement, next-capture oracle publication, RGB input history, Topomap selection, uniform delivery delay and saved-pose B0/B1 certificates passed. Maximum pacing errors were1.16ms(M0),1.83ms(M3) and recorded M5 value in `stage0.json`.

Coverage limitation: all native sample0 paths passed the public-geometry criterion in these pilots, so neither sample replacement nor an actual Graph solve/application/stale result occurred. Graph process startup and synthetic selection/accepted-result/stale/timeout branches are verified separately; real intervention is still NOT_EXERCISED. No parameters were changed to force an intervention. The terminal navigation outcomes are retained in Stage0 records but excluded from performance inference and Stage2 branching. The code/protocol is now frozen clean for the prescribed four delay baselines and16 M0 runs, followed solely by the registered branch.

## Completed campaign

All55 attempts completed without navigation retry on2026-10-22. Main-stage clean execution SHA is `f9f1f0ffec5d9062c767b13a725d8ddfd41041c2`. Stage2a selected2b by its registered rule. Actual main runs exercised Graph acceptance/application and rejection; stale/timeout remain synthetic-only coverage. Read-only aggregation and additional RGB/conditional-speed verification were added only after `complete.json` was written. See [final results and limitations](PHASE2_S1_V2_RESULTS.md), including the inherited visibility metadata label and actual Phase2 oracle-use logs.
