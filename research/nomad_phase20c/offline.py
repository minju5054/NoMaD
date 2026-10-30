"""Saved-log NO_PROGRESS gate. Event list fixed before any seven-start solve."""
import argparse,json,subprocess,time,types,multiprocessing as mp
from pathlib import Path
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,local_to_world
from nomad_phase0.chunk_report import trace
from nomad_phase15b.depth import Snapshot
from nomad_phase19r.evaluate import clean,dump,csv_write,stats
from nomad_phase20.metrics import rows
from nomad_phase2.config import native_safety
from nomad_phase18d.rollout import Evaluator
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
import nomad_phase19s.srg as old_srg
import nomad_phase20.execution as old_execution
from .trigger import reference_direction,NoProgress
from .pool import initialize,ping,solve_event

HERE=ROOT/'research/nomad_phase20c';OUT=ROOT/'research/results/phase20c_offline'


class EmptySafeEvaluator(Evaluator):
    def interval(self,pose,v,w,dt):
        if self.boxes:return super().interval(pose,v,w,dt)
        wall=corridor_arc_minimum(pose,v,w,dt,self.c['corridor'],self.radius)
        return wall,float('inf'),wall,wall

_evaluate=types.FunctionType(old_srg.evaluate.__code__,{**old_srg.__dict__,'Evaluator':EmptySafeEvaluator})
rollout=types.FunctionType(old_execution.rollout.__code__,{**old_execution.__dict__,'evaluate':_evaluate},argdefs=old_execution.rollout.__defaults__)


class Inputs:
    def __init__(self):self.hashes={}
    def track(self,p):
        p=Path(p).resolve();self.hashes[str(p)]=sha256_file(p);return p


def inventory(inputs):
    records=json.loads(inputs.track(ROOT/'research/results/phase20b/runs.json').read_text())
    p=json.loads(inputs.track(ROOT/'research/nomad_phase20b/protocol.json').read_text())
    lookup={(r['scene'],r['index'],r['method']):r for r in records};events=[];excluded=[];diagnostics=[]
    for spec in p['main_order']:
        r=lookup[spec['scene'],spec['index'],spec['method']]
        if r.get('technical_validation')!='PASS':excluded.append(dict(run=r['key'],error=r.get('error')));continue
        run=Path(r['output']);config=json.loads(inputs.track(run/'scenario.json').read_text())
        inputs.track(run/'agent_trajectory.csv');rec,poses=trace(run)
        controls=rows(inputs.track(run/'controller.jsonl'));received=rows(inputs.track(run/'received.jsonl'));updates=rows(inputs.track(run/'depth/updates.jsonl'))
        rtimes=np.array([x['latched_monotonic_ns'] for x in received],dtype=np.int64);utimes=np.array([x['publication_monotonic_ns'] for x in updates],dtype=np.int64)
        spawn=json.loads(inputs.track(run/'dynamic/spawn.json').read_text()) if (run/'dynamic/spawn.json').exists() else None
        tracker=NoProgress();virtual_end=None;world_cache={};validated=set();counts=Counter()
        for c in controls:
            tick=round(c['simulation_time_s']*72);ns=c['monotonic_ns'];t=tick/72
            if virtual_end is not None and t>=virtual_end-1e-12:tracker.ended(virtual_end);virtual_end=None
            k=int(np.searchsorted(rtimes,ns,side='right')-1);packet=received[k] if k>=0 else None
            if packet is not None and packet['id'] not in world_cache:
                world_cache[packet['id']]=np.array([local_to_world(np.array(q),packet['observation_pose']) for q in packet['overnight_metric_samples']])
            samples=world_cache[packet['id']] if packet is not None else None
            u,source=reference_direction(poses,tick,samples)
            mode=c.get('phase20',{}).get('source',c.get('applied_command_source'))
            blocked=mode in ('RECOVER_ROTATE','ALIGN_BRAKE','ALIGN_ROTATE','REPAIR_WAIT')
            fire,forward,reason=tracker.check(poses,tick,u,blocked);counts[reason]+=1
            if not fire:continue
            assert packet is not None
            if packet['id'] not in validated:
                with np.load(inputs.track(run/f"model/derived/{packet['id']:04d}.npz")) as z:np.testing.assert_array_equal(z['metric'],packet['overnight_metric_samples'])
                validated.add(packet['id'])
            j=int(np.searchsorted(utimes,ns,side='right')-1)
            snap=updates[j] if j>=0 else dict(file=str(run/'depth/snapshot_initial.npz'),sim_s=0.,publication_monotonic_ns=0)
            assert snap['publication_monotonic_ns']<=ns and snap['sim_s']<=t+1e-12
            file=inputs.track(snap['file']);field=Snapshot.load(file)
            active=spawn is not None and tick>=spawn['tick'];box=spawn['obstacle'] if active else None
            oracle={**config,'obstacles':[box] if box else []};oracle.pop('dynamic_obstacle',None)
            beyond=bool(box and poses[tick,0]-config['agent_radius_m']>box['center_xy_m'][0]+box['size_xyz_m'][0]/2)
            e=dict(event_id=len(events),run=r['key'],output=str(run),scene=r['scene'],method=r['method'],index=r['index'],tick=tick,time_s=t,
                B=poses[tick].tolist(),u_ref=u.tolist(),reference_source=source,progress_3s_m=forward,source_mode=mode,
                previous_v=float(rec[tick]['v_m_s']),previous_w=float(rec[tick]['w_rad_s']),packet_id=packet['id'],
                observation_pose=packet['observation_pose'],sample_observation_age_s=t-packet['observation_sim_s'],
                original_waypoint_valid=c['valid'],snapshot_file=str(file),snapshot_sim_s=snap['sim_s'],snapshot_age_s=t-snap['sim_s'],
                snapshot_publication_ns=snap['publication_monotonic_ns'],trigger_monotonic_ns=ns,
                phase='PRE_SPAWN' if not active else 'AFTER_BOX_PASSAGE' if beyond else 'BEFORE_BOX_PASSAGE',
                B_depth_clearance_m=float(field.query(poses[tick,None,:2])[0][0])-field.error_bound,
                virtual_end_s=t+6.,virtual_next_eligible_s=t+9.,oracle_config=oracle)
            events.append(e);tracker.started();virtual_end=t+6.
        diagnostics.append(dict(run=r['key'],controller_ticks=len(controls),events=sum(e['run']==r['key'] for e in events),checks=dict(counts)))
    assert len(diagnostics)==10 and len(excluded)==2
    return events,excluded,diagnostics


