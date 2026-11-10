"""Wiring/semantic checks only: no recorded-input solves or simulation."""
import ast,copy,inspect,io,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import config,runtime,launch,campaign,report
from .ec_tail import certify_tail
from nomad_phase32o.test_exec_cert import field
from nomad_phase52ec.rollout import rollout
from nomad_phase32.policy import CappedNA
from nomad_phase38.ec_normal import RTCWithEC

class Tests(unittest.TestCase):
    def test_all40_configs_identical_base_except_registered_wiring(self):
        from nomad_phase47c.config import runtime_config as old
        self.assertEqual(len(config.registered_order()),40);self.assertEqual(config.verify()['main_order'],config.registered_order())
        for j in config.registered_order():
            s,c=config.split(j['scene']);new=config.runtime_config(j['method'],j['index'],90,j['scene']);base=old('OURS-DETOUR+HMM',j['index'],90,s)
            allowed={'run_id'}|{k for k in new if k.startswith('phase53p')}
            self.assertEqual({k:v for k,v in new.items() if k not in allowed},{k:v for k,v in base.items() if k not in allowed})
            self.assertEqual(new['phase38_method'],'OURS-DETOUR');self.assertTrue(new['nomad_goal_stop'])
            json.dumps(new,allow_nan=False)
        self.assertEqual(config.runtime_config('GRAPH-HO',95,90,'LC_D075')['seed_offset'],950000)

    def test_actual_launcher_all40_and_one_smoke_argument_validation(self):
        class Boundary(Exception):pass
        jobs=campaign.jobs();self.assertEqual(len(jobs),40)
        for j in [*jobs,campaign.smoke_job()]:
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**k:self.fail('No processes')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            args=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            if j['index']==95:args.append('--smoke')
            with patch.object(sys,'argv',args),self.assertRaises(Boundary):fn()
        self.assertEqual(len(campaign.smoke_job()['outputs']),1)

    def test_frozen_original_one_second_expiry_retained(self):
        from nomad_isaac.async_core import WaypointExecution
        self.assertIn('age < 1.0',inspect.getsource(WaypointExecution.control))
        self.assertNotIn('nomad_phase52p',inspect.getsource(runtime))
        self.assertNotIn('WaypointExecution',inspect.getsource(runtime.install))
        self.assertIs(runtime.Execution.use_fallback,RTCWithEC.use_fallback)

    def test_frozen_solver_class_and_parameters_not_reimplemented(self):
        from . import worker
        from nomad_phase17.graph import ClearanceGraph,D_PREF_M,SIGMA_CLEARANCE_M
        from nomad_phase15b.graph import DepthGraph
        from nomad_phase12.graph_gf import graph_protocol
        self.assertIs(ClearanceGraph.__bases__[0],DepthGraph)
        self.assertEqual((D_PREF_M,SIGMA_CLEARANCE_M),(.15,.05))
        self.assertIn('from nomad_phase17.graph import ClearanceGraph',inspect.getsource(worker.solve))
        p=graph_protocol();self.assertEqual(p['path_safety_target_m'],.025)
        with self.assertRaisesRegex(ValueError,'speed is zero'):
            ClearanceGraph(np.column_stack([np.linspace(.1,1,8),np.zeros(8)]),[0,0,0],[0,0],field())

    def test_tail_horizon_and_endpoint_stop_commands(self):
        for path,reason in [([[0,0],[3,0]],'HORIZON'),([[0,0],[.09,0]],'ENDPOINT')]:
            trace=rollout([0,0,0],[.3,.2],path)
            self.assertEqual(trace['stop_reason'],reason);self.assertEqual(trace['terminal_vw'],[0.,0.]);self.assertLessEqual(trace['brake_request_s'],2.)
            tail=trace['commands'][round(trace['brake_start_s']*72):]
            self.assertTrue((tail[:,1]==0).all());self.assertLessEqual(trace['duration_s'],2.7)
            record=certify_tail([0,0,0],[.3,.2],path,field());json.dumps(record,allow_nan=False)

    def test_tail_detects_braking_collision_and_continuation_phase(self):
        path=[[0,0],[.1,0]]
        # Endpoint already reached with nonzero speed; old EC checks position
        # only,tail checks the actual deceleration forward motion.
        r=certify_tail([.1,0,0],[.3,0],path,field([.27,0]));self.assertFalse(r['passed'])
        ctl=CappedNA();ctl.replace_path([[0,0],[3,0]],[0,0,0],.3)
        r=certify_tail([0,0,0],[.3,.1],[[0,0],[3,0]],field(),controller=ctl,start_tick=36)
        self.assertEqual(r['control_rounding_ticks'],4);self.assertTrue(r['continuation']);self.assertEqual(ctl.mode,'GO')

    def fake(self,path,tmp,accepted=True,tail=True):
        ex=object.__new__(runtime.Execution);ex.ho_method='GRAPH-HO';ex.ho_prior=None;ex.ho_n=0;ex.ho_dir=Path(tmp);ex.ho_log=io.StringIO()
        ex.ec_samples={4:dict(worlds=np.asarray([path]*8))};ex.active_sample=2;ex.follower=None
        f=SimpleNamespace(save=lambda p:p.write_bytes(b'fixture'));ex.depth_maps=SimpleNamespace(snapshot=lambda:f)
        poses=np.column_stack([path,np.zeros(8)])
        ex.ho_worker=SimpleNamespace(solve=lambda job:dict(accepted=accepted,reason='ACCEPTED' if accepted else 'SOLVER_OR_CERTIFICATE_REJECT',poses=poses,solve_s=.01))
        ex.actual_vw=lambda:[.2,0.];ex.ec_check=lambda *args,**kw:dict(passed=tail,check_id=8)
        return ex

    def test_graph_acceptance_and_fallback_identical_native_path_and_json(self):
        path=np.column_stack([np.linspace(.1,1,8),np.zeros(8)]);core=SimpleNamespace(pose=np.zeros(3));refresh=dict(simulation_time_s=4.)
        for accepted,tail,expected in [(True,True,'GRAPH_HO'),(True,False,'CUT'),(False,True,'CUT')]:
            with tempfile.TemporaryDirectory() as tmp:
                ex=self.fake(path,tmp,accepted,tail)
                with patch.object(RTCWithEC,'commit_path') as install:
                    ex.install_certified(path,core,refresh,4,'SAFE',None)
                    np.testing.assert_array_equal(install.call_args.args[0],path)
                records=[json.loads(line) for line in ex.ho_log.getvalue().splitlines()]
                self.assertEqual(records[-1]['path_type'],expected)
                for record in records:json.dumps(record,allow_nan=False)
                self.assertEqual(ex.ho_prior is not None,expected=='GRAPH_HO')
                job=json.loads(next(Path(tmp).glob('job_*.json')).read_text())
                self.assertEqual(job['boundary'],core.pose.tolist());self.assertEqual(job['previous_command'],[.2,0.])

    def test_common_ec_order_frozen_and_cut_no_solver(self):
        from nomad_phase32.runtime import Execution as old
        import textwrap
        expected=textwrap.dedent(inspect.getsource(old.ec_install)).replace('RAW_INSTALL(self,path,core,refresh,source_id,kind)','self.install_certified(path,core,refresh,source_id,kind,cap)')
        self.assertEqual(runtime._source,expected)
        path=np.column_stack([np.linspace(.1,1,8),np.zeros(8)])
        with tempfile.TemporaryDirectory() as tmp:
            ex=self.fake(path,tmp);ex.ho_method='CUT';ex.ho_worker=None
            with patch.object(RTCWithEC,'commit_path') as installer:ex.install_certified(path,SimpleNamespace(pose=np.zeros(3)),dict(simulation_time_s=1),4,'SAFE',None)
            self.assertEqual(ex.ho_n,0);installer.assert_called_once()

    def test_delay_ast_no_runtime_engine(self):
        from nomad_phase51p.runtime import driver_tree
        from nomad_isaac import async_runtime as original
        class Boundary(Exception):pass
        tree=driver_tree(inspect.getsource(original.run_async),False)
        ns=dict(original.__dict__,_phase24_full_frames=False,ExecutionThread=lambda *a,**k:(_ for _ in ()).throw(Boundary()))
        exec(compile(tree,original.__file__,'exec'),ns)
        with tempfile.TemporaryDirectory() as td:
            c=config.runtime_config('CUT',221,90,'LC_D150')
            with self.assertRaises(Boundary):ns['run_async'](c,Path(td),None,None,None,None,None,{},uniform_delivery_delay_s=1.5,pure_pursuit=True)
            self.assertEqual(json.loads((Path(td)/'delivery_delay_protocol.json').read_text())['configured_additional_s'],1.5)

    def test_factory_and_hmm_keep_original_control_class(self):
        import nomad_isaac.async_core as core
        import nomad_phase15b.execution as factory
        import nomad_phase8.execution as overnight
        identity=core.WaypointExecution.control
        with patch.object(runtime,'frozen_install') as frozen,patch.object(factory,'make_execution'),patch.object(overnight,'OvernightExecution'):
            runtime.install(dict(phase53p=True));frozen.assert_called_once()
            self.assertIs(core.WaypointExecution.control,identity)

    def test_synthetic_report_all40_and_reused_baseline_columns(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,j in enumerate(config.registered_order()):
                r=dict(j,technical_validation='PASS',base_scene=config.split(j['scene'])[0],condition=config.split(j['scene'])[1],success=True,
                    collision=False,wrong_stop=False,timeout_without_declaration=False,goal_time_s=10.,stopped_s=2.,align_rotate_s=1.,command_state_seconds={'ALIGN_ROTATE':1.},graph_adoption_rate=.8)
                (root/'metrics'/f'{i}.json').write_text(json.dumps(r))
            doc=report.generate(root,root/'out',root/'report.md')
            self.assertEqual(json.loads((root/'out/status.json').read_text())['completed'],40)
            self.assertIn('Phase47_D075',doc.read_text());self.assertIn('Phase52_D150',doc.read_text());self.assertIn('ALIGN_ROTATE',doc.read_text())
if __name__=='__main__':unittest.main()
