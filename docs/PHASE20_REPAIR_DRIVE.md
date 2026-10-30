# Phase 20 — SO-only repair recovery pilot

**파일럿 / Offline gate: NOT_READY**. Execution SHA: `5f0ada453bec0d935c8c8d90152811bea6a8a251`. Protocol hash: `50a31546ae91fd716970037752df42dd7478429330ba0bb546e6c1eef90cf9d3`.

The revised main matrix is SO only, seed indices74–79, M1 ROTATE and M2 REPAIR, 12 serial trials. No SLW/LC/CL navigation or noninferiority judgment is planned in this phase. None of these pilot trials has been executed by this offline preflight.

## 0-a. R2 definition

R2 inherits Phase19R initialization, 14 XY variables, fixed B, priors/smoothness/heading objective, curvature≤8, length preservation, trust region, analytic Jacobian, SLSQP(maxiter100, ftol1e−8) and single-attempt solve. Only the first0.30m clearance threshold is relaxed. Oracle geometry never enters optimization, selection or SP/alignment control.

Let c_B = saved depth SDF(B) − h/√2 (the same conservative footprint clearance convention as Phase16D/19R). At each current optimized path sample q, cumulative arclength s(q)≤0.30m uses min(0.025,c_B−0.005); later samples use0.025m. The original per-segment nine-point bound d(q)−h/√2−L/16 is unchanged. Zone membership is recomputed from the optimized path, not the initial path. The piecewise-constant threshold has an analytic zero derivative away from s=0.30m; the zone boundary is explicitly nonsmooth. No smoothing, tuning or restart is introduced.

Exact depth certificate splits the continuous path at0.30m and reuses exact distance to occupied cell centers minus robot radius on both subpaths. The cut is included in both certificates: a continuous far-side path must satisfy0.025m in the limit at the cut. Acceptance still requires solver success, maximum constraint violation≤1e−7 and both exact certificates.

Selected repair is the accepted sample with minimum mean edit (lower-index tie); all8 are attempted once unless Phase19R short/degenerate exclusion applies. Timing p95 uses eligible per-sample attempts including certificate. Eight-sample serial time and counts exceeding the planned0.5s online deadline are separately reported.

| cause | events | successes | fraction |
| --- | --- | --- | --- |
| MARGINAL | 86 | 55 | 0.63953 |
| TRUE_BLOCK | 107 | 77 | 0.71963 |
| NEAR_START | 27 | 14 | 0.51852 |
| OTHER | 21 | 16 | 0.7619 |

```json
{
  "label": "NOT_READY",
  "reasons": [
    "SELECTED_PATH_ORACLE_PENETRATION",
    "ROLLOUT_OVERLAP_EXCEEDS_7_PERCENT"
  ],
  "events": 241,
  "repair_successes": 162,
  "repair_success_fraction": 0.6721991701244814,
  "selected_path_oracle_penetrations": 2,
  "selected_rollout_overlaps": 12,
  "selected_rollout_count": 162,
  "selected_rollout_overlap_fraction": 0.07407407407407407,
  "accepted_sample_paths": 728,
  "all_accepted_path_oracle_penetrations": 14,
  "cause_success": {
    "MARGINAL": {
      "events": 86,
      "successes": 55,
      "fraction": 0.6395348837209303
    },
    "TRUE_BLOCK": {
      "events": 107,
      "successes": 77,
      "fraction": 0.719626168224299
    },
    "NEAR_START": {
      "events": 27,
      "successes": 14,
      "fraction": 0.5185185185185185
    },
    "OTHER": {
      "events": 21,
      "successes": 16,
      "fraction": 0.7619047619047619
    }
  },
  "per_sample_solve_s": {
    "n": 1005,
    "median": 0.016293168999254704,
    "p95": 0.040575193607946855,
    "max": 0.11149463697802275
  },
  "eight_sample_wall_s": {
    "n": 241,
    "median": 0.0777223749901168,
    "p95": 0.2155656669929158,
    "max": 0.3350750939862337
  },
  "eight_sample_over_half_second": 0,
  "selected_mean_edit_m": {
    "n": 162,
    "median": 0.02508100353499551,
    "p95": 0.07369202861622366,
    "max": 0.11072891644468626
  },
  "post_hoc": true
}
```

