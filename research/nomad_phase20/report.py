"""Phase20 gate report. Main campaign reporting is gated on offline READY."""
import json
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean


def preflight_report(out,verdict,six,sha,protocol,replace=False):
    text='# Phase 20 — SO-only repair recovery pilot\n\n'
    text+=f"**파일럿 / 사후 수정 후 재점검 / Offline gate: {verdict['label']}**. Execution SHA: `{sha}`. Protocol hash: `{sha256_file(out/'protocol.json')}`.\n\n"
    text+='The revised main matrix is SO only, seed indices74–79, M1 ROTATE and M2 REPAIR, 12 serial trials. No SLW/LC/CL navigation or noninferiority judgment is planned in this phase. None of these pilot trials has been executed by this offline preflight.\n\n'
    text+='## 0-a. R2 definition\n\n'
    text+='R2 inherits Phase19R initialization, 14 XY variables, fixed B, priors/smoothness/heading objective, curvature≤8, length preservation, trust region, analytic Jacobian, SLSQP(maxiter100, ftol1e−8) and single-attempt solve. Only the first0.30m clearance threshold is relaxed, with the user-requested zero lower bound. B with conservative depth clearance<0 is rejected before any solve. Oracle geometry never enters optimization, selection or SP/alignment control.\n\n'
    text+='Let c_B = saved depth SDF(B) − h/√2 (the same conservative footprint clearance convention as Phase16D/19R). At each current optimized path sample q, cumulative arclength s(q)≤0.30m uses min(0.025,max(0,c_B−0.005)); later samples use0.025m. The original per-segment nine-point bound d(q)−h/√2−L/16 is unchanged. Zone membership is recomputed from the optimized path, not the initial path. The piecewise-constant threshold has an analytic zero derivative away from s=0.30m; the zone boundary is explicitly nonsmooth. No smoothing, tuning or restart is introduced.\n\n'
    text+='Exact depth certificate splits the continuous path at0.30m and reuses exact distance to occupied cell centers minus robot radius on both subpaths. The cut is included in both certificates: a continuous far-side path must satisfy0.025m in the limit at the cut. Acceptance still requires solver success, maximum constraint violation≤1e−7 and both exact certificates.\n\n'
    text+='Selected repair is the accepted sample with minimum mean edit (lower-index tie); all8 are considered once, with negative-depth-B rejection and unchanged Phase19R short/degenerate exclusion. Timing p95 uses eligible per-sample attempts including certificate. Eight-sample serial time and counts exceeding the planned0.5s online deadline are separately reported.\n\n'
    causes=[dict(cause=k,**v) for k,v in verdict['cause_success'].items()]
    text+=table(causes)+'\n\n```json\n'+json.dumps(clean(verdict),indent=2)+'\n```\n\n'
    text+='READY requires zero **selected** repaired-path oracle penetrations, ≤7% oracle overlap among selected 1.5s SP+departure-alignment rollouts, and per-sample solve p95≤0.20s. All accepted sample-path penetrations are reported separately, including unselected paths. There is no minimum repair-success gate. No-selected-repair is not evidence of readiness.\n\n'
    text+='SP is unchanged. The revised departure trigger uses heading error≥45° regardless of speed, or≥20° when actual v<0.01m/s. Braking remains bounded by0.5m/s² before zero-v rotation at≤0.4rad/s. Trigger P stays disabled; actual initial v and heading are retained. The1.5s clock includes braking/rotation. The rollout is endpoint/horizon bounded and oracle-passive, so overlap is monitored but never changes control.\n\n'
    from nomad_phase19s.evaluate import csv_rows
    penetrating=[e for e in csv_rows(out/'events.csv') if e['repair_success'] and e['selected_oracle_clearance_m']<0]
    if penetrating:
        text+='### Selected penetrating repairs\n\n'+table(penetrating,['event_id','run','cause','B_oracle_clearance_m','B_depth_clearance_m','selected_near_threshold_m','selected_depth_clearance_m','selected_oracle_clearance_m'])+'\n\n'
        text+='The revised depth certificate forbids negative clearance. Any remaining oracle penetration is recorded independently and fails READY; no oracle geometry is added to the repair input.\n\n'
    text+='## 0-b. Six published Phase19S 1.5s collisions\n\n'+table(six)+'\n\n'
    text+='These six cases were selected from the previously published D3 SRG prefix-overlap flags before any R2 outcome. The original six-row diagnosis remains preserved; these same fixed repaired paths are evaluated with the newly authorized alignment trigger. Unknown fractions are descriptions of the fixed repaired path, not evidence that unknown space caused the collision. The one-line reasons describe changed alignment and remaining overlap; no further setting is changed from this recheck.\n\n'
    text+=f"Revised alignment fired in {sum(r['departure_alignment'] for r in six)}/{len(six)} of the six previously colliding paths; {sum(r['new_overlap'] for r in six)} still overlap within1.5s. Braking and rotation time are separate columns. Nonpenetrating path geometry is not a PP execution certificate.\n\n"
    text+='## Validation and execution status\n\n'
    text+='Seven unit tests passed (including nonnegative threshold/negative-B rejection and moving-start bounded braking): R2 constraint/objective analytic Jacobians versus finite differences (≤1e−5 away from the hard zone boundary), exact split certificate, SP replacement/straight-speed/pre-turn braking, trigger S conditions without pivot, and equality to protected S-only behavior. Original code/raw/results remain unchanged. The frozen candidate protocol and deterministic12-job order are recorded below.\n\n'
    if verdict['label']=='NOT_READY':
        text+='**Stopped at the mandatory offline gate.** Online repair-thread integration, SO smoke/technical gate, main batch and main result judgments were not executed. No campaign launch command is provided. Constants and thresholds were not changed to pass the gate. The main execution/report infrastructure is not claimed complete.\n\n'
    else:text+='Offline READY permits further online integration and the single SO M2 smoke. READY alone is not a claim that the campaign is prepared or that driving is safe.\n\n'
    text+='## Limits\n\nSection0 is post-hoc analysis of Phase18 saved events. A fixed path rollout has no next FRESH, changing depth map or NoMaD response. Zero path penetration and short-horizon safety do not establish closed-loop driving safety. Simulation pose is assumed exact; oracle is restricted to evaluation.\n\n'
    text+='## Frozen SO pilot and offline protocol\n\n```json\n'+json.dumps(protocol,indent=2,ensure_ascii=False)+'\n```\n'
    with (ROOT/'docs/PHASE20_REPAIR_DRIVE_RECHECK.md').open('w' if replace else 'x') as f:f.write(text)


