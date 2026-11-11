"""Post-run Phase18 outcome/72Hz checkpoint extraction; no controller oracle."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import integrate_se2,sha256_file
from nomad_phase0.chunk_report import trace
from nomad_phase4c.plant import control_command
from nomad_isaac.topomap import candidate_range,select_subgoal
from nomad_j1.common import half_extent
from .config import METHOD,protocol

def rows(path):
    path=Path(path)
    return [json.loads(x) for x in path.read_text().splitlines() if x] if path.exists() else []

def checkpoint(c,summary,poses):
    spec=protocol()['scenes'][c['j_scene']]['checkpoint'];axis=spec['axis'];threshold=spec['threshold_m'];spawn_tick=0
    if spec['dynamic']:
        boxes=(summary.get('dynamic_obstacle') or {}).get('boxes',[])
        if len(boxes)<spec['expected_box_count']:
            return dict(checkpoint_axis=axis,checkpoint_threshold_m=None,checkpoint_start_distance_m=None,
                        checkpoint_time_s=None,checkpoint_tick=None,checkpoint_status='LAST_BOX_NOT_SPAWNED')
        spawn=boxes[-1]['spawn'];box=spawn['obstacle'];spawn_tick=spawn['tick']
        threshold=float(box['center_xy_m'][axis]+half_extent(box,axis)+.30)
    hits=np.flatnonzero(poses[spawn_tick:,axis]>=threshold)
    tick=int(hits[0]+spawn_tick) if len(hits) else None
    return dict(checkpoint_axis=axis,checkpoint_threshold_m=threshold,
                checkpoint_start_distance_m=float(threshold-c['start_pose'][axis]),
                checkpoint_time_s=tick/72 if tick is not None else None,checkpoint_tick=tick,
                checkpoint_status='CROSSED' if tick is not None else 'NOT_CROSSED')

def audit(run):
    run=Path(run);s=json.loads((run/'summary.json').read_text());c=s['scenario'];rec,poses=trace(run)
    launch=json.loads((run/'launch_complete.json').read_text())
    assert launch['exit_code']==0 and (run/'phase26_complete.json').exists() and not (run/'FAILED.json').exists()
    assert c['j0'] and c['j_method']==METHOD and c['goal_tolerance_m']==.3 and c['nomad_goal_stop'] is False
    assert c['integration_hz']==72 and c['controller_hz']==9 and c['observation_hz']==4
    assert c['timeout_sim_s']==90 and c['phase4c_method']=='GRAPH' and c['plant_alpha']=='inf'
    for file in ('declared_arrival.json','oracle_information.json','recovery.jsonl','fallback.jsonl','exec_cert.jsonl'):
        assert not (run/file).exists(),file
    assert json.loads((run/'geometry_check.json').read_text())['status']=='PASS'
    ctrl=rows(run/'controller.jsonl');events=rows(run/'events.jsonl');apps=rows(run/'j_applications.jsonl')
    assert rows(run/'depth/updates.jsonl') and ctrl
    times=np.array([float(r['simulation_time_s']) for r in rec]);duration=float(times[-1])
    np.testing.assert_allclose(times,np.arange(len(rec))/72,rtol=0,atol=1e-12)
    previous=0.;command_error=0.;pose_error=0.
    for row in ctrl:
        expected=(0.,0.);diag=row['pure_pursuit']
        if row['valid'] and diag['stop_reason'] is None:
            x,y=diag['target_local_x_m'],diag['target_local_y_m'];k=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
            expected=control_command('CURV',k,previous,0.,float('inf'))[0]
        actual=[row['commanded_v_m_s'],row['commanded_w_rad_s']]
        command_error=max(command_error,float(np.max(np.abs(np.array(expected)-actual))));previous=actual[0]
        assert not row['j_execution']['recovery'] and not row['j_execution']['stop_wait_special'] and not row['j_execution']['EC']
    for tick in range(1,len(rec)):
        v,w=float(rec[tick]['v_m_s']),float(rec[tick]['w_rad_s']);cc=ctrl[(tick-1)//8]
        np.testing.assert_allclose([v,w],[cc['commanded_v_m_s'],cc['commanded_w_rad_s']],atol=1e-12,rtol=0)
        pose_error=max(pose_error,float(np.abs(integrate_se2(poses[tick-1],v,w,1/72)-poses[tick]).max()))
    assert command_error<1e-12 and pose_error<1e-12
    # Official argmin localization/subgoal, without HMM or goal-node termination.
    manifest=json.loads(Path(c['topomap_manifest']).read_text());closest=0
    requests=rows(run/'requests.jsonl');received=rows(run/'received.jsonl');inference=rows(run/'model/inference.jsonl')
    assert len(requests)==len(received)==len(inference)
    for q,r,inf in zip(requests,received,inference):
        top=inf['topomap'];a,b=candidate_range(closest,len(manifest['nodes'])-1)
        assert (a,b)==(top['candidate_start'],top['candidate_end_inclusive'])
        closest,subgoal,_=select_subgoal(top['distances'],a)
        assert (closest,subgoal)==(top['closest_node'],top['selected_subgoal_id'])
        assert q['seed']==101+c['seed_offset']+2*q['id'] and inf['seed']==q['seed']
        delay=s['delivery_delay']['configured_additional_s']
        assert r['release_deadline_monotonic_ns']==r['packet_received_monotonic_ns']+round(delay*1e9)
        assert r['release_monotonic_ns']>=r['release_deadline_monotonic_ns']
    static=s['obstacle_evaluation'];dynamic=(s.get('dynamic_obstacle') or {}).get('evaluation') or {}
    collision=bool(static['geometric_overlap'] or dynamic.get('geometric_overlap',False))
    wall=float(static['minimum_corridor_clearance_lower_m'])
    corridor=wall<0
    distances=np.linalg.norm(poses[:,:2]-np.asarray(c['goal_pose'][:2]),axis=1)
    assert bool(s['goal_entry'])==(s['termination_reason']=='goal_entry')
    if s['goal_entry']:assert distances[-1]<=.3+1e-12 and not np.any(distances[:-1]<=.3)
    success=bool(s['goal_entry'] and not collision and not corridor)
    timeout=bool(not success and not collision and not corridor and 'timeout' in s['termination_reason'])
    kind='SAFETY_FAILURE' if collision or corridor else 'SUCCESS' if success else 'TIMEOUT' if timeout else 'OTHER_TERMINATION'
    graph=rows(run/'stage2_graph.jsonl');results=[r for r in graph if r['event']=='RESULT']
    for row in graph:
        if row['event']=='SUBMIT':assert not any(k in row for k in ('public_config','obstacles','corridor'))
    stop=sum(abs(float(r['v_m_s']))<1e-12 for r in rec[1:])/72
    clearance_values=[wall]+[float(e['minimum_swept_clearance_lower_m']) for e in (static,dynamic)
                            if e.get('minimum_swept_clearance_lower_m') is not None]
    r=dict(technical_validation='PASS',classification=kind,success=success,collision=collision,wall_intrusion=corridor,
        timeout=timeout,termination_reason=s['termination_reason'],duration_s=duration,goal_time_s=duration if success else None,
        minimum_goal_distance_m=float(distances.min()),stop_time_s=stop,stop_fraction=stop/duration if duration else None,
        minimum_clearance_m=min(clearance_values),
        graph_calls=sum(g['event']=='SUBMIT' for g in graph),graph_applied=sum(a['kind']=='GRAPH' for a in apps),
        graph_dispositions={d:sum(g['disposition']==d for g in results) for d in sorted({g['disposition'] for g in results})},
        solve_times_s=[g['solver']['solver_wall_s'] for g in results if 'solver' in g],
        command_error=command_error,pose_error=pose_error,launcher_wall_s=launch['launcher_wall_s'],
        input_sha256={f:sha256_file(run/f) for f in ('summary.json','agent_trajectory.csv','controller.jsonl','events.jsonl','stage2_graph.jsonl')})
    r.update(checkpoint(c,s,poses));return r