READY requires zero **selected** repaired-path oracle penetrations, ≤7% oracle overlap among selected 1.5s SP+departure-alignment rollouts, and per-sample solve p95≤0.20s. All accepted sample-path penetrations are reported separately, including unselected paths. There is no minimum repair-success gate. No-selected-repair is not evidence of readiness.

SP and trigger S match Phase19S, with trigger P removed. Actual recorded initial v and heading are used; alignment is not forced when v≥0.01m/s. The1.5s clock includes braking/rotation. The rollout is endpoint/horizon bounded and oracle-passive, so overlap is monitored but never changes control.

### Selected penetrating repairs

| event_id | run | cause | B_oracle_clearance_m | B_depth_clearance_m | selected_near_threshold_m | selected_depth_clearance_m | selected_oracle_clearance_m |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 11 | LC_066_D750_FRESHEST-SAFE+TEMPORAL-ENSEMBLE | TRUE_BLOCK | 0.0020891 | -0.004982 | -0.009982 | -0.0013839 | -0.0013909 |
| 12 | LC_066_D750_FRESHEST-SAFE+TEMPORAL-ENSEMBLE | TRUE_BLOCK | 0.0020891 | -0.004982 | -0.009982 | -0.0011069 | -0.0011664 |

The specified near-start threshold can be negative. In these recorded cases the accepted path has a negative depth clearance as well as negative oracle clearance: the relaxed rule itself permits slight depth-footprint penetration. A passing near-start certificate is therefore not a nonpenetration certificate. This is recorded without changing the threshold or adding a new acceptance rule.

## 0-b. Six published Phase19S 1.5s collisions

| event_id | run | scene | fresh_id | previous_v | initial_heading_error_deg | departure_alignment | rotation_s | path_oracle_clearance_m | path_unknown_fraction | cross_track_until_collision_m | collision_type | collision_boxes | collision_pose | collision_time_s | actual_v_at_collision | actual_w_at_collision | reason | source_prefix_reproduced |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 28 | SLW_067_D750_FRESHEST-SAFE | SLW | 8 | 0.098227 | 10.552 | False | 0 | 0.044777 | 0 | 0.08703 | WALL | [] | [1.7083177229791071, -0.8115381395807999, -0.6028874191079332] | 1.4444 | 0.3 | -0.28755 | Start alignment inactive: actual v >=0.01m/s. Safe path clearance did not certify the executed PP arc. | True |
| 53 | SLW_068_D750_FRESHEST-SAFE+HERMITE | SLW | 56 | 0.05 | 42.811 | False | 0 | 0.034864 | 0 | 0.04545 | BOX | ['Slalom3'] | [3.8128569651142827, -0.11245106940688192, -0.3772245083502721] | 0.41667 | 0.25151 | -0.4 | Start alignment inactive: actual v >=0.01m/s. Safe path clearance did not certify the executed PP arc. | True |
| 56 | SLW_068_D750_FRESHEST-SAFE+HERMITE | SLW | 60 | 0 | 15.766 | False | 0 | 0.0067776 | 0 | 0.036448 | BOX | ['Slalom3'] | [3.833701248832614, -0.16065314502392164, -0.5534283906319235] | 0.69444 | 0.14381 | 0.4 | Start alignment inactive: initial heading error <20deg (or no point >=5cm). Safe path clearance did not certify the executed PP arc. | True |
| 167 | SLW_071_D750_FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SLW | 42 | 0.055736 | 101 | False | 0 | 0.036621 | 0 | 0.069896 | WALL | [] | [2.738946266044807, 0.8106715528763534, 1.4504382991621299] | 1.4444 | 0.05 | 0.33797 | Start alignment inactive: actual v >=0.01m/s. Safe path clearance did not certify the executed PP arc. | True |
| 183 | SLW_072_D750_FRESHEST-SAFE+GRAPH-depth-CLR | SLW | 28 | 0.05059 | 118.14 | False | 0 | 0.034495 | 0 | 0.066947 | WALL | [] | [2.819545598333406, 0.8101957578541565, 1.1512306538593569] | 1.3472 | 0.05 | 0.28541 | Start alignment inactive: actual v >=0.01m/s. Safe path clearance did not certify the executed PP arc. | True |
| 217 | SLW_072_D750_FRESHEST-SAFE+TEMPORAL-ENSEMBLE | SLW | 10 | 0.05 | 21.02 | False | 0 | 0.045442 | 0 | 0.050346 | WALL | [] | [1.6878537945525163, -0.8101085849903952, -0.3523460594478234] | 0.91667 | 0.29301 | 0.4 | Start alignment inactive: actual v >=0.01m/s. Safe path clearance did not certify the executed PP arc. | True |