def main_groups(records):
    import numpy as np
    from .config import METHODS
    result=[]
    for method in METHODS:
        rr=[r for r in records if r['method']==method];valid=[r for r in rr if r.get('technical_validation')=='PASS']
        def mean(k):
            xs=[r[k] for r in valid if r.get(k) is not None];return float(np.mean(xs)) if xs else None
        result.append(dict(method=method,planned=6,valid=len(valid),success=sum(r.get('success',False) for r in valid),
            collision=sum(r.get('collision',False) for r in valid),corridor=sum(r.get('corridor',False) for r in valid),
            stuck=sum(r.get('stuck',False) for r in valid),technical=sum(r.get('technical_validation')!='PASS' for r in rr),
            safety_failure=sum(r.get('safety_failure',False) for r in valid),goal_time_s=mean('goal_time_s'),stopped_fraction=mean('stopped_fraction'),
            box_passage_time_s=mean('box_passage_time_s'),passed_box=sum(r.get('passed_box',False) for r in valid),
            minimum_clearance_m=min((r['minimum_clearance_m'] for r in valid if r.get('minimum_clearance_m') is not None),default=None),
            all_unsafe=sum(r.get('all_unsafe',0) for r in valid),recovery_count=sum(r.get('recovery_count',0) for r in valid),
            repair_attempts=sum(r.get('repair_attempts',0) for r in valid),repair_accepted=sum(r.get('repair_accepted',0) for r in valid),
            repair_timeout=sum(r.get('repair_timeout',0) for r in valid),alignment_count=sum(r.get('alignment_count',0) for r in valid),
            alignment_braking_s=mean('alignment_braking_s'),alignment_rotation_s=mean('alignment_rotation_s')))
    return result


