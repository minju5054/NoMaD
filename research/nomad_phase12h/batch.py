"""Ten sequential HERMITE attempts; failed index25 gate ends the experiment."""
import argparse
import json
import time
import traceback
from pathlib import Path
from nomad_isaac.common import ROOT,write_json,sha256_file
from nomad_phase0.s0_batch import exclusive_batch,save_plan,launch_one
from nomad_phase8.batch import build_plan as base_plan,verify
from nomad_phase12.batch import matrix as phase12_matrix
from nomad_phase12.metrics import audit
from .config import HERE,protocol,assert_frozen,references


def matrix(root):
    jobs=[j for j in phase12_matrix(root) if j['method']=='HERMITE-SPLICE']
    assert len(jobs)==10 and [j['index'] for j in jobs]==list(range(25,35))
    return jobs


def build_plan(root):
    p=assert_frozen();offline=json.loads((HERE/'offline_validation.json').read_text())
    assert offline['passed'] and offline['phase8_cases']==30 and offline['failed_run_cases']==1
    for name,digest in offline['source_sha256'].items():assert sha256_file(ROOT/name)==digest,name
    previous=references();plan=base_plan(root,8)
    plan.update(label=p['label'],protocol=p,phase8_protocol=plan['protocol'],jobs=matrix(root),references=[{k:r[k] for k in ('key','method','index','output','classification','reused')} for r in previous])
    files=[f for pkg in ('nomad_phase12','nomad_phase12h') for suffix in ('*.py','*.json') for f in (ROOT/'research'/pkg).glob(suffix)]
    plan['fixed_input_sha256'].update({str(f):sha256_file(f) for f in files})
    plan['fixed_input_sha256'].update(p['reference_sha256'])
    return plan


def completion(root):
    root=Path(root)
    if not (root/'plan.json').exists():return dict(state='NOT_STARTED',attempted=0,completed=0,skipped=0,expected=10)
    plan=json.loads((root/'plan.json').read_text());journal=root/'execution.jsonl'
    data=[json.loads(l) for l in journal.read_text().splitlines()] if journal.exists() else []
    starts=[r['key'] for r in data if r['event']=='START'];ends=[r['key'] for r in data if r['event']=='END'];skips=[r['key'] for r in data if r['event']=='SKIP']
    marker=json.loads((root/'complete.json').read_text()) if (root/'complete.json').exists() else None
    if marker:
        assert starts==ends and len(ends)==marker['attempts'] and len(skips)==marker['skipped']
        assert [r['key'] for r in data if r['event'] in ('END','SKIP')]==[j['key'] for j in plan['jobs']]
    return dict(state=marker['status'] if marker else 'RUNNING',attempted=len(starts),completed=len(ends),skipped=len(skips),expected=10,
                current=starts[-1] if len(starts)>len(ends) else None,technical_passes=marker['technical_passes'] if marker else None)


def execute(plan,root):
    results=[];stopped=False
    with (root/'execution.jsonl').open('x') as stream:
        def log(**r):stream.write(json.dumps(dict(monotonic_ns=time.monotonic_ns(),git_sha=plan['git_sha'],**r))+'\n');stream.flush()
        for j in plan['jobs']:
            assert not Path(j['output']).exists(),'No overwrite/retry'
            meta={k:v for k,v in j.items() if k not in ('argv','shell_command')}
            if stopped:
                r=dict(**meta,classification='SKIPPED_TECHNICAL_GATE',technical_validation='NOT_RUN',success=False,error='Index25 technical failure; no further navigation')
                write_json(root/'metrics'/f"{j['key']}.json",r);log(event='SKIP',key=j['key']);continue
            verify(plan);log(event='START',key=j['key']);start=time.monotonic();code=None
            try:
                code=launch_one(j,root/'launcher_logs'/f"{j['key']}.log")
                if code:raise RuntimeError(f'Launcher exit {code}')
                r=audit(Path(j['output']),j['run_id'],j['seed_offset'],j['delay_s'])
            except Exception as exc:r=dict(classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False,error=repr(exc),traceback=traceback.format_exc())
            r.update(meta);r.update(source_phase='12-H',launcher_exit_code=code,launch_and_audit_wall_s=time.monotonic()-start)
            write_json(root/'metrics'/f"{j['key']}.json",r);results.append(r)
            log(event='END',key=j['key'],classification=r['classification'],technical_validation=r['technical_validation'])
            if j['index']==25:
                stopped=r['classification']=='TECHNICAL_FAILURE'
                write_json(root/'technical_gate.json',dict(index=25,technical_validation=r['technical_validation'],stop_remaining=stopped))
            print(json.dumps(dict(key=j['key'],result=r['classification'],technical_validation=r['technical_validation'])),flush=True)
    write_json(root/'complete.json',dict(status='TECHNICAL_GATE_ABORTED' if stopped else 'COMPLETE',git_sha=plan['git_sha'],attempts=len(results),skipped=10-len(results),technical_passes=sum(r['technical_validation']=='PASS' for r in results),retries=0))


def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for name in ('execute','dry-run','status'):g.add_argument('--'+name,action='store_true')
    ap.add_argument('--run-root',required=True,type=Path);a=ap.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(completion(root)));return
    assert not root.exists(),'Existing outputs preserved'
    if a.dry_run:print(json.dumps(dict(navigation_started=0,jobs=matrix(root)),indent=2));return
    with exclusive_batch():
        plan=build_plan(root);verify(plan);root.mkdir(parents=True,exist_ok=False);save_plan(root,plan)
        (root/'metrics').mkdir();(root/'launcher_logs').mkdir();execute(plan,root)

if __name__=='__main__':main()
