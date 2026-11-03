# Phase23-O3 — registered before training


## U3 definition

U3 preserves frozen U2 factors, Cauchy c=1, acceleration sigma0.05, and time/goal/curvature weights1/1/0.01. Only F7 and the specified output policy are added. Eight current policy starts plus available depth-side starts,4workers, SLSQP maxiter100/ftol1e-8,500ms anytime and the frozen computation-window rollout remain unchanged. No A*, u_ref, odometry history, trigger, Topomap or new-obstacle classifier enters U3.

For each current/memory component j, use its B-frame endpoint displacement e_j. Exclude only from the F7 direction average those with |e_j|<0.05m. Direction is the unit vector of sum_j exp(-tau_j/T_m) e_j/|e_j|. No valid endpoint, or an exactly canceled mean (numerical norm<=1e-12), leaves direction mathematically undefined and F7 inactive. No substitute heading is introduced. The original mixture still retains all candidates.

$$F_7=w_7[\max(0,1.2-(p_{10}-p_0)\cdot\hat d)/0.10]^2.$$

Direction is fixed from observed inputs during each solve, so its active derivative is $-2w_7r\hat d^T(J_{p10}-J_{p0})/0.10$. Grid:w7 in{0.5,1,2} × T_m in{0.5,1,2}s; c=1fixed. No other tuning.

Output first selects the lowest-cost strict feasible iterate received within500ms, as before. Only if none exists, it considers the last available iterate from each start: every F2 node/midpoint inequality must have nonnegative slack; v<=0.33, |omega|<=0.44 and dt in[0.045,1.10]. It picks the lowest-cost qualified last iterate. A later unsafe iterate invalidates that start's earlier tolerated iterate. These are output tolerances only: the optimizer's original hard bounds and constraints are unchanged. All late messages are discarded. FEASIBLE / KINEMATIC_TOLERATED / STOP are recorded. The frozen executor still clips v<=0.3, |omega|<=0.4 and acceleration<=0.5. STOP brakes only after the fixed0.5s computation prefix.

Selection uses only the unchanged242training snapshots(216static,26sudden): timing p95<=0.5s, then minimum rollout collisions, maximum collision-free planned box-passage fraction on26sudden inputs, minimum STOP fraction, maximum static progress median, minimum p50 (fixed grid index only breaks exact ties). As in the prior protocol, if no timing-eligible setting exists, minimum p95 is retained for diagnosis and timing necessarily fails the gate. No evaluation-set snapshot is solved.

U2 uses its frozen selected training outputs. C0 is computed on the same242inputs, and C1 on the same26sudden inputs. They retain frozen23-O timing and rollout. The path-passage metric is unchanged from23-O2: an output path reaches beyond the box rear with its footprint and has no oracle box/wall overlap. Rollout passage is also shown separately. All output failures remain in denominators.

Gate GO_ONLINE requires: U3 sudden planned-passage fraction>=0.8*C0, total U3 rollout collisions<=C0 across242inputs, total STOP fraction<=10%, and total compute p95<=0.5s. Otherwise NO_GO. These are training-set diagnostics used for selection, not held-out performance or closed-loop evidence.

## Status

NOT_EVALUATED.242training cases,9fixed combinations; no held-out evaluation rerun. Representatives fixed before results: ['TD0216', 'TD0217', 'TS0037'].
