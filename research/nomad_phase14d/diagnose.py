"""One offline diagnostic campaign. --publish also commits/pushes only its source/results.

A switch row is a FRESH application plus its eventual GF result. Collision rows:
last three FRESH switches before contact, union the originating FRESH of the
path actually active at contact. Replacements are separate execution intervals.
"""
import argparse
import json
import subprocess
import time
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT, integrate_se2, local_to_world, sha256_file, write_json
from nomad_isaac.async_report import rows
from nomad_isaac.clearance import configured_obstacles, obstacle_bounds, single_obstacle_config, swept_clearance
from nomad_isaac.handoff_audit import path_safety
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase0.chunk_report import trace
from nomad_phase0.graph_v4 import GraphV4, SignedDistanceField
from nomad_phase12.methods import freshest
from nomad_phase4.report import write_csv
from nomad_phase8.report import markdown_table

HERE = ROOT/'research/nomad_phase14d'
OUT = ROOT/'research/results/phase14d'
DOC = ROOT/'docs/PHASE14D_COLLISION_DIAGNOSIS.md'
GF = 'FRESHEST+GRAPH-GF'
TARGETS = {12: (26,33), 13: (39,45)}
THRESHOLD = .025
PROTECTED = {
    'research/nomad_phase0/graph_v4.py': 'e7b7a9b784189644564df24b7c0d02af6e1497f9ef11c63616f597634aa1c445',
    'research/nomad_phase0/graph_v4_protocol.json': '4def6d67a1b3398b4316cc832b214935e59ba2b323004c235fed2771e2d4576f',
    'research/nomad_isaac/clearance.py': '70213b966898efb17e070ead2c24a77b0b58478c1d6b228045157fe91dba048c',
}
RULES = dict(collision_switches='last 3 actual FRESH switches union active path origin; deduplicate by FRESH ID',
    raw='nearest B projection + original remaining polyline; no B-to-projection connector',
    corrected='entire actually ACCEPTED GF path, as requested (not suffix)',
    execution='corrected path: actual GF application to next path application; otherwise original FRESH interval',
    path_vs_footprint='executed minimum minus active polyline minimum; negative means actual motion came closer',
    thresholds=dict(safety_m=.025,graph_drop_m=-.02),
    counterfactual='one protected GraphV4 initialization/solve per collision switch; original sample, dispatch B, previous command/prior unchanged; full oracle SDF/corridor, no online latency gate or rollout',
    cause_precedence=['SELECTION','GRAPH_SHIFT','EXECUTION','OTHER'],
    conclusion_precedence=['ADD_CONSTRAINT','FIX_SELECTION','FIX_EXECUTION','MIXED'])


def sources():
    selected = []
    manifests = {}
    for phase, indices in TARGETS.items():
        path = ROOT/f'research/results/phase{phase}/runs.json'
        hs = ROOT/f'research/results/phase{phase}/input_hashes.json'
        manifests[str(path)] = sha256_file(path)
        manifests[str(hs)] = sha256_file(hs)
        hashes = json.loads(hs.read_text())
        records = [r for r in json.loads(path.read_text()) if r['method']==GF]
        assert len([r for r in records if r['index'] in indices]) == 2
        for r in records:
            collision = r['index'] in indices
            if not collision and not r.get('success'):
                continue
            assert r['technical_validation']=='PASS'
            if collision:
                assert r['classification']=='SAFETY_FAILURE' and r['termination_reason']=='geometric_collision'
            selected.append(dict(phase=phase, collision=collision, record=r, hashes=hashes[r['key']]))
    assert sum(x['collision'] for x in selected)==4 and sum(not x['collision'] for x in selected)==15
    return selected,manifests


def suffix(xy,b):
    """Existing nearest projection; duplicate endpoint only for point-distance use."""
    p=XYPath(xy);s,_=p.project(np.asarray(b)[:2])
    points=np.vstack([p.at(s),p.points[p.s>s]])
    if len(points)==1:points=np.repeat(points,2,axis=0)
    return points


