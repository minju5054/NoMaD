"""Frozen Section0: 241 R2 event solves and six saved SRG collision diagnoses."""
import argparse,json,subprocess,time
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.clearance import swept_clearance,point_clearance as box_point_clearance
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase15.evaluate import sample_path
from nomad_phase15b.depth import Snapshot
from nomad_phase16d.diagnose import clearance
from nomad_phase19r.evaluate import Inputs,select_repair,clean,dump,csv_write,stats
from nomad_phase19s.evaluate import csv_rows
from nomad_phase18d.rollout import Evaluator
from .repair import solve_sample
from .execution import rollout

HERE=ROOT/'research/nomad_phase20';OUT=ROOT/'research/results/phase20_preflight'


def source_events(inputs):
    file=inputs.track(ROOT/'research/results/phase19r/events_eval.csv')
    es=csv_rows(file);assert len(es)==241
    data=[]
    for e in es:
        obj=inputs.event('eval',e['event_id'],e['output'],e['scene'],e['method'],e['index'],e['fresh_id'])
        for key in ('B','depth_clearances_m','oracle_clearances_m','remaining_lengths_m'):
            np.testing.assert_allclose(obj['row'][key],e[key],atol=1e-12,rtol=0)
        assert obj['row']['cause']==e['cause'];data.append(obj)
    return data,es


def first_collision(r,config):
    i=r['first_overlap_tick'];assert i is not None
    ev=Evaluator(config)
    pose=r['poses'][max(0,i-1)];v=r['speeds'][i-1] if i else 0.;w=r['omegas'][i-1] if i else 0.;dt=1/72 if i else 0.
    _,_,wall,_=ev.interval(pose,v,w,dt)
    boxes=[]
    for b,(lo,hi) in zip(config['obstacles'],ev.boxes):
        gap=swept_clearance(pose,v,w,dt,lo,hi,ev.radius,threshold=.025)['lower_m'] if i else box_point_clearance(pose[:2],lo,hi,ev.radius)
        if gap<0:boxes.append(b.get('name',b.get('id','box')))
    return dict(collision_type='WALL_AND_BOX' if wall<0 and boxes else 'WALL' if wall<0 else 'BOX',collision_boxes=boxes,
                collision_pose=r['poses'][i].tolist(),collision_time_s=i/72,actual_v_at_collision=v,actual_w_at_collision=w)


def diagnose_six(inputs,objects,old):
    records=csv_rows(inputs.track(ROOT/'research/results/phase19s/rollouts.csv'))
    selected=[r for r in records if r['dataset']=='D3' and r['rule']=='SRG' and r['legacy_1p5s_prefix']['overlap']]
    assert len(selected)==6
    old_by_id={e['event_id']:e for e in old};obj_by_id={e['row']['event_id']:e for e in objects}
    keys={(r['event_id'],old_by_id[r['event_id']]['selected_sample']) for r in selected};paths={}
    with inputs.track(ROOT/'research/results/phase19r/repair_journal.jsonl').open() as f:
        for line in f:
            r=json.loads(line)
            if r['split']=='eval' and (r['event_id'],r['sample']) in keys:paths[r['event_id']]=r
    assert len(paths)==6
    data=[]
    for saved in selected:
        e=old_by_id[saved['event_id']];obj=obj_by_id[e['event_id']];path=np.array(paths[e['event_id']]['path'])
        r=rollout(e['B'],path,e['previous_actual_v_m_s'],obj['config'])
        np.testing.assert_allclose(r['legacy_1p5s_prefix']['minimum_clearance_m'],saved['legacy_1p5s_prefix']['minimum_clearance_m'],atol=1e-12,rtol=0)
        assert r['overlap'];assert r['trigger_S']==bool(saved['trigger_S'])
        field=Snapshot.load(e['snapshot_file']);q,_=sample_path(path);unknown=field.unknown_fraction(q)
        end=r['first_overlap_tick'];cte=max(XYPath(path).project(p[:2])[1] for p in r['poses'][:end+1])
        target=next((p for p in path if np.linalg.norm(p-np.array(e['B'])[:2])>=.05),None)
        angle=float(abs((np.arctan2(*(target-np.array(e['B'])[:2])[::-1])-e['B'][2]+np.pi)%(2*np.pi)-np.pi)*180/np.pi) if target is not None else None
        reason='Initial alignment completed/started; subsequent PP translation still overlapped.' if r['trigger_S'] else 'Start alignment inactive: actual v >=0.01m/s.' if e['previous_actual_v_m_s']>=.01 else 'Start alignment inactive: initial heading error <20deg (or no point >=5cm).'
        data.append(dict(event_id=e['event_id'],run=e['run'],scene=e['scene'],fresh_id=e['fresh_id'],previous_v=e['previous_actual_v_m_s'],
            initial_heading_error_deg=angle,departure_alignment=r['trigger_S'],rotation_s=r['rotation_time_s'],
            path_oracle_clearance_m=clearance(path,obj['config']),path_unknown_fraction=unknown,cross_track_until_collision_m=cte,
            **first_collision(r,obj['config']),reason=reason+' Safe path clearance did not certify the executed PP arc.',
            source_prefix_reproduced=True))
    return data


