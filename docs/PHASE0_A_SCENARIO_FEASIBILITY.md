# Phase 0-A — offline scenario feasibility checker

Base `3ec84aa685f9b2302dd2a8255372e9f9dfa913b4`; ongoing infrastructure branch
`research/phase0-infrastructure`. This is infrastructure validation, not a
scientific navigation experiment or an evaluation of NoMaD.

## Scope and search contract

Only S0 `two_obstacles_wide_wall_scenario.json` and S2
`early_obstacle_scenario.json` are evaluated. S2 includes the fixed dynamic box
as already active throughout the search; it does not model obstacle appearance,
visibility, inference, latency, or an executed prefix. S1/S3 are not created.

The isolated `research/nomad_phase0/scenario_feasibility.py` imports only the
existing SE(2) integration and obstacle/corridor geometry, NumPy and stdlib.
Navigation, NoMaD, Topomap, original PD, Graph and prior scenarios are unchanged.
No runtime imports the checker. There is no trajectory follower or batch runner.

Frozen `feasibility_protocol.json` records:

- Continuous forward-only Hybrid A* state representatives; duplicate bins
  XY 0.05m, yaw 64 bins (5.625°). Pose is never snapped to the bin center.
- Five 0.5s primitives: v=0.2m/s, w=0, −0.2, +0.2, −0.4, +0.4rad/s.
  These are a subset of the permitted `0≤v≤0.2`, `|w|≤0.4`; no reverse or
  in-place rotation primitive is implemented. This is a checker choice only.
- Euclidean distance-to-goal-disk / max speed heuristic, weight1.5;
  30,000 expansions or120s CPU wall budget per search, path duration at most60s.
  Costs are primitive durations. This is not a shortest-path guarantee.
- Robot circle radius0.09m, obstacle clearance≥0.02m. Corridor footprint
  clearance must be strictly positive, matching the existing geometry monitor;
  the obstacle margin is not silently added to corridor boundaries.
- Goal is the scenario's XY disk (radius0.30m in S0/S2); native goal yaw is
  metadata and is not a terminal constraint.

Every edge uses exact `integrate_se2`. Remote boxes can be certified by a
1-Lipschitz distance bound; near boxes use `swept_clearance`, and every edge
uses `corridor_clearance`. A found witness is reconstructed and **all** arcs
are rechecked using the original swept and corridor functions. Endpoint-only
collision tests do not establish safety. JSON stores poses, constant commands,
durations, per-obstacle clearance, and verification outcome.

## Side definitions and geometric certificates

Left/right mean world +Y/−Y relative to the active dynamic AABB, not PD angular
velocity. Start must be west of the safety-inflated box and the whole goal disk
east of it for this side test.

A qualifying route crosses the dynamic center-X plane west→east once, above
the upper Y face plus0.11m or below the lower face minus0.11m. After that
crossing it cannot return west of that plane. It must then reach the goal
east of the complete inflated box. X need not be monotone elsewhere.
Continuous arc X extrema enforce the no-recross rule.
Thus passing left, returning in front of the obstacle, and later escaping
right is not counted as a successful left bypass.

A local narrow gap alone is **not** a global blockage proof. The checker has
one sufficient certificate for a one-pass side pocket: the dynamic box and
a static box have overlapping raw Y sections, their radius+margin exclusions
join across the gap, and the static box reaches the corresponding corridor
wall. Explicit horizontal and vertical forbidden-center sections then close
the pocket together with the no-recross plane and corridor boundary. The
entire goal disk must be beyond the vertical section. These sections lie
inside raw box Y spans, so the proof does not approximate rounded inflation
corners by square inflated AABBs.

Statuses:

- `FEASIBLE`: a continuously revalidated witness reaches the goal.
- `GEOMETRICALLY_BLOCKED`: an explicit certificate closes the named one-pass
  side pocket. It is not a claim that every route through the scene is blocked.
- `NO_PATH_FOUND`: no witness within the discrete search and its budget;
  even exhaustion of the pruned open set is not an impossibility proof.
- `INVALID_SCENARIO`: invalid input/start or a goal disk outside the corridor
  center domain. An unsafe goal center alone does not invalidate a partly
  reachable goal disk.

S0 has no dynamic box, so left/right entries are null and not applicable;
its unconstrained route is evaluated. S2 is feasible if either named route
has a witness. No global infeasibility theorem is implemented.

## Unresolved research decisions

All four items in research plan section7 remain **UNDECIDED**:

1. 주 실행기를 trajectory follower로 변경할지 — `UNDECIDED`
2. Recovery에서 후진 허용 여부 — `UNDECIDED`
3. Oracle geometry 또는 depth 기반 안전 인식 — `UNDECIDED`
4. 언어 지시를 받는 VLA 필수 여부 — `UNDECIDED`

Reading exact JSON geometry for this offline checker does not select the
online safety-perception approach. Its forward-only primitives likewise do
not decide the future recovery policy.

## Reproduction

From repository root, with the existing environment:

