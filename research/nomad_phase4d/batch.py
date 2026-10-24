"""20 new serial attempts; Phase4c's 12 existing records are never rerun."""
import argparse
import json
import shlex
from pathlib import Path
from types import SimpleNamespace
from nomad_isaac.common import ROOT, sha256_file
from nomad_isaac.async_report import rows
from nomad_phase0.s0_batch import exclusive_batch, save_plan
from nomad_phase4c.batch import build_plan as previous_plan, verify, execute
from nomad_phase4c.config import validate_options
from nomad_phase4c.metrics import audit as phase4c_audit
from .config import HERE, ALPHAS, METHODS, protocol, reference_records, validate_frozen


def matrix(root):
    p = protocol()
    jobs = []
    for i in range(4, 9):
        for alpha in ALPHAS:
            for method in METHODS:
                key = f'S0_{i:02d}_A{alpha}_{method}'
                a = SimpleNamespace(phase4d_confirm=True, phase4c_method=method, plant_alpha=alpha,
                    asynchronous=True, pure_pursuit=True, scenario=ROOT / p['scenario'],
                    topomap=ROOT.parent / p['topomap'], run_id=f'S0_{i:02d}',
                    seed_offset=10000 * i, uniform_delivery_delay_s=.75)
                validate_options(a)
                argv = ['env', '-u', 'LD_LIBRARY_PATH', '-u', 'LD_PRELOAD', '-u', 'PYTHONHOME',
                    '-u', 'VIRTUAL_ENV', 'OPENBLAS_NUM_THREADS=1', 'OMP_NUM_THREADS=1',
                    'bash', str(ROOT / 'research/python.sh'), '-m', 'nomad_isaac.launch',
                    '--phase4d-confirm', '--phase4c-method', method, '--plant-alpha', alpha,
                    '--asynchronous', '--pure-pursuit', '--scenario', str(a.scenario),
                    '--topomap', str(a.topomap), '--seed-offset', str(a.seed_offset),
                    '--run-id', a.run_id, '--uniform-delivery-delay-s', '.75', '--output', str(root / key)]
                jobs.append(dict(key=key, method=method, alpha=alpha, index=i, run_id=a.run_id,
                    seed_offset=a.seed_offset, request_0_seed=101+a.seed_offset,
                    request_0_ddpm_seed=102+a.seed_offset, delay_s=.75, reused=False,
                    output=str(root / key), argv=argv, shell_command=shlex.join(argv)))
    references = [{k: r[k] for k in ('key', 'method', 'alpha', 'index', 'run_id', 'seed_offset', 'delay_s', 'output')}
                  | {'reused': True, 'source_execution_git_sha': r['execution_git_sha']}
                  for r in reference_records()]
    references.sort(key=lambda r: (r['index'], ALPHAS.index(r['alpha']), METHODS.index(r['method'])))
    assert len(jobs) == len({j['key'] for j in jobs}) == 20 and len(references) == 12
    return jobs, references


def audit(run, run_id, offset, delay):
    prov = json.loads((run / 'provenance.json').read_text())
    scenario = json.loads((run / 'summary.json').read_text())['scenario']
    assert prov['phase4d_confirm'] is True and scenario['phase4d_confirm'] is True
    assert json.loads((run / 'phase4d_protocol.json').read_text()) == protocol()
    assert 4 <= int(run_id[-2:]) <= 8
    assert scenario['plant_alpha'] in ALPHAS and scenario['phase4c_method'] in METHODS
    r = phase4c_audit(run, run_id, offset, delay)
    r['label'] = protocol()['label']
    r['input_log_sha256']['phase4d_protocol.json'] = sha256_file(run / 'phase4d_protocol.json')
    return r


def build_plan(root):
    validate_frozen()
    plan = previous_plan(root)
    jobs, references = matrix(root)
    for r in reference_records():
        for name, digest in r['input_log_sha256'].items():
            f = Path(r['output']) / name
            assert sha256_file(f) == digest, f'Reused log changed: {f}'
            plan['fixed_input_sha256'][str(f)] = digest
    paths = list(HERE.glob('*.py')) + [HERE / 'protocol.json', ROOT / protocol()['reference_results']]
    paths += [ROOT / name for name in protocol()['protected_sha256']]
    plan['fixed_input_sha256'].update({str(f): sha256_file(f) for f in paths})
    plan.update(label=protocol()['label'], protocol=protocol(), protocol_sha256=sha256_file(HERE / 'protocol.json'),
                jobs=jobs, references=references)
    return plan


def completion(root):
    if not root.exists():
        return {'state': 'NOT_STARTED', 'completed': 0, 'expected': 20}, False
    journal = rows(root / 'execution.jsonl') if (root / 'execution.jsonl').exists() else []
    starts = [r['key'] for r in journal if r['event'] == 'START']
    ends = [r['key'] for r in journal if r['event'] == 'END']
    marker = json.loads((root / 'complete.json').read_text()) if (root / 'complete.json').exists() else {}
    expected = [r['key'] for r in json.loads((root / 'plan.json').read_text())['jobs']] if (root / 'plan.json').exists() else []
    done = len(expected) == 20 and starts == ends == expected and marker.get('attempts') == 20
    return {'state': 'COMPLETE' if done else 'INCOMPLETE', 'completed': len(ends), 'expected': 20,
            'technical_passes': marker.get('technical_passes'), 'git_sha': marker.get('git_sha')}, done


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true')
    group.add_argument('--dry-run', action='store_true')
    group.add_argument('--status', action='store_true')
    parser.add_argument('--run-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.run_root.resolve()
    if args.status:
        status, done = completion(root)
        print(json.dumps(status)); raise SystemExit(0 if done else 1)
    assert not root.exists(), 'Existing output preserved; no retries/resume/overwrite'
    plan = build_plan(root)
    if args.dry_run:
        print(json.dumps({'navigation_started': 0, 'jobs': plan['jobs'], 'reused': plan['references']}, indent=2)); return
    with exclusive_batch():
        verify(plan)
        root.mkdir(parents=True, exist_ok=False); save_plan(root, plan)
        (root / 'metrics').mkdir(); (root / 'launcher_logs').mkdir()
        execute(plan, root, audit_fn=audit)
    print('20 attempts complete. Generate the report with nomad_phase4d.report --run-root.', flush=True)


if __name__ == '__main__':
    main()
