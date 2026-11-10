"""Run summaries and historical same-seed metrics from stored72Hz records."""
import csv,json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_phase47c.metrics import audit as frozen_audit
from nomad_phase24r.online_metrics import rows
from nomad_phase0.pure_pursuit import XYPath
from nomad_isaac.common import local_to_world

TRACK_STATES={'NORMAL','KEEP_ACTIVE','ALIGN_BRAKE','ALIGN_ROTATE','REPAIR','ENDPOINT'}
def q(a,p):return float(np.quantile(a,p)) if len(a) else None

def waypoint_lifetime(commands,duration,received=(),declared_id=None):
    """Allow only genuine startup missing input; never forgive post-input expiry.

    Receipt is the execution thread's latch, not the IPC packet receive time.
    Final drained/unapplied results are not chunks delivered for navigation.
    The initial command-wait duration ends at the first control record that
    has a chunk (or declared arrival), and is separate from latch time.
    """
    assert commands,'Missing controller records'
    delivered=[float(e['latched_sim_s']) for e in received
               if not e.get('terminal_unapplied',False) or (declared_id is not None and e.get('id')==declared_id)]
    first_received=min(delivered) if delivered else None
    first_control=None;missing_timeout_rows=0;seen=False;previous=-1.
    for i,e in enumerate(commands):
        t=float(e['simulation_time_s']);assert previous<=t<=duration+1e-8,'Invalid controller chronology';previous=t
        assert not e.get('new_timeout',False),f'WAYPOINT_EXPIRY_EVENT at controller row{i},t={t}'
        has_chunk=(e.get('latest_received_id',-1)>=0 or e.get('waypoint_id',-1)>=0
                   or e.get('waypoint_age_wall_s') is not None or e.get('applied_command_source')=='DECLARED_ARRIVAL')
        if has_chunk and first_control is None:first_control=t
        seen=seen or has_chunk
        if e.get('applied_command_source')=='WAYPOINT_TIMEOUT':
            missing=(e.get('status')=='missing' and e.get('valid') is False
                     and e.get('latest_received_id',-1)<0 and e.get('waypoint_id',-1)<0
                     and e.get('waypoint_age_wall_s') is None)
            before_receipt=first_received is None or t<first_received-1e-10
            assert missing and not seen and before_receipt,f'POST_CHUNK_WAYPOINT_TIMEOUT at controller row{i},t={t}'
            missing_timeout_rows+=1
    initial_wait=duration if first_control is None else first_control
    return dict(initial_wait_s=float(initial_wait),first_chunk_received_s=first_received,
                first_chunk_control_s=first_control,startup_missing_timeout_rows=missing_timeout_rows,
                new_timeout_count=0,post_chunk_waypoint_timeout_rows=0)

