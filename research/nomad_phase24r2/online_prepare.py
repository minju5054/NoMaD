"""Freeze the preregistered R2 protocol after the single excluded G smoke."""
import json, csv
from pathlib import Path
from nomad_isaac.common import ROOT, sha256_file
from nomad_isaac.socket_path import socket_path_for_run, validate_socket_path
from .online_config import protocol, verify
from .online_metrics import audit, rows
from .campaign import jobs
from .storage import atomic_json, capacity
import numpy as np

HERE=Path(__file__).parent
OUT=ROOT/'research/results/phase24r2'


def main():
    p=verify();assert p['status']=='DRAFT_PENDING_SMOKE'
    run=ROOT.parent/'artifacts/isaac6/phase24r2_smoke_01/L2_095_G'
    r=audit(run);assert r['technical_validation']=='PASS'
    geometry=json.loads((run/'geometry_check.json').read_text());assert geometry['status']=='PASS'
    inputs=[json.loads(f.read_text()) for f in sorted((run/'g_jobs').glob('input_*.json'))]
    detours=[j for j in inputs if j['mode']=='DETOUR']
    assert detours,'Smoke did not exercise the changed DETOUR job transport'
    with (run/'agent_trajectory.csv').open() as stream:trajectory=list(csv.DictReader(stream))
    times=np.array([float(q['simulation_time_s']) for q in trajectory])
    xy=np.array([[float(q[k]) for k in ('x_m','y_m')] for q in trajectory])
    anchor_error=0.
    for j in detours:
        assert j['return_line']['sigma_m']==.3 and j['return_line']['weight']==1.
        assert j['return_line']['u_ref']==j['u_ref']
        result=json.loads((run/'g_jobs'/f"result_{j['job_id']:04d}.json").read_text())['result']
        assert result['return_line']==j['return_line']
        k=int(np.argmin(abs(times-j['return_line']['anchor_tick']/72)))
        assert abs(times[k]-j['return_line']['anchor_tick']/72)<1e-9
        anchor_error=max(anchor_error,float(np.linalg.norm(xy[k]-j['return_line']['anchor_world'])))
    assert anchor_error<=1e-12
    root=ROOT.parent/'artifacts/isaac6/phase24r2_pilot_01'
    plan=jobs(root);sockets=[socket_path_for_run(Path(j['output'])) for j in plan]
    sizes=[validate_socket_path(s) for s in sockets]
    assert len(set(map(str,sockets)))==12 and max(sizes)<100
    disk=capacity(root,plan)
    # Baseline cost estimate uses prior completed runs; it cannot affect this
    # preregistered matrix or the new factor. No main output is inspected.
    prior=ROOT.parent/'artifacts/isaac6/phase24r_pilot_01/metrics'
    old=[json.loads(f.read_text()) for f in prior.glob('L2_*.json')]
    wall={m:(r['launcher_wall_s'] if m=='G' else max(x['launcher_wall_s'] for x in old if x['method']==m)) for m in p['methods']}
    minutes=(sum(wall[j['method']] for j in plan)*1.15+180)/60
    sources={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))}
    p.update(status='FROZEN',source_sha256=sources,smoke_runs={'L2_G':str(run)},
        smoke_summary=dict(technical_validation='PASS',excluded=True,command_pose_error_m=r['command_pose_error_m'],
                           geometry_max_error_m=geometry['max_error_m'],detour_jobs=len(detours),return_anchor_error_m=anchor_error,launcher_wall_s=r['launcher_wall_s']),
        socket_max_bytes=max(sizes),estimated_total_minutes=minutes,
        estimate_basis='4x new G smoke wall time +4x prior L2 C0 max +4x prior L2 C1 max; 15% allowance +3min report')
    atomic_json(HERE/'online_protocol.json',p)
    ready=dict(passed=True,tests_passed=15,new_tests=7,inherited_tests=8,
        protocol_sha256=sha256_file(HERE/'online_protocol.json'),source_sha256=sources,
        max_socket_bytes=max(sizes),smoke=p['smoke_summary'],main_runs_started=0,
        estimated_total_minutes=minutes,disk_at_freeze={k:v for k,v in disk.items() if k!='details'})
    atomic_json(OUT/'online_readiness.json',ready);atomic_json(OUT/'online_smoke/L2_G.json',r)
    text=f'''# Phase24-R2 endpoint return pilot — preregistration

Base commit: `d133909`. L2 only, G/C0/C1, paired seeds151–154 (offset10000×index), twelve new runs. Existing Phase24/R code, outcomes and labels are preserved. C1 is descriptive. No tuning; exact simulator odometry. The single L2seed95G technical smoke is excluded from results. Main execution is user initiated.

## Only method change

G DETOUR adds $J_{{lat}}=((p_{{10}}-a)^Tn/0.30)^2$, with weight1, $n=(-u_y,u_x)$ and existing unit direction $u=u_{{ref}}$. Its xy gradient is $2((p_{{10}}-a)^Tn)n/0.30^2$; all other variable derivatives are zero. Coordinates are transformed exactly into the predicted-start frame.

For the existing component-based direction, $a$ is the robot pose position at the component's depth-derived `t_new_tick`. Without a component, $a$ is the actual position when DETOUR starts. It is captured once per detour, never re-anchored at the predicted pose or taken from oracle spawn. The unchanged direction selector decides which source applies. Every DETOUR job/result logs the full line, source and anchor tick.

NORMAL is bitwise unchanged. Progress1.2m, obstacle node/midpoint constraints and soft cost, kinematics, time, curvature, initializations, 0.5s anytime rule, output/live continuous certificates, chord-priority rotation, persistent-component trigger, recovery, fallback and goal tolerance inherit Phase24-R. C0/C1 inherit their exact Phase24-R execution factory. Methods receive no oracle geometry.

## Fixed decision

Pilot `R2_PASS` iff G goal successes ≥ C0−1 AND G collisions=0 AND G box passages ≥ C0−1; otherwise `R2_FAIL`. Collision uses the frozen Phase24-R oracle obstacle/wall geometric-overlap metric; margin-only corridor stops remain separately reported. Technical failures remain visible and unsuccessful, with no retry or result-based changes.

## Metrics

All Phase24-R audit metrics remain in runs.json/execution.csv. Added: maximum |y| during accepted detour execution; |y| exactly five seconds after box passage, linearly interpolated from72Hz poses (missing if the run ends earlier); and closest-node progress after each actual detour handover. The latter is last observed closest index at handover+5s minus last at handover, with incomplete-five-second windows flagged and run-end progress also reported. Run termination during a detour is not invented as a handover. No missing observation is extrapolated.

## Validation and execution

15/15 tests passed (7new,8frozen R regression). Tests cover line anchors, rotated-frame analytic gradient within1e−5, unchanged NORMAL/constraints/runtime constants, an obstacle blocking the return line with a feasible certificated detour using the unchanged seven starts and SLSQP options, new metrics and a synthetic twelve-run report.

One excluded G smoke completed technically: command-to-pose error {r['command_pose_error_m']:.3g}m, USD/evaluation wall error {geometry['max_error_m']:.3g}m; {len(detours)} DETOUR jobs transported the fixed return line. The smoke outcome is not used to change any factor or criterion. Maximum socket length {max(sizes)}bytes. Estimated campaign wall time {minutes:.1f}minutes including report.

Full RGB/depth retention is seed151 only; the other seeds keep the frozen compact metrics/map/archive policy. Disk guard requires estimated remaining storage plus20GB before every run. At freeze: expected {disk['expected_remaining_bytes']/1e9:.2f}GB, required {disk['required_free_bytes']/1e9:.2f}GB, available {disk['free_bytes']/1e9:.2f}GB. If insufficient, the campaign stops before launching the next run without modifying data.

Protocol and source SHA256s are frozen in online_protocol.json; old sources are checked as well. The campaign uses the Phase24-R lock/resume/atomic metadata structure and generates, commits and pushes this report after the twelve runs.
'''
    (ROOT/'docs/PHASE24R2_PILOT.md').write_text(text)
    print(json.dumps(dict(status='FROZEN',tests=15,main_runs_started=0,estimate_minutes=minutes,
                          disk_enough=disk['enough'],required_GB=disk['required_free_bytes']/1e9,free_GB=disk['free_bytes']/1e9)))


if __name__=='__main__':main()
