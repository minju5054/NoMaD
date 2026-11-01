"""Fixed snapshot metrics/decisions, with explicit direction and pair denominators."""
import math
import numpy as np
from nomad_phase0.graph_v4 import menger
from .rollout import simulate,evaluate


def shape_metrics(path,case):
    p=np.asarray(path);k=menger(p)[0];edge=p[-1]-p[-2];u=np.asarray(case['u_ref']);normal=np.array([-u[1],u[0]])
    angle=(np.arctan2(edge[1],edge[0])-np.arctan2(u[1],u[0])+np.pi)%(2*np.pi)-np.pi
    return dict(curvature_rms=float(np.sqrt(np.mean(k*k))),curvature_max=float(np.max(np.abs(k))),delta_curvature_rms=float(np.sqrt(np.mean(np.diff(k)**2))),
        heading_error_rad=abs(float(angle)),lateral_error_m=abs(float((p[-1]-np.asarray(case['anchor_xy']))@normal)))


def side_choice(path,case,footprint_pass=False):
    if not case['appearance_available']:return dict(side=None,side_source='NO_ACTIVE_BOX',wide_side=None,wide_choice=None)
    p=np.asarray(path);box=case['spawn']['obstacle'];x,y=box['center_xy_m'];hx,hy=np.asarray(box['size_xyz_m'][:2])/2;r=case['oracle_config']['agent_radius_m'];front=x+hx+r if footprint_pass else x-hx
    side=None;source='NOT_REACHED'
    for a,b in zip(p[:-1],p[1:]):
        if a[0]<front<=b[0] and b[0]>a[0]:
            crossing=a[1]+(b[1]-a[1])*(front-a[0])/(b[0]-a[0]);side='+Y' if crossing>y+1e-9 else '-Y' if crossing<y-1e-9 else None;source='REAR_FOOTPRINT_CROSSING' if footprint_pass else 'FRONT_FACE_CROSSING';break
    if side is None and not footprint_pass and abs(p[-1,1]-y)>=hy+r+.025 and p[-1,0]>case['B'][0]:side='+Y' if p[-1,1]>y else '-Y';source='ENDPOINT_IN_GAP'
    half=case['oracle_config']['corridor']['half_width'];left=half-(y+hy);right=y-hy+half;wide='+Y' if left>right+1e-9 else '-Y' if right>left+1e-9 else None
    return dict(side=side,side_source=source,wide_side=wide,wide_choice=side==wide if side and wide else None)


def characterize(case,method,plan):
    row=dict(case_id=case['case_id'],scene=case['scene'],index=case['index'],source_method=case['method'],method=method,accepted=bool(plan['accepted']),disposition=plan['disposition'],
        compute_s=plan['compute_s'],over_1s=plan['compute_s']>1.,planning_failed=not plan['accepted'])
    result=None
    if plan['accepted']:
        path=plan['path'];row.update(shape_metrics(path,case));row.update(side_choice(path,case));result=evaluate(simulate(case['B'],path,case['previous_vw'][0]),case['oracle_config'])
        row.update({k:result[k] for k in ('completed','completion_time_s','duration_s','jerk_rms','omega_saturation_fraction','tracking_rms','tracking_max','distance_m','termination','oracle_minimum_clearance_m','oracle_collision','oracle_conservative_negative','safe_completion')})
        row['executed_side']=side_choice(result['poses'][:,:2],case,True)['side'];row['depth_clearance_m']=plan.get('depth_clearance_m');row['max_p0_distance_m']=plan.get('max_p0_distance_m')
        end=result['poses'][-1];u=np.array(case['u_ref']);row['actual_end_heading_error_rad']=abs(float((end[2]-np.arctan2(u[1],u[0])+np.pi)%(2*np.pi)-np.pi));row['actual_end_lateral_error_m']=abs(float((end[:2]-np.array(case['anchor_xy']))@np.array([-u[1],u[0]])))
    return row,result


def decision(rows,p2='P2',p3='P3',N=None):
    by={(r['case_id'],r['method']):r for r in rows};ids=sorted({r['case_id'] for r in rows});N=len(ids) if N is None else N
    rr={m:[by[(i,m)] for i in ids if (i,m) in by] for m in ('P0',p2,p3)}
    collision=lambda m:sum(r.get('oracle_collision',False) for r in rr[m]);fails=lambda m:sum(r['planning_failed'] for r in rr[m])/N if N else 1.
    c1=N>0 and collision(p2)<=collision('P0') and collision(p2)<=collision(p3) and fails(p2)<=fails('P0')+.05+1e-12
    side_ids=[i for i in ids if by.get((i,'P0'),{}).get('side') in ('+Y','-Y')]
    same=sum(by.get((i,p2),{}).get('side')==by[i,'P0']['side'] for i in side_ids);c2=bool(side_ids) and same/len(side_ids)>=.9
    common=[i for i in ids if all(by.get((i,m),{}).get('safe_completion',False) for m in ('P0',p2,p3))]
    def median(m,k):return float(np.median([by[i,m][k] for i in common])) if common else None
    med={m:{k:median(m,k) for k in ('completion_time_s','jerk_rms','heading_error_rad','lateral_error_m')} for m in ('P0',p2,p3)}
    c3=bool(common) and med[p2]['completion_time_s']<=med['P0']['completion_time_s']*1.05
    c4=bool(common) and med[p2]['jerk_rms']<=.7*med['P0']['jerk_rms'] and med[p2]['jerk_rms']<med[p3]['jerk_rms']
    c5=bool(common) and all(med[p2][k]<med['P0'][k] and med[p2][k]<med[p3][k] for k in ('heading_error_rad','lateral_error_m'))
    flags=dict(i=bool(c1),ii=bool(c2),iii=bool(c3),iv=bool(c4),v=bool(c5));label='REFINE_READY' if all(flags.values()) else 'REFINE_PARTIAL' if c1 and c2 and any((c3,c4,c5)) else 'REFINE_NOT_BETTER'
    return dict(label=label,LOW_N=N<15,snapshot_n=N,criteria=flags,side_n=len(side_ids),same_side=same,common_completion_n=len(common),common_ids=common,medians=med,
        collisions={m:collision(m) for m in rr},failure_fraction={m:fails(m) for m in rr})
