"""Frozen Phase3 plan, delegated by the existing S0 batch runner."""
import json
import shlex
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_isaac.topomap_report import validate_map
from nomad_phase0.s0_batch import git_state, exclusive_batch, launch_one, save_plan
from .config import HERE, protocol, validate_options
from .metrics import audit


def build_plan(root):
    p=protocol();scenario=ROOT/p['scenario'];topomap=ROOT.parent/p['topomap']
    manifest,mapcheck=validate_map(topomap);assert manifest['node_count']==14
    for name,digest in p['protected_sha256'].items():assert sha256_file(ROOT/name)==digest,name
    fixed=[scenario,topomap,ROOT.parent/'artifacts/checkpoints/nomad.pth',HERE/'protocol.json']
    fixed += [ROOT/name for name in p['protected_sha256']]
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    # Preserve every reference input/output file, without traversing simulator caches.
    reference={}
    for i in range(1,6):
        old=ROOT.parent/f'artifacts/isaac6/s0_paired_n10_01/S0_{i:02d}/PP'
        paths=[old/n for n in ('summary.json','scenario.json','provenance.json','events.jsonl','controller.jsonl',
                              'received.jsonl','requests.jsonl','observations.jsonl','agent_trajectory.csv','clearance.jsonl','model/inference.jsonl')]
        paths+=list((old/'model/raw').glob('*.npz'))+list((old/'model/derived').glob('*.npz'))+list((old/'observations').glob('*.png'))
        assert len(paths)>11
        reference.update({str(f):sha256_file(f) for f in paths})
    jobs=[]
    for i,offset in enumerate(p['offsets'],1):
        runid=f'S0_{i:02d}'
        for d in p['delays_s']:
            key=f'{runid}_D{round(d*1000):03d}';out=root/key
            a=SimpleNamespace(s0_delay_sweep=True,asynchronous=True,pure_pursuit=True,scenario=scenario,
                              topomap=topomap,run_id=runid,seed_offset=offset,uniform_delivery_delay_s=d)
            validate_options(a)
            command=['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV',
                'bash',str(ROOT/'research/python.sh'),'-m','nomad_isaac.launch','--s0-delay-sweep',
                '--asynchronous','--pure-pursuit','--scenario',str(scenario),'--topomap',str(topomap),
                '--seed-offset',str(offset),'--run-id',runid,'--uniform-delivery-delay-s',str(d),'--output',str(out)]
            jobs.append({'key':key,'run_id':runid,'index':i,'condition':f'D{round(d*1000)}','delay_s':d,
                'seed_offset':offset,'request_0_seed':101+offset,'request_0_ddpm_seed':102+offset,
                'output':str(out),'argv':command,'shell_command':shlex.join(command)})
    assert len(jobs)==len({j['output'] for j in jobs})==20
    return {'label':'PHASE3_STAGE1_PLAN',**git_state(),'protocol':p,'protocol_sha256':sha256_file(HERE/'protocol.json'),
        'map_preflight':mapcheck,'fixed_input_sha256':{str(f):sha256_file(f) for f in fixed},
        'reference_preservation_sha256':reference,'jobs':jobs}


def run(args,root):
    plan=build_plan(root)
    if args.dry_run:
        out=args.output.resolve()
        if out==root or root in out.parents:raise ValueError('Dry-run output must be separate')
        out.mkdir(parents=True,exist_ok=False);save_plan(out,plan)
        print(json.dumps({'status':'DRY_RUN','jobs':20,'navigation_started':0,'output':str(out)}));return
    assert not plan['git_status'],'Clean checkout required'
    with exclusive_batch():
        root.mkdir(parents=True,exist_ok=False);save_plan(root,plan)
        (root/'metrics').mkdir();(root/'launcher_logs').mkdir()
        with (root/'execution.jsonl').open('x') as journal:
            for j in plan['jobs']:
                def record(event):
                    journal.write(json.dumps({'key':j['key'],'monotonic_ns':time.monotonic_ns(),**event})+'\n');journal.flush()
                record({'event':'START','retry':False});stage='prelaunch';code=None
                try:
                    assert git_state()=={k:plan[k] for k in ('git_sha','git_status')},'Checkout changed'
                    assert all(sha256_file(Path(f))==h for f,h in plan['fixed_input_sha256'].items()),'Frozen input changed'
                    assert not Path(j['output']).exists(),'No overwrite or retry'
                    stage='launcher';code=launch_one(j,root/'launcher_logs'/f"{j['key']}.log")
                    if code:raise RuntimeError(f'Launcher exit {code}')
                    stage='audit';metric=audit(Path(j['output']),j['run_id'],j['seed_offset'],j['delay_s'])
                except Exception as exc:
                    metric={'classification':'TECHNICAL_FAILURE','technical_validation':'FAIL','success':False,
                        'technical_failure':True,'failure_stage':stage,'error':repr(exc),'traceback':traceback.format_exc()}
                metric.update({k:v for k,v in j.items() if k not in ('argv','shell_command')})
                metric['launcher_exit_code']=code
                write_json(root/'metrics'/f"{j['key']}.json",metric)
                record({'event':'END','classification':metric['classification'],'technical_validation':metric['technical_validation']})
                print(json.dumps({'key':j['key'],'classification':metric['classification'],'technical_validation':metric['technical_validation']}),flush=True)
        preserved=all(sha256_file(Path(f))==h for f,h in plan['reference_preservation_sha256'].items())
        write_json(root/'complete.json',{'attempts':20,'retries':0,'reference_preservation':preserved,'git_sha':plan['git_sha']})
        assert preserved
