"""L2 pilot only: R2_PASS/R2_FAIL, frozen before the twelve main runs."""
import argparse, json, subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT, sha256_file
from nomad_phase17.report import table
from nomad_phase23.report import csv_write
from .online_config import protocol
from .storage import atomic_json

OUT=ROOT/'research/results/phase24r2'
DOC=ROOT/'docs/PHASE24R2_PILOT.md'


def decision(g,c):
    checks=dict(goal_within_one=g['success']>=c['success']-1,
                zero_collisions=g['collision']==0,
                passage_within_one=g['box_passage']>=c['box_passage']-1)
    return dict(label='R2_PASS' if all(checks.values()) else 'R2_FAIL',
                study='PILOT', **checks)


def generate(root, out=OUT, doc=DOC, figures=True):
    p=protocol();out.mkdir(parents=True,exist_ok=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(r['scene'],r['index'],r['method']) for r in p['main_order']}
    assert len(runs)==12 and {(r['scene'],r['index'],r['method']) for r in runs}==expected
    atomic_json(out/'runs.json',runs);summary=[]
    extra=('detour_max_abs_y_m','post_passage_5s_abs_y_m')
    for method in p['methods']:
        rr=[r for r in runs if r['method']==method];valid=[r for r in rr if r['technical_validation']=='PASS']
        med=lambda k:float(np.median([r[k] for r in valid if r.get(k) is not None])) if any(r.get(k) is not None for r in valid) else None
        summary.append(dict(method=method,n=4,valid=len(valid),technical_failure=4-len(valid),
            success=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),
            corridor=sum(r['corridor'] for r in valid),box_passage=sum(r['box_passage'] for r in valid),
            goal_time_median_s=med('goal_time_s'),passage_time_median_s=med('box_passage_from_spawn_s'),
            **{k:med(k) for k in ('minimum_clearance_m','detour_minimum_clearance_m','omega_saturation_fraction','stopped_fraction','compute_p95_s',*extra)}))
    verdict=decision(next(r for r in summary if r['method']=='G'),next(r for r in summary if r['method']=='C0'))
    verdict['technical_failures']=sum(r['technical_failure'] for r in summary)
    atomic_json(out/'decision.json',verdict);csv_write(out/'summary.csv',summary)
    keys=('scene','index','method','classification','success','collision','box_passage','box_passage_from_spawn_s','goal_time_s',*extra,'post_detour_closest_progress')
    paired=[{k:r.get(k) for k in keys} for r in runs];csv_write(out/'paired.csv',paired)
    keys=('index','method','mode_fraction','output_counts','output_fractions','compute_p50_s','compute_p95_s','job_compute_p95_s','recovery_count','rotation_priority_count','rotation_priority_time_s','theta_chord_inconsistent_count','certificate_rejection_count','certificate_alternative_count','path_became_unsafe_count','trigger_after_spawn_s')
    execution=[{k:r.get(k) for k in keys} for r in runs];csv_write(out/'execution.csv',execution)
    marker='\n## Online results\n';text=doc.read_text().split(marker)[0]+marker
    text+=f"\nPilot only; n=4 paired seeds. Prior Phase24/R results are preserved and not pooled. Protocol SHA256 `{sha256_file(Path(__file__).with_name('online_protocol.json'))}`. Exact simulator odometry. Seed95 smoke excluded.\n\n"
    text+=table([verdict])+'\n\n'+table(summary)+'\n\n### Paired results\n\n'+table(paired)+'\n\n### Frozen Phase24-R diagnostics\n\n'+table(execution)
    failures=[{k:r.get(k) for k in ('index','method','output','error')} for r in runs if r['technical_validation']!='PASS']
    text+='\n\nTechnical failures are counted as unsuccessful and preserved without retry: '+str(failures)+'\n'
    if figures:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import csv
        fig,axes=plt.subplots(1,4,figsize=(17,4),constrained_layout=True)
        for ax,index in zip(axes,p['indices']):
            for r in runs:
                if r['index']!=index or r['technical_validation']!='PASS':continue
                with (Path(r['output'])/'agent_trajectory.csv').open() as stream:data=list(csv.DictReader(stream))
                ax.plot([float(x['x_m']) for x in data],[float(x['y_m']) for x in data],label=r['method'])
            ax.set_title(f'L2 seed {index}');ax.set_aspect('equal');ax.legend();ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
        fig.savefig(out/'paths_L2.png',dpi=130);plt.close(fig)
        text+='\n![L2 paths](../research/results/phase24r2/paths_L2.png)\n'
    for f in out.glob('*.csv'):f.write_text(f.read_text())  # canonical LF
    doc.write_text(text+'\n');return verdict


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    print(json.dumps(generate(a.run_root.resolve())))
    if a.publish:
        paths=[str(DOC.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','-f','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase24-R2 endpoint return pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


if __name__=='__main__':main()
