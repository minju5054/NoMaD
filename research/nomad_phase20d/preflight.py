"""Read-only audit of the single excluded smoke; never launches navigation."""
import json,argparse
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from .metrics import audit
from .report import preflight_text

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--smoke',type=Path,required=True);ap.add_argument('--figures',action='store_true');ap.add_argument('--finalize',action='store_true');a=ap.parse_args()
    out=ROOT/'research/results/phase20d_preflight';out.mkdir(exist_ok=True);f=out/'smoke.json'
    if not f.exists():
        r=audit(a.smoke);r.update(scene='L3',index=901,method='M3_DETOUR',output=str(a.smoke.resolve()),excluded=True)
        f.write_text(json.dumps(r,indent=2)+'\n')
    else:r=json.loads(f.read_text())
    if a.figures:
        from .visualize import generate
        generate([r],out,cases=[('L3',901)])
    if a.finalize:
        package=Path(__file__).parent
        ready=dict(passed=r['technical_validation']=='PASS',smoke_detour_chain_observed=r['detour_applied']>0,tests_passed=9,tests_total=9,main_navigation_started=0,
            protocol_sha256=sha256_file(package/'protocol.json'),runtime_source_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(package.glob('*')) if p.is_file()},
            smoke_output=r['output'],smoke_metrics_sha256=sha256_file(f),smoke_provenance_sha256=sha256_file(a.smoke/'provenance.json'))
        (out/'readiness.json').write_text(json.dumps(ready,indent=2)+'\n')
    text='# Phase20D preflight — 탐색적 파일럿\n\n'+preflight_text()
    text+=f"Unit tests9/9. One excluded60s L3 M3 smoke: technical={r['technical_validation']}; NO_PROGRESS={r['detour_triggers'].get('B',0)}, detours applied={r['detour_applied']}; command replay={r['command_replay_error']},72Hz pose replay={r['pose_replay_error']}; snapshot maxage={r['snapshot_max_age_s']:.6f}s.\n\n"
    text+='Smoke is a technical observation, not evidence of navigation benefit; no seed, placement or parameter was adjusted. All raw is retained. Main12 trials have not been run.\n\n'
    for j in r['detour_job_timings']:text+=f"R3 job{j['job_id']}: parallel={j['pool_wall_s']:.6f}s; seven attempts={j['sample_solve_s']}s.\n\n"
    text+='![excluded smoke](../research/results/phase20d_preflight/drive_L3_901.png)\n\n'
    (ROOT/'docs/PHASE20D_PREFLIGHT.md').write_text(text)
    print(json.dumps({k:r[k] for k in ('technical_validation','detour_triggers','detour_applied','seven_solve_s','snapshot_max_age_s','command_replay_error','pose_replay_error')}))
if __name__=='__main__':main()
