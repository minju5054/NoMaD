"""Frozen monitor outcomes plus exact SE(2) command/pose and seed audit."""
import csv,json
from pathlib import Path
import numpy as np
from nomad_isaac.common import integrate_se2

def rows(file):return [json.loads(s) for s in Path(file).read_text().splitlines() if s] if Path(file).exists() else []
def base_audit(run):
    run=Path(run);summary=json.loads((run/'summary.json').read_text());cfg=summary['scenario'];data=list(csv.DictReader((run/'agent_trajectory.csv').open()))
    poses=np.array([[float(r[k]) for k in ('x_m','y_m','yaw_rad')] for r in data]);v=np.array([float(r['v_m_s']) for r in data]);w=np.array([float(r['w_rad_s']) for r in data]);t=np.array([float(r['simulation_time_s']) for r in data]);error=0.
    for i in range(1,len(data)):error=max(error,float(np.max(np.abs(integrate_se2(poses[i-1],v[i],w[i],1/72)-poses[i]))))
    assert error<=1e-12 and np.isfinite(poses).all() and np.max(np.abs(w))<=.4+1e-12 and np.max(v)<=.3+1e-12
    requests=rows(run/'requests.jsonl');inference=rows(run/'model/inference.jsonl');assert len(requests)==len(inference)
    for i,(q,m) in enumerate(zip(requests,inference)):
        assert q['id']==m['id']==i and q['seed']==m['seed']==101+cfg['seed_offset']+2*i and m['ddpm_seed']==q['seed']+1
    obs=summary['obstacle_evaluation'];dynamic=summary.get('dynamic_obstacle',{});de=dynamic.get('evaluation') or {}
    obstacle_collision=bool(obs.get('geometric_overlap') or de.get('geometric_overlap'));corridor=not obs.get('corridor_containment_certified',True) or not de.get('corridor_containment_certified',True)
    wall_clearance=min((d['minimum_corridor_clearance_lower_m'] for d in (obs,de) if d.get('minimum_corridor_clearance_lower_m') is not None),default=float('inf'))
    wall_overlap=wall_clearance<0;collision=obstacle_collision or wall_overlap
    success=bool(summary['goal_entry'] and not collision and not corridor);reason=summary['termination_reason']
    classification='SUCCESS' if success else 'COLLISION' if obstacle_collision else 'CORRIDOR' if corridor else 'STUCK'
    lower=[x for x in (obs.get('minimum_swept_clearance_lower_m'),de.get('minimum_swept_clearance_lower_m'),obs.get('minimum_corridor_clearance_lower_m')) if x is not None]
    passage=de.get('passage') or {};spawn=dynamic.get('spawn') or {};elapsed=summary['simulation_duration_s'];passed=bool(passage)
    g=rows(run/'g_events.jsonl');applications=[r for r in g if r['event']=='APPLY'];dispatched=[r for r in g if r['event']=='DISPATCH']
    return dict(scene=cfg['phase16_scene'],method=cfg['phase24r_method'],index=cfg['seed_offset']//10000,seed_offset=cfg['seed_offset'],output=str(run),technical_validation='PASS',classification=classification,
        success=success,collision=collision,obstacle_collision=obstacle_collision,wall_overlap=wall_overlap,corridor=corridor,termination=reason,duration_s=elapsed,goal_time_s=elapsed if success else None,
        box_passage=passed,box_passage_time_s=passage.get('simulation_time_s'),box_passage_from_spawn_s=passage['simulation_time_s']-spawn['simulation_time_s'] if passed and 'simulation_time_s' in spawn else None,
        passage_side=passage.get('side'),minimum_clearance_m=min(lower) if lower else None,minimum_obstacle_clearance_m=min([x for x in (obs.get('minimum_swept_clearance_lower_m'),de.get('minimum_swept_clearance_lower_m')) if x is not None],default=None),minimum_wall_clearance_m=obs.get('minimum_corridor_clearance_lower_m'),
        omega_saturation_fraction=float(np.mean(np.abs(w[1:])>=.399)) if len(w)>1 else 0.,stopped_fraction=float(np.sum(np.diff(t)*(np.abs(v[1:])<.01))/elapsed) if elapsed else 0.,
        distance_m=summary['distance_travelled_m'],command_pose_error_m=error,inference_count=len(inference),g_dispatches=len(dispatched),g_applications=len(applications),
        g_output_counts={kind:sum(r['output_type']==kind for r in applications) for kind in ('FEASIBLE','KINEMATIC_TOLERATED','STOP')},
        prediction_error_m=[r['prediction_error_m'] for r in applications],application_delay_s=[r['application_delay_s'] for r in applications])

