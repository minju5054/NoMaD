"""Reuse Phase21 audit; exact OBB and executed-window metrics for Phase22."""
import inspect,json,types
from collections import Counter
from pathlib import Path
import numpy as np
import nomad_phase21.metrics as previous
from nomad_phase0.chunk_report import trace
from .drive_config import place,triggered
from .drive_geometry import bounds,swept_gap

source=inspect.getsource(previous.core_audit)
old="g=swept_clearance(poses[tick-1],v,w,1/72,lo,hi,c['agent_radius_m'])"
assert source.count(old)==1
source=source.replace(old,"g=swept_gap(poses[tick-1],v,w,1/72,spawn['obstacle'],c['agent_radius_m'])")
namespace={**previous.__dict__,'place':place,'triggered':triggered,'swept_gap':swept_gap,'obstacle_bounds':lambda c:bounds(c['obstacle'])}
exec(compile(source,__file__,'exec'),namespace)
base_audit=types.FunctionType(previous.audit.__code__,{**previous.audit.__globals__,'core_audit':namespace['core_audit']})
rows=previous.rows


def audit(run):
    run=Path(run);result=base_audit(run);summary=json.loads((run/'summary.json').read_text());method=summary['scenario']['phase22_method'];rec,poses=trace(run)
    detours=rows(run/'detour.jsonl');controls=rows(run/'controller.jsonl');box=rows(run/'dynamic/clearance.jsonl');wall=rows(run/'clearance.jsonl')
    applied={r['job_id']:r for r in detours if r['event']=='APPLIED'};ends={r['job_id']:r for r in detours if r['event']=='END'};triggers={r['job_id']:r for r in detours if r['event']=='TRIGGER'}
    results={r['job_id']:r for r in detours if r['event']=='RESULT'};windows=[];interval_mask=np.zeros(len(rec)-1,dtype=bool);control_groups=[];handover=[]
    passage=result['spawn_s']+result['box_passage_time_s'] if result['passed_box'] else None
    branch_selected=Counter();branch_applied=Counter();branch_executed=Counter();branch_by_job={}
    for identity,r in results.items():
        numeric=r.get('numeric_result') or {};branch=numeric.get('branch','NONE') if method=='P2F_ASTAR_GRAPH' else 'ASTAR' if method=='P0_ASTAR' else 'GRAPH'
        branch_by_job[identity]=branch;branch_selected[branch]+=1
        if identity in applied:branch_applied[branch]+=1
    for identity,a in applied.items():
        end=ends.get(identity);start_tick=round(a['simulation_time_s']*72);end_tick=round(end['simulation_time_s']*72) if end else len(rec)-1
        if end_tick>start_tick:branch_executed[branch_by_job.get(identity,'NONE')]+=1
        interval_mask[start_tick:end_tick]=True;windows.append(dict(job_id=identity,start_tick=start_tick,end_tick=end_tick,termination=end['reason'] if end else 'RUN_TERMINAL_CENSORED'))
        group=[c for c in controls if start_tick<=round(c['simulation_time_s']*72)<end_tick];control_groups.append(group)
        if end:
            target=end_tick+216;u=np.asarray(triggers[identity]['u_ref']);available=min(target,len(rec)-1)
            progress=float((poses[available,:2]-poses[end_tick,:2])@u);next_trigger=next((t for t in detours if t['event']=='TRIGGER' and t['simulation_time_s']>end['simulation_time_s'] and (passage is None or t['simulation_time_s']<passage)),None)
            handover.append(dict(job_id=identity,end_s=end['simulation_time_s'],u_ref=u.tolist(),full3s=target<len(rec),observed_s=(available-end_tick)/72,progress_m=progress,reblock=next_trigger is not None,next_trigger_s=next_trigger['simulation_time_s'] if next_trigger else None))
    v=np.array([float(r['v_m_s']) for r in rec[1:]]);w=np.array([float(r['w_rad_s']) for r in rec[1:]]);moving=interval_mask&(np.abs(v)>1e-6);curvature=w[moving]/v[moving]
    jerk=[]
    for group in control_groups:
        ww=np.array([float(rec[round(c['simulation_time_s']*72)+1]['w_rad_s']) for c in group]);jerk.extend((np.diff(ww,n=2)*81).tolist())
    box_by_end={round(r['end_sim_s']*72):r for r in box};wall_by_end={round(r['end_sim_s']*72):r for r in wall}
    boxes=[];walls=[]
    for index in np.flatnonzero(interval_mask)+1:
        if index in box_by_end:boxes.append(box_by_end[index]['lower_m'])
        if index in wall_by_end:walls.append(previous.corridor_arc_minimum(poses[index-1],v[index-1],w[index-1],1/72,summary['scenario']['corridor'],summary['scenario']['agent_radius_m']))
    backend=rows(run/'repair_pool_jobs.jsonl');branch_events=rows(run/'refinement_branches.jsonl');times=[]
    for job in backend:
        assert not job.get('error'),job.get('error')
        for stage in (job.get('stage_results') or {}).values():
            for attempt in (stage or {}).get('results',[]):assert not attempt.get('error'),attempt.get('error')
    dispatch={r['job_id']:r['dispatch_ns'] for r in triggers.values()}
    for e in branch_events:
        if e['event']=='DELIVERED' and e.get('branch')!='R2' and e['job_id'] in dispatch:times.append((e['decision_ns']-dispatch[e['job_id']])/1e9)
    if method!='P2F_ASTAR_GRAPH':times=[r['wait_s'] for r in results.values()]
    result.update(method=method,detour_windows=windows,detour_execution_s=float(interval_mask.sum()/72),detour_rotation_s=float(np.sum(interval_mask&(np.abs(v)<=1e-6))/72),
        detour_minimum_box_clearance_m=min(boxes,default=None),detour_minimum_wall_clearance_m=min(walls,default=None),detour_minimum_clearance_m=min(boxes+walls,default=None),
        detour_execution_jerk_rms=float(np.sqrt(np.mean(np.square(jerk)))) if jerk else None,detour_execution_curvature_rms=float(np.sqrt(np.mean(curvature*curvature))) if len(curvature) else None,
        handovers=handover,handover_reblock_count=sum(h['reblock'] for h in handover),handover_3s_progress_mean_m=float(np.mean([h['progress_m'] for h in handover if h['full3s']])) if any(h['full3s'] for h in handover) else None,
        branch_selections=dict(branch_selected),branch_applications=dict(branch_applied),branch_executed=dict(branch_executed),GRAPH_FALLBACK_used=bool(branch_executed['GRAPH_FALLBACK']),branch_decision_latency_s=previous.stats(times),
        branch_backend_times_s=[(j.get('backend_end_ns',j['end_ns'])-dispatch[j['job_id']])/1e9 for j in backend if j['kind']=='R3' and j['job_id'] in dispatch],branch_decision_times_s=times,
        branch_backend_time_s=previous.stats([(j.get('backend_end_ns',j['end_ns'])-dispatch[j['job_id']])/1e9 for j in backend if j['kind']=='R3' and j['job_id'] in dispatch]))
    return result
