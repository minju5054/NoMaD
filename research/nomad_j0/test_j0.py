import copy
import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase0.chunk_execution import describe_chunk
from nomad_phase4c.execution import AccelExecution
from nomad_phase4c.plant import control_command
from nomad_phase12.gf_worker import numeric_job
from nomad_phase15b.depth import evaluate_samples
from nomad_phase17.graph import ClearanceGraph
from nomad_phase17.worker import solve_job
from nomad_isaac.common import integrate_se2
from nomad_j1 import common,execution
from . import config,campaign,launch,metrics,report

class Client:
    def __init__(self):self.jobs=[];self.ready=[];self.snapshot_file=None
    def submit(self,j):self.jobs.append(numeric_job(j))
    def poll(self):return self.ready.pop(0) if self.ready else None
    def close(self):pass

class Field:
    error_bound=0.
    metadata={'file':'synthetic.npz','frame_id':0,'sim_s':0.}
    safe=True
    def query(self,q):return np.full(len(q),1. if self.safe else -.1),np.zeros_like(q)
    def unknown_fraction(self,q):return 0.

def event(i,ns,pose,worlds):
    chunk=describe_chunk(worlds[0],pose)
    return dict(id=i,observation_pose=pose.tolist(),observation_sim_s=0.,received_monotonic_ns=ns,
                chunk=chunk,overnight_metric_samples=worlds.tolist(),topomap={'closest_node':99,'goal_node':99})

def refresh(i,ns,sim=0.):
    return dict(simulation_time_s=sim,monotonic_ns=ns,valid=True,status='valid',waypoint_id=i)

