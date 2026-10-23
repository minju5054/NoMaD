# Graph v5.1 offline acceptance gate

v5: convergence 128/201 (63.7%), acceptance 91/201 (45.3%), solve median/p95 117.1/261.3ms; v5.1: convergence 101/201 (50.2%), acceptance 88/201 (43.8%), solve median/p95 155.7/301.3ms; STOP

The preregistered acceptance gate was not reached. No navigation, inference, retry, tuning or pilot command was generated. All 201 attempted inputs are preserved: 200 solver calls and one initialization rejection, retained in the denominator. Four minimal tests passed before the single campaign.

The v5.1 implementation is isolated in `graph_v51.py` and `v51_policy.py`; v5/v4 objectives, weights, controller and existing runtime stay unchanged. No v5.1 navigation gate was enabled because the offline result is STOP. Existing v5 fallback already used the CURV-SPEED formula; the new policy makes that identity explicit and applies temporal acceleration limits to interpolated Graph speeds.

This is conditional acceptance on recorded v5 poses and clocks, not v5.1 closed-loop execution. Measured CPU processing is mapped onto saved dispatch clocks with the stored IPC overhead and a serial worker. Warm starts use only previously accepted v5.1 replay results available at dispatch. Read-only future poses are used only after each solve for application checks.

Both one-/two-tick candidates are frozen before the solve. The optimizer uses the causally estimated candidate; the acceptance distance uses the candidate matching the actual replay application tick. The fixed optimizer boundary is never replaced afterward. A mismatch between estimated and actual ticks is recorded separately and does not certify exact boundary continuity.

Original v5 run data, pilot report and the preexisting untracked `research/results/phase4_pilot/` directory were preserved. No automatic pilot/batch/report extension follows this STOP.
