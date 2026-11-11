"""Frozen executor/selection/asset/launcher/bootstrap wiring tests only."""
import copy,inspect,json,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase0.chunk_execution import describe_chunk
from nomad_phase4c.execution import AccelExecution
from nomad_phase4c.plant import control_command
from nomad_phase40p.launch import bind
from nomad_phase18 import config as old
from nomad_phase18.statistics import paired as frozen_paired
from . import config,execution,launch,campaign,statistics,report

class Tests(unittest.TestCase):
    def test24_configs_original_assets_control_and_checkpoint(self):
        p=config.verify_sources();self.assertEqual(len(config.registered_order()),24)
        for j in config.registered_order():
            manifest=Path(p['topomaps'][j['scene']]['manifest']);scene=config.scene(j['scene'])
            before=old.runtime_config(scene,old.METHODS[0],j['index'],manifest,90)
            c=config.runtime_config(scene,'NOMAD_RAW',j['index'],manifest,90)
            changed={'phase18raw','phase15b_method','raw_sample_index','nomad_goal_stop'}
            self.assertEqual({k:v for k,v in c.items() if k not in changed},{k:v for k,v in before.items() if k not in changed})
            self.assertEqual(c['checkpoint'],scene['checkpoint']);self.assertEqual(c['goal_tolerance_m'],.3);self.assertEqual(c['phase4c_method'],'CURV');self.assertTrue(c['depth_camera']);self.assertIs(c['nomad_goal_stop'],False)
        self.assertEqual(p['retries'],0)
    def test_actual_launcher_argument_checks24_no_subprocess(self):
        class Boundary(Exception):pass
        jobs=campaign.plan_jobs(config.RUN_ROOT);self.assertEqual(len(jobs),24)
        for j in jobs:
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No simulator')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            argv=['launch','--mode','navigation','--scene',j['scene'],'--method','NOMAD_RAW','--index',str(j['index']),'--delay','.75','--topomap',config.protocol()['topomaps'][j['scene']]['manifest'],'--output',j['output']]
            with patch.object(sys,'argv',argv),self.assertRaises(Boundary):fn()
        with patch('subprocess.Popen',return_value=object()) as popen:
            launch.Processes().Popen(['isaac',str(config.ROOT/'research/nomad_phase18/simulator.py')]);self.assertIn(str(config.HERE/'simulator.py'),popen.call_args.args[0])
    def test_sample0_PP_CURV_commands_no_depth_query_or_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);e=execution.RawExecution(root)
            e.depth_maps=SimpleNamespace(snapshot=lambda:SimpleNamespace(metadata={'frame_id':0,'sim_s':0.}),query=lambda *_:self.fail('depth selection forbidden'))
            pose=np.array([1.,2.,.2]);core=SimpleNamespace(pose=pose.copy(),v=0.,w=0.)
            samples=np.array([np.c_[np.linspace(.1,1,8),np.full(8,i*.1)] for i in range(8)])
            switch=dict(id=0,observation_pose=pose.tolist(),observation_sim_s=0.,chunk=describe_chunk(samples[0],pose),overnight_metric_samples=samples.tolist(),topomap={'closest_node':9,'goal_node':9})
            refresh=dict(simulation_time_s=1.,monotonic_ns=time.monotonic_ns(),valid=True,waypoint_id=0,status='valid')
            try:
                e.apply(core,refresh,switch)
                np.testing.assert_array_equal(e.follower.path.points,switch['chunk']['world_xy_m']);self.assertIsNone(e.client)
                expected=control_command('CURV',refresh['stage2']['kappa_pp'],0.,0.,float('inf'))[0]
                np.testing.assert_array_equal([core.v,core.w],expected);self.assertGreater(core.v,0.)
                self.assertEqual(e.settings['follower']['lookahead_m'],.25)
                self.assertEqual(switch['phase18raw']['sample'],0);self.assertFalse(switch['phase18raw']['recovery'])
                json.dumps(switch,allow_nan=False);json.dumps(refresh,allow_nan=False)
                expired=dict(simulation_time_s=2.1,monotonic_ns=time.monotonic_ns(),valid=False,waypoint_id=-1,status='expired')
                e.apply(core,expired,None);self.assertEqual([core.v,core.w],[0.,0.]);self.assertIsNone(e.client)
            finally:e.close()
            for file in root.glob('*.jsonl'):
                for line in file.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
    def test_original_expiry_renderer_and_method_unmodified(self):
        from nomad_isaac.async_core import WaypointExecution
        self.assertIn('age < 1.0',inspect.getsource(WaypointExecution.control))
        self.assertIs(execution.RawExecution.__bases__[0],AccelExecution)
        source=(config.HERE/'simulator.py').read_text();self.assertIn("'nomad_phase17/simulator.py'",source);self.assertNotIn('nomad_phase26',source)
        self.assertNotIn('SPAlignment',inspect.getsource(execution));self.assertNotIn('RECOVER_ROTATE',inspect.getsource(execution))
    def test_no_closest_node_stop_hook_and_exact_metric_delegate(self):
        from nomad_isaac import async_runtime as engine
        import nomad_phase15b.execution as factory
        from . import metrics
        from nomad_phase18.metrics import audit as original_audit
        driver=engine.ExecutionThread
        with patch.object(execution,'frozen_install') as frozen,patch.object(factory,'make_execution'):
            execution.install_runtime_adapters();frozen.assert_called_once();self.assertIs(engine.ExecutionThread,driver)
            self.assertIs(factory.make_execution,execution.make_execution)
        self.assertNotIn('nomad_phase41',inspect.getsource(execution))
        self.assertIs(metrics.frozen_audit,original_audit)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'scenario.json').write_text(json.dumps(dict(phase18raw=True,phase15b_method='NOMAD_RAW',goal_tolerance_m=.3,nomad_goal_stop=False)))
            sentinel=dict(success=True,goal_time_s=12.,checkpoint_time_s=10.,collision=False,corridor=False,stuck=False,graph_calls=0,recovery_count=0)
            with patch.object(metrics,'frozen_audit',return_value=sentinel.copy()) as audit:
                result=metrics.audit(root);audit.assert_called_once_with(root)
            for key,value in sentinel.items():self.assertEqual(result[key],value)
    def test_frozen_bootstrap_code_and_constant_pair_difference(self):
        self.assertIs(statistics._paired.__code__,frozen_paired.__code__)
        records=[]
        for scene in config.SCENES:
            for i in config.INDICES:
                for method,value in [('NOMAD_RAW',float(i)),(config.BASELINES[1],float(i+2))]:records.append(dict(scene=scene,index=i,method=method,checkpoint_time_s=value,technical_validation='PASS'))
        r=statistics.paired(records,config.BASELINES[1]);self.assertEqual(r['n'],24);self.assertEqual(r['seed_clusters'],8);self.assertEqual(r['ci'],[-2.,-2.]);self.assertEqual(r['mean_difference'],-2.)
        expected=bind(frozen_paired,PROPOSED='NOMAD_RAW')(records,config.BASELINES[1],'checkpoint_time_s',alpha=config.protocol()['raw_comparison_alpha'])
        for key in expected:self.assertEqual(r[key],expected[key])
        records[0]['checkpoint_time_s']=None;self.assertEqual(statistics.paired(records,config.BASELINES[1])['n'],23)
    def test_resume_plan_no_retry_and_report24_template(self):
        jobs=campaign.plan_jobs(config.RUN_ROOT);self.assertEqual(len({j['output'] for j in jobs}),24)
        self.assertTrue(all('/attempt' not in j['output'] for j in jobs));self.assertEqual(campaign.campaign.__globals__['__package__'],'nomad_phase18raw')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();oldfile=root/'old.json';oldfile.write_text('[]')
            for j in jobs:
                r=dict(j,technical_validation='PASS',classification='SUCCESS',success=True,collision=False,corridor=False,stuck=False,goal_time_s=10.,checkpoint_time_s=5.)
                (root/'metrics'/('main_'+j['key']+'.json')).write_text(json.dumps(r))
            with patch.object(report,'BASELINE_FILE',oldfile):doc=report.generate(root,root/'out',root/'report.md')
            self.assertEqual(json.loads((root/'out/status.json').read_text())['completed'],24);self.assertIn('탐색적',doc.read_text());self.assertIn('arrival_p95_s',doc.read_text());self.assertIn('종료 판정은 Phase18과 동일(0.3m)',doc.read_text())
if __name__=='__main__':unittest.main()
