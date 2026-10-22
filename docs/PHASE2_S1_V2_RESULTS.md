# Phase 2 S1-v2 — revised N=4 exploratory results

55 navigation attempts completed on 2026-10-22: 3 integration pilots, 4 obstacle-free references, 16 M0 runs and 32 paired M3/M5 runs. No navigation retry, seed change, tuning or Stage2c run. Main execution used clean `f9f1f0ffec5d9062c767b13a725d8ddfd41041c2`; protocol/implementation history is `c6dabc6`, `8257de6`, `f9f1f0f`. Raw files remain at `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/p2_01/`.

This is exploratory N=4 per condition, oracle geometry evaluation, and Isaac RGB closed-loop SE(2) kinematic navigation. It is not a PhysX robot experiment or evidence of statistical superiority or Graph necessity. Same seed offset does not produce identical closed-loop observations, paths or adaptive obstacle positions.

## Protocol and technical verification

M1 excluded. M3/M5 execute unchanged sample0 with the original constant-speed PP, including ALL_UNSAFE fallback. Only sample replacements or accepted Graph outputs use variable speed. There were **zero interventions before spawn**. Checkpoint, 21-node Topomap, NoMaD, original PP/PD, Graph v4 source/weights, geometry/integration helpers and previous experiment inputs retained their protected SHA-256 hashes.

All 55 saved-data audits passed. Actual PP command replay, 72Hz integration and held-command trace errors were exactly0. All seeds, observation anchoring, input-history hashes, selection logic and post-packet delays passed. An independent pass recomputed3,896 dynamic-scene RGB magenta masks and visibility flags. The next-capture publication rule matched the saved observations. Absolute pacing error over80,556 poses: median0.101ms, p950.156ms, max21.340ms; this is soft real-time, with an occasional over-one-tick excursion.

Stage0 did not naturally exercise selection/Graph intervention; those branches had synthetic checks and worker startup validation. Main runs subsequently exercised real Graph solve, acceptance, rejection and application. No real stale result or waypoint-timeout event occurred; these remain synthetic-only coverage. The first pilot's initial audit rejected a8.67e-19m NumPy-version roundoff in an exact equality check. Only the offline comparison was corrected to1e-12, and the same saved run passed. Original failure and amendment remain preserved; no pilot was rerun.

## Delay-only reference and success table

Stage1 M0: D250 **2/2** success (40.889,40.472s); D500 **2/2** success (42.611,41.222s). No observed delay-only failure in this N=2 reference. D0 reused the existing S1-v2 reference; it was not rerun.

Success below means goal entry without geometric overlap/corridor intrusion. The2cm margin is evaluated separately.

| d (m) | D (ms) | M0 | M3 | M5 |
|---|---:|---:|---:|---:|
|0.8|250|0/4|0/4|0/4|
|0.8|500|0/4|0/4|0/4|
|1.0|250|1/4|1/4|0/4|
|1.0|500|0/4|0/4|0/4|

Wilson95% intervals:0/4 →[0,48.99%];1/4 →[4.56,69.94%]. They describe uncertainty only. Full success/collision/timeout intervals and continuous summaries are in [conditions.csv](../research/results/phase2_s1_v2_20261022/conditions.csv).

| Main-run outcome, n=16 per method | M0 | M3 | M5 |
|---|---:|---:|---:|
|Goal success|1|1|0|
|Confirmed geometric overlap|15|15|15|
|90s timeout|0|0|1|
|Corridor intrusion|0|0|0|
|Runs violating2cm margin|15|16|15|
|Goal success retaining2cm margin|1|0|0|
|Native sample0 unsafe decisions|15|22|16|
|Actual nonzero-sample switches|0|9|3|
|ALL_UNSAFE decisions|8|13|12|

M5 selected a nonzero sample4 times but applied it3 times; one request remained pending at collision. Its timeout run passed the box on+Y without collision (minimum clearance0.14266m), then failed to reach the goal by90s; it had no sample replacement or Graph call. M0/M3 successful runs also passed on+Y. No conservative-contact-only stop or technical navigation failure was observed.

## Paired16 classification

| Pattern | Count |
|---|---:|
|All succeed|0|
|M0 fails, M3 succeeds|0|
|M3 fails, M5 succeeds|0|
|All fail|15|
|M0 succeeds, M3 or M5 fails|1|
|Both B0/B1 searches have no witness at first-visible FRESH B|0|

All48 main runs had B0 and B1 goal-reaching witnesses both at spawn and at the first obstacle-visible FRESH's actual B:192 verified searches. No case was excluded as unrescuable. Bounded search failure would not have proved impossibility.

