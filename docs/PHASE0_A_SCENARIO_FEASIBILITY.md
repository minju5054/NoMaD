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
bash research/python.sh -m unittest discover -s research/tests -p test_scenario_feasibility.py
bash research/python.sh -m nomad_phase0.scenario_feasibility --scenario research/nomad_isaac/two_obstacles_wide_wall_scenario.json --dynamic-state absent --output research/results/phase0a_feasibility_20261020/S0.json
bash research/python.sh -m nomad_phase0.scenario_feasibility --scenario research/nomad_isaac/early_obstacle_scenario.json --dynamic-state active --output research/results/phase0a_feasibility_20261020/S2.json
```

Outputs are exclusive-create: use a new output path for another invocation.
No Isaac Sim navigation or GPU inference is involved.
