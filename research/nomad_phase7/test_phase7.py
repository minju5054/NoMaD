"""Phase7 minimum tests; no simulator or fresh model inference."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase6.metrics import compare_selection,mechanisms
from nomad_phase6.report import decide as previous_decide
from nomad_phase6.config import validate_options as legacy_gate
from nomad_phase6.batch import matrix as legacy_matrix
from nomad_phase5.batch import matrix as phase5_matrix
from .rtc import target
from .config import protocol,readiness,validate_options
from .batch import matrix,references,execute,completion
from .report import verdict,decide,generate


class Tests(unittest.TestCase):
    def test_select_float_tolerance_preserves_discrete_rule_and_old_runs(self):
        compare_selection({'selected':2,'safe':True,'clearance':.123},{'selected':2,'safe':True,'clearance':.123+2e-16})
        for changed in ({'selected':3,'safe':True,'clearance':.123},{'selected':2,'safe':False,'clearance':.123},
                        {'selected':2,'safe':True,'clearance':.123+1e-8}):
            with self.assertRaises(AssertionError):compare_selection({'selected':2,'safe':True,'clearance':.123},changed)
        r=json.loads((ROOT/'research/results/phase7_preparation/select_reaudit.json').read_text())['runs']
        self.assertEqual(len(r),8);self.assertTrue(all(x['technical_validation']=='PASS' for x in r))
        self.assertTrue(all(x['max_pose_replay_error']<1e-12 and x['max_pp_command_replay_error']<1e-12 for x in r))
        self.assertEqual(len((ROOT/'docs/PHASE7_SELECT_FIX.md').read_text().splitlines()),3)

    def test_target_normalized_delta_and_mask_projection(self):
        a=np.array([1.,2.,.7]);xy=np.c_[np.arange(8)*.1,np.zeros(8)]
        c,s=np.cos(a[2]),np.sin(a[2]);world=xy@np.array([[c,s],[-s,c]])+a[:2]
        r=target(world,a,.3,.89);self.assertEqual((r['d'],r['H_old']),(2,7))
        y=np.asarray(r['Y']);w=np.asarray(r['W'])
        restored=np.cumsum((y[:7]+1)/2*np.array([7.5,8])+np.array([-2.5,-4]),axis=0)*.05
        np.testing.assert_allclose(restored,r['target_local_xy_m'],atol=1e-14)
        np.testing.assert_allclose(w[:2],1);self.assertEqual(w[-1],0);self.assertTrue(np.all(np.diff(w)<=0))
        ci=(7-2)/(7-2+1);self.assertAlmostEqual(w[2],ci*np.expm1(ci)/np.expm1(1.))
        end=target(world,np.r_[world[-1],a[2]],.3,.89);self.assertEqual(end['H_old'],0);self.assertFalse(np.any(end['W']))

    def test_frozen_offline50_and_readiness_gate(self):
        p=protocol();r=json.loads((ROOT/p['readiness_results']).read_text())
        self.assertEqual(r['count'],50);self.assertEqual(r['max_off_error'],0);self.assertTrue(r['finite_all50'])
        self.assertGreater(r['frozen_sample0_median_m'],.01);self.assertEqual(readiness()['verdict'],'RTC_NOT_READY')
        cases=json.loads((ROOT/'research/results/phase7_offline/cases.json').read_text())
        self.assertEqual(len({(r['run'],r['id']) for r in cases}),50)
        self.assertTrue(all(x['d']>=1 and x['subgoal_reproduced'] for x in cases))
        self.assertEqual(p['beta'],5)
        for n,h in p['protected_sha256'].items():self.assertEqual(sha256_file(ROOT/n),h)

    def test_gate_seed_order_and_legacy625_rejection(self):
        jobs=matrix(Path('/tmp/phase7-never-run'));self.assertEqual(len(jobs),24);self.assertEqual(len(references()),72)
        for k in range(8):
            self.assertEqual([j['method'] for j in jobs[k*3:k*3+3]],['SELECT','CURV','GRAPH'])
            self.assertEqual([j['delay_s'] for j in jobs[k*3:k*3+3]],[.75,.625,.625])
            self.assertTrue(all(j['seed_offset']==10000*(k+9) for j in jobs[k*3:k*3+3]))
        p=protocol();a=SimpleNamespace(phase7_method='GRAPH',phase6_method='GRAPH',phase4c_method='GRAPH',plant_alpha='inf',
            asynchronous=True,pure_pursuit=True,scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],
            run_id='S0_09',seed_offset=90000,uniform_delivery_delay_s=.625)
        validate_options(a)
        for change in ({'uniform_delivery_delay_s':.75},{'plant_alpha':'2.0'},{'phase7_method':'RTC'},{'phase5_method':'GRAPH'}):
            with self.assertRaises(ValueError):validate_options(SimpleNamespace(**{**vars(a),**change}))
        old=vars(a).copy();old.pop('phase7_method')
        with self.assertRaises(ValueError):legacy_gate(SimpleNamespace(**old))
        self.assertEqual(len(legacy_matrix(Path('/tmp/phase6-never-run'))),56)
        self.assertEqual(len(phase5_matrix(Path('/tmp/phase5-never-run'))),48)

    def test_batch_serial_delays_no_retries(self):
        jobs=matrix(Path('/tmp/phase7-mocked-launch'));seen=[]
        def audit(*args):seen.append(args[-1]);return dict(classification='SUCCESS',technical_validation='PASS',success=True)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir();(root/'launcher_logs').mkdir();plan={'jobs':jobs}
            (root/'plan.json').write_text(json.dumps(plan))
            with patch('nomad_phase6.batch.verify'),patch('nomad_phase6.batch.git_state',return_value={'git_sha':'SYNTHETIC'}), \
                 patch('nomad_phase6.batch.launch_one',side_effect=[1]+[0]*23) as launch,patch('builtins.print'):
                execute(plan,root,audit)
            self.assertEqual(launch.call_count,24);self.assertEqual(seen,[j['delay_s'] for j in jobs[1:]])
            status,done=completion(root);self.assertTrue(done);self.assertEqual(status['technical_passes'],23)

    def test_minimum_valid_and_original_phase6_correction(self):
        self.assertEqual(verdict({'success':7,'valid':8},{'success':0,'valid':6}),'INCONCLUSIVE')
        self.assertEqual(verdict({'success':7,'valid':8},{'success':5,'valid':7}),'PASS')
        self.assertEqual(verdict({'success':7,'valid':8},{'success':6,'valid':8}),'FAIL')
        old=json.loads((ROOT/'research/results/phase6/runs.json').read_text());self.assertIsNone(previous_decide(old)['BEATS_SELECT'])
        original=json.loads((ROOT/'research/results/phase6/summary.json').read_text())
        self.assertTrue(original['decisions']['BEATS_SELECT']) # original artifact preserved

    def test_automatic_report_all_tables_and_not_run_rtc(self):
        base=json.loads((ROOT/'research/results/phase5/runs.json').read_text())[0]
        mech=mechanisms(Path(base['output']),True);records=[]
        for j in references()+matrix(Path('/tmp/phase7-synthetic')):
            r=copy.deepcopy(base);r.update({k:v for k,v in j.items() if k not in ('argv','shell_command')})
            success=j['index']< (16 if j['method']=='GRAPH' else 13)
            r.update(success=success,classification='SUCCESS' if success else 'STUCK',technical_validation='PASS',
                     goal_time_s=40. if success else None,inference_ms={'median':40.})
            r['mechanisms']=copy.deepcopy(mech)
            if not success:r['mechanisms']['failure_last3s']=copy.deepcopy(mech['full'])
            records.append(r)
        decision=decide(records);self.assertEqual(decision['BEATS_SELECT'],'PASS');self.assertEqual(decision['BEATS_RTC'],'INCONCLUSIVE')
        self.assertIn('625',decision['delta_success_counts'])
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'results';doc=Path(td)/'report.md'
            with patch('nomad_phase7.report.load',return_value=(records,{'git_sha':'SYNTHETIC'})):
                result=generate(Path(td),out,doc);self.assertEqual(result,decision)
            self.assertEqual(len(list(out.glob('*.png'))),2);self.assertIn('NOT RUN',doc.read_text());self.assertIn('Table 3',doc.read_text())
            summary=json.loads((out/'summary.json').read_text());self.assertTrue(any(g['delay_ms']==625 for g in summary['mechanisms']))
            with self.assertRaises(AssertionError):generate(Path(td),out,doc)


if __name__=='__main__':unittest.main()
