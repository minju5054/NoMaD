"""Outcome-independent saved snapshot manifest; no method execution here."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase0.chunk_report import trace
from nomad_phase20.metrics import rows
from nomad_phase20c.detour_known import radial_reference


def build_manifest():
    train=json.loads((ROOT/'research/results/phase21_tuning/cases.json').read_text());training=[];evaluation=[];hashes={};exclusions=[]
    def load_case(job,run,phase,index,scene,method,identity):
        run=Path(run);_,poses=trace(run);tick=int(job.get('evaluation_tick',round(job['simulation_time_s']*72)))
        config=json.loads((run/'scenario.json').read_text());spawn=json.loads((run/'dynamic/spawn.json').read_text()) if (run/'dynamic/spawn.json').exists() else None
        u,source=(np.asarray(job['u_ref']),job.get('reference_source',{})) if 'u_ref' in job else radial_reference(poses,tick)
        controllers=rows(run/'phase20_commands.jsonl');command=next((r for r in controllers if r['tick']==tick),None)
        previous=job.get('previous_vw',command['before_vw'] if command else [0.,0.])
        # The candidate anchor is stored separately. It is not passed to a planner
        # until the pending protocol choice is explicitly fixed.
        pre_tick=max(0,int(spawn['tick'])-1) if spawn and spawn['tick']<=tick else tick
        candidate_anchor=poses[pre_tick,:2].tolist()
        oracle=dict(config);oracle['obstacles']=list(config.get('obstacles',[]))
        if spawn and spawn['tick']<=tick:oracle['obstacles'].append(spawn['obstacle'])
        file=Path(job['snapshot_file'])
        for f in (file,run/'agent_trajectory.csv',run/'scenario.json'):
            hashes[str(f)]=sha256_file(f)
        if spawn:hashes[str(run/'dynamic/spawn.json')]=sha256_file(run/'dynamic/spawn.json')
        return dict(case_id=identity,phase=phase,index=index,scene=scene,method=method,run=str(run),snapshot_file=str(file),snapshot_sha256=hashes[str(file)],tick=tick,time_s=tick/72,
            B=job['B'],u_ref=u.tolist(),u_ref_source=source,previous_vw=previous,original_stage=job['kind'],trigger=job.get('trigger','A'),
            candidate_anchor_xy=candidate_anchor,candidate_anchor_tick=pre_tick,appearance_available=bool(spawn and spawn['tick']<=tick),
            depth_component=job.get('component'),oracle_config=oracle,spawn=spawn)
    for i,c in enumerate(train):
        job=c['job'];run=Path(c['input']).parent.parent
        training.append(load_case(job,run,c['phase'],c['index'],c['scene'],'M3_DETOUR',f'T{i:03d}'))
    records=json.loads((ROOT/'research/results/phase21/runs.json').read_text());number=0
    for r in sorted(records,key=lambda r:(r['scene'],r['index'],r['method'])):
        if r['method'] not in ('B4_ASTAR','M3_GRAPH'):continue
        run=Path(r['output']);jobs=[]
        for e in rows(run/'repair.jsonl'):
            if e['event']=='SUBMIT':jobs.append(dict(e,kind='R2',trigger='A',evaluation_tick=round(e['simulation_time_s']*72),snapshot_file=e['depth_snapshot']['file']))
        for e in rows(run/'detour.jsonl'):
            if e['event']=='TRIGGER' and e['trigger']=='B':jobs.append(dict(e,snapshot_file=e['depth_snapshot']['file']))
            elif e['event']=='TRIGGER' and e['trigger']=='A':exclusions.append(dict(run=str(run),job_id=e['job_id'],reason='R3 fallback belongs to already included ALL_UNSAFE A event; no duplicate second boundary'))
        for job in sorted(jobs,key=lambda j:(j['evaluation_tick'],j['job_id'])):
            evaluation.append(load_case(job,run,'21',r['index'],r['scene'],r['method'],f'E{number:03d}'));number+=1
    assert len(training)==26 and len(evaluation)==24
    keys=lambda case:(case['run'],case['tick'],case['snapshot_file'])
    assert not ({keys(c) for c in training}&{keys(c) for c in evaluation})
    assert not ({c['snapshot_file'] for c in training}&{c['snapshot_file'] for c in evaluation})
    assert not ({c['index'] for c in training}&{c['index'] for c in evaluation})
    examples=[]
    for predicate in (lambda c:c['scene']=='L2A' and c['index']==111 and c['method']=='M3_GRAPH',lambda c:c['scene']=='L2',lambda c:c['scene']=='L2A' and c['index']!=111):
        found=next(c for c in evaluation if predicate(c) and c['case_id'] not in examples);examples.append(found['case_id'])
    return dict(training=training,evaluation=evaluation,examples=examples,exclusions=exclusions,disjoint=True,input_hashes=hashes)
if __name__=='__main__':
    manifest=build_manifest();out=ROOT/'research/results/phase22o';out.mkdir(exist_ok=True)
    with (out/'manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
    print(json.dumps(dict(training=len(manifest['training']),evaluation=len(manifest['evaluation']),examples=manifest['examples'],disjoint=True)))
