"""Fixed sequential Phase2 stages; no retries, no concurrent GPU navigation."""
import argparse
import json
from pathlib import Path
import subprocess
import traceback
import time
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.topomap_report import validate_map
from nomad_phase0.s0_batch import exclusive_batch, launch_one, git_state
from .config import HERE,protocol,validate_options
from .audit import audit


def job(root,stage,index,delay,distance,method):
    d='none' if distance is None else f'{round(distance*10):02d}'
    key=f'{stage}_D{round(delay*1000)}_d{d}_i{index}_{method}'
    family='PILOT' if stage=='s0' else 'BASE' if stage=='s1' else 'HARD' if stage.startswith('s2c') else 'MAIN'
    runid=f'P2_{family}_{index:02d}';offset=0 if family=='PILOT' else index*10000
    command=['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV',
        'bash',str(ROOT/'research/python.sh'),'-m','nomad_isaac.launch','--asynchronous','--pure-pursuit',
        '--scenario',str(HERE/'scenario.json'),'--topomap',protocol()['topomap'],'--phase2-method',method,
        '--uniform-delivery-delay-s',str(delay),'--run-id',runid,'--seed-offset',str(offset),'--output',str(root/key)]
    if distance is not None:command+=['--phase2-distance-m',str(distance)]
    return {'key':key,'stage':stage,'index':index,'D_s':delay,'d_m':distance,'method':method,'run_id':runid,
        'seed_offset':offset,'request0_seed':101+offset,'output':str(root/key),'argv':command}


def plan(root):
    pilots=[job(root,'s0',0,.5,.8,m) for m in ('M0','M3','M5')]
    baseline=[job(root,'s1',i,D,None,'M0') for i in (1,2) for D in (.25,.5)]
    main=[job(root,'s2a',i,D,d,'M0') for i in range(1,5) for d in (.8,1.) for D in (.25,.5)]
    paired=[job(root,'s2b',i,D,d,m) for i in range(1,5) for d in (.8,1.) for D in (.25,.5) for m in ('M3','M5')]
    hard=[job(root,'s2c0',i,D,.6,'M0') for i in range(1,5) for D in (.5,.75)]
    return {'pilots':pilots,'baseline':baseline,'main':main,'paired':paired,'hard':hard,
        'max_branch2b':55,'max_branch2c':47}


def preflight(root):
    p=protocol();assert all(sha256_file(Path(f))==h for f,h in p['protected_sha256'].items())
    manifest,mapcheck=validate_map(Path(p['topomap']));assert manifest['node_count']==21
    assert sha256_file(HERE/'scenario.json')==p['scenario_sha256']
    layout=plan(root)
    assert [len(layout[k]) for k in ('pilots','baseline','main','paired','hard')]==[3,4,16,32,8]
    from types import SimpleNamespace
    for jobs in (layout[k] for k in ('pilots','baseline','main','paired','hard')):
        for j in jobs:
            validate_options(SimpleNamespace(phase2_method=j['method'],phase2_distance_m=j['d_m'],
                asynchronous=True,pure_pursuit=True,topomap=Path(p['topomap']),prepare_only=False,s1_mode=False,
                s1_v2_mode=False,oracle_safety_stop=False,early_obstacle_mode=None,controlled_delivery_delay=False,
                render_topomap_reference=None,s1_distance_m=None,uniform_delivery_delay_s=j['D_s'],scenario=HERE/'scenario.json',
                run_id=j['run_id'],seed_offset=j['seed_offset']))
    return {'status':'PASS','map':mapcheck,'protocol':p,'plan':layout,'git':git_state()}


