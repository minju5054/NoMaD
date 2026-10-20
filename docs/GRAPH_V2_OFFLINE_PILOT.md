# Graph v2 offline pilot

Scope: saved S0 PP handoffs, oracle geometry, offline mechanism validation.
No navigation, inference, runtime changes, visualization, tuning or restarts.
Base: `a00f3b46cfd3563b7b7e701e451ba2a50a081ac2`.

## Frozen protocol

`research/nomad_phase0/graph_v2_protocol.json` fixes selection, factors, solver,
comparison and improvement criteria before any solve. From each PP run, select
the largest actual applied `|Δw|` and the nearest-to-median value; ties use the
lowest FRESH ID. Deduplicate coincident choices. Initial switches without OLD,
unapplied received predictions, invalid paths/commands and empty recorded
horizons are excluded. Heading validity is not a selection filter.

FRESH remains observation anchored. All methods start at the same actual B.
PP uses the existing 0.25 m lookahead, 0.2 m/s speed, ±0.4 rad/s clipping,
9 Hz refresh and 72 Hz exact integration. Evaluate at most 16 integration
intervals, ending at the next switch pose if earlier, without applying that
next switch command. No origin is appended to the 8-point PP path.

RAW is unchanged; RIGID aligns node 0 and its chord-derived heading with B using
one rigid transform. GRAPH edits eight SE(2) poses. Its prior/relative factors
reuse the existing `between` and `se2_log` definitions. Boundary correspondence
is fixed from RAW's PP nearest projection, including segment indices/fraction.
Auxiliary headings use the nearest outgoing ≥20 mm chord, or nearest incoming
chord if no outgoing one exists. These indices remain fixed during optimization.
No native yaw or waypoint timestamps are assumed.

The graph uses prior, relative-pose, fixed-entry boundary, tangent consistency,
clipped **PP** angular continuity, anti-shrink, native/connector obstacle and
corridor, and refreshed PP rollout safety residuals. It does not use PD
residuals. The full eight-point path and actual PP rollout are evaluated
separately. PP's own projection is unchanged even though graph boundary
correspondence is fixed. Soft safety target is 0.025 m; measured threshold is
0.02 m. Fixed SciPy TRF, three-point derivatives, tolerances 1e-8,
max_nfev 200, zero initial increments, one solve per case.

The original clipped PP angular residual can have flat gradients when saturated.
This is retained and measured, not replaced after seeing results. Improvement
requires reduced `|Δw|`, safe native and executed paths, no worsening of obstacle
or corridor minima beyond 1 µm, retained motion and path length, and no new
endpoint stop. Report angular reductions with safety tradeoffs separately.
100 ms is a future online target, not a pilot acceptance threshold.

## Preflight

All 10 saved PP runs passed the existing batch provenance/seed/command/pose/
clearance validator. There are 882 eligible pairs and 20 selected cases.
Ten initial predictions and two terminal unapplied predictions are excluded.
All selected horizons are 16 ticks. Maximum errors:

- Observation and switch poses: 0.
- Observation-to-world coordinates: 4.44e-16 m.
- First actual PP command: 2.22e-16.
- RAW short-rollout pose: 0.
- RAW swept clearance versus saved log: 1.11e-16 m.

Two small checks cover chord fallback/projection and rigid relative-transform
preservation. No synthetic Graph solve is performed.

## Reproduction

Use existing system Python (NumPy 1.26.4, SciPy 1.11.4). No installation or
NoMaD virtual-environment change is required. From the repository root:

```bash
env PYTHONPATH=research MPLCONFIGDIR=/tmp/nomad-graph-v2-mpl /usr/bin/python3 -m nomad_phase0.graph_v2_pilot --preflight --output /path/to/new/output
env PYTHONPATH=research MPLCONFIGDIR=/tmp/nomad-graph-v2-mpl /usr/bin/python3 -m nomad_phase0.graph_v2_pilot --execute --output /path/to/new/output
```

Commit the fixed implementation/protocol before `--execute`; execution requires
a clean checkout. Preflight refuses an existing output directory; execution
refuses an existing `cases` directory. Missing/changed inputs abort, and a failed
solve is preserved without restart. Input hashes are checked again after solves.

Results will be appended after the single frozen execution.