def readiness(events,repairs):
    chosen=[e for e in events if e['repair_success']];penetrating=sum(e['selected_oracle_clearance_m']<0 for e in chosen)
    overlaps=sum(e['rollout_overlap'] for e in chosen);rate=overlaps/len(chosen) if chosen else None
    timing=stats([r['attempt_wall_s'] for r in repairs if r['solver_started']]);reasons=[]
    if not chosen:reasons.append('NO_SELECTED_REPAIR')
    if penetrating:reasons.append('SELECTED_PATH_ORACLE_PENETRATION')
    if rate is None or rate>.07:reasons.append('ROLLOUT_OVERLAP_EXCEEDS_7_PERCENT')
    if timing['p95'] is None or timing['p95']>.20:reasons.append('SAMPLE_SOLVE_P95_EXCEEDS_200MS')
    causes={c:dict(events=sum(e['cause']==c for e in events),successes=sum(e['cause']==c and e['repair_success'] for e in events)) for c in ('MARGINAL','TRUE_BLOCK','NEAR_START','OTHER')}
    for c in causes.values():c['fraction']=c['successes']/c['events'] if c['events'] else None
    return dict(label='NOT_READY' if reasons else 'READY',reasons=reasons,events=len(events),repair_successes=len(chosen),repair_success_fraction=len(chosen)/len(events),
        selected_path_oracle_penetrations=penetrating,selected_rollout_overlaps=overlaps,selected_rollout_count=len(chosen),selected_rollout_overlap_fraction=rate,
        accepted_sample_paths=sum(r['accepted'] for r in repairs),all_accepted_path_oracle_penetrations=sum(r['accepted'] and r['oracle_clearance_m']<0 for r in repairs),
        cause_success=causes,per_sample_solve_s=timing,eight_sample_wall_s=stats([e['eight_sample_wall_s'] for e in events]),
        eight_sample_over_half_second=sum(e['eight_sample_wall_s']>.5 for e in events),
        selected_mean_edit_m=stats([e['selected_mean_edit_m'] for e in chosen]),post_hoc=True)


