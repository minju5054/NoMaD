# Graph v4 — full-path constrained offline pilot

This is a single fixed-B offline mechanism validation on the same59 saved v3 handoffs. Base `b48c552`; its two subsequent figure-only commits are preserved on `research/phase0-infrastructure`. No navigation, inference, runtime/controller/model changes, optimizer restart or result-based tuning. Code and protocol are committed before the one campaign.

## Frozen formulation

Eight editable SE(2) future poses per sample; raw XY is transformed at its observation pose. Actual B is fixed. Auxiliary headings use the existing >=20mm chord rule, without native yaw or timestamps. Each of8 NoMaD samples is a distinct initialization and its own FRESH prior. An invalid heading initialization is recorded, not repaired with invented yaw.

`graph_v4_protocol.json` freezes all settings. SLSQP uses explicit analytic objective and inequality/equality Jacobians, maxiter100 and ftol1e-8. No finite-difference solver derivative or PP evaluation appears in the objective, constraints or solution selection. Four minimum numerical checks validate analytic derivatives (complex-step, without finite-difference subtraction), known-circle curvature, conservative SDF segment bounds and previous-prior/selection semantics. They run no optimization.

Residuals use local SE(2) relative translation and periodic heading error `2 sin(delta/2)`, plus unit-tangent heading consistency. This is an explicit analytic representation variant, not identical v3 SE(2)-log residuals. Relative scales remain0.01m/10deg, boundary0.01m/10deg and tangent10deg. FRESH prior is deliberately weaker:0.10m/30deg, versus v3's0.02m/15deg. The original definite-side rule and0.02m scale remain; undefined or undisclosed sides have no factor.

Hard path constraints:

- All six consecutive XY triples have signed circumcircle curvature `2 cross(u,v)/(|u||v||u+v|)` within±8/m. This discrete curvature is not a guarantee on PP lookahead curvature.
- Per-sample RAW nearest-projection segment/fraction is fixed once. Its editable entry E must lie at least0.02m forward of B. The circle tangent to B heading and passing E has curvature `2 n_B dot(E-B)/|E-B|^2`, constrained equal to the previous **actual** w/v. No corrected previous command replaces that saved command. Zero previous v is invalid; all59 saved starts have positive v.
- Segment lengths >=max(5mm,80% native segment), total length>=90% native and frozen heading chords>=50% original. XY trust box±0.75m and auxiliary yaw±pi around each original sample. These are fixed numerical/search limits, not impossibility proofs.
- Corridor halfplanes leave5mm footprint clearance for every node; convexity covers all linear segments.
- A public-geometry SDF is precomputed on a1cm grid, padded2m beyond the corridor. Values are signed AABB-union distance minus0.09m robot radius. Bilinear values have analytic cell gradients. At all9 equally spaced positions on each of7 segments, impose `SDF_interpolated - h/sqrt(2) - segment_length/16 >=0.025m`. The grid error and segment Lipschitz bound certify the **entire** polyline, not just sampled nodes. Existing exact `path_safety` independently certifies accepted paths.

Only geometry available at B under v3's first-visible/next-actual-RGB rule enters the SDF, side term and selection. S1 F43 has static geometry only. Evaluation uses all geometry actually active at B. The constraints cover the native8point path; they do **not** certify B-to-entry connectors or the PP arc. PP is evaluated only afterward with unchanged swept-clearance functions.

## Multi-start and previous correction

Two independent conditions: sample0 single-start and eight-start multi-start. Each gets its own successive-S1 history. At most531 solves in one campaign (59+59x8); one solve per method/case/start, no restart or weight change. An identical sample0 in the other condition is not a retry: the methods may have different previous-prior histories and both timings are measured independently.

Only S1 F43–75 uses the immediately previous **accepted path-constraint-feasible** correction of the same method, weak XY sigma0.20m. Existing nearest projection at current B and normalized arclength interpolation of the remaining previous path provide a fixed prior stencil. It is not a physical waypoint correspondence or timestamp. First case or immediately previous rejection means no prior; older corrections are not substituted. A PP validation outcome cannot change history or selection. Saved B/OLD commands remain actual-run data; this is not closed-loop execution of the corrections.

Select the lowest cost among converged, constraint-feasible and exactly certified solutions:

`mean(||XY_corrected - XY_original_sample||^2)/0.10^2 + [max(0,0.25 - forward_B dot(endpoint-B))/0.25]^2`.

Tie-break by sample index. This scores edit and forward-endpoint deficit, never PP outcome or future navigation. Endpoint progress also supplies a residual in the objective. If no feasible solution exists, record `NO_SELECTION`, without an invented STOP/fallback.

**Sample selection only** filters the8 unchanged native paths by public-geometry2cm clearance and corridor containment, then uses the same score with zero edit. It uses the same variable-speed PP as v4, to isolate path editing; it is explicitly not a constant-speed sample-selection baseline. Original sample paths are not modified. Missing safe sample means no selected action.

## Common post-hoc evaluation

Methods: cached RAW, RAW+Speed, RAW+Rate limit, RIGID and Graph v3; new sample selection only, Graph v4 single and Graph v4 multi. Cached v3 solver/path/control records are reused without solving v3 again.

New selected paths and single-start rejected final iterates are evaluated with v3's dedicated speed wrapper: target=clip(0.4/abs(kappa_PP),0.05,0.2); nearest target within acceleration0.5m/s² from previous actual v; w=clip(v*kappa_PP,±0.4). Flags are retained and do not determine safety. No v=0 recovery. Original PurePursuit remains unchanged.

H_switch ends at the next actual switch, or the same explicitly right-censored terminal used in v3. H_chunk follows the frozen path to existing endpoint tolerance or60s, without future FRESH or1s expiry. Mathematical continuations after collision remain diagnostics. Endpoint arrival is not goal arrival.

The v3 **5mm relative loss rule is removed**. Report native-and-rollout >=2cm, corridor containment and completed horizon. Accepted graph actions must converge and satisfy hard path constraints. Separately report H_switch movement>=70% RAW with no stop and joint safe+progress counts. |delta-w| and saturation are descriptive, not substitutes for safety. Missing multi/sample actions stay in the denominator and cannot count as safe STOP. Rejected single-start/v3 iterates are kept as diagnostic evaluations; all-evaluated and accepted-only metrics are separated.

Stress has6 cases, of which3 start below2cm: fixed-goal52=19.190mm, Topomap sudden53=2.655mm and Early RAW64=5.369mm. Preserve and attempt all6; also report the initially-safe denominator3. Prior margin violations cannot be undone.

Report solver wall time per start, total initialization+certificate time, full serial8start selection time and separately SDF construction. Cold-inclusive times add the measured field build cost to each hypothetical standalone method invocation; shared-cache actual builds are also recorded.20ms is an online target, not a solver termination rule. Report both20ms and100ms exceedance rates, convergence and feasibility rejection counts.

## Preflight and frozen command

All59x8 saved samples exist; sample0 observation-world transform and first RAW PP command match exactly. All2,378 protected input/source hashes match. Four minimum tests passed with zero optimization. Existing v3 inputs, raw runs and plots remain unchanged.

```bash
env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_phase0.graph_v4_pilot execute --output /home/gpuadmin/Workspace/NoMaD/artifacts/graph_v4/offline_pilot_01
```

The runner requires a clean commit, frozen protocol/input hashes and a new cases directory. Actual results will be appended after the single execution. No new figure is part of this task.