def audit(run):
    from collections import Counter
    from nomad_isaac.clearance import configured_obstacles
    from nomad_phase22.drive_geometry import swept_gap
    from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
    from nomad_phase16.geometry import centered,shifted
    run=Path(run);result=base_audit(run);summary=json.loads((run/'summary.json').read_text());cfg=summary['scenario'];duration=result['duration_s'];spawn=(summary.get('dynamic_obstacle') or {}).get('spawn')
    if result['method']=='G':
        events=rows(run/'g_events.jsonl');commands=rows(run/'g_commands.jsonl');assert commands and events
        applications=[r for r in events if r['event']=='APPLY'];assert applications
        assert all(abs(r['application_delay_s']-.5)<1e-12 for r in applications)
        pool=rows(run/'g_pool.jsonl');assert not any(r['kind']=='ERROR' for r in pool)
        costs={r['job_id']:r['compute_s'] for r in pool if r['kind']=='FINAL'};job_compute=list(costs.values())
        inputs=[json.loads(f.read_text()) for f in (run/'g_jobs').glob('input_*.json')];parents={r['job_id']:r['parent']['job_id'] for r in inputs if r.get('parent')};superseded_stages=set(parents.values())
        compute=[t+costs.get(parents.get(i),0.) for i,t in costs.items() if i not in superseded_stages];recovery=sum(r['event']=='RECOVERY_START' for r in events)
        kinds=Counter(r['output_type'] for r in applications);modes={}
        for i,r in enumerate(commands):
            end=commands[i+1]['simulation_time_s'] if i+1<len(commands) else duration
            key=r['recovery'] if r['recovery']!='NORMAL' else r['mode'];modes[key]=modes.get(key,0.)+max(0,end-r['simulation_time_s'])
        active=[];start=None
        for r in events:
            if r['event']=='APPLY' and r['mode']=='DETOUR' and r['output_type']!='STOP':start=r['simulation_time_s']
            if r['event']=='MODE_EXIT' and start is not None:active.append((start,r['simulation_time_s']));start=None
        if start is not None:active.append((start,duration))
        final=Counter(r['output_type'] for r in applications if r['job_id'] not in superseded_stages)
        rotations=[r for r in events if r['event']=='ROTATION_PRIORITY_START'];ends=[r for r in events if r['event']=='ROTATION_PRIORITY_END']
        trigger=[r for r in events if r['event']=='MODE_ENTER' and r.get('reason')=='TRIGGER_B']
        unsafe=[r for r in events if r['event']=='PATH_BECAME_UNSAFE']
        rejects=[r for r in events if r['event']=='CERTIFICATE_REJECTED'];alternatives=[r for r in events if r['event']=='CERTIFICATE_ALTERNATIVE_USED']
        timing=dict(mode_fraction={k:v/duration for k,v in modes.items()},output_counts=dict(kinds),output_fractions={k:v/len(applications) for k,v in kinds.items()},pipeline_output_counts=dict(final),job_compute_p95_s=float(np.quantile(job_compute,.95)) if job_compute else None,
            trigger_after_spawn_s=[r['simulation_time_s']-spawn['simulation_time_s'] for r in trigger] if spawn else [],rotation_priority_count=len(rotations),rotation_priority_time_s=sum(r['duration_s'] for r in ends),
            theta_chord_inconsistent_count=sum(bool(r['THETA_CHORD_INCONSISTENT']) for r in rotations),certificate_rejection_count=len(rejects),certificate_alternative_count=len(alternatives),path_became_unsafe_count=len(unsafe))
    else:
        events=rows(run/'detour.jsonl');active=[];start=None
        for r in events:
            if r['event']=='APPLIED':start=r['simulation_time_s']
            if r['event']=='END' and start is not None:active.append((start,r['simulation_time_s']));start=None
        if start is not None:active.append((start,duration))
        recovery=sum(r['event']=='START' for r in rows(run/'recovery.jsonl'))
        compute=[(r.get('numeric_result') or {}).get('dispatch_to_complete_s',r.get('wait_s')) for r in events+rows(run/'repair.jsonl') if r['event']=='RESULT'];compute=[t for t in compute if t is not None];timing=dict(mode_fraction=None,output_counts=None,output_fractions=None)
        trigger=[r for r in events if r['event']=='TRIGGER' and r.get('trigger')=='B'];unsafe=[r for r in events if r.get('disposition')=='APPLICATION_UNSAFE' or r.get('reason')=='PATH_BECAME_UNSAFE']
        timing.update(trigger_after_spawn_s=[r['simulation_time_s']-spawn['simulation_time_s'] for r in trigger] if spawn else [],rotation_priority_count=0,rotation_priority_time_s=0.,theta_chord_inconsistent_count=0,certificate_rejection_count=0,certificate_alternative_count=0,path_became_unsafe_count=len(unsafe))
    data=list(csv.DictReader((run/'agent_trajectory.csv').open()));minimum=None;cc,offset=centered(cfg);boxes=configured_obstacles(cfg);spawn=(summary.get('dynamic_obstacle') or {}).get('spawn')
    for i,r in enumerate(data[1:],1):
        t=float(r['simulation_time_s'])
        if not any(a<t<=b+1e-12 for a,b in active):continue
        previous=data[i-1];pose=np.array([float(previous[k]) for k in ('x_m','y_m','yaw_rad')]);v=float(r['v_m_s']);w=float(r['w_rad_s'])
        gap=corridor_arc_minimum(shifted(pose,offset),v,w,1/72,cc['corridor'],cfg['agent_radius_m'])
        current=boxes+([spawn['obstacle']] if spawn and t>=spawn['simulation_time_s'] else [])
        for box in current:gap=min(gap,swept_gap(pose,v,w,1/72,box,cfg['agent_radius_m'])['lower_m'])
        minimum=gap if minimum is None else min(minimum,gap)
    result.update(**timing,recovery_count=recovery,detour_minimum_clearance_m=minimum,detour_execution_s=sum(b-a for a,b in active),compute_p50_s=float(np.median(compute)) if compute else None,compute_p95_s=float(np.quantile(compute,.95)) if compute else None,
        compute_definition='G dispatch-to-final wall time incl transport; NORMAL->DETOUR stages summed per pipeline; single-job p95 also reported' if result['method']=='G' else 'frozen C0/C1 repair/detour dispatch-to-complete; timeout uses recorded wait',launcher_wall_s=json.loads((run/'launch_complete.json').read_text()).get('launcher_wall_s'))
    return result
