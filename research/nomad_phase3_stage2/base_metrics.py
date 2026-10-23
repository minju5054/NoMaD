"""Actual-command and 72Hz replay checks; original geometry helpers reused."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.async_report import rows
from nomad_isaac.common import integrate_se2, sha256_file
from nomad_isaac.seed_offset import request_seed
from nomad_phase0.chunk_report import trace
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum, classify, margin_violation_duration
from .config import protocol


def extract_run(run, condition, run_id, offset, delay_sweep=True):
    run=Path(run); s=json.loads((run/'summary.json').read_text()); c=s['scenario']; p=protocol()
    prov=json.loads((run/'provenance.json').read_text())
    assert not prov['git_status'] and prov['s0_stage2_method']==c['s0_stage2_method']
    assert s['experiment_label']==p['label'] and s['pure_pursuit_enabled']
    assert c['run_id']==prov['run_id']==run_id and c['seed_offset']==prov['seed_offset']==offset
    assert prov['source_scenario_sha256']==p['scenario_sha256']
    assert c['topomap_manifest_sha256']==p['topomap_manifest_sha256']
    assert sha256_file(Path(c['topomap_manifest']))==p['topomap_manifest_sha256']
    assert (c['controller_hz'],c['integration_hz'],c['observation_hz'])==(9,72,4)
    assert c['timeout_sim_s']==90 and c['selected_sample']==0 and c['selected_waypoint_index']==2
    assert json.loads((run/'stage2_protocol.json').read_text())==p
    assert not prov['controlled_delivery_delay'] and not prov['oracle_safety_stop']
    q,r,m=[rows(run/n) for n in ('requests.jsonl','received.jsonl','model/inference.jsonl')]
    assert len(q)==len(r)==len(m)
    seeds=[]
    for i,(a,b,d) in enumerate(zip(q,r,m)):
        seed=request_seed(c,i)
        assert a['id']==b['id']==d['id']==i and a['seed']==b['seed']==d['seed']==seed
        assert b['ddpm_seed']==d['ddpm_seed']==seed+1
        assert a['run_id']==b['run_id']==d['run_id']==run_id
        seeds.append({'request_id':i,'seed':seed,'ddpm_seed':seed+1})
    rec,poses=trace(run);control=rows(run/'controller.jsonl');gaps=rows(run/'clearance.jsonl')
    assert len(rec)==len(gaps)
    actual=np.array([[x['applied_v_m_s'],x['applied_w_rad_s']] for x in control])
    error=0.;min_corridor=float('inf');distance=stopped=0.
    for i in range(1,len(rec)):
        cmd=[float(rec[i][k]) for k in ('v_m_s','w_rad_s')]
        np.testing.assert_array_equal(cmd,actual[(i-1)//8])
        error=max(error,float(np.max(np.abs(integrate_se2(poses[i-1],*cmd,1/72)-poses[i]))))
        assert abs(float(rec[i]['simulation_time_s'])-i/72)<1e-10
        assert abs(gaps[i]['end_sim_s']-i/72)<1e-10
        stopped+=int(cmd==[0.,0.])/72
        distance+=float(np.linalg.norm(poses[i,:2]-poses[i-1,:2]))
        min_corridor=min(min_corridor,corridor_arc_minimum(poses[i-1],*cmd,1/72,c['corridor'],c['agent_radius_m']))
    assert error<1e-12 and abs(distance-s['distance_travelled_m'])<1e-10
    overlap=any(g['geometric_overlap'] for g in gaps)
    assert overlap==s['obstacle_evaluation']['geometric_overlap']
    outcome=classify(s['goal_entry'],overlap,min_corridor<0,s['termination_reason'],s['simulation_duration_s'],90.)
    metric={'scope':'Oracle geometry; SE(2) kinematic Isaac Sim','method':c['s0_stage2_method'],
        'classification':outcome,'success':outcome=='SUCCESS','technical_failure':False,
        'goal_entry':s['goal_entry'],'goal_time_s':s['simulation_duration_s'] if s['goal_entry'] else None,
        'termination_reason':s['termination_reason'],'duration_s':s['simulation_duration_s'],
        'distance_m':distance,'stop_time_s':stopped,'mean_speed_m_s':distance/s['simulation_duration_s'],
        'moving_mean_speed_m_s':distance/(s['simulation_duration_s']-stopped) if s['simulation_duration_s']>stopped else None,
        'geometric_overlap':overlap,'corridor_violation':min_corridor<0,'minimum_corridor_clearance_m':min_corridor,
        'margin_violation_s':margin_violation_duration(gaps),'max_pose_replay_error':error,
        'w_clipping_fraction':float(np.mean([c['stage2']['OMEGA_CLIPPED'] for c in control])),
        'execution_git_sha':prov['git_sha'],'request_seeds':seeds}
    for box in c['obstacles']:
        key=box['id'];logged=s['obstacle_evaluation']['obstacles'][key]
        value=min(g['obstacles'][key]['lower_m'] for g in gaps)
        assert abs(value-logged['minimum_swept_clearance_lower_m'])<1e-10
        metric[key+'_minimum_clearance_m']=value
        metric[key+'_passage_side']=logged['passage']['side'] if logged['passage'] else 'not_passed'
    return metric
