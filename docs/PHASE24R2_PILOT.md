# Phase24-R2 endpoint return pilot — preregistration

Base commit: `d133909`. L2 only, G/C0/C1, paired seeds151–154 (offset10000×index), twelve new runs. Existing Phase24/R code, outcomes and labels are preserved. C1 is descriptive. No tuning; exact simulator odometry. The single L2seed95G technical smoke is excluded from results. Main execution is user initiated.

## Only method change

G DETOUR adds $J_{lat}=((p_{10}-a)^Tn/0.30)^2$, with weight1, $n=(-u_y,u_x)$ and existing unit direction $u=u_{ref}$. Its xy gradient is $2((p_{10}-a)^Tn)n/0.30^2$; all other variable derivatives are zero. Coordinates are transformed exactly into the predicted-start frame.

For the existing component-based direction, $a$ is the robot pose position at the component's depth-derived `t_new_tick`. Without a component, $a$ is the actual position when DETOUR starts. It is captured once per detour, never re-anchored at the predicted pose or taken from oracle spawn. The unchanged direction selector decides which source applies. Every DETOUR job/result logs the full line, source and anchor tick.

NORMAL is bitwise unchanged. Progress1.2m, obstacle node/midpoint constraints and soft cost, kinematics, time, curvature, initializations, 0.5s anytime rule, output/live continuous certificates, chord-priority rotation, persistent-component trigger, recovery, fallback and goal tolerance inherit Phase24-R. C0/C1 inherit their exact Phase24-R execution factory. Methods receive no oracle geometry.

## Fixed decision

Pilot `R2_PASS` iff G goal successes ≥ C0−1 AND G collisions=0 AND G box passages ≥ C0−1; otherwise `R2_FAIL`. Collision uses the frozen Phase24-R oracle obstacle/wall geometric-overlap metric; margin-only corridor stops remain separately reported. Technical failures remain visible and unsuccessful, with no retry or result-based changes.

## Metrics

All Phase24-R audit metrics remain in runs.json/execution.csv. Added: maximum |y| during accepted detour execution; |y| exactly five seconds after box passage, linearly interpolated from72Hz poses (missing if the run ends earlier); and closest-node progress after each actual detour handover. The latter is last observed closest index at handover+5s minus last at handover, with incomplete-five-second windows flagged and run-end progress also reported. Run termination during a detour is not invented as a handover. No missing observation is extrapolated.

## Validation and execution

15/15 tests passed (7new,8frozen R regression). Tests cover line anchors, rotated-frame analytic gradient within1e−5, unchanged NORMAL/constraints/runtime constants, an obstacle blocking the return line with a feasible certificated detour using the unchanged seven starts and SLSQP options, new metrics and a synthetic twelve-run report.

One excluded G smoke completed technically: command-to-pose error 0m, USD/evaluation wall error 7.45e-10m; 20 DETOUR jobs transported the fixed return line. The smoke outcome is not used to change any factor or criterion. Maximum socket length 90bytes. Estimated campaign wall time 48.9minutes including report.

Full RGB/depth retention is seed151 only; the other seeds keep the frozen compact metrics/map/archive policy. Disk guard requires estimated remaining storage plus20GB before every run. At freeze: expected 27.23GB, required 47.23GB, available 38.79GB. If insufficient, the campaign stops before launching the next run without modifying data.

Protocol and source SHA256s are frozen in online_protocol.json; old sources are checked as well. The campaign uses the Phase24-R lock/resume/atomic metadata structure and generates, commits and pushes this report after the twelve runs.
