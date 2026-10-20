# Topomap + Oracle Safety Stop

2026-10-20. Base `830728850b5f4fc6725c3c33894bf26e1d26df1d`;
branch `research/isaac6-topomap-oracle-stop`. This protocol is committed before
the single allowed navigation. No retry or outcome-dependent parameter change.

## Frozen execution

Unchanged `old_rollout_obstacle_scenario.json`, 14-node 2-second reference
Topomap, checkpoint, sample 0/index 2, original PD, seed schedule, 4/9/72 Hz,
one-second receive-based timeout, and zero extra delivery delay.
Dynamic position comes from the actual OLD command at tick 970.
The existing rendering and collision monitor use that same resolved geometry.

The opt-in `--oracle-safety-stop` runs after `WaypointExecution.control()`.
After successful dynamic spawn, each controller tick evaluates its freshly
computed nominal command over 16 exact 72 Hz intervals. All static and active
dynamic obstacle swept-clearance lower bounds must be at least 0.02 m; corridor
footprint containment must also hold. Otherwise only the actual integration
command becomes `(0,0)`. Next tick re-evaluates; RGB/inference and waypoint
receipt/switch clocks keep running. Missing/expired waypoint stops are separate.
Before spawn, commands pass through unchanged.

`controller.jsonl` and `events.jsonl` retain nominal `v_m_s,w_rad_s`; new
`applied_v_m_s,applied_w_rad_s` fields describe the command actually integrated.
A waypoint switch can occur while its execution is blocked. `safety_stop.jsonl`
stores every controller tick, pose, validity, nominal/actual commands, current
and predicted clearance, reasons, and evaluation times. `agent_trajectory.csv`
retains incoming actual interval commands. An already violated current margin
is explicitly flagged and cannot be repaired by STOP.

This is an exact-scene-geometry **oracle baseline**, not camera-based safety
perception, trajectory reconciliation, or PhysX/real robot dynamics.
Classification and all numerical settings are frozen in
`research/nomad_isaac/oracle_safety_stop_protocol.json`.

## Pre-run validation

Saved baseline B52, same 16/72 s horizon:

| Command | Minimum swept clearance | 2 cm decision |
|---|---:|---|
| RAW `(0.1668959856,+0.4)` | 0.002653804024 m | block |
| STOP `(0,0)` | 0.023340344453 m | safe |

RAW replay matches all 16 stored 72 Hz poses exactly (maximum error 0).
Two new focused gate tests plus existing asynchronous/placement/combination
tests: **23 passed**. Original timeout, safe FRESH resume, unchanged waypoint,
and preexisting violation semantics are covered. Reference 14 node RGB/pose
hashes pass; 745 prior preservation entries remain unchanged.

Preflight artifact: `artifacts/isaac6/topomap_oracle_stop_preflight_01/`.
Single navigation output: `artifacts/isaac6/topomap_oracle_stop_01/`.

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV bash research/python.sh -m nomad_isaac.launch --asynchronous --oracle-safety-stop --topomap /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/topomap_reference_2s_01/topomap/manifest.json --scenario research/nomad_isaac/old_rollout_obstacle_scenario.json --output /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/topomap_oracle_stop_01
```

Actual outcome will be appended after this single run and saved-log validation.