def safety(xy,config):
    return path_safety(np.asarray(xy),config)


def replay_clearance(run):
    """Phase6's swept-arc primitives, applied to saved actual 72Hz commands."""
    run=Path(run);c=json.loads((run/'scenario.json').read_text());rec,poses=trace(run)
    logged=rows(run/'clearance.jsonl');assert len(logged)==len(rec)
    gaps=[];pose_error=0.;clearance_error=0.;per_box={}
    for box in configured_obstacles(c):
        lo,hi=obstacle_bounds(single_obstacle_config(c,box))
        values=[]
        for tick in range(len(rec)):
            v,w=(float(rec[tick][k]) for k in ('v_m_s','w_rad_s'))
            dt=1/72 if tick else 0.
            start=poses[tick-1] if tick else poses[0]
            if tick:pose_error=max(pose_error,float(np.max(abs(integrate_se2(start,v,w,dt)-poses[tick]))))
            g=swept_clearance(start,v,w,dt,lo,hi,c['agent_radius_m'])
            values.append(g['lower_m'])
            clearance_error=max(clearance_error,abs(g['lower_m']-logged[tick]['obstacles'][box['id']]['lower_m']))
        per_box[box['id']]=float(min(values));gaps.append(values)
    assert pose_error<1e-12 and clearance_error<1e-6
    return dict(minimum_m=min(per_box.values()),per_box=per_box,interval_minima=np.min(gaps,axis=0),
                max_pose_error=pose_error,max_clearance_error=clearance_error)


def load_run(source, input_hashes):
    r=source['record'];run=Path(r['output'])
    data=dict(source=source,run=run,config=json.loads((run/'scenario.json').read_text()),
        summary=json.loads((run/'summary.json').read_text()),events=rows(run/'events.jsonl'),
        applications=rows(run/'phase6_applications.jsonl'),graph=rows(run/'stage2_graph.jsonl'),
        controls=rows(run/'controller.jsonl'))
    data['records'],data['poses']=trace(run)
    data['jobs']={g['id']:g for g in data['graph'] if g['event']=='SUBMIT'}
    data['results']={g['id']:g for g in data['graph'] if g['event']=='RESULT'}
    assert len(data['jobs'])==len(data['events'])
    for name in ('scenario.json','summary.json','events.jsonl','phase6_applications.jsonl','stage2_graph.jsonl',
                 'controller.jsonl','agent_trajectory.csv','clearance.jsonl','provenance.json'):
        h=sha256_file(run/name);assert h==source['hashes'][name],name
        input_hashes[str(run/name)]=h
    prov=json.loads((run/'provenance.json').read_text())
    assert prov['git_sha']==r['execution_git_sha']
    data['active_app']=data['applications'][-1]
    last_control=data['controls'][-1]
    assert last_control['waypoint_id']==data['active_app']['id']
    assert bool(last_control['stage2']['corrected_path_active'])==(data['active_app']['kind']=='GRAPH-GF')
    if source['collision']:
        assert data['summary']['termination_reason']=='geometric_collision'
        data['replay']=replay_clearance(run)
        assert abs(data['replay']['minimum_m']-r['minimum_obstacle_clearance_m'])<1e-6
    return data


def interval(data,app):
    start=app['tick'];apps=data['applications'];pos=apps.index(app)
    end=apps[pos+1]['tick'] if pos+1<len(apps) else len(data['poses'])-1
    if end>start:
        gap=float(np.min(data['replay']['interval_minima'][start+1:end+1]))
    else:
        gap=safety(np.repeat(data['poses'][start,None,:2],2,axis=0),data['config'])['obstacle_clearance_m']
    return dict(start_tick=start,end_tick=end,clearance_m=gap)


