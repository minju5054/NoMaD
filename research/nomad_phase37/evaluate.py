"""One fixed offline replay on common saved-map decision opportunities."""
import argparse,csv,json,time,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT
from nomad_isaac.topomap import candidate_range,select_subgoal
from nomad_phase24r.trigger import choose_ahead,component_sets,approach_progress
from nomad_phase20c.detour_known import radial_reference
from nomad_phase32o.evaluate import save,csvout
from . import audit
from .trig import ObservedTrigger
from .topo import possible_query
from .geometry import Reference,polygon,classify

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase37'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return audit.read(p)
def lines(p):return audit.lines(p)


def load_run(r):
    root=Path(r['output']);cfg=read(root/'scenario.json');summary=read(root/'summary.json');geometry=read(root/'geometry_check.json')
    with audit.register(root/'agent_trajectory.csv').open() as f:tr=list(csv.DictReader(f))
    poses=np.array([[float(x[k]) for k in ('x_m','y_m','yaw_rad')] for x in tr])
    manifest=read(cfg['topomap_manifest']);reference=Reference([n['world_pose'] for n in manifest['nodes']])
    static=[(b['id'],polygon(b)) for b in cfg['obstacles']]
    for name,(lo,hi) in geometry['bounds'].items():
        lo=np.array(lo[:2]);hi=np.array(hi[:2]);static.append((name,np.array([lo,[hi[0],lo[1]],hi,[lo[0],hi[1]]])))
    dynamic=summary.get('dynamic_obstacle') or {};items=dynamic.get('boxes') or ([dynamic] if dynamic.get('spawn') else [])
    boxes=[]
    for item in items:
        spawn=item['spawn'];box=spawn['obstacle'];passage=(item.get('evaluation') or {}).get('passage')
        boxes.append(dict(id=box['id'],polygon=polygon(box),spawn_s=spawn['simulation_time_s'],passage_s=passage['simulation_time_s'] if passage else None))
    return root,cfg,poses,reference,static,boxes


def eligible(c,tick,triggers,ends,last_tick):
    # Both rules see the same logged action state. No counterfactual R3 wait
    # duration/trajectory is invented; this is a predicate replay, not driving.
    if tick<216:return False
    if any(e['trigger']=='B' and round(e['simulation_time_s']*72)==tick for e in triggers):return True
    for e in triggers:
        start=round(e['simulation_time_s']*72);end=ends.get(e['job_id'],last_tick)
        if start<=tick<=end:return False
    if any(end<=tick<end+216 for end in ends.values()):return False
    phase=c.get('phase20',{});recovery=c.get('phase17_recovery',{}).get('state')
    return recovery=='NORMAL' and phase.get('pending_job') is None and phase.get('source') not in ('ALIGN_BRAKE','ALIGN_ROTATE','REPAIR_WAIT')


