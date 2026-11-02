# Phase23-O execution failure diagnosis

The saved traceback identifies TypeError in exact_clearance: a JSON list path was passed to an ndarray-only subtraction. All workers exited after the exception. The old state writer had no exceptional/signal cleanup, leaving TRAINING TS0000/PID2009915 behind. The last state update was07:08:36.923UTC and the traceback log was last written07:08:37.223UTC.

Direct dmesg access was denied; sudo required a password. The accessible kernel journal for16:00–16:10KST (covering the failure) contained no OOM/out-of-memory/killed-process/Python match. This does not assert unrestricted access to the full kernel ring buffer.

Fix scope: ndarray conversion; FAILED state with exception/signal/context; dead PID/start-token reconciliation for uncatchable exits; combination/substage journal; persist each plan before postprocessing; watchdogs and worker cleanup; explicit numerical rotation/tick bounds. Original grid, methods, factor constants, warm-start definition and selection criteria match4916cbf. Normal guarded baseline and U rotation traces match the frozen implementation exactly in tests. All16tests pass.

Algorithm time budgets remain250ms U and frozen comparator budgets. Operational watchdogs5s solve/10s comparator/30s rollout/60s oracle/10s exact clearance detect wedged code as technical failure and halt; they do not turn it into a scored algorithm failure. The existing rotation tolerance0.001rad is unchanged. Rotation/tick caps are derived from the existing motion and termination bounds. SIGKILL/OOM cannot run Python finally; status inspection detects a dead process and records an unobserved exit.

## TS0000 serial diagnostic — excluded from training

| combination | solve_wall_s | ROLLOUT | ORACLE | EXACT_CLEARANCE | wall_s | accepted | rollout_ticks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| U00 | 0.2774 | 5.6959e-05 | 0.00089501 | 0.024857 | 0.3204 | False | 0 |
| U01 | 0.27468 | 3.1451e-05 | 0.00043853 | 0.024946 | 0.30862 | False | 0 |
| U02 | 0.27521 | 2.9426e-05 | 0.00040604 | 0.025105 | 0.30183 | False | 0 |
| U03 | 0.27482 | 2.7512e-05 | 0.00043278 | 0.026626 | 0.31045 | False | 0 |
| U04 | 0.27557 | 2.9457e-05 | 0.00043391 | 0.025012 | 0.31007 | False | 0 |
| U05 | 0.27469 | 2.7973e-05 | 0.00040802 | 0.025566 | 0.30924 | False | 0 |
| U06 | 0.27491 | 3.9996e-05 | 0.00044163 | 0.026242 | 0.31029 | False | 0 |
| U07 | 0.27491 | 4.3132e-05 | 0.0006226 | 0.02478 | 0.31824 | False | 0 |

Eight combinations were solved exactly once in one process: total2.489141s. All eight exceeded the unchanged algorithm deadline and produced STOP with0rollout ticks; this is not the registered four-process performance or a tuning result. No weights were selected.

Therefore the initial87-minute projection was insufficient for active trajectory evaluation. Without further graph solves, throughput was measured on the full existing TS0000 source-run trace (2378intervals) and a synthetic2m rollout.

| saved_trace_intervals | saved_trace_oracle_s | oracle_s_per_tick | synthetic_rollout_ticks | synthetic_rollout_s | rollout_s_per_tick | new_graph_solves | new_model_inference |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2378 | 0.53153 | 0.00022352 | 685 | 0.013038 | 1.9034e-05 | 0 | 0 |

| component | seconds |
| --- | --- |
| U_planning_s | 767.02 |
| baseline_planning_allowance_s | 1898.6 |
| postprocessing_s | 3756.1 |
| timestamp_replay_s | 483.25 |
| report_io_allowance_s | 120 |

Including25% allowance: **2.439hours (146.4minutes)**. Strict R2 trust-box geometric upper allowance: 3.821hours. This is a conservative single-case scheduling extrapolation, not a guaranteed duration.

**STOP: estimate exceeds2hours. No full-run command or automatic dataset/grid reduction is supplied. Original full-run completed training combinations remain0; diagnostic files are separate.**
