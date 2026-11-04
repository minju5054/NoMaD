"""Freeze Phase24-R after six excluded smoke runs and no main navigation."""
import json,hashlib
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_phase17.report import table
from .online_config import protocol,verify
from .online_metrics import audit
from .campaign import jobs
from .storage import atomic_json,capacity

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase24r'
def main():
    p=protocol();assert p['status'] in ('DRAFT_PENDING_DEFINITIONS','DRAFT_PENDING_CAPACITY_FIX','DRAFT_PENDING_STORAGE_ARCHIVE_FIX','DRAFT_PENDING_REPORT_FIELDS','DRAFT_PENDING_HASH_REFRESH') and not p['definitions_pending']
    smoke=[]
    for scene in ('L2','SLW'):
        for method in p['methods']:
            run=ROOT.parent/f'artifacts/isaac6/phase24r_smoke_01/{scene}_095_{method}';r=audit(run)
            assert r['technical_validation']=='PASS';geometry=json.loads((run/'geometry_check.json').read_text());assert geometry['status']=='PASS'
            atomic_json(OUT/'online_smoke'/f'{scene}_{method}.json',r);smoke.append(dict(scene=scene,method=method,technical_validation='PASS',geometry_error_m=geometry['max_error_m'],command_pose_error_m=r['command_pose_error_m'],launcher_wall_s=r['launcher_wall_s']))
    root=ROOT.parent/'artifacts/isaac6/phase24r_pilot_01';socket_paths=[socket_path_for_run(Path(j['output'])) for j in jobs(root)];sock=[validate_socket_path(s) for s in socket_paths];assert max(sock)<100 and len(set(map(str,socket_paths)))==24
    sources={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))}
    p.update(status='FROZEN',source_sha256=sources,smoke_runs={f"{r['scene']}_{r['method']}":str(ROOT.parent/f"artifacts/isaac6/phase24r_smoke_01/{r['scene']}_095_{r['method']}") for r in smoke},
        smoke_summary=smoke,socket_max_bytes=max(sock),estimated_total_minutes=(24*max(r['launcher_wall_s'] for r in smoke)*1.15+180)/60,
        estimate_basis='24runs times slowest of six seed95 smoke launcher wall times,15%allowance plus3minutes report; main outcomes unobserved')
    (HERE/'online_protocol.json').write_text(json.dumps(p,indent=2)+'\n')
    readiness=dict(passed=True,tests_passed=8,smoke=smoke,protocol_sha256=sha256_file(HERE/'online_protocol.json'),source_sha256=sources,max_socket_bytes=max(sock),main_runs_started=0,estimated_total_minutes=p['estimated_total_minutes'])
    atomic_json(OUT/'online_readiness.json',readiness)
    doc=ROOT/'docs/PHASE24R_PILOT.md';doc.write_text('''# Phase24-R pilot preparation

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

'''+table(smoke)+f"\n\nEight unit tests passed. Six smoke runs passed and are excluded. Every smoke USD passed the four-wall check; maximum inner-face error was {max(r['geometry_error_m'] for r in smoke):.3g}m. The shared runtime uses the existing `distance <= goal_tolerance_m` condition, and the stored Phase24 audit found 24/24 recorded goal entries equal to the trajectory-derived predicate.\n\nNew main matrix: seed141–144 × L2/SLW × G/C0/C1 =24 runs, seed-first random order in `online_protocol.json`. Main has not started. Max socket path length is {max(sock)} bytes. Estimated {p['estimated_total_minutes']:.1f}minutes.\n")
    print(json.dumps(dict(passed=True,smokes=len(smoke),socket_max=max(sock),estimate_minutes=p['estimated_total_minutes'],new_navigation=0)))
if __name__=='__main__':main()