def execute(jobs,root,state):
    records=[]
    with (root/'journal.jsonl').open('a') as journal:
        for j in jobs:
            assert git_state()==state,'Checkout changed; no new run launched'
            assert not Path(j['output']).exists(),'No retry or overwrite'
            metric=root/'metrics'/f"{j['key']}.json"
            assert not metric.exists()
            journal.write(json.dumps({'event':'START',**j,'monotonic_ns':time.monotonic_ns()})+'\n');journal.flush()
            stage='launch'
            try:
                code=launch_one(j,root/'launcher_logs'/f"{j['key']}.log")
                if code:raise RuntimeError(f'Launcher exit {code}')
                stage='audit'
                result=audit(Path(j['output']),Path(j['output'])/'phase2_audit')
            except Exception as e:
                result={'classification':'TECHNICAL_FAILURE','technical_validation':'FAIL','error':repr(e),
                    'failure_stage':stage,'traceback':traceback.format_exc(),'success':False}
            result.update({k:v for k,v in j.items() if k!='argv'})
            write_json(metric,result);records.append(result)
            journal.write(json.dumps({'event':'END','key':j['key'],'classification':result['classification'],'technical_validation':result['technical_validation']})+'\n');journal.flush()
            print(json.dumps({'key':j['key'],'classification':result['classification'],'technical':result['technical_validation'],
                              'graph':result.get('graph')}),flush=True)
            if result['technical_validation']!='PASS':
                raise RuntimeError(f"Technical blocker at {j['key']}; artifacts retained, no retry or further run")
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['preflight','pilots','continue-pilots','main'],required=True)
    parser.add_argument('--run-root',type=Path,required=True);parser.add_argument('--output',type=Path)
    a=parser.parse_args();root=a.run_root.resolve();check=preflight(root)
    if a.stage=='preflight':
        assert a.output;a.output.mkdir(parents=True,exist_ok=False);write_json(a.output/'preflight.json',check)
        print(json.dumps({'status':'PASS','counts':{k:len(v) for k,v in check['plan'].items() if isinstance(v,list)}}));return
    state=git_state();assert not state['git_status']
    with exclusive_batch():
        if a.stage=='pilots':
            root.mkdir(parents=True,exist_ok=False)
            (root/'metrics').mkdir();(root/'launcher_logs').mkdir()
            write_json(root/'preflight.json',check)
            result=execute(check['plan']['pilots'],root,state)
            write_json(root/'stage0_complete.json',{'status':'PASS','execution':state,'records':[r['key'] for r in result]})
        elif a.stage=='continue-pilots':
            # Resume only UNATTEMPTED pilots after saved-data audit repair, never relaunch M0.
            initial=json.loads((root/'metrics/s0_D500_d08_i0_M0.json').read_text())
            corrected=json.loads((root/'reaudit_M0_01/summary.json').read_text())
            assert initial['failure_stage']=='audit' and corrected['technical_validation']=='PASS'
            assert corrected['run']==initial['output']
            assert not (root/'stage0_complete.json').exists()
            amended={**initial,**corrected,'audit_amendment':'Float64 anchor equality corrected; original audit failure preserved; no navigation retry'}
            (root/'audit_amendments').mkdir(exist_ok=False)
            write_json(root/'audit_amendments/s0_D500_d08_i0_M0.json',amended)
            with (root/'journal.jsonl').open('a') as f:
                f.write(json.dumps({'event':'AUDIT_AMENDMENT','key':initial['key'],'new_classification':corrected['classification'],'navigation_retry':False})+'\n')
            result=execute(check['plan']['pilots'][1:],root,state)
            write_json(root/'stage0_complete.json',{'status':'PASS','execution':state,'records':[initial['key']]+[r['key'] for r in result],
                'audit_amendments':['audit_amendments/s0_D500_d08_i0_M0.json'],'navigation_attempts':3,'navigation_retries':0})
        else:
            assert json.loads((root/'stage0_complete.json').read_text())['status']=='PASS'
            assert not (root/'main_started.json').exists()
            write_json(root/'main_started.json',state)
            base=execute(check['plan']['baseline'],root,state)
            first=execute(check['plan']['main'],root,state)
            failures=[r['key'] for r in first if r['classification'] in ('SAFETY_FAILURE','STUCK')]
            branch='2b' if failures else '2c'
            write_json(root/'branch.json',{'branch':branch,'M0_failed_keys':failures,'rule':protocol()['stages']['branch']})
            if branch=='2b':execute(check['plan']['paired'],root,state)
            else:
                hard=execute(check['plan']['hard'],root,state)
                nextjobs=[job(root,'s2c1',r['index'],r['D_s'],.6,m) for r in hard
                    if r['classification'] in ('SAFETY_FAILURE','STUCK') for m in ('M3','M5')]
                if nextjobs:execute(nextjobs,root,state)
            write_json(root/'complete.json',{'status':'COMPLETE','branch':branch,'execution':state,
                'attempts':len(list((root/'metrics').glob('*.json'))),'retries':0})

if __name__=='__main__':main()
