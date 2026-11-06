"""Read-only command/pose accounting, reusable for smoke and the ten-run report."""
import csv
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from nomad_phase28.tracking import clip_command,na_duration
from .report import lines,read,quant,csv_write,save,stage_values


def clip_causes(raw,before,command,alpha=2.):
    expected,flags=clip_command(raw,before,alpha)
    np.testing.assert_allclose(expected,command,atol=1e-9,rtol=0)
    v,w=map(float,raw);pv,pw=before;eps=1e-12
    causes=dict(v_upper=flags['v_clipped'] and v>.3+eps,
        v_lower=flags['v_clipped'] and v< -eps,
        omega=flags['w_clipped'] and abs(w)>.4+eps,
        acceleration=flags['v_clipped'] and (v>pv+.5/9+eps or v<pv-.5/9-eps),
        angular_acceleration=flags['w_clipped'] and (w>pw+alpha/9+eps or w<pw-alpha/9-eps))
    assert any(causes.values())==flags['any_clipped']
    return causes,flags


def planned_pose(result,elapsed):
    q=np.asarray(result['poses']);times=np.r_[0.,np.cumsum(result['dt'])]
    return np.array([np.interp(elapsed,times,q[:,0]),np.interp(elapsed,times,q[:,1]),np.interp(elapsed,times,np.unwrap(q[:,2]))])


def classify(source,diag,v,detour_state,first_received):
    if not first_received:return 'FIRST_INFERENCE_WAIT'
    if source in ('ALIGN_ROTATE','ALIGN_BRAKE','RECOVER_ROTATE','RECOVER_BRAKE'):return source
    if source in ('DETOUR_WAIT','REPAIR_WAIT','STOP_WAIT'):return source
    if detour_state=='ACTIVE':return 'DETOUR_STOPPED' if abs(v)<.01 else 'DETOUR_MOVING'
    if diag.get('phase28_timed'):return 'H_STOPPED' if abs(v)<.01 else 'H_MOVING'
    if abs(v)>=.01:return 'NA_MOVING'
    return 'OTHER_STOP'


