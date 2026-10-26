"""Read-only audit: original timing/RGB/seed/swept geometry; no oracle control input."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from nomad_isaac.async_report import rows,stats
from nomad_isaac.common import ROOT,integrate_se2,local_to_world,sha256_file
from nomad_isaac.clearance import swept_clearance,obstacle_bounds,single_obstacle_config
from nomad_isaac.topomap import candidate_range,select_subgoal
from nomad_phase0.chunk_report import trace
from nomad_phase0.chunk_execution import protocol as follower_protocol
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from nomad_phase4c.plant import control_command
from nomad_phase3_stage2.execution import decision
from nomad_phase13.metrics import extra_metrics
from nomad_phase12.methods import freshest,TransitionState
from nomad_phase8.execution import select
from .config import METHODS,SAFE,protocol

def audit(run,run_id,offset,delay):
    """Keep the NoMaD batch venv free of SciPy; audit in the existing CPU runtime."""
    import os
    import subprocess
    env=os.environ.copy()
    for key in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):
        env.pop(key,None)
    env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    result=subprocess.run(['/usr/bin/python3','-m','nomad_phase15b.metrics',
        str(Path(run).resolve()),run_id,str(offset),str(delay)],cwd=ROOT,env=env,
        check=False,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f'CPU post-run audit exit {result.returncode}:\n{result.stderr}')
    return json.loads(result.stdout)

def _audit(run,run_id,offset,delay):
    # Only the post-run CPU reporting process imports depth/Graph dependencies.
    from nomad_phase15.evaluate import suffix,oracle_clearance
    from .depth import Snapshot,evaluate_samples
    from .execution import capped_command
    run=Path(run);summary=json.loads((run/'summary.json').read_text());c=summary['scenario'];p=protocol();m=c['phase15b_method']
    prov=json.loads((run/'provenance.json').read_text());env=json.loads((run/'model/environment.json').read_text())
    assert m in METHODS and c['run_id']==run_id and c['seed_offset']==offset==int(run_id[-2:])*10000
    assert c['timeout_sim_s']==90 and c['execution_v_max_m_s']==.3 and c['plant_alpha']=='inf'
    assert (c['observation_hz'],c['controller_hz'],c['integration_hz'])==(4,9,72)
    assert prov['phase15b_method']==m and prov['source_scenario_sha256']==p['scenario_sha256']
    assert sha256_file(Path(c['topomap_manifest']))==p['topomap_manifest_sha256']
    assert env['checkpoint_sha256']==p['checkpoint_sha256'] and env['coverage']['parameter_coverage']==1.
    assert json.loads((run/'phase15b_protocol.json').read_text())==p
    rec,poses=trace(run);ctrl=rows(run/'controller.jsonl');events=rows(run/'events.jsonl');received=rows(run/'received.jsonl')
    requests=rows(run/'requests.jsonl');inference=rows(run/'model/inference.jsonl');gaps=rows(run/'clearance.jsonl');plant=rows(run/'plant.jsonl')
    assert len(rec)==len(gaps)==len(plant) and len(requests)==len(received)==len(inference)
    assert [round(x['simulation_time_s']*72) for x in ctrl]==list(range(0,len(rec)-1,8))
    err=0.
    for tick in range(1,len(rec)):
        command=ctrl[(tick-1)//8];v,w=command['commanded_v_m_s'],command['commanded_w_rad_s']
        assert [float(rec[tick][k]) for k in ('v_m_s','w_rad_s')]==[v,w]
        assert plant[tick]['actual_v_m_s']==v and plant[tick]['actual_w_rad_s']==w
        err=max(err,float(np.max(abs(integrate_se2(poses[tick-1],v,w,1/72)-poses[tick]))))
    assert err<1e-12
    obs={o['observation_id']:o for o in rows(run/'observations.jsonl') if 'observation_id' in o};frames={}
    for i,o in obs.items():
        with Image.open(run/o['rgb_file']) as im:frame=np.asarray(im)
        assert hashlib.sha256(frame.tobytes()).hexdigest()==o['frame_sha256'];frames[i]=frame
    manifest=json.loads(Path(c['topomap_manifest']).read_text());closest=0;samples={};delivery=[];last_receive=-1
    for k,(q,r,inf) in enumerate(zip(requests,received,inference)):
        assert q['id']==r['id']==inf['id']==k and q['seed']==r['seed']==inf['seed']==101+offset+2*k
        assert r['ddpm_seed']==inf['ddpm_seed']==q['seed']+1 and q['request_submit_monotonic_ns']>last_receive
        last_receive=r['received_monotonic_ns'];ids=q['history_observation_ids'];assert len(ids)==4 and np.all(np.diff(ids)>0)
        assert hashlib.sha256(np.stack([frames[i] for i in ids]).tobytes()).hexdigest()==inf['history_sha256']
        top=inf['topomap'];a,b=candidate_range(closest,len(manifest['nodes'])-1)
        assert (a,b)==(top['candidate_start'],top['candidate_end_inclusive']);closest,sg,_=select_subgoal(top['distances'],a)
        assert (closest,sg)==(top['closest_node'],top['selected_subgoal_id']) and inf['goal_sha256']==manifest['nodes'][sg]['rgb_sha256']
        assert top['diffusion_steps']==10 and top['diffusion_passes']==1
        np.testing.assert_allclose(poses[round(q['observation_sim_s']*72)],q['observation_pose'],atol=1e-12,rtol=0)
        assert r['release_monotonic_ns']==r['received_monotonic_ns'] and r['release_deadline_monotonic_ns']==r['packet_received_monotonic_ns']+round(delay*1e9)
        assert r['release_monotonic_ns']>=r['release_deadline_monotonic_ns'];delivery.append((r['release_monotonic_ns']-r['packet_received_monotonic_ns'])/1e9)
        with np.load(run/f'model/raw/{k:04d}.npz') as raw,np.load(run/f'model/derived/{k:04d}.npz') as derived:
            z=raw['normalized_diffusion'];metric=derived['metric'];assert z.shape==metric.shape==(8,8,2)
            cumulative=np.cumsum((z+1)/2*np.array([7.5,8.])+np.array([-2.5,-4.]),axis=1).astype(np.float32)
            np.testing.assert_array_equal(cumulative,derived['cumulative']);np.testing.assert_array_equal(cumulative*np.float32(.05),metric)
            np.testing.assert_array_equal(metric[0,2],r['selected_waypoint_m']);samples[k]=metric.copy()
        np.testing.assert_allclose(local_to_world(metric[0],q['observation_pose']),r['chunk']['world_xy_m'],atol=1e-12,rtol=0)
    updates=rows(run/'depth/updates.jsonl');assert len(updates)==len(obs)
    for u in updates:
        o=obs[u['frame_id']];assert u['sim_s']==o['observation_sim_s'] and u['capture_end_monotonic_ns']==o['capture_end_monotonic_ns']
        np.testing.assert_array_equal(u['pose'],o['observation_pose']);assert u['publication_monotonic_ns']>=u['capture_end_monotonic_ns']
        assert sha256_file(Path(u['file']))==u['snapshot_sha256']
    graph=rows(run/'stage2_graph.jsonl');jobs={j['job_id']:j for j in graph if j['event']=='SUBMIT'}
    results=[r for r in graph if r['event']=='RESULT'];accepted={r['applied_tick']:r for r in results if r['disposition']=='ACCEPTED'}
    assert len(jobs)==(len(events) if 'GRAPH' in m else 0)
    apps=rows(run/'phase6_applications.jsonl');app_at={a['tick']:a for a in apps};ev_at={round(e['application_sim_s']*72):e for e in events}
    assert len(apps)==len(events)+len(accepted)
    state=TransitionState('TEMPORAL-ENSEMBLE') if m=='TEMPORAL-ENSEMBLE' else None
    follower=None;previous_v=0.;command_error=0.;selections=[];ages=[];unknown=[];dangerous=agree=total=0
    cap=False
    for j,control in enumerate(ctrl):
        tick=j*8;b=poses[tick];event=ev_at.get(tick)
        if event:
            np.testing.assert_array_equal(event['agent_pose_at_switch'],b)
            assert control['monotonic_ns']>=event['received_monotonic_ns'] and (j==0 or ctrl[j-1]['monotonic_ns']<event['received_monotonic_ns'])
            worlds=np.array([local_to_world(x,event['observation_pose']) for x in samples[event['id']]])
            meta=event['phase15b']['detail']['snapshot'] if m in SAFE else event['depth_snapshot'];field=Snapshot.load(meta['file'])
            assert meta['publication_monotonic_ns']<=control['monotonic_ns'] or meta['publication_monotonic_ns']<=event.get('phase15b_selection_monotonic_ns',control['monotonic_ns'])
            if not meta['empty_unknown']:ages.append(control['simulation_time_s']-meta['sim_s'])
            depth_xy,detail=evaluate_samples(worlds,b,field)
            if m in SAFE:
                np.testing.assert_allclose(event['phase15b']['applied_initial_world_xy'],depth_xy,atol=1e-12,rtol=0)
                assert event['phase15b']['detail']['selected_sample']==detail['selected_sample'];xy=depth_xy;cap=detail['all_unsafe'];selected=detail['selected_sample'];selections.append(detail)
            elif m=='FRESHEST':xy,d=freshest(worlds,b);selected=d['selected_sample']
            elif m=='TEMPORAL-ENSEMBLE':xy,d=state.switch(worlds,b,event['id'],received[event['id']]['received_monotonic_ns'],control['monotonic_ns']);selected=0
            else:xy,d=select(samples[event['id']],event['observation_pose'],b,c);selected=d['selected_sample']
            for i,candidate in enumerate(detail['candidates']):
                oracle=oracle_clearance(suffix(worlds[i],b)[0],c)>=.025
                dangerous+=int(candidate['safe'] and not oracle);agree+=int(candidate['safe']==oracle);total+=1
            if m!='TEMPORAL-ENSEMBLE':unknown.append(detail['candidates'][selected]['unknown_fraction'])
            try:follower=PurePursuit(xy,follower_protocol()['follower'])
            except ValueError:follower=None
        if tick in accepted:
            result=accepted[tick];assert not event and result['id']==control['waypoint_id'] and result['result_received_ns']<=control['monotonic_ns']
            assert decision(result,control['latest_received_id'],control['valid'])[0]=='ACCEPTED'
            if m==SAFE[2]:
                field=Snapshot.load(result['depth_snapshot_file']);assert field.exact_clearance(np.asarray(result['applied_world_xy']))>=.025-1e-8
            follower=PurePursuit(result['applied_world_xy'],follower_protocol()['follower'])
        if tick in app_at and follower:np.testing.assert_allclose(app_at[tick]['world_xy'],follower.path.points,atol=1e-12,rtol=0)
        if control['latest_received_id']>=0:
            age=(control['monotonic_ns']-received[control['latest_received_id']]['received_monotonic_ns'])/1e9
            assert control['valid']==(age<1.)
        diag=state.ensemble.control(b,control['monotonic_ns'])[0] if state else follower.control(b)[1] if follower and control['valid'] else None
        command=(0.,0.)
        if control['valid'] and diag is not None and not diag['endpoint_stop']:
            x,y=diag['target_local_x_m'],diag['target_local_y_m'];k=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
            command=capped_command(k,previous_v)[0] if cap else control_command('CURV',k,previous_v,0.,float('inf'))[0]
        command_error=max(command_error,float(np.max(abs(np.array(command)-[control['commanded_v_m_s'],control['commanded_w_rad_s']]))));previous_v=command[0]
    assert command_error<1e-12
    minimum={};wall=[];overlap=corridor=False;margin=0.;clear_error=0.
    for tick in range(1,len(rec)):
        v,w=[float(rec[tick][k]) for k in ('v_m_s','w_rad_s')];unsafe=False
        for box in c['obstacles']:
            lo,hi=obstacle_bounds(single_obstacle_config(c,box));g=swept_clearance(poses[tick-1],v,w,1/72,lo,hi,c['agent_radius_m'])
            minimum[box['id']]=min(minimum.get(box['id'],float('inf')),g['lower_m']);overlap|=g['geometric_overlap'];unsafe|=g['lower_m']<.02
            clear_error=max(clear_error,abs(g['lower_m']-gaps[tick]['obstacles'][box['id']]['lower_m']))
        gap=corridor_arc_minimum(poses[tick-1],v,w,1/72,c['corridor'],c['agent_radius_m']);wall.append(gap);corridor|=gap<0
        if unsafe:margin+=1/72
    assert clear_error<1e-10
    goal=bool(summary['goal_entry']);reason=summary['termination_reason'];duration=(len(rec)-1)/72
    classification='SAFETY_FAILURE' if overlap or corridor else 'SUCCESS' if goal else 'STUCK' if reason in ('simulation_timeout','navigation_wall_timeout') else 'CONSERVATIVE_CONTACT_STOP'
    distance=float(np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1).sum());times=np.array([x['simulation_time_s'] for x in ctrl]);dt=np.maximum(0.,np.r_[times[1:],duration]-times)
    result=dict(classification=classification,technical_validation='PASS',success=classification=='SUCCESS',goal_entry=goal,goal_time_s=duration if goal else None,termination_reason=reason,duration_s=duration,distance_m=distance,mean_speed_m_s=distance/duration if duration else 0.,stop_time_s=sum(abs(float(x['v_m_s']))<1e-12 for x in rec[1:])/72,geometric_overlap=bool(overlap),corridor_violation=bool(corridor),minimum_obstacle_clearance_m=min(minimum.values()),minimum_corridor_clearance_m=min(wall),obstacle_minima=minimum,margin_violation_s=margin,max_pose_replay_error=err,max_pp_command_replay_error=command_error,max_swept_clearance_replay_error=clear_error,execution_git_sha=prov['git_sha'],endpoint_clamp_fraction=float(np.mean([bool(x['pure_pursuit'].get('endpoint_clamped')) for x in ctrl])),inference_ms=stats([m['inference_ms'] for m in inference]),actual_delivery_delay_s=stats(delivery),all_unsafe=sum(d['all_unsafe'] for d in selections),fallback_cap_time_fraction=float(sum(t for t,x in zip(dt,ctrl) if x.get('depth_fallback_cap_active'))/duration) if duration else 0.,depth=dict(update_ms=stats([u['update_ms'] for u in updates]),snapshot_age_s=stats(ages),decision_count=total,agreement_count=agree,dangerous_false_safe=dangerous,selected_unknown_fraction=stats(unknown),empty_snapshot_switches=sum(e['depth_snapshot']['empty_unknown'] for e in events)),graph=dict(calls=len(jobs),dispositions=dict(Counter(x['disposition'] for x in results)),independent_nonconverged=sum(not x['solver']['success'] for x in results if 'solver' in x),solver_samples_s=[x['solver']['solver_wall_s'] for x in results if 'solver' in x],solver_time_s=stats([x['solver']['solver_wall_s'] for x in results if 'solver' in x]),accepted_sdf_active_fraction=float(np.mean([r['solver']['sdf_active_within_1mm'] for r in accepted.values()])) if accepted and m==SAFE[2] else None))
    result.update(extra_metrics(run,result))
    paths=[f for pat in ('*.json','*.jsonl','*.csv','depth/*','model/*.json','model/*.jsonl','model/raw/*.npz','model/derived/*.npz') for f in run.glob(pat) if f.is_file()]
    result['input_log_sha256']={str(f.relative_to(run)):sha256_file(f) for f in paths}
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Read-only Phase15B post-run CPU audit')
    parser.add_argument('run',type=Path)
    parser.add_argument('run_id')
    parser.add_argument('offset',type=int)
    parser.add_argument('delay',type=float)
    args=parser.parse_args()
    print(json.dumps(_audit(args.run,args.run_id,args.offset,args.delay)))