def trigger_run(r):
    root,cfg,poses,reference,static,boxes=load_run(r)
    controls=lines(root/'controller.jsonl');events=lines(root/'detour.jsonl');updates=lines(root/'depth/updates.jsonl')
    conditions={e['tick']:e for e in events if e['event']=='NEW_OBSTACLE_CONDITION'}
    triggers=[e for e in events if e['event']=='TRIGGER'];ends={e['job_id']:round(e['simulation_time_s']*72) for e in events if e['event']=='END'}
    byframe={u['frame_id']:u for u in updates};copies={}
    for file in sorted((root/'repair_jobs').glob('input_*.npz')):
        m=audit.metadata(file);copies[(m['frame_id'],m['sim_s'])]=file
    def resolve(meta):
        f=Path(meta['file']);return f if f.exists() else copies.get((meta['frame_id'],meta['sim_s']))
    tracker=ObservedTrigger();last_file=None;field=None;rows=[];counts=Counter();legacy_cache={}
    for c in controls:
        tick=round(c['simulation_time_s']*72);gate_record=conditions.get(tick)
        meta=gate_record['snapshot'] if gate_record else byframe.get(c.get('phase20d',{}).get('depth_frame'))
        available=resolve(meta) if meta else None
        allowed=eligible(c,tick,triggers,ends,len(poses)-1)
        counts['all_control_ticks']+=1;counts['eligible_ticks']+=allowed
        if available is None:
            counts['map_missing_ticks']+=1;counts['eligible_map_missing_ticks']+=allowed;continue
        counts['map_available_ticks']+=1
        if available!=last_file:field=audit.history_map(available);last_file=available
        # Tracking uses all common map observations, including before3s and
        # while an existing action suppresses a new trigger. It issues no action.
        tracker.observe(field,poses,tick)
        if not allowed:continue
        counts['common_eligible_ticks']+=1
        old,detail=choose_ahead(field,poses,tick,legacy_cache);old_u=np.array(old['u_ref']) if old else radial_reference(poses,tick)[0]
        forward=float((poses[tick,:2]-poses[tick-216,:2])@old_u)
        drop=approach_progress(component_sets(field)[old['component_id']],poses[tick-216],poses[tick])[0] if old else None
        old_fire=bool(old and (forward<.2 or (drop is not None and drop<.1)))
        new=tracker.check(field,poses,tick);chosen=new['component'];new_u=np.array(chosen['u_ref']) if chosen else radial_reference(poses,tick)[0]
        old_label,old_objects=classify(poses[tick],old_u,tick/72,static,boxes)
        new_label,new_objects=classify(poses[tick],new_u,tick/72,static,boxes)
        old_angle=reference.angle(poses[tick],old_u);new_angle=reference.angle(poses[tick],new_u)
        rows.append(dict(phase=r['phase'],scene=r['scene'],index=r['index'],method=r['method'],tick=tick,time_s=tick/72,
            success=r['success'],robot_pose=poses[tick].tolist(),output=str(root),snapshot_file=str(available),frame=meta['frame_id'],snapshot_age_s=tick/72-meta['sim_s'],
            snapshot_source='RECORDED_CONDITION' if gate_record else 'CONTROL_RECORD',
            original_fire=old_fire,TRIG_fire=new['fire'],original_label=old_label,TRIG_label=new_label,
            original_objects=old_objects,TRIG_objects=new_objects,original_u_ref=old_u.tolist(),TRIG_u_ref=new_u.tolist(),
            original_direction_error_deg=old_angle,TRIG_direction_error_deg=new_angle,
            original_direction_wrong=old_angle>90.,TRIG_direction_wrong=new_angle>90.,
            original_t_new_tick=old['t_new_tick'] if old else None,t_ref_tick=chosen['t_ref_tick'] if chosen else None,
            direction_guard_applied=chosen['direction']['guard']['overridden'] if chosen else False,
            cells_ahead=chosen['cells_ahead'] if chosen else 0,original_progress_3s_m=forward,original_distance_drop_m=drop,
            TRIG_progress_3s_m=new.get('progress_3s_m'),TRIG_distance_drop_m=new.get('distance_drop_m'),
            new_static_trigger=r['scene'] in ('SLW','LC') and new['fire'] and not old_fire))
    availability=dict(phase=r['phase'],scene=r['scene'],index=r['index'],method=r['method'],**counts,
        map_availability=counts['map_available_ticks']/counts['all_control_ticks'],
        eligible_map_availability=counts['common_eligible_ticks']/counts['eligible_ticks'] if counts['eligible_ticks'] else None)
    return rows,availability


def topo_run(r):
    root,cfg,poses,reference,_,_=load_run(r);logs=lines(root/'model/inference.jsonl');states={(0,0)};rows=[]
    for e in logs:
        m=e['topomap'];dist=dict(zip(m['candidate_ids'],m['distances']));start,end=candidate_range(m['previous_closest_node'],m['goal_node'],4)
        assert (start,end)==(m['candidate_start'],m['candidate_end_inclusive'])
        raw,subgoal,_=select_subgoal(m['distances'],start,3)
        assert (raw,subgoal)==(m['closest_node'],m['selected_subgoal_id'])
        outputs=set();missing_any=False
        for state in states:
            options,missing=possible_query(state,dist,m['goal_node']);outputs.update(options);missing_any|=missing
        states={(H,c) for H,c,sg in outputs};subgoals={sg for H,c,sg in outputs};pose=e['observation_pose']
        s,_,_,nearest=reference.pose_metrics(pose)
        behind=lambda sg:reference.node_s[sg]<s-.2
        ahead=lambda sg:sg>nearest+2
        rows.append(dict(phase=r['phase'],scene=r['scene'],index=r['index'],method=r['method'],success=r['success'],query_id=e['id'],
            observation_s=e['observation_sim_s'],robot_s_m=s,nearest_node=nearest,original_closest=raw,original_subgoal=subgoal,
            original_behind=bool(behind(subgoal)),original_ahead=bool(ahead(subgoal)),
            TOPO_subgoal_exact=len(subgoals)==1,TOPO_possible_subgoals=sorted(subgoals),TOPO_possible_states=sorted(states),
            missing_required_window=missing_any,TOPO_behind_lower=all(behind(sg) for sg in subgoals),TOPO_behind_upper=any(behind(sg) for sg in subgoals),
            TOPO_ahead_lower=all(ahead(sg) for sg in subgoals),TOPO_ahead_upper=any(ahead(sg) for sg in subgoals)))
    return rows


def trigger_gate(rows):
    box=[r for r in rows if r['original_fire'] and r['original_label']=='BOX_AHEAD']
    retained=sum(r['TRIG_fire'] for r in box)
    bad={v:sum(r[v+'_fire'] and r[v+'_label'] in ('PASSED_BOX','NOTHING_AHEAD') for r in rows) for v in ('original','TRIG')}
    direction={}
    for v in ('original','TRIG'):
        selected=[r for r in rows if r[v+'_fire'] and r[v+'_label']!='STATIC_AHEAD']
        direction[v]=dict(n=len(selected),wrong=sum(r[v+'_direction_wrong'] for r in selected),rate=sum(r[v+'_direction_wrong'] for r in selected)/len(selected) if selected else None)
    retention=retained/len(box) if box else None
    checks=dict(box_recall=retention is not None and retention>=.95,
        false_trigger_reduction=bad['TRIG']<=.5*bad['original'],
        direction_error_reduction=all(direction[v]['rate'] is not None for v in direction) and direction['TRIG']['rate']<=.5*direction['original']['rate'])
    return dict(label='OFFLINE_OK' if all(checks.values()) else 'OFFLINE_FAIL',checks=checks,
        original_BOX_AHEAD=len(box),TRIG_fired_at_same_BOX_AHEAD_opportunity=retained,box_recall=retention,false_trigger_counts=bad,direction=direction,
        scope='same saved-map, same logged eligibility, 9Hz decision opportunities; STATIC_AHEAD excluded from all gates')


