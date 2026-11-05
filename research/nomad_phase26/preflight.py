"""Verify excluded smoke artifacts, freeze sources and prepare the main command."""
import json,shutil
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_phase17.report import table
from .config import protocol,runtime_config,METHODS,SCENES
from .campaign import jobs
from .storage import atomic_json,capacity

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase26'

def figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from nomad_phase16.geometry import rect
    from nomad_isaac.clearance import configured_obstacles
    from .scenes import place
    fig,axes=plt.subplots(1,5,figsize=(18,5),constrained_layout=True)
    for ax,scene in zip(axes,SCENES):
        c=runtime_config('C0',95,level=scene);xmin,xmax,ymin,ymax=rect(c)
        ax.add_patch(Rectangle((xmin,ymin),xmax-xmin,ymax-ymin,fill=False,ec='black',lw=2))
        for b in configured_obstacles(c):
            x,y=b['center_xy_m'];sx,sy,_=b['size_xyz_m'];ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,fc='.6'))
        if scene in ('H1','H2'):
            poses=[[3.3,1.2,1.5707963267948966]] if scene=='H1' else [[2.,0,0],[5.,0,0]]
            for i,pose in enumerate(poses):
                b=place(c,pose,i)['obstacle'];x,y=b['center_xy_m'];sx,sy,_=b['size_xyz_m'];ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,fc='purple',alpha=.55));ax.scatter(*pose[:2],marker='D',c='purple')
        elif scene=='L2':
            from nomad_phase21.config import place as old_place
            b=old_place(c,[2.,0,0])['obstacle'];x,y=b['center_xy_m'];sx,sy,_=b['size_xyz_m'];ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,fc='purple',alpha=.55))
        ax.scatter(*c['start_pose'][:2],marker='o',c='green',label='start');ax.scatter(*c['goal_pose'][:2],marker='*',c='red',label='goal')
        ax.set_title(scene+(' (held-out)' if scene in ('H1','H2') else ''));ax.set_aspect('equal');ax.set_xlim(xmin-.2,xmax+.2);ax.set_ylim(ymin-.2,ymax+.2);ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
    fig.suptitle('Green: start   Red star: goal   Gray: existing obstacles   Purple: sudden boxes / spawn fixtures',fontsize=11)
    fig.savefig(OUT/'scenes.png',dpi=150);plt.close(fig)

