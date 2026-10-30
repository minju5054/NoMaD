"""Read-only command/pose/RGB/depth audit and SO pilot metrics."""
import json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
from nomad_isaac.common import integrate_se2,local_to_world,sha256_file
from nomad_isaac.clearance import obstacle_bounds,single_obstacle_config,swept_clearance,corridor_clearance
from nomad_phase0.chunk_report import trace
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from nomad_isaac.topomap import candidate_range,select_subgoal
from nomad_phase15b.depth import Snapshot,evaluate_samples
from .config import place,triggered
from nomad_phase16.execution import stop_command
from nomad_phase20.execution import SPAlignment

def rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x] if Path(path).exists() else []
def stats(v):return dict(n=len(v),median=float(np.median(v)) if v else None,p95=float(np.quantile(v,.95)) if v else None)


def core_audit(run):
    run=Path(run);s=json.loads((run/'summary.json').read_text());c=s['scenario'];rec,poses=trace(run)
    ctrl=rows(run/'controller.jsonl');events=rows(run/'events.jsonl');requests=rows(run/'requests.jsonl');received=rows(run/'received.jsonl');inference=rows(run/'model/inference.jsonl')
    commands=rows(run/'phase20_commands.jsonl');repairs=rows(run/'repair.jsonl');recovery=rows(run/'recovery.jsonl');steps={r['tick']:r for r in rows(run/'recovery_72hz.jsonl')}
    assert len(requests)==len(received)==len(inference);assert len(ctrl)==len(commands)
    assert [r['tick'] for r in commands]==list(range(0,len(rec)-1,8))
    apply={r['tick']:r for r in repairs if r['event']=='PATH_APPLIED'};sp=None;err=pose_error=0.;previous=0.
    te_expected=te_replay(run,commands,events,repairs) if c['phase21_method']=='B1_SAFE_TE' else None
    for a,b in zip(ctrl,commands):
        if b['tick'] in apply:
            p=apply[b['tick']];sp=SPAlignment();sp.replace_path(p['path_world'],p['pose'],p['previous_vw'][0])
        actual=[a['commanded_v_m_s'],a['commanded_w_rad_s']];source=b['source']
        if te_expected is not None:expected=te_expected[b['tick']]
        elif source in ('NORMAL','KEEP_ACTIVE','REPAIR','DETOUR','ALIGN_BRAKE','ALIGN_ROTATE','ENDPOINT'):
            assert sp is not None;expected,diag=sp.control(b['pose'],previous)
            if diag['completed']:expected=stop_command(previous)
        elif source=='RECOVER_ROTATE':expected=[0.,actual[1]];assert abs(actual[1])==.3
        elif source=='WAIT_FRESH':expected=[0.,0.]
        else:expected=stop_command(previous)
        err=max(err,float(np.max(np.abs(np.array(expected)-actual))))
        assert abs(actual[0]-previous)<=.5/9+1e-12;previous=actual[0]
    for tick in range(1,len(rec)):
        a=ctrl[(tick-1)//8];v,w=float(rec[tick]['v_m_s']),float(rec[tick]['w_rad_s'])
        expected=steps[tick]['actual_vw'] if tick in steps else [a['commanded_v_m_s'],a['commanded_w_rad_s']]
        np.testing.assert_allclose([v,w],expected,atol=1e-12,rtol=0)
        pose_error=max(pose_error,float(np.max(np.abs(integrate_se2(poses[tick-1],v,w,1/72)-poses[tick]))))
    assert err<1e-12 and pose_error<1e-12
    obs=[r for r in rows(run/'observations.jsonl') if 'observation_id' in r];frames={}
    assert all('oracle_information' not in o for o in obs)
    assert not (run/'oracle_information.json').exists()
    for o in obs:
        with Image.open(run/o['rgb_file']) as im:frame=np.asarray(im)
        assert hashlib.sha256(frame.tobytes()).hexdigest()==o['frame_sha256'];frames[o['observation_id']]=frame
    manifest=json.loads(Path(c['topomap_manifest']).read_text());assert len(manifest['nodes'])==21
    closest=0;delay=s['delivery_delay']['configured_additional_s'];delivery=[]
    for i,(q,r,m) in enumerate(zip(requests,received,inference)):
        assert q['id']==r['id']==m['id']==i and q['seed']==m['seed']==101+c['seed_offset']+2*i and m['ddpm_seed']==q['seed']+1
        assert hashlib.sha256(np.stack([frames[k] for k in q['history_observation_ids']]).tobytes()).hexdigest()==m['history_sha256']
        assert r['release_deadline_monotonic_ns']==r['packet_received_monotonic_ns']+round(delay*1e9)
        assert r['received_monotonic_ns']==r['release_monotonic_ns']>=r['release_deadline_monotonic_ns']
        t=m['topomap'];a,b=candidate_range(closest,20);assert (a,b)==(t['candidate_start'],t['candidate_end_inclusive'])
        closest,subgoal,_=select_subgoal(t['distances'],a);assert (closest,subgoal)==(t['closest_node'],t['selected_subgoal_id'])
        assert m['goal_sha256']==manifest['nodes'][subgoal]['rgb_sha256'] and t['diffusion_steps']==10
        np.testing.assert_allclose(q['observation_pose'],poses[round(q['observation_sim_s']*72)],atol=1e-12,rtol=0)
        delivery.append((r['release_monotonic_ns']-r['packet_received_monotonic_ns'])/1e9)
    for e in events:
        with np.load(run/f"model/derived/{e['id']:04d}.npz") as z:samples=z['metric'].copy()
        np.testing.assert_array_equal(samples,e['overnight_metric_samples'])
        if 'phase16' not in e:assert e.get('phase17_selection_deferred') or e.get('phase20d_selection_deferred') or e.get('phase21_raw');continue
        d=e['phase16']['selection'];field=Snapshot.load(d['snapshot']['file'])
        assert d['snapshot']['publication_monotonic_ns']<=e['phase16_selection_ns']
        _,check=evaluate_samples(np.array([local_to_world(x,e['observation_pose']) for x in samples]),e['agent_pose_at_switch'],field)
        assert check['selected_sample']==d['selected_sample'] and check['all_unsafe']==d['all_unsafe']
    spawn=json.loads((run/'dynamic/spawn.json').read_text()) if (run/'dynamic/spawn.json').exists() else None
    placement=json.loads((run/'dynamic/placement.json').read_text()) if (run/'dynamic/placement.json').exists() else None
    gaps=rows(run/'dynamic/clearance.jsonl');walls=rows(run/'clearance.jsonl');minimum=None;collision=False;gap_error=0.
    if spawn:
        expected=place(c,poses[spawn['tick']]);np.testing.assert_array_equal(expected['obstacle']['center_xy_m'],spawn['obstacle']['center_xy_m'])
        assert not any(triggered(c,p) for p in poses[:spawn['tick']])
        render=json.loads((run/'dynamic_render_update.json').read_text());assert render['obstacle']==spawn['obstacle']
        lo,hi=obstacle_bounds(single_obstacle_config(c,spawn['obstacle']))
        for i in range(1,len(gaps)):
            tick=spawn['tick']+i;v,w=float(rec[tick]['v_m_s']),float(rec[tick]['w_rad_s'])
            g=swept_clearance(poses[tick-1],v,w,1/72,lo,hi,c['agent_radius_m'])
            gap_error=max(gap_error,abs(g['lower_m']-gaps[i]['lower_m']))
        assert gap_error<1e-9
        minimum=min(r['lower_m'] for r in gaps);collision=any(r['geometric_overlap'] for r in gaps)
    wall_min=min(r['corridor_lower_m'] for r in walls);wall_exact_min=float('inf')
    for tick,r in enumerate(walls):
        v,w=(float(rec[tick][k]) for k in ('v_m_s','w_rad_s'))
        bounded=corridor_clearance(poses[max(0,tick-1)],poses[tick],v,w,1/72 if tick else 0,c['corridor'],c['agent_radius_m'])
        assert abs(bounded-r['corridor_lower_m'])<1e-12
        exact=corridor_arc_minimum(poses[max(0,tick-1)],v,w,1/72 if tick else 0,c['corridor'],c['agent_radius_m'])
        wall_exact_min=min(wall_exact_min,exact)
    corridor=wall_exact_min<=0
    visible=next((o for o in obs if o.get('dynamic',{}).get('visible')),None);depth_seen=None;map_seen=None
    if spawn:
        for o in obs:
            f=run/f"depth/depth_{o['observation_id']:04d}.npz"
            if o.get('dynamic',{}).get('visible') and f.exists():
                with np.load(f) as z:d=z['depth']
                mask=np.array(Image.open(run/o['dynamic_mask_file']))>0
                if np.any(mask & np.isfinite(d) & (d>0) & (d<=3.)):depth_seen=o['observation_sim_s'];break
        for u in rows(run/'depth/updates.jsonl'):
            if u['sim_s']<spawn['simulation_time_s']:continue
            field=Snapshot.load(u['file']);iy,ix=np.nonzero(field.occupied);p=field.origin+np.c_[ix,iy]*field.h
            if np.any(np.all((p>=lo-.015)&(p<=hi+.015),axis=1)):map_seen=u['sim_s'];break
    pass_tick=None;side=None
    if spawn:
        candidates=np.flatnonzero((np.arange(len(poses))>=spawn['tick'])&(poses[:,0]-c['agent_radius_m']>hi[0]))
        if len(candidates):pass_tick=int(candidates[0]);side='+Y' if poses[pass_tick,1]>=spawn['obstacle']['center_xy_m'][1] else '-Y'
    attempts=[r for r in repairs if r['event']=='SUBMIT'];results=[r for r in repairs if r['event']=='RESULT'];counts=Counter(r['disposition'] for r in results)
    assert not any(r['disposition']=='ERROR' for r in results)
    outcomes=[r for r in repairs if r['event']=='FIRST_FRESH_AFTER_REPAIR']
    duration=s['simulation_duration_s'];mode_seconds=Counter();repair_follow_s=0.;active_kind=None
    for tick in range(1,len(rec)):
        control_tick=((tick-1)//8)*8
        if control_tick in apply:active_kind=apply[control_tick]['kind']
        source=commands[(tick-1)//8]['source'];mode_seconds[source]+=1/72
        if active_kind=='REPAIR' and source in ('NORMAL','KEEP_ACTIVE','REPAIR'):repair_follow_s+=1/72
    stopped=sum(mode_seconds[k] for k in ('STOP_WAIT','REPAIR_WAIT','DETOUR_WAIT','RECOVER_ROTATE','WAIT_FRESH'))
    success=bool(s['goal_entry'] and not collision and not corridor)
    invalid=placement and placement['status']=='PLACEMENT_INVALID'
    classification='PLACEMENT_INVALID' if invalid else 'SAFETY_FAILURE' if collision or corridor else 'SUCCESS' if success else 'STUCK' if s['termination_reason'] in ('simulation_timeout','navigation_wall_timeout') else 'STOPPED_NO_OVERLAP'
    return dict(technical_validation='PASS',success=success,classification=classification,collision=collision,corridor=corridor,stuck=classification=='STUCK',
        safety_failure=collision or corridor,termination_reason=s['termination_reason'],duration_s=duration,goal_time_s=duration if success else None,
        minimum_clearance_m=minimum,minimum_wall_clearance_m=wall_exact_min,minimum_monitor_wall_bound_m=wall_min,distance_m=s['distance_travelled_m'],stopped_fraction=stopped/duration if duration else 0.,
        actual_zero_speed_fraction=sum(abs(float(r['v_m_s']))<.01 for r in rec[1:])/max(1,len(rec)-1),mode_seconds=dict(mode_seconds),
        alignment_count=sum(r['event']=='PATH_APPLIED' and r['alignment'] for r in repairs),alignment_braking_s=mode_seconds['ALIGN_BRAKE'],alignment_rotation_s=mode_seconds['ALIGN_ROTATE'],
        all_unsafe=sum(e.get('phase16',{}).get('selection',{}).get('all_unsafe',False) for e in events),recovery_count=sum(r['event']=='START' for r in recovery),
        repair_attempts=len(attempts),repair_accepted=counts['ACCEPTED'],repair_rejected=counts['REJECTED'],repair_timeout=counts['TIMEOUT'],repair_dispositions=dict(counts),
        repair_acceptance=counts['ACCEPTED']/len(attempts) if attempts else None,repair_execution_s=repair_follow_s,
        repair_resolved_all_unsafe_fraction=counts['ACCEPTED']/sum(e.get('phase16',{}).get('selection',{}).get('all_unsafe',False) for e in events) if any(e.get('phase16',{}).get('selection',{}).get('all_unsafe',False) for e in events) else None,
        post_repair_safe_count=sum(r['safe_sample_count']>0 for r in outcomes),post_repair_fresh_count=len(outcomes),
        repair_wall_s=stats([r['wait_s'] for r in results]),spawn_s=spawn['simulation_time_s'] if spawn else None,
        first_visible_s=visible['observation_sim_s'] if visible else None,first_depth_observed_s=depth_seen,first_depth_map_observed_s=map_seen,
        box_passage_time_s=pass_tick/72-spawn['simulation_time_s'] if pass_tick is not None else None,passed_box=pass_tick is not None,pass_side=side,
        command_replay_error=err,pose_replay_error=pose_error,clearance_replay_error=gap_error,oracle_publications=0,
        requests=len(requests),switches=len(events),inference_ms=stats([m['inference_ms'] for m in inference]),delivery_s=stats(delivery))



def te_replay(run,commands,events,applications):
    from nomad_phase12.methods import TemporalTargets
    from nomad_phase16.execution import filter_ensemble
    from .execution import TEProfile
    control_by_tick={round(r['simulation_time_s']*72):r for r in rows(run/'controller.jsonl')}
    ensemble=TemporalTargets();profiles={};switches={round(e['application_sim_s']*72):e for e in events};applied={r['tick']:r for r in applications if r['event']=='PATH_APPLIED'};result={}
    for b in commands:
        tick=b['tick'];e=switches.get(tick)
        if tick in applied:
            r=applied[tick];sp=TEProfile();sp.replace_path(r['path_world'],r['pose'],r['previous_vw'][0]);sp.ensemble=ensemble;profiles[r['id']]=sp
            ensemble.push(np.array(r['path_world']),r['id'],e['received_monotonic_ns'])
        elif e and 'phase16' in e and e['phase16']['selection']['all_unsafe']:
            field=Snapshot.load(e['phase16']['selection']['snapshot']['file']);filter_ensemble(ensemble,b['pose'],field,e['monotonic_ns'] if 'monotonic_ns' in e else control_by_tick[tick]['monotonic_ns'])
        source=b['source'];before=b['before_vw'][0]
        if source in ('NORMAL','KEEP_ACTIVE','ALIGN_BRAKE','ALIGN_ROTATE','ENDPOINT'):
            sp=profiles[b['path_source_id']];sp.now_ns=control_by_tick[tick]['monotonic_ns']
            command,diag=sp.control(b['pose'],before)
            if diag['completed']:command=stop_command(before)
        elif source=='RECOVER_ROTATE':command=b['command']
        elif source=='WAIT_FRESH':command=[0.,0.]
        else:command=stop_command(before)
        result[tick]=command
    return result


def audit(run):
    run=Path(run);result=core_audit(run);rec,poses=trace(run);summary=json.loads((run/'summary.json').read_text());c=summary['scenario'];d=rows(run/'detour.jsonl');jobs=rows(run/'repair_pool_jobs.jsonl');repairs=rows(run/'repair.jsonl');controls=rows(run/'controller.jsonl')
    spawn=result['spawn_s'];passage=spawn+result['box_passage_time_s'] if result['passed_box'] else None
    if c['depth_camera']:
        updates=rows(run/'depth/updates.jsonl');archives=rows(run/'depth/archives.jsonl');assert len(updates)==len(archives)
        for u,a in zip(updates,archives):assert u['frame_id']==a['frame_id'] and u['publication_monotonic_ns']<=a['archive_start_ns'] and sha256_file(a['file'])==a['snapshot_sha256']
    else:assert not (run/'depth').exists(),'B0 must have no depth map'
    path_rows=[r for r in repairs if r['event']=='PATH_APPLIED' and r['kind'] in ('REPAIR','DETOUR')];curv=[];path_stats=[]
    from nomad_phase0.graph_v4 import menger
    for r in path_rows:
        k=menger(np.array(r['path_world']))[0];curv.extend(k.tolist());path_stats.append(dict(tick=r['tick'],kind=r['kind'],rms=float(np.sqrt(np.mean(k*k))),max_abs=float(np.max(np.abs(k))),path=r['path_world']))
    windows=[]
    for r in path_rows:
        end=next((e['simulation_time_s'] for e in d if e['event']=='END' and e['simulation_time_s']>=r['simulation_time_s']),None) if r['kind']=='DETOUR' else None
        if end is None:end=next((q['simulation_time_s'] for q in repairs if q['event']=='PATH_APPLIED' and q['simulation_time_s']>r['simulation_time_s']),summary['simulation_duration_s'])
        windows.append((r['simulation_time_s'],end))
    w=np.array([r['commanded_w_rad_s'] for r in controls]);times=np.array([r['simulation_time_s'] for r in controls]);mask=np.array([any(a<=t<b for a,b in windows) for t in times]);dw=np.diff(w);jerk=np.diff(w,n=2)*81
    selected_dw=dw[mask[1:]&mask[:-1]];selected_jerk=jerk[mask[2:]&mask[1:-1]&mask[:-2]]
    triggers=[r for r in d if r['event']=='TRIGGER'];ends=[r for r in d if r['event']=='END'];applied=[r for r in d if r['event']=='APPLIED']
    false_B=sum(r['trigger']=='B' and not r.get('new_obstacle_condition',{}).get('new_obstacle_ahead',False) for r in triggers)
    reblock=[dict(end_s=e['simulation_time_s'],next_trigger_s=t['simulation_time_s']) for e in ends for t in [next((r for r in triggers if r['simulation_time_s']>e['simulation_time_s'] and (passage is None or r['simulation_time_s']<passage)),None)] if t is not None]
    method=c['phase21_method'];inf=rows(run/'model/inference.jsonl');rtc=[r for r in inf if 'rtc' in r or 'rtc_prefix_error' in r]
    result.update(method=method,scene=c['blockage_level'],passage_censored=not result['passed_box'],passage_time_capped_s=result['box_passage_time_s'] if result['passed_box'] else 90.,
        curvature_rms=float(np.sqrt(np.mean(np.square(curv)))) if curv else None,curvature_max=float(np.max(np.abs(curv))) if curv else None,path_curvature=path_stats,
        angular_delta_rms=float(np.sqrt(np.mean(selected_dw**2))) if len(selected_dw) else None,angular_delta_max=float(np.abs(selected_dw).max()) if len(selected_dw) else None,
        angular_jerk_rms=float(np.sqrt(np.mean(selected_jerk**2))) if len(selected_jerk) else None,angular_jerk_max=float(np.abs(selected_jerk).max()) if len(selected_jerk) else None,
        trigger_count=len(triggers),triggers_by_kind=dict(Counter(r['trigger'] for r in triggers)),false_trigger_B=false_B,unconditional_A_count=sum(r['trigger']=='A' for r in triggers),
        detour_applied=len(applied),detour_jobs=[{k:j.get(k) for k in ('job_id','kind','pool_wall_s','dispatch_to_complete_s','sample_solve_s')} for j in jobs],
        planner_time_s=stats([j['dispatch_to_complete_s'] for j in jobs]),reblock_count=len(reblock),reblocks=reblock,rtc_records=len(rtc),
        goal_y_m=float(poses[-1,1]) if result['success'] else None)
    return result
