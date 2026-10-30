"""Read-only command/pose/RGB/depth audit and SO pilot metrics."""
import json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
from nomad_isaac.common import integrate_se2,local_to_world,sha256_file
from nomad_isaac.clearance import obstacle_bounds,single_obstacle_config,swept_clearance,corridor_clearance
from nomad_phase0.chunk_report import trace
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from nomad_isaac.topomap import candidate_range,select_subgoal
from nomad_phase15b.depth import Snapshot,evaluate_samples
from .config import place
from nomad_phase16.execution import stop_command
from nomad_phase20.execution import SPAlignment

def rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x] if Path(path).exists() else []
def stats(v):return dict(n=len(v),median=float(np.median(v)) if v else None,p95=float(np.quantile(v,.95)) if v else None)


def core_audit(run):
    run=Path(run);s=json.loads((run/'summary.json').read_text());c=s['scenario'];rec,poses=trace(run)
    ctrl=rows(run/'controller.jsonl');events=rows(run/'events.jsonl');requests=rows(run/'requests.jsonl');received=rows(run/'received.jsonl');inference=rows(run/'model/inference.jsonl')
    commands=rows(run/'phase20_commands.jsonl');repairs=rows(run/'repair.jsonl');recovery=rows(run/'recovery.jsonl');steps={r['tick']:r for r in rows(run/'recovery_72hz.jsonl')}
    assert len(requests)==len(received)==len(inference);assert len(ctrl)==len(commands)
    assert [r['tick'] for r in commands]==list(range(0,len(rec)-1,8))
    apply={r['tick']:r for r in repairs if r['event']=='PATH_APPLIED'};sp=None;err=pose_error=0.;previous=0.
    for a,b in zip(ctrl,commands):
        if b['tick'] in apply:
            p=apply[b['tick']];sp=SPAlignment();sp.replace_path(p['path_world'],p['pose'],p['previous_vw'][0])
        actual=[a['commanded_v_m_s'],a['commanded_w_rad_s']];source=b['source']
        if source in ('NORMAL','KEEP_ACTIVE','REPAIR','DETOUR','ALIGN_BRAKE','ALIGN_ROTATE','ENDPOINT'):
            assert sp is not None;expected,diag=sp.control(b['pose'],previous)
            if diag['completed']:expected=stop_command(previous)
        elif source=='RECOVER_ROTATE':expected=[0.,actual[1]];assert abs(actual[1])==.3
        elif source=='WAIT_FRESH':expected=[0.,0.]
        else:expected=stop_command(previous)
        err=max(err,float(np.max(np.abs(np.array(expected)-actual))))
        assert abs(actual[0]-previous)<=.5/9+1e-12;previous=actual[0]
    for tick in range(1,len(rec)):
        a=ctrl[(tick-1)//8];v,w=float(rec[tick]['v_m_s']),float(rec[tick]['w_rad_s'])
        expected=steps[tick]['actual_vw'] if tick in steps else [a['commanded_v_m_s'],a['commanded_w_rad_s']]
        np.testing.assert_allclose([v,w],expected,atol=1e-12,rtol=0)
        pose_error=max(pose_error,float(np.max(np.abs(integrate_se2(poses[tick-1],v,w,1/72)-poses[tick]))))
    assert err<1e-12 and pose_error<1e-12
    obs=[r for r in rows(run/'observations.jsonl') if 'observation_id' in r];frames={}
    assert all('oracle_information' not in o for o in obs)
    assert not (run/'oracle_information.json').exists()
    for o in obs:
        with Image.open(run/o['rgb_file']) as im:frame=np.asarray(im)
        assert hashlib.sha256(frame.tobytes()).hexdigest()==o['frame_sha256'];frames[o['observation_id']]=frame
    manifest=json.loads(Path(c['topomap_manifest']).read_text());assert len(manifest['nodes'])==21
    closest=0;delay=s['delivery_delay']['configured_additional_s'];delivery=[]
    for i,(q,r,m) in enumerate(zip(requests,received,inference)):
        assert q['id']==r['id']==m['id']==i and q['seed']==m['seed']==101+c['seed_offset']+2*i and m['ddpm_seed']==q['seed']+1
        assert hashlib.sha256(np.stack([frames[k] for k in q['history_observation_ids']]).tobytes()).hexdigest()==m['history_sha256']
        assert r['release_deadline_monotonic_ns']==r['packet_received_monotonic_ns']+round(delay*1e9)
        assert r['received_monotonic_ns']==r['release_monotonic_ns']>=r['release_deadline_monotonic_ns']
        t=m['topomap'];a,b=candidate_range(closest,20);assert (a,b)==(t['candidate_start'],t['candidate_end_inclusive'])
        closest,subgoal,_=select_subgoal(t['distances'],a);assert (closest,subgoal)==(t['closest_node'],t['selected_subgoal_id'])
        assert m['goal_sha256']==manifest['nodes'][subgoal]['rgb_sha256'] and t['diffusion_steps']==10
        np.testing.assert_allclose(q['observation_pose'],poses[round(q['observation_sim_s']*72)],atol=1e-12,rtol=0)
        delivery.append((r['release_monotonic_ns']-r['packet_received_monotonic_ns'])/1e9)
    for e in events:
        with np.load(run/f"model/derived/{e['id']:04d}.npz") as z:samples=z['metric'].copy()
        np.testing.assert_array_equal(samples,e['overnight_metric_samples'])
        if 'phase16' not in e:assert e.get('phase17_selection_deferred') or e.get('phase20d_selection_deferred');continue
        d=e['phase16']['selection'];field=Snapshot.load(d['snapshot']['file'])
        assert d['snapshot']['publication_monotonic_ns']<=e['phase16_selection_ns']
        _,check=evaluate_samples(np.array([local_to_world(x,e['observation_pose']) for x in samples]),e['agent_pose_at_switch'],field)
        assert check['selected_sample']==d['selected_sample'] and check['all_unsafe']==d['all_unsafe']
    spawn=json.loads((run/'dynamic/spawn.json').read_text()) if (run/'dynamic/spawn.json').exists() else None
    placement=json.loads((run/'dynamic/placement.json').read_text()) if (run/'dynamic/placement.json').exists() else None
    gaps=rows(run/'dynamic/clearance.jsonl');walls=rows(run/'clearance.jsonl');minimum=None;collision=False;gap_error=0.
    if spawn:
        expected=place(c,poses[spawn['tick']]);np.testing.assert_array_equal(expected['obstacle']['center_xy_m'],spawn['obstacle']['center_xy_m'])
        assert not any(2<=p[0]<=2.1 for p in poses[:spawn['tick']])
        render=json.loads((run/'dynamic_render_update.json').read_text());assert render['obstacle']==spawn['obstacle']
        lo,hi=obstacle_bounds(single_obstacle_config(c,spawn['obstacle']))
        for i in range(1,len(gaps)):
            tick=spawn['tick']+i;v,w=float(rec[tick]['v_m_s']),float(rec[tick]['w_rad_s'])
            g=swept_clearance(poses[tick-1],v,w,1/72,lo,hi,c['agent_radius_m'])
            gap_error=max(gap_error,abs(g['lower_m']-gaps[i]['lower_m']))
        assert gap_error<1e-9
        minimum=min(r['lower_m'] for r in gaps);collision=any(r['geometric_overlap'] for r in gaps)
    wall_min=min(r['corridor_lower_m'] for r in walls);wall_exact_min=float('inf')
    for tick,r in enumerate(walls):
        v,w=(float(rec[tick][k]) for k in ('v_m_s','w_rad_s'))
        bounded=corridor_clearance(poses[max(0,tick-1)],poses[tick],v,w,1/72 if tick else 0,c['corridor'],c['agent_radius_m'])
        assert abs(bounded-r['corridor_lower_m'])<1e-12
        exact=corridor_arc_minimum(poses[max(0,tick-1)],v,w,1/72 if tick else 0,c['corridor'],c['agent_radius_m'])
        wall_exact_min=min(wall_exact_min,exact)
    corridor=wall_exact_min<=0
    visible=next((o for o in obs if o.get('dynamic',{}).get('visible')),None);depth_seen=None;map_seen=None
    if spawn:
        for o in obs:
            f=run/f"depth/depth_{o['observation_id']:04d}.npz"
            if o.get('dynamic',{}).get('visible') and f.exists():
                with np.load(f) as z:d=z['depth']
                mask=np.array(Image.open(run/o['dynamic_mask_file']))>0
                if np.any(mask & np.isfinite(d) & (d>0) & (d<=3.)):depth_seen=o['observation_sim_s'];break
        for u in rows(run/'depth/updates.jsonl'):
            if u['sim_s']<spawn['simulation_time_s']:continue
            field=Snapshot.load(u['file']);iy,ix=np.nonzero(field.occupied);p=field.origin+np.c_[ix,iy]*field.h
            if np.any(np.all((p>=lo-.015)&(p<=hi+.015),axis=1)):map_seen=u['sim_s'];break
    pass_tick=None;side=None
    if spawn:
        candidates=np.flatnonzero((np.arange(len(poses))>=spawn['tick'])&(poses[:,0]-c['agent_radius_m']>hi[0]))
        if len(candidates):pass_tick=int(candidates[0]);side='+Y' if poses[pass_tick,1]>=spawn['obstacle']['center_xy_m'][1] else '-Y'
    attempts=[r for r in repairs if r['event']=='SUBMIT'];results=[r for r in repairs if r['event']=='RESULT'];counts=Counter(r['disposition'] for r in results)
    assert not any(r['disposition']=='ERROR' for r in results)
    outcomes=[r for r in repairs if r['event']=='FIRST_FRESH_AFTER_REPAIR']
    duration=s['simulation_duration_s'];mode_seconds=Counter();repair_follow_s=0.;active_kind=None
    for tick in range(1,len(rec)):
        control_tick=((tick-1)//8)*8
        if control_tick in apply:active_kind=apply[control_tick]['kind']
        source=commands[(tick-1)//8]['source'];mode_seconds[source]+=1/72
        if active_kind=='REPAIR' and source in ('NORMAL','KEEP_ACTIVE','REPAIR'):repair_follow_s+=1/72
    stopped=sum(mode_seconds[k] for k in ('STOP_WAIT','REPAIR_WAIT','DETOUR_WAIT','RECOVER_ROTATE','WAIT_FRESH'))
    success=bool(s['goal_entry'] and not collision and not corridor)
    invalid=placement and placement['status']=='PLACEMENT_INVALID'
    classification='PLACEMENT_INVALID' if invalid else 'SAFETY_FAILURE' if collision or corridor else 'SUCCESS' if success else 'STUCK' if s['termination_reason'] in ('simulation_timeout','navigation_wall_timeout') else 'STOPPED_NO_OVERLAP'
    return dict(technical_validation='PASS',success=success,classification=classification,collision=collision,corridor=corridor,stuck=classification=='STUCK',
        safety_failure=collision or corridor,termination_reason=s['termination_reason'],duration_s=duration,goal_time_s=duration if success else None,
        minimum_clearance_m=minimum,minimum_wall_clearance_m=wall_exact_min,minimum_monitor_wall_bound_m=wall_min,distance_m=s['distance_travelled_m'],stopped_fraction=stopped/duration if duration else 0.,
        actual_zero_speed_fraction=sum(abs(float(r['v_m_s']))<.01 for r in rec[1:])/max(1,len(rec)-1),mode_seconds=dict(mode_seconds),
        alignment_count=sum(r['event']=='PATH_APPLIED' and r['alignment'] for r in repairs),alignment_braking_s=mode_seconds['ALIGN_BRAKE'],alignment_rotation_s=mode_seconds['ALIGN_ROTATE'],
        all_unsafe=sum(e.get('phase16',{}).get('selection',{}).get('all_unsafe',False) for e in events),recovery_count=sum(r['event']=='START' for r in recovery),
        repair_attempts=len(attempts),repair_accepted=counts['ACCEPTED'],repair_rejected=counts['REJECTED'],repair_timeout=counts['TIMEOUT'],repair_dispositions=dict(counts),
        repair_acceptance=counts['ACCEPTED']/len(attempts) if attempts else None,repair_execution_s=repair_follow_s,
        repair_resolved_all_unsafe_fraction=counts['ACCEPTED']/sum(e.get('phase16',{}).get('selection',{}).get('all_unsafe',False) for e in events) if any(e.get('phase16',{}).get('selection',{}).get('all_unsafe',False) for e in events) else None,
        post_repair_safe_count=sum(r['safe_sample_count']>0 for r in outcomes),post_repair_fresh_count=len(outcomes),
        repair_wall_s=stats([r['wait_s'] for r in results]),spawn_s=spawn['simulation_time_s'] if spawn else None,
        first_visible_s=visible['observation_sim_s'] if visible else None,first_depth_observed_s=depth_seen,first_depth_map_observed_s=map_seen,
        box_passage_time_s=pass_tick/72-spawn['simulation_time_s'] if pass_tick is not None else None,passed_box=pass_tick is not None,pass_side=side,
        command_replay_error=err,pose_replay_error=pose_error,clearance_replay_error=gap_error,oracle_publications=0,
        requests=len(requests),switches=len(events),inference_ms=stats([m['inference_ms'] for m in inference]),delivery_s=stats(delivery))


def audit(run):
    run=Path(run);result=core_audit(run);detours=rows(run/'detour.jsonl');jobs=rows(run/'repair_pool_jobs.jsonl')
    commands=rows(run/'phase20_commands.jsonl');ctrl=rows(run/'controller.jsonl');updates=rows(run/'depth/updates.jsonl');archives=rows(run/'depth/archives.jsonl')
    s=json.loads((run/'summary.json').read_text());epoch=s['epoch_monotonic_ns'];duration=s['simulation_duration_s'];rec,poses=trace(run)
    assert len(updates)==len(archives)==len([o for o in rows(run/'observations.jsonl') if 'observation_id' in o])
    for u,a in zip(updates,archives):
        assert u['frame_id']==a['frame_id'] and u['processing_end_ns']<=u['publication_monotonic_ns']<=a['archive_start_ns']
        assert u['dropped_frames']==0 and sha256_file(a['file'])==a['snapshot_sha256']
    events=rows(run/'events.jsonl');applied=[r for r in detours if r['event']=='APPLIED'];outcomes=[];overlaps=[]
    trigger={r['job_id']:r for r in detours if r['event']=='TRIGGER'};ends={r['job_id']:r for r in detours if r['event']=='END'}
    geometry=rows(run/'dynamic/clearance.jsonl');spawn=json.loads((run/'dynamic/spawn.json').read_text()) if (run/'dynamic/spawn.json').exists() else None
    for r in applied:
        end=ends.get(r['job_id']);stop=end['simulation_time_s'] if end else duration;t=r['simulation_time_s']
        overlap=any(g.get('geometric_overlap',False) and t<g['end_sim_s']<=stop for g in geometry)
        overlaps.append(dict(job_id=r['job_id'],start_s=t,end_s=stop,collision=overlap))
        if end:
            e=next((e for e in events if e['application_sim_s']>stop and 'phase16' in e),None)
            if e:
                selection=e['phase16']['selection'];index=selection['selected_sample'];path=local_to_world(np.array(e['overnight_metric_samples'][index]),e['observation_pose'])
                forward=float((path[-1]-np.array(e['agent_pose_at_switch'])[:2])@np.array(trigger[r['job_id']]['u_ref']))
                outcomes.append(dict(job_id=r['job_id'],fresh_id=e['id'],forward_endpoint_m=forward,progress_recovered=forward>=.2,safe_samples=sum(c['safe'] for c in selection['candidates'])))
    ages=[c['phase20d']['snapshot_age_s'] for c in ctrl if c['phase20d']['depth_frame']>=0]
    live=[u for u in updates if u['publication_monotonic_ns']<=epoch+round(s['navigation_wall_seconds']*1e9)]
    pubs=[epoch]+[u['publication_monotonic_ns'] for u in live]+[epoch+round(s['navigation_wall_seconds']*1e9)]
    gaps=[dict(start_s=max(0.,(a-epoch)/1e9),end_s=(b-epoch)/1e9,length_s=(b-a)/1e9) for a,b in zip(pubs,pubs[1:]) if b-a>=500_000_000]
    dc=Counter(r['disposition'] for r in detours if r['event']=='RESULT');mode=result['mode_seconds']
    jd=[j for j in jobs if j['kind']=='R3'];jr=[j for j in jobs if j['kind']=='R2']
    assert not any(r.get('error') for r in jobs),'CPU planner transport error'
    # Recheck every actual detour application against the map/time available then.
    from .recent import RecentSnapshot
    from .runtime import Execution
    for r in applied:
        cmd=next(c for c in ctrl if abs(c['simulation_time_s']-r['simulation_time_s'])<1e-12)
        u=next(u for u in updates if u['frame_id']==cmd['phase20d']['depth_frame']);field=RecentSnapshot.load(u['file'])
        assert Execution.certificate(None,field,r['pose'],round(r['simulation_time_s']*72),r['path'],r['B'])
    pass_time=spawn['simulation_time_s']+result['box_passage_time_s'] if spawn and result['passed_box'] else None
    result.update(detour_triggers=dict(Counter(r['trigger'] for r in trigger.values())),detour_attempts=len(trigger),detour_submitted=sum(r['event']=='SUBMIT' for r in detours),
        detour_applied=len(applied),detour_dispositions=dict(dc),detour_timeout=dc['TIMEOUT'],detour_rejected=dc['REJECTED'],
        detour_wait_s=mode.get('DETOUR_WAIT',0.),detour_execution_s=sum(x['end_s']-x['start_s'] for x in overlaps),detour_moving_s=mode.get('DETOUR',0.),
        detour_collision_count=sum(x['collision'] for x in overlaps),detour_intervals=overlaps,
        detour_then_box_pass_count=sum(x['start_s']<pass_time for x in overlaps) if pass_time is not None else 0,
        detour_before_box_pass_count=sum(pass_time is None or x['start_s']<pass_time for x in overlaps),
        post_detour_outcomes=outcomes,post_detour_progress_recovered=sum(x['progress_recovered'] for x in outcomes),post_detour_outcome_count=len(outcomes),
        seven_solve_s=stats([j['pool_wall_s'] for j in jd]),detour_job_timings=[{k:j[k] for k in ('job_id','sample_solve_s','pool_wall_s','dispatch_to_complete_s','cache')} for j in jd],
        repair_job_timings=[{k:j[k] for k in ('job_id','sample_solve_s','pool_wall_s','dispatch_to_complete_s')} for j in jr],
        snapshot_age_s=stats(ages),snapshot_max_age_s=max(ages,default=None),publication_gaps=gaps,max_publication_gap_s=max([(b-a)/1e9 for a,b in zip(pubs,pubs[1:])],default=0.),
        depth_updates=len(updates),depth_dropped_frames=0,depth_update_ms=stats([u['update_ms'] for u in updates]),depth_queue_max=max([u['queue_length_at_publish'] for u in updates],default=0),depth_archive_queue_max=max([u['archive_queue_length'] for u in updates],default=0))
    return result
