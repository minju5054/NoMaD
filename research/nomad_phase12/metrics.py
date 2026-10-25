"""Phase8 saved-data validator adapted only for the three opt-in transition kernels.
Original validator and original methods remain unchanged.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from nomad_isaac.async_report import rows,stats
from nomad_isaac.common import integrate_se2,local_to_world,sha256_file
from nomad_isaac.clearance import swept_clearance,obstacle_bounds,single_obstacle_config
from nomad_isaac.topomap import candidate_range,select_subgoal
from nomad_phase0.chunk_report import trace
from nomad_phase0.chunk_execution import protocol as follower_protocol
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from nomad_phase4c.plant import control_command
from nomad_phase3_stage2.execution import decision
from nomad_phase6.metrics import compare_selection,mechanisms
from nomad_phase1.s1 import VisibilityGate
from nomad_phase2.config import place
from nomad_phase9.intent import intention,splice
from nomad_phase8.execution import select
from nomad_phase8.config import protocol
from nomad_phase8.request import rtc_target
from .methods import NEW,PATH_BASELINES,GF,TransitionState,freshest
from .gf_worker import validate_job
from .config import protocol as phase12_protocol

def baseline_audit(run,run_id,offset,delay,*,transition_factory=TransitionState,path_baselines=PATH_BASELINES):
    run=Path(run);summary=json.loads((run/'summary.json').read_text());c=summary['scenario'];phase=c['overnight_phase'];p=protocol(phase)
    prov=json.loads((run/'provenance.json').read_text());env=json.loads((run/'model/environment.json').read_text())
    assert prov['overnight_phase']==phase and prov['overnight_method']==c['overnight_method']
    assert c['run_id']==run_id and c['seed_offset']==offset and offset==int(run_id[-2:])*10000
    assert c['timeout_sim_s']==90 and c['execution_v_max_m_s']==.3 and c['plant_alpha']=='inf'
    assert (c['observation_hz'],c['controller_hz'],c['integration_hz'])==(4,9,72)
    assert prov['source_scenario_sha256']==p['scenario_sha256'] and sha256_file(Path(c['topomap_manifest']))==p['topomap_manifest_sha256']
    assert env['checkpoint_sha256']==p['checkpoint_sha256'] and env['coverage']['parameter_coverage']==1.
    assert json.loads((run/'overnight_protocol.json').read_text())==p
    rec,poses=trace(run);ctrl=rows(run/'controller.jsonl');events=rows(run/'events.jsonl');received=rows(run/'received.jsonl')
    requests=rows(run/'requests.jsonl');inference=rows(run/'model/inference.jsonl');gaps=rows(run/'clearance.jsonl');plant=rows(run/'plant.jsonl')
    assert len(rec)==len(gaps)==len(plant) and len(requests)==len(received)==len(inference)
    assert [round(x['simulation_time_s']*72) for x in ctrl]==list(range(0,len(rec)-1,8))
    err=0.
    for tick in range(1,len(rec)):
        command=ctrl[(tick-1)//8];v,w=command['commanded_v_m_s'],command['commanded_w_rad_s']
        assert [float(rec[tick][k]) for k in ('v_m_s','w_rad_s')]==[v,w]
        assert plant[tick]['actual_v_m_s']==v and plant[tick]['actual_w_rad_s']==w
        err=max(err,float(np.max(abs(integrate_se2(poses[tick-1],v,w,1/72)-poses[tick]))))
    assert err<1e-12
    observations=[o for o in rows(run/'observations.jsonl') if 'observation_id' in o]
    obs={o['observation_id']:o for o in observations};frames={}
    for i,o in obs.items():
        with Image.open(run/o['rgb_file']) as im:frame=np.asarray(im)
        assert hashlib.sha256(frame.tobytes()).hexdigest()==o['frame_sha256'];frames[i]=frame
    spawn=json.loads((run/'dynamic/spawn.json').read_text()) if (run/'dynamic/spawn.json').exists() else None
    placement=json.loads((run/'dynamic/placement.json').read_text()) if (run/'dynamic/placement.json').exists() else None
    publications=rows(run/'overnight_oracle.jsonl');publication=publications[0] if publications else None
    assert len(publications)<=1
    if c.get('phase10b_no_obstacle'):
        assert phase==9 and c['overnight_method'] in ('CURV','GRAPH-v6')
        assert c['obstacles']==[] and 'dynamic_obstacle' not in c
        assert spawn is None and placement is None and publication is None
        assert all('oracle_information' not in o and 'dynamic' not in o for o in observations)
    elif phase==9:
        gate=VisibilityGate();available=None
        for o in observations:
            expected=gate.observe(o);assert o['oracle_information']==expected
            if expected['geometry_available'] and available is None:available=o
            if spawn:assert o['dynamic']['active']==(round(o['observation_sim_s']*72)>=spawn['tick'])
        if publication:
            assert available and publication['gate']==available['oracle_information']
            assert publication['publication_monotonic_ns']>=available['capture_end_monotonic_ns']
            assert publication['obstacle']==spawn['obstacle']
        if placement:
            tick=placement['decision_tick'];expected=place(c,poses[tick])
            assert not any(2<=x<=2.1 for x in poses[:tick,0]) and 2<=poses[tick,0]<=2.1
            assert placement['status']==expected['status']
            np.testing.assert_array_equal(placement['obstacle']['center_xy_m'],expected['obstacle']['center_xy_m'])
            assert expected['left_wall_gap_m']>=.4-1e-12 and expected['right_wall_gap_m']>=.4-1e-12
    def public_at(ns):
        public={**c,'obstacles':list(c['obstacles'])};public.pop('dynamic_obstacle',None)
        if publication and publication['publication_monotonic_ns']<=ns:public['obstacles'].append(publication['obstacle'])
        return public
    manifest=json.loads(Path(c['topomap_manifest']).read_text());closest=0;worlds={};samples={};delivery=[];prefix=[];last_receive=-1
    for k,(q,r,m) in enumerate(zip(requests,received,inference)):
        assert q['id']==r['id']==m['id']==k and q['seed']==r['seed']==m['seed']==101+offset+2*k
        assert r['ddpm_seed']==m['ddpm_seed']==q['seed']+1 and q['request_submit_monotonic_ns']>last_receive
        last_receive=r['received_monotonic_ns'];ids=q['history_observation_ids']
        assert len(ids)==4 and np.all(np.diff(ids)>0)
        assert hashlib.sha256(np.stack([frames[i] for i in ids]).tobytes()).hexdigest()==m['history_sha256']
        t=m['topomap'];a,b=candidate_range(closest,len(manifest['nodes'])-1)
        assert (a,b)==(t['candidate_start'],t['candidate_end_inclusive']);closest,subgoal,_=select_subgoal(t['distances'],a)
        assert (closest,subgoal)==(t['closest_node'],t['selected_subgoal_id']) and m['goal_sha256']==manifest['nodes'][subgoal]['rgb_sha256']
        assert t['diffusion_steps']==10 and t['diffusion_passes']==1
        np.testing.assert_allclose(poses[round(q['observation_sim_s']*72)],q['observation_pose'],atol=1e-12,rtol=0)
        chain=[r[n] for n in ('pose_sample_monotonic_ns','observation_monotonic_ns','capture_end_monotonic_ns','request_submit_monotonic_ns','request_send_monotonic_ns','inference_start_monotonic_ns','inference_end_monotonic_ns','host_output_ready_monotonic_ns','persistence_end_monotonic_ns','packet_received_monotonic_ns','release_monotonic_ns')]
        assert np.all(np.diff(np.array(chain,dtype=np.int64))>=0)
        assert r['release_monotonic_ns']==r['received_monotonic_ns'] and r['release_deadline_monotonic_ns']==r['packet_received_monotonic_ns']+round(delay*1e9)
        assert r['release_monotonic_ns']>=r['release_deadline_monotonic_ns'];delivery.append((r['release_monotonic_ns']-r['packet_received_monotonic_ns'])/1e9)
        with np.load(run/f'model/raw/{k:04d}.npz') as raw,np.load(run/f'model/derived/{k:04d}.npz') as derived:
            z=raw['normalized_diffusion'];metric=derived['metric'];assert z.shape==metric.shape==(8,8,2) and np.isfinite(z).all() and np.isfinite(metric).all()
            cumulative=np.cumsum((z+1)/2*np.array([7.5,8.])+np.array([-2.5,-4.]),axis=1).astype(np.float32)
            np.testing.assert_array_equal(cumulative,derived['cumulative']);np.testing.assert_array_equal(cumulative*np.float32(.05),metric)
            np.testing.assert_array_equal(metric[0,2],r['selected_waypoint_m']);samples[k]=metric.copy()
        worlds[k]=local_to_world(samples[k][0],np.array(q['observation_pose']))
        np.testing.assert_allclose(worlds[k],r['chunk']['world_xy_m'],atol=1e-12,rtol=0)
        if c['overnight_method'].startswith('RTC'):
            target=q['rtc_target'];assert r['rtc_target']==target
            if target['d']:
                errors=np.linalg.norm(samples[k][:,:target['d']]-np.array(target['target_local_xy_m'])[None,:target['d']],axis=2)
                prefix.extend(errors.ravel().tolist())
                if c['overnight_method']=='RTC-hard':assert errors.max()<=1e-6
    graph=rows(run/'stage2_graph.jsonl');jobs={j['job_id']:j for j in graph if j['event']=='SUBMIT'}
    results=[r for r in graph if r['event']=='RESULT'];accepted={r['applied_tick']:r for r in results if r['disposition']=='ACCEPTED'}
    assert len(jobs)==(len(events) if c['phase4c_method']=='GRAPH' else 0)
    apps=rows(run/'phase6_applications.jsonl');app_at={a['tick']:a for a in apps};ev_at={round(e['application_sim_s']*72):e for e in events}
    assert len(apps)==len(ev_at)+len(accepted) and set(app_at)==set(ev_at)|set(accepted)
    state=transition_factory(c['phase12_method']) if c['phase12_method'] in path_baselines else None
    follower=None;previous_v=0.;command_error=0.;selections=[];graph_ticks=0;valid_ticks=0;clamps=0;curvatures=[]
    for j,control in enumerate(ctrl):
        tick=j*8;b=poses[tick];event=ev_at.get(tick)
        if event:
            np.testing.assert_array_equal(event['agent_pose_at_switch'],b)
            assert control['monotonic_ns']>=event['received_monotonic_ns'] and (j==0 or ctrl[j-1]['monotonic_ns']<event['received_monotonic_ns'])
            world_samples=np.array([local_to_world(x,np.asarray(event['observation_pose'])) for x in samples[event['id']]])
            xy,detail=freshest(world_samples,b) if c['phase12_method']==GF else state.switch(world_samples,b,event['id'],received[event['id']]['received_monotonic_ns'],control['monotonic_ns'])
            meta=event['phase12'];assert not meta['oracle_used'] and meta['method']==c['phase12_method']
            compare_selection(detail,meta['detail']);selections.append(detail)
            np.testing.assert_allclose(meta['applied_initial_world_xy'],xy,rtol=0,atol=1e-12)
            try:follower=PurePursuit(xy,follower_protocol()['follower'])
            except ValueError:follower=None
        if tick in accepted:
            result=accepted[tick];assert not event and result['id']==control['waypoint_id'] and result['result_received_ns']<=control['monotonic_ns']
            if j:assert ctrl[j-1]['monotonic_ns']<result['result_received_ns']
            assert result['solver']['success'] and result['solver']['constraints_satisfied']
            assert result['geometry_free_assert'] and result['solver']['certificate_scope']=='NONE_ORACLE_FREE' and result['solver']['exact_certificate_pass'] is None
            follower=PurePursuit(result['applied_world_xy'],follower_protocol()['follower'])
        if tick in app_at:
            a=app_at[tick];np.testing.assert_array_equal(a['pose'],b)
            if follower:np.testing.assert_allclose(a['world_xy'],follower.path.points,atol=1e-12,rtol=0)
        command=(0.,0.)
        if control['latest_received_id']>=0:
            age=(control['monotonic_ns']-received[control['latest_received_id']]['received_monotonic_ns'])/1e9
            assert control['valid']==(age<1.) and abs(age-control['waypoint_age_wall_s'])<1e-12
        else:assert not control['valid']
        ensemble_diag=None
        if c['phase12_method']=='TEMPORAL-ENSEMBLE':
            ensemble_diag,ensemble=state.ensemble.control(b,control['monotonic_ns'])
            compare_selection(ensemble,control['phase12_ensemble'])
            if tick in app_at:compare_selection(ensemble['components'],app_at[tick]['ensemble_components'])
        if control['valid']:
            diag=ensemble_diag if c['phase12_method']=='TEMPORAL-ENSEMBLE' else follower.control(b)[1] if follower else None
            if diag is not None:
                valid_ticks+=1;graph_ticks+=int(control['stage2']['corrected_path_active'])
                if not diag['endpoint_stop']:
                    x,y=diag['target_local_x_m'],diag['target_local_y_m'];d2=x*x+y*y;k=2*y/d2 if d2>1e-24 else 0.
                    command,flags=control_command('CURV',k,previous_v,float(rec[tick]['w_rad_s']),float('inf'));curvatures.append(abs(k))
                    np.testing.assert_allclose([control['pure_pursuit'][x] for x in ('target_x_m','target_y_m')],[diag[x] for x in ('target_x_m','target_y_m')],atol=1e-12,rtol=0)
                clamps+=int(bool(control['pure_pursuit']['endpoint_clamped']))
        actual=[control['commanded_v_m_s'],control['commanded_w_rad_s']];command_error=max(command_error,float(np.max(abs(np.array(actual)-command))));previous_v=actual[0]
    assert command_error<1e-12
    for result in results:
        tick=round(result['evaluated_sim_s']*72);control=ctrl[tick//8]
        assert decision(result,control['latest_received_id'],control['valid'])[0]==result['disposition']
    for job in jobs.values():
        tick=round(job['switch_sim_s']*72);event=ev_at[tick];np.testing.assert_array_equal(job['boundary'],poses[tick])
        np.testing.assert_allclose(job['world_xy'],event['phase12']['applied_initial_world_xy'],atol=1e-12,rtol=0)
        validate_job({k:v for k,v in job.items() if k!='event'})
        previous=[r for r in results if r['disposition']=='ACCEPTED' and r['applied_tick']<tick]
        expected=previous[-1]['applied_world_xy'] if previous else None
        assert job['previous_xy']==expected
        before=ctrl[tick//8-1] if tick else None
        expected_command=[before['commanded_v_m_s'],plant[tick]['actual_w_rad_s']] if before else [0.,0.]
        np.testing.assert_allclose(job['previous_command'],expected_command,atol=1e-12,rtol=0)
    # RTC target must match the applied OLD path at the actual observation snapshot.
    if c['overnight_method'].startswith('RTC'):
        for q in requests:
            snap=q['rtc_snapshot'];tick=snap['tick']
            assert tick==round(q['observation_sim_s']*72) and snap['pose']==q['observation_pose']
            assert snap['snapshot_monotonic_ns']<=q['observation_monotonic_ns']
            old_apps=[a for a in apps if a['monotonic_ns']==snap.get('path_application_monotonic_ns')]
            old=old_apps[-1] if old_apps else None
            assert not old or old['monotonic_ns']<=snap['snapshot_monotonic_ns']
            if old and snap['old_world_xy'] is not None:
                np.testing.assert_array_equal(snap['old_world_xy'],old['world_xy'])
                assert snap['applied_id']==old['id']
            compare_selection(rtc_target(snap),q['rtc_target'])
    # Collision evaluator includes all physical geometry after spawn, irrespective of oracle visibility.
    minimum={};overlap=False;corridor=False;margin=0.;wall=[];clear_error=0.
    dynamic_gaps=rows(run/'dynamic/clearance.jsonl') if spawn else [];dynamic_at=0
    for tick in range(1,len(rec)):
        v,w=[float(rec[tick][k]) for k in ('v_m_s','w_rad_s')];boxes=list(c['obstacles'])
        if spawn and tick>=spawn['tick']:boxes.append(spawn['obstacle'])
        unsafe=False
        for box in boxes:
            lo,hi=obstacle_bounds(single_obstacle_config(c,box));spawning=spawn and box['id']=='DynamicObstacle' and tick==spawn['tick']
            start=poses[tick] if spawning else poses[tick-1];dt=0. if spawning else 1/72
            g=swept_clearance(start,v,w,dt,lo,hi,c['agent_radius_m']);minimum[box['id']]=min(minimum.get(box['id'],float('inf')),g['lower_m'])
            overlap|=g['geometric_overlap'];unsafe|=g['lower_m']<.02
            stored=dynamic_gaps[tick-spawn['tick']] if box['id']=='DynamicObstacle' else gaps[tick]['obstacles'][box['id']]
            clear_error=max(clear_error,abs(g['lower_m']-stored['lower_m']))
        gap=corridor_arc_minimum(poses[tick-1],v,w,1/72,c['corridor'],c['agent_radius_m']);wall.append(gap);corridor|=gap<0
        if unsafe:margin+=1/72
    assert clear_error<1e-10
    goal=bool(summary['goal_entry']);reason=summary['termination_reason'];placement_invalid=reason=='placement_invalid'
    classification='PLACEMENT_INVALID' if placement_invalid else 'SAFETY_FAILURE' if overlap or corridor else 'SUCCESS' if goal else 'STUCK' if reason in ('simulation_timeout','navigation_wall_timeout') else 'CONSERVATIVE_CONTACT_STOP'
    duration=(len(rec)-1)/72;distance=float(np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1).sum())
    stop=sum(abs(float(x['v_m_s']))<1e-12 for x in rec[1:])/72
    side=None
    if spawn:
        box=spawn['obstacle'];front=box['center_xy_m'][0]-.175;rear=box['center_xy_m'][0]+.175
        mask=(poses[:,0]>=front)&(poses[:,0]<=rear);ys=poses[mask,1]-box['center_xy_m'][1]
        if poses[:,0].max()>rear+c['agent_radius_m']:side='+Y' if len(ys) and np.all(ys>0) else '-Y' if len(ys) and np.all(ys<0) else 'MIXED'
    result=dict(classification=classification,technical_validation='PASS',success=classification=='SUCCESS',technical_failure=False,goal_entry=goal,goal_time_s=duration if goal else None,termination_reason=reason,
        duration_s=duration,distance_m=distance,stop_time_s=stop,mean_speed_m_s=distance/duration if duration else 0.,geometric_overlap=bool(overlap),corridor_violation=bool(corridor),minimum_obstacle_clearance_m=min(minimum.values()) if minimum else None,
        obstacle_minima=minimum,minimum_corridor_clearance_m=min(wall) if wall else None,margin_violation_s=margin,dynamic_passage_side=side,
        max_pose_replay_error=err,max_pp_command_replay_error=command_error,max_swept_clearance_replay_error=clear_error,execution_git_sha=prov['git_sha'],max_abs_y_m=float(abs(poses[:,1]).max()),
        endpoint_clamp_fraction=clamps/len(ctrl),curvature_saturated_fraction=float(np.mean(np.array(curvatures)>8)) if curvatures else None,
        inference_ms=stats([m['inference_ms'] for m in inference[1:]]),rtc_prefix_error_m=stats(prefix),actual_delivery_delay_s=stats(delivery),selection=dict(switches=len(selections),replacements=sum(x['selected_sample']!=0 for x in selections),all_unsafe=0,sample_index_counts=dict(Counter(x['selected_sample'] for x in selections))),
        graph=dict(calls=len(jobs),dispositions=dict(Counter(x['disposition'] for x in results)),independent_nonconverged=sum(not x['solver']['success'] for x in results if 'solver' in x),solver_time_s=stats([x['solver']['solver_wall_s'] for x in results if 'solver' in x]),solver_samples_s=[x['solver']['solver_wall_s'] for x in results if 'solver' in x],corrected_distance_fraction=float(sum(np.linalg.norm(poses[t,:2]-poses[t-1,:2]) for t in range(1,len(poses)) if ctrl[(t-1)//8]['stage2']['corrected_path_active'])/distance) if distance else None,corrected_valid_tick_fraction=graph_ticks/valid_ticks if valid_ticks else None),spawn=spawn,oracle_publication=publication)
    for name,g in minimum.items():result[name+'_minimum_clearance_m']=g
    result['mechanisms']=phase12_mechanisms(run,result['success'],c['phase12_method'])
    paths=[f for name in ('*.json','*.jsonl','*.csv','model/*.json','model/*.jsonl','model/raw/*.npz','model/derived/*.npz','dynamic/*.json','dynamic/*.jsonl') for f in run.glob(name)]
    result['input_log_sha256']={str(f.relative_to(run)):sha256_file(f) for f in paths if f.is_file()}
    return result


def phase12_mechanisms(run,success,method):
    if method!='TEMPORAL-ENSEMBLE':return mechanisms(run,success)
    from nomad_phase6.metrics import application_measure,summarize_window
    run=Path(run);records,poses=trace(run);times=np.array([float(r['simulation_time_s']) for r in records])
    controls=rows(run/'controller.jsonl');gaps=rows(run/'clearance.jsonl');apps=rows(run/'phase6_applications.jsonl');measured=[]
    for a in apps:
        comps=a['ensemble_components'];parts=[application_measure({**a,'world_xy':c['world_xy']},poses[a['tick']]) for c in comps]
        weights=[c['weight'] for c in comps]
        heading=sum(w*p['heading_abs_rad'] for w,p in zip(weights,parts)) if parts and all(p['heading_abs_rad'] is not None for p in parts) else None
        distance=sum(w*p['cross_track_m'] for w,p in zip(weights,parts)) if parts else None
        measured.append(dict(time_s=a['simulation_time_s'],kind=method,id=a['id'],heading_abs_rad=heading,cross_track_m=distance,
                             heading_invalid_reason=None if heading is not None else 'no_or_short_component_tangent',component_count=len(parts)))
    curvature=[(c['simulation_time_s'],abs(c['stage2']['kappa_pp'])) for c in controls if c['pure_pursuit']['stop_reason'] is None and c['stage2']['kappa_pp'] is not None]
    return dict(full=summarize_window(measured,curvature,poses,times,gaps,0.,times[-1]),
        failure_last3s=None if success else summarize_window(measured,curvature,poses,times,gaps,max(0.,times[-1]-3.),times[-1]),
        applications=measured,scope='Phase6 component projection metrics weighted at switch; no unique ensemble path')


def audit(run,run_id,offset,delay):
    from nomad_phase8.metrics import audit as original_audit
    run=Path(run);c=json.loads((run/'scenario.json').read_text());p=phase12_protocol();m=c['phase12_method']
    assert m in p['methods'] and 25<=int(run_id[-2:])<=34 and delay==.75
    assert json.loads((run/'phase12_protocol.json').read_text())==p
    assert json.loads((run/'provenance.json').read_text())['phase12_method']==m
    r=(baseline_audit if m in NEW else original_audit)(run,run_id,offset,delay)
    ctrl=rows(run/'controller.jsonl');times=np.array([x['simulation_time_s'] for x in ctrl]);dt=np.maximum(0.,np.r_[times[1:],r['duration_s']]-times)
    active=np.array([x['pure_pursuit']['stop_reason'] is None for x in ctrl]);slow=np.array([(x['stage2'].get('v_target_m_s') or .3)<.2-1e-12 for x in ctrl])
    r['curv_slow_time_fraction']=float(dt[active&slow].sum()/dt[active].sum()) if dt[active].sum() else None
    r['phase12_method']=m
    if m=='TEMPORAL-ENSEMBLE':
        counts=[x['phase12_ensemble']['chunk_count'] for x in ctrl if x['valid'] and x['phase12_ensemble']['chunk_count']]
        r['ensemble_mean_chunks']=float(np.mean(counts)) if counts else None
    if m in NEW:
        assert not rows(run/'overnight_oracle.jsonl')
        if m in PATH_BASELINES:assert not rows(run/'stage2_graph.jsonl')
        assert all(e['phase12']['oracle_used'] is False for e in rows(run/'events.jsonl'))
    r['input_log_sha256']['phase12_protocol.json']=sha256_file(run/'phase12_protocol.json')
    return r