class Tests(unittest.TestCase):
    def test_plan20_order_and_real_launch_dry_run(self):
        plan=campaign.jobs(config.RUN_ROOT)
        self.assertEqual(len(plan),20)
        self.assertEqual([r['delay'] for r in plan],[0.]*10+[.75]*10)
        self.assertEqual({r['index'] for r in plan},{221,222})
        for j in plan:
            a=launch.parser().parse_args(j['argv'][4:]+['--dry-run'])
            with patch.object(launch.subprocess,'Popen',side_effect=AssertionError('No simulation')):
                p=launch.build(a)
            self.assertIn('nomad_isaac.worker',p['worker']);self.assertLess(p['socket_bytes'],100)
            self.assertEqual(p['simulations_started'],0)
        self.assertFalse(config.RUN_ROOT.exists())

    def test_frozen_control_assets_and_no_goal_node_stop(self):
        p=config.verify()
        for j in config.order():
            c=config.runtime_config(j['method'],j['index'],level=j['scene'])
            self.assertEqual(c['goal_tolerance_m'],.3);self.assertFalse(c['nomad_goal_stop'])
            self.assertEqual((c['observation_hz'],c['controller_hz'],c['integration_hz']),(4,9,72))
            self.assertEqual(c['plant_alpha'],'inf');self.assertTrue(c['depth_camera'])
            self.assertEqual(c['phase4c_method'],'GRAPH');self.assertEqual(c['goal_mode'],'topomap')
            self.assertEqual(c['topomap_manifest'],p['scenes'][j['scene']]['topomap'])
        self.assertIs(execution.Execution.__bases__[0],AccelExecution)
        self.assertIs(execution.evaluate_samples,evaluate_samples)
        self.assertIn('ClearanceGraph',inspect.getsource(solve_job))
        self.assertEqual(('*' in inspect.getsource(execution.install)),False)
        from nomad_isaac.async_core import WaypointExecution
        self.assertIn('age < 1.0',inspect.getsource(WaypointExecution.control))
        from nomad_isaac.async_runtime import ExecutionThread
        self.assertIn('distance <= c["goal_tolerance_m"]',inspect.getsource(ExecutionThread.run))

    def test_safe_selection_curv_and_json100ticks(self):
        with tempfile.TemporaryDirectory() as temp:
            field=Field();client=Client();e=execution.Execution(Path(temp),client)
            e.depth_maps=SimpleNamespace(snapshot=lambda:field)
            pose=np.array([0.,0.,0.]);worlds=np.array([np.c_[np.linspace(.1,1+i*.02,8),np.zeros(8)] for i in range(8)])
            core=SimpleNamespace(pose=pose.copy(),v=0.,w=0.,latest={'id':0},applied_id=0)
            s=event(0,1_000_000_000,pose,worlds)
            try:
                r=refresh(0,1_000_000_000);e.apply(core,r,s)
                self.assertEqual(e.active_sample,7);self.assertEqual(len(client.jobs),1)
                np.testing.assert_array_equal(client.jobs[0]['world_xy'],worlds[7])
                self.assertNotIn('public_config',client.jobs[0]);self.assertGreater(core.v,0.)
                self.assertEqual([core.v,core.w],list(control_command('CURV',0.,0.,0.,float('inf'))[0]))
                json.dumps(s,allow_nan=False)
                for tick in range(1,105):
                    ns=1_000_000_000+round(tick/9*1e9);r=refresh(0,ns,tick/9)
                    e.apply(core,r,None);json.dumps(r,allow_nan=False)
                    if tick>=9:self.assertEqual([core.v,core.w],[0.,0.])
                self.assertEqual(r['status'],'expired')
            finally:e.close()
            for f in Path(temp).glob('*.jsonl'):
                for line in f.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)

    def test_all_unsafe_keeps_path_clock_and_endpoint_latch(self):
        with tempfile.TemporaryDirectory() as temp:
            client=Client();field=Field();e=execution.Execution(Path(temp),client);e.depth_maps=SimpleNamespace(snapshot=lambda:field)
            q=np.zeros(3);worlds=np.tile(np.c_[np.linspace(0.,1.,8),np.zeros(8)],(8,1,1))
            core=SimpleNamespace(pose=q.copy(),v=0.,w=0.,latest={'id':0},applied_id=0)
            try:
                e.apply(core,refresh(0,1_000_000_000),event(0,1_000_000_000,q,worlds));old=e.follower
                core.pose=np.array([1.,0.,0.]);e.apply(core,refresh(0,1_100_000_000),None)
                self.assertTrue(e.endpoint_latched)
                core.pose=np.array([.7,0.,0.]);e.apply(core,refresh(0,1_200_000_000),None)
                self.assertEqual(core.v,0.)
                field.safe=False;core.latest={'id':1};core.applied_id=1
                s=event(1,1_500_000_000,q,worlds);e.apply(core,refresh(1,1_500_000_000),s)
                self.assertIs(e.follower,old);self.assertTrue(e.endpoint_latched)
                self.assertEqual(e.path_received_ns,1_000_000_000);self.assertEqual(len(client.jobs),1)
                field.safe=True;s=event(2,2_000_000_000,q,worlds);core.latest={'id':2};core.applied_id=2
                e.apply(core,refresh(2,2_000_000_000),s);self.assertFalse(e.endpoint_latched);self.assertGreater(core.v,0.)
            finally:e.close()

    def test_graph_result_accept_and_superseded(self):
        with tempfile.TemporaryDirectory() as temp:
            e=execution.Execution(Path(temp),Client());field=Field();e.depth_maps=SimpleNamespace(snapshot=lambda:field)
            q=np.zeros(3);xy=np.c_[np.linspace(.1,1.,8),np.zeros(8)];bank=np.tile(xy,(8,1,1))
            core=SimpleNamespace(pose=q.copy(),v=0.,w=0.,latest={'id':0},applied_id=0)
            try:
                e.apply(core,refresh(0,1_000_000_000),event(0,1_000_000_000,q,bank))
                start=e.pending[0]['dispatch_ns']
                e.client.ready.append(dict(job_id=0,id=0,worker_start_ns=start,worker_end_ns=start+1000,
                    result_received_ns=1_100_000_000,poses=np.c_[xy,np.zeros(8)].tolist(),accepted=True,solver={'success':True}))
                r=refresh(0,1_100_000_000);e.apply(core,r,None);self.assertEqual(r['stage2']['graph_applied_job'],0)
                e.apply(core,refresh(1,1_200_000_000),event(1,1_200_000_000,q,bank));core.latest={'id':2};core.applied_id=2
                start=e.pending[1]['dispatch_ns']
                e.client.ready.append(dict(job_id=1,id=1,worker_start_ns=start,worker_end_ns=start+1000,
                    result_received_ns=1_300_000_000,accepted=False,solver={'success':False}))
                e.apply(core,refresh(2,1_300_000_000),event(2,1_300_000_000,q,bank))
            finally:e.close()
            results=[r for r in metrics.rows(Path(temp)/'stage2_graph.jsonl') if r['event']=='RESULT']
            self.assertEqual([r['disposition'] for r in results],['ACCEPTED','SUPERSEDED'])

    def test_checkpoint_geometry_rotation_and_missing_h2(self):
        self.assertAlmostEqual(common.checkpoint_spec('SLW')['threshold_m'],4.6)
        self.assertAlmostEqual(common.checkpoint_spec('LC')['threshold_m'],2.4)
        self.assertAlmostEqual(common.checkpoint_spec('H1-v2')['threshold_m'],1.6)
        c=config.runtime_config(config.METHOD,221,level='H2');poses=np.c_[np.linspace(0,8,100),np.zeros((100,2))]
        self.assertIsNone(metrics.checkpoint(c,{},poses)['checkpoint_time_s'])
        box=dict(center_xy_m=[6.,-.3],size_xyz_m=[.4,1.,.8],yaw_rad=np.pi/2)
        s={'dynamic_obstacle':{'boxes':[{},dict(spawn=dict(tick=50,obstacle=box))]}}
        r=metrics.checkpoint(c,s,poses);self.assertAlmostEqual(r['checkpoint_threshold_m'],6.8)
        self.assertEqual(r['checkpoint_tick'],int(np.flatnonzero(poses[:,0]>=6.8)[0]))
        self.assertEqual(r['checkpoint_start_distance_m'],6.8)

    def test_selection_top3_strict_increase_and_missing(self):
        rr=[]
        for s,zero in zip(config.SCENES,[5.,3.,7.,4.,6.]):
            for d in config.DELAYS:
                for i in config.INDICES:rr.append(dict(scene=s,index=i,delay=d,method=config.METHOD,technical_validation='PASS',success=True,checkpoint_time_s=zero+d))
        r=report.selection(rr);self.assertEqual(r['selected_scenes'],['SLW','LC','H1-v2'])
        for x in rr:
            if x['scene']=='SLW' and x['delay']==.75:x['checkpoint_time_s']=3.
            if x['scene']=='LC' and x['index']==221:x['success']=False
            if x['scene']=='H2' and x['delay']==.75:x['checkpoint_time_s']=None
        self.assertEqual(report.selection(rr)['selected_scenes'],['H1-v2','CL'])

    def test_report_template_and_dry_run_does_not_create_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);doc=report.generate(root,root/'out',root/'J0.md')
            self.assertIn('종료 판정은 Phase18과 동일(0.3m)',doc.read_text())
            self.assertEqual(json.loads((root/'out/decision.json').read_text())['selected_scenes'],[])
            with patch.object(sys,'argv',['campaign','--run-root',str(root/'run'),'--dry-run']),patch.object(campaign,'execute',side_effect=AssertionError('No campaign')):
                with patch('builtins.print'):campaign.main()
            self.assertFalse((root/'run').exists())

    def test_actual_driver_monitor_construction_all5_without_worker_or_simulator(self):
        from nomad_isaac.async_runtime import ExecutionThread
        import nomad_phase15b.execution as factory
        import nomad_phase15b.depth as depth
        import nomad_isaac.clearance as clearance
        import nomad_isaac.sudden_obstacle as sudden
        import nomad_phase1.s1_v2 as s1
        original_monitor=s1.CorridorOnlyMonitor
        for scene in config.SCENES:
            c=config.runtime_config(config.METHOD,221,level=scene)
            with tempfile.TemporaryDirectory() as temp,patch.object(factory,'make_execution'),patch.object(depth,'DepthMapThread'),patch.object(clearance,'corridor_clearance'),patch.object(s1,'CorridorOnlyMonitor',original_monitor),patch.object(sudden,'SuddenObstacleMonitor'):
                execution.install(c)
                with patch.object(execution,'Execution',return_value=SimpleNamespace()):
                    driver=ExecutionThread(c,Path(temp),pure_pursuit=True)
                driver.monitor.observe_interval(np.array(c['start_pose']),np.array(c['start_pose']),0.,0.,0.,0.)
                result=driver.monitor.finish(False)
                self.assertFalse(result['geometric_overlap'])
                if scene=='H2':self.assertIsNone(result['minimum_swept_clearance_lower_m'])
                if driver.dynamic is not None:
                    driver.dynamic.observe_tick(0,c['start_pose'],c['start_pose'],0.,0.,-1,False,0)
                    driver.dynamic.finish(False)

if __name__=='__main__':unittest.main()
