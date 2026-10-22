"""Independent replay, visibility/provenance checks and saved-pose feasibility."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from nomad_isaac.async_report import rows, stats
from nomad_isaac.common import ROOT, integrate_se2, local_to_world, sha256_file, write_json
from nomad_isaac.clearance import corridor_clearance, swept_clearance, obstacle_bounds, single_obstacle_config
from nomad_isaac.topomap import candidate_range, select_subgoal
from nomad_phase0.chunk_execution import protocol as pp_protocol
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from .config import place, select, protocol
from .execution import speed_command


def feasibility(run,states,box,config,out):
    from nomad_phase0.actual_pose_recovery import action_sets, PROTOCOL
    from nomad_phase0.scenario_feasibility import Scene, search, InvalidScenario
    p=json.loads(PROTOCOL.read_text()); result={}
    for label,state in states.items():
        if state is None:
            result[label]={'status':'NO_ACTUAL_BOUNDARY'};continue
        c=copy.deepcopy(config);c.update(start_pose=state['pose'],dynamic_obstacle=box)
        try:scene=Scene(c,'active')
        except InvalidScenario as exc:
            result[label]={m:{'status':'INVALID_START','reason':str(exc)} for m in ('B0','B1')};continue
        result[label]={}
        for method,actions in action_sets(p).items():
            if method=='B2':continue
            setting={**p['search'],'primitives_vw':actions,'minimum_v_m_s':0.}
            r=search(scene,setting,side=None)
            write_json(out/f'feasibility_{label}_{method}.json',{'state':state,'geometry':c,'settings':setting,**r})
            result[label][method]={k:v for k,v in r.items() if k!='witness'}
            if r['witness']:
                w=r['witness'];result[label][method]['witness_summary']={k:w[k] for k in ('path_duration_s','distance_m','minimum_obstacle_clearance_m','goal_distance_m')}
    return result


def audit(run,out,do_feasibility=True):
    out.mkdir(exist_ok=False)
    summary=json.loads((run/'summary.json').read_text());config=summary['scenario']
    prov=json.loads((run/'provenance.json').read_text());assert not prov['git_status']
    assert json.loads((run/'model/environment.json').read_text())['checkpoint_sha256']==protocol()['protected_sha256'][str(ROOT.parent/'artifacts/checkpoints/nomad.pth')]
    with (run/'agent_trajectory.csv').open() as f:trace=list(csv.DictReader(f))
    poses=np.array([[float(r[k]) for k in ('x_m','y_m','yaw_rad')] for r in trace])
    vw=np.array([[float(r[k]) for k in ('v_m_s','w_rad_s')] for r in trace])
    pose_error=max((float(np.max(abs(integrate_se2(poses[i-1],*vw[i],1/72)-poses[i]))) for i in range(1,len(poses))),default=0.)
    assert pose_error<1e-12
    controls=rows(run/'controller.jsonl');events=rows(run/'events.jsonl');received=rows(run/'received.jsonl')
    req=rows(run/'requests.jsonl');inf=rows(run/'model/inference.jsonl')
    observations=[r for r in rows(run/'observations.jsonl') if 'observation_id' in r]
    decisions=rows(run/'phase2_decisions.jsonl');graph=rows(run/'phase2_graph.jsonl');public=rows(run/'phase2_oracle.jsonl')
    assert len(req)==len(received)==len(inf)
    frames={}
    for o in observations:
        frame=np.array(Image.open(run/o['rgb_file']))
        assert frame.shape==(240,320,3) and hashlib.sha256(frame.tobytes()).hexdigest()==o['frame_sha256']
        frames[o['observation_id']]=frame
    closest=0;subgoal=None;delays=[]
    for i,(r,n) in enumerate(zip(received,inf)):
        assert r['id']==n['id']==i and r['seed']==101+config['seed_offset']+2*i and n['ddpm_seed']==r['seed']+1
        history=np.stack([frames[j] for j in r['history_observation_ids']])
        assert hashlib.sha256(history.tobytes()).hexdigest()==r['history_sha256']==n['history_sha256']
        t=n['topomap'];a,b=candidate_range(closest,20)
        assert (a,b)==(t['candidate_start'],t['candidate_end_inclusive'])
        close,chosen,_=select_subgoal(t['distances'],a);assert (close,chosen)==(t['closest_node'],t['selected_subgoal_id'])
        assert t['diffusion_steps']==10 and t['diffusion_passes']==1
        closest,subgoal=close,chosen
        delay=(r['release_monotonic_ns']-r['packet_received_monotonic_ns'])/1e9
        assert delay+1e-9>=r['additional_delivery_delay_s']==prov['uniform_delivery_delay_s']
        assert r['received_monotonic_ns']==r['release_monotonic_ns']
        delays.append(delay)
        np.testing.assert_array_equal(poses[round(r['observation_sim_s']*72)],r['observation_pose'])
    visible=[o for o in observations if o.get('dynamic',{}).get('visible')]
    first_visible=visible[0] if visible else None;available=None
    if first_visible:
        later=[o for o in observations if o['observation_id']>first_visible['observation_id']]
        available=later[0] if later else None
        if available:
            gate=available['oracle_information'];assert gate['geometry_available']
            assert gate['available_from']['observation_id']==available['observation_id']
            if public:assert public[0]['publication_monotonic_ns']>=available['capture_end_monotonic_ns']
    e_by_tick={round(e['application_sim_s']*72):e for e in events};assert len(e_by_tick)==len(events)
    follower=None;active=None;previous=[0.,0.];pp_error=0.;command_trace_error=0.;last_control=None
    for c in controls:
        tick=round(c['simulation_time_s']*72);assert tick%8==0
        if tick in e_by_tick:
            active=e_by_tick[tick];np.testing.assert_array_equal(poses[tick],active['agent_pose_at_switch'])
            xy=active['phase2']['world_xy_m'];follower=PurePursuit(xy,pp_protocol()['follower'])
            with np.load(run/f"model/derived/{active['id']:04d}.npz",allow_pickle=False) as data:
                native=local_to_world(data['metric'][active['phase2']['selected_sample']],np.array(active['observation_pose']))
            if not active['phase2']['graph_applied']:np.testing.assert_allclose(xy,native,rtol=0,atol=1e-12)
        age=None if active is None else (c['monotonic_ns']-active['received_monotonic_ns'])/1e9
        valid=age is not None and age<1.
        assert valid==c['valid']
        source=c['applied_command_source']
        if not valid or source=='invalid_chunk':expected=(0.,0.)
        elif c['graph_wait']:expected=previous
        else:
            expected,diag=follower.control(poses[tick])
            if c['variable_speed'] and not diag['endpoint_stop']:
                x,y=diag['target_local_x_m'],diag['target_local_y_m'];k=2*y/(x*x+y*y) if x*x+y*y>=1e-24 else 0.
                expected,flags=speed_command(k,previous[0])
                for flag,value in flags.items():assert c['pure_pursuit'][flag]==value
        actual=[c['applied_v_m_s'],c['applied_w_rad_s']]
        pp_error=max(pp_error,float(np.max(abs(np.array(expected)-actual))))
        end=min(tick+8,len(poses)-1)
        if end>tick:command_trace_error=max(command_trace_error,float(np.max(abs(vw[tick+1:end+1]-actual))))
        previous=actual
    assert pp_error<1e-12 and command_trace_error==0
    static=rows(run/'clearance.jsonl');assert len(static)==len(poses)
    exact_wall=[]
    for i,p in enumerate(poses):
        start=poses[max(0,i-1)];dt=1/72 if i else 0.
        gap=corridor_clearance(start,p,*vw[i],dt,config['corridor'],.09)
        assert abs(gap-static[i]['corridor_lower_m'])<1e-12
        exact_wall.append(corridor_arc_minimum(start,*vw[i],dt,config['corridor'],.09))
    spawn=summary.get('dynamic_obstacle',{}).get('spawn');dynamic=[];states={};first_fresh=None;first_B=None
    if spawn:
        check=place(config,spawn['pose']);assert check['obstacle']['center_xy_m']==spawn['obstacle']['center_xy_m']
        np.testing.assert_array_equal(poses[spawn['tick']],spawn['pose'])
        render=json.loads((run/'dynamic_render_update.json').read_text());assert render['obstacle']==spawn['obstacle']
        lower,upper=obstacle_bounds(single_obstacle_config(config,spawn['obstacle']))
        dynamic=rows(run/'dynamic/clearance.jsonl')
        for j,row in enumerate(dynamic):
            i=spawn['tick']+j;dt=0. if j==0 else 1/72
            gap=swept_clearance(poses[i if j==0 else i-1],*vw[i],dt,lower,upper,.09,.02)
            assert abs(row['lower_m']-gap['lower_m'])<1e-12 and row['geometric_overlap']==gap['geometric_overlap']
        if first_visible:
            first_fresh=next((r for r in received if any(h['active'] and h['visible'] for h in r['history_dynamic'])),None)
            first_B=next((e for e in events if first_fresh and e['id']==first_fresh['id']),None)
        states={'spawn':{'pose':spawn['pose'],'tick':spawn['tick']},
                'first_visible_B':{'pose':first_B['agent_pose_at_switch'],'tick':round(first_B['application_sim_s']*72)} if first_B else None}
    for d in decisions:
        if 'sample0_unsafe' not in d:continue
        c=copy.deepcopy(config);c['obstacles']=[]
        if d['geometry_available']:
            assert available and d['decision_ns']>=public[0]['publication_monotonic_ns'];c['obstacles']=[spawn['obstacle']]
        with np.load(run/f"model/derived/{d['id']:04d}.npz",allow_pickle=False) as data:
            r=received[d['id']];world=np.array([local_to_world(x,np.array(r['observation_pose'])) for x in data['metric']])
        recomputed=select(world,d['boundary'],c)
        if config['phase2_method']=='M0':recomputed['selected_sample']=0
        for k in ('sample0_unsafe','selected_sample','all_unsafe'):assert d[k]==recomputed[k]
    outcome=summary['termination_reason'];overlap=any(r['geometric_overlap'] for r in dynamic);corridor=min(exact_wall)<0
    status=('PLACEMENT_INVALID' if outcome=='placement_invalid' else 'SAFETY_FAILURE' if overlap or corridor or outcome=='conservative_contact_stop'
            else 'SUCCESS' if summary['goal_entry'] else 'STUCK' if outcome=='simulation_timeout' else 'TECHNICAL_FAILURE')
    elapsed=summary['simulation_duration_s'];movement=np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1)
    changes=[abs(e['actual_command_delta'][1]) for e in events if e['actual_command_before']!=[0.,0.]]
    completed_graph=[g for g in graph if g.get('kind')=='result'];dec=[d for d in decisions if 'sample0_unsafe' in d]
    boundary=None
    if first_fresh:
        boundary={'fresh_id':first_fresh['id'],'A':first_fresh['observation_pose'],'t_obs':first_fresh['observation_sim_s'],
            't_ready_ns':first_fresh['ready_monotonic_ns'],'t_packet_ns':first_fresh['packet_received_monotonic_ns'],
            't_release_ns':first_fresh['release_monotonic_ns'],'B':first_B['agent_pose_at_switch'] if first_B else None,
            't_switch':first_B['application_sim_s'] if first_B else None,'status':'APPLIED' if first_B else 'PRE_HANDOFF_FAILURE'}
        if first_B:
            a=round(first_fresh['observation_sim_s']*72);b=round(first_B['application_sim_s']*72)
            boundary.update(old_distance_m=float(movement[a:b].sum()),yaw_change_rad=float((poses[b,2]-poses[a,2]+np.pi)%(2*np.pi)-np.pi),
                            observation_to_switch_s=first_B['application_sim_s']-first_fresh['observation_sim_s'])
    result={'technical_validation':'PASS','scope':protocol()['safety_scope'],'run':str(run),'execution_git_sha':prov['git_sha'],
        'classification':status,'success':status=='SUCCESS','goal_entry':summary['goal_entry'],'geometric_overlap':overlap,
        'corridor_intrusion':corridor,'conservative_contact_stop':outcome=='conservative_contact_stop','timeout':status=='STUCK',
        'termination_reason':outcome,'duration_s':elapsed,'goal_time_s':elapsed if summary['goal_entry'] else None,
        'stop_s':float(np.count_nonzero(np.abs(vw[1:,0])<1e-12)/72),'distance_m':float(movement.sum()),
        'minimum_clearance_m':min((r['lower_m'] for r in dynamic),default=None),
        'margin_violation_s':sum(r['end_sim_s']-r['start_sim_s'] for r in dynamic if r['lower_m']<.02),
        'minimum_corridor_m':min(exact_wall),'y_std_m':float(np.std(poses[:,1])),'max_abs_y_m':float(abs(poses[:,1]).max()),
        'passage':summary.get('dynamic_obstacle',{}).get('evaluation',{}).get('passage') if spawn else None,
        'spawn':spawn,'first_visible':{k:first_visible[k] for k in ('observation_id','observation_sim_s','capture_end_monotonic_ns','rgb_file')} if first_visible else None,
        'oracle_available':{k:available[k] for k in ('observation_id','observation_sim_s','capture_end_monotonic_ns')} if available else None,
        'first_fresh':boundary,'sample0_unsafe_count':sum(d['sample0_unsafe'] for d in dec),
        'selection_replacement_count':sum(d['selected_sample']!=0 for d in dec),'ALL_UNSAFE_count':sum(d['all_unsafe'] for d in dec),
        'actual_replacement_count':sum(e['phase2']['selected_sample']!=0 for e in events),
        'graph':{'calls':sum(g.get('event')=='SUBMIT' for g in graph),'returned':len(completed_graph),
            'accepted':sum(g.get('accepted',False) and not g['stale'] for g in completed_graph),
            'applied':sum(g.get('applied',False) for g in completed_graph),
            'nonconverged':sum(not g.get('solver',{}).get('success',True) for g in completed_graph),
            'initialization_rejected':sum(g.get('initialization_rejected',False) for g in completed_graph),
            'stale':sum(g['stale'] for g in completed_graph),'solve_wall_s':stats([g['solver']['solver_wall_s'] for g in completed_graph if 'solver' in g]),
            'dispatch_to_result_s':stats([g['elapsed_s'] for g in completed_graph]),
            'movement_during_graph_m':stats([g['movement_since_dispatch_m'] for g in completed_graph])},
        'switch_abs_dw':stats(changes),'curvature_saturated_control_count':sum(c['pure_pursuit'].get('CURVATURE_SATURATED',False) for c in controls),
        'controller_count':len(controls),'waypoint_timeouts':summary['waypoint_timeout_episodes'],
        'requests':len(req),'switches':len(events),'packet_release_s':stats(delays),
        'warm_inference_ms':stats([r['inference_ms'] for r in inf[1:]]),
        'validation':{'pose_error':pose_error,'pp_command_error':pp_error,'command_trace_error':command_trace_error,
                      'RGB_history_hashes':True,'uniform_delay':True,'public_geometry_gate':True,'native_and_selection':True,
                      'max_pacing_error_s':max(abs(float(r['pacing_error_s'])) for r in trace)},
        'input_hashes':{str(f.relative_to(run)):sha256_file(f) for f in list(run.glob('*.json'))+list(run.glob('*.jsonl'))+[run/'agent_trajectory.csv']}}
    if spawn and do_feasibility:result['feasibility']=feasibility(run,states,spawn['obstacle'],config,out)
    else:result['feasibility']={'status':'NOT_REQUESTED' if spawn else 'NOT_APPLICABLE_NO_SPAWN'}
    write_json(out/'summary.json',result)
    return result
