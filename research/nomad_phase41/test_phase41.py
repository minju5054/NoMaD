import io,json,os,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import config,stop,metrics,report,campaign,launch


class Tests(unittest.TestCase):
    def engine(self,out,enabled,closest):
        o=object.__new__(stop.ExecutionThread)
        o.config=dict(integration_hz=72,timeout_sim_s=3/72,timeout_navigation_wall_s=90.,goal_pose=[.2,0,0],goal_tolerance_m=.3)
        o.out=out;o.nomad_goal_stop=enabled;o.declared_arrival=None
        o.calls=[];o.core=SimpleNamespace(pose=np.zeros(3),v=.1,w=.2,applied_id=-1,command_valid=True)
        def integrate():o.calls.append('integrate')
        def control(*a):o.calls.append('control');return None,None
        o.core.integrate=integrate;o.core.control=control;o.core.receive=lambda *a:o.calls.append('receive')
        o.monitor=SimpleNamespace(stop_reason=None,plan=lambda *a:None,observe_interval=lambda *a:None)
        o.stage2=o.phase2=o.chunk_executor=o.safety=o.graph=o.dynamic=None
        o.state={};o.lock=threading.Lock();o.done=threading.Event();o.started=threading.Event();o.cancel=threading.Event()
        o.epoch_ns=0;o.reason='simulation_timeout';o.error=None;o.goal_entry=False;o.minimum_distance=99.;o.distance=0.
        o.received=[];o.events=[]
        data=np.zeros((8,8,2));meta=dict(id=0,topomap=dict(closest_node=closest,goal_node=4),received_monotonic_ns=1)
        response=(meta,dict(metric=data,normalized_diffusion=data,selected_waypoint=data[0,2]))
        queue=[response]
        o.client=SimpleNamespace(poll=lambda:queue.pop(0) if queue else None)
        return o,response

    def test_stop_before_control_at_first_received_tick_and_optional_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            for enabled,closest,reason in ((True,4,'declared_arrival'),(True,3,'simulation_timeout'),(False,4,'goal_entry')):
                out=Path(td)/f'{enabled}_{closest}';out.mkdir();o,_=self.engine(out,enabled,closest)
                with patch.object(stop.frozen.time,'monotonic_ns',return_value=1_000_000_000):o.run()
                try:
                    self.assertIsNone(o.error);self.assertEqual(o.reason,reason);self.assertTrue(o.done.is_set())
                    if reason=='declared_arrival':
                        self.assertEqual(o.calls,[]);self.assertEqual([o.core.v,o.core.w],[0.,0.]);self.assertFalse(o.goal_entry)
                        row=json.loads((out/'controller.jsonl').read_text())
                        self.assertEqual(row['applied_command_source'],'DECLARED_ARRIVAL')
                        self.assertEqual(row['applied_v_m_s'],0.);self.assertEqual(row['applied_w_rad_s'],0.)
                        self.assertEqual(o.state['actual_vw'],[0.,0.]);self.assertEqual(o.declared_arrival['tick'],0)
                    elif enabled:self.assertIn('control',o.calls)
                    for file in out.glob('*.jsonl'):
                        for line in file.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
                finally:o.rf.close()
            out=Path(td)/'terminal';out.mkdir();o,response=self.engine(out,True,4);o.rf=io.StringIO()
            o.accept(response,1.,terminal=True);self.assertIsNone(o.declared_arrival)

    def test_exact_predicate_and_preregistered_metrics(self):
        self.assertFalse(stop.goal_node_reached({}));self.assertFalse(stop.goal_node_reached({'topomap':{'closest_node':3,'goal_node':4}}))
        self.assertTrue(stop.goal_node_reached({'topomap':{'closest_node':4,'goal_node':4}}))
        for distance,main,small,wide,wrong in ((.3,True,True,True,False),(.5,True,False,True,False),(1.,False,False,True,True),(1.1,False,False,False,True)):
            r=metrics.outcomes(True,distance,False,'declared_arrival')
            self.assertEqual((r['success'],r['success_0p3'],r['success_1p0'],r['wrong_stop']),(main,small,wide,wrong))
            self.assertFalse(metrics.outcomes(True,distance,True,'declared_arrival')['success'])
        self.assertTrue(metrics.outcomes(False,.1,False,'simulation_timeout')['timeout_without_declaration'])
        self.assertFalse(metrics.outcomes(False,.1,False,'collision')['timeout_without_declaration'])

    def test_fifteen_frozen_configs_and_launcher_arguments_no_simulator(self):
        from nomad_phase38.config import runtime_config as parent
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        class Boundary(Exception):pass
        plan=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(plan),15)
        for j in plan:
            c=config.runtime_config(j['method'],j['index'],90,j['scene'])
            self.assertEqual({k:v for k,v in c.items() if k not in ('phase41','nomad_goal_stop')},parent(j['method'],j['index'],90,j['scene']))
            for output in j['outputs']:self.assertLess(validate_socket_path(socket_path_for_run(Path(output))),100)
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No simulator')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            argv=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            with patch.object(sys,'argv',argv),self.assertRaises(Boundary):fn()
        code='''
from nomad_phase41 import campaign as c
from nomad_phase41.config import RUN_ROOT
def halt():
 assert len(c.frozen.base.jobs(RUN_ROOT))==15
 assert c.frozen.base.protocol()['smoke']['enabled'] is False
 assert c.frozen.base.run_job.__globals__['subprocess'].__class__ is c.Routes
 print('FIFTEEN_NO_SMOKE_NO_EXECUTION')
c.frozen.base.main=halt
c.main()
assert not RUN_ROOT.exists()
'''
        r=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr[-1500:]);self.assertIn('FIFTEEN_NO_SMOKE_NO_EXECUTION',r.stdout)

    def test_tables_and_same_fifteen_historical_pairs(self):
        prior=json.loads((config.OUT/'preparation/baselines.json').read_text());self.assertEqual(len(prior),15)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,j in enumerate(config.protocol()['main_order']):
                row=dict(j,technical_validation='PASS',termination='declared_arrival',collision=False,
                    stop_distance_m=.4,final_goal_distance_m=.4,**metrics.outcomes(True,.4,False,'declared_arrival'))
                (root/'metrics'/f'{i}.json').write_text(json.dumps(row))
            doc=report.generate(root,root/'results',root/'report.md',prior)
            self.assertTrue(all(not line or line.startswith('|') for line in doc.read_text().splitlines()))
            result=json.loads((root/'results/analysis.json').read_text());self.assertEqual(result['paired_valid'],15)
            self.assertTrue((root/'results/paired.csv').exists())


if __name__=='__main__':unittest.main()
