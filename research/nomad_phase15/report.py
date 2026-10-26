"""One command: offline evaluation, figures, report, scoped commit and push."""
import argparse
import json
from pathlib import Path
import subprocess
from nomad_isaac.common import ROOT, sha256_file, write_json
from .replay_render import DEFAULT_ROOT
from .evaluate import evaluate

OUT=ROOT/'research/results/phase15a'
DOC=ROOT/'docs/PHASE15A_DEPTH_SDF.md'


def f(value, digits=3):
    return '—' if value is None else f'{value:.{digits}f}'


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def document(summary):
    conditions=summary['conditions'];rows=[];timing=[];conf=[];cause=[]
    for name,c in conditions.items():
        err=c['clearance_error_m']; dangerous=c['dangerous_oracle_clearance_m'];t=c['timing']
        rows.append([name,c['samples'],f(100*c['agreement_fraction'])+'%',f(100*c['dangerous_fraction'])+'%',
            f(100*c['conservative_fraction'])+'%',f(err['median']),f(err['p5']),f(err['p95']),f(100*c['selection_agreement_fraction'])+'%'])
        for part in ('pointcloud_ms','accumulate_ms','sdf_ms','update_ms'):
            timing.append([name,part,f(t[part]['median']),f(t[part]['p95'])])
        counts=c['confusion'];conf.append([name,*[counts.get(key,0) for key in ('both_safe','both_unsafe','depth_only_safe','depth_only_unsafe')]])
        cause.append([name,*[c['error_causes'].get(key,0) for key in ('UNKNOWN','HEIGHT_FILTER','RANGE_EXCEEDED','OTHER')],
                      f(dangerous['median']),f(dangerous['p5']),f(dangerous['p95'])])
    text=[
        '# Phase 15-A — Depth local SDF offline validation','',
        f"**{summary['label']}**. Render SHA `{summary['render_git_sha']}`; report SHA `{summary['report_git_sha']}`.",'',
        f"{summary['runs']} Phase 13 runs; {summary['frames']} saved RGB capture poses replayed with depth only. No navigation, inference or Graph solve. Simulator pose is assumed exact (no odometry error).",
        '',table(['Noise','Samples','Agreement','Dangerous','Conservative','Error median m','p5 m','p95 m','Selection match'],rows),'',
        '## Confusion and dangerous decisions','',
        table(['Noise','Both safe','Both unsafe','Depth only safe','Depth only unsafe'],conf),'',
        table(['Noise','Unknown','Height filter','Range exceeded','Other','Danger oracle median m','p5 m','p95 m'],cause),'',
        'Attribution is diagnostic evidence at the oracle-limiting surface, not a causal proof. Height/range rejected-hit support within 2cm takes precedence over unknown; all support flags remain in switches.csv. The virtual xmin corridor boundary is not a rendered back wall.',
        '', '## Timing','',table(['Noise','Update component','Median ms','p95 ms'],timing),'',
        'Pointcloud includes noise injection/backprojection; accumulation includes occupancy/coverage; SDF includes the distance transform. Totals exclude renderer, disk I/O and sample evaluation. No warmup/timing observations are discarded.',
        '', '## FRESHEST-SAFE counterfactual','',
        'All 8 native samples remain observation-anchored. Safety is evaluated on the nearest-B projection suffix, without a connector. Among safe suffixes choose maximum remaining arclength, tie low sample index. No safe candidate is null/ALL_UNSAFE. These are offline selections, not executed navigation.',
        '',table(['Noise','Selected','Selected oracle unsafe','Both null','Selected oracle clearance median / p5 / p95 m'],[
            [name,c['selected_count'],c['selected_unsafe'],c['selection_both_null'],
             ' / '.join(f(c['depth_selection_oracle_clearance_m'][k]) for k in ('median','p5','p95'))] for name,c in conditions.items()]),'',
        'Collision-run rows identify the original FRESH switch of the path active at the saved collision; they do not move B to a later Graph application.',
        '',table(['Run','Noise','FRESH','Depth pick','Oracle pick','Depth pick oracle clearance m'],[
            [r['run'],r['noise'],r['fresh_id'],r['depth_selected'],r['oracle_selected'],f(r['depth_selection_oracle_clearance_m'])]
            for r in summary['collision_counterfactuals']]),'',
        '## Map and observation limits','',
        table(['Noise','Points/observation median','Obstacle points median','Unknown grid median'],[
            [name,f(c['timing']['points']['median'],0),f(c['timing']['obstacle_points']['median'],0),f(c['timing']['unknown_fraction']['median'])]
            for name,c in conditions.items()]),'',
        'The 1cm static occupancy map keeps observed surfaces, does not fill solid interiors, and never treats unknown as occupied. Coverage is camera-height line of sight plus observed hits, not a 3D free-space certificate. Depth-only safety can therefore be falsely optimistic. The h/√2 bound covers bilinear interpolation of grid-site distance only, not sensing, occlusion, float16 or occupancy quantization errors. Polyline clearance also subtracts half the sample spacing.',
        '', 'Depth includes visible walls, without oracle half-plane constraints. Oracle exact obstacle/corridor geometry is used only by evaluation. Grid allocation matches the prior padded SDF bounds. Noise is the prescribed independent Gaussian σ=0.01·d² on axial depth, not a calibrated stereo noise model.',
        '', 'Capture availability uses original capture-completion monotonic time, never a future frame or a mixed-clock subtraction. Busy-skipped inference captures still contribute depth. Saved pose-to-USD differences below 1µm are checked and actual USD extrinsics are stored.',
        '', '[NVIDIA camera/annotator documentation](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/sensors/isaacsim_sensors_camera.html).',
        '', '![SDF comparison](../research/results/phase15a/sdf_compare.png)','',
        '![Clearance scatter](../research/results/phase15a/clearance_scatter.png)','',
        '## Pre-registered decision','',
        'Noisy condition, first matching rule only: dangerous >2% → DEPTH_NOT_READY; otherwise update p95 >50ms → TIMING_NOT_READY; otherwise conservative >20% → DEPTH_CONSERVATIVE; otherwise DEPTH_READY.',
        ''
    ]
    if summary['label']=='TIMING_NOT_READY':
        text += ['Accuracy passed; optimize implementation and remeasure timing only in a subsequent task. Component timing is reported above.','']
    text += ['No label establishes closed-loop safety or navigation success. Unknown geometry and odometry assumptions remain material limits.','',summary['label'],'']
    return '\n'.join(text)


