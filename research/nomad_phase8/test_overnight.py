import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from nomad_isaac.common import ROOT
from nomad_isaac.async_core import WaypointExecution
from nomad_phase0.chunk_execution import describe_chunk
from nomad_phase0.graph_v4 import SignedDistanceField
from nomad_phase9.graph import GraphV6,FreeField
from nomad_phase9.intent import intention,splice,tangents,hermite,place
from nomad_phase8.config import protocol,runtime_config,validate_options
from nomad_phase8.batch import matrix
from nomad_phase8.execution import OvernightExecution,select
from nomad_phase8.report import verdict,paired_margin
from nomad_phase8.request import rtc_target
from nomad_phase1.s1 import VisibilityGate


def config(phase=9,method='CURV'):
    p=protocol(phase);source=json.loads((ROOT/p['scenario']).read_text());i=1 if phase==9 else 17
    args=SimpleNamespace(overnight_phase=phase,overnight_method=method,phase4c_method='GRAPH' if 'GRAPH' in method else 'CURV',plant_alpha='inf',asynchronous=True,pure_pursuit=True,scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id=f'S{1 if phase==9 else 0}_{i:02d}',seed_offset=10000*i,uniform_delivery_delay_s=.75)
    return runtime_config(source,args),args

class Checks(unittest.TestCase):
    def test_placement_left_right_clamp(self):
        c,_=config()
        for sign in (1,-1):
            for y in (0.,1.3,-1.3):
                c['diagnostic_y_offset_m']=sign*.15;p=place(c,[2.,y,0.]);b=p['obstacle']
                self.assertAlmostEqual(b['center_xy_m'][0],3.465)
                self.assertAlmostEqual(b['center_xy_m'][1],np.clip(y+sign*.15,-.925,.925))
                self.assertGreaterEqual(p['left_wall_gap_m'],.4-1e-12);self.assertGreaterEqual(p['right_wall_gap_m'],.4-1e-12)
                self.assertEqual(p['status'],'PLACED')
    def test_waypoint_side(self):
        c,_=config()
        for y,side in ((.15,-1),(-.15,1),(0.,1)):
            c['obstacles']=[{'id':'DynamicObstacle','center_xy_m':[3.465,y],'size_xyz_m':[.35,.35,.8]}]
            t=intention(c,[2.,0.,0.]);self.assertEqual(t['side'],side)
            np.testing.assert_allclose(t['V'],[3.465,y+side*.415]);self.assertIsNone(intention(c,[4.,0,0]))
    def test_hermite_c1(self):
        b=np.array([2.,0.,.3]);t={'V':[3.465,-.265],'E':[3.94,-.265]};ta,tv,te=tangents(b,t);v=np.array(t['V']);e=np.array(t['E'])
        path=splice(b,t);np.testing.assert_array_equal(path[0],b[:2]);np.testing.assert_array_equal(path[32],v);np.testing.assert_allclose(path[-1],e)
        h=1e-25
        left=np.imag(hermite(b[:2],v,ta,tv,1+1j*h))/h;right=np.imag(hermite(v,e,tv,te,1j*h))/h
        np.testing.assert_allclose(left,tv,atol=1e-12);np.testing.assert_allclose(right,tv,atol=1e-12)
    def test_intent_analytic_complex_step(self):
        c,_=config();c.pop('dynamic_obstacle');c['obstacles']=[{'id':'DynamicObstacle','center_xy_m':[3.465,.15],'size_xyz_m':[.35,.35,.8]}];c['public_intent']=intention(c,[2.,0.,0.])
        p=json.loads((ROOT/'research/nomad_phase0/graph_v4_protocol.json').read_text());xy=np.column_stack([np.linspace(2.1,3.7,8),np.linspace(.04,.16,8)])
        g=GraphV6(xy,[2.,0.,0.],[.2,.01],c,p,SignedDistanceField(c,p['sdf_resolution_m'],p['sdf_padding_m']))
        x=g.initial.ravel();r,j,_,_=g.residual_jacobian(x)
        for k in range(24):
            z=x.astype(complex);z[k]+=1e-25j
            np.testing.assert_allclose(np.imag(g.residual_jacobian(z)[0])/1e-25,j[:,k],atol=2e-9,rtol=2e-9)
    def test_empty_geometry_select(self):
        c,_=config();c.pop('dynamic_obstacle');samples=np.stack([np.column_stack([np.linspace(.1,.4+i*.02,8),np.zeros(8)]) for i in range(8)])
        xy,detail=select(samples,[0.,0.,0.],[0.,0.,0.],c);self.assertEqual(detail['selected_sample'],7);self.assertFalse(detail['all_unsafe'])
    def test_matrix_gate_seed(self):
        p8=matrix(Path('/tmp/test_only8'),8,False);p9=matrix(Path('/tmp/test_only9'),9,False)
        self.assertEqual((len(p8),len(p9)),(48,40));self.assertEqual([j['method'] for j in p9[:4]],protocol(9)['methods'])
        self.assertTrue(all(j['seed_offset']==10000*j['index'] for j in p8+p9))
        _,a=config();a.seed_offset+=1
        with self.assertRaises(AssertionError):validate_options(a)
    def test_oracle_capture_gate(self):
        g=VisibilityGate()
        def record(i,visible):return dict(observation_id=i,observation_sim_s=i*.25,capture_end_monotonic_ns=i*250000000,frame_sha256=str(i),rgb_file=str(i),dynamic={'active':i>=1,'visible':visible})
        self.assertFalse(g.observe(record(0,False))['geometry_available']);self.assertFalse(g.observe(record(1,True))['geometry_available']);self.assertTrue(g.observe(record(4,False))['geometry_available'])
    def test_subclass_execution_and_fallback(self):
        c,_=config(8,'SELECT');samples=np.stack([np.column_stack([np.linspace(.1,.4+i*.02,8),np.zeros(8)]) for i in range(8)])
        with tempfile.TemporaryDirectory() as tmp:
            executor=OvernightExecution(c,Path(tmp));core=WaypointExecution([0,0,0],72,9)
            row={'id':0,'received_monotonic_ns':1000000000,'observation_pose':[0,0,0],'observation_sim_s':0.,'observation_monotonic_ns':900000000,'chunk':describe_chunk(samples[0],[0,0,0]),'overnight_metric_samples':samples.tolist()}
            core.receive(row,samples[0,2]);refresh,event=core.control(0,1000000001);executor.apply(core,refresh,event)
            self.assertEqual(event['overnight']['selection']['selected_sample'],7);self.assertAlmostEqual(core.v,.5/9)
            self.assertEqual(event['chunk']['world_xy_m'],row['chunk']['world_xy_m'])
            refresh,event=core.control(8,2100000000);executor.apply(core,refresh,event);self.assertEqual((core.v,core.w),(0.,0.));executor.close()
    def test_rtc_disabled_and_real_old(self):
        snap=dict(command_valid=False,applied_id=-1,tick=1,pose=[0,0,0]);self.assertEqual(rtc_target(snap)['d'],0)
        snap.update(command_valid=True,applied_id=2,old_world_xy=[[.1,0],[.2,0],[.3,0]],actual_vw=[.3,0]);t=rtc_target(snap);self.assertEqual(t['d'],2)
    def test_phase9_runtime_setup_no_execution(self):
        from nomad_isaac.async_runtime import ExecutionThread
        c,_=config();c['goal_mode']='topomap'
        with tempfile.TemporaryDirectory() as tmp:
            engine=ExecutionThread(c,Path(tmp),pure_pursuit=True)
            self.assertIsNone(engine.phase2);self.assertIsNotNone(engine.stage2)
            self.assertTrue(engine.dynamic.s1);self.assertIsNone(engine.dynamic.obstacle)
            engine.stage2.close();engine.monitor.finish(False);engine.dynamic.finish(False)
    def test_graph_empty_public_and_prior(self):
        c,_=config();c.pop('dynamic_obstacle');c['public_intent']=None
        p=json.loads((ROOT/'research/nomad_phase0/graph_v4_protocol.json').read_text())
        xy=np.column_stack([np.linspace(.1,.6,8),np.zeros(8)])
        g=GraphV6(xy,[0,0,0],[.2,0],c,p,FreeField())
        r,j,_,_=g.residual_jacobian(g.initial.ravel());self.assertTrue(np.isfinite(r).all() and np.isfinite(j).all())
        certificate,ok=g.certificate(g.initial);self.assertTrue(ok);self.assertIsNone(certificate['obstacle_clearance_m'])
    def test_full_matrix_with_offline_gate(self):
        from nomad_phase8.config import readiness
        if not (ROOT/'research/nomad_phase8/readiness.json').exists():self.skipTest('one-shot offline gate not yet completed')
        jobs=matrix(Path('/tmp/no_navigation8'),8)
        self.assertEqual(len(jobs),56 if readiness()['included'] else 48)
        for i in range(9,25):
            order=[j['method'] for j in jobs if j['index']==i]
            self.assertEqual(order,(['CURV','SELECT','GRAPH','SELECT+GRAPH'] if i>=17 else ['SELECT+GRAPH','RTC-soft']+(['RTC-hard'] if readiness()['included'] else [])))
    def test_phase9_technical_gate_no_navigation(self):
        from unittest.mock import patch
        from nomad_phase8.batch import execute
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();(root/'launcher_logs').mkdir()
            jobs=matrix(root,9,False);calls=[]
            def launch(job,log):calls.append(job['key']);return 1 if len(calls)==2 else 0
            with patch('nomad_phase8.batch.verify'),patch('nomad_phase8.batch.launch_one',side_effect=launch),patch('nomad_phase8.metrics.audit',return_value=dict(classification='STUCK',technical_validation='PASS',success=False)),patch('builtins.print'):
                execute(dict(protocol=protocol(9),git_sha='TEST_ONLY',jobs=jobs),root)
            marker=json.loads((root/'complete.json').read_text())
            self.assertEqual(len(calls),4);self.assertEqual(marker['status'],'PHASE9_ABORTED')
    def test_phase8_failure_does_not_block_phase9_or_reports(self):
        import os,sys
        from unittest.mock import patch
        from nomad_phase8.overnight import main
        with tempfile.TemporaryDirectory() as tmp:
            fake=Path(tmp)/'repo';fake.mkdir();(Path(tmp)/'artifacts/isaac6').mkdir(parents=True)
            with patch('nomad_phase8.overnight.ROOT',fake),patch.object(sys,'argv',['overnight']),patch('nomad_phase8.overnight.subprocess.call',side_effect=[1,1,0,0]) as launch:
                with self.assertRaises(SystemExit) as exc:main()
            self.assertEqual(exc.exception.code,1);self.assertEqual(launch.call_count,4)
            records=[json.loads(x) for x in (Path(tmp)/'artifacts/isaac6/overnight_phase8_9.jsonl').read_text().splitlines()]
            self.assertEqual([r['stage'] for r in records if r['event']=='START'],['phase8_batch','phase8_report','phase9_batch','phase9_report'])
    def test_inconclusive_and_bootstrap(self):
        self.assertEqual(verdict([{'valid':13,'planned':16}],True),'INCONCLUSIVE')
        self.assertEqual(verdict([{'valid':14,'planned':16}],True),'PASS')
        rs=[dict(method=m,index=i,delay_s=.75,technical_validation='PASS',minimum_obstacle_clearance_m=v) for i in range(9,25) for m,v in (('GRAPH',.04),('SELECT',.03))]
        self.assertEqual(paired_margin(rs,'GRAPH','SELECT')['verdict'],'PASS')

if __name__=='__main__':unittest.main()