def topo_summary(rows):
    result=[]
    for success in (False,True):
        group=[r for r in rows if r['success']==success];n=len(group)
        result.append(dict(success=success,n=n,exact_subgoal_queries=sum(r['TOPO_subgoal_exact'] for r in group),
            **{key:sum(r[key] for r in group)/n if n else None for key in ('original_behind','original_ahead','TOPO_behind_lower','TOPO_behind_upper','TOPO_ahead_lower','TOPO_ahead_upper')}))
    failed,success=result
    checks=dict(failure_behind_reduction=failed['TOPO_behind_upper']<=.5*failed['original_behind'],
        success_behind_increase=success['TOPO_behind_upper']<=success['original_behind']+.02,
        success_ahead_increase=success['TOPO_ahead_upper']<=success['original_ahead']+.02)
    definite_fail=(failed['TOPO_behind_lower']>.5*failed['original_behind'] or success['TOPO_behind_lower']>success['original_behind']+.02 or success['TOPO_ahead_lower']>success['original_ahead']+.02)
    return dict(label='TOPO_OK' if all(checks.values()) else 'TOPO_FAIL' if definite_fail else 'TOPO_NOT_ESTABLISHED_MISSING_SCORES',
        checks_using_upper_bounds=checks,groups=result,missing_distances_inferred=False)


def verify():
    p=json.loads((HERE/'protocol.json').read_text());assert p['status']=='FROZEN_OFFLINE'
    for f,h in p['source_hashes'].items():assert sha(ROOT/f)==h,f
    return p


def main():
    verify();runs=[dict(r,phase='32') for r in read(ROOT/'research/results/phase32/runs.json') if r['method']=='C0-NA+EC']
    runs+=[dict(r,phase='35') for r in read(ROOT/'research/results/phase35/runs.json') if r['method']=='OURS'];assert len(runs)==30
    trigger_rows=[];availability=[];topo_rows=[];start=time.monotonic()
    for i,r in enumerate(runs):
        path=OUT/'per_run'/f"{r['phase']}_{r['scene']}_{r['index']}.json"
        assert not path.exists(),'One evaluation only; existing result must not be silently overwritten'
        tr,aa=trigger_run(r);tt=topo_run(r);save(path,dict(triggers=tr,availability=aa,topo=tt))
        trigger_rows+=tr;availability.append(aa);topo_rows+=tt
        save(OUT/'status.json',dict(status='RUNNING',completed=i+1,planned=30,elapsed_s=time.monotonic()-start))
        print('[offline]',i+1,'/30',r['phase'],r['scene'],r['index'],flush=True)
    decision=trigger_gate(trigger_rows);topo=topo_summary(topo_rows)
    decision.update(TOPO=topo['label'],planned_new_method='OURS+TRIG+TOPO-H' if topo['label']=='TOPO_OK' else 'OURS+TRIG',
        online_preparation_allowed=decision['label']=='OFFLINE_OK',simulation_started=False)
    labels=[]
    for scene in ('SLW','LC','L2','H1','H2','ALL'):
        for variant in ('original','TRIG'):
            selected=[r for r in trigger_rows if r[variant+'_fire'] and (scene=='ALL' or r['scene']==scene)]
            labels.append(dict(scene=scene,rule=variant,n=len(selected),**{name:sum(r[variant+'_label']==name for r in selected) for name in ('BOX_AHEAD','STATIC_AHEAD','PASSED_BOX','NOTHING_AHEAD')}))
    csvout(OUT/'triggers.csv',trigger_rows);csvout(OUT/'availability.csv',availability);csvout(OUT/'trigger_summary.csv',labels)
    new_static=[r for r in trigger_rows if r['new_static_trigger']]
    if new_static:csvout(OUT/'new_static_triggers.csv',new_static)
    else:(OUT/'new_static_triggers.csv').write_text('phase,scene,index,time_s,original_fire,TRIG_fire,TRIG_label\n')
    csvout(OUT/'topo_queries.csv',topo_rows)
    save(OUT/'decision.json',decision);save(OUT/'topo_decision.json',topo);save(OUT/'input_hashes.json',audit.HASHES)
    save(OUT/'status.json',dict(status='COMPLETE_OFFLINE',completed=30,planned=30,elapsed_s=time.monotonic()-start,label=decision['label']))
    print(json.dumps(dict(TRIG=decision,TOPO=topo)))

if __name__=='__main__':main()
