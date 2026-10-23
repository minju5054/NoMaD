# Phase 3 Stage 1: S0 RAW + PP delivery-delay sweep

## Preregistration (before navigation)

Base `c7fc0bc`; branch `research/phase0-infrastructure`. Frozen protocol:
`research/nomad_phase3/protocol.json`. This is an **N=5 exploratory study** in
**SE(2) kinematic Isaac Sim**, with **Oracle geometry evaluation only**.
No Graph, sample selection, RIGID, rate limit, recovery or safety intervention.

The unchanged S0 scenario and 2-second/14-node Topomap are used. Sample 0,
lookahead 0.25m, speed 0.2m/s, angular bound 0.4rad/s, 4/9/72Hz, and 1-second
release-based waypoint timeout remain unchanged. The new opt-in mode changes
only the simulation termination ceiling to 90s and enables the existing uniform
post-packet result-delivery hold. Original scenario JSON remains at 60s.

Order: S0_01 to S0_05, each D=0,250,500,750ms. Offsets 10000 to 50000;
inference seed `101 + offset + 2*request_id`, DDPM seed +1. Exactly 20 attempts,
no retries. Technical failures are recorded and the next unattempted job runs.
The global S0 batch lock prevents concurrent batch GPU navigation.

Success = goal entry without confirmed geometric overlap or corridor intrusion.
2cm margin violations remain separate. A conservative contact stop without
confirmed overlap is retained as `OTHER_TERMINATION`, never called collision.
STUCK requires the 90s simulation timeout. Technical failures remain explicit.

A→B motion is summed from actual 72Hz executed poses, not a hypothetical OLD
continuation. Net wrapped yaw and total absolute yaw are separate. Staleness
uses the original PP nearest projection at actual B divided by FRESH path
length. World paths use observation pose, never switch anchoring. First switch
and invalid paths are separated; received-only outputs do not acquire a B.
Clamp fractions use remaining tracked path length <0.25m. Fixed-speed curvature
saturation means |kappa_PP|>2/m at non-stopped control ticks (the 0.4/0.2 bound).
Run-level distributions and descriptive pooled event distributions are saved;
pooled events do not increase the experimental N. Host/simulation clocks remain
separate. Pacing lateness and wall/simulation duration ratio are reported.

Stage 2 selection is fixed: among positive D with <=3 verified successes out of
5, choose the smallest two. If all positive D achieve >=4/5, stop and report no
handoff-correction necessity established in this S0 range. No Stage 2 navigation
is authorized by this task. Technical failures weaken any navigation inference.

## Preflight

19 targeted tests passed: new gate, paired seeds, legacy runner defaults,
unchanged `ChunkExecution` class, existing S0 metrics/chunk execution/delivery
hold tests. Dry-run constructs exactly 20 unique outputs in the specified order.
No extra navigation or inference was used for preflight.

Existing S0_01–05 PP records all reproduce: pose re-integration maximum error
0; PP command error <=8.89e-16; swept-clearance error <=1.67e-16. All five old
runs reached the goal. RGB history, Topomap selection, native normalization,
seeds and observation anchors were validated. Checkpoint SHA-256:
`70f79b8262527e20e56ced64a3e3d7ef91855bc9e7c3fa348d78edcb83c6a333`.
Topomap SHA-256:
`5b720e71b03b9809488ca81c340bfe691f39542371bad03eddf7a40246285f36`.

Execution command (new output must not exist):

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 bash research/python.sh -m nomad_phase0.s0_batch --delay-sweep --execute --run-root /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase3_s0_delay_01
```

Results pending at preregistration. Code/protocol will be committed before launch.