```bash
bash research/python.sh -m pytest -q research/tests/test_scenario_feasibility.py research/tests/test_obstacle_geometry.py
bash research/python.sh -m nomad_phase0.scenario_feasibility --scenario research/nomad_isaac/two_obstacles_wide_wall_scenario.json --dynamic-state absent --output research/results/phase0a_feasibility_20261020/S0.json
bash research/python.sh -m nomad_phase0.scenario_feasibility --scenario research/nomad_isaac/early_obstacle_scenario.json --dynamic-state active --output research/results/phase0a_feasibility_20261020/S2.json
```

Outputs are exclusive-create: use a new output path for another invocation.
No Isaac Sim navigation or GPU inference is involved.

## S0 / S2 results

The checker/settings were committed as `3637f5a` before either invocation.
Both used the same code/settings; there was no search tuning. S0's source was
clean. S2 provenance lists only the newly generated, untracked S0 result
directory; no source had changed.

| Scene / route | Status | Goal witness | Minimum obstacle clearance | Corridor footprint clearance |
|---|---|---|---:|---:|
| S0, unrestricted | `FEASIBLE` | 4.4m / 22.0s | 0.021829288m | 0.954015310m |
| S0, dynamic left/right | Not applicable | No dynamic box | — | — |
| S2, left (+Y) | `GEOMETRICALLY_BLOCKED` | Certified one-pass pocket, no search | — | — |
| S2, right (−Y) | `FEASIBLE` | 4.4m / 22.0s | 0.021829288m | 0.954015310m |

Both found paths consist of44 constant-command arcs /45 SE(2) poses and reach
the0.30m goal disk at distance0.286888838m. Each search expanded166 states and
generated325; it terminated with `GOAL_WITNESS_REVALIDATED`, not a budget limit.
Search plus witness-check wall time was0.028629s /0.043274s in these invocations;
these are infrastructure timings, not navigation/inference performance.
Reconstructed pose error was0, and every continuous arc passed the unchanged
swept/corridor functions. There is no geometric overlap along either witness.

The deterministic search finds the **same** path in S0 and S2: it takes the
negative-Y side of both static boxes and the dynamic box. S2's dynamic
center-plane crossing is `(2.372279542, −0.335251812, 0.132012267rad)`;
it crosses once and never returns west of the plane before reaching the goal.
Per-obstacle minimum clearances are:

- Static1: 0.021829288m in both scenes.
- Static2: 0.107984685m in both scenes.
- Dynamic (S2 only): 0.149394826m.

This is a start-to-goal witness in the frozen scene, **not** a continuation
from a historical robot pose on the positive-Y side of Static1. It does not
claim that NoMaD will choose this path or that a sudden appearance during the
previous execution is recoverable.

### S2 narrow gap and left-side proof

Dynamic right face `x=2.547279542`; Static2 left face `x=2.75`.

```text
Actual surface gap:           0.202720458m = 20.2720458cm
Robot diameter:               0.180000000m
Required two-sided safe gap:  0.220000000m = 22cm
Safety-width deficit:         0.017279542m = 1.7279542cm
Best centered gap clearance:  0.011360229m per side (< 0.02m)
```

Thus it is a **safety-margin blockage**, not a claim that the physical circle
cannot fit without the required margin. The certificate additionally verifies:

- At `y=0.110674603`, forbidden center-X intervals
  `[2.372279542,2.657279542]` and `[2.64,3.0]` overlap by0.017279542m.
- At `x=3.0`, Static2 blocks the interval from that separator up to the
  corridor's positive-Y wall (its raw Y span is `[0,1.5]`).
- A left crossing enters above the horizontal separator. The corridor closes
  the top, and the side convention forbids returning west of `x=2.372279542`.
  It cannot exit this pocket to the goal disk, whose minimum X is4.2m.

The JSON contains these sections explicitly. No conclusion is drawn from
gap width alone. Returning in front of the dynamic box and taking a right
bypass is outside the definition of a successful left route.

## Validation and limitations

Five focused new tests and six existing obstacle-geometry tests passed
(`11 passed`): original arc/corridor equality, endpoint-safe but colliding
interior, numeric gap/certificate, rejection of side recrossing, and invalid
start/goal-region checks. The final witnesses independently recheck every
original continuous primitive. Original runtime/geometry/scenario files are
unchanged; outputs are new small JSONs in
`research/results/phase0a_feasibility_20261020/`.
`validation.json` records source/scenario hashes and successful preservation
of3,073 entries from the existing raw-data hash manifests.

No figure is needed to establish the numeric witnesses and certificate.
No Isaac navigation, GPU inference, trajectory follower, recovery, Graph,
depth processing, batch runner, S1/S3 design or environment change was performed.
Quantized duplicate pruning, five forward arcs, weighted heuristic,60s path
cap and finite expansion/wall budgets make the search incomplete.
`NO_PATH_FOUND` would remain absence of evidence, not impossibility.
The checker uses exact supplied geometry with a circle footprint and unicycle
kinematics; it says nothing about perception uncertainty, PhysX, tracking,
language-conditioned VLA requirements or online control performance.
All four research-plan section7 decisions remain `UNDECIDED`.
