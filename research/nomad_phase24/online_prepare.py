"""Freeze the tested pilot only after all three excluded smoke runs pass."""
import json,copy
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_phase17.report import table
from .online_metrics import audit
from .online_config import verify
from .report import plots

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase24_online'
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def main():
    p=verify();assert p['status']=='SMOKE_DRAFT';smoke=[]
    for method in p['methods']:
        run=Path(p['smoke_runs'][method]);result=audit(run)
        assert result['technical_validation']=='PASS';write(OUT/'online_smoke'/f'{method}.json',result)
        provenance=json.loads((run/'provenance.json').read_text());assert provenance['smoke_excluded'] and provenance['index']==95
        smoke.append(dict(method=method,technical_validation=result['technical_validation'],command_pose_error_m=result['command_pose_error_m'],inference_count=result['inference_count'],launcher_wall_s=result['launcher_wall_s'],output=str(run)))
    root=ROOT.parent/'artifacts/isaac6/phase24_pilot_01';sockets=[str(socket_path_for_run(root/'main'/f"{r['scene']}_{r['index']:03d}_{r['method']}")) for r in p['main_order']]
    assert len(set(sockets))==24;maximum=max(validate_socket_path(Path(s)) for s in sockets);assert maximum<100
    sources={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))}
    p.update(status='FROZEN',source_sha256=sources,offline_gate_sha256=sha256_file(ROOT/'research/results/phase24_offline/gate.json'),estimated_total_minutes=(24*max(r['launcher_wall_s'] for r in smoke)*1.15+180)/60,
        estimate_basis='24runs times slowest seed95 launcher wall time,15%allowance plus3minutes report; main outcomes not observed',socket_max_bytes=maximum)
    write(HERE/'online_protocol.json',p)
    readiness=dict(passed=True,smoke=smoke,tests_passed=18,protocol_sha256=sha256_file(HERE/'online_protocol.json'),source_sha256=sources,max_socket_bytes=maximum,new_main_runs=0,estimated_total_minutes=p['estimated_total_minutes'])
    write(OUT/'online_readiness.json',readiness)
    # Presentation-only: NORMAL has no progress factor. Do not draw the unused
    # direction stored for possible fallback; source records remain untouched.
    op=json.loads((HERE/'protocol.json').read_text());records=[]
    for key in op['figures']:
        r=json.loads((ROOT/f'research/results/phase24_offline/records/{key}.json').read_text())
        if r['methods']['G']['plan']['mode']=='NORMAL':r['methods']['G']['plan']['u_ref']=None
        records.append(r)
    plots(records,op['figures'])
    doc=ROOT/'docs/PHASE24_DECISION_GRAPH.md';marker='\n## Online preparation\n';text=doc.read_text().split(marker)[0]
    text+=marker+'\nThe registered offline gate passed. All three required final L2seed95smokes passed; the earlier Gsmoke before the timeout-prediction fix is also preserved. All four attempts are excluded from the24-run pilot. The pilot has not started.\n\n'+table(smoke)+'\n\n'
    text+=f"Tests:18/18. Short sockets:maximum{maximum}bytes. Online protocol SHA256 `{readiness['protocol_sha256']}`. Main order:seed131–134→sceneL2/SLW→registered method permutation;24runs, one attempt each; lock/resume and completed-run preservation. Estimated total{p['estimated_total_minutes']:.1f}minutes.\n\n"
    text+='Application:install paths at exactlydispatch+36integration ticks; keep the global9Hzcommand phase. The first command using that path is the next eligible control tick. Every new NORMAL FRESH launches G; a no-output result applies bounded braking and launches one DETOUR solve. Mode changes invalidate obsolete-mode jobs. DETOUR keeps the frozen20Fhandover conditions (the no-new-obstacle exit applies to triggerB; the originalA/no-component branch retains endpoint/6s/depth-certificate exits). Pending native candidates are logged and selection resumes on the next FRESH after handover. Recovery is the unchanged12-turn Phase17last resort. A*is only C1.\n\n'
    text+='Preflight execution fix: '+p['preflight_execution_fix']+' The original Gsmoke is preserved at '+p['preserved_smoke_attempts'][0]+'.\n\n'
    text+='Collision in both offline and online decisions means oracle geometric obstacle overlap or negative footprint wall clearance; corridor stops are also a separate column. NoMaD, geometry, constants and frozen C0/C1executors were not edited. Online Guses the exact graph factors tested offline.\n\n'
    text+='The four offline figures retain their registered snapshot IDs. Unused u_refarrows are hidden in NORMAL-mode figures; numerical results and raw records are unchanged.\n'
    doc.write_text(text);print(json.dumps(dict(passed=True,tests=18,smokes=3,estimated_minutes=p['estimated_total_minutes'],main_runs_started=0)))
if __name__=='__main__':main()
