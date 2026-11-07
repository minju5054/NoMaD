"""Frozen evaluation outcomes plus descriptive Phase35 telemetry only."""
import csv,json
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_phase26.metrics import audit as base_audit
from nomad_phase32.report import audit as ec_audit,lines

def q(values,p):return float(np.quantile(values,p)) if len(values) else None

def audit(root):
    root=Path(root);cfg=json.loads((root/'scenario.json').read_text());method=cfg['phase35_method']
    r=ec_audit(root) if method in ('OURS','ASTAR+EC') else base_audit(root)
    r.update(method=method,mean_speed_m_s=r['distance_m']/r['duration_s'])
    commands=lines(root/'phase20_commands.jsonl');events=lines(root/'events.jsonl');detours=lines(root/'detour.jsonl')
    applies=[x for x in detours if x['event']=='APPLIED'];active={};detour_s=0.;path_lengths=[]
    for e in detours:
        if e['event']=='APPLIED':
            active[e['job_id']]=e['simulation_time_s']
        elif e['event']=='END' and e['job_id'] in active:detour_s+=e['simulation_time_s']-active.pop(e['job_id'])
    detour_s+=sum(r['duration_s']-t for t in active.values())
    for e in lines(root/'repair.jsonl'):
        if e['event']=='PATH_APPLIED' and e['kind']=='DETOUR':path_lengths.append(float(np.linalg.norm(np.diff(np.asarray(e['path_world']),axis=0),axis=1).sum()))
    costs=[x['pool_wall_s'] for x in lines(root/'repair_pool_jobs.jsonl') if x.get('pool_wall_s') is not None]
    lat=[e['application_sim_s']-e['observation_sim_s'] for e in events if e.get('application_sim_s') is not None]
    receipt=[e['application_sim_s']-e['received_sim_s'] for e in events if e.get('application_sim_s') is not None and e.get('received_sim_s') is not None]
    states=Counter()
    for i,e in enumerate(commands):
        end=commands[i+1]['time_s'] if i+1<len(commands) else r['duration_s']
        states[e['source']]+=max(0.,end-e['time_s'])
    inference=[e['inference_ms']/1000 for e in lines(root/'model/inference.jsonl')]
    r.update(detour_execution_s=detour_s,detour_path_lengths_m=path_lengths,detour_path_total_m=sum(path_lengths),
        compute_times_s=costs,compute_p50_s=q(costs,.5),compute_p95_s=q(costs,.95),
        inference_p50_s=q(inference,.5),inference_p95_s=q(inference,.95),
        chunk_handoff_delay_s=lat,chunk_receive_to_apply_s=receipt,
        chunk_delay_p50_s=q(lat,.5),chunk_delay_p95_s=q(lat,.95),command_state_seconds=dict(states))
    tr=list(csv.DictReader((root/'agent_trajectory.csv').open()));t=np.array([float(x['simulation_time_s']) for x in tr]);xy=np.array([[float(x[k]) for k in ('x_m','y_m')] for x in tr]);goal=np.asarray(cfg['goal_pose'])[:2]
    distances=np.linalg.norm(xy-goal,axis=1);near=float(distances.min());before=max(0,int(np.searchsorted(t,t[-1]-10)))
    progress=float(distances[before]-distances[-1]);maximum=float(np.linalg.norm(xy-xy[0],axis=1).max())
    summary=json.loads((root/'summary.json').read_text());contacts=[]
    def visit(v):
        if isinstance(v,dict):
            c=v.get('first_contact')
            if isinstance(c,dict):contacts.append(c)
            for x in v.values():visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    visit(summary.get('obstacle_evaluation'));visit(summary.get('dynamic_obstacle'))
    structural=any('InnerCorner' in json.dumps(c) or 'Wall' in json.dumps(c) for c in contacts)
    if r['success']:cause=None
    elif r.get('obstacle_collision'):cause='WALL_COLLISION' if structural else 'BOX_COLLISION'
    elif r.get('wall_overlap') or r.get('corridor'):cause='WALL_COLLISION'
    elif near<=.6:cause='NEAR_GOAL_HOVER'
    elif r.get('box_passage'):cause='POST_PASSAGE_TIMEOUT'
    elif r['scene'] in ('SLW','LC') and progress<.2:cause='STATIC_NARROW_STUCK'
    elif r.get('boxes') and not r.get('box_passage'):cause='DETOUR_FAIL'
    elif (r['scene'] in ('L2','H1','H2') and not r.get('boxes')) or maximum<.5:cause='EARLY_STUCK'
    else:cause='OTHER'
    r.update(primary_cause=cause,minimum_goal_distance_m=near,last10_goal_progress_m=progress,
             maximum_start_displacement_m=maximum,structural_contact=structural)
    # Archive proof, never an additional control check. All installations must
    # expose the common strict >90 degree departure threshold.
    apps=[e for e in lines(root/'repair.jsonl') if e['event']=='PATH_APPLIED']
    assert all(e.get('threshold_deg')==90. for e in apps), 'Executor threshold differs'
    r['executor_installations']=len(apps);r['executor_threshold_deg']=90.
    return r
