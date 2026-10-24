"""21 serial launches plus three frozen reused CURV runs; report automatically."""
import argparse
import json
import shlex
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_phase0.s0_batch import git_state,exclusive_batch,launch_one,save_plan
from nomad_phase4.batch import build_plan as prior_plan
from .config import HERE,METHODS,protocol,validate_options,allowed_status
from .metrics import audit


def matrix(root):
    p=protocol();jobs=[];references=[]
    for i in range(1,4):
        references.append({'key':f'S0_{i:02d}_Ainf_CURV','method':'CURV','alpha':'inf','index':i,
            'run_id':f'S0_{i:02d}','seed_offset':i*10000,'delay_s':.75,'reused':True,
            'output':str(Path(p['reuse_root'])/f'S0_{i:02d}_D750_CURV-SPEED')})
        for alpha,methods in (('inf',('GRAPH',)),('2.0',METHODS),('1.0',METHODS)):
            for method in methods:
                key=f'S0_{i:02d}_A{alpha}_{method}'
                a=SimpleNamespace(phase4c_method=method,plant_alpha=alpha,asynchronous=True,pure_pursuit=True,
                    scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id=f'S0_{i:02d}',
                    seed_offset=i*10000,uniform_delivery_delay_s=.75)
                validate_options(a)
                argv=['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV',
                    'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','bash',str(ROOT/'research/python.sh'),
                    '-m','nomad_isaac.launch','--phase4c-method',method,'--plant-alpha',alpha,
                    '--asynchronous','--pure-pursuit','--scenario',str(a.scenario),'--topomap',str(a.topomap),
                    '--seed-offset',str(a.seed_offset),'--run-id',a.run_id,'--uniform-delivery-delay-s','.75',
                    '--output',str(root/key)]
                jobs.append({'key':key,'method':method,'alpha':alpha,'index':i,'run_id':a.run_id,
                    'seed_offset':a.seed_offset,'request_0_seed':101+a.seed_offset,'request_0_ddpm_seed':102+a.seed_offset,
                    'delay_s':.75,'reused':False,'output':str(root/key),'argv':argv,'shell_command':shlex.join(argv)})
    assert len(jobs)==len({j['output'] for j in jobs})==21 and len(references)==3
    return jobs,references


def build_plan(root):
    plan=prior_plan(root);p=protocol();jobs,references=matrix(root)
    paths=list(HERE.glob('*.py'))+[HERE/'protocol.json']
    for r in references:
        run=Path(r['output'])
        paths += [run/name for name in ('summary.json','scenario.json','provenance.json','agent_trajectory.csv',
            'controller.jsonl','events.jsonl','received.jsonl','requests.jsonl','observations.jsonl','clearance.jsonl',
            'stage2_graph.jsonl','model/inference.jsonl','model/environment.json')]
    preexisting=ROOT/'research/results/phase4_pilot'
    if preexisting.exists():paths+=list(preexisting.glob('*'))
    plan['fixed_input_sha256'].update({str(f):sha256_file(f) for f in paths if f.is_file()})
    plan.update(label=p['label'],protocol=p,protocol_sha256=sha256_file(HERE/'protocol.json'),jobs=jobs,references=references,
        preexisting_status=git_state()['git_status'])
    return plan


def verify(plan):
    assert allowed_status(git_state()['git_status']),'Only preexisting report outputs may be untracked; commit source first'
    assert git_state()['git_status']==plan['preexisting_status'],'Checkout changed'
    for name,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(name))==h,'Frozen input changed: '+name


def execute(plan,root,audit_fn=audit):
    sha=git_state()['git_sha'];results=[]
    with (root/'execution.jsonl').open('x') as journal:
        def record(row):journal.write(json.dumps({'monotonic_ns':time.monotonic_ns(),'git_sha':sha,**row})+'\n');journal.flush()
        for job in plan['jobs']:
            verify(plan);assert git_state()['git_sha']==sha
            assert not Path(job['output']).exists(),'No overwrite/retry'
            record({'event':'START','key':job['key'],'retry':False});code=None;phase='launcher';start=time.monotonic()
            try:
                code=launch_one(job,root/'launcher_logs'/f"{job['key']}.log")
                if code:raise RuntimeError(f'Launcher exit {code}')
                phase='audit';metric=audit_fn(Path(job['output']),job['run_id'],job['seed_offset'],.75)
            except Exception as e:
                metric={'classification':'TECHNICAL_FAILURE','technical_validation':'FAIL','success':False,
                    'error':repr(e),'traceback':traceback.format_exc(),'failure_stage':phase}
            metric.update({k:v for k,v in job.items() if k not in ('argv','shell_command')})
            metric.update(launcher_exit_code=code,launch_and_audit_wall_s=time.monotonic()-start)
            write_json(root/'metrics'/f"{job['key']}.json",metric);results.append(metric)
            record({'event':'END','key':job['key'],'classification':metric['classification'],'technical_validation':metric['technical_validation']})
            print(json.dumps({'key':job['key'],'result':metric['classification'],'validation':metric['technical_validation']}),flush=True)
    verify(plan)
    write_json(root/'complete.json',{'git_sha':sha,'attempts':len(results),'technical_passes':sum(r['technical_validation']=='PASS' for r in results),'retries':0})


def main():
    p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--dry-run',action='store_true')
    p.add_argument('--run-root',type=Path,required=True);a=p.parse_args();root=a.run_root.resolve()
    assert not root.exists(),'Output exists; no overwrite/retry/resume'
    plan=build_plan(root)
    if a.dry_run:
        print(json.dumps({'navigation_started':0,'jobs':plan['jobs'],'reused':plan['references']},indent=2));return
    assert not (ROOT/'research/results/phase4c').exists() and not (ROOT/'docs/PHASE4C_ACCEL_LIMIT.md').exists(),'Existing report preserved'
    with exclusive_batch():
        verify(plan);root.mkdir(parents=True,exist_ok=False);save_plan(root,plan)
        (root/'metrics').mkdir();(root/'launcher_logs').mkdir()
        execute(plan,root)
    from .report import generate
    result=generate(root,ROOT/'research/results/phase4c',ROOT/'docs/PHASE4C_ACCEL_LIMIT.md')
    print(result['verdict'],flush=True)

if __name__=='__main__':main()
