"""Frozen serial overnight batch; no retries; navigation only with --execute."""
import argparse
import json
import shlex
import subprocess
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import rows
from nomad_phase0.s0_batch import exclusive_batch,git_state,save_plan,launch_one
from .config import protocol,validate_options,base_method,readiness

def matrix(root,phase,hard=None):
    if hard is None:hard=readiness()['included']
    p=protocol(phase);conditions=[]
    if phase==8:
        for i in range(9,25):
            methods=['CURV','SELECT','GRAPH','SELECT+GRAPH'] if i>=17 else ['SELECT+GRAPH','RTC-soft']+(['RTC-hard'] if hard else [])
            conditions.extend((i,.75,m) for m in methods)
    else:
        for i in range(1,9):
            conditions.extend((i,.75,m) for m in p['methods'])
            if i<=4:conditions.extend((i,0.,m) for m in ('CURV','GRAPH-v6'))
    jobs=[]
    for i,d,m in conditions:
        run_id=f'S{0 if phase==8 else 1}_{i:02d}';key=f'{run_id}_D{round(d*1000):03d}_{m}'
        a=SimpleNamespace(overnight_phase=phase,overnight_method=m,phase4c_method=base_method(m),plant_alpha='inf',asynchronous=True,pure_pursuit=True,scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id=run_id,seed_offset=10000*i,uniform_delivery_delay_s=d)
        # hard readiness is intentionally checked at build/launch, allowing offline matrix tests.
        if not (m=='RTC-hard' and hard is not None and not (ROOT/'research/nomad_phase8/readiness.json').exists()):validate_options(a)
        argv=['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','bash',str(ROOT/'research/python.sh'),'-m','nomad_isaac.launch','--overnight-phase',str(phase),'--overnight-method',m,'--phase4c-method',a.phase4c_method,'--plant-alpha','inf','--asynchronous','--pure-pursuit','--scenario',str(a.scenario),'--topomap',str(a.topomap),'--seed-offset',str(a.seed_offset),'--run-id',run_id,'--uniform-delivery-delay-s',str(d),'--output',str(root/key)]
        jobs.append(dict(key=key,method=m,alpha='inf',index=i,run_id=run_id,seed_offset=10000*i,delay_s=d,reused=False,output=str(root/key),argv=argv,shell_command=shlex.join(argv)))
    expected=(56 if hard else 48) if phase==8 else 40
    assert len(jobs)==len({j['key'] for j in jobs})==expected
    return jobs

def references(phase):
    if phase!=8:return []
    records=json.loads((ROOT/'research/results/phase7/runs.json').read_text())
    return [dict(r,reused=True) for r in records if r['delay_s']==.75 and r['method'] in ('CURV','RIGID-ENTRY','SELECT','GRAPH')]

def permitted_status(status):
    prefixes=('?? research/results/phase4_pilot/','?? docs/PHASE8_RESULTS.md','?? research/results/phase8/')
    return all(x in prefixes for x in status.splitlines())

def verify(plan):
    state=git_state();assert state['git_sha']==plan['git_sha'] and permitted_status(state['git_status']),'Commit code first; unexpected checkout edits'
    for path,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(path))==h,'Frozen input changed: '+path

def build_plan(root,phase):
    p=protocol(phase);state=git_state();gate=readiness()
    assert permitted_status(state['git_status']),'Commit source/protocol first'
    files=[]
    for package in ('nomad_phase8','nomad_phase9'):
        files+=list((ROOT/'research'/package).glob('*.py'))+list((ROOT/'research'/package).glob('*.json'))
    files += [ROOT/p['scenario'],ROOT.parent/p['topomap'],ROOT/'research/run_overnight_phase8_9.sh']
    files += [ROOT/'research/nomad_isaac'/n for n in ('launch.py','simulator.py','async_runtime.py')]
    files += [ROOT/n for n in p['protected_sha256']]
    manifest=json.loads((ROOT.parent/p['topomap']).read_text())
    from nomad_isaac.topomap import load_map
    images,_=load_map(ROOT.parent/p['topomap']);assert len(images)==p['topomap_nodes']
    # Map filenames are resolved by the canonical loader; hash every node file too.
    files+=list((ROOT.parent/p['topomap']).parent.glob('*.png'))
    checkpoint=ROOT.parent/'artifacts/checkpoints/nomad.pth';assert sha256_file(checkpoint)==p['checkpoint_sha256']
    files+=[checkpoint]
    if phase==8:files+=[ROOT/'research/results/phase7/runs.json',ROOT/'research/results/phase7/input_hashes.json']
    return dict(label=p['label'],git_sha=state['git_sha'],protocol=p,rtc_hard=gate['included'],jobs=matrix(root,phase,gate['included']),references=references(phase),fixed_input_sha256={str(f):sha256_file(f) for f in files})