def oracle_path(path,config):
    r=native_safety(np.asarray(path),config);return min(r['corridor_clearance_m'],r['minimum_clearance_m'] if r['minimum_clearance_m'] is not None else float('inf'))

def gap_direction(path,e):
    boxes=e['oracle_config']['obstacles']
    if not boxes:return dict(gap_direction=None,endpoint_beyond_front=None,endpoint_in_gap=None)
    box=boxes[0];x,y=box['center_xy_m'];hx,hy=np.array(box['size_xyz_m'][:2])/2;p=np.array(path)[-1];r=e['oracle_config']['agent_radius_m'];wall=e['oracle_config']['corridor']['half_width']
    beyond=bool(p[0]>x-hx);left=y+hy+r+.025<=p[1]<=wall-r-.025;right=-wall+r+.025<=p[1]<=y-hy-r-.025
    return dict(gap_direction=bool(beyond or left or right),endpoint_beyond_front=beyond,endpoint_in_gap=bool(left or right))

def decision(events,solutions):
    selected=[e for e in events if e['accepted']];accepted=[r for r in solutions if r['accepted']]
    penetrations=sum(r['oracle_clearance_m']<0 for r in accepted);overlap=sum(e['rollout_overlap'] for e in selected)
    rate=overlap/len(selected) if selected else None;acceptance=len(selected)/len(events) if events else 0.
    times=[e['seven_wall_s'] for e in events];timing=stats(times);fail=[]
    if acceptance<.5:fail.append('ACCEPTANCE_BELOW_50_PERCENT')
    if penetrations:fail.append('ACCEPTED_PATH_ORACLE_PENETRATION')
    if rate is None or rate>.07:fail.append('ROLLOUT_OVERLAP_ABOVE_7_PERCENT')
    if timing['p95'] is None or timing['p95']>1.:fail.append('SEVEN_PARALLEL_P95_ABOVE_1_SECOND')
    return dict(label='NOT_READY' if fail else 'READY',reasons=fail,triggers=len(events),accepted_triggers=len(selected),acceptance_fraction=acceptance,
        accepted_initializations=len(accepted),accepted_path_oracle_penetrations=penetrations,
        selected_path_oracle_penetrations=sum(e['selected_oracle_clearance_m']<0 for e in selected),rollout_overlaps=overlap,rollout_count=len(selected),rollout_overlap_fraction=rate,
        seven_parallel_s=timing,timeout_events=sum(t>1. for t in times),
        accepted_within_1s=sum(e['accepted'] and e['seven_wall_s']<=1. for e in events),
        gap_direction_applicable=sum(e.get('gap_direction') is not None for e in selected),gap_direction_count=sum(bool(e.get('gap_direction')) for e in selected),
        post_hoc=True,scope='Saved poses remain unchanged during virtual detour windows; no closed-loop counterfactual claim')

