# Phase24 — frozen preparation; NOT_EVALUATED


## Input/output pipeline

| Stage | Inputs | Output |
|---|---|---|
| Decision D | Current8NoMaD candidates, observed depth, current execution state; depth-component history and odometry for the frozen20Fdirection rule | NORMAL reference r and sigma_r, or DETOUR u_ref |
| Single graph G | Predicted application pose/speed at+0.5s, base depth V1 SDF, r/sigma_r or u_ref | Eleven SE(2)poses, ten dt values, FEASIBLE / KINEMATIC_TOLERATED / STOP |
| Executor | Pose/dt trajectory and current pose/speed | Protected PP(.25m) steering, arclength-interpolated graph speed; graph omega for rotation segments |
| Evaluation only | Oracle boxes/walls, next-Topomap-node direction, saved source outcomes | Collision, clearance, progress and passage measurements |

| Mode | Entry/meaning | Reference |
|---|---|---|
| NORMAL | Ordinary operation | FRESHEST among native depth-safe suffixes; if none safe, FRESHEST among all8; no ALL_UNSAFE stop or R2 repair |
| DETOUR | Frozen20Ftrigger B or no NORMAL graph output within0.5s | Component-frozen preappearance u_ref and1.2m progress target; no path prior |
| Return to NORMAL | Frozen20F: no new obstacle ahead, endpoint,6s, or current depth safety failure | Next NORMAL candidate reference |
| Last resort | Registered no-output/fallback handling | Existing RECOVER_ROTATE, counted separately |

| Prior mechanism | New location |
|---|---|
| FRESHEST/depth selection | Decision D; reference and at most2alternative safe seeds |
| New-obstacle NO_PROGRESS, u_ref, handover | Decision D, frozen20Fconditions |
| Safety correction, kinematics, travel time | Graph factors in both modes |
| Mixed/Cauchy/history priors and learned F7direction | Removed |
| ALL_UNSAFE trigger and R2 repair | Removed |
| SP and start alignment | Removed from Gexecution; replaced by optimized speed/rotation |
| Rotation recovery | Decision D's last resort |
| A* | Comparison C1only; never a Gseed or fallback |

## Full graph definition

Let p0=0,theta0=0 in the predicted application-B frame; variables are (p_i,theta_i),i=1..10 and dt_i,i=0..9. The snapshot SDF already subtracts robot radius0.09m. All Ginput geometry is observed depth, not oracle geometry.

NORMAL reference: protected B-suffix projection, prepend B and arclength-resample to11positions (B+10future points). Short suffixes use the original allowed OLD supplementation; A*-derived OLD is withheld. sigma_r=clip(median_i sqrt(Var_j(x_ji)+Var_j(y_ji)),0.03,0.15), using the same prepared current8candidate dispersion as23-O.

$$J_{ref,N}=\sum_{i=1}^{10}\|p_i-r_i\|^2/\sigma_r^2+\|p_{10}-r_{10}\|^2/0.3^2.$$

DETOUR has no path or endpoint prior:
$$J_{ref,D}=[\max(0,1.2-(p_{10}-p_0)\cdot u_{ref})/0.10]^2.$$

Obstacle queries Q contain11nodes and10segment midpoints. Hard d(q)>=m(q), where m=min(0.025,max(0,d(B)-0.005)) on the first0.30m of current trajectory arclength, otherwise0.025m. Soft
$$J_{obs}=\sum_{q\in Q}[\max(0,0.15-d(q))/0.05]^2.$$
This is the inherited node/midpoint test, not a continuous collision certificate.

For segment l_i=|p_{i+1}-p_i|, v_i=l_i/dt_i and omega_i=wrap(theta_{i+1}-theta_i)/dt_i. Hard v_i<=0.3, |omega_i|<=0.4, dt_i in[0.05,1]. Initial acceleration a0=(v0-v_actual)/dt0; later a_i=2(v_i-v_{i-1})/(dt_i+dt_{i-1}). Soft acceleration, including the initial-speed boundary:
$$J_a=\sum_i[\max(0,|a_i|-0.5)/0.05]^2.$$

