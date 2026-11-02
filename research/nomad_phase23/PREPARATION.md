# Phase23-O — registered and ready for user-run offline evaluation

Tests11/11 PASS; early/middle/late saved V1 occupancy+observed replay exact; fake-data selection report, final tables and figures PASS. Real training/evaluation solves:0. No experimental decision yet.

Approved: arclength-interpolated graph speed with PP; explicit graph rotation for v<0.01; bounded stop; arrival-driven nominal4Hz replan with U-only warm start. Short candidates are retained, active-short fractions and conditional forward output are reported. Fixed nonholonomic sigma0.03m. Timing gate precedes collision/failure/rank-sum/p50 tuning selection; all-over-budget chooses minimum p95 and flags it.

Training216static+26sudden, evaluation795static+34sudden. Eight weight combinations. Cases are replayed chronologically per run/configuration; cached results rebuild the warm state on resume without resolving completed cases. Offline inputs are sparse recorded candidates, not a fabricated4Hz closed-loop stream. Previous A*-derived repair paths are withheld from U supplementation.

The user-run staged runner will write selection evidence into protocol.json and the report, commit FROZEN weights, then evaluate. It will generate the final report and commit/push when called with --publish. A separate output lock prevents concurrent runs. Existing phase files and original data remain read-only.
