"""Twenty serial user-launched Graph-v6.1 comparisons. No retries; dry-run never launches."""
import argparse
import json
import shlex
import time
import traceback
from pathlib import Path

from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_phase0.s0_batch import exclusive_batch, save_plan, launch_one
from nomad_phase8.batch import matrix as base_matrix, build_plan as base_plan, verify, completion
from .config import protocol


def matrix(root):
    jobs=[];originals=base_matrix(root,9,False)
    for i in range(1,9):
        for scene in ('sudden','noobs'):
            for d in (.75,0.):
                if i>(8 if scene=='sudden' and d==.75 else 4):continue
                j=dict(next(x for x in originals if (x['index'],x['delay_s'],x['method'])==(i,d,'GRAPH-v6')))
                key=f"{scene}_{j['key']}.1";output=str(root/key);argv=list(j['argv'])
                argv[argv.index('--output')+1]=output
                argv+=['--phase11-v61']+(['--phase10b-no-obstacle'] if scene=='noobs' else [])
                j.update(key=key,output=output,argv=argv,shell_command=shlex.join(argv),method='GRAPH-v6.1',scene=scene,phase11_v61=True)
                jobs.append(j)
    assert len(jobs)==len({j['key'] for j in jobs})==20
    return jobs


def build_plan(root):
    plan=base_plan(root,9);p=protocol()
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h,name
    plan.update(label=p['label'],protocol=p,phase9_protocol=plan['protocol'],jobs=matrix(root),references=[],rtc_hard=False)
    files=[]
    for package in ('nomad_phase10b','nomad_phase11'):
        files+=list((ROOT/'research'/package).glob('*.py'))+list((ROOT/'research'/package).glob('*.json'))
    files += [ROOT/path for ref in p['reference_sets'].values() for path in ref.values()]
    files += [ROOT/name for name in p['protected_sha256']]
    plan['fixed_input_sha256'].update({str(f):sha256_file(f) for f in files})
    return plan


def execute(plan,root):
    from .metrics import audit
    results=[]
    with (root/'execution.jsonl').open('x') as journal:
        def record(**r):
            journal.write(json.dumps(dict(monotonic_ns=time.monotonic_ns(),git_sha=plan['git_sha'],**r))+'\n');journal.flush()
        for j in plan['jobs']:
            verify(plan);assert not Path(j['output']).exists(),'No retry/overwrite'
            record(event='START',key=j['key']);start=time.monotonic();code=None
            try:
                code=launch_one(j,root/'launcher_logs'/f"{j['key']}.log")
                if code:raise RuntimeError(f'Launcher exit {code}')
                r=audit(Path(j['output']),j['run_id'],j['seed_offset'],j['delay_s'])
            except Exception as exc:
                r=dict(classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False,error=repr(exc),traceback=traceback.format_exc())
            r.update({k:v for k,v in j.items() if k not in ('argv','shell_command')})
            r.update(launcher_exit_code=code,launch_and_audit_wall_s=time.monotonic()-start)
            write_json(root/'metrics'/f"{j['key']}.json",r);results.append(r)
            record(event='END',key=j['key'],classification=r['classification'],technical_validation=r['technical_validation'])
            print(json.dumps(dict(key=j['key'],result=r['classification'],technical_validation=r['technical_validation'])),flush=True)
    write_json(root/'complete.json',dict(status='COMPLETE',git_sha=plan['git_sha'],attempts=len(results),expected=20,
        technical_passes=sum(r['technical_validation']=='PASS' for r in results),retries=0))


def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for name in ('execute','dry-run','status'):g.add_argument('--'+name,action='store_true')
    ap.add_argument('--run-root',required=True,type=Path);a=ap.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(completion(root)));return
    assert not root.exists(),'Preserve existing output; no resume/retry'
    if a.dry_run:
        jobs=matrix(root);print(json.dumps(dict(navigation_started=0,attempts=len(jobs),jobs=jobs),indent=2));return
    with exclusive_batch():
        plan=build_plan(root);verify(plan);root.mkdir(parents=True,exist_ok=False);save_plan(root,plan)
        (root/'metrics').mkdir();(root/'launcher_logs').mkdir();execute(plan,root)


if __name__=='__main__':main()
