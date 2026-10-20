# Phase 0-B — independent Pure Pursuit on the S0 witness

2026-10-20. Base `67c3304950a3e3b41df3e7640ecf02d1ab77cd2e`,
same `research/phase0-infrastructure` branch.
This is an offline infrastructure check, not NoMaD performance evaluation
or a decision to replace the primary executor.

## Frozen method

`research/nomad_phase0/follower_protocol.json` freezes the S0/scenario hashes,
the following settings, and a single Pure Pursuit simulation without tuning:

- Lookahead0.25m in path arclength; constant v0.2m/s; w clipped to±0.4rad/s.
- Nearest XY polyline projection with nondecreasing arclength progress.
  Interpolate the target at progress+lookahead, clamped to the path endpoint.
- Transform that point into current robot-local coordinates and use
  `curvature=2*y_local/(x_local²+y_local²)`, `w=v*curvature`.
- Stop `(0,0)` within0.01m of the path endpoint. No curvature-dependent
  slowdown, obstacle knowledge, world goal, timestamp, or reference yaw
  enters follower control.
- Pure Pursuit refresh9Hz; exact SE(2) integration72Hz; one held command
  spans8 integration ticks. Maximum60s, world-goal tolerance0.30m.

The geometric reference samples each original continuous primitive at72Hz.
Only its world XY array is supplied to Pure Pursuit. The original0.5s
primitive durations are used for reconstruction and exact-command replay,
never as follower waypoint deadlines. No native NoMaD yaw/time is assumed.

The original common/clearance functions are reused without modification.
The passive evaluator checks each **already executed** interval. It terminates
on geometric overlap, uncertified contact, or loss of certified corridor
containment; it does not predict future risk, select commands or slow down.
A positive clearance below0.02m is recorded but does not terminate execution.
This is a requested termination monitor, not a safety controller.

## Validation sequence and measurements

1. Reproduce all44 original0.5s primitives and their original full-primitive
   swept/corridor bounds. Compare them with saved S0 boundary poses/clearance.
2. Replay those commands at72Hz and compare every primitive boundary with
   saved poses. Also compare the dense direct arc samples with the sequential
   integration trace. Abort before Pure Pursuit on any mismatch.
3. Perform the single Pure Pursuit simulation. No geometry is passed into
   `PurePursuit.control()`. Goal checking belongs to the harness only.
4. Plot saved XY traces without another simulation.

Exact replay keeps the original command change instants at0.5s, even though
these do not all lie on the9Hz grid. Its44 command records are explicitly
separate from the follower's9Hz commands.

Original0.5s swept lower bounds and finer1/72s lower bounds can differ because
the chord/sagitta bound is less conservative on shorter arcs. We reproduce
the original bounds at their original interval lengths rather than claiming
the two discretizations' lower bounds must be identical.

Cross-track error is unsigned nearest-distance to the dense XY polyline,
measured at all uniformly spaced72Hz poses including start/final.
Clipping fraction means the raw PP output differs from applied output.
Bound occupancy is reported separately: constant v0.2m/s is at its upper
bound without necessarily being clipped. Ratios use command-record counts.

Three focused tests cover projection/interpolation, PP formula and signed
clipping, monotone progress and endpoint stop. Replay itself provides the
required integrator and continuous-clearance check.

## Output and commands

New output only:
`artifacts/phase0/phase0b_s0_pure_pursuit_01/` under the workspace root.

```bash
bash research/python.sh -m pytest -q research/tests/test_pure_pursuit.py
bash research/python.sh -m nomad_phase0.validate_follower run --output /home/gpuadmin/Workspace/NoMaD/artifacts/phase0/phase0b_s0_pure_pursuit_01
MPLCONFIGDIR=/tmp/nomad-phase0b-mpl PYTHONPATH=research /usr/bin/python3 -m nomad_phase0.validate_follower plot --output /home/gpuadmin/Workspace/NoMaD/artifacts/phase0/phase0b_s0_pure_pursuit_01
```

Both entry points reject existing output files. Plotting uses already
installed system Matplotlib; the existing NoMaD environment is not modified.
Files:

- `follower_settings.json`, `provenance.json`, `output_hashes.json`.
- `reference_replay.json` and `pure_pursuit.json`.
- `reference_xy.csv`, `reference_pose_72hz.csv`,
  `reference_primitive_commands.csv`.
- `pure_pursuit_pose_72hz.csv`, `pure_pursuit_commands_9hz.csv`.
- One XY comparison figure (`path_comparison.svg`, PNG preview of same figure).

## Research decisions and scope

All four research-plan section7 items remain **UNDECIDED**:

1. 주 실행기를 trajectory follower로 변경할지.
2. Recovery에서 후진 허용 여부.
3. Oracle geometry 또는 depth 기반 안전 인식.
4. 언어 지시를 받는 VLA 필수 여부.

The original NoMaD/Topomap/PD/Graph/runtime/scenarios, earlier feasibility
results and raw data are preserved. No Isaac Sim, GPU inference, obstacle
avoidance planner, safety controller, reverse recovery, batch runner,
S1/S2/S3 experiment, parameter sweep or environment installation is included.