def counterfactual(job,config,field,protocol):
    result=dict(disposition='INITIALIZATION_REJECTED',accepted=False,solve_calls=0,
                corrected_clearance_m=None,world_xy=None)
    start=time.perf_counter()
    try:
        graph=GraphV4(job['world_xy'],job['boundary'],job['previous_command'],config,protocol,field,job['previous_xy'])
        result['solve_calls']=1
        poses,solver=graph.solve()  # Exactly one call, never restart/tune.
        accepted=bool(solver['feasible'])
        disposition='ACCEPTED' if accepted else 'NONCONVERGED' if not solver['success'] else 'CONSTRAINT_FAILURE' if not solver['constraints_satisfied'] else 'CERTIFICATE_FAILURE'
        result.update(disposition=disposition,accepted=accepted,solver=solver,world_xy=poses[:,:2].tolist())
        if accepted:result['corrected_clearance_m']=safety(poses[:,:2],config)['obstacle_clearance_m']
    except Exception as exc:
        result.update(error=repr(exc),disposition='SOLVE_ERROR' if result['solve_calls'] else 'INITIALIZATION_REJECTED')
    result['wall_s']=time.perf_counter()-start
    result['SDF_WOULD_FIX']='YES' if result['accepted'] and result['corrected_clearance_m']>=THRESHOLD else 'NO' if result['accepted'] else 'NO_SOLUTION'
    return result


