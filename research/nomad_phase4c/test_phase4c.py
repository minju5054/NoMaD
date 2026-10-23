import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from nomad_isaac.common import ROOT,integrate_se2
from nomad_isaac.async_core import WaypointExecution
from nomad_phase3_stage2.test_stage2 import FakeClient,metadata
from nomad_phase4.execution import command_policy as curv
from .plant import AngularPlant,control_command,limited_omega
from .execution import AccelExecution
from .batch import matrix
from .config import protocol,validate_options


class Tests(unittest.TestCase):
    def test_72hz_plant_identity_reversal_and_stops(self):
        for alpha in ('inf','2.0','1.0'):
            core=SimpleNamespace(pose=np.zeros(3),v=.2,w=0.);plant=AngularPlant(alpha);expected=core.pose.copy();previous=0.
            for tick in range(1,73):
                core.w=.4 if tick<25 else -.4 if tick<49 else 0.
                core.v=.2 if tick<49 else 0.
                v,w=plant.integrate(core,tick)
                if alpha=='inf':
                    self.assertEqual(w,core.w);expected=integrate_se2(expected,core.v,core.w,1/72)
                    np.testing.assert_array_equal(core.pose,expected)
                else:
                    self.assertLessEqual(abs(w-previous),float(alpha)/72+1e-12)
                    self.assertAlmostEqual(w,previous+np.clip(core.w-previous,-float(alpha)/72,float(alpha)/72))
                self.assertEqual(v,core.v);previous=w
            plant.close()
        self.assertAlmostEqual(limited_omega(.4,0,1),.4-1/72)

    def test_curv_acc_limits_and_infinite_identity(self):
        for k in (-20,-4,0,2,20):
            for v in (0,.05,.2,.3):
                for w in (-.4,0,.4):
                    a,_=control_command('CURV+ACC',k,v,w,float('inf'))
                    self.assertEqual(a,curv('CURV-SPEED',k,v)[0])
                    for alpha in (1.,2.):
                        (vv,ww),flags=control_command('CURV+ACC',k,v,w,alpha)
                        self.assertTrue(.05<=vv<=.3 and abs(ww)<=.4)
                        self.assertLessEqual(abs(vv-v),.5/9+1e-12)
        (v,w),flags=control_command('CURV+ACC',2,.2,0,1.)
        self.assertAlmostEqual(v,.2-.5/9);self.assertAlmostEqual(w,2*v)
        self.assertTrue(flags['angular_reach_limited'])
        self.assertTrue(control_command('CURV+ACC',0,.2,.4,1.)[1]['zero_curvature_unreachable'])

    def test_graph_handoff_uses_actual_omega_and_curv_execution(self):
        with tempfile.TemporaryDirectory() as td:
            fake=FakeClient();e=AccelExecution({'phase4c_method':'GRAPH','plant_alpha':'1.0'},Path(td),fake)
            core=WaypointExecution([0,0,0]);e.last_command=[.2,.4];e.plant.actual_w=.1
            core.receive(metadata(0,1_000_000_000),[.3,0])
            r,s=core.control(0,1_000_000_001);e.apply(core,r,s)
            self.assertAlmostEqual(r['commanded_v_m_s'],.2+.5/9);self.assertEqual(r['applied_w_rad_s'],.1)
            self.assertEqual(fake.jobs[0]['previous_command'],[.2,.1]);self.assertEqual(fake.jobs[0]['previous_commanded_vw'],[.2,.4])
            self.assertNotIn('actual_command_after',s['chunk_transition'])
            for tick in range(1,9):
                prev=core.pose.copy();e.plant.integrate(core,tick);e.integrate_record(prev,core.pose)
            points=np.column_stack([np.linspace(.1,.8,8),np.full(8,.1),np.zeros(8)])
            fake.results.append({'job_id':0,'id':0,'worker_start_ns':1_000_000_010,'worker_end_ns':1_050_000_010,
                'result_received_ns':1_055_000_000,'accepted':True,'poses':points.tolist(),
                'solver':{'success':True,'constraints_satisfied':True,'exact_certificate_pass':True}})
            r,s=core.control(8,1_111_111_111);e.apply(core,r,s)
            self.assertIsNone(s);self.assertTrue(r['stage2']['corrected_path_active'])
            self.assertEqual(r['stage2']['graph_applied_job'],0)
            expected=curv('CURV-SPEED',r['stage2']['kappa_pp'],.2+.5/9)[0]
            np.testing.assert_allclose([core.v,core.w],expected)
            for tick in range(9,17):e.plant.integrate(core,tick)
            before=core.pose.copy();actual=e.plant.actual_w
            r,s=core.control(16,2_111_111_111);e.apply(core,r,s)
            self.assertFalse(r['valid']);self.assertEqual([core.v,core.w],[0.,0.])
            e.plant.integrate(core,17)
            self.assertAlmostEqual(e.plant.actual_w,max(0.,actual-1/72))
            np.testing.assert_array_equal(core.pose[:2],before[:2]);e.close()
            log=[json.loads(x) for x in (Path(td)/'plant.jsonl').read_text().splitlines()]
            self.assertEqual(len(log),18)

    def test_gate_matrix_seed_and_no_reference_rerun(self):
        jobs,refs=matrix(Path('/tmp/phase4c-never-navigate'))
        self.assertEqual(len(jobs),21);self.assertEqual(len(refs),3)
        self.assertTrue(all(j['method']=='GRAPH' for j in jobs if j['alpha']=='inf'))
        for j in jobs+refs:self.assertEqual(j['seed_offset'],j['index']*10000)
        p=protocol();a=SimpleNamespace(phase4c_method='GRAPH',plant_alpha='inf',asynchronous=True,pure_pursuit=True,
            scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id='S0_01',seed_offset=10000,uniform_delivery_delay_s=.75)
        validate_options(a)
        for change in ({'phase4c_method':'CURV'},{'uniform_delivery_delay_s':0.},{'plant_alpha':'3.0'},{'phase4_method':'GRAPH-v5'},{'seed_offset':0}):
            with self.assertRaises(ValueError):validate_options(SimpleNamespace(**{**vars(a),**change}))
        from nomad_phase4.batch import matrix as v5matrix
        self.assertEqual(len(v5matrix(Path('/tmp/phase4-still-14'))),14)

    def test_report_decision_and_generation(self):
        from .report import decide,generate
        jobs,refs=matrix(Path('/tmp/phase4c-never-navigate'));all_jobs=refs+jobs
        source=ROOT.parent/'artifacts/isaac6/phase4_pilot_01'
        saved=json.loads((source/'metrics/S0_01_D750_CURV-SPEED.json').read_text());records=[]
        for j in all_jobs:
            row=copy.deepcopy(saved);row.update({k:v for k,v in j.items() if k not in ('argv','shell_command')})
            row.update(output=str(source/'S0_01_D750_CURV-SPEED'),success=True,classification='SUCCESS',
                omega_tracking_rms_rad_s=0.,omega_tracking_max_rad_s=0.,plant_intervals=100)
            if row['alpha']=='1.0' and row['method']!='GRAPH' and row['index']==1:row.update(success=False,classification='STUCK')
            records.append(row)
        self.assertEqual(decide(records)['verdict'],'ACCEL_ADVANTAGE_CANDIDATE')
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'results';doc=Path(td)/'report.md'
            with patch('nomad_phase4c.report.load',return_value=(records,{'git_sha':'SYNTHETIC_REPORT_TEST'},[])):
                generate(Path(td),out,doc)
            self.assertTrue((out/'alpha1_index1_paths.png').exists());self.assertTrue((out/'paired.csv').exists())
            self.assertIn('SYNTHETIC_REPORT_TEST',doc.read_text())
        records[-1]['success']=False;self.assertEqual(decide(records)['verdict'],'STOP_AND_REPORT')

if __name__=='__main__':unittest.main()
