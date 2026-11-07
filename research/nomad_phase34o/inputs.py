"""Audit all experimental R2 calls (including technical attempts), no solves."""
import argparse, csv, hashlib, json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase32o.evaluate import save, csvout, clean
from nomad_storage_sdf.loader import load_npz

OUT = ROOT / 'research/results/phase34o'
ARTIFACTS = ROOT.parent / 'artifacts/isaac6'
ROOTS = ('phase28_pilot_01', 'phase28t_main_01', 'phase29_01',
         'phase30r_dev_01', 'phase31p_01', 'phase32_01')
HASHES = {}


def register(path):
    path = Path(path).resolve()
    if str(path) not in HASHES:
        HASHES[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path


def read(path):
    return json.loads(register(path).read_text())


def lines(path):
    return [json.loads(x) for x in register(path).read_text().splitlines() if x] if Path(path).exists() else []


def trace(path):
    with register(path).open() as f:
        rows = list(csv.DictReader(f))
    return {round(float(r['simulation_time_s']) * 72): dict(
        pose=[float(r[k]) for k in ('x_m', 'y_m', 'yaw_rad')],
        vw=[float(r[k]) for k in ('v_m_s', 'w_rad_s')]) for r in rows}


def collect():
    inventories = read(ROOT / 'research/results/phase31d/runs.json') + read(ROOT / 'research/results/phase32/runs.json')
    by_output = {r['output']: r for r in inventories}
    collisions = read(ROOT / 'research/results/phase31e/box_collision_details.json')
    collision_by_job = {(v['row']['output'], v['row']['job_id']): v['row']['uid']
                        for v in collisions.values() if v['row']['underlying_path_state'] == 'R2'}
    cases = []
    for root_name in ROOTS:
        for log in sorted((ARTIFACTS / root_name).glob('**/repair.jsonl')):
            # No development smoke or preparation data mixed into experiment.
            relative = log.relative_to(ARTIFACTS / root_name)
            if relative.parts[0] not in ('main', 'dev', 'confirm'):
                continue
            run = log.parent; entries = lines(log)
            submits = [e for e in entries if e['event'] == 'SUBMIT']
            if not submits:
                continue
            cfg = read(run / 'scenario.json'); tr = trace(run / 'agent_trajectory.csv')
            controls = {round(e['simulation_time_s'] * 72): e for e in lines(run / 'controller.jsonl')}
            updates = lines(run / 'depth/updates.jsonl'); ec = lines(run / 'exec_cert.jsonl')
            pubs = np.array([u['publication_monotonic_ns'] for u in updates], dtype=np.int64)
            results = {e['job_id']: e for e in entries if e['event'] == 'RESULT'}
            apps = [e for e in entries if e['event'] == 'PATH_APPLIED' and e.get('kind') == 'REPAIR']
            copies = None
            def resolve_update(i):
                nonlocal copies
                path = Path(updates[i]['file'])
                if path.exists():
                    return str(register(path))
                if copies is None:
                    copies = {}
                    for f in sorted((run / 'repair_jobs').glob('input_*.npz')):
                        data = load_npz(f); m = json.loads(str(data['metadata']))
                        copies[(m.get('frame_id'), m.get('sim_s'))] = str(f)
                other = copies.get((updates[i]['frame_id'], updates[i]['sim_s']))
                return str(register(other)) if other else None
            for submit in submits:
                job_id = submit['job_id']; job_file = run / 'repair_jobs' / f'transport_{job_id:04d}.json'
                job = read(job_file)
                assert job['kind'] == 'R2' and len(job['samples_world']) == 8
                np.testing.assert_array_equal(job['B'], submit['B'])
                np.testing.assert_array_equal(job['samples_world'], submit['samples_world'])
                planning_file = str(register(job['snapshot_file']))
                # Verify restoration before any optimization; no writes to raw.
                field = load_npz(planning_file)
                assert np.isfinite(field['values']).all() and field['occupied'].shape == field['values'].shape
                result = results.get(job_id)
                matching = [a for a in apps if a['id'] == submit['id'] and a['simulation_time_s'] >= submit['simulation_time_s']]
                if result:
                    matching = [a for a in matching if abs(a['simulation_time_s'] - result['simulation_time_s']) < 1e-8]
                assert len(matching) <= 1
                app = matching[0] if matching else None
                event = app or result
                context = None
                if event:
                    tick = round(event['simulation_time_s'] * 72)
                    state = tr[tick]
                    if app:
                        np.testing.assert_allclose(state['pose'], app['pose'], atol=1e-9, rtol=0)
                    control = controls[tick]
                    i = int(np.searchsorted(pubs, control['monotonic_ns'], side='right')) - 1
                    assert i >= 0
                    snapshot = resolve_update(i)
                    previous = [e for e in ec if e['event'] == 'INSTALL' and e['apply_tick'] < tick]
                    cap = previous[-1]['speed_cap_m_s'] if previous else None
                    context = dict(tick=tick, simulation_time_s=tick/72,
                        pose=state['pose'], actual_vw=state['vw'], snapshot_file=snapshot,
                        snapshot_frame=updates[i]['frame_id'], snapshot_capture_s=updates[i]['sim_s'],
                        snapshot_age_s=tick/72-updates[i]['sim_s'], speed_cap_m_s=cap,
                        source='ACTUAL_INSTALL' if app else 'RESULT_DECISION_COUNTERFACTUAL',
                        map_status='EXACT_LATEST_PUBLISHED' if snapshot else 'MISSING_LATEST_MAP')
                inventory = by_output.get(str(run), {})
                run_key = run.parent.name
                method = inventory.get('method', run_key.split('_', 2)[-1])
                case = dict(case_id=f'J{len(cases):04d}', run=str(run), root=root_name,
                    stage=relative.parts[0], scene=inventory.get('scene', run_key.split('_')[0]),
                    index=inventory.get('index', int(run_key.split('_')[1])), method=method,
                    uid=inventory.get('uid', root_name+'_'+run_key), job_id=job_id,
                    fresh_id=submit['id'], dispatch_s=submit['simulation_time_s'],
                    B=job['B'], previous_vw=job.get('previous_vw', submit['previous_vw']),
                    samples_world=job['samples_world'], planning_snapshot_file=planning_file,
                    source_job_file=str(job_file), original_disposition=result.get('disposition') if result else 'NO_RESULT',
                    actual_install=app, ec_context=context,
                    collision_uid=collision_by_job.get((str(run), job_id)))
                cases.append(case)
    assert len(cases) == 411
    assert sum(c['root'] == 'phase32_01' for c in cases) == 44
    assert {c['collision_uid'] for c in cases if c['collision_uid']} == set(collision_by_job.values())
    summary = dict(jobs=len(cases), runs=len({c['run'] for c in cases}),
        roots=dict(Counter(c['root'] for c in cases)), collision_cases=sum(bool(c['collision_uid']) for c in cases),
        contexts=dict(Counter(c['ec_context']['source'] if c['ec_context'] else 'NO_RESULT' for c in cases)),
        maps=dict(Counter(c['ec_context']['map_status'] if c['ec_context'] else 'NO_RESULT' for c in cases)),
        scope='Experimental main/dev/confirm including technical attempts with jobs; smoke excluded')
    save(OUT / 'inputs.json', cases); save(OUT / 'input_hashes.json', HASHES); save(OUT / 'input_audit.json', summary)
    csvout(OUT / 'input_inventory.csv', [dict(case_id=c['case_id'], root=c['root'], scene=c['scene'], index=c['index'],
        method=c['method'], job_id=c['job_id'], original_disposition=c['original_disposition'],
        context=c['ec_context']['source'] if c['ec_context'] else 'NO_RESULT',
        map_status=c['ec_context']['map_status'] if c['ec_context'] else 'NO_RESULT', collision_uid=c['collision_uid']) for c in cases])
    print(json.dumps(clean(summary), indent=2))
    return cases


if __name__ == '__main__':
    collect()