def main_decision(groups):
    a,b=groups
    if a['valid']!=6 or b['valid']!=6:return dict(label='PILOT_INCONCLUSIVE',reason='Missing/technical/invalid evidence; formula not interpreted as a valid six-pair comparison')
    if b['success']>=a['success']+2 and b['safety_failure']<=a['safety_failure']:label='REPAIR_BETTER_SO'
    elif b['success']<=a['success']-2 or b['safety_failure']>=a['safety_failure']+2:label='REPAIR_WORSE_SO'
    else:label='REPAIR_EQUAL_SO'
    return dict(label=label,scope='파일럿',success_M1=a['success'],success_M2=b['success'],safety_M1=a['safety_failure'],safety_M2=b['safety_failure'])


def main_pairs(records):
    import numpy as np
    rows=[];lookup={(r['index'],r['method']):r for r in records if r.get('technical_validation')=='PASS'}
    for metric in ('stopped_fraction','box_passage_time_s'):
        data=[]
        for i in range(74,80):
            a,b=lookup.get((i,'M1_ROTATE')),lookup.get((i,'M2_REPAIR'))
            if a and b and a.get(metric) is not None and b.get(metric) is not None:data.append((i,b[metric]-a[metric]))
        diff=np.array([x[1] for x in data]);ci=None
        if len(diff):
            draw=np.random.default_rng(20261031).integers(0,len(diff),(20000,len(diff)))
            ci=np.quantile(diff[draw].mean(axis=1),[.025,.975]).tolist()
        rows.append(dict(metric=metric,n=len(data),mean_difference=float(diff.mean()) if len(diff) else None,ci95=ci,
            paired_indices=[x[0] for x in data],interpretation='descriptive only; paired seed resampling, one scene; missing times not imputed'))
    return rows