def run():
    assert not OUT.exists(),'No overwrite or automatic restart'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip(),'Freeze code/protocol before event solves'
    p=json.loads((HERE/'protocol.json').read_text());inputs=Inputs();sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for f,h in p['protected_sha256'].items():inputs.track(ROOT/f,h)
    for f in HERE.glob('*'):
        if f.is_file():inputs.track(f)
    objects,old=source_events(inputs)
    # Before any R2 result is inspected, fix all 241 events and the six published cases.
    OUT.mkdir(parents=True);dump(OUT/'protocol.json',p);dump(OUT/'input_manifest.json',dict(git_sha=sha,sha256=inputs.hashes))
    six=diagnose_six(inputs,objects,old);csv_write(OUT/'srg_six_collisions.csv',six)
    print('[diagnosis] six published 1.5s SRG collisions reproduced',flush=True)
    events=[];repairs=[];rollout_traces=[]
    with (OUT/'repair_journal.jsonl').open('x') as log:
        for obj in objects:
            e=dict(obj['row']);field=Snapshot.load(e['snapshot_file']);start=time.perf_counter()
            results=[solve_sample(path,e['B'],field) for path in obj['native']]
            e['eight_sample_wall_s']=time.perf_counter()-start;selected=select_repair(results)
            e.update(repair_success=selected is not None,selected_sample=selected)
            for i,r in enumerate(results):
                record=dict(event_id=e['event_id'],run=e['run'],cause=e['cause'],sample=i,**r)
                record['oracle_clearance_m']=clearance(np.array(r['path']),obj['config']) if r['path'] is not None else None
                log.write(json.dumps(clean(record),allow_nan=False)+'\n');log.flush()
                repairs.append({k:v for k,v in record.items() if k not in ('path','reference')})
            if selected is not None:
                r=results[selected];path=np.array(r['path']);roll=rollout(e['B'],path,e['previous_actual_v_m_s'],obj['config'])
                e.update(selected_mean_edit_m=r['mean_edit_m'],selected_oracle_clearance_m=clearance(path,obj['config']),
                    selected_depth_clearance_m=r['depth_clearance_m'],selected_near_threshold_m=r['near_threshold_m'],
                    rollout_overlap=roll['overlap'],rollout_negative_witness=roll['geometric_negative_witness'],
                    rollout_minimum_clearance_m=roll['minimum_clearance_m'],rollout_distance_m=roll['distance_m'],
                    rollout_trigger_S=roll['trigger_S'],rollout_duration_s=roll['duration_s'],rollout_rotation_s=roll['rotation_time_s'])
                rollout_traces.append(dict(event_id=e['event_id'],selected_sample=selected,**{k:v for k,v in roll.items() if k not in ('speeds','omegas','phases')}))
            events.append(e)
            if len(events)%20==0:print(f'[R2 offline] {len(events)}/241 events; eight samples each, no retry',flush=True)
    verdict=readiness(events,repairs)
    csv_write(OUT/'events.csv',events);csv_write(OUT/'repairs.csv',repairs);dump(OUT/'readiness.json',verdict);dump(OUT/'rollout_traces.json',rollout_traces)
    from .report import preflight_report
    preflight_report(OUT,verdict,six,sha,p)
    for file,h in inputs.hashes.items():assert sha256_file(file)==h,file
    dump(OUT/'complete.json',dict(git_sha=sha,events=len(events),sample_decisions=len(repairs),solver_attempts=sum(r['solver_started'] for r in repairs),
        new_Isaac_navigation=0,new_NoMaD_inference=0,new_render=0,protected_and_input_hashes_unchanged=True,label=verdict['label']))
    print(json.dumps(dict(label=verdict['label'],repair_success=verdict['repair_success_fraction'],NEAR_START=verdict['cause_success']['NEAR_START'],
                         penetrations=verdict['selected_path_oracle_penetrations'],overlap=verdict['selected_rollout_overlap_fraction'],p95=verdict['per_sample_solve_s']['p95'])),flush=True)


def publish():
    assert (OUT/'complete.json').exists()
    ignore=OUT/'.gitignore'
    if not ignore.exists():ignore.write_text('/repair_journal.jsonl\n/rollout_traces.json\n')
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--','research/nomad_phase20',str(OUT.relative_to(ROOT)),'docs/PHASE20_REPAIR_DRIVE.md'],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Record Phase20 R2 offline readiness and SRG collision diagnosis'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    if OUT.exists():assert (OUT/'complete.json').exists(),'Partial attempt preserved'
    else:run()
    if a.publish:publish()


if __name__=='__main__':main()
