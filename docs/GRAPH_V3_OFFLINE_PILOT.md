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

Execution requires a clean committed checkout and matching input/protocol hashes. Existing output/cases cannot be overwritten. Final results are pending the one registered execution.
