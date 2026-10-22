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

## Completed one-time execution

Frozen execution commit: `b2470a7`. All59 cases finished in the one campaign: **531/531 solves attempted**, **403 converged and constraint-feasible**, **128 nonconverged**. There were no initialization rejections, new navigation, inference, restarts or parameter changes. SLSQP logged its normal clipping of intermediate trial points to the fixed trust bounds; no protocol adjustment followed.

- Single-start:43/59 accepted paths;16 nonconverged solves (S0:3, S1:7, stress:6).
- Multi-start:360/472 feasible starts;112 nonconverged starts. A feasible candidate was selected in53/59 cases (all20 S0 and33 S1; none of6 stress).
- Solver statuses across531 starts:403 successful,109 positive-directional-derivative line-search exits,14 iteration limits,5 incompatible-inequality exits. A failed numerical search is **not** proof that no feasible path exists.
- The previous-correction prior was verified on281 start stencils:25 single-start S1 cases and32x8 multi-start S1 candidates. No PP outcome was used to select candidates or update this prior.

### Safety and progress

Counts below are **H_switch / H_chunk**, requiring native full path and evaluated PP rollout >=2cm, corridor containment, horizon completion and an accepted method output. Missing actions and rejected final iterates do not count as safe. Stress uses the3 initially-safe B cases; the other3 remain in the raw CSV and the `all` summary partition, separately labelled initially unsafe. Safe counts are unchanged when adding them, but denominators and collision counts are not.

| Method | S0 (20) | S1 P0 (33) | Stress initially safe B (3) |
| --- | --- | --- | --- |
| RAW | 19 / 11 | 32 / 25 | 0 / 0 |
| RAW+Speed | 19 / 15 | 32 / 28 | 1 / 0 |
| RAW+Rate limit | 19 / 10 | 32 / 24 | 0 / 0 |
| RIGID | 19 / 13 | 33 / 22 | 0 / 0 |
| Sample selection only | 20 / 18 | 33 / 32 | 1 / 0 |
| Graph v3 | 16 / 14 | 33 / 32 | 0 / 0 |
| Graph v4 single | 17 / 16 | 26 / 24 | 0 / 0 |
| Graph v4 multi | 20 / 19 | 33 / 30 | 0 / 0 |

Adding the required **>=70% RAW H_switch travel and no stop** gives:

| Method | S0 (20) | S1 P0 (33) | Stress initially safe B (3) |
| --- | --- | --- | --- |
| RAW | 19 / 11 | 32 / 25 | 0 / 0 |
| RAW+Speed | 15 / 13 | 26 / 26 | 0 / 0 |
| RAW+Rate limit | 19 / 10 | 32 / 24 | 0 / 0 |
| RIGID | 19 / 13 | 33 / 22 | 0 / 0 |
| Sample selection only | 19 / 17 | 28 / 28 | 0 / 0 |
| Graph v3 | 15 / 13 | 29 / 28 | 0 / 0 |
| Graph v4 single | 15 / 15 | 25 / 23 | 0 / 0 |
| Graph v4 multi | 17 / 16 | 29 / 28 | 0 / 0 |

Sample selection uses unchanged geometry and the same variable-speed executor as v4. In S1 its32/33 H_chunk result matches cached v3 and exceeds v4 multi's30/33. S0 multi improves the safe-complete count to19/20 versus selection-only18/20 and v3 14/20, but the safe-plus-progress count is16/20 versus selection-only17/20. This pilot does not establish blanket superiority of trajectory correction.

### Overlap and RAW-unsafe transitions

The next table counts overlaps among **accepted outputs only**, H_switch / H_chunk. `0 (no action)` is not collision avoidance. Full diagnostic-iterate overlap counts remain separate in JSON/CSV. V4 multi has no selected path in any stress case.

| Method | S0 (20) | S1 P0 (33) | Stress initially safe B (3) |
| --- | --- | --- | --- |
| RAW | 0 / 5 | 0 / 7 | 1 / 3 |
| RAW+Speed | 0 / 1 | 0 / 5 | 0 / 2 |
| RAW+Rate limit | 0 / 5 | 0 / 9 | 1 / 3 |
| RIGID | 0 / 5 | 0 / 8 | 1 / 3 |
| Sample selection only | 0 / 0 | 0 / 1 | 0 / 1 |
| Graph v3 | 0 / 0 | 0 / 0 | 0 / 1 |
| Graph v4 single | 0 / 0 | 0 / 0 | N/A: no accepted action |
| Graph v4 multi | 0 / 0 | 0 / 2 | N/A: no accepted action |

RAW native-or-rollout unsafe → accepted safe-complete transitions (not necessarily the70% progress criterion):

