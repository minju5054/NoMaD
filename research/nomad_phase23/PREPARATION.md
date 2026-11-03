# Phase23-O — FROZEN configuration; ready for user-run tuning/evaluation

User decision2026-11-03: adopt454static+34sudden=488evaluation snapshots. Training242snapshots×8weights and failure-window5samples/run are unchanged. Prior829-case manifest and context are archived under registration_history. Estimated full staged run: about2h08m, explicitly approved despite the earlier2h threshold.

Planning:8policy+available side initializers,4workers,500ms anytime. Factor definitions/grid/SLSQP options and optimized.py remain unchanged. Predict using the existing rollout/controller, not constant-speed motion. U applies at exactly0.5s; C0/C1 SAFE_SAMPLE switches remain at saved B, while R2/R3/A* use measured computation within1s. During computation the installed OLD path continues. A missing U solution causes braking only after0.5s. Application pose/time tests compare the actual prefix with the frozen rollout.

Configuration status is FROZEN, weights_status is PENDING. The runner must train all242cases, commit the selected weights/selection evidence, then evaluate488cases and generate/commit/push the report. No training or evaluation has been run.32pre-freeze tests pass; repeat the same suite after the freeze commit before releasing the command.

No synthetic4Hz feedback is created from sparse snapshots. Saved OLD XY inputs use the common PP/SP executor and current speed; explicit OLD pose/dt inputs use the existing graph-speed executor. Missing native timing is not fabricated. No extra start-alignment trigger is introduced for an already installed path.
