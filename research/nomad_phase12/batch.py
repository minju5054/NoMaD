"""Serial70 frozen attempts; index25 technical gate drops only broken new methods."""
import argparse
import json
import shlex
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_phase0.s0_batch import exclusive_batch,git_state,save_plan,launch_one
from nomad_phase8.batch import build_plan as old_plan,verify
from .config import protocol,METHODS,internal,validate_options
from .methods import NEW


def matrix(root):
    p=protocol();jobs=[]
    for i in p['indices']:
        for m in METHODS:
            rid=f'S0_{i:02d}';key=f'{rid}_D750_{m}';output=str(root/key)
            a=SimpleNamespace(phase12_method=m,overnight_phase=8,overnight_method=internal(m),phase4c_method='GRAPH' if m in ('SELECT+GRAPH','FRESHEST+GRAPH-GF') else 'CURV',plant_alpha='inf',asynchronous=True,pure_pursuit=True,scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id=rid,seed_offset=10000*i,uniform_delivery_delay_s=.75)
            validate_options(a)
            argv=['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','bash',str(ROOT/'research/python.sh'),'-m','nomad_isaac.launch',
                '--phase12-method',m,'--overnight-phase','8','--overnight-method',a.overnight_method,'--phase4c-method',a.phase4c_method,'--plant-alpha','inf',
                '--asynchronous','--pure-pursuit','--scenario',str(a.scenario),'--topomap',str(a.topomap),'--seed-offset',str(a.seed_offset),'--run-id',rid,'--uniform-delivery-delay-s','.75','--output',output]
            jobs.append(dict(key=key,method=m,index=i,run_id=rid,seed_offset=a.seed_offset,delay_s=.75,output=output,argv=argv,shell_command=shlex.join(argv),reused=False))
    assert len(jobs)==len({j['key'] for j in jobs})==70
    return jobs


def build_plan(root):
    plan=old_plan(root,8);p=protocol();lock=json.loads((ROOT/'research/nomad_phase12/offline_validation_r2.json').read_text())
    assert lock['count']==30 and all(lock['checks'].values()),'Offline functionality gate failed'
    for name,h in lock['source_sha256'].items():assert sha256_file(ROOT/name)==h
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h
    plan.update(label=p['label'],protocol=p,phase8_protocol=plan['protocol'],jobs=matrix(root),references=[])
    files=list((ROOT/'research/nomad_phase12').glob('*.py'))+list((ROOT/'research/nomad_phase12').glob('*.json'))
    files += [ROOT/path for path in p['protected_sha256']]
    plan['fixed_input_sha256'].update({str(f):sha256_file(f) for f in files});return plan


def completion(root):
    if not (root/'plan.json').exists():return dict(state='NOT_STARTED',attempted=0,finished_slots=0,expected=70)
    plan=json.loads((root/'plan.json').read_text());path=root/'execution.jsonl'
    data=[json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    starts=[r['key'] for r in data if r['event']=='START'];ends=[r['key'] for r in data if r['event']=='END'];skips=[r['key'] for r in data if r['event']=='SKIP']
    marker=json.loads((root/'complete.json').read_text()) if (root/'complete.json').exists() else None
    if marker:
        assert starts==ends and len(ends)==marker['attempts'] and len(skips)==marker['skipped']
        assert [r['key'] for r in data if r['event'] in ('END','SKIP')]==[j['key'] for j in plan['jobs']]
    return dict(state=marker['status'] if marker else 'RUNNING',attempted=len(starts),completed=len(ends),skipped=len(skips),finished_slots=len(ends)+len(skips),expected=70,
                current=starts[-1] if len(starts)>len(ends) else None,technical_passes=marker['technical_passes'] if marker else None)


def execute(plan,root):
    from .metrics import audit
    disabled=set();results=[];skipped=[]
    with (root/'execution.jsonl').open('x') as journal:
        def record(**r):journal.write(json.dumps(dict(monotonic_ns=time.monotonic_ns(),git_sha=plan['git_sha'],**r))+'\n');journal.flush()
        for j in plan['jobs']:
            verify(plan);assert not Path(j['output']).exists(),'No retry/overwrite'
            meta={k:v for k,v in j.items() if k not in ('argv','shell_command')}
            if j['method'] in disabled:
                r=dict(**meta,classification='SKIPPED_TECHNICAL_GATE',technical_validation='NOT_RUN',success=False,error='New-method index25 technical gate')
                write_json(root/'metrics'/f"{j['key']}.json",r);skipped.append(r);record(event='SKIP',key=j['key'],method=j['method']);continue
            record(event='START',key=j['key']);start=time.monotonic();code=None
            try:
                code=launch_one(j,root/'launcher_logs'/f"{j['key']}.log")
                if code:raise RuntimeError(f'Launcher exit {code}')
                r=audit(Path(j['output']),j['run_id'],j['seed_offset'],j['delay_s'])
            except Exception as e:r=dict(classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False,error=repr(e),traceback=traceback.format_exc())
            r.update(meta);r.update(launcher_exit_code=code,launch_and_audit_wall_s=time.monotonic()-start)
            write_json(root/'metrics'/f"{j['key']}.json",r);results.append(r)
            record(event='END',key=j['key'],classification=r['classification'],technical_validation=r['technical_validation'])
            if j['index']==25 and j['method'] in NEW and r['classification']=='TECHNICAL_FAILURE':disabled.add(j['method'])
            if j['index']==25 and j['method']==METHODS[-1]:write_json(root/'technical_gate.json',dict(index=25,disabled_methods=sorted(disabled),attempts=7,results=[dict(method=r['method'],technical_validation=r['technical_validation']) for r in results]))
            print(json.dumps(dict(key=j['key'],result=r['classification'],technical_validation=r['technical_validation'])),flush=True)
    write_json(root/'complete.json',dict(status='COMPLETE',git_sha=plan['git_sha'],attempts=len(results),skipped=len(skipped),expected=70,technical_passes=sum(r['technical_validation']=='PASS' for r in results),disabled_methods=sorted(disabled),retries=0))


def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for k in ('execute','dry-run','status'):g.add_argument('--'+k,action='store_true')
    ap.add_argument('--run-root',required=True,type=Path);a=ap.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(completion(root)));return
    assert not root.exists(),'Existing outputs preserved'
    if a.dry_run:print(json.dumps(dict(navigation_started=0,attempts=70,jobs=matrix(root)),indent=2));return
    with exclusive_batch():
        plan=build_plan(root);verify(plan);root.mkdir(parents=True,exist_ok=False);save_plan(root,plan)
        (root/'metrics').mkdir();(root/'launcher_logs').mkdir();execute(plan,root)


if __name__=='__main__':main()