def main_figures(records,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import numpy as np
    from pathlib import Path
    from nomad_phase0.chunk_report import trace
    from .metrics import rows
    colors={'M1_ROTATE':'tab:blue','M2_REPAIR':'tab:green'}
    def draw(ax,r,extra=False):
        path=Path(r['output'])
        if not (path/'agent_trajectory.csv').exists():return
        _,p=trace(path);ax.plot(p[:,0],p[:,1],color=colors[r['method']],alpha=.7,label=f"{r['method']} {r['index']}")
        if (path/'dynamic/spawn.json').exists():
            box=json.loads((path/'dynamic/spawn.json').read_text())['obstacle'];x,y=box['center_xy_m'];w,h=box['size_xyz_m'][:2]
            ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,alpha=.15,color=colors[r['method']]))
        if extra:
            for e in rows(path/'repair.jsonl'):
                if e['event']=='PATH_APPLIED' and e['kind']=='REPAIR':
                    q=np.array(e['path_world']);ax.plot(q[:,0],q[:,1],color='purple',lw=.8)
            for e in rows(path/'recovery.jsonl'):
                if e['event']=='START':ax.scatter(*e['pose'][:2],facecolors='none',edgecolors='red',s=35)
        ax.axhline(1.5,c='.5');ax.axhline(-1.5,c='.5');ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
    for name,selected,extra in [('paths_SO',records,False),('so_examples',[r for r in records if r['index']==74],True)]:
        fig,ax=plt.subplots(figsize=(11,4))
        for r in selected:draw(ax,r,extra)
        if selected:ax.legend(fontsize=6,ncol=3)
        ax.set_title('SO pilot; depth-only control, oracle boxes shown for evaluation');fig.tight_layout();fig.savefig(out/f'{name}.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,4))
    for i,m in enumerate(colors):
        values=[r['stopped_fraction'] for r in records if r['method']==m and r.get('technical_validation')=='PASS']
        if values:ax.scatter(np.repeat(i,len(values)),values,color=colors[m]);ax.plot([i-.15,i+.15],[np.median(values)]*2,color=colors[m])
    ax.set_xticks([0,1],list(colors));ax.set_ylabel('STOP_WAIT + recovery + repair-wait fraction');fig.tight_layout();fig.savefig(out/'stop_fraction.png',dpi=140);plt.close(fig)
    for r in records:
        if r.get('success'):continue
        fig,ax=plt.subplots(figsize=(9,4));draw(ax,r,True);ax.set_title(f"{r['method']} {r['index']}: {r.get('classification')}");fig.tight_layout();fig.savefig(out/f"failure_SO_{r['method']}_{r['index']}.png",dpi=140);plt.close(fig)


def render_main(records,root,out,doc,figures=True):
    from .config import protocol
    from nomad_phase19r.evaluate import csv_write
    p=protocol();groups=main_groups(records);pairs=main_pairs(records);decision=main_decision(groups)
    out.mkdir(parents=True,exist_ok=True)
    for name,value in [('runs',records),('decisions',decision)]:
        with (out/f'{name}.json').open('w') as f:json.dump(clean(value),f,indent=2)
    for name,values in [('summary',groups),('paired',pairs)]:
        file=out/f'{name}.csv'
        if file.exists():file.unlink()
        csv_write(file,values)
    if figures:main_figures(records,out)
    offline=json.loads((ROOT/'research/results/phase20_preflight_02/readiness.json').read_text())
    text='# Phase 20 — SO repair recovery 파일럿\n\n'
    text+=f"Protocol SHA256: `{sha256_file(ROOT/'research/nomad_phase20/protocol.json')}`. Offline assessment: **사후 수정 후 재점검 / {offline['label']}**.\n\n"
    text+='SP and revised stop–align–go are shared by M1/M2. R2 repair is used only at ALL_UNSAFE; it waits at STOP_WAIT, uses no oracle, and falls back after rejection or0.5s timeout. Main runs are seed74–79, SO only. This is a 파일럿, not a confirmatory experiment.\n\n'
    text+='## Offline gate\n\n```json\n'+json.dumps(offline,indent=2)+'\n```\n\n[Original NOT_READY](../research/results/phase20_preflight/readiness.json) and [recheck diagnosis](PHASE20_REPAIR_DRIVE_RECHECK.md) remain available.\n\n'
    text+='## Method summary\n\n'+table(groups)+'\n\n## Seed × method\n\n'
    text+=table(records,['index','method','classification','success','collision','corridor','stuck','goal_time_s','stopped_fraction','box_passage_time_s','minimum_clearance_m','all_unsafe','repair_attempts','repair_accepted','repair_timeout','recovery_count','alignment_count','alignment_braking_s','alignment_rotation_s','first_visible_s','first_depth_observed_s','first_depth_map_observed_s','pass_side'])+'\n\n'
    text+='## Pilot decision\n\n```json\n'+json.dumps(decision,indent=2)+'\n```\n\n## Paired descriptive differences (M2−M1)\n\n'+table(pairs)+'\n\n'
    text+='Box passage is first tick with the entire footprint beyond box rear (+X); passage time starts at physical spawn. Missing passage times remain missing. Stopped fraction is the union of STOP_WAIT, repair wait, recovery rotation and WAIT_FRESH; departure-alignment braking/rotation and actual near-zero-speed fraction are separately recorded. A conservative contact stop without a geometric witness is not relabelled a collision. All technical failures are retained; missing valid trials prevent an interpreted six-pair verdict.\n\n'
    text+='## Technical failures\n\n'+table([r for r in records if r.get('technical_validation')!='PASS'],['index','method','output','error'])+'\n\n'
    for name in ('paths_SO','so_examples','stop_fraction'):text+=f'![{name}](../research/results/phase20/{name}.png)\n\n'
    text+='NoMaD uses RGB only. Both methods use the same noisy V1 depth map and exact simulator odometry (no odometry error); oracle boxes/walls are used only for rendering, placement and evaluation. The physical box can differ across methods because placement depends on actual pose. Paired seeds therefore do not imply identical RGB, trajectories or box positions. Depth unknown remains free; neither short offline readiness nor a successful pilot establishes general safety.\n'
    doc.write_text(text)
    return decision


def main():
    import argparse,subprocess
    from pathlib import Path
    from .config import protocol
    from .campaign import read
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    root=a.run_root.resolve();plan=read(root/'plan.json');assert len(plan['jobs'])==12
    records=[read(root/'metrics'/f"main_{j['key']}.json") for j in plan['jobs']];assert all(records)
    out=ROOT/'research/results/phase20';doc=ROOT/'docs/PHASE20_REPAIR_DRIVE.md'
    decision=render_main(records,root,out,doc)
    if a.publish:
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
        subprocess.run(['git','add','--',str(doc.relative_to(ROOT)),str(out.relative_to(ROOT))],cwd=ROOT,check=True)
        subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in out.glob('*.png')]],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase20 SO repair recovery pilot'],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    print(json.dumps(decision))


if __name__=='__main__':main()
