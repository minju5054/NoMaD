# Phase 1 S1 + Pure Pursuit + uniform delivery delay

Base `9c7a43d`, branch `research/phase0-infrastructure`. This is integration
preflight and at most two navigation pilots, not a D×d region-map experiment.
No Graph, recovery, reranking, safety controller, new perception or visualization.

## Frozen scenario and information protocol

`research/nomad_phase1/s1_scenario.json` retains all S0 geometry/settings and adds
one hidden magenta 0.35×0.35×0.8 m axis-aligned box. First actual 72 Hz pose in
`x=[1.9,2.0], y=[-1.4,1.4]` triggers a single placement. Given unit heading ray u,
box half sizes h and radius r=0.09, its center is
`pose.xy + u * (r + d + min_i(h_i / abs(u_i)))` (ignore zero components).
Slab-ray intersection independently measures d from the circular footprint's
forward boundary to the first box surface. This is not center distance or
Euclidean nearest clearance. Current pose and frozen geometry are the only
placement inputs. No prediction, command, future pose or outcome is used.
Static overlap, box/corridor containment and current footprint margin are
checked; invalid placement terminates without adjustment or retry.

Frozen candidates: d={0.8,1.0,1.2,1.5}m, D={0,0.25,0.5,0.75}s. Only P0
(D=0,d=1.2,seed101) and P1 (D=.75,d=.8,seed101) may be launched, once each.
Existing single-outstanding IPC delay runs after GPU inference and full packet
receive. Controller receive time is release; OLD's original receive age and
1s timeout are untouched. Observation-anchored eight-point sample 0 feeds the
unchanged PP (.25m lookahead, .2m/s, ±.4rad/s, 4/9/72Hz).

`--s1-mode --s1-distance-m ...` is the sole exception to old PP/dynamic/Topomap/
delay restrictions. S0 and earlier modes retain their gates. Existing adaptive
OLD-rollout placement and scenarios remain unchanged. The independent execution
thread decides the spawn; a snapshot carries the exact resolved box/spawn tick
to the existing main-thread USD update. RGB capture and geometric monitoring
use this same simulation timestamp; rendering does not block 72Hz execution.

Oracle information is **metadata only**. RGB uses the existing magenta rule and
20-pixel threshold. The first visible capture does not grant availability;
the next actually captured frame does, at its host capture-completion time.
Missed scheduled slots do not count. The final capture is logged too. No visible
frame means no information release. PP never receives obstacle geometry;
post-execution safety evaluation knows all active geometry from spawn onward.

## Preflight and execution gate

36 related/new minimal tests passed: mode isolation, oblique ray distance,
first tick activation, invalid placement, next-capture information timing,
existing PP anchoring/timeout and IPC uniform-delay behavior. Topomap14 node
RGB/pose/hash and checkpoint hash verified. The saved seed101 PP reference
first enters the trigger at tick845. All four candidate distances produce
nonoverlapping contained boxes at that saved pose. This is a preflight geometry
check, not a guarantee of valid placement or visibility on new trajectories.

Before pilots, freeze code/protocol in a clean commit. Launch P0, validate its
technical logs, then launch P1 only if that technical gate passes. Navigation
failure alone does not imply technical failure. No retry or result-based change.
Output root: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase1_s1_preflight_01/`.

For each actual spawn, reuse Phase0-A's unchanged forward-only checker once per
world +Y/−Y side (5 primitives, .5s, XY5cm/yaw64 bins, 30k expansions/120wall-s/
60path-s). It checks a one-pass path to the goal from actual yaw/pose. This is
not an online planner or a B0/B1 sweep. NO_PATH_FOUND means unconfirmed within
that bounded model, not geometric impossibility or proof that PP must fail.

Results pending the two frozen pilots. All original raw/results are preserved.
