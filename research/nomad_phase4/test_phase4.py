import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from nomad_isaac.common import ROOT, integrate_se2, sha256_file
from nomad_isaac.async_core import WaypointExecution
from nomad_phase0.chunk_execution import ChunkExecution
from nomad_phase0.graph_v4 import GraphV4
from nomad_phase3_stage2.test_stage2 import FakeClient,metadata
from .config import protocol,validate_options
from .graph_v5 import GraphV5,SignedDistanceField
from .execution import command_policy,predict_boundary,decision,Phase4Execution,V5Client
from .batch import matrix


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=protocol();cls.gp=cls.p['graph_parameters']
        cls.c=json.loads((ROOT/cls.p['scenario']).read_text())
        cls.field=SignedDistanceField(cls.c,cls.gp['sdf_resolution_m'],cls.gp['sdf_padding_m'])

    def fixture(self,v=.2,w=.03):
        xy=np.column_stack([np.linspace(.112,.812,8),.013+np.linspace(0,.7,8)**2*.07])
        return GraphV5(xy,[0,0,.01],[v,w],self.c,self.gp,self.field)

    def test_speed_curvature_and_analytic_derivatives(self):
        g=self.fixture();x=g.initial_vector.copy();x[24:]=np.linspace(.2,.27,8)
        values,jac,eq,je=g.constraints(x);base=GraphV4.constraints(g,x[:24])[0]
        k=g.geometry(x)[2][[0,0,1,2,3,4,5,5]]
        np.testing.assert_allclose(values[len(base):len(base)+8],1-k*x[24:]/.4)
        # Complex-step checks are verification only; the solver uses explicit analytic Jacobians.
        of,oj=g.objective(x)
        for i in range(32):
            z=x.astype(complex);z[i]+=1e-25j
            np.testing.assert_allclose(g.objective(z)[0].imag/1e-25,oj[i],atol=1e-6,rtol=1e-6)
            zz=g.constraints(z)
            np.testing.assert_allclose(zz[0].imag/1e-25,jac[:,i],atol=1e-6,rtol=1e-6)
            np.testing.assert_allclose(zz[2].imag/1e-25,je[:,i],atol=1e-6,rtol=1e-6)
        for k in (-20,-4,0,4,20):
            for v in (0,.05,.2,.3):
                (vv,w),flags=command_policy('CURV-SPEED',k,v)
                self.assertTrue(.05<=vv<=.3 and abs(w)<=.4 and abs(vv-v)<=.5/9+1e-12)
        cmd,_=command_policy('GRAPH-v5',2,.1,{'s_m':[0,.5],'v_m_s':[.1,.3]},.25)
        np.testing.assert_allclose(cmd,[.2,.4])
        self.assertEqual(command_policy('RAW',0,0)[0],(.3,0.))

    def test_acceleration_constraint(self):
        g=self.fixture();x=g.initial_vector.copy();x[24:]=[.05,.3,.05,.3,.05,.3,.05,.3]
        length=g.geometry(x)[0];values=g.constraints(x)[0][-14:];change=np.diff(x[24:]**2)
        np.testing.assert_allclose(values,np.r_[length-change,length+change])
        x[24:]=.2;self.assertTrue(np.all(g.constraints(x)[0][-14:]>=0))
        self.assertAlmostEqual(g.constraints(x)[2][-1],0)

    def test_boundary_mismatch_runtime_profile_and_timeout(self):
        pose=np.array([1.,.2,.4]);np.testing.assert_allclose(predict_boundary(pose,[.3,.4]),integrate_se2(pose,.3,.4,2/9))
        result={'id':0,'worker_start_ns':1_000_000_010,'worker_end_ns':1_050_000_010,'accepted':True,'solver':{'success':True}}
        self.assertEqual(decision(result,0,True,[.021,0,0],[0,0,0])[0],'APP_MISMATCH')
        self.assertEqual(decision(result,0,True,[.019,0,0],[0,0,0])[0],'ACCEPTED')
        self.assertEqual(decision(result,1,True,[0,0,0],[0,0,0])[0],'SUPERSEDED')
        self.assertEqual(decision({**result,'worker_end_ns':1_400_000_010},0,True,[0,0,0],[0,0,0])[0],'STALE')
        with tempfile.TemporaryDirectory() as d:
            fake=FakeClient();exe=Phase4Execution({'phase4_method':'GRAPH-v5'},Path(d),fake)
            core=WaypointExecution([0,0,0]);core.receive(metadata(0,1_000_000_000),[.3,0])
            refresh,switch=core.control(0,1_000_000_001);exe.apply(core,refresh,switch)
            self.assertAlmostEqual(core.v,.5/9)
            np.testing.assert_allclose(fake.jobs[0]['boundary'],predict_boundary([0,0,0],[core.v,core.w]))
            before=core.pose.copy();core.pose=integrate_se2(core.pose,core.v,core.w,1/9);exe.integrate_record(before,core.pose)
            poses=np.column_stack([np.linspace(.1,.8,8),np.zeros(8),np.zeros(8)])
            profile={'s_m':np.linspace(0,.7,8).tolist(),'v_m_s':np.linspace(.15,.3,8).tolist()}
            fake.results.append({**result,'job_id':0,'result_received_ns':1_055_000_000,'poses':poses.tolist(),'speed_profile':profile})
            refresh,switch=core.control(8,1_111_111_111);exe.apply(core,refresh,switch)
            self.assertEqual(refresh['stage2']['graph_applied_job'],0);self.assertEqual(core.v,.15)
            self.assertEqual(core.latest['received_monotonic_ns'],1_000_000_000)
            refresh,switch=core.control(80,2_111_111_111);exe.apply(core,refresh,switch)
            self.assertFalse(refresh['valid']);self.assertEqual((core.v,core.w),(0.,0.));exe.close()
        with tempfile.TemporaryDirectory() as d:
            client=V5Client(Path(d));self.assertTrue(client.ready.is_set());client.close()

    def test_zero_speed_initialization(self):
        g=self.fixture(0,0)
        self.assertTrue(g.zero_speed_variant);self.assertEqual(g.v0,.05)
        self.assertEqual(g.initial[0,2],g.boundary[2]);self.assertEqual(g.kappa_before,0)
        self.assertTrue(np.all(g.initial_vector[24:]==.05))

    def test_gate_seed_legacy_and_report_decision(self):
        jobs=matrix(Path('/tmp/phase4-never-navigate'));self.assertEqual(len(jobs),14)
        for j in jobs:
            self.assertEqual(j['seed_offset'],j['index']*10000)
            self.assertEqual(j['request_0_seed'],101+j['seed_offset'])
        opts=SimpleNamespace(phase4_method='GRAPH-v5',asynchronous=True,pure_pursuit=True,
            scenario=ROOT/self.p['scenario'],topomap=ROOT.parent/self.p['topomap'],run_id='S0_01',seed_offset=10000,uniform_delivery_delay_s=.75)
        validate_options(opts)
        for change in ({'uniform_delivery_delay_s':.5},{'pure_pursuit':False},{'s0_stage2_method':'GRAPH'},{'seed_offset':0}):
            with self.assertRaises(ValueError):validate_options(SimpleNamespace(**{**vars(opts),**change}))
        for name,digest in self.p['protected_sha256'].items():self.assertEqual(sha256_file(ROOT/name),digest)
        core=WaypointExecution([0,0,0]);exe=ChunkExecution();core.receive(metadata(0,10),[.3,0]);r,s=core.control(0,11);exe.apply(core,r,s)
        self.assertEqual((core.v,core.w),(.2,0.));self.assertNotIn('stage2',r)
        from .report import decision as verdict
        records=[{**j,'technical_validation':'PASS','success':True,'goal_time_s':8 if j['method']=='GRAPH-v5' else 10} for j in jobs]
        self.assertEqual(verdict(records)['verdict'],'PROCEED_TO_PARETO')
        records[-1]['success']=False;self.assertEqual(verdict(records)['verdict'],'STOP_AND_REPORT')
        for r in records:
            if r['method']=='CURV-SPEED':r['success']=False
        self.assertFalse(verdict(records)['checks']['D750_graph_goal_median_le_90pct_curv'])
        # End-to-end report formatting with explicitly synthetic method labels; never a new run.
        from unittest.mock import patch
        from .report import generate
        source=ROOT.parent/'artifacts/isaac6/phase3_stage2_s0_01'
        saved=json.loads((source/'metrics/S0_01_D750_GRAPH.json').read_text())
        fake_records=[]
        for j in jobs:
            row=copy.deepcopy(saved);row.update({k:v for k,v in j.items() if k not in ('argv','shell_command')})
            row['output']=str(source/'S0_01_D750_GRAPH')
            row['graph']['temporal_acceleration_exceedance_ticks']=0
            fake_records.append(row)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'results';doc=Path(td)/'report.md'
            with patch('nomad_phase4.report.load',return_value=(fake_records,{'git_sha':'SYNTHETIC_REPORT_TEST'}, {}, [])):
                generate(Path(td),out,doc)
            self.assertTrue((out/'d750_paths.png').exists())
            self.assertIn('SYNTHETIC_REPORT_TEST',doc.read_text())
            self.assertTrue((out/'conditions.csv').exists())

if __name__=='__main__':unittest.main()
