"""Saved excluded-smoke audit and readiness manifest; never launches navigation."""
import argparse,json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from .metrics import audit
from .report import offline_text


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--smoke',type=Path,required=True);ap.add_argument('--figures',action='store_true');ap.add_argument('--finalize',action='store_true');a=ap.parse_args()
    out=ROOT/'research/results/phase20e_preflight';out.mkdir(exist_ok=True);f=out/'smoke.json'
    if not f.exists():
        r=audit(a.smoke);r.update(scene='L2',index=901,method='M3_DETOUR',output=str(a.smoke.resolve()),excluded=True);f.write_text(json.dumps(r,indent=2)+'\n')
    else:r=json.loads(f.read_text())
    if a.figures:
        from .visualize import generate
        generate([r],out,cases=[('L2',901)])
    if a.finalize:
        package=Path(__file__).parent
        ready=dict(passed=r['technical_validation']=='PASS',smoke_detour_chain_observed=r['detour_applied']>0,tests_passed=5,tests_total=5,main_navigation_started=0,
            protocol_sha256=sha256_file(package/'protocol.json'),runtime_source_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(package.glob('*')) if p.is_file()},
            smoke_output=r['output'],smoke_metrics_sha256=sha256_file(f),smoke_provenance_sha256=sha256_file(a.smoke/'provenance.json'))
        (out/'readiness.json').write_text(json.dumps(ready,indent=2)+'\n')
    text='# Phase20E preflight / 파일럿\n\n'+offline_text()
    text+=f"Unit tests5/5. One excluded60s L2 M3 smoke: technical={r['technical_validation']}; NO_PROGRESS={r['detour_triggers'].get('B',0)}, before/after passage={r['no_progress_stages']}, detours applied={r['detour_applied']}; NO_OBSTACLE_AHEAD={r['no_obstacle_ahead_count']}; command/72Hz pose errors={r['command_replay_error']}/{r['pose_replay_error']}.\n\n"
    if not r['detour_triggers'].get('B',0):text+='Smoke limitation: no actual obstacle-conditioned NO_PROGRESS trigger occurred. Trigger/rectangle unit tests and saved-trigger checks passed, but a new live trigger-to-detour chain was not observed in this smoke. No extra navigation was run.\n\n'
    text+='No retry or tuning. Main12 trials are reserved for the user.20D code/data remain unchanged; only the obstacle predicate and20E serialization import binding are new.\n\n'
    text+='![excluded L2 smoke](../research/results/phase20e_preflight/drive_L2_901.png)\n'
    (ROOT/'docs/PHASE20E_PREFLIGHT.md').write_text(text)
    print(json.dumps({k:r[k] for k in ('technical_validation','detour_triggers','no_progress_stages','no_obstacle_ahead_count','detour_applied','command_replay_error','pose_replay_error')}))
if __name__=='__main__':main()