def switch_row(data,event,hashes):
    source=data['source'];r=source['record'];identifier=event['id'];b=np.array(event['agent_pose_at_switch'])
    tick=round(event['application_sim_s']*72);np.testing.assert_allclose(b,data['poses'][tick],atol=1e-12,rtol=0)
    fname=f'model/derived/{identifier:04d}.npz';path=data['run']/fname
    h=sha256_file(path);assert h==source['hashes'][fname];hashes[str(path)]=h
    with np.load(path) as d:metric=d['metric'].copy()
    np.testing.assert_array_equal(metric,event['overnight_metric_samples'])
    worlds=np.array([local_to_world(x,np.asarray(event['observation_pose'])) for x in metric])
    xy,detail=freshest(worlds,b);selected=detail['selected_sample']
    assert selected==event['phase12']['detail']['selected_sample']
    np.testing.assert_allclose(xy,event['phase12']['applied_initial_world_xy'],atol=1e-12,rtol=0)
    job=data['jobs'][identifier];np.testing.assert_allclose(xy,job['world_xy'],atol=1e-12,rtol=0)
    np.testing.assert_array_equal(job['boundary'],b)
    assert job['switch_sim_s']==event['application_sim_s']
    previous=data['controls'][tick//8-1] if tick else None
    if previous:np.testing.assert_allclose(job['previous_command'],[previous['commanded_v_m_s'],event['plant_actual_w_at_controller_rad_s']],atol=1e-12,rtol=0)
    earlier=[g for g in data['graph'] if g['event']=='RESULT' and g['disposition']=='ACCEPTED' and g['applied_tick']<tick]
    assert job['previous_xy']==(earlier[-1]['applied_world_xy'] if earlier else None)
    raw_suffix=suffix(xy,b);raw=safety(raw_suffix,data['config'])
    result=data['results'].get(identifier);accepted=bool(result and result['disposition']=='ACCEPTED')
    corrected=np.asarray(result['applied_world_xy']) if accepted else None
    corrected_safety=safety(corrected,data['config']) if accepted else None
    app=next(a for a in data['applications'] if a['id']==identifier and a['kind']=='FRESHEST')
    graph_app=next((a for a in data['applications'] if a['id']==identifier and a['kind']=='GRAPH-GF'),None)
    assert (graph_app is not None)==accepted
    if graph_app:
        assert graph_app['tick']==result['applied_tick']
        np.testing.assert_allclose(graph_app['world_xy'],corrected,atol=1e-12,rtol=0)
    row=dict(phase=source['phase'],index=r['index'],key=r['key'],cohort='collision_last3' if source['collision'] else 'success_all',
        id=identifier,job_id=job['job_id'],observation_time_s=event['observation_sim_s'],switch_time_s=event['application_sim_s'],
        observation_pose=event['observation_pose'],B=b.tolist(),previous_vw=job['previous_command'],selected_sample=selected,
        disposition=result['disposition'] if result else 'TERMINAL_UNAPPLIED',accepted=accepted,
        graph_applied_tick=result['applied_tick'] if accepted else None,
        raw_selected_clearance_m=raw['obstacle_clearance_m'],raw_suffix_corridor_clearance_m=raw['corridor_clearance_m'],
        corrected_clearance_m=corrected_safety['obstacle_clearance_m'] if accepted else None,
        corrected_corridor_clearance_m=corrected_safety['corridor_clearance_m'] if accepted else None,
        delta_m=corrected_safety['obstacle_clearance_m']-raw['obstacle_clearance_m'] if accepted else None,
        active_at_collision=False)
    detail=dict(world_samples=worlds.tolist(),raw_world=xy.tolist(),raw_suffix=raw_suffix.tolist(),
                corrected_world=corrected.tolist() if accepted else None,job=job,raw_app=app,graph_app=graph_app)
    if source['collision']:
        all_gaps=[safety(suffix(x,b),data['config'])['obstacle_clearance_m'] for x in worlds]
        raw_interval=interval(data,app);active=graph_app or app;exec_interval=interval(data,active)
        row.update(best_raw_clearance_m=max(all_gaps),raw_sample_clearances_m=all_gaps,
            safe_raw_samples=sum(g>=THRESHOLD for g in all_gaps),SAFE_SAMPLE_EXISTED='YES' if any(g>=THRESHOLD for g in all_gaps) else 'NO',
            executed_clearance_m=exec_interval['clearance_m'],execution_start_tick=exec_interval['start_tick'],execution_end_tick=exec_interval['end_tick'],
            execution_path_kind=active['kind'],raw_execution_clearance_m=raw_interval['clearance_m'],
            raw_execution_start_tick=raw_interval['start_tick'],raw_execution_end_tick=raw_interval['end_tick'],
            active_path_clearance_m=row['corrected_clearance_m'] if accepted else row['raw_selected_clearance_m'],
            active_at_collision=active==data['active_app'])
        row['path_vs_footprint_m']=row['executed_clearance_m']-row['active_path_clearance_m']
    return row,detail


def cause(row):
    if row['raw_selected_clearance_m']<THRESHOLD:return 'SELECTION'
    if row['corrected_clearance_m'] is not None and row['corrected_clearance_m']<THRESHOLD and row['delta_m']<=-.02:return 'GRAPH_SHIFT'
    if row['active_path_clearance_m']>=THRESHOLD and row['executed_clearance_m']<0:return 'EXECUTION'
    return 'OTHER'


def conclusion(collisions):
    add=sum(r['cause']=='GRAPH_SHIFT' or r['SDF_WOULD_FIX']=='YES' for r in collisions)
    selection=sum(r['cause']=='SELECTION' and r['SAFE_SAMPLE_EXISTED']=='YES' for r in collisions)
    execution=sum(r['cause']=='EXECUTION' for r in collisions)
    return 'ADD_CONSTRAINT' if add>=3 else 'FIX_SELECTION' if selection>=3 else 'FIX_EXECUTION' if execution>=3 else 'MIXED'


def control_summary(switches):
    out=[]
    for cohort in ('success_all','collision_last3'):
        group=[r for r in switches if r['cohort']==cohort];accepted=[r for r in group if r['accepted']]
        d=np.array([r['delta_m'] for r in accepted]);n=len(d)
        out.append(dict(cohort=cohort,runs=len({(r['phase'],r['index']) for r in group}),switches=len(group),accepted=n,
            delta_lt_minus_02_count=int((d<-.02).sum()),delta_lt_minus_02_fraction=float((d<-.02).mean()) if n else None,
            delta_lt_0_fraction=float((d<0).mean()) if n else None,delta_median_m=float(np.median(d)) if n else None,
            delta_p10_m=float(np.quantile(d,.1)) if n else None,delta_p90_m=float(np.quantile(d,.9)) if n else None,
            corrected_lt_025_count=sum(r['corrected_clearance_m']<THRESHOLD for r in accepted),
            corrected_lt_025_fraction=sum(r['corrected_clearance_m']<THRESHOLD for r in accepted)/n if n else None))
    return out


def collision_figure(data,row,detail,cf,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    fig,ax=plt.subplots(figsize=(10,5));c=data['config'];r=data['source']['record']
    for box in configured_obstacles(c):
        x,y=box['center_xy_m'];sx,sy=box['size_xyz_m'][:2]
        ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,color='#999999',alpha=.45))
        ax.text(x,y,box['id'],fontsize=8,ha='center')
    for y in (-c['corridor']['half_width'],c['corridor']['half_width']):ax.axhline(y,color='gray',lw=1)
    for x in (c['corridor']['xmin'],c['corridor']['xmax']):ax.axvline(x,color='gray',lw=1)
    for i,xy in enumerate(detail['world_samples']):
        xy=np.asarray(xy);ax.plot(xy[:,0],xy[:,1],color='#aaaaaa',lw=.9,label='8 original samples' if i==0 else None)
    raw=np.array(detail['raw_world']);ax.plot(raw[:,0],raw[:,1],'--',color='#1565c0',lw=1.8,label='Selected original (full)')
    if detail['corrected_world'] is not None:
        xy=np.array(detail['corrected_world']);ax.plot(xy[:,0],xy[:,1],color='#1565c0',lw=2,label='Applied GF (full)')
    if cf['accepted']:
        xy=np.array(cf['world_xy']);ax.plot(xy[:,0],xy[:,1],color='#8e24aa',lw=2,label='Oracle v4 (offline ACCEPTED)')
    else:
        ax.text(.02,.03,'Oracle v4: '+cf['disposition']+' (no accepted path)',transform=ax.transAxes,fontsize=8)
    pose=data['poses'];ax.plot(pose[:,0],pose[:,1],color='black',lw=1.3,label='Actual robot trajectory')
    b=row['B'];ax.plot(b[0],b[1],'o',color='#ef8b21',label='B (FRESH switch)')
    ax.arrow(b[0],b[1],.15*np.cos(b[2]),.15*np.sin(b[2]),width=.004,color='#ef8b21',length_includes_head=True)
    contact=data['summary']['obstacle_evaluation']['first_contact']['detected_pose']
    ax.plot(*contact[:2],'rx',ms=9,mew=2,label='Detected collision')
    ax.add_patch(Circle(contact[:2],c['agent_radius_m'],fill=False,color='red',lw=.8))
    ax.set(xlabel='World X (m)',ylabel='World Y (m)',title=f"Phase {row['phase']} index {r['index']} / FRESH {row['id']} / {row['cause']}")
    points=np.vstack([pose[:,:2],np.asarray(detail['world_samples']).reshape(-1,2),np.asarray(cf['world_xy']) if cf['accepted'] else raw])
    ax.set_xlim(min(-.2,float(points[:,0].min())-.2),max(3.55,float(points[:,0].max())+.2))
    ax.set_ylim(-c['corridor']['half_width']-.12,c['corridor']['half_width']+.12)
    ax.set_aspect('equal');ax.legend(fontsize=7,loc='lower left',ncol=2)
    fig.tight_layout();fig.savefig(out/f"collision_{row['phase']}_{row['index']}.png",dpi=160);plt.close(fig)


