import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from nomad_phase12 import methods
from nomad_phase12.methods import hermite_splice
from nomad_phase12.config import METHODS
from .config import protocol,assert_frozen
from .batch import matrix,execute,completion
from .offline import check_failed_input,edge_cases
from .report import comparisons,generate


class HermiteChecks(unittest.TestCase):
    def test_bool_fix_changes_no_numeric_path(self):
        code=inspect.getsource(hermite_splice).replace('join_endpoint_clamped=bool(s+.30>path.s[-1])','join_endpoint_clamped=s+.30>path.s[-1]')
        ns=dict(vars(methods));exec(code,ns);old=ns['hermite_splice']
        xy=np.column_stack([np.linspace(.02,.5,8),np.linspace(0,.1,8)])
        a,ma=old(xy,[0.,0.,.1]);b,mb=hermite_splice(xy,[0.,0.,.1]);np.testing.assert_array_equal(a,b)
        self.assertIsInstance(ma['join_endpoint_clamped'],np.bool_);self.assertIs(type(mb['join_endpoint_clamped']),bool)
        with self.assertRaises(TypeError):json.dumps(ma)
        ma['join_endpoint_clamped']=bool(ma['join_endpoint_clamped']);self.assertEqual(json.dumps(ma),json.dumps(mb))

    def test_actual_failed_switch_and_short_endpoint_paths(self):
        self.assertTrue(check_failed_input()['passed']);self.assertTrue(all(r['passed'] for r in edge_cases()))

    def test_ten_jobs_and_first_attempt_technical_gate(self):
        assert_frozen()
        for fail in (True,False):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'metrics').mkdir();(root/'launcher_logs').mkdir();jobs=matrix(root)
                self.assertEqual(len(jobs),10);self.assertEqual([j['seed_offset'] for j in jobs],[10000*i for i in range(25,35)])
                self.assertTrue(all(j['method']=='HERMITE-SPLICE' for j in jobs))
                plan=dict(jobs=jobs,git_sha='FIXTURE',protocol=protocol());(root/'plan.json').write_text(json.dumps(plan))
                with patch('nomad_phase12h.batch.verify'),patch('nomad_phase12h.batch.launch_one',return_value=1 if fail else 0) as launch,patch('nomad_phase12h.batch.audit',return_value=dict(classification='STUCK',technical_validation='PASS',success=False)),patch('builtins.print'):
                    execute(plan,root)
                state=completion(root)
                self.assertEqual(launch.call_count,1 if fail else 10)
                self.assertEqual(state['skipped'],9 if fail else 0)
                self.assertEqual(state['state'],'TECHNICAL_GATE_ABORTED' if fail else 'COMPLETE')

    def test_paired_criteria_and_one_figure_report(self):
        rs=[]
        for i in range(25,35):
            for m in METHODS:
                success=i<=30 if m=='HERMITE-SPLICE' else True
                rs.append(dict(key=f'{m}_{i}',index=i,method=m,delay_s=.75,classification='SUCCESS' if success else 'STUCK',technical_validation='PASS',success=success,
                    goal_time_s=20 if success else None,mean_speed_m_s=.2 if m=='HERMITE-SPLICE' else .25,minimum_obstacle_clearance_m=.03,source_phase='12-H' if m=='HERMITE-SPLICE' else '12'))
        c=comparisons(rs);self.assertEqual(c[0]['BEATS_HERMITE_SPLICE'],'PASS');self.assertEqual(c[0]['SPEED_VS_HERMITE_SPLICE'],'FASTER')
        bad=copy.deepcopy(rs)
        for r in bad:
            if r['method']=='HERMITE-SPLICE' and r['index']>=33:r['technical_validation']='FAIL'
        self.assertEqual(comparisons(bad)[0]['BEATS_HERMITE_SPLICE'],'INCONCLUSIVE');self.assertEqual(comparisons(bad)[0]['SPEED_VS_HERMITE_SPLICE'],'INCONCLUSIVE')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'results';doc=root/'report.md'
            with patch('nomad_phase12h.report.load',return_value=(rs,{'git_sha':'FIXTURE'},{'state':'COMPLETE','attempted':10,'skipped':0},{})):
                generate(root,out,doc)
                self.assertEqual(len(list(out.glob('*.png'))),1);self.assertIn('different commit',doc.read_text());self.assertIn('privileged reference',doc.read_text())
                with self.assertRaises(AssertionError):generate(root,out,doc)

if __name__=='__main__':unittest.main()
