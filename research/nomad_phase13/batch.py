"""Frozen 48 serial attempts. Technical failures do not skip later jobs."""
import argparse
import json
import shlex
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_phase0.s0_batch import exclusive_batch, git_state, save_plan, launch_one
from nomad_phase8.batch import verify
from .config import HERE, protocol, validate_options
from .methods import GF


def matrix(root):
    p = protocol()
    jobs = []
    for i in p['indices']:
        for m in p['method_order'][str(i)]:
            rid = f'S0_{i:02d}'
            key = f'{rid}_D750_{m}'
            a = SimpleNamespace(phase13_method=m, overnight_phase=8, overnight_method='CURV',
                phase4c_method='GRAPH' if m == GF else 'CURV', plant_alpha='inf', asynchronous=True,
                pure_pursuit=True, scenario=ROOT/p['scenario'], topomap=ROOT.parent/p['topomap'],
                run_id=rid, seed_offset=10000*i, uniform_delivery_delay_s=.75)
            validate_options(a)
            argv = ['env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','VIRTUAL_ENV',
                'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','bash',str(ROOT/'research/python.sh'),
                '-m','nomad_isaac.launch','--phase13-method',m,'--overnight-phase','8','--overnight-method','CURV',
                '--phase4c-method',a.phase4c_method,'--plant-alpha','inf','--asynchronous','--pure-pursuit',
                '--scenario',str(a.scenario),'--topomap',str(a.topomap),'--seed-offset',str(a.seed_offset),
                '--run-id',rid,'--uniform-delivery-delay-s','.75','--output',str(root/key)]
            jobs.append(dict(key=key,method=m,index=i,run_id=rid,seed_offset=a.seed_offset,delay_s=.75,
                output=str(root/key),argv=argv,shell_command=shlex.join(argv)))
    assert len(jobs) == len({j['key'] for j in jobs}) == 48
    return jobs


def build_plan(root):
    p = protocol()
    state = git_state()
    # Existing unrelated untracked results are explicitly excluded from the experiment.
    assert state['git_status'].strip() in ('', '?? research/results/phase4_pilot/'), 'Commit source/protocol first'
    check = json.loads((HERE/'offline_validation.json').read_text())
    assert check['passed']
    for name, h in check['source_sha256'].items():
        assert sha256_file(ROOT/name) == h, name
    from nomad_isaac.topomap import load_map
    images, _ = load_map(ROOT.parent/p['topomap'])
    assert len(images) == p['topomap_nodes']
    ckpt = ROOT.parent/'artifacts/checkpoints/nomad.pth'
    assert sha256_file(ckpt) == p['checkpoint_sha256']
    files = [ROOT/p['scenario'], ROOT.parent/p['topomap'], ckpt]
    files += list((ROOT.parent/p['topomap']).parent.glob('*.png'))
    files += [ROOT/n for n in p['protected_sha256']]
    files += [ROOT/n for n in check['source_sha256']]
    files += [HERE/'offline_validation.json']
    plan = dict(label=p['label'], git_sha=state['git_sha'], protocol=p, jobs=matrix(root),
                fixed_input_sha256={str(f):sha256_file(f) for f in files})
    verify(plan)
    return plan


def completion(root):
    if not (root/'plan.json').exists():
        return dict(state='NOT_STARTED', completed=0, expected=48)
    plan = json.loads((root/'plan.json').read_text())
    journal = root/'execution.jsonl'
    data = [json.loads(l) for l in journal.read_text().splitlines()] if journal.exists() else []
    starts = [r['key'] for r in data if r['event']=='START']
    ends = [r['key'] for r in data if r['event']=='END']
    marker = json.loads((root/'complete.json').read_text()) if (root/'complete.json').exists() else None
    if marker:
        assert starts == ends == [j['key'] for j in plan['jobs']] and len(ends)==48
    return dict(state='COMPLETE' if marker else 'RUNNING', completed=len(ends), expected=48,
                current=starts[-1] if len(starts)>len(ends) else None,
                technical_passes=marker['technical_passes'] if marker else None)


def execute(plan, root):
    from .metrics import audit
    results = []
    with (root/'execution.jsonl').open('x') as journal:
        def record(**r):
            journal.write(json.dumps(dict(monotonic_ns=time.monotonic_ns(),git_sha=plan['git_sha'],**r))+'\n')
            journal.flush()
        for job in plan['jobs']:
            verify(plan)
            assert not Path(job['output']).exists(), 'No retry/overwrite'
            record(event='START',key=job['key'])
            code = None
            start = time.monotonic()
            try:
                code = launch_one(job, root/'launcher_logs'/f"{job['key']}.log")
                if code:
                    raise RuntimeError(f'Launcher exit {code}')
                r = audit(Path(job['output']),job['run_id'],job['seed_offset'],job['delay_s'])
            except Exception as exc:
                r = dict(classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False,
                         error=repr(exc),traceback=traceback.format_exc())
            r.update({k:v for k,v in job.items() if k not in ('argv','shell_command')})
            r.update(launcher_exit_code=code,launch_and_audit_wall_s=time.monotonic()-start)
            write_json(root/'metrics'/f"{job['key']}.json",r)
            results.append(r)
            record(event='END',key=job['key'],classification=r['classification'],technical_validation=r['technical_validation'])
            print(json.dumps(dict(key=job['key'],result=r['classification'])),flush=True)
    write_json(root/'complete.json',dict(status='COMPLETE',git_sha=plan['git_sha'],attempts=48,
        technical_passes=sum(r['technical_validation']=='PASS' for r in results),retries=0,skipped=0))


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    for name in ('execute','dry-run','status'):
        g.add_argument('--'+name,action='store_true')
    ap.add_argument('--run-root',required=True,type=Path)
    a = ap.parse_args()
    root = a.run_root.resolve()
    if a.status:
        print(json.dumps(completion(root))); return
    assert not root.exists(), 'Existing run root preserved'
    if a.dry_run:
        print(json.dumps(dict(navigation_started=0,attempts=48,jobs=matrix(root)),indent=2)); return
    with exclusive_batch():
        plan = build_plan(root)
        root.mkdir(parents=True,exist_ok=False)
        save_plan(root,plan)
        (root/'metrics').mkdir()
        (root/'launcher_logs').mkdir()
        execute(plan,root)


if __name__=='__main__':
    main()