def analyze(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (root/'agent_trajectory.csv').open() as f:trace=list(csv.DictReader(f))
    t=np.array([float(r['simulation_time_s']) for r in trace]);dt=np.r_[0.,np.diff(t)];mid=t-dt/2
    pose=np.array([[float(r[k]) for k in ('x_m','y_m','yaw_rad')] for r in trace]);vel=np.array([float(r['v_m_s']) for r in trace])
    commands=lines(root/'phase20_commands.jsonl');ct=np.array([r['time_s'] for r in commands]);ci=np.searchsorted(ct,mid+1e-10,side='right')-1
    depth=lines(root/'phase20d_commands.jsonl');dtime=[r['time_s'] for r in depth];di=np.searchsorted(dtime,mid+1e-10,side='right')-1
    events=lines(root/'phase28_handoff.jsonl');applied=[e for e in events if e['event']=='APPLIED'];by_job={e['job_id']:e for e in applied}
    stages=defaultdict(list)
    for e in events:
        if e['event']=='TIMING_RESULT' and e.get('result'):
            for k,v in stage_values(e['result']).items():
                if v is not None:stages[k].append(v)
    csv_write(out/'stage_times.csv',[dict(stage=k,n=len(v),p50_s=quant(v),p95_s=quant(v,.95)) for k,v in stages.items()])
    hcommands=[e for e in events if e['event']=='COMMAND'];clips=[];combinations=Counter()
    cfg=read(root/'scenario.json');alpha=cfg.get('phase28_alpha',2.)
    for e in hcommands:
        d=e['diag'];causes,flags=clip_causes(d['raw_command'],e['before_vw'],e['command'],alpha)
        assert bool(d['any_clipped'])==flags['any_clipped']
        row=dict(time_s=e['simulation_time_s'],job_id=e['job_id'],case_id=e['case_id'],clipped=flags['any_clipped'],
            planned_v=d['feedforward'][0],planned_w=d['feedforward'][1],planned_v_at_upper=bool(d['feedforward'][0]>=.3-1e-7),
            raw_v=d['raw_command'][0],raw_w=d['raw_command'][1],actual_v=e['command'][0],actual_w=e['command'][1],**causes)
        clips.append(row)
        if row['clipped']:combinations['+'.join(k for k,v in causes.items() if v)]+=1
    counts=[dict(cause=k,count=sum(r[k] for r in clips),planned_v_at_upper=sum(r[k] and r['planned_v_at_upper'] for r in clips)) for k in ('v_upper','v_lower','omega','acceleration','angular_acceleration')]
    csv_write(out/'clip_commands.csv',clips);csv_write(out/'clip_causes.csv',counts)
    csv_write(out/'clip_combinations.csv',[dict(causes=k,count=v) for k,v in combinations.items()])
    budget=defaultdict(float);track=[];active=defaultdict(float);a_times=[r['simulation_time_s'] for r in applied]
    ai=np.searchsorted(a_times,mid+1e-10,side='right')-1
    for i in range(1,len(t)):
        c=commands[max(0,ci[i])];d=c.get('SP',{});ds=depth[di[i]].get('detour_state','NORMAL') if di[i]>=0 else 'NORMAL'
        first=int(trace[i]['incoming_waypoint_id'])>=0
        state=classify(c['source'],d,vel[i],ds,first);budget[state]+=float(dt[i])
        if d.get('phase28_timed') and ai[i]>=0:
            a=applied[ai[i]];job=a['job_id'];active[job]+=float(dt[i]);elapsed=t[i]-a['simulation_time_s']
            target=planned_pose(a['result'],elapsed);error=abs(float((target[2]-pose[i,2]+np.pi)%(2*np.pi)-np.pi))
            track.append(dict(time_s=float(t[i]),job_id=job,elapsed_s=float(elapsed),position_error_m=float(np.linalg.norm(target[:2]-pose[i,:2])),heading_error_deg=error*180/np.pi))
    assert abs(sum(budget.values())-t[-1])<1e-8
    budget_rows=[dict(state=k,seconds=v,fraction=v/t[-1]) for k,v in sorted(budget.items())]
    csv_write(out/'time_budget.csv',budget_rows);csv_write(out/'tracking_72hz.csv',track)
    paths=[e for e in lines(root/'repair.jsonl') if e['event']=='PATH_APPLIED'];schedules=[]
    for i,p in enumerate(paths):
        start=p['simulation_time_s'];end=paths[i+1]['simulation_time_s'] if i+1<len(paths) else float(t[-1]);kind=p['kind']
        a=next((e for e in applied if abs(e['simulation_time_s']-start)<1e-9),None) if kind=='HANDOFF' else None
        if a:
            planned=sum(a['result']['dt']);used=active[a['job_id']];completed=any(e['job_id']==a['job_id'] and e['diag']['completed'] for e in hcommands)
        else:
            try:
                schedule=na_duration(p['path_world'],p['pose'],p['previous_vw'][0])
                # Use the logged alignment decision: C0 and NA thresholds differ.
                turning=abs(np.deg2rad(p['heading_error_deg']))/.4+max(0.,p['previous_vw'][0])/.5 if p.get('alignment') else 0.
                planned=schedule['sp_time_s']+turning
            except (ValueError,IndexError):planned=None
            used=end-start;completed=any(start<=c['time_s']<end and c['SP'].get('completed') for c in commands)
        schedules.append(dict(kind=kind,start_s=start,end_s=end,planned_sum_dt_s=planned if a else None,
            na_ideal_full_schedule_s=planned if not a else None,actual_interval_s=end-start,active_execution_s=used,
            actual_minus_full_plan_s=used-planned if planned is not None else None,completed=completed,
            ended_before_full_plan=planned is not None and used<planned-1/72))
    csv_write(out/'path_schedules.csv',schedules)
    hand=[r for r in schedules if r['kind']=='HANDOFF'];fully=[r for r in hand if r['completed']]
    summary=dict(duration_s=float(t[-1]),stop_s=float(dt[abs(vel)<.01].sum()),stop_fraction=float(dt[abs(vel)<.01].sum()/t[-1]),
        alignment_rotation_s=budget.get('ALIGN_ROTATE',0.),alignment_brake_s=budget.get('ALIGN_BRAKE',0.),
        detour_execution_s=sum(v for k,v in budget.items() if k.startswith('DETOUR_') and k!='DETOUR_WAIT'),
        detour_wait_s=budget.get('DETOUR_WAIT',0.),h_commands=len(clips),clip_count=sum(r['clipped'] for r in clips),
        clip_fraction=sum(r['clipped'] for r in clips)/len(clips) if clips else None,
        clipped_with_planned_v_at_upper=sum(r['clipped'] and r['planned_v_at_upper'] for r in clips),
        position_error_p50_m=quant([r['position_error_m'] for r in track]),position_error_p95_m=quant([r['position_error_m'] for r in track],.95),
        heading_error_p50_deg=quant([r['heading_error_deg'] for r in track]),heading_error_p95_deg=quant([r['heading_error_deg'] for r in track],.95),
        tracking_samples=len(track),h_paths=len(hand),h_completed_paths=len(fully),h_ended_before_plan=sum(r['ended_before_full_plan'] for r in hand),
        h_sum_full_plan_s=sum(r['planned_sum_dt_s'] for r in hand),h_sum_active_s=sum(r['active_execution_s'] for r in hand),
        completed_actual_minus_plan_p50_s=quant([r['actual_minus_full_plan_s'] for r in fully]))
    save(out/'analysis.json',summary)
    return summary,budget_rows,counts,schedules