Frozen TEB-style soft terms, sigma_nh=0.03m:
$$r_{nh,i}=((\cos\theta_i+\cos\theta_{i+1})\delta y_i-(\sin\theta_i+\sin\theta_{i+1})\delta x_i)/0.03,$$
$$r_{back,i}=\min(0,\delta p_i\cdot[\cos\theta_i,\sin\theta_i])/0.03.$$
$$J_{motion,time}=J_a+\sum_i(r_{nh,i}^2+r_{back,i}^2)+1.0\sum_i dt_i+0.01\sum_i(\kappa_{i+1}-\kappa_i)^2.$$
The last sum uses the frozen Menger valid-chord mask (>=1cm); rotation segments are not assigned fabricated curvature. Total J=J_ref,mode+J_obs+J_motion,time. There is no max-mixture, Cauchy, memory prior or F7.

NORMAL starts: r, nonempty current OLD remainder (unless A*-derived), then the next2safe candidates ranked by remaining length/index. DETOUR starts: the unchanged1.5m straight fans at0,+30,-30,+60,-60,+90,-90degrees around u_ref, with11points. SLSQP, analytic Jacobians, maxiter100, ftol1e-8,4workers, shared0.5s. The same frozen initializer creates pose headings/time guesses; no native yaw/timing is assumed.

Output policy is exactly23-O3: choose the least-cost received feasible iterate; otherwise the least-cost last available iterate with every F2slack>=0 and v<=0.33,|omega|<=0.44,dt in[0.045,1.1]; otherwise STOP. The optimizer itself keeps the strict bounds. The executor retains v<=0.3,|omega|<=0.4,acceleration<=0.5. Translation uses PPdirection and graph speed by arclength; rotation uses graph omega. No SP/start-alignment fallback is added to G.

## Why decisions are outside the graph

The preserved23-O3registered GO_ONLINE used8already-passed snapshots. The corrected pre-passage label is PRE_PASSAGE_NO_GO: U3planned0/16, C0planned2/16, C1planned3/16. In the frozen diagnostic,13/16intent directions differed from corridor+x by>=45degrees. All5converted comparator detours cost more than U3; F7was the largest increasing term inall5. Additional seeds retained feasible passage candidates but the objective selected none. These are diagnostic findings, not evidence of improved obstacle avoidance. Phase24therefore supplies intent through Dand keeps physical trajectory generation in one graph.

## Registered offline rules

{'priority': ['MODE_RECOMPUTED: original20Fobservable trigger predicate on saved odometry/depth', 'MODE_FROM_C0: R3attempt only when required histories missing', 'MODE_FALLBACK: failed NORMAL output promotes to one DETOUR solve'], 'predicate_transient_guards': 'fresh counterfactual trigger state: busyFalse,cooldowninactive,blockedFalse,suppress-1; no prior Gstate or source-method transient state imputed', 'reference': '20F component-frozen preappearance direction; if none, approved20FAradial/start-heading fallback', 'normal_failure': 'only if neitherFEASIBLE norKINEMATIC_TOLERATED; same depth/candidates; one extra solve', 'second_start': 'propagate first0.5s OLD prefix; execute firstSTOP bounded braking during second0.5s; extend odometry with only that deterministic prefix for direction at transition', 'time': 'sum measured per-stage solves; fixed application delay0.5s/stage, total1s on fallback; no new captures/inference', 'comparators': 'reuse frozen C0/C1 only for equivalent trigger/direction arguments; otherwise recompute frozen solvers with the newly reconstructed Btrigger/component direction; Abranch retains radial direction', 'gate': 'passage count on16PRE_PASSAGE; collision on216STATIC; STOP/p95 on their232union.2PRE_SPAWN+8ALREADY_PASSED excluded; all26sudden also shown.'}

242inputs;232gate cohort. Estimated43.2min with two Gsolves per input and all268baseline recomputations budgeted.9unit tests passed. No new Gsnapshot solve or navigation has run.