def completion(root):
    if not (root/'plan.json').exists():return dict(state='NOT_STARTED',completed=0,expected=None)
    plan=json.loads((root/'plan.json').read_text());journal=rows(root/'execution.jsonl') if (root/'execution.jsonl').exists() else []
    ends=[r for r in journal if r['event']=='END'];starts=[r for r in journal if r['event']=='START'];marker=json.loads((root/'complete.json').read_text()) if (root/'complete.json').exists() else {}
    if marker:
        assert [r['key'] for r in ends]==[r['key'] for r in starts]==[j['key'] for j in plan['jobs'][:len(ends)]]
        assert marker['attempts']==len(ends)
    return dict(state=marker.get('status','RUNNING'),completed=len(ends),expected=len(plan['jobs']),current=starts[-1]['key'] if len(starts)>len(ends) else None,technical_passes=marker.get('technical_passes'))

def execute(plan,root):
    from .metrics import audit
    results=[];phase=plan['protocol']['phase']
    with (root/'execution.jsonl').open('x') as journal:
        def record(data):journal.write(json.dumps(dict(monotonic_ns=time.monotonic_ns(),git_sha=plan['git_sha'],**data))+'\n');journal.flush()
        for job in plan['jobs']:
            verify(plan);assert not Path(job['output']).exists(),'No retry/overwrite'
            record(dict(event='START',key=job['key']));code=None;start=time.monotonic()
            try:
                code=launch_one(job,root/'launcher_logs'/f"{job['key']}.log")
                if code:raise RuntimeError(f'Launcher exit {code}')
                metric=audit(Path(job['output']),job['run_id'],job['seed_offset'],job['delay_s'])
            except Exception as exc:metric=dict(classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False,error=repr(exc),traceback=traceback.format_exc())
            metric.update({k:v for k,v in job.items() if k not in ('argv','shell_command')});metric.update(launcher_exit_code=code,launch_and_audit_wall_s=time.monotonic()-start)
            write_json(root/'metrics'/f"{job['key']}.json",metric);results.append(metric)
            record(dict(event='END',key=job['key'],classification=metric['classification'],technical_validation=metric['technical_validation']))
            print(json.dumps(dict(key=job['key'],result=metric['classification'],technical_validation=metric['technical_validation'])),flush=True)
            if phase==9 and len(results)==4 and any(r['classification']=='TECHNICAL_FAILURE' for r in results):break
    status='PHASE9_ABORTED' if len(results)<len(plan['jobs']) else 'COMPLETE'
    write_json(root/'complete.json',dict(status=status,git_sha=plan['git_sha'],attempts=len(results),expected=len(plan['jobs']),technical_passes=sum(r['technical_validation']=='PASS' for r in results),retries=0))

def main(phase=8):
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--dry-run',action='store_true');g.add_argument('--status',action='store_true');p.add_argument('--run-root',type=Path,required=True);a=p.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(completion(root)));return
    assert not root.exists(),'Existing run root preserved; no resume/retry'
    if a.dry_run:
        jobs=matrix(root,phase);print(json.dumps(dict(navigation_started=0,attempts=len(jobs),jobs=jobs),indent=2));return
    with exclusive_batch():
        plan=build_plan(root,phase);verify(plan);root.mkdir(parents=True,exist_ok=False);save_plan(root,plan)
        (root/'metrics').mkdir();(root/'launcher_logs').mkdir();execute(plan,root)

if __name__=='__main__':main()
