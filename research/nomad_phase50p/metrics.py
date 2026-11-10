"""Read-only outcomes: frozen static evaluator plus relative moving-circle sweep."""
import csv,json
from pathlib import Path
import numpy as np
from nomad_phase24r.online_metrics import base_audit,rows
from nomad_phase41.metrics import outcomes
from nomad_phase43p.localization import Localization

def time_metrics(data,start=0.,end=None):
    if len(data)<2:return dict(stopped_s=0.,slow_moving_s=0.,decelerating_s=0.)
    t=np.array([float(x['simulation_time_s']) for x in data]);v=np.array([float(x['v_m_s']) for x in data])
    end=t[-1] if end is None else end;dt=np.maximum(0,np.minimum(t[1:],end)-np.maximum(t[:-1],start))
    return dict(stopped_s=float(dt[np.abs(v[1:])<.01].sum()),
        slow_moving_s=float(dt[(v[1:]>=.01)&(v[1:]<.3-1e-6)].sum()),decelerating_s=float(dt[np.diff(v)<-1e-8].sum()))

def contact_time(summary):
    times=[]
    def visit(obj):
        if isinstance(obj,dict):
            contact=obj.get('first_contact')
            if isinstance(contact,dict) and contact.get('detected_sim_s') is not None:times.append(contact['detected_sim_s'])
            for value in obj.values():visit(value)
        elif isinstance(obj,list):
            for value in obj:visit(value)
    visit(summary.get('obstacle_evaluation'));visit(summary.get('dynamic_obstacle'))
    return min(times) if times else None

def collision_ec(events,when):
    return [] if when is None else [dict(e,seconds_before_contact=when-e['simulation_time_s']) for e in events
        if e.get('simulation_time_s') is not None and when-2-1e-12<=e['simulation_time_s']<=when+1e-12]

def ghost_summary(events,removal,duration):
    output=[]
    for sec in range(5):
        group=[e for e in events if sec<=e['offset_from_removal_s']<sec+1 or sec==4 and e['offset_from_removal_s']==5]
        row=dict(after_removal_bin_s=f'{sec}-{sec+1}',snapshots=len(group),
            observation_available_s=max(0.,min(1.,duration-removal['simulation_time_s']-sec)) if removal else 0.)
        for name in ('endpoint_occupied_cells','endpoint_new_occupied_cells','swept_trail_occupied_cells','swept_trail_new_occupied_cells'):
            values=[e[name] for e in group];row[name+'_median']=float(np.median(values)) if values else None
            row[name+'_max']=max(values) if values else None;row[name+'_last']=values[-1] if values else None
        output.append(row)
    return output

def audit(root):
    root=Path(root);r=base_audit(root);s=json.loads((root/'summary.json').read_text());c=s['scenario'];d=s['dynamic_obstacle']
    assert c['phase50p'] and c['phase47c_method']=='OURS-DETOUR+HMM' and c['nomad_goal_stop'] and c['depth_camera']
    assert json.loads((root/'geometry_check.json').read_text())['status']=='PASS'
    assert (root/'phase26_complete.json').exists() and not (root/'oracle_information.json').exists()
    assert rows(root/'depth/updates.jsonl');assert not any(e.get('error') for e in rows(root/'repair_pool_jobs.jsonl'))
    apps=[e for e in rows(root/'repair.jsonl') if e['event']=='PATH_APPLIED'];assert all(e.get('threshold_deg')==90. for e in apps)
    assert not [e for e in rows(root/'detour.jsonl') if e['event']=='APPLIED'],'Frozen OURS-DETOUR must not detour'
    nodes=json.loads(Path(c['topomap_manifest']).read_text())['nodes'];selector=Localization([n['world_pose'] for n in nodes])
    for e in rows(root/'model/inference.jsonl'):
        expected=selector.select(e['topomap']['distances'],e['hmm_odometry_total_m'])
        for key in ('candidate_ids','closest_node','selected_subgoal_id'):assert e['topomap'][key]==expected[key]
    declared=(root/'declared_arrival.json').exists();stop=json.loads((root/'declared_arrival.json').read_text()) if declared else None
    assert declared==(s['termination_reason']=='declared_arrival')
    if stop:assert stop['closest_node']==stop['goal_node'] and stop['stop_command']==[0.,0.];np.testing.assert_array_equal(stop['pose'],s['final_pose'])
    distance=float(s['final_goal_distance_m']);r.update(outcomes(declared,distance,r['collision'],r['termination']))
    r.update(method='OURS-DETOUR+HMM',scene=c['phase50p_condition'],base_scene=c['phase16_scene'],speed_m_s=c['phase50p_moving']['speed_m_s'],
        goal_time_s=s['simulation_duration_s'] if r['success'] else None,stop_distance_m=distance if declared else None,final_distance_m=distance,
        classification='SUCCESS' if r['success'] else 'COLLISION' if r['collision'] else 'WRONG_STOP' if r['wrong_stop'] else 'TIMEOUT' if r['timeout_without_declaration'] else 'OTHER')
    r['person_spawned']=d['status']=='SPAWNED';r['person_collision']=bool(d['evaluation']['geometric_overlap'])
    r['minimum_person_clearance_m']=d['evaluation']['minimum_swept_clearance_lower_m']
    r['minimum_person_center_distance_m']=d['evaluation']['minimum_center_distance_upper_m'];r['person_removal']=d['removal']
    r['spawn_reference_remaining_m']=d['spawn']['reference_remaining_m'] if d.get('spawn') else None
    if r['person_spawned']:
        assert (root/'person_render_setup.json').exists();setup=json.loads((root/'person_render_setup.json').read_text())
        assert setup['spawn_s']==d['spawn']['simulation_time_s'] and setup['radius_m']==.2
        persons=rows(root/'dynamic/person_trajectory.jsonl');assert persons and all(e['id']=='MovingPerson' for e in persons)
    data=list(csv.DictReader((root/'agent_trajectory.csv').open()));r.update(time_metrics(data))
    r['person_present_time']=time_metrics(data,d['spawn']['simulation_time_s'],d['exit_sim_s']) if d.get('spawn') else None
    ec=rows(root/'exec_cert.jsonl');ticks=rows(root/'exec_cert_72hz.jsonl');assert ticks and max(x['tick'] for x in ticks)==round(r['duration_s']*72)
    r['ec_slow_cap_s']=sum(bool(x['speed_cap_active']) for x in ticks)/72
    r['ec_reject_stopped_s']=sum(x['ec_reject_latched'] and x['physical_stop'] for x in ticks)/72
    r['ec_checks']=sum(e['event']=='CHECK' for e in ec);r['ec_rejects']=sum(e['event']=='CHECK' and not e['passed'] for e in ec)
    when=contact_time(s);r['contact_time_s']=when;r['ec_before_contact_2s']=collision_ec(ec,when)
    ghost=rows(root/'dynamic/post_removal_ghost.jsonl');r['ghost_by_second']=ghost_summary(ghost,d['removal'],r['duration_s'])
    r['post_removal_5s_available']=bool(d['removal'] and r['duration_s']>=d['removal']['simulation_time_s']+5)
    r['ghost_last_offset_s']=d['ghost_last_offset_s'];r['ghost_snapshot_count']=len(ghost)
    r['launcher_wall_s']=json.loads((root/'launch_complete.json').read_text())['launcher_wall_s']
    return r
