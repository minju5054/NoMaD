"""Offline audit/evaluation only. Never feeds geometry back to an executor."""
import hashlib,json
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from nomad_isaac.common import integrate_se2,sha256_file,local_to_world
from nomad_isaac.clearance import obstacle_bounds,single_obstacle_config,swept_clearance
from nomad_phase0.chunk_report import trace
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from nomad_phase15.evaluate import sample_path,suffix
from nomad_phase15b.depth import Snapshot,evaluate_samples
from nomad_phase4c.plant import control_command
from nomad_phase16.execution import stop_command
from .config import SAFE
from nomad_phase16.geometry import centered,shifted,path_safety,point_box_distance,rect

def rows(p):return [json.loads(l) for l in Path(p).read_text().splitlines() if l] if Path(p).exists() else []
def stats(v):
    a=np.array(v,dtype=float)
    return dict(n=len(a),median=float(np.median(a)) if len(a) else None,p95=float(np.quantile(a,.95)) if len(a) else None)
def atomic_json(p,d):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');tmp.replace(p)

def audit(run):
    run=Path(run);s=json.loads((run/'summary.json').read_text());c=s['scenario'];m=c['phase15b_method'];rec,poses=trace(run)
    ctr=rows(run/'controller.jsonl');events=rows(run/'events.jsonl');requests=rows(run/'requests.jsonl');received=rows(run/'received.jsonl');inference=rows(run/'model/inference.jsonl');gaps=rows(run/'clearance.jsonl');graph=rows(run/'stage2_graph.jsonl')
    recover=rows(run/'recovery.jsonl');recovery_steps={r['tick']:r for r in rows(run/'recovery_72hz.jsonl')}
    assert len(rec)==len(gaps);assert len(requests)==len(received)==len(inference)
    np.testing.assert_allclose([float(r['simulation_time_s']) for r in rec],np.arange(len(rec))/72,atol=1e-12,rtol=0)
    np.testing.assert_allclose([r['simulation_time_s'] for r in ctr],np.arange(len(ctr))/9,atol=1e-12,rtol=0)
    previous_v=0.;command_error=0.
    for control in ctr:
        expected=[0.,0.];diag=control['pure_pursuit']
        recovery=control.get('phase17_recovery',{})
        if recovery.get('state') in ('RECOVER_ROTATE','WAIT_FRESH'):
            expected=[0.,control['commanded_w_rad_s'] if recovery['state']=='RECOVER_ROTATE' else 0.]
            if recovery['state']=='RECOVER_ROTATE':assert abs(expected[1])==.3
        elif control['valid']:
            if control.get('phase16_fallback_mode')=='STOP_WAIT':expected=stop_command(previous_v)
            elif diag['stop_reason'] is None:
                x,y=diag['target_local_x_m'],diag['target_local_y_m'];k=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
                expected=control_command('CURV',k,previous_v,0.,float('inf'))[0]
        actual=[control['commanded_v_m_s'],control['commanded_w_rad_s']]
        command_error=max(command_error,float(np.max(np.abs(np.array(expected)-actual))));previous_v=actual[0]
        ensemble=control.get('phase16_ensemble') or control.get('phase12_ensemble')
        if ensemble and ensemble['components']:
            weights=np.exp(-.5*np.arange(len(ensemble['components'])));weights/=weights.sum()
            np.testing.assert_allclose(ensemble['weights'],weights,atol=1e-12,rtol=0)
            assert all(0<=control['monotonic_ns']-x['received_ns']<1e9 for x in ensemble['components'])
    assert command_error<1e-12
    pose_error=0.;gap_error=0.;oracle_min=float('inf');wall_min=float('inf');margin=0.;collision=False;crossed=False
    cc,off=centered(c)
    for tick in range(1,len(rec)):
        control=ctr[(tick-1)//8];v,w=float(rec[tick]['v_m_s']),float(rec[tick]['w_rad_s'])
        expected=recovery_steps[tick]['actual_vw'] if tick in recovery_steps else [control['commanded_v_m_s'],control['commanded_w_rad_s']]
        np.testing.assert_allclose([v,w],expected,atol=1e-12,rtol=0)
        pose_error=max(pose_error,float(np.abs(integrate_se2(poses[tick-1],v,w,1/72)-poses[tick]).max()))
        near=False
        for box in c['obstacles']:
            lo,hi=obstacle_bounds(single_obstacle_config(c,box));gap=swept_clearance(poses[tick-1],v,w,1/72,lo,hi,c['agent_radius_m'])
            gap_error=max(gap_error,abs(gap['lower_m']-gaps[tick]['obstacles'][box['id']]['lower_m']))
            oracle_min=min(oracle_min,gap['lower_m']);near|=gap['lower_m']<.02;collision|=gap['geometric_overlap']
        wall=corridor_arc_minimum(shifted(poses[tick-1],off),v,w,1/72,cc['corridor'],c['agent_radius_m']);wall_min=min(wall_min,wall);crossed|=wall<0
        margin+=near/72
    assert pose_error<1e-12 and gap_error<1e-9
    from nomad_isaac.topomap import load_map,candidate_range,select_subgoal
    load_map(c['topomap_manifest']);assert sha256_file(c['topomap_manifest'])==c['topomap_manifest_sha256']
    manifest=json.loads(Path(c['topomap_manifest']).read_text());closest=0;frames={}
    obs={o['observation_id']:o for o in rows(run/'observations.jsonl') if 'observation_id' in o}
    for oid,o in obs.items():
        with Image.open(run/o['rgb_file']) as im:f=np.array(im)
        assert hashlib.sha256(f.tobytes()).hexdigest()==o['frame_sha256'];frames[oid]=f
    for k,(q,r,inf) in enumerate(zip(requests,received,inference)):
        assert q['id']==r['id']==inf['id']==k and q['seed']==101+c['seed_offset']+2*k and inf['seed']==q['seed']
        assert inf['ddpm_seed']==q['seed']+1
        delay=s['delivery_delay']['configured_additional_s']
        assert r['release_deadline_monotonic_ns']==r['packet_received_monotonic_ns']+round(delay*1e9)
        assert r['release_monotonic_ns']==r['received_monotonic_ns'] and r['release_monotonic_ns']>=r['release_deadline_monotonic_ns']
        assert hashlib.sha256(np.stack([frames[i] for i in q['history_observation_ids']]).tobytes()).hexdigest()==inf['history_sha256']
        np.testing.assert_allclose(q['observation_pose'],poses[round(q['observation_sim_s']*72)],rtol=0,atol=1e-12)
        top=inf['topomap'];a,b=candidate_range(closest,len(manifest['nodes'])-1)
        assert (a,b)==(top['candidate_start'],top['candidate_end_inclusive'])
        closest,subgoal,_=select_subgoal(top['distances'],a);assert (closest,subgoal)==(top['closest_node'],top['selected_subgoal_id'])
        assert inf['goal_sha256']==manifest['nodes'][subgoal]['rgb_sha256']
        with np.load(run/f'model/raw/{k:04d}.npz') as raw,np.load(run/f'model/derived/{k:04d}.npz') as derived:
            cumulative=np.cumsum((raw['normalized_diffusion']+1)/2*np.array([7.5,8.])+[-2.5,-4.],axis=1).astype(np.float32)
            np.testing.assert_array_equal(cumulative*np.float32(.05),derived['metric'])
    duration=(len(rec)-1)/72;times=np.array([x['simulation_time_s'] for x in ctr]);dt=np.maximum(0,np.r_[times[1:],duration]-times)
    active=np.array([x['pure_pursuit']['stop_reason'] is None and x.get('phase16_fallback_mode')!='STOP_WAIT' for x in ctr])
    slow=np.array([(x['stage2'].get('v_target_m_s') or .3)<.2-1e-12 for x in ctr])
    reason=s['termination_reason'];success=bool(s['goal_entry'] and not collision and not crossed)
    kind='SAFETY_FAILURE' if collision or crossed else 'SUCCESS' if success else 'STUCK' if 'timeout' in reason else 'OTHER_TERMINATION'
    distance=float(np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1).sum());checkpoint=np.flatnonzero(poses[:,c['checkpoint']['axis']]>=c['checkpoint']['threshold_m']);tick=int(checkpoint[0]) if len(checkpoint) else None
    fallback=rows(run/'fallback.jsonl');apps=rows(run/'phase16_applications.jsonl') or rows(run/'phase6_applications.jsonl')
    dangerous=total=unknown_risky=0;unknown=[];rejected_unknown=[];snapshot_age=[];fallback_modes=Counter(x['mode'] for x in fallback)
    for e in events:
        if e.get('phase17_selection_deferred'):continue
        # The execution wrapper takes its own immutable pointer after the core's
        # preliminary capture. Use the actual selector input if publication raced.
        meta=e.get('phase16',{}).get('selection',{}).get('snapshot',e['depth_snapshot'])
        assert meta.get('publication_monotonic_ns',0)<=e.get('phase16_selection_ns',e.get('phase15b_selection_monotonic_ns',e['application_monotonic_ns']))
        snap=Snapshot.load(meta['file']);worlds=np.array([local_to_world(np.array(x),e['observation_pose']) for x in e['overnight_metric_samples']]);B=e['agent_pose_at_switch']
        _,decision=evaluate_samples(worlds,B,snap);snapshot_age.append(e['application_sim_s']-snap.metadata['sim_s'])
        if m in SAFE:
            logged=e['phase16']['selection'];assert decision['selected_sample']==logged['selected_sample'] and decision['all_unsafe']==logged['all_unsafe']
        selected=decision['selected_sample'] if m in SAFE else 0
        for i,candidate in enumerate(decision['candidates']):
            p,_=suffix(worlds[i],B);safety=path_safety(p,c);oracle=min(safety['obstacle_clearance_m'],safety['corridor_clearance_m'])
            dangerous+=bool(candidate['safe'] and oracle<.025);total+=1
        q,_=sample_path(suffix(worlds[selected],B)[0])
        (rejected_unknown if m in SAFE and decision['all_unsafe'] else unknown).append(snap.unknown_fraction(q))
    app_risk=[];applied_unknown=[];event_by_id={e['id']:e for e in events}
    for app in apps:
        if app.get('fallback_mode')=='STOP_WAIT':continue  # No path-following command while braking/waiting.
        meta=app.get('depth_snapshot') or event_by_id.get(app['id'],{}).get('depth_snapshot')
        if not meta:continue
        component_paths=[x['world_xy'] for x in app.get('ensemble_components',[])] or ([app['world_xy']] if app.get('world_xy') else [])
        if not component_paths:continue
        snap=Snapshot.load(meta['file']);q=np.vstack([sample_path(suffix(np.array(path),app['pose'])[0])[0] for path in component_paths]);cells,ok=snap.cells(q);is_unknown=np.ones(len(q),bool)
        x,y=cells[ok].T;is_unknown[ok]=~snap.observed[y,x]
        applied_unknown.append(float(is_unknown.mean()))
        xmin,xmax,ymin,ymax=rect(c);d=np.minimum.reduce([q[:,0]-xmin,xmax-q[:,0],q[:,1]-ymin,ymax-q[:,1]])-c['agent_radius_m']
        for box in c['obstacles']:d=np.minimum(d,point_box_distance(q,box)-c['agent_radius_m'])
        risk=is_unknown & (d<.025);count=int(risk.sum());unknown_risky+=count
        app_risk.append(dict(tick=app['tick'],unknown_risky_points=count,near_terminal_risky_points=int(np.sum(risk & (np.linalg.norm(q-poses[-1,:2],axis=1)<=.12)))))
    jobs=[g for g in graph if g['event']=='SUBMIT'];results=[g for g in graph if g['event']=='RESULT'];accepted=[g for g in results if g['disposition']=='ACCEPTED'];solve=[g['solver']['solver_wall_s'] for g in results if 'solver' in g]
    for job in jobs:assert not any(k in job for k in ('public_config','obstacles','corridor')),'Oracle configuration leaked into a Phase17 Graph job'
    if 'GRAPH-depth' in m:
        for result in accepted:
            snap=Snapshot.load(result['depth_snapshot_file']);assert snap.exact_clearance(np.array(result['applied_world_xy']))>=.025-1e-8
    depth=rows(run/'depth/updates.jsonl');mode_times={mode:float(sum(t for t,x in zip(dt,ctr) if x.get('phase16_fallback_mode')==mode)) for mode in ('KEEP_ACTIVE','STOP_WAIT')}
    result=dict(technical_validation='PASS',classification=kind,success=success,collision=bool(collision),corridor=bool(crossed),stuck=kind=='STUCK',termination_reason=reason,
        duration_s=duration,goal_time_s=duration if success else None,distance_m=distance,reference_length_m=c['reference_length_m'],no_detour_success=success and distance<=1.3*c['reference_length_m'],
        checkpoint_time_s=tick/72 if tick is not None else None,checkpoint_mean_speed_m_s=float(np.linalg.norm(np.diff(poses[:tick+1,:2],axis=0),axis=1).sum()/(tick/72)) if tick else None,
        minimum_oracle_clearance_m=min(oracle_min,wall_min),minimum_obstacle_clearance_m=oracle_min,minimum_wall_clearance_m=wall_min,margin_violation_s=margin,
        curv_slow_fraction=float(dt[active & slow].sum()/dt[active].sum()) if dt[active].sum() else None,endpoint_clamp_fraction=float(np.mean([bool(x['pure_pursuit'].get('endpoint_clamped')) for x in ctr])),
        stop_duration_s=sum(abs(float(r['v_m_s']))<1e-12 for r in rec[1:])/72,fallback_events=dict(fallback_modes),fallback_time_s=mode_times,
        te_removed_chunks=sum(r.get('removed_chunk_count',0) for r in fallback),te_expired_chunks_at_fallback=sum(r.get('expired_chunk_count',0) for r in fallback),
        fallback_time_fraction={k:v/duration for k,v in mode_times.items()},graph_calls=len(jobs),graph_accepted=len(accepted),graph_dispositions=dict(Counter(g['disposition'] for g in results)),
        graph_initialization_rejected=sum(bool(g.get('initialization_rejected')) for g in results),solve_time_s=stats(solve),
        sdf_active_count=sum(bool(g['solver'].get('sdf_active_within_1mm')) for g in accepted) if 'GRAPH-depth' in m else None,
        depth_update_ms=stats([r['update_ms'] for r in depth]),snapshot_age_s=stats(snapshot_age),dangerous_false_safe_count=dangerous,depth_sample_decisions=total,
        selected_unknown_fraction=stats(unknown),rejected_candidate_unknown_fraction=stats(rejected_unknown),applied_path_unknown_fraction=stats(applied_unknown),unknown_risky_path_points=unknown_risky,
        unknown_associated_safety_failure=bool((collision or crossed) and app_risk and apps and app_risk[-1]['tick']==apps[-1]['tick'] and app_risk[-1]['near_terminal_risky_points']>0),unknown_causal_failure_count=None,
        inference_ms=stats([r['inference_ms'] for r in inference]),actual_delivery_delay_s=stats([(r['release_monotonic_ns']-r['packet_received_monotonic_ns'])/1e9 for r in received]),
        pose_replay_error=pose_error,command_replay_error=command_error,clearance_replay_error=gap_error,pacing_error_s=stats([abs(float(r['pacing_error_s'])) for r in rec]),request_count=len(requests),switch_count=len(events),
        input_sha256={p:sha256_file(run/p) for p in ('summary.json','agent_trajectory.csv','controller.jsonl','events.jsonl','stage2_graph.jsonl','scenario.json')})
    result.update(recovery_metrics(run,recover,recovery_steps,events,graph,poses,c))
    return result

