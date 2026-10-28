import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import ROOT,local_to_world
from nomad_phase15.depth_sdf import DepthSDF
from nomad_phase15b.depth import Snapshot,evaluate_samples
from nomad_phase8 import rtc_hard
from nomad_phase8.request import rtc_target
from .config import METHODS,SCENES,RTC,PROPOSED,runtime_config,scene,protocol
from .statistics import paired,speed_label,composite,decisions


def fake_runs():
    return [dict(scene=sc,index=i,method=m,key=f'{sc}_{i}_{m}',output='/tmp/phase18_synthetic_no_raw',
        technical_validation='PASS',classification='SUCCESS',success=True,collision=False,corridor=False,stuck=False,
        checkpoint_time_s=20+(i-66)+SCENES.index(sc)+(0 if m==PROPOSED else 2),goal_time_s=30.,
        minimum_oracle_clearance_m=.1,minimum_obstacle_clearance_m=.1,minimum_wall_clearance_m=.2)
        for i in range(66,74) for sc in SCENES for m in METHODS]


class Tests(unittest.TestCase):
    def test_rtc_target_roundoff_does_not_relax_discrete_choices(self):
        from .metrics import assert_target_equal
        a=dict(Y=[[.1,.2]],W=[1.],d=1,H_old=1,old_waypoint_indices=[0])
        b=copy.deepcopy(a);b['Y'][0][0]+=2.22e-16;assert_target_equal(a,b)
        b['d']=0
        with self.assertRaises(AssertionError):assert_target_equal(a,b)
        b=copy.deepcopy(a);b['Y'][0][0]+=.001
        with self.assertRaises(AssertionError):assert_target_equal(a,b)

    def test_shared_wrapper_defers_scientific_imports_until_kit(self):
        import ast
        file=Path(__file__).with_name('simulator.py');tree=ast.parse(file.read_text())
        imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertEqual([n.names[0].name if isinstance(n,ast.Import) else n.module for n in imports],['ast','sys','pathlib'])
        self.assertNotIn('runpy',file.read_text())
        import sys
        from importlib.machinery import PathFinder
        fixed_path=[str(ROOT/'research/nomad_phase17'),*sys.path[1:]]
        found=PathFinder.find_spec('statistics',fixed_path)
        self.assertNotIn('nomad_phase18',found.origin)
        self.assertIn('sys.path[0]=str(source.parent)',file.read_text())
        launcher=Path(__file__).with_name('launch.py').read_text()
        self.assertEqual(launcher.count("str(ROOT/'research/nomad_phase18/simulator.py')"),1)
        self.assertNotIn('simulator_'+str(METHODS[0]),launcher)

    def test_rtc_eight_samples_reach_shared_safe_selector(self):
        from .execution import make_execution
        from nomad_phase17.execution import SafeExecution
        run=ROOT.parent/'artifacts/isaac6/phase12_baselines_02/S0_25_D750_RTC-hard'
        e=next(json.loads(l) for l in (run/'events.jsonl').read_text().splitlines() if json.loads(l)['id']==1)
        control=next(json.loads(l) for l in (run/'controller.jsonl').read_text().splitlines() if json.loads(l)['simulation_time_s']==e['application_sim_s'])
        with np.load(run/'model/derived/0001.npz') as z:samples=z['metric'].copy()
        field=DepthSDF([-4,-3.5,8,6.2]);field.values[:]=.5
        snap=Snapshot(field,dict(file='synthetic',frame_id=0,sim_s=0.))
        worlds=np.array([local_to_world(x,e['observation_pose']) for x in samples])
        expected,detail=evaluate_samples(worlds,e['agent_pose_at_switch'],snap)
        with tempfile.TemporaryDirectory() as tmp:
            obj=make_execution(dict(phase18=True,phase15b_method=RTC),Path(tmp));self.assertIsInstance(obj,SafeExecution)
            self.assertIsNone(obj.client);obj.depth_maps=SimpleNamespace(snapshot=lambda:snap)
            core=SimpleNamespace(pose=np.array(e['agent_pose_at_switch']),v=0.,w=0.,latest={'id':1},applied_id=1)
            e=copy.deepcopy(e);e['overnight_metric_samples']=samples.tolist();e['chunk']['world_xy_m']=worlds[0].tolist()
            with patch('nomad_phase16.execution.evaluate_samples',wraps=evaluate_samples) as spy:obj.apply(core,copy.deepcopy(control),e)
            np.testing.assert_array_equal(spy.call_args.args[0],worlds);self.assertEqual(spy.call_args.args[0].shape,(8,8,2))
            self.assertEqual(e['phase16']['selection']['selected_sample'],detail['selected_sample'])
            np.testing.assert_array_equal(obj.follower.path.points,expected);obj.close()

    def test_d0_preserves_protected_delegate(self):
        sentinel=object();model=object();condition=object();noise=object();y=np.zeros((8,2));w=np.ones(8)
        with patch.object(rtc_hard,'soft_diffuse',return_value=sentinel) as delegate:
            self.assertIs(rtc_hard.diffuse(model,condition,noise,123,y,w,0),sentinel)
            delegate.assert_called_once_with(model,condition,noise,123,y,w,5.)
        snapshot=dict(command_valid=True,old_world_xy=np.c_[np.linspace(.1,.8,8),np.zeros(8)].tolist(),pose=[0,0,0],actual_vw=[0,0],applied_id=2,tick=10)
        t=rtc_target(snapshot);self.assertEqual(t['d'],0);self.assertGreater(sum(t['W']),0)
        t=rtc_target({**snapshot,'old_world_xy':None});self.assertEqual(t['d'],0);self.assertEqual(sum(t['W']),0)

    def test_protocol_matrix_hashes_and_gate_reuse(self):
        from .config import verify_sources
        from .campaign import plan_jobs
        p=verify_sources();jobs=plan_jobs(ROOT.parent/'artifacts/isaac6/phase18_confirm_01')
        self.assertEqual(len(jobs),144);self.assertLess(max(j['socket_bytes'] for j in jobs),100)
        self.assertEqual({j['index'] for j in jobs},set(range(66,74)))
        self.assertTrue(all(j['seed_offset']==j['index']*10000 for j in jobs));self.assertEqual(len(p['gate_metric_files']),6)
        c=runtime_config(scene('CL'),RTC,66,p['topomaps']['CL']['manifest'])
        self.assertEqual(c['overnight_method'],'RTC-hard');self.assertEqual(c['phase4c_method'],'CURV')

    def test_cluster_ci_and_all_primary_labels(self):
        records=fake_runs();p=paired(records,METHODS[1],'checkpoint_time_s')
        self.assertEqual(p['n'],24);self.assertEqual(p['seed_clusters'],8);self.assertEqual(p['ci'],[-2.,-2.])
        self.assertAlmostEqual(p['confidence'],1-.05/3);self.assertEqual(speed_label(p),'FASTER')
        self.assertEqual(speed_label({**p,'ci':[1,2]}),'SLOWER');self.assertEqual(speed_label({**p,'ci':[-1,1]}),'INCONCLUSIVE')
        self.assertEqual(speed_label({**p,'n':11}),'INSUFFICIENT_PAIRS')
        self.assertEqual(composite(True,True,True),'CONFIRMED');self.assertEqual(composite(False,True,True),'PARTIAL')
        self.assertEqual(composite(True,False,False),'NOT_CONFIRMED');self.assertEqual(composite(True,None,None),'INCONCLUSIVE')
        d=decisions(records,'INCONCLUSIVE');self.assertEqual(d['overall'],'ALL_CONFIRMED')
        next(r for r in records if r['method']==PROPOSED)['technical_validation']='FAIL'
        self.assertTrue(all(r['combined']=='INCONCLUSIVE' for r in decisions(records,'INCONCLUSIVE')['primary']))

    def test_fake_report_tables_and_figures(self):
        from .report import render
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);doc=folder/'report.md'
            result=render(fake_runs(),folder/'results',doc,dict(protocol_sha256='SYNTHETIC',execution_git_sha='TEST_ONLY'))
            self.assertEqual(result['overall'],'ALL_CONFIRMED')
            for file in ['runs.json','summary.csv','paired.csv','decisions.json','checkpoint_by_method.png','paired_diff.png','clearance_by_method.png','paths_SLW.png','paths_LC.png','paths_CL.png']:
                self.assertTrue((folder/'results'/file).exists(),file)
            text=doc.read_text();self.assertIn('사전 등록 확인 실험',text);self.assertIn('98.333333%',text);self.assertIn('RTC hard-masking ablation (DDPM adaptation)',text)


if __name__=='__main__':unittest.main()