def histogram(switches,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups=[[r['delta_m'] for r in switches if r['cohort']==cohort and r['accepted']] for cohort in ('success_all','collision_last3')]
    bins=np.histogram_bin_edges(np.concatenate(groups),bins=24)
    fig,axes=plt.subplots(1,2,figsize=(10,4),sharex=True)
    for ax,values,label in zip(axes,groups,('15 successful runs: all ACCEPTED switches','4 collision runs: selected ACCEPTED switches')):
        ax.hist(values,bins=bins,color='#427aa1',alpha=.85);ax.axvline(-.02,color='red',ls='--',label='-0.02m');ax.axvline(0,color='black',lw=.8)
        ax.set(title=f'{label}\nn={len(values)}',xlabel='Corrected full - selected suffix clearance (m)',ylabel='Switch count');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'delta_hist.png',dpi=160);plt.close(fig)


def report(collisions,summary,label,metadata):
    counts=dict(Counter(r['cause'] for r in collisions))
    lines=['# Phase 14-D — GRAPH-GF collision diagnosis','',
        f"Analysis source commit: `{metadata['analysis_git_sha']}`; immutable input/source hashes in `research/results/phase14d/provenance.json`.",
        f"4 collision runs + 15 successful GF runs; {metadata['collision_switches']} collision-window FRESH switches, {metadata['control_switches']} success switches. No navigation or NoMaD inference; {metadata['counterfactual_attempts']} oracle v4 attempts / {metadata['solver_calls']} solver calls, zero retries.",'',
        '## Measurement rules','',
        '- Unit: actual FRESH switch and its GF result. For each collision, take the final three FRESH switches and union the FRESH that originated the active path; deduplicate by ID. Actual GF replacement ticks are logged separately. All 15 success runs contribute every actual FRESH switch; terminal received-but-unswitched predictions are excluded.',
        '- Sample paths remain anchored to their observation pose. B is the recorded FRESH switch/Graph dispatch pose. RAW clearance uses the suffix starting at the existing nearest projection of B, without a fictitious B connector. Corrected clearance uses the entire ACCEPTED GF polyline, as requested. Thus delta compares different extents and alone is not proof that the overlapping path moved toward a box.',
        '- Footprint clearance reuses exact segment/AABB distance and the Phase6 runtime swept-arc lower bound, with radius0.09m. No new collision-distance algorithm. Wall clearance is recorded separately. Native full path, remaining RAW suffix and actual PP arcs are distinct.',
        '- Execution clearance is measured only while that actual path is active: GF replacement to next application/termination, or RAW switch to next application when GF is not accepted. RAW-before-GF intervals are separate columns. path_vs_footprint = executed clearance minus active-path clearance; a negative value means execution came closer, not necessarily a pure cross-track/corner-cutting measurement.',
        '- Controls use no new geometry. Oracle geometry is used exclusively in this offline diagnosis and its explicitly privileged counterfactual solve. Protected GraphV4 and protocol are imported unchanged, including their geometry-dependent side factors. Original sample, B, previous command and stored previous accepted GF prior are identical; no chaining of counterfactual priors.',
        '- Offline ACCEPTED means converged + protected constraints + exact certificate. No online STALE/SUPERSEDED gate is simulated. SDF_WOULD_FIX=YES only means an accepted full polyline with clearance>=0.025m: it does **not** prove safe PP execution, safe B-to-entry connection, or that the real collision would have been avoided.',
        '- Cause priority: SELECTION, GRAPH_SHIFT, EXECUTION, OTHER; conclusion priority: ADD_CONSTRAINT, FIX_SELECTION, FIX_EXECUTION, MIXED. Safe sample counts are obstacle-only>=0.025m per request, not a controller-feasibility guarantee.','',
        '## Collision cases','']
    cols=['phase','index','id','execution_path_kind','raw_selected_clearance_m','corrected_clearance_m','delta_m','best_raw_clearance_m','safe_raw_samples','executed_clearance_m','path_vs_footprint_m','cause','counterfactual_disposition','counterfactual_clearance_m','SDF_WOULD_FIX','SAFE_SAMPLE_EXISTED']
    lines+=markdown_table(collisions,cols)
    for r in collisions:
        lines+=['',f"- Phase {r['phase']} / {r['index']}: {r['cause']}; active {r['execution_path_kind']} from tick {r['execution_start_tick']} to {r['execution_end_tick']}; RAW {r['raw_selected_clearance_m']:.6f}m, GF {r['corrected_clearance_m']:.6f}m, executed {r['executed_clearance_m']:.6f}m; safe originals {r['safe_raw_samples']}/8, oracle {r['counterfactual_disposition']} ({r['SDF_WOULD_FIX']})."]
    lines+=['','## Success controls vs collision window','', 'Fractions use ACCEPTED switches with defined delta as denominator. Windows differ (all successful switches vs last three before each collision); these are descriptive, not independent-run causal comparisons. A low-clearance prediction in a successful run does not imply that its unsafe segment was actually executed.','']
    lines+=markdown_table(summary,list(summary[0]))
    lines+=['','## Figures','']
    for r in collisions:lines += [f"![Phase {r['phase']} index {r['index']}](../research/results/phase14d/collision_{r['phase']}_{r['index']}.png)",'']
    lines+=['![Clearance delta](../research/results/phase14d/delta_hist.png)','', '## Reproduction and limits','',
        f"72Hz replay: maximum pose error {metadata['max_pose_replay_error']:.3g}; clearance recomputation vs logged intervals {metadata['max_clearance_replay_error']:.3g}m. Input and protected-code hashes checked before and after analysis.",
        'Failed/infeasible solves and original unsafe samples are retained. One local SLSQP failure is not a proof that no feasible path exists. Counterfactual safety is path-level evidence only, with simulator oracle geometry; no online depth pipeline was implemented.','',
        '## Preregistered conclusion','', f'Cause counts: {json.dumps(counts,sort_keys=True)}.']
    next_step={'ADD_CONSTRAINT':'다음 단계 후보: depth SDF 제약.', 'FIX_SELECTION':'다음 단계 후보: depth 안전 필터 선택.', 'FIX_EXECUTION':'다음 단계 후보: PP 실행 여유(margin) 검토.'}
    if label in next_step:lines+=['',next_step[label]]
    lines+=['',label]
    DOC.write_text('\n'.join(lines)+'\n')


