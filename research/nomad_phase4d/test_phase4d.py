import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase4c.config import validate_options, runtime_config
from nomad_phase4c.batch import matrix as old_matrix
from .config import ALPHAS, METHODS, protocol, reference_records, validate_frozen
from .batch import matrix, completion, execute
from .report import paired_table, bootstrap, assess, generate


def fixture_records():
    source = { (r['alpha'], r['method']): r for r in reference_records() if r['index'] == 1 }
    records = []
    for a in ALPHAS:
        for m in METHODS:
            for i in range(1, 9):
                r = copy.deepcopy(source[a, m])
                r.update(key=f'S0_{i:02d}_A{a}_{m}', index=i, run_id=f'S0_{i:02d}', seed_offset=10000*i,
                    reused=i <= 3, success=True, technical_validation='PASS', classification='SUCCESS',
                    goal_time_s=30.+i-(2. if m == 'GRAPH' else 0.))
                records.append(r)
    return records


class Tests(unittest.TestCase):
    def test_gate_seed_matrix_and_original_gate_preserved(self):
        jobs, refs = matrix(Path('/tmp/phase4d-never-run'))
        self.assertEqual((len(jobs), len(refs)), (20, 12))
        self.assertEqual({j['index'] for j in jobs}, set(range(4, 9)))
        self.assertEqual({j['method'] for j in jobs}, set(METHODS))
        self.assertEqual(len({j['output'] for j in jobs + refs}), 32)
        for j in jobs + refs:
            self.assertEqual(j['seed_offset'], 10000*j['index'])
        p = protocol()
        a = SimpleNamespace(phase4d_confirm=True, phase4c_method='CURV', plant_alpha='inf',
            asynchronous=True, pure_pursuit=True, scenario=ROOT/p['scenario'], topomap=ROOT.parent/p['topomap'],
            run_id='S0_04', seed_offset=40000, uniform_delivery_delay_s=.75)
        validate_options(a)
        for change in ({'phase4d_confirm': False}, {'phase4c_method': 'CURV+ACC'}, {'plant_alpha': '1.0'},
                       {'run_id': 'S0_03', 'seed_offset': 30000}, {'seed_offset': 0}, {'uniform_delivery_delay_s': 0.}):
            with self.assertRaises(ValueError): validate_options(SimpleNamespace(**{**vars(a), **change}))
        self.assertEqual(runtime_config({}, a)['phase4d_confirm'], True)
        self.assertEqual(tuple(map(len, old_matrix(Path('/tmp/phase4c-never-run')))), (21, 3))
        validate_frozen()

    def test_bootstrap_pairing_pooled_clusters_and_missing_times(self):
        records = fixture_records()
        pairs = paired_table(records)
        a = bootstrap(pairs); b = bootstrap(pairs)
        self.assertEqual(a, b)
        self.assertEqual((a['paired_success_n'], a['seed_clusters_n']), (16, 8))
        self.assertEqual(a['bootstrap_ci95_s'], [-2., -2.])
        # Identical across-alpha measurements must not double the independent sample count.
        for r in pairs:
            r['delta_graph_minus_curv_s'] = float(r['index']-5)
        single = bootstrap([r for r in pairs if r['alpha'] == 'inf'])
        pooled = bootstrap(pairs)
        np.testing.assert_array_equal(single['bootstrap_ci95_s'], pooled['bootstrap_ci95_s'])
        failed = next(r for r in records if r['alpha'] == 'inf' and r['method'] == 'GRAPH' and r['index'] == 1)
        failed.update(success=False, classification='STUCK', goal_time_s=None)
        row = paired_table(records)[0]
        self.assertIsNone(row['delta_graph_minus_curv_s']); self.assertIsNone(row['GRAPH_goal_s'])
        self.assertEqual(bootstrap([row])['paired_success_n'], 0)

    def test_preregistered_three_way_decision_and_fisher(self):
        records = fixture_records()
        d = assess(records, paired_table(records), 'pooled')
        self.assertEqual(d['verdict'], 'CONFIRMED'); self.assertEqual(d['fisher_exact_two_sided_p'], 1.)
        for r in records:
            if r['method'] == 'GRAPH': r['goal_time_s'] += 2.
        d = assess(records, paired_table(records), 'pooled')
        self.assertEqual(d['verdict'], 'PARTIAL'); self.assertFalse(d['speed_claim'])
        records[8].update(success=False, classification='STUCK', goal_time_s=None)
        d = assess(records, paired_table(records), 'pooled')
        self.assertEqual(d['verdict'], 'NOT_CONFIRMED')

    def test_batch_serial_no_retry_and_completion_status(self):
        jobs, _ = matrix(Path('/tmp/phase4d-fixture'))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root/'metrics').mkdir(); (root/'launcher_logs').mkdir()
            plan = {'jobs': jobs, 'git_sha': 'SYNTHETIC_TEST'}
            (root/'plan.json').write_text(json.dumps(plan))
            self.assertFalse(completion(root)[1])
            result = {'classification':'SUCCESS', 'technical_validation':'PASS', 'success':True}
            with patch('nomad_phase4c.batch.verify'), patch('nomad_phase4c.batch.git_state', return_value={'git_sha':'SYNTHETIC_TEST'}), \
                 patch('nomad_phase4c.batch.launch_one', side_effect=[1]+[0]*19) as launch, \
                 patch('builtins.print'):
                execute(plan, root, audit_fn=lambda *args: dict(result))
            self.assertEqual(launch.call_count, 20)
            state, done = completion(root)
            self.assertTrue(done); self.assertEqual(state['technical_passes'], 19)
            first = json.loads((root/'metrics'/f"{jobs[0]['key']}.json").read_text())
            self.assertEqual(first['classification'], 'TECHNICAL_FAILURE')

    def test_report_tables_only_no_overwrite(self):
        records = fixture_records()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); out = root/'results'; doc = root/'report.md'
            with patch('nomad_phase4d.report.load', return_value=(records, {'git_sha':'SYNTHETIC_TEST'})):
                result = generate(root, out, doc)
            self.assertEqual(result['overall_verdict'], 'CONFIRMED')
            self.assertEqual(len(result['conditions']), 6)
            self.assertTrue((out/'paired_goal_times.csv').is_file())
            self.assertFalse(list(out.glob('*.png')))
            self.assertIn('SYNTHETIC_TEST', doc.read_text())
            with self.assertRaises(AssertionError): generate(root, out, doc)


if __name__ == '__main__':
    unittest.main()
