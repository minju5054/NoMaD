# Graph v3 PP-aware offline pilot

Base `3b78d3663c591b84aabf0b2c0aeee2cd2bc84e1b`, same Phase0 branch. This is offline mechanism validation at fixed saved switch boundaries, not navigation improvement or online timing evidence. No Isaac/GPU inference, new scenario, recovery, tuning, restart or visualization.

## Pre-registered mechanism

`research/nomad_phase0/graph_v3_protocol.json` freezes all weights and criteria before any solve. `GraphV3` subclasses the unchanged v2 graph: eight editable auxiliary SE(2) poses, fixed B, observation-anchored FRESH, fixed RAW nearest-projection entry, ≥20mm chord-derived auxiliary headings. It reuses v2 prior, relative pose, boundary, tangent consistency, anti-shrink and native/connector safety factors unchanged. No native yaw or waypoint time is invented.

The v2 constant-speed PP residual groups are replaced by variable-speed PP applied-w and swept safety groups. A new **pre-clipping curvature** residual compares κ_PP with previous actual w/max(v,0.05), sigma0.5/m (equivalent to v2's0.1rad/s scale at0.2m/s). The clipped applied-w term remains. Soft obstacle target0.025m, pass threshold0.02m, other v2 weights and TRF solver settings remain fixed (3-point Jacobian, max_nfev200, tolerances1e-8, zero increments, one solve).

Side preservation applies only to disclosed AABBs where every RAW native full-path crossing of world x=center_x has the same signed y-center_y outside half-Y-width+radius. Absent, vertical/ambiguous or inside crossings are `SIDE_UNDEFINED`. The factor freezes RAW segment indices/fractions and penalizes loss of that side (sigma0.02m). Actual corrected and executed side diagnostics are recomputed; they are not proof of completed obstacle bypass. This is not a new correspondence search.

Dynamic geometry is supplied to the solve only after the **next actually captured RGB** following first visible magenta RGB has completed before B's host timestamp. Static geometry is known. The disclosed set stays fixed during each solve. Safety evaluation separately uses all geometry actually active at B. The same next-frame rule is reconstructed from saved RGB for historical stress runs; their online controllers did not use that information rule. P0 FRESH43's B precedes publication, so its graph receives only static obstacles.

## User-fixed speed and baseline rules

The existing PurePursuit remains unchanged. A dedicated wrapper reuses its projection/lookahead state; control remains9Hz and integration72Hz.

- Variable speed (both RAW+Speed and Graphv3): target=clip(0.4/|κ_PP|,0.05,0.2), zero curvature target0.2. Choose the closest target within previous actual v±0.5/9 m/s; w=clip(vκ_PP,−0.4,0.4). No termination just because curvature cannot be attained.
- Record `CURVATURE_SATURATED` (|κ|>8), `ACCEL_LIMITED`, `OMEGA_CLIPPED` at each executed9Hz control tick, plus weighted held72Hz interval counts. Flags alone never determine safety or improvement. RAW/rigid/v2 may also saturate; acceleration-limited is not applicable to their constant-speed rule.
- RAW+Rate limit: original0.2m/s PP with |Δw|≤0.1 per9Hz tick, initialized from previous actual w. `RATE_LIMITED` is additionally recorded.
- No zero-speed rotation. At the existing0.01m endpoint condition on a9Hz refresh, the offline continuation terminates before issuing a zero-speed command. Early H_switch endpoint completion is stop/truncation and cannot qualify as an improvement; natural H_chunk completion is reported separately.
- Output speed profile is the ordered pairs of projected path arclength and target/applied speed along the H_chunk continuation from B. Repeated arclength samples are retained with control ordinal because acceleration and pose are stateful. This is not intrinsic NoMaD timing, nor a universal open-loop v(s) independent of entry state.

Methods: RAW, RAW+Speed, RAW+Rate limit, RIGID (same v2 first-pose rigid alignment), saved Graphv2, Graphv3. V2 optimized paths/solver outcomes are reused only for S0; S1/stress are `NOT_AVAILABLE`, with no new v2 solve.

## Data and horizons

- (a) Exactly20 saved v2-selected S0 PP handoffs, including the original seven clipping-plateau cases.
- (b) Every P0 FRESH43–75 switch:33 handoffs, through the last switch before recorded dynamic-obstacle whole-footprint far-X passage at19.944444s. No performance filtering.
- (c) Six stress boundaries: fixed-goal F51/F52, Topomap sudden F52/F53, Early RAW F63/F64. Their actual OLD controller was PD; PP is a counterfactual initialized from the previous actual PD(v,w), not a replay of that PD collision.

H_switch uses **all intervals until the next actual switch**. This explicitly differs from v2's min(16,next-switch) evaluation: its saved corrected paths are re-evaluated at the new common horizon, while its original optimization horizon remains16. If no next switch was recorded, use the final recorded pose and mark the horizon right-censored. No invented switch pose.

H_chunk freezes that path without future FRESH or the1s waypoint expiry and follows to the existing endpoint criterion. Max60s prevents unbounded looping; failure to finish is `CHUNK_TIMEOUT`. This is an unexecuted continuation, not claimed to match the original asynchronous execution. Collision does not truncate this geometric counterfactual; overlap is recorded and cannot count as safe.

## Frozen judgment

Native full path and evaluated PP rollout must both have obstacle clearance≥0.02m and corridor containment. Loss versus RAW in either native/rollout obstacle or corridor minimum must be≤0.005m. H_switch travel must be≥70% RAW with no stop/truncation. Improvement additionally needs |Δw| reduction>1e-6rad/s; convergence is required for graph acceptance. The primary v3 comparison uses **RAW+Speed**, requires angular reduction relative to it and≥70% of its H_switch travel as well. RAW-relative improvement is secondary. H_chunk qualification additionally requires endpoint completion and its own safety/loss checks. These are per-case joint conditions, not averages hiding failures.

Stress RAW-unsafe→method-safe transitions are reported separately for native+rollout joint safety, with native and rollout failures also separated. Unsafe initial B cannot be repaired retroactively. Flags do not substitute for swept-clearance evaluation. 100ms is a future online target, not a pass gate; all solve times and failures are preserved. Fixed-B solves do not simulate solve-time motion.

## Validation / execution

Seven minimum tests passed (five new, two v2). All59 inputs exist with prior hash checks. The53 actual-PP handoffs reproduce the first saved command (maximum error2.22e-16) and complete stored H_switch pose segments; the six PD stress intervals separately reproduce their actual PD integration. No v3 solve has run at this protocol registration.

Use existing system Python3.12 / NumPy1.26.4 / SciPy1.11.4, without environment changes:

```bash
env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_phase0.graph_v3_pilot preflight --output /home/gpuadmin/Workspace/NoMaD/artifacts/graph_v3/offline_pilot_01
env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_phase0.graph_v3_pilot execute --output /home/gpuadmin/Workspace/NoMaD/artifacts/graph_v3/offline_pilot_01
```

Execution requires a clean committed checkout and matching input/protocol hashes. Existing output/cases cannot be overwritten. The one registered execution is complete; results follow. The commands above document the frozen procedure and must not be rerun into the existing output.

## Completed single execution

The clean frozen execution commit was `9fa49b1e2af6632ce71b846897804d60cf4f3ba2`.
Exactly **59 Graph v3 solves**, no restart/tuning, produced 630 method/horizon evaluations.
There were **52 converged and 7 nonconverged** solves; all seven exhausted `max_nfev=200`.
Every returned iterate, including failures, is preserved. No navigation or inference ran.

The 53 actual-PP cases reproduced their saved first command to 2.22e-16 and the saved 72Hz pose intervals exactly. The six historical PD cases separately passed PD replay; their PP rows are counterfactual. Post-processing verified 53,632 control records. Both variable-speed conditions satisfy the hard speed range [0.05,0.2]m/s, |w|≤0.4rad/s and acceleration≤0.5m/s². Reintegrating held commands agrees with saved counterfactual endpoints within 5.61e-13. No zero-speed rotation command was issued. All 2,311 input/source hashes remained unchanged. Seven minimum tests passed before execution.

### Method comparison

The next table reports mean switch |Δw| in rad/s. The same initial switch command is used for H_switch and H_chunk. Graph v3 means include **all final iterates**, including the seven rejected nonconverged ones; these are diagnostic means, not accepted-action performance.

| Method | S0 (20) | S1 P0 (33) | Stress (6) |
| --- | --- | --- | --- |
| RAW | 0.4252 | 0.1467 | 0.1452 |
| RAW+Speed | 0.4252 | 0.1467 | 0.1452 |
| RAW+Rate limit | 0.0993 | 0.0630 | 0.0285 |
| RIGID | 0.4017 | 0.1427 | 0.1452 |
| Graph v2 | 0.3671 | N/A | N/A |
| Graph v3 | 0.2669 | 0.0667 | 0.1452 |

Accepted safe-and-complete counts below are **H_switch / H_chunk**. They require native full path and actual evaluated PP rollout ≥2cm, corridor containment, completed horizon, and graph convergence where applicable. These counts do not alone establish angular/progress improvement. Native safety, rollout safety, overlap and corridor fields are separate in the CSV.

| Method | S0 (20) | S1 P0 (33) | Stress (6) |
| --- | --- | --- | --- |
| RAW | 19 / 11 | 32 / 25 | 0 / 0 |
| RAW+Speed | 19 / 15 | 32 / 28 | 1 / 0 |
| RAW+Rate limit | 19 / 10 | 32 / 24 | 0 / 0 |
| RIGID | 19 / 13 | 33 / 22 | 0 / 0 |
| Graph v2 | 20 / 12 | N/A | N/A |
| Graph v3 | 16 / 14 | 33 / 32 | 0 / 0 |

Joint improvement versus RAW+Speed, including the registered 5mm clearance-loss and 70% H_switch travel tests, is shown below (**H_switch / H_chunk**). This comparison is primary for Graph v3. RAW+Speed itself cannot reduce its own switch discontinuity. Its first w also equals RAW in all 59 cases because it either remains at0.2m/s or still clips after acceleration-limited slowing.

| Method | S0 (20) | S1 P0 (33) | Stress (6) |
| --- | --- | --- | --- |
| RAW | 0 / 0 | 0 / 0 | 0 / 0 |
| RAW+Speed | 0 / 0 | 0 / 0 | 0 / 0 |
| RAW+Rate limit | 15 / 6 | 13 / 9 | 0 / 0 |
| RIGID | 3 / 3 | 6 / 6 | 0 / 0 |
| Graph v2 | 10 / 8 | N/A | N/A |
| Graph v3 | 8 / 8 | 12 / 12 | 0 / 0 |

Graph v3 contributes qualifying changes in **8/20 S0 and 12/33 S1** cases, and **0/6 stress** cases. It does not dominate the simple rate limiter or saved Graph v2. No run-level or closed-loop conclusion follows.

The table below gives mean H_switch travel (mm) and mean speed (m/s). All constant-speed methods have RAW's travel; their trajectories and safety can still differ. H_chunk travel can be large because of looping and is **not** interpreted as progress.

| Dataset | RAW travel / speed | RAW+Speed travel / speed | Graph v3 travel / speed |
| --- | --- | --- | --- |
| S0 (20) | 51.11 / 0.2000 | 45.38 / 0.1777 | 48.69 / 0.1916 |
| S1 P0 (33) | 49.83 / 0.2000 | 44.46 / 0.1790 | 46.78 / 0.1883 |
| Stress (6) | 31.48 / 0.2000 | 17.90 / 0.1177 | 18.47 / 0.1206 |

H_chunk termination and safety are not inferred from movement alone. Entries below show **overlap count / corridor-intrusion count / chunk-timeout count**. These include diagnostic nonconverged iterates; no nonconverged graph is accepted above.

| Method | S0 (20) | S1 P0 (33) | Stress (6) |
| --- | --- | --- | --- |
| RAW | 5 / 2 / 7 | 7 / 0 / 8 | 6 / 0 / 6 |
| RAW+Speed | 1 / 2 / 3 | 5 / 0 / 5 | 5 / 0 / 2 |
| RAW+Rate limit | 5 / 1 / 9 | 9 / 0 / 9 | 6 / 0 / 6 |
| RIGID | 5 / 0 / 6 | 8 / 2 / 9 | 6 / 0 / 6 |
| Graph v2 | 4 / 2 / 8 | N/A | N/A |
| Graph v3 | 0 / 1 / 3 | 0 / 0 / 0 | 5 / 0 / 0 |

Graph v3 has no S0/S1 overlap in H_chunk, but S0 still has one corridor intrusion and three non-completions. S1 FRESH60 converges and reaches its endpoint but has **6.312mm** minimum clearance, failing2cm. The soft safety residual is not a hard safety guarantee and optimizes H_switch, not H_chunk. In the stress H_switch comparison, RAW/Speed/Rate/Rigid/Graphv3 overlap counts are4/0/3/4/0; avoidance of overlap alone does not meet2cm or imply convergence.

### Original seven clipping-plateau cases

RAW+Speed and Graph v3 both have **0/7 joint improvements**, for either horizon. Graph v3 lowers |Δw| in5/7, but four cases do not converge; the two converged cases with smaller |Δw| violate the allowed5mm clearance loss. These reasons may overlap.

| Case | RAW | RAW+Speed | Graph v3 | Converged | Graph failed H_switch criteria |
| --- | --- | --- | --- | --- | --- |
| S0_03_F0079 | 0.8000 | 0.8000 | 0.8000 | False | converged; raw_clearance_loss_le_5mm; H_switch_progress_and_no_stop; angular_reduction |
| S0_04_F0089 | 0.8000 | 0.8000 | 0.8000 | True | raw_clearance_loss_le_5mm; H_switch_progress_and_no_stop; angular_reduction |
| S0_06_F0027 | 0.8000 | 0.8000 | 0.5560 | False | converged; raw_clearance_loss_le_5mm |
| S0_07_F0090 | 0.8000 | 0.8000 | 0.4597 | False | converged; raw_clearance_loss_le_5mm |
| S0_08_F0036 | 0.8000 | 0.8000 | 0.4878 | True | raw_clearance_loss_le_5mm |
| S0_09_F0025 | 0.7065 | 0.7065 | 0.4072 | False | converged; raw_clearance_loss_le_5mm |
| S0_10_F0024 | 0.8000 | 0.8000 | 0.4343 | True | raw_clearance_loss_le_5mm |

### Stress transitions and initial safety

Accepted transitions from RAW native-or-rollout unsafe to joint safe are:

| Method | H_switch / 6 | H_chunk / 6 |
| --- | --- | --- |
| RAW | 0 | 0 |
| RAW+Speed | 1 | 0 |
| RAW+Rate limit | 0 | 0 |
| RIGID | 0 | 0 |
| Graph v2 | N/A | N/A |
| Graph v3 | 0 | 0 |

The single RAW+Speed short-horizon transition is fixed-goal FRESH51: PP clearance19.188→28.897mm. Graph v3's final iterate has the same short-horizon clearance but does **not converge**, so it is not accepted. Both continuations fall to12.685mm in H_chunk. This is evidence for a short slowing benefit, not complete safe recovery.

Three B states already violate2cm: fixed-goal F52=19.190mm, Topomap sudden F53=2.655mm, Early RAW F64=5.369mm (Static2). No future correction can retroactively satisfy the complete interval at these starts. The other B minima are fixed-goal F51=44.174mm, Topomap sudden F52=23.340mm, Early RAW F63=22.351mm. They remain in the denominator, with their failures explicitly retained.

### Geometry changes, side information and trade-offs

| Dataset | Mean per-case XY RMS change (mm) | Largest point change (mm) |
| --- | --- | --- |
| S0 (20) | 24.628 | 116.415 |
| S1 P0 (33) | 16.717 | 162.378 |
| Stress (6) | 35.912 | 96.484 |

The frozen native-side rule is world +X crossing with signed world Y offset. No side is invented for chunks that do not cross the obstacle centerline. Counts below are disclosed **case-obstacle labels**, not distinct obstacles or successful bypasses. Corrected-label change includes becoming undefined and is not itself a safety judgment.

| Dataset | Definite native side labels | SIDE_UNDEFINED labels | Definite labels changed after Graph |
| --- | --- | --- | --- |
| S0 (20) | 0 | 40 | 0 |
| S1 P0 (33) | 5 | 93 | 0 |
| Stress (6) | 1 | 17 | 0 |

P0 FRESH43's B is earlier than next-frame oracle publication; only static geometry entered that solve. All later P0 cases have dynamic geometry. The actual active dynamic box was still used for F43's independent safety evaluation. H_switch has3/14/16/24 integration intervals depending on recorded switches/termination. Fixed-goal52, Topomap53 and EarlyRAW64 are explicitly right-censored at the saved terminal pose, with no invented next switch.

Against RAW+Speed at H_switch, Graph v3 fails the5mm RAW-clearance-loss test in12 S0,18 S1 and3 stress cases; it fails70% progress in2/4/5 cases respectively. These overlap with other failures and cannot be subtracted as exclusive categories. Per-case reasons and obstacle-versus-corridor loss are retained in `tradeoffs.csv`.

### Flag counts and proportions

Flags describe commands, not safety. Each cell is **count / executed9Hz control ticks (percent)**. Counts include every method's diagnostic continuation, including nonconverged graph iterates. H_chunk timeouts contribute their entire observed60s and therefore many ticks; comparisons are exposure-weighted, not per-case averages. `flag_counts.csv` also gives held72Hz interval counts/ratios and `RATE_LIMITED`. ACCEL_LIMITED is not applicable to constant-speed methods (shown0). For RAW+Rate limit, OMEGA_CLIPPED marks the underlying physical PP cap, while RATE_LIMITED separately marks the additional slew cap.


**H_switch**

| Dataset / method | CURVATURE_SATURATED | ACCEL_LIMITED | OMEGA_CLIPPED |
| --- | --- | --- | --- |
| S0 / RAW | 6/46 (13.0%) | 0/46 (0.0%) | 16/46 (34.8%) |
| S0 / RAW+Speed | 5/46 (10.9%) | 8/46 (17.4%) | 9/46 (19.6%) |
| S0 / RAW+Rate limit | 6/46 (13.0%) | 0/46 (0.0%) | 17/46 (37.0%) |
| S0 / RIGID | 5/46 (10.9%) | 0/46 (0.0%) | 14/46 (30.4%) |
| S0 / Graph v2 | 6/46 (13.0%) | 0/46 (0.0%) | 16/46 (34.8%) |
| S0 / Graph v3 | 0/46 (0.0%) | 3/46 (6.5%) | 3/46 (6.5%) |
| S1 P0 / RAW | 13/74 (17.6%) | 0/74 (0.0%) | 20/74 (27.0%) |
| S1 P0 / RAW+Speed | 13/74 (17.6%) | 14/74 (18.9%) | 16/74 (21.6%) |
| S1 P0 / RAW+Rate limit | 13/74 (17.6%) | 0/74 (0.0%) | 20/74 (27.0%) |
| S1 P0 / RIGID | 10/74 (13.5%) | 0/74 (0.0%) | 18/74 (24.3%) |
| S1 P0 / Graph v3 | 0/74 (0.0%) | 7/74 (9.5%) | 7/74 (9.5%) |
| Stress / RAW | 6/10 (60.0%) | 0/10 (0.0%) | 10/10 (100.0%) |
| Stress / RAW+Speed | 6/10 (60.0%) | 10/10 (100.0%) | 10/10 (100.0%) |
| Stress / RAW+Rate limit | 6/10 (60.0%) | 0/10 (0.0%) | 10/10 (100.0%) |
| Stress / RIGID | 6/10 (60.0%) | 0/10 (0.0%) | 10/10 (100.0%) |
| Stress / Graph v3 | 2/10 (20.0%) | 9/10 (90.0%) | 9/10 (90.0%) |

**H_chunk**

| Dataset / method | CURVATURE_SATURATED | ACCEL_LIMITED | OMEGA_CLIPPED |
| --- | --- | --- | --- |
| S0 / RAW | 321/4374 (7.3%) | 0/4374 (0.0%) | 3254/4374 (74.4%) |
| S0 / RAW+Speed | 1115/2337 (47.7%) | 8/2337 (0.3%) | 1119/2337 (47.9%) |
| S0 / RAW+Rate limit | 435/5323 (8.2%) | 0/5323 (0.0%) | 4619/5323 (86.8%) |
| S0 / RIGID | 317/3450 (9.2%) | 0/3450 (0.0%) | 3240/3450 (93.9%) |
| S0 / Graph v2 | 322/4506 (7.1%) | 0/4506 (0.0%) | 3254/4506 (72.2%) |
| S0 / Graph v3 | 1060/1931 (54.9%) | 5/1931 (0.3%) | 1065/1931 (55.2%) |
| S1 P0 / RAW | 361/4715 (7.7%) | 0/4715 (0.0%) | 4322/4715 (91.7%) |
| S1 P0 / RAW+Speed | 2731/3159 (86.5%) | 14/3159 (0.4%) | 2734/3159 (86.5%) |
| S1 P0 / RAW+Rate limit | 388/5236 (7.4%) | 0/5236 (0.0%) | 4870/5236 (93.0%) |
| S1 P0 / RIGID | 350/5753 (6.1%) | 0/5753 (0.0%) | 4320/5753 (75.1%) |
| S1 P0 / Graph v3 | 0/653 (0.0%) | 7/653 (1.1%) | 7/653 (1.1%) |
| Stress / RAW | 272/3240 (8.4%) | 0/3240 (0.0%) | 3240/3240 (100.0%) |
| Stress / RAW+Speed | 1086/1332 (81.5%) | 12/1332 (0.9%) | 1091/1332 (81.9%) |
| Stress / RAW+Rate limit | 257/3240 (7.9%) | 0/3240 (0.0%) | 3240/3240 (100.0%) |
| Stress / RIGID | 311/3240 (9.6%) | 0/3240 (0.0%) | 3240/3240 (100.0%) |
| Stress / Graph v3 | 82/447 (18.3%) | 11/447 (2.5%) | 91/447 (20.4%) |

### Solve latency and online limitations

Wall time across all59 attempts: **median2.658s, p9538.618s, max52.146s**; **59/59 (100%) exceed100ms**. Minimum1.225s, mean8.778s. These are measured CPU wall times with one BLAS/OMP thread, not GPU inference times. The100ms target was not used to accept/reject outcomes or tune the solver.

Nonconverged IDs: S0_03_F0079, S0_06_F0027, S0_07_F0090, S0_09_F0025, old_rollout_obstacle_01_F0051, topomap_sudden_01_F0052, early_raw_01_F0064. All hit the fixed200-function-evaluation limit. Piecewise projection, clipping, hinge and swept-minimum factors remain possible numerical limitations; the experiment does not isolate a unique numerical cause.

Online integration is not validated. The main unresolved issue is enforcing actual execution safety/progress while a solve takes seconds and B moves. This pilot provides neither hard safety guarantees nor solve-time boundary handling. Short-horizon soft safety can fail over H_chunk; reducing angular discontinuity can lose clearance or movement. No additional solve, tuning, navigation or recovery was performed.

### Preserved outputs

- `research/results/graph_v3_offline_pilot_20261022/summary.json`: full dataset/method/horizon aggregates.
- `comparison.csv`:630 per-case method/horizon records, including safety, motion, side, solver and flag fields.
- `graph_v3_corrections.json`: all59 returned world trajectories and ordered arclength speed profiles, including marked nonconverged iterates.
- `method_summary.csv`, `flag_counts.csv`, `plateau.csv`, `tradeoffs.csv`: compact tables.
- `selection.json`, `execution.json`, `preflight.json`, `verification.json`: case selection,2,311 hashes, clean execution SHA, validation and59 output hashes.
- `verify_saved_outputs.py`: exact read-only numerical verification/export script used after the frozen execution; it never calls the solver and refuses existing output files.
- Complete control traces and factor costs remain at `/home/gpuadmin/Workspace/NoMaD/artifacts/graph_v3/offline_pilot_01/cases/` (about74MB, excluded from Git). Existing raw/derived runs are unchanged.

This remains **offline mechanism validation with oracle geometry**. H_chunk is a frozen, unexecuted continuation; stress PP is counterfactual after actual PD. S0 selected maxima/medians, one contiguous S1 window and historical failures are not an unbiased performance sample. None of these results establishes closed-loop improvement, Graph necessity or real-time applicability.