def main():
    p=protocol();assert p['status']=='DRAFT'
    root=ROOT.parent/'artifacts/isaac6/phase26_smoke_01'
    rows=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    assert len(rows)==15 and all(r['technical_validation']=='PASS' for r in rows)
    assert {(r['scene'],r['method']) for r in rows}=={(j['scene'],j['method']) for j in jobs(root,True)}
    geometry={}
    OUT.mkdir(parents=True,exist_ok=True)
    for scene in ('H1','H2'):
        folder=ROOT.parent/f'artifacts/isaac6/phase26_geometry_01/{scene}'
        result=json.loads((folder/'geometry_only.json').read_text());assert result['passed'];geometry[scene]=result
        destination=OUT/'geometry'/scene;destination.mkdir(parents=True,exist_ok=True)
        for f in folder.iterdir():
            if f.suffix=='.png' or f.name in ('geometry_only.json','geometry_check.json'):shutil.copyfile(f,destination/f.name)
    # Preserve and hash transitive runtime dependencies, not just the wrapper.
    folders=('nomad_phase0','nomad_phase8','nomad_phase12','nomad_phase15','nomad_phase15b','nomad_phase16','nomad_phase17','nomad_phase18','nomad_phase18d','nomad_phase19r','nomad_phase20','nomad_phase20b','nomad_phase20c','nomad_phase20d','nomad_phase20e','nomad_phase20f','nomad_phase21','nomad_phase24r','nomad_phase24r2','nomad_isaac')
    for folder in folders:
        for f in (ROOT/'research'/folder).glob('*'):
            if f.suffix in ('.py','.json'):p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    legacy=json.loads((ROOT/'research/nomad_phase21/protocol.json').read_text())
    for name in legacy['protected_sha256']:
        f=ROOT/name;p['frozen_sources'][name]=sha256_file(f)
    source={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))}
    main_root=ROOT.parent/'artifacts/isaac6/phase26_pilot_01';plan=jobs(main_root);disk=capacity(main_root,plan)
    assert not any(main_root.glob('main/**/agent_trajectory.csv')),'Main navigation must not have started in preparation'
    def wall(j):
        match=[r for r in rows if r['method']==j['method'] and r['scene']==j['scene']]
        if not match:match=[r for r in rows if r['method']==j['method']]
        return max(r['launcher_wall_s'] for r in match)
    estimate=(sum(wall(j) for j in plan)*1.15+300)/3600
    lengths=[validate_socket_path(socket_path_for_run(Path(s))) for j in plan for s in j['outputs']]
    p.update(status='FROZEN',source_sha256=source,pending_questions=[],
        implementation_definitions=dict(H1='exit y0.9, trigger y[1.2,1.3], fixed +y route axis, box cross center x3.6,1m footprint-to-front gap; original LC objects kept',
            exclusions='B0 reference failure does not exclude primary paired groups',astar='Literal user clauses: goal+2 BETTER first; otherwise goal>=B4-1 and collision<=B4 NONINFERIOR; else WORSE'),
        geometry_checks={s:str((OUT/'geometry'/s/'geometry_only.json').relative_to(ROOT)) for s in geometry},
        geometry_adjustments_used={'H1':0,'H2':0},smoke_passed=15,tests_passed=8,
        estimated_hours=estimate,estimated_retry_upper_hours=2*estimate,socket_max_bytes=max(lengths))
    atomic_json(HERE/'protocol.json',p)
    smoke=[{k:r.get(k) for k in ('scene','method','technical_validation','command_pose_error_m','wall_geometry_error_m','launcher_wall_s','attempt_count','output')} for r in rows]
    failed_attempts=[]
    for r in rows:
        for attempt in r.get('attempts',[]):
            if attempt['technical_validation']=='PASS':continue
            failure=Path(attempt['output'])/'FAILED.json'
            cause=json.loads(failure.read_text()).get('error') if failure.exists() else attempt.get('error')
            failed_attempts.append(dict(scene=r['scene'],method=r['method'],attempt=attempt['attempt'],cause=cause,preserved_output=attempt['output']))
    atomic_json(OUT/'smoke.json',smoke)
    atomic_json(OUT/'preflight.json',dict(passed=True,protocol_sha256=sha256_file(HERE/'protocol.json'),source_sha256=source,
        tests_passed=8,smoke=smoke,technical_failures_preserved=failed_attempts,geometry=geometry,main_navigation_started=0,planned=60,estimated_hours=estimate,
        disk={k:v for k,v in disk.items() if k!='details'},max_socket_bytes=max(lengths)))
    figures()
    text=f'''# Phase26 — preregistered pilot preflight

**Preparation only. Main seed201–202 runs have not started.** Source baseline: Phase24-R2 C0, frozen hashes in protocol.json. Protocol SHA256 `{sha256_file(HERE/'protocol.json')}`. All previous code/results/raw are preserved.

## Methods

| Method | Normal handoff | Blocked response |
|---|---|---|
| B0 NOMAD_RAW | sample0, common PP/SP/start alignment; no depth/filter | No fallback or RECOVER_ROTATE; reference only |
| B1 SAFE_TE | Phase18 handoff rules via Phase21; depth SAFE, K3 TE/expiry/KEEP, SP/alignment from latest selected chunk | Frozen fallback/RECOVER_ROTATE; no detour |
| B2 SAFE_RTC | Phase18 RTC-hard/DDPM and SAFE through Phase21; common PP/SP/start alignment | Frozen fallback/RECOVER_ROTATE; no detour |
| B3 SAFE_ROTATE | FRESHEST-SAFE/common executor | Frozen fallback/RECOVER_ROTATE; no R2/R3 |
| B4 ASTAR | Same as C0 | C0 R2 SLSQP unchanged; only R3 replaced by Phase21 A*, lambda4.0, smoothing0 |
| C0 | Phase24-R2 C0 unchanged | R2 SLSQP→R3 SLSQP seven starts; conservative map, continuous certificate, frozen24-R trigger/direction/handover/recovery |

All use RGB+the reused scene Topomap, D750, PP lookahead0.25, Phase18D SP, start alignment,9Hz control/72Hz integration/nominal4Hz observations,90s simulation cap. NoMaD metric scaling remains unchanged. B1/B2 are **Phase18 handoff rules + common PP/SP executor**. Depth V1/shadow/recency/persistent-component behavior is identical for B1–B4/C0; B0 has no depth annotator or map. Simulator odometry is exact. Oracle enters placement/render/evaluation only; planner inputs remain depth snapshots/pose/samples. R3's frozen implementation actually has20XY variables; the historical SE(2) wording does not authorize a model change. SaferPath is excluded.

## Scenes and held-out definitions

SLW and LC reuse Phase18 JSON/reference/Topomap hashes; L2 reuses the Phase24-R2 definition. All four USD wall inner faces must equal each scene's evaluation rectangle before navigation, including LC's asymmetric y bounds.

H1: LC corner exit is y=0.9, spawn at y∈[1.2,1.3]. The fixed route axis is+y. The box has world x/y/z size1.0/0.4/0.8m, cross-axis center x3.6, with a1.0m gap between the robot's forward footprint support and the near box face (the existing L2 placement convention). Initial depth fixture center is(3.6,2.49). Existing LC obstacles stay present. The wide gap is0.7m. **H1 is explicitly a u_ref limitation test**, not a tuned scene.

H2: x∈[2.0,2.1] spawns a0.4×1.0×0.8m box at y+0.3; after footprint passage of it, x∈[5.0,5.1] spawns the second at y−0.3. The same1m front clearance convention is used. Both boxes stay rendered and monitored; the second never replaces the first in collision evaluation. Scene passage requires both, with per-box times also retained. Geometry-only testing used neither policy nor inference. No position adjustment was needed.

![Scenes](../research/results/phase26/scenes.png)

## Registered pilot decisions and missing data

Six methods×five scenes×paired seeds201–202=60runs. Fixed seed-first scene/method order is stored in protocol.json (permutation seed20261105). One identical-seed retry is allowed only after technical failure; remaining runs continue. If a primary method fails again, that complete scene×seed primary group is excluded. B0 failures do not affect primary groups. Attempt data are preserved; no outcome-based retry or tuning.

Sudden pooled L2/H1/H2: C0_BETTER_vs_B1/B2/B3 iff goal successes≥comparator+2 and collisions≤comparator. Against ASTAR, the literal registered goal≥B4+2 clause gives BETTER first; otherwise goal≥B4−1 AND collision≤B4 gives NONINFERIOR; otherwise WORSE. Collisions are also reported separately; no extra collision condition is added to the written BETTER clause. Static SLW/LC: STATIC_OK iff C0goal≥B3−1 and C0collisions≤B3. PILOT_SUPPORTS requires all three better flags, ASTAR not WORSE and STATIC_OK; PILOT_AGAINST when B3better fails and ASTAR is WORSE; otherwise PILOT_MIXED, listing satisfied/missed criteria. The thresholds do not change after technical exclusions. Effective paired n and scene results are explicit. Exact sign p is descriptive only. B0 has no decision role.

Primary endpoint is goal entry. Secondary endpoints: box/wall geometric collisions separately, goal time, per-box and scene passage/time, minimum footprint clearance, omega saturation, actual stopped fraction, recovery count, detour triggers/application delay and solve p95. Margin-only corridor stops remain separately visible. Missing passage time is not imputed. After SUPPORTS/MIXED, the report adds only a draft seeds203–208 confirmation plan; no expansion runs are launched.

## Verification

8unit tests pass: H1/H2 placement/sequence, persistent two-box evaluation, wall refusal, exact C0-L2 configuration regression, B4's R2 passthrough, label/exclusion functions and a fake60-row report. The15requested seed95smokes are excluded and interpreted only technically. The table deliberately omits navigation outcomes.

'''+table(smoke)+f'''

Both held-out geometry checks passed with no adjustment. See the RGB/depth images below. Wall checks and command→72Hz pose checks passed in every smoke. The second H2 box is explicitly verified in the depth-only fixture and unit test; no performance assumption is made about whether a policy reaches its trigger in a smoke.

## Time, storage and operational safety

Estimated60-run time including15%allowance and5min report: **{estimate:.2f}hours**. A conservative all-runs-need-retry bound is **{2*estimate:.2f}hours**. This is measured launcher wall time, using same scene/method smoke when available and the slower same-method held-out smoke otherwise.

Estimated normal remaining data: **{disk['expected_remaining_bytes']/1e9:.2f}GB**; with20GBheadroom: **{disk['required_free_bytes']/1e9:.2f}GB**; available at freeze: **{disk['free_bytes']/1e9:.2f}GB**. Full RGB/depth is retained only for seed201 in each scene; seed202 retains trajectories/metrics/FRESH+visualization maps/planner inputs, using the7d823b7 archival policy. Capture, inference and live map behavior are unchanged. Disk is checked before every attempt, including retries; insufficient space stops before launch. Atomic state/backup and resume retain completed attempts. Short socket paths are prechecked for all120possible attempts; maximum {max(lengths)}bytes.

Main execution is user initiated, locked and resumable. Report generation uses /usr/bin/python3 with PYTHONPATH=research, then commits/pushes new results. No venv packages were installed. No method is run on a new seed in preflight.
'''
    text+='\n## Preserved preparation failures\n\n'+table(failed_attempts)+'\n\nThe new multi-box evaluation adapter initially omitted the protected driver’s `avoidance_success` summary field. Only that return schema was corrected, its regression assertion was added, and the same dev seed was retried once. No planner/controller/factor/threshold or scene position was changed in response to a navigation outcome. All failed attempt directories remain intact.\n'
    for scene in ('H1','H2'):
        for f in sorted((OUT/'geometry'/scene).glob('*.png')):text+=f'\n![{scene} {f.name}](../research/results/phase26/geometry/{scene}/{f.name})\n'
    (ROOT/'docs/PHASE26_PREFLIGHT.md').write_text(text)
    print(json.dumps(dict(status='FROZEN',smoke_passed=15,planned=60,main_started=0,estimated_hours=estimate,required_GB=disk['required_free_bytes']/1e9,free_GB=disk['free_bytes']/1e9)))
if __name__=='__main__':main()