| Method | S0 (20) | S1 P0 (33) | Stress initially safe B (3) |
| --- | --- | --- | --- |
| RAW | 0 / 0 | 0 / 0 | 0 / 0 |
| RAW+Speed | 0 / 3 | 0 / 3 | 1 / 0 |
| RAW+Rate limit | 0 / 1 | 0 / 0 | 0 / 0 |
| RIGID | 0 / 2 | 1 / 0 | 0 / 0 |
| Sample selection only | 1 / 5 | 1 / 7 | 1 / 0 |
| Graph v3 | 1 / 3 | 1 / 7 | 0 / 0 |
| Graph v4 single | 1 / 5 | 0 / 1 | 0 / 0 |
| Graph v4 multi | 1 / 6 | 1 / 6 | 0 / 0 |

The initially-safe stress set contains fixed-goal51, Topomap sudden52 and Early RAW63. V4 finds no accepted solution for any; no recovery advantage is demonstrated. The excluded initial violations are fixed-goal52=19.190mm, Topomap53=2.655mm and Early RAW64=5.369mm. They were still solved/evaluated and are not silently discarded. In all6 stress cases, selection-only has2 selected outputs; its one safe H_switch continuation does not complete H_chunk safely and does not retain70% RAW short-horizon travel.

### Angular discontinuity and actual PP saturation

Mean switch |delta-w| in rad/s below uses **accepted outputs**, with its sample count in parentheses. Different acceptance sets make these conditional means descriptive, not a paired performance proof. All-final-iterate means are also retained in `method_summary.csv`; rejected v4 single/v3 iterates are never treated as selected actions.

| Method | S0 (20) | S1 P0 (33) | Stress initially safe B (3) |
| --- | --- | --- | --- |
| RAW | 0.4252 (n=20) | 0.1467 (n=33) | 0.0000 (n=3) |
| RAW+Speed | 0.4252 (n=20) | 0.1467 (n=33) | 0.0000 (n=3) |
| RAW+Rate limit | 0.0993 (n=20) | 0.0630 (n=33) | 0.0000 (n=3) |
| RIGID | 0.4017 (n=20) | 0.1427 (n=33) | 0.0000 (n=3) |
| Sample selection only | 0.3563 (n=20) | 0.1076 (n=33) | 0.0000 (n=2) |
| Graph v3 | 0.1947 (n=16) | 0.0667 (n=33) | 0.0000 (n=1) |
| Graph v4 single | 0.3653 (n=17) | 0.1319 (n=26) | N/A (n=0) |
| Graph v4 multi | 0.3625 (n=20) | 0.1184 (n=33) | N/A (n=0) |

Actual PP `CURVATURE_SATURATED` (|kappa_PP|>8) ratios among accepted control records, **H_switch / H_chunk**. This is not the graph's node-curvature constraint. Ratios are9Hz exposure-weighted; long looping failures contribute many records. All-evaluated and accepted counts/denominators for every flag are in `flag_counts.csv`.

| Method | S0 (20) | S1 P0 (33) | Stress initially safe B (3) |
| --- | --- | --- | --- |
| RAW | 13.04% / 7.34% | 17.57% / 7.66% | 66.67% / 9.57% |
| RAW+Speed | 10.87% / 47.71% | 17.57% / 86.45% | 66.67% / 96.17% |
| RAW+Rate limit | 13.04% / 8.17% | 17.57% / 7.41% | 66.67% / 9.57% |
| RIGID | 10.87% / 9.19% | 13.51% / 6.08% | 66.67% / 10.19% |
| Sample selection only | 0.00% / 0.00% | 4.05% / 52.56% | 100.00% / 100.00% |
| Graph v3 | 0.00% / 39.93% | 0.00% / 0.00% | 0.00% / 0.00% |
| Graph v4 single | 7.50% / 64.75% | 0.00% / 0.00% | N/A / N/A |
| Graph v4 multi | 0.00% / 0.00% | 5.41% / 51.23% | N/A / N/A |

### Why full-path feasibility did not ensure PP safety

All403 feasible graph starts were independently rechecked: minimum **public-geometry native** clearance33.577mm, maximum discrete node curvature8.000000402/m (within frozen numerical constraint tolerance), maximum boundary-curvature equality error1.10e-11/m. Conservative SDF discretization explains the clearance being above the25mm target. This verifies the path constraints, **not** the PP follower's swept route.

The four v4-multi H_chunk failures were:

