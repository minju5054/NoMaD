"""Plumbing and algebra only: no simulator or numerical optimizer runs."""
import io,json,sys,tempfile,unittest,copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import config,launch,campaign,runtime,report,worker
from .graph import Graph
from nomad_ugraph.graph import Graph as FrozenGraph
from nomad_phase32o.test_exec_cert import field
from nomad_phase53p.config import runtime_config as cut_config
from nomad_night20261111.runtime import HoldExecution

class Tests(unittest.TestCase):
    def test_24_configs_exact_cut_plus_wiring(self):
        self.assertEqual(len(config.registered_order()),24)
        for j in config.registered_order():
            s,d=config.split(j['scene']);c=config.runtime_config(j['method'],j['index'],90,j['scene'])
            old=cut_config('CUT',j['index'],90,('H1' if s=='H1-v2' else s)+'_'+d)
            if s=='H1-v2':
                from nomad_h1v2.scene import configure
                old=configure(old);self.assertEqual(c['h1v2']['requested_target']['y_m'],1.10)
            allowed={'run_id'}|{k for k in c if k.startswith('phase55p')}
            self.assertEqual({k:v for k,v in c.items() if k not in allowed},{k:v for k,v in old.items() if k not in allowed})
            self.assertTrue(c['nomad_goal_stop']);self.assertEqual(c['phase38_method'],'OURS-DETOUR');json.dumps(c,allow_nan=False)
    def test_actual_launcher_24_without_process_start(self):
        class Boundary(Exception):pass
        for j in campaign.jobs():
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('Forbidden process')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            with patch.object(sys,'argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]),self.assertRaises(Boundary):fn()
        self.assertEqual(len(campaign.jobs()),24)
    def test_real_subprocess_route_and_delay_without_launch(self):
        for j in config.registered_order():
            proc=launch.Processes()
            with patch('subprocess.Popen',return_value=SimpleNamespace()) as popen:
                proc.Popen(['/home/gpuadmin/isaacsim/python.sh',str(config.ROOT/'research/nomad_phase26/simulator.py'),'--level',j['scene'],'--delay','.75'])
                args=popen.call_args.args[0]
                self.assertIn(str(config.HERE/'simulator.py'),args)
                self.assertEqual(float(args[args.index('--delay')+1]),1.5 if 'D150' in j['scene'] else .75)
                proc.Popen(['python','-m','nomad_isaac.worker'])
                self.assertIn('nomad_phase43p.worker',popen.call_args.args[0])
    def test_only_forward_speed_inequality_changes(self):
        samples=np.array([np.c_[np.linspace(.1,.8,8),np.zeros(8)] for _ in range(8)])
        a=FrozenGraph([0,0,0,.1],0,samples,field());b=Graph([0,0,0,.1],0,samples,field())
        z=np.zeros(50);r=a.values(z);s=b.values(z)
        self.assertEqual(r['objective'],s['objective']);np.testing.assert_array_equal(r['gradient'],s['gradient'])
        expected=r['inequalities'].copy();expected[26:52]-=.3
        np.testing.assert_array_equal(s['inequalities'],expected);np.testing.assert_array_equal(s['jacobian'],r['jacobian'])
        self.assertIs(Graph.objective,FrozenGraph.objective);self.assertIs(Graph.check,FrozenGraph.check)
        # Repeated cache query must not subtract the bound again.
        np.testing.assert_array_equal(b.values(z)['inequalities'],expected)
    def test_worker_all11_initializations_transport_no_solver(self):
        class Pool:
            def map(self,fn,items):
                self.items=list(items);return [dict(start_index=i,hard_feasible=False) for _,i in self.items]
        p=Pool();r=worker.solve(dict(snapshot_file='dry-only'),p)
        self.assertEqual([i for _,i in p.items],list(range(11)));self.assertEqual(len(r['results']),11);json.dumps(r,allow_nan=False)
    def fake(self,tmp,accepted=True):
        e=object.__new__(runtime.Execution);e.u_count=0;e.u_prior=None;e.u_dir=Path(tmp);e.u_file=io.StringIO();e.u_cycle=None
        e.ec_cap=None;e.ec_generation=0;e.ec_pending=None;e.u_next=None;e.u_due=None
        e.active_sample=0;e.active_id=4;e.ec_samples={4:dict(worlds=np.zeros((8,8,2)))}
        f=SimpleNamespace(metadata={'frame_id':3},save=lambda p:p.write_bytes(b'dryrun'))
        e.depth_maps=SimpleNamespace(snapshot=lambda:f);e.actual_vw=lambda:[.1,.02]
        states=np.c_[np.linspace(0,.3,26),np.zeros(26),np.zeros(26),np.zeros(26)].tolist()
        results=[dict(start_index=i,objective=float(i),hard_feasible=accepted,active_candidate=i%8,states=states,maximum_violation=0.) for i in range(11)]
        e.u_worker=SimpleNamespace(solve=lambda job:dict(results=copy.deepcopy(results),solve_s=.1,rpc_s=.12))
        e.ec_check=lambda *a,**k:dict(passed=True,check_id=12)
        e.recovery=SimpleNamespace(state='NORMAL',decision=lambda *_:None);e.ec_log=lambda *a,**k:None;e.set_hold=lambda *a,**k:None
        e.install_certified=lambda *a,**k:setattr(e,'sp',SimpleNamespace(speed_cap=None))
        return e
    def test_actual_pose_world8_and_minimum_cost_ec_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            e=self.fake(tmp);core=SimpleNamespace(pose=np.array([1.,2.,.3]));refresh=dict(simulation_time_s=2.)
            packet=dict(id=8,observation_pose=[10.,20.,0.],overnight_metric_samples=np.zeros((8,8,2)))
            calls=[]
            def check(*args,**kw):calls.append(1);return dict(passed=len(calls)==2,check_id=len(calls))
            e.ec_check=check;r=e.prepare_solution(core,refresh,packet,140)
            self.assertEqual(r['job']['initial'],[1.,2.,.3,.1]);self.assertEqual(r['job']['omega'],.02)
            np.testing.assert_array_equal(np.asarray(r['job']['samples_world'])[0,0],[10,20])
            self.assertEqual(r['chosen']['start_index'],1);self.assertEqual(len(r['checks']),2)
            json.dumps(json.loads(next(Path(tmp).glob('job*.json')).read_text()),allow_nan=False)
    def test_adopt_once_prior_only_on_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            e=self.fake(tmp);core=SimpleNamespace(pose=np.zeros(3));refresh=dict(simulation_time_s=1.)
            e.u_cycle=e.prepare_solution(core,refresh,None,68);self.assertIsNone(e.u_prior)
            self.assertTrue(e.adopt(core,refresh));self.assertEqual(e.u_prior['time_s'],1.)
            self.assertTrue(e.adopt(core,refresh));self.assertEqual(e.ec_generation,1)
            records=[json.loads(x) for x in e.u_file.getvalue().splitlines()];self.assertEqual(len(records),1)
            json.dumps(records,allow_nan=False);self.assertFalse(records[0]['graph_velocity_executed'])
    def test_no_solution_or_ec_reject_preserves_cut_fallback(self):
        for accepted in (True,False):
            with tempfile.TemporaryDirectory() as tmp:
                e=self.fake(tmp,accepted);e.ec_check=lambda *a,**k:dict(passed=False,check_id=2)
                core=SimpleNamespace(pose=np.zeros(3));refresh=dict(simulation_time_s=1.)
                e.u_cycle=e.prepare_solution(core,refresh,None,68)
                self.assertIsNone(e.u_cycle['chosen'])
                with patch.object(HoldExecution,'ec_install',return_value={'installed':True,'kind':'CUT'}) as old:
                    result=e.ec_install([[0,0],[1,0]],core,refresh,4,'SAFE');old.assert_called_once();self.assertEqual(result['kind'],'CUT')
                self.assertIsNone(e.u_prior)
    def test_periodic_clock_36ticks(self):
        with tempfile.TemporaryDirectory() as tmp:
            e=self.fake(tmp);e.u_next=36;e.plant=SimpleNamespace(last_tick=35)
            with patch.object(HoldExecution,'integrate_record'):
                e.integrate_record(None,None);self.assertIsNone(e.u_due)
                e.plant.last_tick=36;e.integrate_record(None,None);self.assertEqual(e.u_due,36);self.assertEqual(e.u_next,72)
    def test_stop_feasible_not_replaced_by_cut(self):
        with tempfile.TemporaryDirectory() as tmp:
            e=self.fake(tmp);core=SimpleNamespace(pose=np.zeros(3));refresh=dict(simulation_time_s=1.)
            e.u_cycle=e.prepare_solution(core,refresh,None,68);e.u_cycle['chosen']['stationary']=True
            with patch.object(runtime.OriginalEC,'ec_stop') as stop:
                self.assertTrue(e.adopt(core,refresh));stop.assert_called_once()
            self.assertTrue(json.loads(e.u_file.getvalue())['stationary_xy'])
    def test_hold_factory_and_h1v2_wiring(self):
        import nomad_isaac.async_runtime as engine
        import nomad_phase15b.execution as factory
        import nomad_phase8.execution as overnight
        from nomad_h1v2 import scene
        original=engine.WaypointExecution
        with patch.object(runtime,'frozen_install') as frozen,patch.object(factory,'make_execution'),patch.object(overnight,'OvernightExecution'),patch.object(scene,'install_environment') as h1:
            try:
                runtime.install(dict(h1v2=True));self.assertIs(engine.WaypointExecution,runtime.HoldCore);h1.assert_called_once();frozen.assert_called_once()
            finally:engine.WaypointExecution=original
    def test_real_execution_method_chain_arrival_periodic_and_json(self):
        # Exercise the actual frozen apply chain; only expensive solver and
        # EC predicate are fixtures. No pose integration or process starts.
        import time
        with tempfile.TemporaryDirectory() as tmp:
            f=field();f.metadata={'frame_id':0,'sim_s':1.,'publication_monotonic_ns':1};f.observed=np.ones_like(f.occupied)
            states=np.c_[np.linspace(0,.6,26),np.zeros((26,3))].tolist()
            client=SimpleNamespace(solve=lambda job:dict(results=[dict(start_index=i,objective=i,hard_feasible=True,states=states,active_candidate=0) for i in range(11)],solve_s=.01,rpc_s=.02),close=lambda:None)
            e=runtime.Execution(Path(tmp),client);e.depth_maps=SimpleNamespace(snapshot=lambda:f)
            e.ec_check=lambda *a,**k:dict(check_id=0,passed=True)
            core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.)
            packet=dict(id=0,observation_pose=[0,0,0],overnight_metric_samples=np.array([np.c_[np.linspace(.1,1,8),np.zeros(8)]]*8),received_monotonic_ns=time.monotonic_ns())
            try:
                e.apply(core,dict(simulation_time_s=1.,monotonic_ns=time.monotonic_ns(),valid=True),packet)
                self.assertEqual(e.path_kind,'UGRAPH');self.assertIsNotNone(e.u_prior)
                e.u_due=108
                e.apply(core,dict(simulation_time_s=112/72,monotonic_ns=time.monotonic_ns(),valid=True),None)
                self.assertEqual(e.u_count,2);self.assertEqual(e.path_kind,'UGRAPH')
                for file in Path(tmp).glob('*.jsonl'):
                    for line in file.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
                record=[json.loads(line) for line in (Path(tmp)/'ugraph.jsonl').read_text().splitlines() if json.loads(line)['event']=='SOLVE']
                self.assertEqual(record[-1]['periodic_delay_ticks'],4);self.assertTrue(all(x['applied'] for x in record))
                ho=[json.loads(x) for x in (Path(tmp)/'graph_ho.jsonl').read_text().splitlines()]
                self.assertTrue(all(x['path_type']=='UGRAPH' for x in ho))
            finally:e.close()
    def test_complete_report24_historical_missing_is_dash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir()
            for i,j in enumerate(config.registered_order()):
                r=dict(j,technical_validation='PASS',success=True,collision=False,classification='SUCCESS',goal_time_s=20.,box_passage=True,command_state_seconds={'ALIGN_ROTATE':1.})
                (root/'metrics'/f'{i}.json').write_text(json.dumps(r))
            doc=report.generate(root,root/'out',root/'report.md')
            self.assertEqual(json.loads((root/'out/status.json').read_text())['completed'],24)
            self.assertIn('Phase53_CUT',doc.read_text());self.assertIn('Phase52_CUT-HOLD',doc.read_text());self.assertIn('—',doc.read_text());self.assertIn('H1-v2',doc.read_text())
if __name__=='__main__':unittest.main()