These six cases were selected from the previously published D3 SRG prefix-overlap flags before any R2 outcome. Their saved clearances are reproduced with S-only control. Unknown fractions are descriptions of the fixed repaired path, not evidence that unknown space caused the collision. The one-line reasons distinguish trigger inactivity from a subsequent tracking failure; no experiment setting is changed from this diagnosis.

Departure alignment fired in 0/6 cases: 5 were already moving at ≥0.01m/s, and 1 did not meet the heading trigger. Nonpenetrating paths are distinguished from paths satisfying the full2.5cm margin. These are observed execution discrepancies, not proof of a unique causal mechanism.

## Validation and execution status

Five unit tests passed: R2 constraint/objective analytic Jacobians versus finite differences (≤1e−5 away from the hard zone boundary), exact split certificate, SP replacement/straight-speed/pre-turn braking, trigger S conditions without pivot, and equality to protected S-only behavior. Original code/raw/results remain unchanged. The frozen candidate protocol and deterministic12-job order are recorded below.

**Stopped at the mandatory offline gate.** Online repair-thread integration, SO smoke/technical gate, main batch and main result judgments were not executed. No campaign launch command is provided. Constants and thresholds were not changed to pass the gate. The main execution/report infrastructure is not claimed complete.

## Limits

Section0 is post-hoc analysis of Phase18 saved events. A fixed path rollout has no next FRESH, changing depth map or NoMaD response. Zero path penetration and short-horizon safety do not establish closed-loop driving safety. Simulation pose is assumed exact; oracle is restricted to evaluation.

## Frozen SO pilot and offline protocol

