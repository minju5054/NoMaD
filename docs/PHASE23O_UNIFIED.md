# Phase23-O — FROZEN preparation; NOT_EVALUATED


## Input/output and pipeline

| Component | Input / output |
|---|---|
| U input | Eight observation-anchored NoMaD XY candidates; available depth V1 SDF; current pose/speed and executing path; OLD remainder for short-candidate supplementation |
| Computation motion | Continue the current path for0.5s; predict application pose and speed without future observations. The same prefix is included in rollout safety/progress evaluation. |
| U solve | B-local poses $x_0\ldots x_{10}$ and ten $\Delta t$; four-worker SLSQP multi-start; no oracle, Topomap pose, trigger, progress history, u_ref or A* input |
| U output | Eleven world SE(2) poses and ten time intervals; graph segment speeds → PP direction at lookahead0.25m; separately registered handling of pure graph rotations |
| Evaluation only | Oracle rotated boxes/walls, Topomap next-node metadata, recorded trigger membership |

| Current rule | Unified counterpart |
|---|---|
| FRESHEST + candidate rejection | F1 selects a max-mixture component inside the objective; all8 candidates retained |
| Depth safety filter | F2 point/midpoint constraints and clearance preference |
| SP + heuristic start alignment | F3 pose/time kinematics; PP + graph speed; no heading-threshold alignment rule |
| Trigger/u_ref detour target | F5 active NoMaD candidate endpoint, applied at every selected snapshot |
| Detour handover | Single finite trajectory; no online handover trigger in U |

## Factor definitions

Let $p_i\in\mathbb R^2$, $\theta_i\in\mathbb R$, $\tau_i=\Delta t_i$;
$p_0=0,\theta_0=0$ in the predicted application-pose frame. The prediction horizon is0.5s from the current snapshot. The supplied SDF already subtracts radius0.09m; it is **not subtracted twice**.
All distances are metres and times seconds. $R_Bp_i+b$ transforms queries to world coordinates.

F1: $j^*=\arg\min_{j\in0..7}\sum_{i=1}^{10}\|p_i-\hat p_{ji}\|^2/\sigma_p^2$ (ties: smallest index).
$\sigma_p=\operatorname{clip}(\operatorname{median}_i\sqrt{\operatorname{Var}_j\hat p_{ji,x}+\operatorname{Var}_j\hat p_{ji,y}},.03,.15)$.
Only this component contributes F1 and F5 at each objective evaluation. Candidate headings/timestamps are not assumed native.
Suffix projection reuses the protected PP polyline rule; short suffixes append only the required prefix of the projected OLD remainder up to0.3m, then arclength-resample. Short/unavailable OLD handling is registered separately.

F2 queries $Q=\{p_0,...,p_{10},(p_i+p_{i+1})/2\}$.
$d(q)\ge m(q)$, where $m=\min(.025,\max(0,d(B)-.005))$ for current path arclength≤0.30m and $m=.025$ thereafter.
Soft loss $\sum_{q\in Q}[\max(0,.15-d(q))/.05]^2$.
These are node/midpoint constraints, **not a continuous-segment safety certificate**. Out-of-grid queries are infeasible; unknown cells inside the input grid retain the source V1 free-space treatment.

F3: $\ell_i=\|p_{i+1}-p_i\|$, $v_i=\ell_i/\tau_i$, $\omega_i=\operatorname{wrap}(\theta_{i+1}-\theta_i)/\tau_i$.
Hard $v_i\le.3$, $|\omega_i|\le.4$, $.05\le\tau_i\le1$.
Initial acceleration $a_0=(v_0-v_{actual})/\tau_0$; subsequent $a_i=2(v_i-v_{i-1})/(\tau_i+\tau_{i-1})$; $|a_i|\le.5$.
The actual initial speed is a boundary value, not an invented native waypoint time.
TEB-style nonholonomic residual $r_{nh,i}=((\cos\theta_i+\cos\theta_{i+1})\delta y_i-(\sin\theta_i+\sin\theta_{i+1})\delta x_i)/\sigma_{nh}$.
Forward consistency $r_{back,i}=\min(0,\delta p_i\cdot[\cos\theta_i,\sin\theta_i])/\sigma_{nh}$.
Their squared sums are fixed-weight terms; $\sigma_{nh}$ is preregistered and not tuned.

