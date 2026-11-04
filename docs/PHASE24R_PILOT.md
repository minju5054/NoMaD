# Phase24-R pilot preparation

Phase24 results and labels are preserved. Its 12 SLW records are listed as `SCENE_BOUNDARY_NOT_PERCEIVABLE` in `research/results/phase24r/phase24_slw_validity.json` and are excluded from Phase24-R pooling.

## Registered changes from Phase24

| Area | Phase24 | Phase24-R |
|---|---|---|
| SLW walls | Renderer fixed y=±1.55 while evaluation used ±0.9 | Scene-specific inner faces are checked against all four corridor faces before navigation; mismatch refuses launch |
| G detour planning field | Base V1; unknown free | C0 R3 split field: base first0.3m, strict occupied/unknown/stale-free elsewhere |
| G certificate | Node+midpoint hard condition only | Output certificate:9points/segment, h/√2+L/16, conservative start, exact segment distance; alternate output may replace a rejected one |
| G live check | DETOUR only | Same continuous certificate in NORMAL and DETOUR |
| Alignment | Graph pose rotation segments only | Before a new/entered segment whose chord differs by>30°, rotate in place to chord±10°; record theta–chord discrepancy |
| Component lifetime | 10s t_new window | Occupied+observed cells stay active until passed along u_ref |
| No-progress | Forward3s<0.2m | Forward criterion OR fixed-current-component distance reduction<0.1m |
| Goal | Existing common async tolerance | Audited: all Phase24 runs use shared0.3m test; Phase24 L2_133_G never entered it |

The graph objective, node/midpoint hard constraints, soft obstacle term/weight, solver settings, NoMaD/checkpoint/Topomap, seeds, timeout and `G_HELPS/G_HURTS/G_INCONCLUSIVE` function are fixed before the new pilot. C0/C1 retain their existing solver implementations; decision/depth/certificate interfaces are shared.

## Verification

| scene | method | technical_validation | geometry_error_m | command_pose_error_m | launcher_wall_s |
| --- | --- | --- | --- | --- | --- |
| L2 | G | PASS | 7.4506e-10 | 0 | 211.8 |
| L2 | C0 | PASS | 7.4506e-10 | 0 | 201.12 |
| L2 | C1 | PASS | 7.4506e-10 | 0 | 185.66 |
| SLW | G | PASS | 7.4506e-10 | 0 | 225.24 |
| SLW | C0 | PASS | 7.4506e-10 | 0 | 210.47 |
| SLW | C1 | PASS | 7.4506e-10 | 0 | 209.98 |

Eight unit tests passed. Six smoke runs passed and are excluded. Every smoke USD passed the four-wall check; maximum inner-face error was 7.45e-10m. The shared runtime uses the existing `distance <= goal_tolerance_m` condition, and the stored Phase24 audit found 24/24 recorded goal entries equal to the trajectory-derived predicate.

New main matrix: seed141–144 × L2/SLW × G/C0/C1 =24 runs, seed-first random order in `online_protocol.json`. Main has not started. Max socket path length is 90 bytes. Estimated 106.6minutes.
