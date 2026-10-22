"""Twelve predetermined D0 runs, gated by C0 reproduction. No retries."""
import argparse
import json
from pathlib import Path
import time
import traceback
from types import SimpleNamespace
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.topomap_report import validate_map
from nomad_isaac.async_report import rows
from nomad_phase0.s0_batch import exclusive_batch,launch_one,git_state
from nomad_phase2.audit import audit
from .config import protocol,validate_options,MaskSchedule
from .data import scope,evaluate,aggregate
import numpy as np


def plan(root):
    p=protocol();jobs=[]
    for r in p['navigation_order']:
        c,i,d=r['condition'],r['index'],r['d_m'];key=f'{c}_d{round(d*10):02d}_i{i}';runid=f'DIAG_{c}_{i:02d}'
        argv=['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV','bash',str(ROOT/'research/python.sh'),
              '-m','nomad_isaac.launch','--asynchronous','--pure-pursuit','--scenario',str(ROOT/p['scenario']),
              '--topomap',p['topomap'],'--phase2-method','M0','--diagnostic-condition',c,'--phase2-distance-m',str(d),
              '--uniform-delivery-delay-s','0','--run-id',runid,'--seed-offset',str(r['offset']),'--output',str(root/key)]
        jobs.append({**r,'key':key,'run_id':runid,'output':str(root/key),'argv':argv})
    return jobs


def preflight(root):
    p=protocol();assert all(sha256_file(Path(f))==h for f,h in p['protected_sha256'].items())
    manifest,check=validate_map(Path(p['topomap']));assert manifest['node_count']==21
    jobs=plan(root);assert len(jobs)==12
    for j in jobs:
        validate_options(SimpleNamespace(phase2_method='M0',asynchronous=True,pure_pursuit=True,topomap=Path(p['topomap']),
            diagnostic_condition=j['condition'],prepare_only=False,s1_mode=False,s1_v2_mode=False,oracle_safety_stop=False,
            early_obstacle_mode=None,controlled_delivery_delay=False,render_topomap_reference=None,s1_distance_m=None,
            uniform_delivery_delay_s=0.,scenario=ROOT/p['scenario'],run_id=j['run_id'],seed_offset=j['offset'],phase2_distance_m=j['d_m']))
    return {'status':'PASS','map':check,'jobs':jobs,'git':git_state()}


def audit_diagnostic(run,out):
    result=audit(run,out,do_feasibility=False)
    summary=json.loads((run/'summary.json').read_text());config=summary['scenario']
    assert config['diagnostic_condition'] in ('C1','C2','C3')
    records=rows(run/'model/inference.jsonl');events=rows(run/'events.jsonl');requests=rows(run/'requests.jsonl')
    assert len(records)==len(requests)
    box=summary.get('dynamic_obstacle',{}).get('spawn',{}).get('obstacle')
    schedule=MaskSchedule(config['diagnostic_condition'])
    # Replay every captured decision (including busy captures), then compare accepted inputs.
    for o in rows(run/'observations.jsonl'):
        if 'diagnostic_mode' not in o:continue
        m=o['diagnostic_mode'];snapshot={'pose':m['decision_pose'],'tick':m['decision_tick'],'monotonic_ns':m['decision_monotonic_ns']}
        assert schedule.decide(o.get('oracle_information'),box if o.get('dynamic',{}).get('active') else None,snapshot)==m
    for n,r in zip(records,requests):
        assert n['diagnostic_mode']==r['diagnostic_mode']
        assert n['topomap']['goal_mask']==n['diagnostic_mode']['goal_mask']
        assert n['additional_delivery_delay_s']==0
    assert not rows(run/'phase2_graph.jsonl')
    assert all(e['phase2']['selected_sample']==0 and not e['phase2']['variable_speed'] and not e['phase2']['graph_applied'] for e in events)
    selected,captures,box,c=scope(run);fresh=[]
    for n in selected:
        with np.load(run/f"model/derived/{n['id']:04d}.npz") as f:r=evaluate(f['metric'],n['observation_pose'],c,box)
        fresh.append({'id':n['id'],'t_obs':n['observation_sim_s'],'goal_mask':n['diagnostic_mode']['goal_mask'],
                      'closest_node':n['topomap']['closest_node'],'subgoal':n['topomap']['selected_subgoal_id'],**r})
    write_json(out/'fresh.json',fresh)
    result.update(condition=config['diagnostic_condition'],masked_request_ids=[n['id'] for n in records if n['diagnostic_mode']['goal_mask']],
                  fresh_summary=aggregate(fresh),mask_schedule_verified=True,no_selection_graph_or_added_delay=True,
                  scope_busy_skips=sum(o.get('status')=='busy_history_only' for o in captures))
    write_json(out/'diagnostic_summary.json',result)
    return result


def execute(root):
    state=git_state();assert not state['git_status']
    c0=json.loads((root/'c0/summary.json').read_text());assert c0['status']=='PASS' and c0['execution']==state
    check=preflight(root);jobs=check['jobs']
    assert all(not Path(j['output']).exists() for j in jobs)
    (root/'metrics').mkdir(exist_ok=False);(root/'launcher_logs').mkdir(exist_ok=False)
    write_json(root/'navigation_preflight.json',check)
    with (root/'journal.jsonl').open('x') as journal:
        for j in jobs:
            assert git_state()==state
            journal.write(json.dumps({'event':'START',**j,'monotonic_ns':time.monotonic_ns()})+'\n');journal.flush()
            print('START',j['key'],flush=True)
            try:
                code=launch_one(j,root/'launcher_logs'/f"{j['key']}.log")
                if code:raise RuntimeError(f'Launcher exit {code}')
                result=audit_diagnostic(Path(j['output']),Path(j['output'])/'diagnostic_audit')
            except Exception as exc:
                result={'classification':'TECHNICAL_FAILURE','technical_validation':'FAIL','error':repr(exc),'traceback':traceback.format_exc()}
            result.update({k:v for k,v in j.items() if k!='argv'});write_json(root/'metrics'/f"{j['key']}.json",result)
            journal.write(json.dumps({'event':'END','key':j['key'],'classification':result['classification']})+'\n');journal.flush()
            print('END',j['key'],result['classification'],flush=True)
            if result['technical_validation']!='PASS':raise RuntimeError('Technical blocker; preserving attempt, no retry')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.execute:
        with exclusive_batch():execute(args.root)
    else:print(json.dumps(preflight(args.root),indent=2))
