"""Descriptive saved-log analysis only; never changes primary metrics/labels."""
import csv
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from nomad_j0.report import csv_write
from .config import ROOT,SCENES,METHODS

def rows(path):
    path=Path(path)
    return [json.loads(x) for x in path.read_text().splitlines() if x] if path.exists() else []

def median(items):
    values=[float(x) for x in items if x is not None]
    return float(np.median(values)) if values else None

def horizon_metrics(t,xy,velocity,controls,last):
    end=float(t[last]);duration=end-float(t[0]);dt=np.diff(t[:last+1]);distance=float(np.linalg.norm(np.diff(xy[:last+1],axis=0),axis=1).sum())
    stop=float(dt[np.abs(velocity[1:last+1])<1e-12].sum())
    times=np.array([r['simulation_time_s'] for r in controls],float)
    weights=np.maximum(0.,np.minimum(np.r_[times[1:],t[-1]],end)-times)
    active=np.array([r.get('valid',False) and r['pure_pursuit'].get('stop_reason') is None for r in controls],bool)
    # Actual CURV target, not a low command caused only by acceleration or EC.
    slow=np.array([r.get('stage2',{}).get('v_target_m_s') is not None and
                   0<float(r['stage2']['v_target_m_s'])<.3-1e-12 for r in controls],bool)&active
    active_time=float(weights[active].sum());slow_time=float(weights[slow].sum())
    return dict(duration_s=duration,mean_speed_m_s=distance/duration if duration>0 else None,distance_m=distance,
        stop_s=stop,curvature_slow_s=slow_time,active_PP_s=active_time,
        curvature_slow_fraction_active=slow_time/active_time if active_time else None,
        curvature_slow_fraction_total=slow_time/duration if duration else None)

def exploratory_pairs(records):
    lookup={(r['scene'],r['index'],r['method']):r for r in records if r.get('technical_validation')=='PASS'}
    detail=[]
    for (scene,index,method),a in lookup.items():
        if method!='OURS':continue
        for other in ('OURS-noGRAPH','NOMAD_RAW'):
            b=lookup.get((scene,index,other))
            if b is None:continue
            ac=a['checkpoint_time_s'];bc=b['checkpoint_time_s'];sa=bool(a['collision'] or a['wall_intrusion']);sb=bool(b['collision'] or b['wall_intrusion'])
            detail.append(dict(scene=scene,index=index,comparator=other,OURS_success=bool(a['success']),other_success=bool(b['success']),
                success_difference=int(a['success'])-int(b['success']),OURS_safety_failure=sa,other_safety_failure=sb,safety_difference=int(sa)-int(sb),
                OURS_checkpoint_s=ac,other_checkpoint_s=bc,checkpoint_difference_s=float(ac-bc) if ac is not None and bc is not None else None))
    summary=[]
    for scene in (*SCENES,'ALL'):
        for other in ('OURS-noGRAPH','NOMAD_RAW'):
            rr=[r for r in detail if r['comparator']==other and (scene=='ALL' or r['scene']==scene)]
            cp=[r['checkpoint_difference_s'] for r in rr if r['checkpoint_difference_s'] is not None]
            summary.append(dict(scene=scene,comparator=other,pairs=len(rr),
                OURS_only_success=sum(r['OURS_success'] and not r['other_success'] for r in rr),other_only_success=sum(r['other_success'] and not r['OURS_success'] for r in rr),
                success_difference=sum(r['success_difference'] for r in rr),
                OURS_only_safety_failure=sum(r['OURS_safety_failure'] and not r['other_safety_failure'] for r in rr),
                other_only_safety_failure=sum(r['other_safety_failure'] and not r['OURS_safety_failure'] for r in rr),
                safety_difference=sum(r['safety_difference'] for r in rr),checkpoint_pairs=len(cp),
                checkpoint_mean_difference_s=float(np.mean(cp)) if cp else None,checkpoint_median_difference_s=median(cp)))
    return detail,summary

