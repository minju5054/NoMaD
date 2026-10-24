"""Read-only S0 delay audit. No model inference or counterfactual navigation."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image
from nomad_isaac.async_report import rows, stats, wrapped
from nomad_isaac.common import integrate_se2, local_to_world, original_controller, sha256_file
from nomad_isaac.clearance import swept_clearance, obstacle_bounds, single_obstacle_config
from nomad_isaac.topomap import candidate_range, select_subgoal
from nomad_phase0.chunk_report import trace
from nomad_phase0.chunk_execution import protocol as follower_protocol
from nomad_phase0.pure_pursuit import PurePursuit, XYPath
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from .base_metrics import extract_run
from .execution import decision
from .plant import control_command,alpha_value
from .config import protocol



def corridor_breach_axes(pose, v, w, dt, corridor, radius):
    """Label the exact arc extrema used by the existing corridor metric, including X walls."""
    times = [0., dt]
    if w != 0:
        a, b = sorted((pose[2], pose[2]+w*dt))
        for k in range(math.floor(a/(math.pi/2)), math.ceil(b/(math.pi/2))+1):
            t = (k*math.pi/2-pose[2])/w
            if 0 < t < dt:
                times.append(t)
    xy = np.array([integrate_se2(pose, v, w, t)[:2] for t in times])
    bounds = {'back_wall_negative_x': np.min(xy[:,0]-corridor['xmin'])-radius,
              'end_wall_positive_x': np.min(corridor['xmax']-xy[:,0])-radius,
              'left_wall_positive_y': np.min(corridor['half_width']-xy[:,1])-radius,
              'right_wall_negative_y': np.min(corridor['half_width']+xy[:,1])-radius}
    return [name for name,value in bounds.items() if value < 0]


def audit(run, run_id, offset, delay, legacy=False, switch_world_xy=None):
    run = Path(run)
    result = extract_run(run, 'PP', run_id, offset, delay_sweep=not legacy)
    s = json.loads((run/'summary.json').read_text()); c = s['scenario']
    environment=json.loads((run/'model/environment.json').read_text())
    assert environment['checkpoint_sha256']==protocol()['checkpoint_sha256']
    assert environment['coverage']['parameter_coverage']==1.0
    records, poses = trace(run)
    control, events, received, requests, inference, gaps = [rows(run/n) for n in
        ('controller.jsonl','events.jsonl','received.jsonl','requests.jsonl','model/inference.jsonl','clearance.jsonl')]
    observations = {o['observation_id']:o for o in rows(run/'observations.jsonl') if 'observation_id' in o}
    manifest = json.loads(Path(c['topomap_manifest']).read_text())
    frames = {}
    for i,o in observations.items():
        with Image.open(run/o['rgb_file']) as im: frame = np.asarray(im)
        assert hashlib.sha256(frame.tobytes()).hexdigest() == o['frame_sha256']
        frames[i] = frame
    closest = 0; worlds = {}; delivery = []; last_receive = -1
    for q,r,m in zip(requests,received,inference):
        assert q['request_submit_monotonic_ns'] > last_receive
        last_receive = r['received_monotonic_ns']
        assert len(r['history_observation_ids']) == 4 and np.all(np.diff(r['history_observation_ids'])>0)
        assert [observations[i]['frame_sha256'] for i in r['history_observation_ids']] == r['history_frame_sha256']
        assert hashlib.sha256(np.stack([frames[i] for i in r['history_observation_ids']]).tobytes()).hexdigest() == m['history_sha256'] == r['history_sha256']
        t=m['topomap']; a,b=candidate_range(closest,13)
        assert (a,b)==(t['candidate_start'],t['candidate_end_inclusive'])
        closest,subgoal,_=select_subgoal(t['distances'],a)
        assert (closest,subgoal)==(t['closest_node'],t['selected_subgoal_id'])
        assert m['goal_sha256']==manifest['nodes'][subgoal]['rgb_sha256']
        assert t['diffusion_steps']==10 and t['diffusion_passes']==1
        chain=[r[k] for k in ('pose_sample_monotonic_ns','observation_monotonic_ns','capture_end_monotonic_ns',
            'request_submit_monotonic_ns','request_send_monotonic_ns','inference_start_monotonic_ns',
            'inference_end_monotonic_ns','host_output_ready_monotonic_ns','persistence_end_monotonic_ns','received_monotonic_ns')]
        assert np.all(np.diff(np.array(chain,dtype=np.int64))>=0)
        assert r['ready_monotonic_ns']==r['inference_end_monotonic_ns']
        obs_tick=round(r['observation_sim_s']*72)
        np.testing.assert_allclose(poses[obs_tick],r['observation_pose'],rtol=0,atol=1e-12)
        assert int(records[obs_tick]['monotonic_ns'])==r['pose_sample_monotonic_ns']
        if not legacy:
            packet,release=r['packet_received_monotonic_ns'],r['release_monotonic_ns']
            assert release==r['received_monotonic_ns'] and packet>=r['persistence_end_monotonic_ns']
            assert r['release_deadline_monotonic_ns']==packet+round(delay*1e9)
            assert release>=r['release_deadline_monotonic_ns'] and r['additional_delivery_delay_s']==delay
            delivery.append((release-packet)/1e9)
        with np.load(run/f"model/raw/{r['id']:04d}.npz") as raw, np.load(run/f"model/derived/{r['id']:04d}.npz") as derived:
            z,metric=raw['normalized_diffusion'],derived['metric']
            assert z.shape==metric.shape==(8,8,2) and np.isfinite(metric).all()
            cumulative=np.cumsum(((z+1)/2)*np.array([7.5,8.])+np.array([-2.5,-4.]),axis=1).astype(np.float32)
            np.testing.assert_array_equal(cumulative,derived['cumulative'])
            np.testing.assert_array_equal(cumulative*np.float32(.05),metric)
            np.testing.assert_array_equal(metric[0,2],r['selected_waypoint_m'])
            worlds[r['id']]=local_to_world(metric[0],np.asarray(r['observation_pose']))
            np.testing.assert_allclose(worlds[r['id']],r['chunk']['world_xy_m'],rtol=0,atol=1e-12)
    graph_log=rows(run/'stage2_graph.jsonl')
    jobs={r['job_id']:r for r in graph_log if r['event']=='SUBMIT'}
    results=[r for r in graph_log if r['event']=='RESULT']
    applications={r['applied_tick']:r for r in results if r['disposition']=='ACCEPTED'}
    assert len(applications)==sum(r['disposition']=='ACCEPTED' for r in results)
    assert len(jobs)==(len(events) if c['phase4c_method']=='GRAPH' else 0)
    by_tick={round(e['application_sim_s']*72):e for e in events}
    follower=None; max_command_error=0.; valid_ticks=clamped=curvature_ticks=0; handoffs=[]
    pd=original_controller();previous_v=0.;fresh_switch_s=None;corrected=False;graph_ticks=0
    flag_counts={k:0 for k in ("CURVATURE_SATURATED","ACCEL_LIMITED","OMEGA_CLIPPED")}
    assert [round(c['simulation_time_s']*72) for c in control]==list(range(0,len(records)-1,8))
    for index,ctrl in enumerate(control):
        tick=index*8; pose=poses[tick]; e=by_tick.get(tick)
        if e:
            fresh_switch_s=ctrl['simulation_time_s'];corrected=False
            np.testing.assert_allclose(pose,e['agent_pose_at_switch'],rtol=0,atol=1e-12)
            assert ctrl['monotonic_ns']>=e['received_monotonic_ns']
            if index: assert control[index-1]['monotonic_ns']<e['received_monotonic_ns']
            applied_xy=worlds[e['id']] if switch_world_xy is None else switch_world_xy(worlds[e['id']],pose,e)
            try: follower=PurePursuit(applied_xy,follower_protocol()['follower'])
            except ValueError: follower=None
            start=round(e['observation_sim_s']*72); path=follower.path if follower else None
            projected,distance=path.project(pose[:2]) if path else (None,None)
            before=np.array([control[index-1][k] for k in ('commanded_v_m_s','commanded_w_rad_s')]) if index else np.zeros(2)
            after=np.array([ctrl[k] for k in ('commanded_v_m_s','commanded_w_rad_s')])
            handoffs.append({'id':e['id'],'old_id':e['chunk_transition']['old_id'],
                'observation_sim_s':e['observation_sim_s'],'switch_sim_s':e['application_sim_s'],
                'A':e['observation_pose'],'B':pose.tolist(),
                'A_B_distance_m':float(np.linalg.norm(np.diff(poses[start:tick+1,:2],axis=0),axis=1).sum()),
                'A_B_displacement_m':float(np.linalg.norm(pose[:2]-poses[start,:2])),
                'A_B_yaw_rad':float(wrapped(pose[2]-poses[start,2])),
                'A_B_abs_yaw_rad':abs(float(wrapped(pose[2]-poses[start,2]))),
                'A_B_total_abs_yaw_rad':float(np.abs(np.diff(np.unwrap(poses[start:tick+1,2]))).sum()),
                'path_valid':path is not None,'path_length_m':float(path.s[-1]) if path else None,
                'projected_arclength_m':projected,'projection_distance_m':distance,
                'staleness':projected/float(path.s[-1]) if path else None,
                'remaining_length_m':float(path.s[-1])-projected if path else None,
                'abs_dw':abs(float(after[1]-before[1])),'w_sign_flip':bool(after[1]*before[1]<0),
                'before_vw':before.tolist(),'after_vw':after.tolist(),
                'observation_to_switch_wall_s':(e['application_monotonic_ns']-e['observation_monotonic_ns'])/1e9,
                'tangent_delta_rad':e['chunk_transition']['signed_tangent_change_rad']})
        if tick in applications:
            a=applications[tick];job=jobs[a['job_id']]
            assert e is None and ctrl['valid'] and a['id']==ctrl['waypoint_id']
            assert a['result_received_ns']<=ctrl['monotonic_ns']
            if index: assert control[index-1]['monotonic_ns']<a['result_received_ns']
            assert a['solver']['success'] and a['solver']['constraints_satisfied'] and a['solver']['exact_certificate_pass']
            assert a['processing_wall_s']<=.5
            follower=PurePursuit(a['applied_world_xy'],follower_protocol()['follower']);corrected=True
            np.testing.assert_allclose(job['boundary'],poses[round(job['switch_sim_s']*72)],rtol=0,atol=1e-12)
        assert ctrl['stage2']['corrected_path_active']==corrected
        expected=(0.,0.)
        if ctrl['latest_received_id']>=0:
            r=received[ctrl['latest_received_id']]
            age=(ctrl['monotonic_ns']-r['received_monotonic_ns'])/1e9
            assert abs(age-ctrl['waypoint_age_wall_s'])<1e-12 and ctrl['valid']==(age<1.)
            nominal=pd(r['selected_waypoint_m']) if ctrl['valid'] else (0.,0.)
        else: nominal=(0.,0.); assert not ctrl['valid']
        np.testing.assert_allclose(nominal,[ctrl['v_m_s'],ctrl['w_rad_s']],rtol=0,atol=1e-12)
        if ctrl['valid'] and follower:
            expected,diag=follower.control(pose); valid_ticks+=1
            clamp=follower.path.s[-1]-follower.progress<.25
            assert clamp==ctrl['pure_pursuit']['endpoint_clamped']
            clamped+=int(clamp)
            x,y=diag['target_local_x_m'],diag['target_local_y_m']; d2=x*x+y*y
            kappa=2*y/d2 if d2>1e-24 else 0.
            curvature_ticks+=int(abs(kappa)>8. and not diag['endpoint_stop'])
            if not diag['endpoint_stop']:
                actual_w=float(records[tick]['w_rad_s'])
                expected,flags=control_command(c['phase4c_method'],kappa,previous_v,actual_w,alpha_value(c['plant_alpha']))
                for key,value in flags.items():
                    stored=ctrl['stage2'][key]
                    if value is None:assert stored is None
                    else:assert abs(value-stored)<1e-12
                for key in flag_counts: flag_counts[key]+=int(flags[key])
            graph_ticks+=int(corrected)
        actual=np.array([ctrl['commanded_v_m_s'],ctrl['commanded_w_rad_s']])
        assert ctrl['applied_v_m_s']==actual[0]
        assert ctrl['applied_w_rad_s']==float(records[tick]['w_rad_s'])
        assert ctrl['plant_actual_w_at_controller_rad_s']==float(records[tick]['w_rad_s'])
        max_command_error=max(max_command_error,float(np.max(np.abs(actual-expected))))
        previous_v=float(actual[0])
    assert max_command_error<1e-12
    # Independently recompute every swept interval with the existing geometry functions.
    max_clearance_error=0.; first_failure=None
    for i in range(1,len(records)):
        row=records[i]; cmd=[float(row[k]) for k in ('v_m_s','w_rad_s')]; causes=[]
        for box in c['obstacles']:
            lo,hi=obstacle_bounds(single_obstacle_config(c,box))
            g=swept_clearance(poses[i-1],*cmd,1/72,lo,hi,c['agent_radius_m'])
            stored=gaps[i]['obstacles'][box['id']]
            max_clearance_error=max(max_clearance_error,abs(g['lower_m']-stored['lower_m']))
            assert g['geometric_overlap']==stored['geometric_overlap']
            if g['geometric_overlap']:causes.append(box['id'])
        if corridor_arc_minimum(poses[i-1],*cmd,1/72,c['corridor'],c['agent_radius_m'])<0:
            causes.extend(corridor_breach_axes(poses[i-1],*cmd,1/72,c['corridor'],c['agent_radius_m']))
        if causes and first_failure is None:
            first_failure={'tick':i,'simulation_time_s':i/72,'pose':poses[i].tolist(),'causes':causes}
    assert max_clearance_error<1e-10
    if result['classification']=='SAFETY_FAILURE': assert first_failure is not None
    handoff=[h for h in handoffs if h['old_id']>=0]
    def distribution(key):return stats([h[key] for h in handoff if h[key] is not None])
    result.update(label=protocol()['label'],technical_validation='PASS',delay_s=delay,
        max_abs_y_m=float(np.abs(poses[:,1]).max()),failure=first_failure,
        final_pose=poses[-1].tolist(),final_goal_distance_m=s['final_goal_distance_m'],
        first_switch=handoffs[0] if handoffs else None,handoffs=handoff,
        handoff_statistics={k:distribution(k) for k in ('A_B_distance_m','A_B_abs_yaw_rad','staleness','abs_dw','observation_to_switch_wall_s')},
        last_three_fresh=handoffs[-3:] if result['classification']!='SUCCESS' else [],
        endpoint_clamped_ticks=clamped,endpoint_clamp_fraction=clamped/len(control),
        endpoint_clamp_valid_fraction=clamped/valid_ticks if valid_ticks else None,valid_pp_control_ticks=valid_ticks,
        curvature_saturated_ticks=curvature_ticks,curvature_saturated_fraction=curvature_ticks/len(control),
        received_interval_wall_s=stats(np.diff([r['received_monotonic_ns'] for r in received])/1e9),
        actual_delivery_delay_s=stats(delivery),warm_inference_ms=stats([r['inference_ms'] for r in received[1:]]),
        observation_to_ready_wall_s=stats([(r['ready_monotonic_ns']-r['observation_monotonic_ns'])/1e9 for r in received]),
        observation_to_release_wall_s=stats([(r['received_monotonic_ns']-r['observation_monotonic_ns'])/1e9 for r in received]),
        busy_skips=s['busy_observation_skips'],missed_captures=s['missed_capture_slots'],waypoint_timeout_episodes=s['waypoint_timeout_episodes'],
        receive_count=len(received),switch_count=len(events),unswitched_ids=sorted(set(r['id'] for r in received)-set(e['id'] for e in events)),
        pacing_error_s=stats([float(r['pacing_error_s']) for r in records]),
        navigation_wall_s=s['navigation_wall_seconds'],wall_simulation_ratio=s['navigation_wall_seconds']/s['simulation_duration_s'],
        max_pp_command_replay_error=max_command_error,max_swept_clearance_replay_error=max_clearance_error,
        verified_rgb_frames=len(frames),input_log_sha256={n:sha256_file(run/n) for n in
        ('scenario.json','provenance.json','requests.jsonl','received.jsonl','events.jsonl','controller.jsonl','agent_trajectory.csv','clearance.jsonl','model/inference.jsonl','plant.jsonl','stage2_graph.jsonl','observations.jsonl','summary.json','model/environment.json')})
    from collections import Counter
    for r in results:
        ctrl=control[round(r['evaluated_sim_s']*9)]
        status,stale,duration=decision(r,ctrl['latest_received_id'],ctrl['valid'])
        assert (status,stale)==(r['disposition'],r['stale_flag'])
        job=jobs[r['job_id']];i=round(job['switch_sim_s']*72);j=round(r['evaluated_sim_s']*72)
        measured=float(np.linalg.norm(np.diff(poses[i:j+1,:2],axis=0),axis=1).sum())
        assert abs(measured-r['movement_since_dispatch_m'])<1e-10
    for job in jobs.values():
        tick=round(job['switch_sim_s']*72);index=tick//8
        before_v=control[index-1]['commanded_v_m_s'] if index else 0.
        np.testing.assert_allclose(job['previous_command'],[before_v,float(records[tick]['w_rad_s'])],atol=1e-12,rtol=0)
        np.testing.assert_allclose(job['boundary'],poses[tick],atol=1e-12,rtol=0)
        np.testing.assert_allclose(job['world_xy'],worlds[job['id']],atol=1e-12,rtol=0)
    result.update(flag_counts=flag_counts,flag_fraction={k:v/len(control) for k,v in flag_counts.items()},
        graph={'calls':len(jobs),'dispositions':dict(Counter(r['disposition'] for r in results)),
            'terminal_unapplied':sum(r['event']=='TERMINAL_UNAPPLIED' for r in graph_log),
            'correction_abs_dw':stats([abs(r['after_vw'][1]-r['before_vw'][1]) for r in graph_log if r['event']=='APPLIED_COMMAND']),
            'solver_time_s':stats([r['solver']['solver_wall_s'] for r in results if 'solver' in r]),
            'processing_time_s':stats([r['processing_wall_s'] for r in results]),
            'queue_wait_s':stats([r['queue_wait_s'] for r in results]),
            'movement_during_processing_and_wait_m':stats([r['movement_since_dispatch_m'] for r in results]),
            'independent_nonconverged':sum(not r['solver']['success'] for r in results if 'solver' in r),
            'independent_constraint_failure':sum(not r['solver']['constraints_satisfied'] or not r['solver']['exact_certificate_pass'] for r in results if 'solver' in r),
            'stale_flags':sum(r['stale_flag'] for r in results),'corrected_control_ticks':graph_ticks,
            'corrected_valid_tick_fraction':graph_ticks/valid_ticks if valid_ticks else None,
            'corrected_fresh_fraction':len(applications)/len(events) if events else None})
    result['switch_sign_reversals']=sum(h['w_sign_flip'] for h in handoff)
    return result
