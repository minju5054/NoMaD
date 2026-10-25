"""Original Phase9 replay plus saved-log route and short-chunk diagnostics."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.async_report import rows,stats
from nomad_isaac.common import sha256_file
from nomad_phase0.chunk_report import trace
from nomad_phase8.metrics import audit as original_audit
from .config import protocol


def wrap(a):return (a+np.pi)%(2*np.pi)-np.pi


def route_windows(times,poses):
    """Sample-held 72Hz intervals; final sample never creates extra time."""
    t=np.asarray(times);p=np.asarray(poses);dt=np.diff(t)
    assert len(t)==len(p) and np.all(dt>0)
    mask=abs(wrap(p[:-1,2]))>=np.deg2rad(150)-1e-12
    starts=np.flatnonzero(mask & ~np.r_[False,mask[:-1]])
    ends=np.flatnonzero(mask & ~np.r_[mask[1:],False])
    events=[]
    for a,b in zip(starts,ends):
        duration=float(t[b+1]-t[a])
        if duration>=2-1e-10:
            events.append(dict(start_s=float(t[a]),end_s=float(t[b+1]),duration_s=duration,
                               start_x_m=float(p[a,0]),start_y_m=float(p[a,1]),start_yaw_rad=float(p[a,2])))
    near=p[:,0]>6.5
    return dict(backtracking_events=events,backtracking_count=len(events),
        near_goal_max_abs_y_m=float(abs(p[near,1]).max()) if near.any() else None,
        near_goal_left_time_s=float(dt[(p[:-1,0]>6.5)&(p[:-1,1]>1.)].sum()),
        near_goal_time_s=float(dt[p[:-1,0]>6.5].sum()))


def route_metrics(run,success):
    run=Path(run);rr,pose=trace(run);t=np.array([float(r['simulation_time_s']) for r in rr]);ctrl=rows(run/'controller.jsonl')
    ct=np.array([c['simulation_time_s'] for c in ctrl]);dt=np.maximum(0,np.r_[ct[1:],t[-1]]-ct)
    valid=np.array([c['valid'] and c['pure_pursuit']['stop_reason'] is None and not c['pure_pursuit'].get('endpoint_stop',False) for c in ctrl],dtype=bool)
    slow=np.array([(c['stage2'].get('v_target_m_s') or .3)<.2-1e-12 for c in ctrl])
    actual=np.array([c['commanded_v_m_s']<.2-1e-12 for c in ctrl]);clamp=np.array([bool(c['pure_pursuit'].get('endpoint_clamped')) for c in ctrl])
    den=dt[valid].sum()
    def fraction(mask):return float(dt[valid&mask].sum()/den) if den else None
    request={r['id']:r for r in rows(run/'requests.jsonl')};events={r['id']:r for r in rows(run/'events.jsonl')};series=[]
    for r in rows(run/'model/inference.jsonl'):
        tm=r['topomap'];q=request[r['id']]
        series.append(dict(id=r['id'],observation_sim_s=q['observation_sim_s'],switch_sim_s=events.get(r['id'],{}).get('application_sim_s'),
                           closest_node=tm['closest_node'],subgoal=tm['selected_subgoal_id']))
    return dict(**route_windows(t,pose),duration_s=float(t[-1]),final_pose=pose[-1].tolist(),
        failure_time_s=None if success else float(t[-1]),failure_pose=None if success else pose[-1].tolist(),
        curv_slow_fraction=fraction(slow),actual_speed_below_point2_fraction=fraction(actual),endpoint_clamp_fraction=fraction(clamp),active_pp_time_s=float(den),
        closest_backwards=sum(b['closest_node']<a['closest_node'] for a,b in zip(series,series[1:])),
        subgoal_backwards=sum(b['subgoal']<a['subgoal'] for a,b in zip(series,series[1:])),topomap_series=series,
        topomap_failure_last10=[] if success else [r for r in series if t[-1]-10<=r['observation_sim_s']<=t[-1]])


def x_bin(x):
    if 0<=x<2:return '0–2'
    if 2<=x<4:return '2–4'
    if 4<=x<6:return '4–6'
    if 6<=x<=8:return '6–8'
    return 'OUTSIDE'


def graph_calls(run,record,dataset):
    """Consumes existing results only. No Graph import, construction or solve."""
    data=rows(Path(run)/'stage2_graph.jsonl');results={x['job_id']:x for x in data if x['event']=='RESULT'}
    terminal={x['job_id'] for x in data if x['event']=='TERMINAL_UNAPPLIED'};calls=[]
    end=record['duration_s'];is_failure=not record['success']
    for j in data:
        if j['event']!='SUBMIT':continue
        r=results.get(j['job_id'],{});solver=r.get('solver');xy=np.asarray(j['world_xy']);b=np.asarray(j['boundary']);f=np.array([np.cos(b[2]),np.sin(b[2])])
        nlength=float(np.linalg.norm(np.diff(xy,axis=0),axis=1).sum());out=np.asarray(r['poses'])[:,:2] if 'poses' in r else None
        calls.append(dict(dataset=dataset,key=record['key'],method=record['method'],index=record['index'],delay_s=record['delay_s'],
            job_id=j['job_id'],fresh_id=j['id'],time_s=j['switch_sim_s'],boundary_x_m=float(b[0]),observation_x_m=j['observation_pose'][0],x_bin=x_bin(b[0]),
            fresh_length_m=nlength,short=nlength<.25,solver_ran=solver is not None,
            nonconverged=bool(solver and not solver['success']),solver_success=solver['success'] if solver else None,
            initialization_rejected=bool(r.get('initialization_rejected')),initialization_error=r.get('error'),
            disposition=r.get('disposition','TERMINAL_UNAPPLIED' if j['job_id'] in terminal else 'MISSING_RESULT'),
            accepted=r.get('disposition')=='ACCEPTED',progress_cost=solver['factor_costs'].get('endpoint_progress') if solver else None,
            fresh_endpoint_forward_m=float((xy[-1]-b[:2])@f),
            corrected_endpoint_forward_m=float((out[-1]-b[:2])@f) if out is not None else None,
            endpoint_edit_forward_m=float((out[-1]-xy[-1])@f) if out is not None else None,
            failure_last10=bool(is_failure and max(0,end-10)<=j['switch_sim_s']<=end),
            public_obstacle_count=len(j['public_config']['obstacles']),intent_active=bool(j['public_config'].get('public_intent'))))
    return calls


def audit(run,run_id,offset,delay):
    run=Path(run);c=json.loads((run/'scenario.json').read_text());prov=json.loads((run/'provenance.json').read_text())
    assert c.get('phase10b_no_obstacle') is True and prov.get('phase10b_no_obstacle') is True
    assert c['overnight_phase']==9 and c['overnight_method'] in ('CURV','GRAPH-v6')
    assert c['obstacles']==[] and 'dynamic_obstacle' not in c and 'diagnostic_y_offset_m' not in c
    assert 1<=int(run_id[-2:])<=4 and delay in (0.,.75)
    assert json.loads((run/'phase10b_protocol.json').read_text())==protocol()
    assert not (run/'dynamic').exists() and not (run/'oracle_information.json').exists()
    assert rows(run/'overnight_oracle.jsonl')==[]
    render=json.loads((run/'render_check.json').read_text());assert render['obstacle_count']==0
    assert render['straight_corridor_floor_xy_bounds']==[[-1.,-1.5],[9.,1.5]]
    r=original_audit(run,run_id,offset,delay)
    for e in rows(run/'events.jsonl'):
        assert e['overnight']['public_obstacle_ids']==[] and e['overnight']['intent'] is None and e['overnight']['oracle_gate'] is None
    for j in rows(run/'stage2_graph.jsonl'):
        if j['event']=='SUBMIT':assert j['public_config']['obstacles']==[] and j['public_config']['public_intent'] is None
        if 'solver' in j:assert 'heuristic_intent_xy' not in j['solver']['factor_costs'] and j['solver']['exact_path_certificate']['obstacle_clearance_m'] is None
    r['route']=route_metrics(run,r['success']);r['phase10b_no_obstacle']=True
    for name in ('phase10b_protocol.json','render_check.json'):
        r['input_log_sha256'][name]=sha256_file(run/name)
    return r
