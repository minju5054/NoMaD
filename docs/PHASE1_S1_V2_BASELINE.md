# S1-v2 obstacle-free baseline pilot

This is a single baseline preparation pilot in `SE(2) kinematic Isaac Sim`, with passive oracle corridor evaluation. It does not test delay robustness or sudden-obstacle avoidance.

## Frozen before rendering/navigation

- Scenario: `research/nomad_phase1/s1_v2_scenario.json`; protocol: `s1_v2_protocol.json`.
- Start `(0,0,0)`, goal `(8,0,0)`, XY tolerance 0.30 m; corridor X [-1,9], Y [-1.5,1.5] m; no static/dynamic obstacles; radius 0.09 m. Obstacle clearance is **not applicable**, not a measured large clearance. Corridor footprint checks remain active.
- Reference: exact existing SE(2) integration at 72 Hz with `(v,w)=(0.2,0)`, ending at first actual integrated pose in goal tolerance. RGB at 0,2,4,... simulation seconds plus terminal pose; no policy navigation/inference during reference generation.
- Existing camera, lights, floor/wall materials and thickness, 0.5 m floor seam spacing and 1.5 m panel cadence retained. Corridor length extends to 10 m; existing panel locations/colours remain and brown panels at X=6.5,8 m extend the pattern. End wall/door move to the new corridor end. No result-based visual changes.
- Navigation: one attempt, zero retries; NoMaD sample 0, native 8 XY points, original 10 diffusion steps, seed 101+2×request ID (DDPM +1); PP lookahead 0.25 m, v=0.2 m/s, |w|≤0.4 rad/s, 4/9/72 Hz, 1 s timeout; explicit uniform post-packet delivery delay D=0; max 60 simulation seconds. No Graph, recovery, dynamic obstacle, or safety override.
- Official Topomap radius=4 / close_threshold=3; selection uses RGB and learned distance scores only. Reference pose metadata is excluded from worker map inputs. No fixed 14-node assumption for this new map.
- S0/S1-v1 restrictions, reference manifests, checkpoint, PP, original PD and NoMaD output semantics remain unchanged. S1-v2 permits only this D=0 pilot, without seed offsets or batch runner.

## Validation and results

Actual RGB generation passed: 21 nodes at 0,2,...,38 s plus terminal 38.5 s (x=7.700000000000565 m), from 2,773 exact-integrated poses. All PNG/pixel hashes, USD poses (zero maximum error), source hashes, checkpoint and 304 protected files passed. Relevant minimal tests: 32 passed. Reference/render code commit: `593b77a`. The single navigation ran from clean commit `b7e4b2acbafae22419e1148730f1623b3d0b8151`. Saved PP commands were re-evaluated at the actual controller poses, all 72 Hz intervals re-integrated, and corridor bounds recomputed independently. Existing normalization, checkpoint coverage, clock, timeout and history validators passed. No retry, parameter change or new visualization was performed.


## Actual D=0 result

| Measurement | Result |
|---|---|
| Goal entry / termination | True / `goal_entry`, 41.833333 s |
| Final pose / XY goal distance | (8.082742, 0.287711, -0.564044 rad) / 0.299372 m |
| Travel / stopped time | 8.144443 m / 1.111111 s (initial wait only) |
| Obstacle collision / clearance | No obstacles; clearance N/A |
| Corridor intrusion / minimum footprint clearance | False / 0.827256 m |
| Request / receive / actual switch | 164 / 164 / 163; ID163 terminal received but unapplied |
| RGB captures / busy skips / missed slots | 168 / 1 / 0 |
| Waypoint timeout | 0 episodes; exact-timeout unit test passed, no natural timeout exercised |
| Cold GPU inference | 268.613 ms |
| Warm GPU inference median / p95 | 35.217 / 37.353 ms |
| Observation→ready median / p95 | 71.953 / 122.286 ms (capture-start host clock) |
| Observation→switch median / p95 | 137.929 / 166.203 ms (host clock) |
| D0 packet→release median / p95 | 10.656 / 18.152 microseconds; IPC overhead, no intentional wait |
| Pacing absolute error p95 / max | 0.154 / 1.356 ms; real-time factor 0.9999976 |
| PP command / pose integration maximum error | 0 / 0 |
| Checkpoint parameter coverage | 100%; no missing/unexpected keys |

All 164 raw/derived outputs retained `(8,8,2)` finite metric trajectories with exact recorded normalization/cumsum/scaling and sample0/index2 reference selection. PP actually used the observation-anchored sample0 path. Each selected RGB hash, four-frame worker history hash and observation/switch pose association passed. All 304 protected hashes and 15 frozen source hashes were unchanged. Model, original PD, PP settings and existing raw results were not modified.

Topomap ended at closest/subgoal 20/20 (final node). Closest node moved backward 3 times (IDs15,36,144); subgoal moved backward 9 times. Six of the subgoal backward changes occurred with unchanged closest node when its minimum learned score crossed from <3 to ≥3 (IDs27,43,51,57,136,152). The other three coincide with argmin closest changes. Every selection exactly matches the official rule. These are observed selection fluctuations, not evidence that a particular perception or diffusion failure caused them; the scores are not metric distances. No threshold or feature tuning followed.

The obstacle-free scene, new map and D0 closed-loop baseline passed technical validation and goal entry. They can support the next separately specified D×N=5 baseline task. This implementation intentionally permits only D0/offset0: broader delay conditions, seed schedule and batch execution still require their own protocol/mode extension. Neither delayed navigation reliability nor sudden-obstacle avoidance is established by this one run.

## Saved artifacts and reproduction

- Raw/reference/map/run/audit: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/s1_v2_baseline_01/`.
- Small results and node metadata: `research/results/phase1_s1_v2_baseline_20261022/` (preflight, summary, per-request Topomap selection, input hashes and interpretation).
- Scenario SHA256: `3bbb2e210af9ca7e5e712aca95994cfb7dcba547a6367a894d4d1f4992857096`.
- Topomap SHA256: `0d80ec037e2fa14264d9276f010efea2764c6bf269ac81f1bfb21f294d14cb0a`.
- Checkpoint SHA256: `70f79b8262527e20e56ced64a3e3d7ef91855bc9e7c3fa348d78edcb83c6a333`.
- Existing Isaac6.0.1-rc.7, RTX5060Ti16GB, driver595.99.02, PyTorch2.7.0+cu128 / torchvision0.22.0+cu128 / Diffusers0.11.1. No environment install/change.

The one executed navigation command (do not repeat against the existing output) was:

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV bash research/python.sh -m nomad_isaac.launch --s1-v2-mode --scenario research/nomad_phase1/s1_v2_scenario.json --asynchronous --pure-pursuit --topomap /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/s1_v2_baseline_01/render/topomap/manifest.json --uniform-delivery-delay-s 0 --output /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/s1_v2_baseline_01/run
```

First-start RTX shader compilation preceded the navigation clock. Real-time pacing statistics above cover actual kinematic execution, not startup or reference rendering. GUI/video/figures, Graph, dynamic obstacles, recovery and further navigation were not added.
