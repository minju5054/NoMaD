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

## Results — 2026-10-22

Both pilots used clean `ce6ae01`, one attempt each, no retries or post-result
changes. Existing Isaac Sim 6.0.1-rc.7 and RTX5060Ti were used without any
installation change. Startup shader compilation and initial renderer warnings
resolved before both RGB gates passed; startup time is not inference/delivery
latency or navigation time.

| Metric | P0: D=0ms, d=1.2m | P1: D=750ms, d=0.8m |
|---|---:|---:|
| Integration validation | PASS | PP/delay PASS; S1 overall INCONCLUSIVE |
| Termination | Goal entry | PLACEMENT_INFEASIBLE |
| Simulation time | 24.319444s | 13.444444s |
| Request / switch count | 94 / 93 | 13 / 12 |
| Actual packet→release median / p95 | 0.01056 / 0.01559ms | 750.07072 / 750.08953ms |
| Warm GPU inference median / p95 | 35.163 / 43.673ms | 36.000 / 51.837ms |
| Goal / collision / corridor intrusion | yes / no / no | no / no / no |
| Minimum dynamic clearance | 70.973mm | N/A: never spawned |
| Static1 / Static2 minimum clearance | 123.852 / 119.799mm | 409.441 / 759.134mm |
| Total stop time | 1.111111s | 2.222222s |
| Waypoint timeout episodes | 0 | 0 |
| Busy observation skips / missed slots | 1 / 0 | 38 / 0 |
| Pacing maximum absolute error | 1.334ms | 1.485ms |

Both runs reproduced every actual PP command and every 72Hz integrated pose
with maximum error **0**. Original sample0, normalization/cumsum, observation
anchoring, seeds and next-control-tick switches passed existing validation.
Every accepted result respected its uniform deadline, including terminal
unapplied results. P1 recorded actual valid OLD movement during delivery in
12 windows: median 147.222mm, max147.222mm, minimum100mm (the terminal window
is cut short by run termination). These use complete measured intervals only.
Pacing and inference-clock mapping passed. Neither run naturally exercised the
1s timeout; exact timeout behavior remains covered by the existing synthetic
tests, not claimed as observed here. Neither executed run violated 2cm margin.

### P0 valid S1 spawn and first FRESH

Tick845 / 11.736111s: actual pose
`(1.901448758, 0.361814159, -0.676557820)`; obstacle center
`(3.082303718, -0.586393504)`. Independent ray measurement gives d=1.2m;
nearest Euclidean footprint clearance is 1.178698m. USD AABB and activated
collision geometry match. The box remains absent before this tick.

First visible RGB is frame47 (snapshot11.736111s); information becomes
available only after frame48 (snapshot11.986111s) completes capture. Exact
capture-completion monotonic timestamps and image hashes are preserved; these
snapshot simulation times are not substituted for host information arrival.
Geometry is never used by PP.

First observed-obstacle FRESH is ID43, input history44–47. Its pixel-stack hash
matches the worker input. OLD42 moves30.556mm and changes yaw+0.016100rad from
observation A to switch B at11.888889s:
`B=(1.925426334,0.342874845,-0.660457356)`.
Dynamic clearance A→B is1.178698→1.148145m; minimum during OLD execution is
1.148145m. GPU ready/packet/release/switch host timestamps are in the summary.
This is an actual handoff, with no re-anchoring or invented B.

The actual path passes on the dynamic box's +Y side and reaches the goal.
From the actual spawn pose, existing forward-only one-pass checker found both
side witnesses: +Y12.5s/min20.367mm, −Y16.5s/min21.255mm. All continuous
arcs were reverified. These are offline oracle feasibility witnesses, not
executed PP paths or a causal explanation of the pilot's success.

### P1 placement rejection and remaining blocker

First trigger is tick968 /13.444444s, actual pose
`(1.900864313,1.070726142,+0.533894681)`.
The fixed ray rule proposes center `(2.842004474,1.627091241)` at measured
d=0.8000000000000006m. This **rejected candidate** overlaps Static2 and its
upper face exceeds the corridor by0.302091m. It is not an actual spawned box.
Offline recomputation confirms the same trigger, center and rejection reasons.

The monitor correctly terminates without spawning: zero dynamic collision
checks, no USD visibility update, no magenta RGB detection and no oracle
information release. There is no obstacle-conditioned FRESH or switch B;
side feasibility is **NOT_EVALUATED_NO_VALID_SPAWN**. This is not a collision
or PRE_HANDOFF_FAILURE; it is the prespecified invalid-placement outcome.
PP+uniform delay worked, but dynamic appearance and delayed handoff were not
validated in P1. They are not marked PASS.

**Overall: INCONCLUSIVE_S1_DELAYED_SPAWN_NOT_VALIDATED.** The current fixed
trigger/forward-ray placement does not guarantee a valid S1 box at actual
delayed-run poses. This blocks proceeding directly to the full D×d map. A
separately agreed scenario-validity protocol is needed before that experiment;
no location adjustment, new scenario, parameter tuning or extra navigation was
performed here. Even with seed101 in both runs, accepted RGB/request association
differs, and d also differs; this is not a paired causal delay comparison.

## Saved evidence and changes

New `nomad_phase1/s1.py`, scenario/protocol, `s1_audit.py` and four small tests;
narrow hooks in `launch.py`, `simulator.py`, `async_runtime.py`,
`sudden_obstacle.py` and the PP mode validator only. The original PP algorithm,
PD, NoMaD, Topomap, delivery-delay implementation, timing core, prior Graph and
S0/adaptive scenarios are unchanged. Old source/artifact protection hashes and
all220 prior paired-batch log hashes match after both runs.

Small JSON/CSV/provenance/hash/witness files:
[`research/results/phase1_s1_preflight_20261022`](../research/results/phase1_s1_preflight_20261022).
Full immutable model raw/derived, RGB, pose, chunk and timing logs remain in
the artifact root above. No additional figure, video, sweep or Graph work.
