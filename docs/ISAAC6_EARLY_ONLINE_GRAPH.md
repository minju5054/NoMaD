# Early fixed obstacle + online Graph: frozen two-run protocol

2026-10-20. Runtime base `a76ed2b`; Graph source `3a60531`.
Branch `research/isaac6-early-online-graph`.

## Scenario and scope

New `early_obstacle_scenario.json` fixes the dynamic box center to
`(2.372279542,0.110674603) m`, size `(.35,.35,.8) m`, spawn tick792/11.0s.
The original actual-OLD adaptive-placement scenario and its frozen validation
are unchanged. A separate mode validates only the new scenario hash and the
unchanged 14-node Topomap. All model/PD/seed/4·9·72Hz/timeout/goal settings remain
unchanged. Maximum navigation time is 60 simulation seconds, extra delay zero.
Fixed dynamic visibility uses existing USD time samples and RGB magenta evidence;
collision activation uses the same tick and box. No instance-mask dependency.

Two conditions, **one navigation each, no retries**:

- EARLY-RAW: original NoMaD/Topomap/PD; no command safety override.
- EARLY-GRAPH: oracle nominal-command check after spawn, STOP and separate CPU
  Graph worker only when a valid nominal command fails the 16/72s safety check.

## Graph action semantics

Only required factor definitions are extracted from the prior branch; their ASTs
are identical. The original factor protocol is copied byte-for-byte.
Eight future SE(2) nodes, fixed current B, unchanged prior/relative/boundary/
tangent/minimum-segment/native-safety/controller-safety residuals and SciPy
solver. First heading uses the same frozen chord variant; invalid initialization
is rejected without a solve. Soft safety target .025m, actual pass threshold .02m.
Each FRESH ID has at most one attempt; no restart or parameter tuning.

The existing `/usr/bin/python3` with SciPy1.11.4 runs the CPU worker.
No packages/environments are changed. No optimization runs on the 72Hz thread.
Only one solve is outstanding. While waiting, actual command is STOP, but RGB
capture, NoMaD inference, nominal FRESH switches and original receive timeout
continue. The worker receives only its sample0, observation pose, fixed B and
currently active geometry. World trajectories retain their observation anchor.

Converged results are accepted only if B is unchanged (component error <=1e-9),
geometry is identical, and a new original-PD rollout check passes.
The corrected world index2 becomes B-local PD input. A **separate Graph action**
holds that command for at most16 integration ticks, rechecking safety at the
intermediate9Hz update; unsafe continuation is cancelled. Then the newest nominal
waypoint is re-evaluated. A pending solve holds STOP even if a newer nominal
waypoint arrives; an accepted bounded Graph action completes before nominal
control resumes. These are explicit stop-and-plan scheduling decisions.

The original one-second timeout applies to nominal NoMaD commands. An older
Graph input may generate a separate accepted Graph action; input/receive age,
solve start/end, result receipt, wait and application times are recorded.
`events.jsonl` retains nominal FRESH switch semantics. `graph_control.jsonl`
records actual source/action ID and command; `agent_trajectory.csv` contains
actual integrated commands. Late results at navigation termination are saved
but never applied. This is not real-time Graph or PhysX robot execution.

## Preflight

- Saved tick792 poses: initial clearance .426326m (static2s reference) and
  .465345m (previous sudden run); center bearing −30.922° / −31.775°, inside
  90° horizontal FOV. Center sight ray has no static-box intersection.
  Box separation .202720m; corridor containment passes.
  These are geometric visibility checks; actual RGB is validated in each run.
- All eight required factor/function AST definitions match the previous source.
- One saved B52 CPU-worker solve: k2, convergence14nfev, wall1.765051s,
  `(v,w)=(.013416543383,+.4)`, clearance .021677381344m.
  Corrected poses/command match the prior offline result within1e-9.
- Focused scheduler/late-result/boundary rejection plus existing
  timeout/activation/frozen-mode tests: **21 passed**.
- Protocol: `early_graph_protocol.json`; preflight artifact:
  `artifacts/isaac6/early_graph_preflight_01/`.

## Commands

Run each once from the committed clean source:

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV bash research/python.sh -m nomad_isaac.launch --asynchronous --early-obstacle-mode raw --topomap /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/topomap_reference_2s_01/topomap/manifest.json --scenario research/nomad_isaac/early_obstacle_scenario.json --output /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/early_raw_01
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV bash research/python.sh -m nomad_isaac.launch --asynchronous --early-obstacle-mode graph --topomap /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/topomap_reference_2s_01/topomap/manifest.json --scenario research/nomad_isaac/early_obstacle_scenario.json --output /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/early_graph_01
```

Actual results will be recorded after the two runs. No outcome-dependent changes.