```json
{
  "phase": 20,
  "base_commit": "78ee7e1",
  "status": "OFFLINE_GATE_FROZEN",
  "label_scope": "파일럿",
  "scenes": [
    "SO"
  ],
  "methods": [
    "M1_ROTATE",
    "M2_REPAIR"
  ],
  "indices": [
    74,
    75,
    76,
    77,
    78,
    79
  ],
  "main_order": [
    {
      "scene": "SO",
      "index": 74,
      "method": "M2_REPAIR",
      "seed_offset": 740000
    },
    {
      "scene": "SO",
      "index": 74,
      "method": "M1_ROTATE",
      "seed_offset": 740000
    },
    {
      "scene": "SO",
      "index": 75,
      "method": "M1_ROTATE",
      "seed_offset": 750000
    },
    {
      "scene": "SO",
      "index": 75,
      "method": "M2_REPAIR",
      "seed_offset": 750000
    },
    {
      "scene": "SO",
      "index": 76,
      "method": "M2_REPAIR",
      "seed_offset": 760000
    },
    {
      "scene": "SO",
      "index": 76,
      "method": "M1_ROTATE",
      "seed_offset": 760000
    },
    {
      "scene": "SO",
      "index": 77,
      "method": "M1_ROTATE",
      "seed_offset": 770000
    },
    {
      "scene": "SO",
      "index": 77,
      "method": "M2_REPAIR",
      "seed_offset": 770000
    },
    {
      "scene": "SO",
      "index": 78,
      "method": "M1_ROTATE",
      "seed_offset": 780000
    },
    {
      "scene": "SO",
      "index": 78,
      "method": "M2_REPAIR",
      "seed_offset": 780000
    },
    {
      "scene": "SO",
      "index": 79,
      "method": "M1_ROTATE",
      "seed_offset": 790000
    },
    {
      "scene": "SO",
      "index": 79,
      "method": "M2_REPAIR",
      "seed_offset": 790000
    }
  ],
  "navigation_count": 12,
  "shuffle_seed": 20261031,
  "offline": {
    "source_events": "research/results/phase19r/events_eval.csv",
    "events": 241,
    "order": "unchanged CSV order; samples 0 through 7",
    "sample_attempts": 1,
    "retries": 0,
    "R2": "R inherited unchanged except piecewise start safety threshold and certificate",
    "c_B": "depth SDF(B) minus h/sqrt(2), same conservative footprint convention as Phase16D/19R",
    "near_region_m": 0.3,
    "near_threshold": "min(.025,c_B-.005)",
    "far_threshold_m": 0.025,
    "zone_membership": "current optimized cumulative arclength at each of63 inspection points, not frozen initial mask",
    "jacobian": "analytic within each zone; hard nonsmooth threshold at .30m, no smoothing/tuning",
    "certificate": "continuous split at .30m; exact occupied-site distance minus radius; split point checked by both near and far certificates",
    "selection": "minimum mean edit over8 resampled points among accepted; lower index tie",
    "rollout": "SP + trigger S only, actual event speed and heading; 108 integration ticks; oracle-passive evaluation",
    "readiness": {
      "selected_oracle_penetrations_equal": 0,
      "selected_rollout_overlap_fraction_max": 0.07,
      "eligible_sample_solve_p95_s_max": 0.2
    },
    "missing_repair_evidence": "NOT_READY, no fabricated zero-risk rate",
    "diagnosis_0b": "six saved Phase19S D3 SRG legacy_1p5s_prefix overlaps; no result-driven changes"
  },
  "control": {
    "lookahead_m": 0.25,
    "vmax_m_s": 0.3,
    "omega_max_rad_s": 0.4,
    "acceleration_m_s2": 0.5,
    "observation_hz": 4,
    "controller_hz": 9,
    "integration_hz": 72,
    "waypoint_timeout_s": 1,
    "navigation_timeout_s": 90,
    "delivery_delay_ms": 750,
    "speed": "protected Phase18D SP; rebuild on path replacement",
    "start_alignment": "Phase19S S: v<.01; first stored path point >=.05m from B; heading error>=20deg; brake then in-place |w|<=.4",
    "pivot_trigger_P": false,
    "fallback": "Phase16 KEEP_ACTIVE / STOP_WAIT",
    "recovery": "Phase17 RECOVER_ROTATE (30deg, .3rad/s, maximum12 per run)"
  },
  "M1": "No ordinary Graph; shared depth FRESHEST-SAFE selection, SP+S, KEEP/STOP/ROTATE",
  "M2": "ALL_UNSAFE -> serial eight-sample R2 in one CPU worker while STOP_WAIT; min-edit accepted repair, S alignment then follow; timeout .5s -> shared M1 fallback; no ordinary Graph",
  "depth": {
    "variant": "15A2 V1",
    "noise_sigma": "0.01*d^2",
    "unknown": "not occupied",
    "odometry": "exact simulator pose",
    "oracle_controller_input": false
  },
  "SO": {
    "source_scenario": "research/nomad_phase2/scenario.json",
    "source_scenario_sha256": "b5d7a5df40e3efdf3371a4d4d5a9621aa21b98c9bf297d9b0ba69b2d05475fae",
    "topomap": "/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/s1_v2_baseline_01/render/topomap/manifest.json",
    "topomap_sha256": "0d80ec037e2fa14264d9276f010efea2764c6bf269ac81f1bfb21f294d14cb0a",
    "nodes": 21,
    "placement": {
      "trigger_x": [
        2.0,
        2.1
      ],
      "distance_m": 1.2,
      "size": [
        0.35,
        0.35,
        0.8
      ],
      "y_offset_m": 0.15,
      "y_clamp": [
        -0.925,
        0.925
      ],
      "s": "odd +1; even -1"
    },
    "oracle_publication": false,
    "evaluation_dynamic_geometry": true,
    "success_gate": false
  },
  "seed_rule": "inference=101+10000*index+2*request_id; DDPM=inference+1",
  "navigation_verdict": {
    "priority": [
      "REPAIR_BETTER_SO",
      "REPAIR_WORSE_SO",
      "REPAIR_EQUAL_SO"
    ],
    "better": "success(M2)>=success(M1)+2 AND safety_failure(M2)<=safety_failure(M1)",
    "worse": "success(M2)<=success(M1)-2 OR safety_failure(M2)>=safety_failure(M1)+2",
    "safety_failure": "obstacle collision or corridor intrusion",
    "auxiliary_noninferiority_removed": true,
    "paired_descriptive": [
      "SO stopped-time fraction M2-M1",
      "SO box-passage time M2-M1"
    ],
    "bootstrap_replicates": 20000,
    "bootstrap_seed": 20261031
  },
  "smoke": {
    "scene": "SO",
    "method": "M2_REPAIR",
    "seconds": 30,
    "count": 1,
    "excluded_from_main": true,
    "required_events": [
      "spawn",
      "depth observation",
      "ALL_UNSAFE",
      "repair attempt"
    ]
  },
  "campaign": "only after READY and smoke; reuse Phase18 serial/restart-without-retry/lock/socket checks; user launches main, no assistant main navigation",
  "protected_sha256": {
    "research/nomad_phase19r/repair.py": "01314bdc267cfda557275f5ba5844e4433eea2ac86bfbdf9c8ea7f2b04eb516a",
    "research/nomad_phase19r/evaluate.py": "7520b87af37728e5e192021ef9290183f866e9b91c6327a4937628a6ad2b2f3c",
    "research/nomad_phase19s/srg.py": "865c8d457604da192bf86e1d911cec0ca006efe6c1143cbb361269c33ba70054",
    "research/nomad_phase18d/rollout.py": "1cd7b1bdbd3139369ef7c3c36839923afa8b09c0d09bcf55f4b0076d3728798f",
    "research/nomad_phase18d/speed_profile.py": "912432a9458db68799f2a2603643f03c74cf5a254f5ee713104ab4ba3f572629",
    "research/nomad_phase0/graph_v4.py": "e7b7a9b784189644564df24b7c0d02af6e1497f9ef11c63616f597634aa1c445",
    "research/nomad_phase0/pure_pursuit.py": "5e6010bad728dc7130457dfc71da0a92e5e0d86f1a63dfefc2aae1105475993d",
    "research/nomad_phase0/chunk_execution.py": "b93858c5a16818ea1c406f3b1c25142baeb6d2abc3c47a6c3222376961a142c8",
    "research/nomad_phase15b/depth.py": "f6072c9591c7696feef66d65d1048fbf7ad65b0ed0ba408a5f746e8577718919",
    "research/nomad_phase16/geometry.py": "044ac3e855d1445d97e9e63400e521a80bbaffcf34f81c26fa2e2809157bc0e0",
    "research/nomad_phase17/execution.py": "6f2fbeaad9be6684159276da53b010a1604b8d70f72443cddbbac8ba7b926fa5",
    "research/nomad_phase18/campaign.py": "3492de134860e6c4c211bd43a2faba7db4bd7c2ddc16b9314994c2115e3709b2",
    "research/nomad_isaac/clearance.py": "70213b966898efb17e070ead2c24a77b0b58478c1d6b228045157fe91dba048c",
    "research/nomad_isaac/common.py": "37411b364e3d39547d2c134e2cbe67f9b9e5d09b7cfad6709567960859e4d03d"
  }
}
```