def publish(destination, doc):
    # Exact report scope; never stage artifacts, old results or unrelated files.
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='research/phase0-infrastructure':raise RuntimeError('Unexpected publication branch')
    paths=[str(doc.relative_to(ROOT)),str(destination.relative_to(ROOT))]
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    subprocess.run(['git','add','-f','--',str((destination/'sdf_compare.png').relative_to(ROOT)),
                    str((destination/'clearance_scatter.png').relative_to(ROOT))],cwd=ROOT,check=True)
    staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
    if any(name!=paths[0] and not name.startswith(paths[1]+'/') for name in staged):
        raise RuntimeError('Unrelated staged changes: refusing mixed commit')
    subprocess.run(['git','-c','core.whitespace=cr-at-eol','diff','--cached','--check'],cwd=ROOT,check=True)
    if staged:
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m',
                        'Record Phase 15-A depth SDF offline evaluation'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin',branch],cwd=ROOT,check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root',type=Path,default=DEFAULT_ROOT)
    parser.add_argument('--depth-noise',choices=['both','none','gaussian'],default='both',
                        help='Noise is applied offline to saved noiseless float16 depth; default evaluates both')
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    if args.publish and args.depth_noise!='both':parser.error('Published Phase15-A report requires both noise conditions')
    complete=OUT/'complete.json'
    if complete.exists():
        old=json.loads(complete.read_text())
        for path,digest in old['output_hashes'].items():assert sha256_file(ROOT/path)==digest,f'Result modified: {path}'
        summary=json.loads((OUT/'summary.json').read_text())
        assert Path(summary['render_root']).resolve()==args.run_root.resolve()
    else:
        if DOC.exists():raise FileExistsError(f'Refusing overwrite: {DOC}')
        noise=['none','gaussian'] if args.depth_noise=='both' else [args.depth_noise]
        summary=evaluate(args.run_root,OUT,noise)
        with DOC.open('x') as f:f.write(document(summary))
        hashes={str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(OUT.iterdir()) if p.is_file()}
        hashes[str(DOC.relative_to(ROOT))]=sha256_file(DOC)
        write_json(complete,dict(output_hashes=hashes))
    if args.publish:publish(OUT,DOC)
    print(summary['label'],flush=True)


if __name__=='__main__':main()
