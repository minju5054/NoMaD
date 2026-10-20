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

## Single frozen execution results

Executed at clean `afd4d0dd252d2801536ee7a82899a2b9815a3586`. Twenty solves,
zero retries, zero navigation/inference. All 20 terminated by SciPy `ftol`;
heading rejection and nonconvergence were both 0/20. This is numerical
convergence of a soft objective, not a proof of an optimum or hard feasibility.
`S0_05_F0090` used the short-segment chord fallback; no case was dropped because
of short segments.

Selected FRESH IDs (maximum / nearest median):

| Run | Maximum | Median |
|---|---:|---:|
| S0_01 | 91 | 79 |
| S0_02 | 86 | 54 |
| S0_03 | 79 | 8 |
| S0_04 | 89 | 3 |
| S0_05 | 90 | 39 |
| S0_06 | 27 | 73 |
| S0_07 | 90 | 24 |
| S0_08 | 36 | 10 |
| S0_09 | 25 | 49 |
| S0_10 | 24 | 1 |

These are deliberately selected extremes/median representatives, not an
unbiased sample of all switches. The failing S0_08 run remains included.
Initial ID 0 in each run and received-but-unapplied S0_08 ID 51 / S0_10 ID 94
were excluded. All candidate rankings and actual OLD IDs are saved.

| Metric, 20 cases | RAW | RIGID | GRAPH v2 |
|---|---:|---:|---:|
| Switch `abs(Δw)` mean, rad/s | 0.425200 | 0.401720 | 0.367062 |
| Switch `abs(Δw)` median, rad/s | 0.325461 | 0.298177 | 0.125050 |
| Switch `abs(Δw)` p95 / max, rad/s | 0.8 / 0.8 | 0.8 / 0.8 | 0.8 / 0.8 |
| Angular sign reversals | 11 | 11 | 9 |
| XY modification RMS, case mean, mm | 0 | 24.176 | 8.328 |
| Fixed-entry boundary gap, case mean, mm | 20.134 | 0 | 8.093 |
| Native full path meets safety criteria | 19/20 | 19/20 | 20/20 |
| PP rollout meets safety criteria | 20/20 | 20/20 | 20/20 |
| Smallest PP swept obstacle clearance, m | 0.122398 | 0.122516 | 0.122259 |
| Rollout travel per case, mm | 44.444 | 44.444 | 44.444 |
| Endpoint stop / overlap / corridor intrusion | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

Every comparison uses the identical B and 16 ticks, with original PP updates at
offset ticks 0 and 8. All methods kept v=0.2 m/s; angular reduction was not caused
by stopping or speed reduction. Graph XY path length ratios were
0.9680–1.0598; mean relative-transform translation error was 2.515 mm and mean
relative heading RMS error 0.01550 rad. RIGID relative-transform error was
at most 6.70e-16.

Graph reduced `abs(Δw)` in 12 cases, left 7 unchanged, and increased it in 1
(threshold 0.001 rad/s). RIGID: 7 decreased / 6 unchanged / 7 increased.
Mean paired Graph−RAW change was −0.05814 rad/s. For maximum cases, mean
RAW/RIGID/GRAPH was 0.73088/0.66855/0.64423 rad/s; for median cases it was
0.11952/0.13489/0.08989 rad/s. No uncertainty or population-level superiority
claim is made from this intentionally selected pilot.

### Safety tradeoffs and failure mechanisms

- **Clipping plateau:** the seven unchanged Graph cases are S0_03 F79,
  S0_04 F89, S0_06 F27, S0_07 F90, S0_08 F36, S0_09 F25, S0_10 F24.
  Their final unbounded PP angular commands remain beyond ±0.4 rad/s.
  The applied-w continuity residual is locally flat in this region. Shape and
  boundary factors change the path but fail to change the saturated first
  command. The worst 0.8 rad/s jumps therefore remain.
- **Competing objectives:** S0_02 F54's RAW full prediction overlaps Static2
  (−1.141 mm), although its short RAW PP execution is safe. Graph moves the
  native full-path clearance to 24.271 mm while `abs(Δw)` increases from
  0.116793 to 0.124975 rad/s. This is a path-safety/continuity tradeoff, not a
  demonstrated execution failure.
- **No joint improvement under the frozen strict criterion:** all 20 Graph
  rollouts and native paths meet the absolute safety thresholds. Nevertheless,
  compared with RAW, Graph reduces native obstacle minima in 14 cases
  (largest loss 4.812 mm), native corridor minima in 12 (24.713 mm),
  rollout obstacle minima in 4 (0.140 mm), and rollout corridor minima in 3
  (0.145 mm). Every angular-improving case loses at least one of these minima.
  Thus **0/20 GRAPH and 0/20 RIGID qualify** under the predefined requirement
  not to degrade any safety minimum by more than 1 µm. This is not a claim
  that the 2 cm threshold failed; the absolute safety checks pass. We do not
  relax the criterion after seeing results.

Graph solve wall time (actual `least_squares` duration): median **0.668 s**,
p95 **1.778 s**, max **1.885 s**, total 16.420 s. All exceed the future 100 ms
target; it was not used to reject or tune this pilot. Timing excludes loading,
preflight and final report evaluation. Existing system Python 3.12.3 /
NumPy 1.26.4 / SciPy 1.11.4 was used; no environment was changed.

Before online integration, the primary unresolved mechanism is reduction of
large **saturated PP** jumps while retaining safety and path geometry.
This pilot's soft factors do not guarantee that combined result. Computation
time and how movement would continue during a solve also remain unresolved;
all reported counterfactuals start at a fixed saved B and hide no simulated
online delay. No online integration, tuning or additional experiment was run.

## Saved evidence

Results: [`research/results/graph_v2_offline_pilot_20261020`](../research/results/graph_v2_offline_pilot_20261020).
`comparison.csv` has 60 method rows; `cases/*.json` retain each input, fixed
entry/chords, solver/factor cost, corrected path and 17-pose rollout.
`selection.json` preserves deterministic rankings/exclusions and 1,011 input
and source hashes. `summary.json` and `verification.json` contain aggregate
metrics and checks. All 110 previously recorded PP log hashes also match.
Raw outputs remain at
`/home/gpuadmin/Workspace/NoMaD/artifacts/graph_v2/offline_pilot_01/`.
Original source artifacts and runtime code were not modified.

The evidence establishes limited **offline mechanism validation** only.
It does not establish closed-loop improvement, Graph necessity, statistical
superiority, or online latency feasibility.
