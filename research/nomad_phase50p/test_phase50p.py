import copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import config,launch,campaign,metrics,report
from .motion import placement,geometry_check,center_at,travel_duration,relative_sweep,MovingPersonMonitor,GhostLog,reference

class Tests(unittest.TestCase):
    def test_frozen_method_geometry_and_shared_draws(self):
        from nomad_phase47c.config import runtime_config as old
        p=config.verify();self.assertEqual(len(p['main_order']),12)
        for row in p['main_order']:
            scene,speed=config.condition(row['scene']);c=config.runtime_config(row['method'],row['index'],90,row['scene']);baseline=old(row['method'],row['index'],90,scene)
            self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase50p') and k not in ('dynamic_obstacle','run_id')},
                             {k:v for k,v in baseline.items() if k not in ('dynamic_obstacle','run_id')})
            spec=c['phase50p_moving'];self.assertTrue(geometry_check(c,spec)['passed']);self.assertEqual(spec['speed_m_s'],speed)
            self.assertGreaterEqual(spec['spawn_distance_m'],1.5);self.assertLessEqual(spec['spawn_distance_m'],2.5)
            self.assertEqual(spec['exit_policy'],'REMOVE_AT_OPPOSITE_EDGE')
            other=config.runtime_config(row['method'],row['index'],90,f'{scene}_V{100 if speed==.5 else 50:03d}')
            self.assertEqual({k:v for k,v in spec.items() if k!='speed_m_s'},{k:v for k,v in other['phase50p_moving'].items() if k!='speed_m_s'})
            np.testing.assert_allclose(np.linalg.norm(center_at(spec,.2)-center_at(spec,.1)),speed*.1,atol=1e-12)

    def test_moving_collision_between_endpoints_and_arc_bound(self):
        hit=relative_sweep([0,0,0],0,0,1,[0,-1],[0,1]);self.assertTrue(hit['geometric_overlap']);self.assertAlmostEqual(hit['upper_m'],-.29)
        self.assertFalse(relative_sweep([0,0,0],0,0,1,[1,-1],[1,1])['geometric_overlap'])
        from nomad_isaac.common import integrate_se2
        for v,w in ((.3,.4),(.3,-.4),(0,.4)):
            h=1/72;a=np.array([.29,-.01]);b=a+[0,1/72]
            r=relative_sweep([0,0,0],v,w,h,a,b)
            truth=min(np.linalg.norm(integrate_se2([0,0,0],v,w,t)[:2]-(a+(b-a)*t/h))-.29 for t in np.linspace(0,h,1001))
            self.assertLessEqual(r['lower_m'],truth+1e-12);self.assertLessEqual(truth,r['upper_m']+1e-7)
            json.dumps(r,allow_nan=False)

    def test_one_crossing_removal_exact_time_and_distance(self):
        for condition in config.SCENES:
            c=config.runtime_config(config.METHODS[0],221,90,condition);p=c['phase50p_moving'];ref=reference(c)
            pose=np.r_[ref.at(p['trigger_s_m']+1e-8),0.]
            with tempfile.TemporaryDirectory() as td:
                monitor=MovingPersonMonitor(c,Path(td))
                for tick in range(int((travel_duration(p)+5.1)*72)+1):monitor.observe_tick(tick,pose,pose,0.,0.,-1,False,0)
                result=monitor.finish(False);self.assertEqual(result['status'],'SPAWNED');self.assertTrue(monitor.retired)
                removal=result['removal'];self.assertAlmostEqual(removal['simulation_time_s'],travel_duration(p));self.assertEqual(removal['person_center_xy_m'],p['end_xy'])
                self.assertAlmostEqual(removal['center_distance_m'],np.linalg.norm(pose[:2]-p['end_xy']))
                self.assertEqual(removal['surface_wall_gap_m'],.05)
                entries=[json.loads(x) for x in (Path(td)/'dynamic/person_trajectory.jsonl').read_text().splitlines()]
                retired=[e for e in entries if e['simulation_time_s']>=removal['simulation_time_s']]
                self.assertTrue(retired and all(not e['active'] for e in retired));json.dumps(result,allow_nan=False)

    def test_ghost_telemetry_no_map_mutation_and_no_zero_imputation(self):
        p=dict(start_xy=[0.,0.],end_xy=[1.,0.]);occupied=np.zeros((40,50),bool)
        f=SimpleNamespace(h=.05,origin=np.array([-.5,-1.]),occupied=occupied,observed=np.ones_like(occupied),metadata=dict(frame_id=0,sim_s=0.))
        with tempfile.TemporaryDirectory() as td:
            g=GhostLog(Path(td),p);g.sample(f,0.,None,None)
            occupied[20,30]=True;before=occupied.copy();f.metadata=dict(frame_id=1,sim_s=2.1,publication_monotonic_ns=123)
            g.sample(f,2.2,0.,2.);g.sample(f,2.3,0.,2.);g.close();np.testing.assert_array_equal(before,f.occupied)
            events=[json.loads(x) for x in (Path(td)/'post_removal_ghost.jsonl').read_text().splitlines()]
            self.assertEqual(len(events),1);self.assertEqual(events[0]['endpoint_new_occupied_cells'],1)
            b=metrics.ghost_summary(events,dict(simulation_time_s=2.),2.5);self.assertIsNone(b[1]['endpoint_occupied_cells_median']);self.assertEqual(b[1]['observation_available_s'],0)

    def test_launch_validation_and_worker_routes_without_process(self):
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        class Boundary(Exception):pass
        jobs=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(jobs),12)
        for j in jobs:
            for out in j['outputs']:self.assertLess(validate_socket_path(socket_path_for_run(Path(out))),100)
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No subprocess')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            with patch.object(sys,'argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]),self.assertRaises(Boundary):fn()
        proc=launch.Processes()
        with patch('subprocess.Popen',return_value=object()) as popen:
            proc.Popen(['python','-m','nomad_isaac.worker']);self.assertEqual(popen.call_args.args[0][2],'nomad_phase43p.worker')
            proc.Popen(['python',str(config.ROOT/'research/nomad_phase26/simulator.py')]);self.assertEqual(popen.call_args.args[0][1],str(config.HERE/'simulator.py'))
        code='''
from nomad_phase50p import campaign as c
from nomad_phase50p.config import RUN_ROOT
def halt():
 assert len(c.frozen.base.jobs(RUN_ROOT))==12
 assert c.frozen.base.run_job.__globals__['subprocess'].__class__ is c.Routes
c.frozen.base.main=halt
c.main()
assert not RUN_ROOT.exists()
'''
        r=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr[-2000:])

    def test_runtime_uses_frozen_executor_and_passive_monitor(self):
        from . import runtime
        import nomad_isaac.async_runtime as a
        import nomad_isaac.sudden_obstacle as s
        class Original:
            def run(self):return 'same'
            def __init__(self,*args,**kwargs):self.dynamic=SimpleNamespace();self.stage2=SimpleNamespace(depth_maps=SimpleNamespace(snapshot=lambda:'map'))
        with patch.object(runtime,'frozen_install') as install,patch.object(a,'ExecutionThread',Original),patch.object(s,'SuddenObstacleMonitor'):
            runtime.install(dict(phase47c_method='OURS-DETOUR+HMM'))
            self.assertEqual(install.call_count,1);self.assertIs(a.ExecutionThread.run,Original.run)
            e=a.ExecutionThread();self.assertEqual(e.dynamic.depth_provider(),'map');self.assertIs(s.SuddenObstacleMonitor,MovingPersonMonitor)

    def test_time_metrics_collision_window_and_fake_report(self):
        data=[dict(simulation_time_s=t,v_m_s=v) for t,v in enumerate([0,0,.1,.3,.2])]
        self.assertEqual(metrics.time_metrics(data),dict(stopped_s=1.,slow_moving_s=2.,decelerating_s=1.))
        events=[dict(event='CHECK',simulation_time_s=t,passed=True) for t in (1,2,3,4,5)]
        self.assertEqual([e['simulation_time_s'] for e in metrics.collision_ec(events,4)],[2,3,4])
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,j in enumerate(config.registered_order()):
                row=dict(j,technical_validation='PASS',success=True,collision=False,person_collision=False,wrong_stop=False,person_spawned=True,
                    stopped_s=1.,slow_moving_s=2.,decelerating_s=.1,ec_slow_cap_s=0.,person_removal=None,ghost_by_second=[],ec_before_contact_2s=[])
                (root/'metrics'/f'{i}.json').write_text(json.dumps(row))
            doc=report.generate(root,root/'results',root/'report.md')
            self.assertTrue(all(not line or line.startswith('|') for line in doc.read_text().splitlines()))
            self.assertEqual(json.loads((root/'results/analysis.json').read_text())['completed'],12)

if __name__=='__main__':unittest.main()
