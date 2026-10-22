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

Pending actual RGB generation and the single navigation. Navigation must start from a clean committed checkout after validating reference/map poses, RGB hashes, checkpoint and settings. Saved PP commands will be re-evaluated at the actual controller poses, all 72 Hz intervals re-integrated, and corridor bounds recomputed independently. Existing normalization, checkpoint coverage, clock, timeout and history validators will be reused. No additional visualization is planned.
