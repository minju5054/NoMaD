"""Phase20 gate report. Main campaign reporting is gated on offline READY."""
import json
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table


def preflight_report(out,verdict,six,sha,protocol):
    text='# Phase 20 — SO-only repair recovery pilot\n\n'
    text+=f"**파일럿 / Offline gate: {verdict['label']}**. Execution SHA: `{sha}`. Protocol hash: `{sha256_file(out/'protocol.json')}`.\n\n"
    text+='The revised main matrix is SO only, seed indices74–79, M1 ROTATE and M2 REPAIR, 12 serial trials. No SLW/LC/CL navigation or noninferiority judgment is planned in this phase. None of these pilot trials has been executed by this offline preflight.\n\n'
    text+='## 0-a. R2 definition\n\n'
    text+='R2 inherits Phase19R initialization, 14 XY variables, fixed B, priors/smoothness/heading objective, curvature≤8, length preservation, trust region, analytic Jacobian, SLSQP(maxiter100, ftol1e−8) and single-attempt solve. Only the first0.30m clearance threshold is relaxed. Oracle geometry never enters optimization, selection or SP/alignment control.\n\n'
    text+='Let c_B = saved depth SDF(B) − h/√2 (the same conservative footprint clearance convention as Phase16D/19R). At each current optimized path sample q, cumulative arclength s(q)≤0.30m uses min(0.025,c_B−0.005); later samples use0.025m. The original per-segment nine-point bound d(q)−h/√2−L/16 is unchanged. Zone membership is recomputed from the optimized path, not the initial path. The piecewise-constant threshold has an analytic zero derivative away from s=0.30m; the zone boundary is explicitly nonsmooth. No smoothing, tuning or restart is introduced.\n\n'
    text+='Exact depth certificate splits the continuous path at0.30m and reuses exact distance to occupied cell centers minus robot radius on both subpaths. The cut is included in both certificates: a continuous far-side path must satisfy0.025m in the limit at the cut. Acceptance still requires solver success, maximum constraint violation≤1e−7 and both exact certificates.\n\n'
    text+='Selected repair is the accepted sample with minimum mean edit (lower-index tie); all8 are attempted once unless Phase19R short/degenerate exclusion applies. Timing p95 uses eligible per-sample attempts including certificate. Eight-sample serial time and counts exceeding the planned0.5s online deadline are separately reported.\n\n'
    causes=[dict(cause=k,**v) for k,v in verdict['cause_success'].items()]
    text+=table(causes)+'\n\n```json\n'+json.dumps(verdict,indent=2)+'\n```\n\n'
    text+='READY requires zero **selected** repaired-path oracle penetrations, ≤7% oracle overlap among selected 1.5s SP+departure-alignment rollouts, and per-sample solve p95≤0.20s. All accepted sample-path penetrations are reported separately, including unselected paths. There is no minimum repair-success gate. No-selected-repair is not evidence of readiness.\n\n'
    text+='SP and trigger S match Phase19S, with trigger P removed. Actual recorded initial v and heading are used; alignment is not forced when v≥0.01m/s. The1.5s clock includes braking/rotation. The rollout is endpoint/horizon bounded and oracle-passive, so overlap is monitored but never changes control.\n\n'
    text+='## 0-b. Six published Phase19S 1.5s collisions\n\n'+table(six)+'\n\n'
    text+='These six cases were selected from the previously published D3 SRG prefix-overlap flags before any R2 outcome. Their saved clearances are reproduced with S-only control. Unknown fractions are descriptions of the fixed repaired path, not evidence that unknown space caused the collision. The one-line reasons distinguish trigger inactivity from a subsequent tracking failure; no experiment setting is changed from this diagnosis.\n\n'
    text+='## Validation and execution status\n\n'
    text+='Five unit tests passed: R2 constraint/objective analytic Jacobians versus finite differences (≤1e−5 away from the hard zone boundary), exact split certificate, SP replacement/straight-speed/pre-turn braking, trigger S conditions without pivot, and equality to protected S-only behavior. Original code/raw/results remain unchanged. The frozen candidate protocol and deterministic12-job order are recorded below.\n\n'
    if verdict['label']=='NOT_READY':
        text+='**Stopped at the mandatory offline gate.** Online repair-thread integration, SO smoke/technical gate, main batch and main result judgments were not executed. No campaign launch command is provided. Constants and thresholds were not changed to pass the gate. The main execution/report infrastructure is not claimed complete.\n\n'
    else:text+='Offline READY permits further online integration and the single SO M2 smoke. READY alone is not a claim that the campaign is prepared or that driving is safe.\n\n'
    text+='## Limits\n\nSection0 is post-hoc analysis of Phase18 saved events. A fixed path rollout has no next FRESH, changing depth map or NoMaD response. Zero path penetration and short-horizon safety do not establish closed-loop driving safety. Simulation pose is assumed exact; oracle is restricted to evaluation.\n\n'
    text+='## Frozen SO pilot and offline protocol\n\n```json\n'+json.dumps(protocol,indent=2,ensure_ascii=False)+'\n```\n'
    with (ROOT/'docs/PHASE20_REPAIR_DRIVE.md').open('x') as f:f.write(text)
