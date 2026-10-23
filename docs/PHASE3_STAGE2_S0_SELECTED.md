# Phase 3 Stage 2: selected S0 speed / Graph comparison

Base `d99d3e8`, branch `research/phase0-infrastructure`. This is an N=4 selection experiment with oracle static geometry and SE(2) kinematic Isaac Sim, not evidence of general Graph superiority.

## Frozen implementation

`research/nomad_phase3_stage2/protocol.json` fixes the 15-run matrix. D750 index 1 CURV-SPEED / HORIZON-SPEED / GRAPH are the three included technical pilots. Remaining jobs: D750 indices 2–4 (three methods each), then D0 GRAPH indices 1–3. RAW reuses Stage 1; no new RAW run. Seed is `101 + 10000*index + 2*request_id`, DDPM +1.

The original PP computes the target and curvature. A separate opt-in applied-command wrapper changes speed only, or replaces the world path after an accepted Graph result. Original PP, PD, NoMaD, Topomap, Graph v4 and its weights are unchanged. The timing core still applies FRESH at the first eligible 9Hz tick and expires the waypoint one second after release. Endpoint/invalid/missing/timeout stops remain unchanged; active moving commands use 0.05–0.2 m/s and acceleration 0.5 m/s².

HORIZON-SPEED uses the literal nearest projection to measure remaining arclength, and elapsed simulation time since the actual FRESH switch: `max(0.998-elapsed, 0.1)`. CURV-SPEED and GRAPH use the existing v3/v4 curvature speed rule. Both preserve angular clipping at ±0.4 rad/s.

Each GRAPH FRESH immediately applies its raw observation-anchored sample 0 and submits one job with the actual switch pose B, previous applied command, and last accepted corrected path. The unchanged v4 runs in the existing external CPU worker. One serial FIFO processes every switched FRESH; the queue's 512 slots exceed the 361-capture bound of a 90-second run. Control never waits. Queue/IPC delay, optimizer time, processing time (setup + solve + certificate), and movement until result handling are logged separately. Processing >0.5 seconds is STALE. Newer received FRESH takes precedence as SUPERSEDED; the stale flag is also retained. Terminal pending jobs are logged and cannot move the agent.

Only convergence + original constraints + original exact certificate allow replacement at the next eligible controller tick, and only while the same FRESH remains valid. Graph does not reset timeout or alter original observation anchoring. The corrected path is not re-anchored to the later application pose. A zero previous speed retains v4's initialization rejection; no fictitious curvature is substituted. No safety-stop or recovery is added.

## Execution boundary

Run `nomad_phase3_stage2.batch --pilots` only once at a new root. A later `--remaining` invocation requires all three pilot technical validations, a clean checkout, unchanged frozen source/input hashes, and no previous remaining attempt. It launches exactly 12 jobs serially. Failed jobs are preserved; no retry/resume of an interrupted remaining invocation. A documentation/result-only commit between pilots and remaining runs is permitted because execution source hashes are fixed and both Git SHAs are recorded.

The requested superiority criterion is frozen: GRAPH D750 successes exceed the best simple speed baseline by at least two; its successful-run median goal time is at most 1.2 times the fastest median among speed methods with successes; D0 GRAPH success count is at least Stage 1 RAW at the same three indices. If neither speed baseline succeeds, the time criterion is unavailable, not an automatic pass. Full comparison and the requested overlay are deferred until the user completes the remaining runs.

## Preflight

Eight targeted/legacy tests passed: speed bounds/acceleration, horizon time, opt-in gates/seeds/matrix, original D0 behavior, Graph result/supersession/staleness and unchanged timeout. A synthetic straight-path CPU worker smoke check returned a converged feasible solution; this is IPC/function validation, not navigation evidence. Dry-run contains exactly 3 pilots + 12 remaining jobs. Protected source/checkpoint and all 14 Topomap RGB nodes are hash-validated by the batch preflight.

Pilot technical results will be added after the single authorized execution of each method. No scientific outcome comparison is made at this point.