| Case / selected sample | Native clearance | PP outcome |
| --- | --- | --- |
| S0_03_F0008 /4 |534.677mm | Corridor intrusion;60s chunk timeout; no obstacle overlap |
| S1_P0_F0043 /1 |164.420mm | Corridor intrusion;60s timeout; no obstacle overlap; dynamic geometry not yet public at B |
| S1_P0_F0063 /6 |54.458mm | Obstacle overlap;60s timeout; actual PP curvature saturation throughout540 control ticks |
| S1_P0_F0064 /0 |34.526mm | Obstacle overlap;60s timeout; actual PP curvature saturation throughout540 control ticks |

For F63/F64, discrete path curvature is at most8.00000001/8.00000033 per metre and boundary-circle curvature is2/m, as requested. Nevertheless first PP lookahead curvature is **8.369/8.321 per metre**. The path-entry circle and three-point path curvature are different quantities from PP's current-pose-to-lookahead geometry. Later saturated constant-curvature continuations overlap obstacles. H_switch remains safe, but full-chunk execution does not. The other two failures show that absence of curvature saturation also does not ensure endpoint convergence or corridor containment.

This is direct negative evidence against treating the chosen path-level constraints as a sufficient substitute for PP execution constraints. It does not prove that all path-level formulations must fail. No new constraints or tuning were introduced after observing these results.

### Timing and convergence

Wall times include failures. Shared SDF preparation is measured separately (5 public-geometry fields,14.20–16.99ms each). Cold-inclusive values add that field's actual build time to each hypothetical standalone method invocation. Serial multi-start time includes **all8 starts**, initialization, exact certificates and selection; it is not disguised as one-start latency.

| Timing | N | median ms | p95 ms | max ms | >20ms | >100ms |
| --- | --- | --- | --- | --- | --- | --- |
| Graph v3_cached_solver_s | 59 | 2657.89 | 38617.64 | 52146.20 | 100.0% | 100.0% |
| single_per_start_solver_s | 59 | 54.47 | 208.72 | 507.91 | 100.0% | 20.3% |
| Graph v4 single_method_s | 59 | 55.79 | 209.97 | 509.18 | 100.0% | 20.3% |
| Graph v4 single_cold_inclusive_s | 59 | 72.78 | 226.39 | 524.70 | 100.0% | 27.1% |
| multi_per_start_solver_s | 472 | 56.74 | 168.30 | 506.58 | 100.0% | 22.2% |
| Graph v4 multi_method_s | 59 | 598.76 | 1088.78 | 2379.21 | 100.0% | 100.0% |
| Graph v4 multi_cold_inclusive_s | 59 | 615.75 | 1104.38 | 2394.73 | 100.0% | 100.0% |
| Sample selection only_method_s | 59 | 3.58 | 3.83 | 3.89 | 0.0% | 0.0% |

Every v4 solve exceeded20ms. Single total median55.79ms is substantially below cached v3's2657.89ms, but misses the20ms goal. Multi total median598.76ms remains above100ms in59/59 cases. The sample-selection baseline took median3.58ms. Different formulations/workloads and cached measurement dates prevent attribution of the speedup solely to analytic Jacobians.

Single start nonconvergence is16/59; multi individual-start nonconvergence112/472, leaving6/59 cases without a selected feasible result. These should not be compared to v3's7/59 failures as though v4 multi ran only59 optimizations. No solver deadline, restart or parameter change was used to improve timings.

### Verification and preserved outputs

Post-execution read-only verification checked all531 final constraint vectors,403 exact feasible path certificates, deterministic candidate selection,281 previous-prior stencils and12,265 new PP control records. Maximum pose discrepancy after held-command integration is1.04e-12; speed/acceleration/clipping flags match the frozen v3 speed rule. All cached baseline method records are identical to v3 and all2,378 input/source hashes remain unchanged. Four preflight numerical tests passed; no post-result optimization was run.

Results are in `research/results/graph_v4_offline_pilot_20261022/`: summary,944-row comparison,531-start CSV (including failed paths), selected-path JSON, method/flag/timing tables, protocol execution/input provenance and verification. Full factor diagnostics, every candidate's auxiliary poses and new control traces remain in `/home/gpuadmin/Workspace/NoMaD/artifacts/graph_v4/offline_pilot_01/cases/` (~88MB, excluded from Git). Original results were not overwritten. The copied original v3 method records retain legacy v3 qualification metadata for provenance; v4 tables recompute the new criteria and never use the5mm loss rule.

The next unresolved mechanism is consistency between path-level curvature/entry constraints and the **actual PP lookahead/endpoint dynamics**, along with no-action handling and compute-delay moving-B validity. Sample selection alone is a strong baseline in this dataset. No online navigation, feasibility theorem, Graph necessity or real-time applicability is established by this offline pilot.
