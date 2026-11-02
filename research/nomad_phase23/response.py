"""Evaluation-only response/stop bookkeeping; no oracle information to U."""
import numpy as np
from nomad_phase15.evaluate import suffix
from nomad_phase22.drive_geometry import rotation,bounds
from nomad_isaac.clearance import segment_clearance

def avoiding_output(path,application_pose,box,radius):
    if path is None:return dict(avoids=False,reason='NO_OUTPUT_PATH')
    tail,_=suffix(path,application_pose);tail=np.vstack([np.asarray(application_pose)[:2],tail])
    R=rotation(box);local=(tail-box['center_xy_m'])@R;half=np.asarray(box['size_xyz_m'][:2])/2
    clearance=min(segment_clearance(a,b,-half,half,radius)[0] for a,b in zip(local[:-1],local[1:]))
    lo,hi=bounds(box);side=(tail[:,1]>=hi[1]+radius+.025)|(tail[:,1]<=lo[1]-radius-.025)
    ahead=tail[:,0]>application_pose[0]+1e-9
    qualifies=bool(clearance>=0 and np.any(side&ahead))
    return dict(avoids=qualifies,reason='SAFE_SIDE_REACH' if qualifies else 'NO_SAFE_SIDE_REACH',box_path_clearance_m=float(clearance))

def reaction(case,plan,result,reference=None):
    if case['group']!='sudden':return dict(reaction_status='NOT_APPLICABLE')
    if reference is None or reference.get('first_map_available_s') is None:return dict(reaction_status='BOX_NOT_OBSERVED')
    box=case['spawn']['obstacle'];radius=case['oracle_config']['agent_radius_m'];_,hi=bounds(box)
    if case['B'][0]-radius>hi[0]:return dict(reaction_status='ALREADY_PASSED_AT_SNAPSHOT')
    delay=float(plan.get('application_delay_s',plan['compute_s']));output_time=case['tick']/72+delay
    first=float(reference['first_map_available_s'])
    if output_time<first:return dict(reaction_status='BEFORE_DEPTH_AVAILABLE')
    application=plan.get('B_pred',plan.get('application_pose',case['B']))
    decision=avoiding_output(plan.get('path'),application,box,radius)
    if not decision['avoids']:return dict(reaction_status='NO_AVOIDING_OUTPUT_CENSORED',**decision)
    return dict(reaction_status='OBSERVED_AVOIDING_OUTPUT_UPPER_BOUND',reaction_delay_s=output_time-first,
        reaction_distance_m=float(reference['distance_to_snapshot_m']+result.get('computation_prefix_distance_m',0.)),
        first_depth_map_available_s=first,output_time_s=output_time,**decision)

def stop_metrics(plan,result):
    dt=np.asarray(result.get('step_dt_s',[1/72]*len(result['speeds'])));speed=np.asarray(result['speeds']);commands=result.get('commands',[])
    brake_modes={'NO_PLAN_BRAKE','GRAPH_ROTATION_BRAKE','BASELINE_COMPUTATION_BRAKE'}
    brake=0.
    for i,c in enumerate(commands):
        begin=c.get('time_s',c['tick']/72);end=commands[i+1].get('time_s',commands[i+1]['tick']/72) if i+1<len(commands) else result['duration_s']
        if c.get('mode') in brake_modes:brake+=max(0.,end-begin)
    requested=not plan['accepted']
    return dict(stop_requested=requested,deceleration_stop_occurred=brake>0,braking_duration_s=min(brake,result['duration_s']),
        observed_stationary_s=float(dt[speed<.01].sum()),post_stop_wait_right_censored=requested,
        stop_duration_note='Only the finite counterfactual trace is observed; waiting for future NoMaD candidates is not fabricated.')