def generate(records,out,make_figures=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);runrows=[];stop_positions=[];ec_rows=[];errors=[]
    for r in records:
        if r.get('technical_validation')!='PASS':continue
        run=Path(r['output']);trace=run/'agent_trajectory.csv';control_file=run/'controller.jsonl'
        if not trace.exists() or not control_file.exists():
            errors.append(dict(key=r['key'],reason='MISSING_SAVED_LOG'));continue
        with trace.open() as f:rr=list(csv.DictReader(f))
        t=np.array([float(x['simulation_time_s']) for x in rr]);xy=np.array([[float(x['x_m']),float(x['y_m'])] for x in rr]);v=np.array([float(x['v_m_s']) for x in rr])
        controls=rows(control_file);full=horizon_metrics(t,xy,v,controls,len(t)-1)
        cp=r.get('checkpoint_time_s');cp_tick=round(cp*72) if cp is not None else None
        if cp_tick is not None:assert 0<=cp_tick<len(t) and abs(t[cp_tick]-cp)<1e-9
        checkpoint=horizon_metrics(t,xy,v,controls,cp_tick) if cp_tick is not None else None
        row=dict(key=r['key'],scene=r['scene'],index=r['index'],method=r['method'],checkpoint_observed=cp is not None,
                 input_sha256={str(trace):sha256_file(trace),str(control_file):sha256_file(control_file)})
        row.update({'full_'+k:value for k,value in full.items()})
        row.update({'checkpoint_'+k:checkpoint[k] if checkpoint else None for k in full})
        runrows.append(row)
        if r['method']=='OURS':
            checks=[x for x in rows(run/'exec_cert.jsonl') if x['event']=='CHECK']
            for scope in ('SAFE_INSTALL','GRAPH_INSTALL','PERIODIC'):
                vv=[x for x in checks if x['scope']==scope]
                ec_rows.append(dict(scene=r['scene'],index=r['index'],key=r['key'],scope=scope,checks=len(vv),rejected=sum(not x['passed'] for x in vv)))
            if r['scene']=='H1-v3' and r['timeout']:
                stopped=np.flatnonzero(np.abs(v)<1e-12);last=int(stopped[-1]) if len(stopped) else None
                first=last
                while first is not None and first>0 and abs(v[first-1])<1e-12:first-=1
                stop_positions.append(dict(index=r['index'],key=r['key'],final_x_m=float(xy[-1,0]),final_y_m=float(xy[-1,1]),
                    final_goal_distance_m=float(rr[-1]['goal_distance_m']),stationary_at_end=bool(abs(v[-1])<1e-12),
                    last_stop_x_m=float(xy[last,0]) if last is not None else None,last_stop_y_m=float(xy[last,1]) if last is not None else None,
                    last_stop_start_s=float(t[first]) if first is not None else None,last_stop_end_s=float(t[last]) if last is not None else None,
                    total_stop_s=full['stop_s']))
    summary=[]
    names=('mean_speed_m_s','curvature_slow_fraction_active','curvature_slow_fraction_total','stop_s','distance_m')
    for scene in (*SCENES,'ALL'):
        for method in METHODS:
            rr=[r for r in runrows if r['method']==method and (scene=='ALL' or r['scene']==scene)]
            item=dict(scene=scene,method=method,valid_runs=len(rr),checkpoint_runs=sum(r['checkpoint_observed'] for r in rr))
            for scope in ('checkpoint','full'):
                for name in names:item[scope+'_'+name+'_median']=median([r[scope+'_'+name] for r in rr])
            summary.append(item)
    ec_summary=[]
    for scene in (*SCENES,'ALL'):
        for scope in ('SAFE_INSTALL','GRAPH_INSTALL','PERIODIC','ALL'):
            rr=[r for r in ec_rows if (scene=='ALL' or r['scene']==scene) and (scope=='ALL' or r['scope']==scope)]
            count=sum(r['checks'] for r in rr);rejected=sum(r['rejected'] for r in rr)
            ec_summary.append(dict(scene=scene,scope=scope,checks=count,rejected=rejected,reject_fraction=rejected/count if count else None))
    pair_detail,pair_summary=exploratory_pairs(records)
    pictures=[]
    if make_figures:
        from nomad_slwv2.figures import plot_run
        for r in records:
            if r['scene']!='H1-v3' or r['method'] not in ('OURS','OURS-noGRAPH','NOMAD_RAW') or not 231<=r['index']<=238:continue
            path=ROOT/'docs/figures/j1_interim'/f"H1-v3_{r['index']}_{r['method']}.png"
            pictures.append(plot_run(r['output'],dict(r,scene=f"H1-v3 / {r['method']}"),path))
    for name,data in [('exploratory_runs',runrows),('exploratory_summary',summary),('exploratory_pairs',pair_detail),
                      ('exploratory_paired_summary',pair_summary),('ours_ec_rejections',ec_rows),('ours_ec_summary',ec_summary),('h1v3_ours_timeout_positions',stop_positions)]:
        csv_write(out/(name+'.csv'),data)
    result=dict(scope='EXPLORATORY_ONLY_NOT_PRIMARY',summary=summary,paired_summary=pair_summary,ours_ec=ec_summary,
                h1v3_timeout_positions=stop_positions,figures=pictures,data_errors=errors,
                definitions=dict(speed='saved path distance / elapsed time, including stops',stop='|actual v|<1e-12,72Hz intervals',
                    curvature_slow='active PP only,0<v_target<0.3m/s; acceleration-only low speed and EC_BRAKE excluded',
                    horizons='checkpoint if reached,otherwiseN/A; full-run counterparts shown separately',
                    aggregation='median of per-run metrics; no extra tests/corrections',figures='H1-v3,231–238,OURS/OURS-noGRAPH/NOMAD_RAW only'))
    atomic_json(out/'exploratory.json',result);return result