Paired M3−M0 success difference is0 in every condition. M5−M3 is−25percentage points at d1.0/D250 (fixed-seed paired bootstrap95%:[−75,0]); other conditions are0 with empirical bootstrap[0,0]. The degenerate intervals from four equal observed differences do not establish equivalence. There are **zero Graph-associated success patterns**, and no demonstrated case requiring Graph.

## Actual intervention and failure pattern

Only d1.0/D250/index1 (offset10000) has M0 success and M5 failure. See [recorded paths](../research/results/phase2_s1_v2_20261022/individual_paths.png) and [case analysis](../research/results/phase2_s1_v2_20261022/case_analysis.json).

- **M0:** no intervention; goal at41.5278s, minimum clearance75.51mm.
- **M3:** FRESH28 replaced sample0 with sample1 (world XY RMS difference26.30mm, no path editing). Goal at41.2083s, but minimum clearance9.365mm and0.5556s below margin. First violation at16.8472s while executing unchanged sample0 FRESH31.
- **M5:** Graph FRESH27, initialized from sample1, applied at14.5556s: RMS edit20.59mm relative to selected sample (71.57mm relative to sample0). Graph FRESH31, initialized from sample0, applied at16.2222s: RMS edit104.52mm, initial applied command(0.14444,+0.4). Its actual execution reached12.874mm clearance; first margin violation occurred at16.4722s. FRESH32 Graph was rejected; sample0 fallback applied at16.5556s, then overlap at16.625s (minimum−0.314mm).

Thus the observed Graph31 path certificate did not ensure actual PP execution margin, and subsequent RAW fallback collided. The three runs already differed in observation/trajectory before intervention and spawned slightly different world Y boxes. This is an adverse paired pattern, not proof that Graph alone caused the outcome. No counterfactual rollout or new optimization was run for this analysis.

## Graph, timing and discontinuities

16 calls:15 returned,7 accepted and actually applied,8 nonconverged,0 initialization rejection,0 stale. One call ended pending when OLD execution collided; it is neither a convergence failure nor a stale result. No correction reached a successful goal run.

Solver wall time over15 completed solves: median91.72ms, p95185.60ms, max190.30ms. Dispatch-to-result (including worker/field/certificate/IPC): median107.39ms, p95199.49ms, max209.96ms. OLD movement during completed calls: median22.22mm, max44.44mm. B is fixed at actual controller-tick dispatch; CPU start/queue timing is recorded separately. Corrected paths are not reanchored at application. M5 total Graph-wait interval time was2.514s across16 runs; original1s timeout semantics remained active.

| Actual successive FRESH switches | M0 | M3 | M5 |
|---|---:|---:|---:|
|Median abs Δω (rad/s)|0.15592|0.15366|0.14622|
|p95 abs Δω (rad/s)|0.80000|0.76174|0.76594|
|Max abs Δω (rad/s)|0.8|0.8|0.8|
|ω sign reversals|282|275|322|
|Curvature-saturated evaluated PP ticks|111/2342 (4.74%)|108/2349 (4.60%)|148/2775 (5.33%)|

Switch statistics exclude the first applied FRESH and include subsequent actual STOP-to-motion transitions. Tick flags exclude missing/expired commands, endpoint stops and Graph hold ticks where PP curvature was not evaluated. These pooled descriptive values are not a paired causal comparison; M5 contains a90s run.

## Limits and remaining issue

7/16 M0,6/16 M3 and7/16 M5 runs collided without any native sample0-unsafe decision. The public native-path criterion can therefore miss actual PP execution risk. Even accepted Graph paths did not guarantee executed margin at a moving application boundary. Online execution-aware risk/acceptance is the central unresolved issue; no new controller, Graph formulation or experiment was added.

The inherited capture-layer `oracle_information.used_for_control=false` field is a Phase1 metadata label and is not authoritative for Phase2 usage. Actual usage/publication is logged in `phase2_decisions.geometry_available/public_obstacle_ids` and `phase2_oracle.jsonl`; these timestamps were audited. Raw labels were preserved, and this limitation must be respected when reusing the dataset.

Small results are in [research/results/phase2_s1_v2_20261022](../research/results/phase2_s1_v2_20261022). `runs.csv` retains run-level seed/SHA, timing, actual boundary, clearance, passage, feasibility and interventions; `graph_results.csv` retains every returned Graph result. Large RGB, model outputs and original traces remain outside Git. Results are fixed; no retry or additional sweep is implied.
