# Phase 2 policy diagnosis — frozen protocol

Base `e2eac6b`, same Phase 0 branch. C0 runs before twelve new D0 navigations. Protocol: `research/nomad_diagnostic/protocol.json`. Existing source artifacts are read-only.

C0 uses all 127 actual inference inputs from the 16 Phase 2 main M0 runs after oracle availability and before entire-footprint passage. The 167 busy captures in that window are counted separately; they have no invented seed or subgoal. Re-encode the original candidate batch and saved selected subgoal, reuse saved initial noise and DDPM seed, and compare conditioned normalized output, metric output and selected condition at predeclared tolerances. Decode official exploration mask=1 with identical initial/DDPM noise. The fake goal has an independent fixed RNG; official `explore.py` uses no-grad goal-masked encoding. No navigation is performed in C0.

User-fixed pooled observation bands (also report all run fractions): `<10% RARE`, `10% <= p <30% INDETERMINATE`, `>=30% SUFFICIENT`. Indicator is at least one native-safe sample among eight. Apply the same bands to both modes. A short safe prediction that does not reach the box center X is **not demonstrated avoidance**: no lateral extrapolation; report NOT_REACHED and safe-and-crossing separately. Native safety is full eight-point polyline clearance >=2cm plus corridor containment, using existing geometry functions; it does not establish actual PP execution safety.

C1: d=.8 and 1.2m, indices1–3 each. C2: d=1m, lateral placement offsets +.2/-.2/+.2m. C3: d=1m, centered, official goal mask=1 from oracle-public next FRESH until actual X>box rear+.30, then latch back to conditioned. Topomap localization/distance evaluation continues unchanged to preserve node logs; only the masked condition is decoded during exploration. Oracle data only controls this diagnostic inference-mode switch, never PP, selection or stopping. Decision pose is logged separately; native world paths retain observation anchors.

All runs: original sample0 PP, 4/9/72Hz, 1s waypoint timeout, 90s bounded navigation, no additional result delay, seed101+10000*index+2*request_id, DDPM+1. Twelve attempts, no retry or parameter changes. Runtime hooks are explicitly gated by diagnostic mode; legacy option restrictions remain. Existing model, checkpoint, Topomap, PP, PD, Graph and collision code remain unchanged.

Minimal preflight: four diagnostic unit tests and 13 existing Phase2/delivery tests pass. Topomap21-node RGB/hash check and fixed checkpoint/source hashes pass. Graph is not called and sample selection is disabled. Actual command/pose replay, swept clearance, RGB history hashes, gate/mask schedule and seed audits run after each navigation. Technical failure stops further launch attempts.

C1 success suggests delay may contribute; C1 failure with C2/C3 success indicates conditional avoidance. All three failing together with masked pooled ratio<10% supports the specified current-setting failure diagnosis. D0 retains real asynchronous inference age, so failure alone cannot establish that delay/handoff has zero influence. Results are exploratory N=3 per condition and not a model-wide capability proof.

Pending: C0 GPU reproduction and all twelve navigations. No result is PASS before execution.