def run():
    assert not OUT.exists(),'No overwrite or automatic restart'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip(),'Commit protocol before saved-input solves'
    p=json.loads((HERE/'protocol.json').read_text());inputs=Inputs()
    for file,h in p['protected_sha256'].items():assert sha256_file(ROOT/file)==h;inputs.track(ROOT/file)
    for f in HERE.glob('*'):
        if f.is_file():inputs.track(f)
    events,excluded,checks=inventory(inputs);assert events
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();OUT.mkdir(parents=True)
    dump(OUT/'protocol.json',p);dump(OUT/'events_before_solve.json',events);dump(OUT/'excluded_runs.json',excluded);dump(OUT/'trigger_checks.json',checks)
    dump(OUT/'input_manifest.json',dict(git_sha=sha,sha256=inputs.hashes));dump(OUT/'example_ids.json',[e['event_id'] for e in events[:4]])
    print(f'[inventory] {len(events)} fixed events from10 valid runs;2 technical excluded; first4 examples fixed',flush=True)
    context=mp.get_context('spawn');ready=context.Queue();solutions=[];examples={}
    with ProcessPoolExecutor(max_workers=4,mp_context=context,initializer=initialize,initargs=(ready,)) as pool,(OUT/'solutions.jsonl').open('x') as log:
        futures=[pool.submit(ping) for _ in range(4)];pids=[ready.get(timeout=90) for _ in range(4)];assert len(set(pids))==4
        for f in futures:f.result()
        for e in events:
            result=solve_event(pool,{k:e[k] for k in ('B','u_ref','snapshot_file')});e['seven_wall_s']=result['seven_wall_s'];e['selected_initialization']=result['selected'];e['accepted']=result['selected'] is not None
            for r in result['results']:
                r.update(event_id=e['event_id'],run=e['run'],scene=e['scene'],oracle_clearance_m=oracle_path(r['path'],e['oracle_config']) if r['path'] is not None else None)
                log.write(json.dumps(clean(r),allow_nan=False)+'\n');log.flush();solutions.append({k:v for k,v in r.items() if k not in ('path','initial_path')})
            roll=None
            if e['accepted']:
                chosen=result['results'][result['selected']];roll=rollout(e['B'],chosen['path'],e['previous_v'],e['oracle_config'])
                e.update(selected_oracle_clearance_m=chosen['oracle_clearance_m'],selected_progress_m=chosen['progress_m'],selected_unknown_fraction=chosen['unknown_fraction'],
                    rollout_overlap=roll['overlap'],rollout_minimum_clearance_m=roll['minimum_clearance_m'],rollout_distance_m=roll['distance_m'],
                    rollout_alignment=roll['trigger_S'],rollout_rotation_s=roll['rotation_time_s'],**gap_direction(chosen['path'],e))
            if e['event_id']<4:examples[str(e['event_id'])]=dict(event=e,result=result,rollout=roll)
            if (e['event_id']+1)%10==0:print(f"[R3] {e['event_id']+1}/{len(events)} events preserved",flush=True)
    verdict=decision(events,solutions);csv_write(OUT/'events.csv',[{k:v for k,v in e.items() if k!='oracle_config'} for e in events]);csv_write(OUT/'initializations.csv',solutions)
    dump(OUT/'decision.json',verdict);dump(OUT/'examples.json',examples)
    from .report import offline_report
    offline_report(OUT,events,solutions,verdict,examples,excluded,sha,p)
    for file,h in inputs.hashes.items():assert sha256_file(file)==h,file
    dump(OUT/'complete.json',dict(git_sha=sha,event_count=len(events),initialization_records=len(solutions),solver_attempts=sum(r['solver_started'] for r in solutions),
        label=verdict['label'],new_navigation=0,new_NoMaD_inference=0,new_render=0,original_inputs_and_sources_unchanged=True))
    print(json.dumps(clean(verdict)),flush=True)

def publish():
    assert (OUT/'complete.json').exists();ignore=OUT/'.gitignore'
    if not ignore.exists():ignore.write_text('/solutions.jsonl\n')
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--','research/nomad_phase20c',str(OUT.relative_to(ROOT)),'docs/PHASE20C_DETOUR.md'],cwd=ROOT,check=True)
    subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in OUT.glob('*.png')]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Record Phase20C frozen R3 offline readiness gate'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    if OUT.exists():assert (OUT/'complete.json').exists(),'Partial attempt preserved'
    else:run()
    if a.publish:publish()

if __name__=='__main__':main()
