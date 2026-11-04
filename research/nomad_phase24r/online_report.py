"""Preregistered per-scene G/C0 pilot decisions; C1 is a reference row."""
import argparse,json,subprocess,csv
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase23.report import csv_write
from nomad_phase17.report import table
from nomad_phase23.run import commit
from .online_config import protocol

OUT=ROOT/'research/results/phase24r';DOC=ROOT/'docs/PHASE24R_PILOT.md'
def decision(g,c):
    enough_goal=g['success']>=c['success'];safe=g['collision']<=c['collision']
    clearance=g['min_clearance_median_m'] is not None and c['min_clearance_median_m'] is not None and g['min_clearance_median_m']>=c['min_clearance_median_m']+.03
    omega=g['omega_saturation_median'] is not None and c['omega_saturation_median'] is not None and g['omega_saturation_median']<=c['omega_saturation_median']*.5
    label='G_HELPS' if enough_goal and safe and (clearance or omega) else 'G_HURTS' if g['success']<=c['success']-2 or not safe else 'G_INCONCLUSIVE'
    return dict(scene=g['scene'],label='PILOT_'+label,goal_not_lower=enough_goal,collisions_not_higher=safe,clearance_gain_3cm=clearance,omega_halved=omega)

def generate(root,out=OUT,doc=DOC,figures=True):
    out.mkdir(parents=True,exist_ok=True);p=protocol();rows=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))];assert len(rows)==24
    (out/'runs.json').write_text(json.dumps(rows,indent=2)+'\n');summary=[]
    for scene in ('L2','SLW','ALL'):
        for method in p['methods']:
            rr=[r for r in rows if r['method']==method and (scene=='ALL' or r['scene']==scene)];valid=[r for r in rr if r['technical_validation']=='PASS']
            med=lambda k:float(np.median([r[k] for r in valid if r.get(k) is not None])) if any(r.get(k) is not None for r in valid) else None
            summary.append(dict(scene=scene,method=method,n=len(rr),valid=len(valid),success=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),corridor=sum(r['corridor'] for r in valid),stuck=sum(r['classification']=='STUCK' for r in valid),technical_failure=len(rr)-len(valid),
                goal_time_median_s=med('goal_time_s'),box_passage=sum(r['box_passage'] for r in valid),passage_time_median_s=med('box_passage_from_spawn_s'),min_clearance_median_m=med('minimum_clearance_m'),detour_min_clearance_median_m=med('detour_minimum_clearance_m'),
                omega_saturation_median=med('omega_saturation_fraction'),stopped_fraction_median=med('stopped_fraction'),recovery_count=sum(r.get('recovery_count',0) for r in valid),compute_p95_median_s=med('compute_p95_s')))
    decisions=[decision(next(r for r in summary if r['scene']==scene and r['method']=='G'),next(r for r in summary if r['scene']==scene and r['method']=='C0')) for scene in ('L2','SLW')]
    csv_write(out/'summary.csv',summary);(out/'decisions.json').write_text(json.dumps(decisions,indent=2)+'\n')
    paired=[{k:r.get(k) for k in ('scene','index','method','classification','success','box_passage','box_passage_from_spawn_s','goal_time_s','minimum_clearance_m','detour_minimum_clearance_m','omega_saturation_fraction','stopped_fraction','recovery_count','technical_validation')} for r in rows];csv_write(out/'paired.csv',paired)
    details=[{k:r.get(k) for k in ('scene','index','method','mode_fraction','output_counts','output_fractions','pipeline_output_counts','job_compute_p95_s','compute_p50_s','compute_p95_s','compute_definition','recovery_count','trigger_after_spawn_s','rotation_priority_count','rotation_priority_time_s','theta_chord_inconsistent_count','certificate_rejection_count','certificate_alternative_count','path_became_unsafe_count')} for r in rows];csv_write(out/'execution.csv',details)
    marker='\n## Online pilot results\n';text=doc.read_text().split(marker)[0]
    text+=marker+'\nPhase24-R pilot, four new paired seeds per scene; C1 is descriptive only. Exact simulator odometry is assumed. The six seed95 smoke runs are excluded. Phase24 SLW runs are retained as SCENE_BOUNDARY_NOT_PERCEIVABLE and are not pooled with this rerun.\n\n'
    text+=f"Online protocol SHA256 `{sha256_file(Path(__file__).with_name('online_protocol.json'))}`. G installs the graph at36integration ticks and retains the global9Hz controller phase; C0/C1retain Phase21executors and timing.\n\n"
    text+='### Registered decisions\n\n'+table(decisions)+'\n\n### Outcomes\n\n'+table(summary)+'\n\n### Paired inputs\n\n'+table(paired)+'\n\n### Mode/output/timing\n\n'+table(details)+'\n\n'
    text+='Trigger/certificate/rotation metrics are per run in execution.csv: trigger time after box spawn, chord-priority rotations and duration, theta–chord inconsistency, certificate rejections/alternative use, and PATH_BECAME_UNSAFE count.\n\n'
    failed=[{k:r.get(k) for k in ('scene','index','method','output','error')} for r in rows if r['technical_validation']!='PASS'];text+='Technical failures (preserved; no automatic retry): '+str(failed)+'\n\n'
    recovery=root/'recovery/disk_full_20261104/recovery.json'
    if recovery.exists():
        incident=json.loads(recovery.read_text());(out/'disk_recovery.json').write_text(json.dumps(incident,indent=2)+'\n')
        text+='Disk incident: four completed runs were preserved byte-for-byte; the interrupted SLWseed131C1attempt is DISK_FULL TECHNICAL_FAILURE and was explicitly authorized for one same-seed retry. SLWseed131Ghad no requests/trajectory and was restarted after preserving its startup attempt. Archived attempts are excluded from the24main rows; no outcome-based retry was added.\n\n'
        text+=table([{k:r[k] for k in ('key','reason','classification','preserved_attempt','max_additional_attempts')} for r in incident['retries']])+'\n\n'
        text+='After the incident, full raw RGB/depth is retained for seed131in each scene. Other seeds retain live capture/inference/map updates unchanged, but archive only FRESH/1Hz/final maps, all planner snapshots, trajectories and metrics. Runtime latency includes the reduced archival load without compensation. Method factors, weights, seeds and decision criteria remain the frozen protocol.\n\n'
    if figures:
        for file in plots(rows,out):text+=f'![{file}](../research/results/phase24r/{file})\n\n'
    doc.write_text(text);return decisions