F4: $w_t\sum_i\tau_i$ (equivalently unary residual $\sqrt{w_t\tau_i}$).
F5: $w_g\|p_{10}-\hat p_{j^*,10}\|^2/.3^2$.
F6: $w_c\sum_i(\kappa_{i+1}-\kappa_i)^2$, with signed Menger curvature and analytic derivatives reused from Graph v4.
Only adjacent valid triples (chords and endpoint chord≥1cm) contribute; zero-translation rotation has no defined spatial curvature.
Total objective is F1+F2soft+F3soft+F4+F5+F6. Hard constraints are F2/F3.

Eight policy starts plus up to two straight polylines through depth-component left/right edges offset0.25m; a missing intersecting component produces no fabricated side seed.
Connected components use4-connectivity, within2m of B and intersecting a candidate footprint.
SLSQP uses analytic Jacobians, maxiter100, ftol1e−8. Any observed feasible iterate (violation≤1e−7) before the shared500ms deadline can be selected by minimum objective; solver success and feasibility are recorded separately.
The reported wall time includes initialization, IPC, worker SDF loading and result collection, including overruns.

References: [Olson & Agarwal author manuscript](https://april.eecs.umich.edu/pdfs/olson2013ijrr.pdf) and [official TEB nonholonomic formulation](https://github.com/rst-tu-dortmund/teb_local_planner/blob/noetic-devel/include/teb_local_planner/g2o_types/edge_kinematics.h), [TEB acceleration](https://github.com/rst-tu-dortmund/teb_local_planner/blob/noetic-devel/include/teb_local_planner/g2o_types/edge_acceleration.h).
The max-mixture here is the user-specified equal-weight policy-candidate adaptation, not a reproduction of SLAM results.

## Pre-evaluation amendment

The user selected solver-check variant(ii): the shared cutoff and tuning/decision timing thresholds change from0.25s to0.5s before evaluation. Diagnostic feasible output was29/30without a limit, versus19/30delivered within0.25s. Eight policy starts plus available side starts,4workers, factor definitions, the8weight grid, maxiter100 and ftol1e-8 stay fixed. Optimized implementation SHA256:069f1c651640e5e32593825b819dffdfb4e6662d839d560047fbfc7bc1fd053d. Diagnostic results are not evaluation results.

U fixes x0 to the predicted application pose0.5s ahead. The current-path computation prefix is included in collision, progress, duration and distance evaluation. Compute wall time is reported without rounding or clipping; it is separate from the scheduled0.5s application delay. Only feasible messages received before cutoff are eligible. Late paths are discarded, while worker exceptions still propagate. The2026-11-03user decision fixes all computation prefixes to the existing rollout code/controller and exact72Hz SE(2) integrator: no constant-speed or constant-twist surrogate. U applies exactly0.5s later even if a feasible result arrives earlier; no-feasible braking starts only at that application pose. C0/C1 retain FRESHEST selection at the saved B and apply R2/R3/A* output after measured computation, with a shared1s delivery cap and late paths rejected. Separate work-time and application-delay distributions are reported.

The recorded OLD input contains XY geometry and current speed, not invented native timestamps. Its prefix uses frozen PP/SP, resuming the installed path and any saved SP alignment mode rather than triggering a fresh alignment on OLD. An explicit pose/dt OLD, when supplied, reuses the existing PP/graph-speed rollout instead. Newly applied U paths always use graph speeds. The bounded prefix reuses the existing rollout function bytecode and changes only its horizon; a fractional final72Hz interval uses that same controller command with the existing exact integrator. If OLD ends before computation finishes, its existing bounded braking/hold is used; no synthetic forward extension is invented.

Before any tuning/evaluation, the user approved the runtime reduction: static evaluation uniform samples10→5per run, preserving all5final10s failure-window samples and deduplication. Evaluation is454static+34sudden=488instead of829; training242snapshots and8weight combinations remain byte-identical. This was a scheduling amendment (about2h08m versus2h42m), not selection based on method outcomes. Original manifests/context are preserved under registration_history. Protocol settings are FROZEN before running; weights_status remains PENDING until training selects and commits the weights, before any evaluation.

## Descriptive diagnostics

Response origin is the first published saved depth snapshot with occupied cells in the evaluation box footprint (15mm localization tolerance). A qualifying avoiding output has nonnegative exact box clearance and reaches beyond a lateral box support plus footprint radius and25mm while making positive world-x progress. Oracle geometry is used only for these measurements. Among sparse selected snapshots, the earliest qualifying output gives an upper bound on response time/distance; it is not a densely observed onset. Missing qualifying output is censored, not zero. Distance includes historical pre-snapshot odometry and computation-prefix motion. reaction.csv has one row per recorded run/method.

Stop fraction counts no-feasible-plan braking requests. Braking and stationary duration cover only the finite trace; waiting for missing future candidates is right-censored. Iteration-limit rate uses completed initializer diagnostics, with pending starts separately reported. Failed-plan obstacle/kinematic active constraints are nonexclusive counts from the last received iterates. Initializer adoption uses accepted outputs (0-7policy,8-9available sides). Intent error compares the active endpoint with the evaluation progress direction; that direction is never passed into U.

## Registered execution and warm starts

Translation uses protected PP lookahead0.25m and graph segment speeds linearly interpolated at the **projected arclength**, with knots at translating-segment midpoints. No elapsed-time lookup or SP is used for U. Rotation segments are those with graph v<0.01m/s: brake within0.5m/s², then use graph omega's signed magnitude (limited to0.4rad/s). Only the last9Hz angular step is shortened to avoid overshooting the target heading. Completed rotation segments advance the segment cursor; zero-speed rotation knots are excluded from translating-speed interpolation. No heading-threshold start alignment is introduced. Only absence of a feasible solution available at the500ms cutoff produces a bounded braking stop; late worker output does not invalidate an already received feasible solution. The22-O2 endpoint/projection/time stopping rules remain; U has no heuristic-alignment time exemption.

The selected planning configuration is the measured variant(ii):8candidate starts and up to2depth-edge starts,4workers,500ms total cutoff. The earlier extra warm initialization is not used. Feasible improving iterates are published during solving; the parent selects the cheapest received pre-cutoff iterate and does not join late workers before returning. Solver options and all factor formulas/weights are unchanged. A* output is never a U seed or fallback; an A*-derived historical OLD path is withheld from U supplementation and recorded.

This offline dataset contains selected saved candidate arrivals, not a new4Hz closed-loop stream. It evaluates those selected arrivals chronologically; it does not simulate overlapping500ms jobs at250ms arrival intervals. No missing candidates are generated and no future depth/NoMaD feedback is invented. Thus the evaluation cannot establish closed-loop4Hz behavior.

Short original FRESH means native suffix<0.3m. Available non-A* OLD geometry may supplement it as originally specified; if it is still short, all8mixture candidates remain and resampling stays inside the available polyline. The report separately gives native-short and still-short active fractions (denominator: plans with an active candidate), and graph endpoint forward displacement conditional on each category. Forward displacement is measured along B heading, not u_ref.

## Preparation status

Configuration FROZEN; weights PENDING. Training242snapshots×8weights; evaluation488(454static+34sudden). Original failure-window samples retained and training input identical. Scheduling estimate about2h08m was approved by the user. The runner will commit training selection evidence before evaluation. No experimental label or weight selection exists yet.32pre-freeze unit tests passed; final verification follows the configuration commit.