def publish():
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    assert git('branch','--show-current')=='research/phase0-infrastructure'
    assert git('remote','get-url','origin') in ('https://github.com/minju5054/NoMaD.git','git@github.com:minju5054/NoMaD.git')
    assert not git('diff','--cached','--name-only'),'Unrelated staged changes'
    intended={str(DOC.relative_to(ROOT)),*[str(f.relative_to(ROOT)) for directory in (HERE,OUT) for f in directory.iterdir() if f.is_file()]}
    assert set(git('diff','--name-only').splitlines())<=intended,'Unrelated tracked changes'
    git('add','--',str(HERE.relative_to(ROOT)),str(OUT.relative_to(ROOT)),str(DOC.relative_to(ROOT)))
    git('add','-f','--',*[str(f.relative_to(ROOT)) for f in sorted(OUT.glob('*.png'))])
    changed=set(git('diff','--cached','--name-only').splitlines());assert changed<=intended
    if changed:
        git('-c','core.whitespace=cr-at-eol','diff','--cached','--check')
        git('-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Record Phase 14-D oracle-free Graph collision diagnosis')
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    return git('rev-parse','--short','HEAD')


def execute():
    assert not OUT.exists() and not DOC.exists(),'Outputs preserved; no repeated solves'
    for name,h in PROTECTED.items():assert sha256_file(ROOT/name)==h,name
    source,hashes=sources()
    code={str(f):sha256_file(f) for f in [*HERE.glob('*.py'),*[ROOT/n for n in PROTECTED],
        ROOT/'research/nomad_isaac/handoff_audit.py',ROOT/'research/nomad_phase0/pure_pursuit.py',
        ROOT/'research/nomad_phase0/graph_v2.py',ROOT/'research/nomad_phase0/graph_v3.py']}
    OUT.mkdir(parents=True,exist_ok=False)
    write_json(OUT/'state.json',dict(state='RUNNING',rules=RULES,retries=0))
    switches=[];collisions=[];evidence=[];fields={};attempts=0;solves=0;max_pose=0.;max_gap=0.
    protocol=json.loads((ROOT/'research/nomad_phase0/graph_v4_protocol.json').read_text())
    with (OUT/'counterfactuals.jsonl').open('x') as journal:
        def log(row):journal.write(json.dumps(row)+'\n');journal.flush()
        for src in source:
            data=load_run(src,hashes);selected=data['events']
            if src['collision']:
                before=[e for e in selected if e['application_sim_s']<=data['summary']['simulation_duration_s']]
                chosen={e['id'] for e in before[-3:]}|{data['active_app']['id']}
                selected=[e for e in before if e['id'] in chosen]
                max_pose=max(max_pose,data['replay']['max_pose_error']);max_gap=max(max_gap,data['replay']['max_clearance_error'])
            for event in selected:
                row,detail=switch_row(data,event,hashes)
                if src['collision']:
                    field_key=json.dumps({k:data['config'][k] for k in ('obstacles','corridor','agent_radius_m')},sort_keys=True)
                    if field_key not in fields:fields[field_key]=SignedDistanceField(data['config'],protocol['sdf_resolution_m'],protocol['sdf_padding_m'])
                    attempts+=1;identity=dict(phase=src['phase'],index=src['record']['index'],id=event['id'])
                    log(dict(event='START',**identity,job=detail['job']))
                    cf=counterfactual(detail['job'],data['config'],fields[field_key],protocol);solves+=cf['solve_calls']
                    log(dict(event='END',**identity,result=cf))
                    row.update(counterfactual_disposition=cf['disposition'],counterfactual_clearance_m=cf['corrected_clearance_m'],SDF_WOULD_FIX=cf['SDF_WOULD_FIX'],counterfactual_wall_s=cf['wall_s'])
                    evidence.append(dict(**identity,**detail,counterfactual=cf))
                    if row['active_at_collision']:
                        row['cause']=cause(row)
                        contact=data['summary']['obstacle_evaluation']['first_contact']
                        row.update(collision_time_s=contact['detected_sim_s'],collision_pose=contact['detected_pose'],collision_obstacle=contact['obstacle_id'])
                        collisions.append(dict(row));collision_figure(data,row,detail,cf,OUT)
                switches.append(row)
    assert len(collisions)==4
    for name,h in {**hashes,**code}.items():assert sha256_file(Path(name))==h,name
    summary=control_summary(switches);label=conclusion(collisions)
    metadata=dict(analysis_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        label=label,rules=RULES,collision_switches=sum(r['cohort']=='collision_last3' for r in switches),
        control_switches=sum(r['cohort']=='success_all' for r in switches),counterfactual_attempts=attempts,solver_calls=solves,
        max_pose_replay_error=max_pose,max_clearance_replay_error=max_gap,input_sha256=hashes,source_sha256=code,
        navigation_count=0,inference_count=0,retries=0,protected_sha256=PROTECTED)
    for name,records in (('switches',switches),('collisions',collisions),('control_summary',summary)):write_csv(OUT/f'{name}.csv',records)
    write_json(OUT/'evidence.json',evidence);write_json(OUT/'summary.json',dict(metadata=metadata,collisions=collisions,controls=summary))
    write_json(OUT/'provenance.json',metadata);histogram(switches,OUT);report(collisions,summary,label,metadata)
    write_json(OUT/'state.json',dict(state='COMPLETE',label=label,solver_calls=solves,attempts=attempts,retries=0))
    write_json(OUT/'report_files.json',{str(f.relative_to(ROOT)):sha256_file(f) for f in [DOC,*sorted(OUT.iterdir())] if f.is_file()})
    return label


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');args=ap.parse_args()
    if OUT.exists():
        assert args.publish and (OUT/'report_files.json').exists(),'Partial/previous output preserved; no repeated solves'
        assert json.loads((OUT/'state.json').read_text())['state']=='COMPLETE'
        for name,h in json.loads((OUT/'report_files.json').read_text()).items():assert sha256_file(ROOT/name)==h,name
        meta=json.loads((OUT/'provenance.json').read_text())
        for name,h in {**meta['input_sha256'],**meta['source_sha256']}.items():assert sha256_file(Path(name))==h,name
        label=meta['label']
    else:label=execute()
    sha=publish() if args.publish else None
    print(json.dumps(dict(label=label,commit=sha,report=str(DOC))))


if __name__=='__main__':main()
