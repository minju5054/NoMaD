"""Synthetic algebra and runtime/launcher plumbing; no optimization or simulation."""
import inspect,json,pickle,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase32o.test_exec_cert import field
from nomad_phase55p.graph import Graph as BaseGraph,solve_start as original_solve
from nomad_phase58p.runtime import LatchedProfile
from . import config,campaign,launch,graph,worker,runtime,report,figures

class Tests(unittest.TestCase):
    def samples(self):return np.array([np.c_[np.linspace(.1,1,8),np.full(8,i*.03)] for i in range(8)])
    def test_only_goal_cost_and_analytic_gradient_added(self):
        f=field();args=([0,0,.1,.12],.02,self.samples(),f)
        a=BaseGraph(*args);b=graph.Graph(*args,goal_xy=[1.2,.2]);z=a.initial_controls(0)
        old=a.values(z);new=b.values(z);delta=new['states'][-1,:2]-[1.2,.2]
        self.assertAlmostEqual(new['costs']['goal'],float(delta@delta/.3**2))
        for key in old['costs']:self.assertEqual(old['costs'][key],new['costs'][key])
        np.testing.assert_array_equal(old['inequalities'],new['inequalities']);np.testing.assert_array_equal(old['jacobian'],new['jacobian'])
        np.testing.assert_array_equal(old['terminal_jacobian'],new['terminal_jacobian']);self.assertEqual(old['terminal'],new['terminal'])
        expected=2*delta@new['sensitivity'][-1,:2]/.3**2
        np.testing.assert_allclose(new['gradient']-old['gradient'],expected,atol=1e-12)
        eps=1e-6
        for i in range(50):
            step=np.zeros(50);step[i]=eps
            numeric=(b.values(z+step)['costs']['goal']-b.values(z-step)['costs']['goal'])/(2*eps)
            self.assertAlmostEqual(numeric,expected[i],delta=1e-5)
        b.values(z);cost=b.objective(z)[0];self.assertEqual(cost,b.objective(z)[0])
        self.assertIs(graph.solve_start,original_solve)
        for i in range(11):np.testing.assert_array_equal(a.initial_controls(i),b.initial_controls(i))
        np.testing.assert_array_equal(a.bounds.lb,b.bounds.lb);np.testing.assert_array_equal(a.bounds.ub,b.bounds.ub)
    def packet(self,identifier=4,node=1):
        return dict(id=identifier,observation_pose=[.1,0,0],observation_sim_s=.5,received_monotonic_ns=time.monotonic_ns(),
            overnight_metric_samples=self.samples(),topomap=dict(closest_node=node,goal_node=5,oracle=dict(analysis_only=True,HMM_used=False)))
    def test_goal_node_held_between_chunks_and_clamped(self):
        e=object.__new__(runtime.Execution);e.node_xy=np.c_[np.arange(6),np.zeros(6)];e.target=None
        e.update_goal(self.packet());core=SimpleNamespace(pose=np.array([4.,2.,0.]))
        ctx=e.goal_context(core,4);self.assertEqual(ctx['target_node'],3);self.assertEqual(ctx['goal_xy'],[3.,0.]);self.assertAlmostEqual(ctx['goal_distance_at_solve_m'],np.sqrt(5))
        core.pose=np.array([5.,0.,0.]);self.assertEqual(e.goal_context(core,4)['target_node'],3)
        e.update_goal(self.packet(5,5));self.assertEqual(e.goal_context(core,5)['target_node'],5)
    def fake_worker(self,accepted):
        states=np.c_[np.linspace(0,.5,26),np.zeros((26,3))].tolist();captured=[]
        def solve(job):
            captured.append(job)
            return dict(results=[dict(start_index=i,objective=float(i),hard_feasible=accepted,active_candidate=0,states=states,costs={'goal':1.}) for i in range(11)],solve_s=.01,rpc_s=.02)
        return SimpleNamespace(solve=solve,close=lambda:None),captured
    def test_real_cut_base_U_acceptance_periodic_target_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=field();f.observed=np.ones_like(f.occupied);f.metadata=dict(frame_id=1,sim_s=1.,publication_monotonic_ns=1)
            w,captured=self.fake_worker(True);e=runtime.Execution(Path(tmp),np.c_[np.arange(6),np.zeros((6,2))],w)
            e.depth_maps=SimpleNamespace(snapshot=lambda:f);e.ec_check=lambda *a,**kw:dict(passed=True,check_id=1)
            core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.);packet=self.packet()
            try:
                e.apply(core,dict(simulation_time_s=1.,monotonic_ns=time.monotonic_ns(),valid=True),packet)
                self.assertIsInstance(e.sp,LatchedProfile);self.assertEqual(e.path_kind,'UGRAPH');self.assertEqual(captured[-1]['goal_xy'],[3.,0.]);self.assertEqual(e.u_count,1)
                e.u_due=108;core.pose=np.array([.2,0,0.])
                e.apply(core,dict(simulation_time_s=112/72,monotonic_ns=time.monotonic_ns(),valid=True),None)
                self.assertEqual(captured[-1]['target_node'],3);self.assertAlmostEqual(captured[-1]['goal_distance_at_solve_m'],2.8)
                self.assertEqual(captured[-1]['initial'][:3],core.pose.tolist());self.assertIsNotNone(captured[-1]['previous'])
                for p in Path(tmp).glob('*.jsonl'):
                    for line in p.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
                events=[json.loads(line) for line in (Path(tmp)/'ugraph.jsonl').read_text().splitlines()]
                self.assertTrue(all(e['target_node']==3 for e in events));self.assertFalse((Path(tmp)/'hold.jsonl').exists())
            finally:e.close()
    def test_U_failure_uses_original_cut_not_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=field();f.observed=np.ones_like(f.occupied);f.metadata=dict(frame_id=1,sim_s=1.,publication_monotonic_ns=1)
            w,_=self.fake_worker(False);e=runtime.Execution(Path(tmp),np.c_[np.arange(6),np.zeros((6,2))],w)
            e.depth_maps=SimpleNamespace(snapshot=lambda:f);e.ec_check=lambda *a,**kw:dict(passed=True,check_id=1)
            core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.)
            try:
                e.apply(core,dict(simulation_time_s=1.,monotonic_ns=time.monotonic_ns(),valid=True),self.packet())
                self.assertEqual(e.path_kind,'SAFE');self.assertIsNone(e.u_prior);self.assertIsInstance(e.sp,LatchedProfile)
                with patch.object(runtime.CUTBase,'use_fallback',return_value={'reason':'frozen CUT'}) as fallback:
                    self.assertEqual(e.use_fallback(core,dict(simulation_time_s=2.))['reason'],'frozen CUT');fallback.assert_called_once()
            finally:e.close()
    def test_worker_goal_payload_and_all11_starts_without_optimizer(self):
        self.assertIs(worker.solve.__globals__['start_one'],worker.start_one);pickle.dumps(worker.start_one)
        class Pool:
            def map(self,fn,payloads):
                self.payloads=list(payloads);return [dict(start_index=i) for _,i in self.payloads]
        pool=Pool();r=worker.solve({'goal_xy':[1,2]},pool);self.assertEqual([i for _,i in pool.payloads],list(range(11)));json.dumps(r,allow_nan=False)
        with tempfile.TemporaryDirectory() as tmp:
            f=field();f.observed=np.ones_like(f.occupied);f.metadata={'frame_id':1};file=Path(tmp)/'field.npz';f.save(file)
            job=dict(initial=[0,0,0,0],omega=0.,samples_world=self.samples().tolist(),previous=None,simulation_time_s=0.,snapshot_file=str(file),goal_xy=[1.,2.])
            def no_solve(g,i):self.assertIsInstance(g,graph.Graph);np.testing.assert_array_equal(g.goal_xy,[1.,2.]);return dict(start_index=i)
            with patch.object(graph,'solve_start',side_effect=no_solve):self.assertEqual(worker.start_one((job,3))['start_index'],3)
    def test_six_configs_and_real_launcher_oracle_worker_route(self):
        from nomad_phase61p import config as base
        class Boundary(Exception):pass
        self.assertEqual(len(campaign.jobs()),6)
        for j in campaign.jobs():
            c=config.runtime_config(j['method'],j['index'],90,j['scene']);expected=base.runtime_config('CUT',j['index'],90,j['scene'])
            expected['run_id']=c['run_id'];self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase62p')},expected)
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**k:self.fail('No process')));fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            with patch.object(sys,'argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]),self.assertRaises(Boundary):fn()
            with patch('subprocess.Popen',return_value=SimpleNamespace()) as popen:
                proc=launch.Processes();proc.Popen(['python','-m','nomad_isaac.worker']);self.assertIn('nomad_phase61p.worker',popen.call_args.args[0])
                proc.Popen(['isaac',str(config.ROOT/'research/nomad_phase26/simulator.py')]);self.assertIn(str(config.HERE/'simulator.py'),popen.call_args.args[0])
    def test_no_hold_core_and_frozen_expiry_installer(self):
        import nomad_isaac.async_runtime as engine
        import nomad_phase15b.execution as factory
        import nomad_phase8.execution as overnight
        original=engine.WaypointExecution
        with patch.object(runtime,'frozen_install') as frozen,patch.object(factory,'make_execution'),patch.object(overnight,'OvernightExecution'):
            runtime.install({'phase62p':True});self.assertIs(engine.WaypointExecution,original);frozen.assert_called_once()
        from nomad_isaac.async_core import WaypointExecution
        self.assertIn('age < 1.0',inspect.getsource(WaypointExecution.control))
        from nomad_night20261111.runtime import HoldExecution
        self.assertFalse(issubclass(runtime.Execution,HoldExecution))
    def test_report_six_and_three_baseline_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();baseline=root/'baseline.json'
            baseline.write_text(json.dumps([dict(scene='SLW',index=229,method=m,technical_validation='PASS',success=True,collision=False,wrong_stop=False,timeout_without_declaration=False,box_passage=True,goal_time_s=20.,stopped_s=2.) for m in ('CUT','CONS','CONS+G18')]))
            for i,j in enumerate(config.registered_order()):(root/'metrics'/f'{i}.json').write_text(json.dumps(dict(j,key=str(i),technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)))
            with patch.object(report,'BASELINE',baseline),patch.object(figures,'generate',return_value=[]) as fig:doc=report.generate(root,root/'out',root/'report.md')
            self.assertEqual(len(fig.call_args.args[0]),6)
            for name in ('P61_CUT_success','P61_CONS_success','P61_CONS+G18_success','u_goal_distance_at_solve_median_m'):self.assertIn(name,doc.read_text())
            self.assertEqual(json.loads((root/'out/status.json').read_text())['completed'],6)
if __name__=='__main__':unittest.main()