def extra(root):
    root=Path(root);summary=json.loads((root/'summary.json').read_text());c=summary['scenario'];duration=summary['simulation_duration_s']
    trajectory=list(csv.DictReader((root/'agent_trajectory.csv').open()));t=np.array([float(x['simulation_time_s']) for x in trajectory]);xy=np.array([[float(x[k]) for k in ('x_m','y_m')] for x in trajectory]);v=np.array([float(x['v_m_s']) for x in trajectory])
    apps=[e for e in rows(root/'repair.jsonl') if e['event']=='PATH_APPLIED'];commands=rows(root/'phase20_commands.jsonl')
    inference={e['id']:e for e in rows(root/'model/inference.jsonl')};switches={e['id']:e for e in rows(root/'events.jsonl')};rec=rows(root/'reconstruction.jsonl')
    ec_installs=[e for e in rows(root/'exec_cert.jsonl') if e['event']=='INSTALL']
    install_meta=[e for e in rec if e['event']=='INSTALL_META'];ctes=[];raw_dist=[];heading=[];native_cache={};app_cursor=cmd_cursor=0;current=None;native=None;state_seconds=Counter();last_app=None
    def angle(path,pose):
        p=XYPath(path);s,_=p.project(pose[:2]);d=p.at(min(p.s[-1],s+.05))-p.at(s)
        return float(np.arctan2(d[1],d[0])) if np.linalg.norm(d)>1e-9 else None
    for j,a in enumerate(apps):
        if last_app is not None:
            before=angle(last_app['path_world'],a['pose']);after=angle(a['path_world'],a['pose'])
            if before is not None and after is not None:heading.append(abs((after-before+np.pi)%(2*np.pi)-np.pi))
        last_app=a
    for i in range(1,len(t)):
        left=t[i-1];dt=t[i]-left
        while cmd_cursor+1<len(commands) and commands[cmd_cursor+1]['time_s']<=left+1e-10:cmd_cursor+=1
        command=commands[cmd_cursor] if commands and commands[cmd_cursor]['time_s']<=left+1e-10 else None
        source=command['source'] if command else 'INITIAL_INFERENCE_WAIT';state_seconds[source]+=dt
        while app_cursor<len(apps) and apps[app_cursor]['simulation_time_s']<=left+1e-10:
            a=apps[app_cursor];current=XYPath(a['path_world']);native=None
            m=next((m for m in install_meta if m['id']==a['id'] and m['tick']==a['tick']),None)
            if m is not None and m.get('original_candidate_world') is not None:
                try:native=XYPath(m['original_candidate_world'])
                except ValueError:pass
            elif a['id'] in inference:
                source_event=switches.get(a['id'],{});chosen=source_event.get('phase16',{}).get('selection',{}).get('selected_sample')
                installed=next((e for e in ec_installs if e['id']==a['id'] and e['apply_tick']==a['tick']),None)
                if installed is not None:chosen=installed.get('selected_sample',chosen)
                file=root/'model/derived'/f"{a['id']:04d}.npz"
                if chosen is not None and file.exists():
                    key=(a['id'],chosen)
                    if key not in native_cache:
                        with np.load(file) as z:points=local_to_world(z['metric'][chosen],inference[a['id']]['observation_pose'])
                        try:native_cache[key]=XYPath(points)
                        except ValueError:native_cache[key]=None
                    native=native_cache[key]
            app_cursor+=1
        if current is not None and source in TRACK_STATES:
            ctes.append(current.project(xy[i])[1])
            if native is not None:raw_dist.append(native.project(xy[i])[1])
    dynamic=summary.get('dynamic_obstacle') or {};box_rows=dynamic.get('boxes')
    if box_rows is None:box_rows=[dynamic] if dynamic.get('spawn') else []
    observation=[]
    for i,box in enumerate(box_rows,1):
        spawn=box['spawn'];at=spawn['simulation_time_s'];installed=[a for a in apps if a['simulation_time_s']<at-1e-10]
        a=installed[-1] if installed else None;obs=inference.get(a['id']) if a else None
        # Spawn/evaluation precedes this tick's control: an install on the
        # same tick is not counted as the path already active at spawn.
        prior_commands=[x for x in commands if x['time_s']<at-1e-10];command=prior_commands[-1] if prior_commands else None
        valid=bool(a and command and command.get('path_source_id')==a['id'] and command['source'] in TRACK_STATES)
        observation.append(dict(box_number=i,spawn_s=at,path_id=a['id'] if valid else None,
            observation_s=obs['observation_sim_s'] if valid and obs else None,
            observed_before_spawn=bool(obs['observation_sim_s']<at) if valid and obs else None,
            installed_path_available=valid,command_source=command['source'] if command else None))
    elapsed_hold=0.;longest=0.;start=None
    for e in rec:
        if e['event']=='HOLD_REJECTED_START' and start is None:start=e['simulation_time_s']
        elif e['event']=='HOLD_REJECTED_END' and start is not None:
            dt=e['simulation_time_s']-start;elapsed_hold+=dt;longest=max(longest,dt);start=None
    if start is not None:elapsed_hold+=duration-start;longest=max(longest,duration-start)
    jobs=rows(root/'reconstruction_pool.jsonl');costs=[e['pool_wall_s'] for e in jobs if e.get('pool_wall_s') is not None]
    results=[e for e in rec if e['event']=='RESULT'];dispatch=[e for e in rec if e['event']=='DISPATCH'];applied=[e for e in results if e.get('applied')]
    counts=Counter(e['disposition'] for e in results);checks=[e for e in rows(root/'exec_cert.jsonl') if e['event']=='CHECK']
    return dict(stopped_s=float(np.sum(np.diff(t)[np.abs(v[1:])<.01])),command_state_seconds=dict(state_seconds),
        tracking_error_p50_m=q(ctes,.5),tracking_error_p95_m=q(ctes,.95),tracking_samples=len(ctes),
        chunk_heading_jump_p50_deg=None if not heading else q(heading,.5)*180/np.pi,chunk_heading_jump_p95_deg=None if not heading else q(heading,.95)*180/np.pi,
        raw_candidate_distance_mean_m=float(np.mean(raw_dist)) if raw_dist else None,raw_candidate_distance_samples=len(raw_dist),spawn_path_observations=observation,
        ec_checks=len(checks),ec_rejects=sum(not e['passed'] for e in checks),hold_after_rejection_s=elapsed_hold,hold_after_rejection_max_s=longest,
        graph_dispatches=len(dispatch),graph_applied=len(applied),graph_acceptance_rate=len(applied)/len(dispatch) if dispatch else None,
        graph_solve_p50_s=q(costs,.5),graph_solve_p95_s=q(costs,.95),graph_pool_times_s=costs,graph_dispositions=dict(counts),
        graph_prediction_errors_m=[e['prediction_error_m'] for e in results],graph_terminal_unapplied=sum(e['event']=='TERMINAL_UNAPPLIED' for e in rec),
        graph_late_results=sum(e['event']=='LATE_RESULT' for e in rec))

def audit(root):
    root=Path(root);r=frozen_audit(root);c=json.loads((root/'scenario.json').read_text());assert c['phase52p']
    assert r['detour_applied_count']==0 and r['g_dispatches']==0
    declaration=root/'declared_arrival.json'
    declared_id=json.loads(declaration.read_text())['id'] if declaration.exists() else None
    startup=waypoint_lifetime(rows(root/'controller.jsonl'),r['duration_s'],rows(root/'received.jsonl'),declared_id)
    r.update(extra(root));r.update(method=c['phase52p_method'],base_scene=r['scene'],scene=c['phase52p_level'],condition=c['phase52p_condition'])
    r.update(startup)
    states=r['command_state_seconds']
    # Raw command records remain byte-identical. This label is report-only.
    states['INITIAL_CHUNK_WAIT']=states.pop('INITIAL_INFERENCE_WAIT',0.)+states.pop('WAYPOINT_TIMEOUT',0.)
    for e in rows(root/'reconstruction.jsonl'):
        if e['event']=='RESULT' and e.get('applied'):assert e['tick']==e['apply_tick'] and e['disposition']=='ACCEPTED'
    summary=json.loads((root/'summary.json').read_text());assert summary['delivery_delay']['configured_additional_s']==c['phase52p_delay_s']
    return r
