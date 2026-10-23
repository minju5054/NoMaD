"""Frozen 14-run Graph v5 pilot; executed only by explicit user --execute."""
import argparse
import json
import shlex
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_isaac.topomap_report import validate_map
from nomad_phase0.s0_batch import git_state, exclusive_batch, launch_one, save_plan
from .config import HERE, METHODS, protocol, validate_options
from .metrics import audit


def matrix(root):
    p=protocol();jobs=[]
    for d,indices,methods in ((.75,range(1,5),METHODS),(0.,range(1,3),('GRAPH-v5',))):
        for i in indices:
            for method in methods:
                key=f'S0_{i:02d}_D{round(d*1000):03d}_{method}'
                options=SimpleNamespace(phase4_method=method,asynchronous=True,pure_pursuit=True,
                    scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id=f'S0_{i:02d}',
                    seed_offset=i*10000,uniform_delivery_delay_s=d)
                validate_options(options)
                argv=['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV',
                    'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','bash',str(ROOT/'research/python.sh'),
                    '-m','nomad_isaac.launch','--phase4-method',method,'--asynchronous','--pure-pursuit',
                    '--scenario',str(options.scenario),'--topomap',str(options.topomap),'--seed-offset',str(i*10000),
                    '--run-id',options.run_id,'--uniform-delivery-delay-s',str(d),'--output',str(root/key)]
                jobs.append({'key':key,'method':method,'run_id':options.run_id,'index':i,'delay_s':d,
                    'seed_offset':i*10000,'request_0_seed':101+i*10000,'request_0_ddpm_seed':102+i*10000,
                    'output':str(root/key),'argv':argv,'shell_command':shlex.join(argv)})
    assert len(jobs)==14 and len({j['output'] for j in jobs})==14
    return jobs


def build_plan(root):
    p=protocol();m,check=validate_map(ROOT.parent/p['topomap']);assert m['node_count']==14
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h,name
    checkpoint=ROOT.parent/'artifacts/checkpoints/nomad.pth'
    assert sha256_file(checkpoint)==p['checkpoint_sha256']
    # Explicit dependency families only; no repository-wide discovery.
    paths=[]
    for family in ('nomad_phase4','nomad_phase3_stage2','nomad_isaac','nomad_preflight'):
        paths.extend((ROOT/'research'/family).glob('*.py'))
    paths += [ROOT/name for name in p['protected_sha256']]
    paths += [HERE/'protocol.json',ROOT/p['scenario'],ROOT.parent/p['topomap'],checkpoint,
        ROOT/'research/python.sh']
    for name in ('chunk_execution.py','chunk_report.py','s0_batch.py','s0_batch_metrics.py',
                 'graph_v2.py','graph_v3.py','graph_v3_protocol.json','chunk_pilot_protocol.json'):
        paths.append(ROOT/'research/nomad_phase0'/name)
    for name in ('execution.py','graph_worker.py'):
        paths.append(ROOT/'research/nomad_phase2'/name)
    return {**git_state(),'label':p['label'],'protocol':p,'protocol_sha256':sha256_file(HERE/'protocol.json'),
        'run_root':str(root),'map_validation':check,'jobs':matrix(root),
        'fixed_input_sha256':{str(f):sha256_file(f) for f in paths}}


def verify(plan):
    assert not git_state()['git_status'],'Clean committed checkout required'
    for name,h in plan['fixed_input_sha256'].items():
        assert sha256_file(Path(name))==h, f'Frozen input changed: {name}'


def execute(plan,root,jobs,phase):
    execution_sha=git_state()['git_sha']
    results=[]
    with (root/f'{phase}_execution.jsonl').open('x') as journal:
        def record(row):
            journal.write(json.dumps({'monotonic_ns':time.monotonic_ns(),'git_sha':execution_sha,**row})+'\n');journal.flush()
        for job in jobs:
            verify(plan)
            assert git_state()['git_sha']==execution_sha,'Checkout changed during execution'
            assert not Path(job['output']).exists(),'No overwrite or retry'
            record({'event':'START','key':job['key'],'retry':False})
            stage='launcher';code=None;start=time.monotonic()
            try:
                code=launch_one(job,root/'launcher_logs'/f"{job['key']}.log")
                if code:raise RuntimeError(f'Launcher exited {code}')
                stage='audit'
                metric=audit(Path(job['output']),job['run_id'],job['seed_offset'],job['delay_s'])
            except Exception as e:
                metric={'classification':'TECHNICAL_FAILURE','technical_validation':'FAIL',
                    'technical_failure':True,'failure_stage':stage,'error':repr(e),'traceback':traceback.format_exc()}
            metric.update({k:v for k,v in job.items() if k not in ('argv','shell_command')})
            metric.update(launcher_exit_code=code,launch_and_audit_wall_s=time.monotonic()-start)
            write_json(root/'metrics'/f"{job['key']}.json",metric)
            results.append(metric)
            record({'event':'END','key':job['key'],'technical_validation':metric['technical_validation'],
                'classification':metric['classification']})
            print(json.dumps({'key':job['key'],'technical_validation':metric['technical_validation'],
                'classification':metric['classification']}),flush=True)

    verify(plan)
    write_json(root/f'{phase}_complete.json',{'attempts':len(results),'retries':0,'git_sha':execution_sha,
        'technical_passes':sum(r['technical_validation']=='PASS' for r in results),'keys':[r['key'] for r in results]})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run',action='store_true')
    group.add_argument('--execute',action='store_true')
    parser.add_argument('--run-root',type=Path,required=True)
    a=parser.parse_args();root=a.run_root.resolve()
    assert not root.exists(),'Output already exists: no overwrite/retry/resume'
    plan=build_plan(root)
    if a.dry_run:
        print(json.dumps({'navigation_started':0,'jobs':plan['jobs']},indent=2));return
    with exclusive_batch():
        verify(plan)
        root.mkdir(parents=True,exist_ok=False);save_plan(root,plan)
        (root/'metrics').mkdir();(root/'launcher_logs').mkdir()
        execute(plan,root,plan['jobs'],'pilot')
        print('14 attempts complete; run nomad_phase4.report --run-root for automatic report.',flush=True)

if __name__=='__main__':main()