def plots(rows,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from nomad_phase22.drive_geometry import corners
    from nomad_isaac.clearance import configured_obstacles
    files=[];colors=dict(G='seagreen',C0='darkorange',C1='steelblue')
    for scene in ('L2','SLW'):
        fig,axes=plt.subplots(1,4,figsize=(18,5),constrained_layout=True)
        for ax,index in zip(axes,protocol()['indices']):
            rr=[r for r in rows if r['scene']==scene and r['index']==index]
            for r in rr:
                run=Path(r['output'])
                if r['technical_validation']!='PASS':ax.plot([],[],color=colors[r['method']],label=r['method']+' TECHNICAL_FAILURE');continue
                data=list(csv.DictReader((run/'agent_trajectory.csv').open()));ax.plot([float(x['x_m']) for x in data],[float(x['y_m']) for x in data],color=colors[r['method']],label=r['method'])
                summary=json.loads((run/'summary.json').read_text());boxes=configured_obstacles(summary['scenario']);spawn=(summary.get('dynamic_obstacle') or {}).get('spawn')
                if spawn:boxes=boxes+[spawn['obstacle']]
                for box in boxes:ax.add_patch(Polygon(corners(box),color='.4',alpha=.12))
            ax.set_aspect('equal');ax.set_title(f'{scene} seed{index}');ax.legend(fontsize=8);ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
        file=f'paths_{scene}.png';fig.savefig(out/file,dpi=130);plt.close(fig);files.append(file)
    return files

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',required=True,type=Path);ap.add_argument('--publish',action='store_true');a=ap.parse_args();generate(a.run_root.resolve())
    commit('Report Phase24 decision graph online pilot',[OUT,DOC])
    subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in OUT.glob('*.png')]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Add Phase24 online figures'],cwd=ROOT,check=True)
    if a.publish:subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
