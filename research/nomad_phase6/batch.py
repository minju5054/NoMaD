"""Frozen serial Phase6 56-attempt batch; never launches without --execute."""
import argparse
import json
import shlex
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import rows
from nomad_phase0.s0_batch import exclusive_batch,save_plan,git_state,launch_one
from nomad_phase5.batch import build_plan as previous_plan
from nomad_phase4c.batch import verify
from .config import HERE,METHODS,protocol,base_method,validate_options
from .metrics import audit


def matrix(root):
    p=protocol();jobs=[]
    conditions=[(i,d,m) for i in p['indices'] for d in p['delay_sweep'] for m in ('CURV','GRAPH')]
    conditions += [(i,.75,'SELECT') for i in p['indices']]
    for i,d,method in conditions:
        key=f'S0_{i:02d}_D{round(d*1000):03d}_{method}'
        a=SimpleNamespace(phase6_method=method,phase4c_method=base_method(method),plant_alpha='inf',
            asynchronous=True,pure_pursuit=True,scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],
            run_id=f'S0_{i:02d}',seed_offset=10000*i,uniform_delivery_delay_s=d)
        validate_options(a)
        argv=['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV',
            'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','bash',str(ROOT/'research/python.sh'),'-m','nomad_isaac.launch',
            '--phase6-method',method,'--phase4c-method',a.phase4c_method,'--plant-alpha','inf',
            '--asynchronous','--pure-pursuit','--scenario',str(a.scenario),'--topomap',str(a.topomap),
            '--seed-offset',str(a.seed_offset),'--run-id',a.run_id,'--uniform-delivery-delay-s',str(d),'--output',str(root/key)]
        jobs.append(dict(key=key,method=method,alpha='inf',index=i,run_id=a.run_id,seed_offset=a.seed_offset,
            request_0_seed=101+a.seed_offset,request_0_ddpm_seed=102+a.seed_offset,delay_s=d,reused=False,
            output=str(root/key),argv=argv,shell_command=shlex.join(argv)))
    assert len(jobs)==len({j['key'] for j in jobs})==56
    return jobs


def references():
    p=protocol()
    return [dict(key=f'S0_{i:02d}_D750_{m}',method=m,alpha='inf',index=i,run_id=f'S0_{i:02d}',
        seed_offset=10000*i,delay_s=.75,reused=True,output=str(Path(p['reference_root'])/f'S0_{i:02d}_{m}'))
        for i in p['indices'] for m in p['reference_methods']]


def build_plan(root):
    plan=previous_plan(root);p=protocol();refs=references()
    paths=list(HERE.glob('*.py'))+[HERE/'protocol.json',ROOT/p['reference_results'],ROOT/'research/results/phase5/summary.json']
    for ref in refs:
        run=Path(ref['output']);metric=Path(p['reference_root'])/'metrics'/f"{ref['run_id']}_{ref['method']}.json"
        old=json.loads(metric.read_text());assert old['technical_validation']=='PASS'
        # Freeze all inputs consumed by the original audit and new mechanism analysis.
        paths += [metric,run/'phase5_applications.jsonl']+[run/n for n in old['input_log_sha256']]
        for n,h in old['input_log_sha256'].items():assert sha256_file(run/n)==h,'Reference changed: '+str(run/n)
    plan['fixed_input_sha256'].update({str(f):sha256_file(f) for f in paths})
    plan.update(label=p['label'],protocol=p,protocol_sha256=sha256_file(HERE/'protocol.json'),jobs=matrix(root),references=refs)
    return plan



def completion(root):
    if not root.exists():return {'state':'NOT_STARTED','completed':0,'expected':56},False
    journal=rows(root/'execution.jsonl') if (root/'execution.jsonl').exists() else []
    starts=[r['key'] for r in journal if r['event']=='START'];ends=[r['key'] for r in journal if r['event']=='END']
    marker=json.loads((root/'complete.json').read_text()) if (root/'complete.json').exists() else {}
    expected=[r['key'] for r in json.loads((root/'plan.json').read_text())['jobs']] if (root/'plan.json').exists() else []
    done=len(expected)==56 and starts==ends==expected and marker.get('attempts')==56
    return dict(state='COMPLETE' if done else 'INCOMPLETE',completed=len(ends),expected=56,
                technical_passes=marker.get('technical_passes'),git_sha=marker.get('git_sha')),done


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
                phase='audit';metric=audit_fn(Path(job['output']),job['run_id'],job['seed_offset'],job['delay_s'])
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
    parser=argparse.ArgumentParser(description=__doc__);g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',action='store_true');g.add_argument('--dry-run',action='store_true');g.add_argument('--status',action='store_true')
    parser.add_argument('--run-root',type=Path,required=True);a=parser.parse_args();root=a.run_root.resolve()
    if a.status:
        status,done=completion(root);print(json.dumps(status));raise SystemExit(0 if done else 1)
    assert not root.exists(),'Existing output preserved; no retry/resume/overwrite'
    plan=build_plan(root)
    if a.dry_run:print(json.dumps({'navigation_started':0,'jobs':plan['jobs']},indent=2));return
    with exclusive_batch():
        verify(plan);root.mkdir(parents=True,exist_ok=False);save_plan(root,plan)
        (root/'metrics').mkdir();(root/'launcher_logs').mkdir();execute(plan,root,audit_fn=audit)
    print('56 attempts complete; run nomad_phase6.report --run-root.',flush=True)


if __name__=='__main__':main()