def recovery_metrics(run,recover,steps,events,graph,poses,config):
    from .recovery import free_rays,ANGLE
    starts=[r for r in recover if r['event']=='START'];ends=[r for r in recover if r['event']=='END']
    outcomes=[r for r in recover if r['event']=='FIRST_FRESH']
    assert len(starts)<=12
    for s in starts:
        assert s['stop_wait_streak']>=2 and abs(s['previous_actual_v_m_s'])<.01
        snap=Snapshot.load(s['snapshot']['file']);sign,rays=free_rays(snap,s['pose'])
        assert sign==s['sign'] and rays==s['rays_m']
        end=next((e for e in ends if e['recovery_id']==s['recovery_id']),None)
        segment=[x for x in steps.values() if x['recovery_id']==s['recovery_id'] and x['state']=='RECOVER_ROTATE']
        assert all(x['actual_vw'][0]==0 and abs(x['actual_vw'][1])<=.3 for x in segment)
        if end:
            assert abs(end['angle_rad']-sign*ANGLE)<1e-10
            np.testing.assert_allclose(poses[s['tick']:end['tick']+1,:2],np.tile(s['pose'][:2],(end['tick']-s['tick']+1,1)),atol=1e-12,rtol=0)
    for o in outcomes:
        e=next(e for e in events if e['id']==o['id'])
        assert o['safe_sample_count']==sum(x['safe'] for x in e['phase16']['selection']['candidates'])
    jobs={g['job_id']:g for g in graph if g['event']=='SUBMIT'}
    accepted=[g for g in graph if g['event']=='RESULT' and g['disposition']=='ACCEPTED']
    delta=[]
    for g in accepted:
        job=jobs[g['job_id']]
        def gap(x):
            s=path_safety(np.array(x),config);return min(s['obstacle_clearance_m'],s['corridor_clearance_m'])
        delta.append(gap(g['applied_world_xy'])-gap(job['world_xy']))
    solved=[g for g in graph if g['event']=='RESULT' and 'solver' in g]
    return dict(recovery_count=len(starts),recovery_completed=len(ends),
        recovery_time_s=sum(s['state']=='RECOVER_ROTATE' for s in steps.values())/72,
        recovery_time_fraction=sum(s['state']=='RECOVER_ROTATE' for s in steps.values())/(len(poses)-1),
        recovery_observed_outcomes=len(outcomes),recovery_safe_outcomes=sum(o['safe_sample_count']>0 for o in outcomes),
        recovery_limit_reached=len(starts)==12,recovery_deferred_fresh=sum(e.get('phase17_selection_deferred',False) for e in events),
        accepted_clearance_delta_m=delta,clearance_solved_jobs=len(solved),
        clearance_active_jobs=sum(g['solver'].get('clearance_preference_active',False) for g in solved))

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('output',type=Path);a=p.parse_args();result=audit(a.run)
    assert not a.output.exists();atomic_json(a.output,result);print(result['technical_validation'])
if __name__=='__main__':main()
