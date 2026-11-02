# Solver diagnosis status

30 fixed training-only snapshots were checked before/after mathematically identical caching and vectorization.21tests pass, including F1–F6 finite-difference checks. All250final states are bit-identical; no variant was selected. Improved unbounded single-process best-found p95=0.832s and total p95=1.009s, still above0.25s. **Hold full tuning/evaluation pending user decision.** See docs/PHASE23O_SOLVER_CHECK.md. The main grid, factor definitions,4workers,250ms budget and decision criteria remain unchanged.

# Execution repair status

The initial run failed at exact clearance because a JSON list was not converted to ndarray. This is repaired with failure/signal journaling, combination checkpoints and watchdogs.16tests pass. TS0000 serial8-combination diagnostic is complete and excluded from training; all plans timed out in serial mode, so active evaluation throughput was separately measured from a saved trace and a synthetic rollout without further solves. Conservative full-run scheduling estimate2.439h exceeds the user2h threshold. **STOP: do not resume the full matrix before the user decides scope.** See docs/PHASE23O_EXECUTION_DIAGNOSIS.md.

# Phase23-O — registered and ready for user-run offline evaluation

Tests11/11 PASS; early/middle/late saved V1 occupancy+observed replay exact; fake-data selection report, final tables and figures PASS. Real training/evaluation solves:0. No experimental decision yet.

Approved: arclength-interpolated graph speed with PP; explicit graph rotation for v<0.01; bounded stop; arrival-driven nominal4Hz replan with U-only warm start. Short candidates are retained, active-short fractions and conditional forward output are reported. Fixed nonholonomic sigma0.03m. Timing gate precedes collision/failure/rank-sum/p50 tuning selection; all-over-budget chooses minimum p95 and flags it.

Training216static+26sudden, evaluation795static+34sudden. Eight weight combinations. Cases are replayed chronologically per run/configuration; cached results rebuild the warm state on resume without resolving completed cases. Offline inputs are sparse recorded candidates, not a fabricated4Hz closed-loop stream. Previous A*-derived repair paths are withheld from U supplementation.

The user-run staged runner will write selection evidence into protocol.json and the report, commit FROZEN weights, then evaluate. It will generate the final report and commit/push when called with --publish. A separate output lock prevents concurrent runs. Existing phase files and original data remain read-only.
