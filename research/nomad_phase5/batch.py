"""Frozen serial Phase5 48-attempt batch; never launches without --execute."""
import argparse
import json
import shlex
from pathlib import Path
from types import SimpleNamespace
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.async_report import rows
from nomad_phase0.s0_batch import exclusive_batch,save_plan
from nomad_phase4c.batch import build_plan as previous_plan,verify,execute
from .config import HERE,METHODS,protocol,base_method,validate_options
from .metrics import audit


def matrix(root):
    p=protocol();jobs=[]
    for i in range(9,17):
        for method in METHODS:
            key=f'S0_{i:02d}_{method}'
            a=SimpleNamespace(phase5_method=method,phase4c_method=base_method(method),plant_alpha='inf',
                asynchronous=True,pure_pursuit=True,scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],
                run_id=f'S0_{i:02d}',seed_offset=10000*i,uniform_delivery_delay_s=.75)
            validate_options(a)
            argv=['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV',
                'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','bash',str(ROOT/'research/python.sh'),'-m','nomad_isaac.launch',
                '--phase5-method',method,'--phase4c-method',a.phase4c_method,'--plant-alpha','inf',
                '--asynchronous','--pure-pursuit','--scenario',str(a.scenario),'--topomap',str(a.topomap),
                '--seed-offset',str(a.seed_offset),'--run-id',a.run_id,'--uniform-delivery-delay-s','.75','--output',str(root/key)]
            jobs.append(dict(key=key,method=method,alpha='inf',index=i,run_id=a.run_id,seed_offset=a.seed_offset,
                request_0_seed=101+a.seed_offset,request_0_ddpm_seed=102+a.seed_offset,delay_s=.75,reused=False,
                output=str(root/key),argv=argv,shell_command=shlex.join(argv)))
    assert len(jobs)==len({j['key'] for j in jobs})==48
    return jobs


def build_plan(root):
    plan=previous_plan(root);p=protocol()
    paths=list(HERE.glob('*.py'))+[HERE/'protocol.json']+[ROOT/n for n in p['protected_sha256']]
    plan['fixed_input_sha256'].update({str(f):sha256_file(f) for f in paths})
    plan.update(label=p['label'],protocol=p,protocol_sha256=sha256_file(HERE/'protocol.json'),jobs=matrix(root),references=[])
    return plan


def completion(root):
    if not root.exists():return {'state':'NOT_STARTED','completed':0,'expected':48},False
    journal=rows(root/'execution.jsonl') if (root/'execution.jsonl').exists() else []
    starts=[r['key'] for r in journal if r['event']=='START'];ends=[r['key'] for r in journal if r['event']=='END']
    marker=json.loads((root/'complete.json').read_text()) if (root/'complete.json').exists() else {}
    expected=[r['key'] for r in json.loads((root/'plan.json').read_text())['jobs']] if (root/'plan.json').exists() else []
    done=len(expected)==48 and starts==ends==expected and marker.get('attempts')==48
    return dict(state='COMPLETE' if done else 'INCOMPLETE',completed=len(ends),expected=48,
                technical_passes=marker.get('technical_passes'),git_sha=marker.get('git_sha')),done


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
    print('48 attempts complete; run nomad_phase5.report --run-root.',flush=True)


if __name__=='__main__':main()
