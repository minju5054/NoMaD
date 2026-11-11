"""Dry-run wiring only: no simulator, numerical solver or saved-input replay."""
import copy,inspect,json,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import config,launch,campaign,runtime,report,figures
from nomad_phase32o.test_exec_cert import field
from nomad_phase40p.launch import bind
from nomad_phase47c.config import runtime_config as frozen_config

class Tests(unittest.TestCase):
    def test_all18_frozen_configs_and_block_order(self):
        order=config.registered_order();self.assertEqual(len(order),18)
        for s in config.SCENES:
            for i in config.INDICES:
                self.assertEqual({x['method'] for x in order if x['scene']==s and x['index']==i},set(config.METHODS))
        for j in order:
            c=config.runtime_config(j['method'],j['index'],90,j['scene'])
            m='NOMAD_RAW' if j['method']=='NOMAD_RAW' else 'OURS-DETOUR+HMM'
            old=bind(frozen_config,INDICES=config.INDICES,protocol=config.protocol)(m,j['index'],90,'H1' if j['scene']=='H1-v2' else j['scene'])
            if j['scene']=='H1-v2':
                from nomad_h1v2.scene import configure
                old=configure(old);self.assertEqual(c['h1v2']['requested_target']['y_m'],1.10)
            allowed={'run_id'}|{k for k in c if k.startswith('phase57p')}
            self.assertEqual({k:v for k,v in c.items() if k not in allowed},{k:v for k,v in old.items() if k not in allowed})
            self.assertTrue(c['nomad_goal_stop']);self.assertEqual(bool(c.get('phase43p')),j['method']!='NOMAD_RAW');json.dumps(c,allow_nan=False)
    def test_real_launcher_args_all18_and_worker_route(self):
        class Boundary(Exception):pass
        for j in campaign.jobs():
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**k:self.fail('No process allowed')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            with patch.object(sys,'argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]),self.assertRaises(Boundary):fn()
            processes=launch.Processes(j['method']!='NOMAD_RAW')
            with patch('subprocess.Popen',return_value=SimpleNamespace()) as popen:
                processes.Popen(['python','-m','nomad_isaac.worker'])
                self.assertIn('nomad_isaac.worker' if j['method']=='NOMAD_RAW' else 'nomad_phase43p.worker',popen.call_args.args[0])
                processes.Popen(['isaac',str(config.ROOT/'research/nomad_phase26/simulator.py')])
                self.assertIn(str(config.HERE/'simulator.py'),popen.call_args.args[0])
    def test_no_depth_prefilter_all_eight_ranked_after_B(self):
        samples=np.array([np.c_[np.linspace(0,1+i*.1,8),np.zeros(8)] for i in range(8)])
        selected,detail=runtime.longest(samples,np.array([.7,0,0]),SimpleNamespace(query=lambda *_:self.fail('No depth query')))
        self.assertEqual(detail['selected_sample'],7);self.assertEqual(len(detail['candidates']),8)
        self.assertTrue(all(x['safe'] and x['clearance_m'] is None for x in detail['candidates']))
        self.assertAlmostEqual(detail['candidates'][0]['remaining_length_m'],.3)
        self.assertLess(runtime.MinExecution.__mro__.index(runtime.SelectionBridge),runtime.MinExecution.__mro__.index(runtime.BaseSelection))
    def test_fullspeed_only_reject_then_wait_no_keep(self):
        items=[dict(key=str(i),index=i) for i in range(8)];seen=[]
        result=runtime.full_speed(items[0],items,lambda item,cap:(seen.append((item['index'],cap)) or {'passed':False}))
        self.assertEqual(result['route'],'STOP_WAIT');self.assertEqual(seen,[(i,None) for i in range(8)])
        seen=[];result=runtime.full_speed(items[0],items,lambda item,cap:(seen.append(item['index']) or {'passed':item['index']==2}))
        self.assertEqual(result['item']['index'],2);self.assertEqual(seen,[0,1,2])
    def test_alignment_disabled_endpoint_latched_until_replace(self):
        p=runtime.MinProfile();p.replace_path([[0,0],[-1,0]],[0,0,0],0.)
        self.assertFalse(p.trigger_S);self.assertEqual(p.mode,'GO');self.assertEqual(p.alignment_count,0)
        p.replace_path([[0,0],[.1,0]],[0,0,0],.2)
        _,diag=p.control(np.array([.1,0,0]),.2);self.assertTrue(diag['completed'])
        for _ in range(3):
            command,diag=p.control(np.array([.3,0,0]),.1);self.assertEqual(command,(0.,0.));self.assertTrue(diag['endpoint_latched']);json.dumps(diag,allow_nan=False)
        p.replace_path([[.3,0],[1,0]],[.3,0,0],0.);self.assertFalse(p.endpoint_latched)
        _,diag=p.control(np.array([.3,0,0]),0.);self.assertFalse(diag['completed'])
    def test_EC_receives_same_latching_profile_no_rollout(self):
        e=object.__new__(runtime.MinExecution);captured=[]
        def check(*args,**kw):captured.append(args[-1]);return {'passed':True}
        with patch.object(runtime.Handoff,'ec_check',side_effect=check):
            e.ec_check([0,0,0],[.1,0],[[0,0],[-1,0]],None,0.,'NORMAL','INSTALL',None)
            self.assertIsInstance(captured[-1],runtime.MinProfile);self.assertFalse(captured[-1].trigger_S)
            p=runtime.MinProfile();p.replace_path([[0,0],[1,0]],[0,0,0],0);p.endpoint_latched=True
            e.ec_check([0,0,0],[.1,0],[[0,0],[1,0]],None,.5,'NORMAL','PERIODIC',None,p)
            self.assertIs(captured[-1],p);self.assertTrue(p.endpoint_latched)
    def test_recovery_disabled_and_graph_reused_exactly(self):
        recovery=runtime.NoRecovery(SimpleNamespace(state='NORMAL',streak=2))
        for _ in range(20):recovery.decision('STOP_WAIT');self.assertFalse(recovery.eligible(0.))
        self.assertEqual(recovery.state,'NORMAL')
        from nomad_night20261111.graph import drop_boundary,HoldClearanceGraph
        from nomad_phase17.graph import ClearanceGraph
        self.assertIs(HoldClearanceGraph.__bases__[0],ClearanceGraph)
        self.assertTrue(drop_boundary([0.,0.]));self.assertTrue(drop_boundary([.019,0.]));self.assertTrue(drop_boundary([.02,.17]))
        self.assertFalse(drop_boundary([.02,.16]));self.assertFalse(drop_boundary([.3,.4]))
        self.assertIn('from nomad_night20261111.worker import Client',inspect.getsource(runtime.Execution.__init__))
    def test_actual_apply_chain_graph_fallback_JSON_no_solve(self):
        for method in ('MIN','MIN+G18'):
            with tempfile.TemporaryDirectory() as tmp:
                f=field();f.observed=np.ones_like(f.occupied);f.metadata=dict(frame_id=1,sim_s=1.,publication_monotonic_ns=1)
                calls=[];worker=SimpleNamespace(solve=lambda j:(calls.append(j) or dict(accepted=False,reason='SOLVER_OR_CERTIFICATE_REJECT',solve_s=.01)),close=lambda:None)
                e=runtime.MinExecution(method,Path(tmp),worker);e.depth_maps=SimpleNamespace(snapshot=lambda:f);e.ec_check=lambda *a,**k:dict(passed=True,check_id=1)
                core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.)
                packet=dict(id=0,observation_pose=[0,0,0],overnight_metric_samples=np.array([np.c_[np.linspace(.1,1+i*.1,8),np.zeros(8)] for i in range(8)]),received_monotonic_ns=time.monotonic_ns())
                try:
                    e.apply(core,dict(simulation_time_s=1.,monotonic_ns=time.monotonic_ns(),valid=True),packet)
                    self.assertEqual(e.active_sample,7);self.assertIsInstance(e.sp,runtime.MinProfile);self.assertFalse(e.sp.trigger_S)
                    self.assertEqual(len(calls),int(method=='MIN+G18'));self.assertTrue(packet['phase16']['selection']['depth_filter_disabled'])
                    e.ec_check=lambda *a,**k:dict(passed=False,check_id=2)
                    packet['id']=1;e.apply(core,dict(simulation_time_s=2.,monotonic_ns=time.monotonic_ns(),valid=True),packet)
                    self.assertEqual(e.mode,'STOP_WAIT');self.assertIsNone(e.follower);self.assertEqual(e.recovery.state,'NORMAL')
                    for p in Path(tmp).glob('*.jsonl'):
                        for line in p.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
                finally:e.close()
    def test_raw_factory_not_overridden_expiry_unchanged(self):
        import nomad_phase15b.execution as factory
        import nomad_isaac.async_runtime as engine
        original=engine.WaypointExecution
        c=config.runtime_config('NOMAD_RAW',227,90,'SLW')
        with patch.object(runtime,'frozen_install') as frozen,patch.object(factory,'make_execution') as method:
            runtime.install(c);frozen.assert_called_once();self.assertIs(factory.make_execution,method);self.assertIs(engine.WaypointExecution,original)
        from nomad_isaac.async_core import WaypointExecution
        self.assertIn('age < 1.0',inspect.getsource(WaypointExecution.control))
    def test_report18_and_technical_placeholder_figures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir()
            for i,j in enumerate(config.registered_order()):
                r=dict(j,key=f"{j['scene']}_{j['index']}_{j['method']}",technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)
                (root/'metrics'/f'{i}.json').write_text(json.dumps(r))
            with patch.object(figures,'generate',return_value=[]) as plotted:
                doc=report.generate(root,root/'out',root/'report.md');self.assertEqual(len(plotted.call_args.args[0]),18)
            self.assertEqual(json.loads((root/'out/status.json').read_text())['completed'],18);self.assertIn('MIN+G18',doc.read_text())
            files=figures.generate([r],root/'figures');self.assertEqual(len(files),1);self.assertTrue(Path(files[0]).exists())
if __name__=='__main__':unittest.main()
