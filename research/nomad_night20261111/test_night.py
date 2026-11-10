"""Numerical parity, routing, deadline/retry and paired-report unit tests."""
import copy,inspect,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase17.graph import ClearanceGraph
from nomad_phase32o.test_exec_cert import field
from nomad_phase53p.runtime import Execution as Handoff
from nomad_phase32.runtime import Execution as ECExecution
from .graph import HoldClearanceGraph,drop_boundary
from . import config,queue,runtime,report

class Tests(unittest.TestCase):
    def test_boundary_threshold_and_all_other_factors_rows_identical(self):
        self.assertTrue(drop_boundary([0,0]));self.assertTrue(drop_boundary([.019,0]));self.assertFalse(drop_boundary([.02,0]))
        self.assertFalse(drop_boundary([.05,.4]));self.assertTrue(drop_boundary([.049,.4]))
        xy=np.column_stack([np.linspace(.1,1.3,8),np.linspace(0,.1,8)]);f=field();B=[0,0,0]
        for command in ([.2,.1],[.01,0],[0,0],[.03,.4]):
            new=HoldClearanceGraph(xy,B,command,f);old=ClearanceGraph(xy,B,command if not drop_boundary(command) else [.2,0],f)
            x=new.initial.ravel()+np.linspace(-.001,.001,24)
            self.assertEqual(new.p,old.p);np.testing.assert_array_equal(new.initial,old.initial)
            for a,b in zip(new.objective(x),old.objective(x)):np.testing.assert_allclose(a,b,atol=1e-12,rtol=0)
            ng,nj,ne,nej=new.constraints(x);og,oj,oe,oej=old.constraints(x)
            np.testing.assert_array_equal(ng,og);np.testing.assert_array_equal(nj,oj)
            if drop_boundary(command):self.assertEqual(ne.shape,(0,));self.assertEqual(nej.shape,(0,24));self.assertFalse(new.flags['boundary_curvature'])
            else:np.testing.assert_array_equal(ne,oe);np.testing.assert_array_equal(nej,oej)
            self.assertEqual(new.certificate(x.reshape(8,3)),old.certificate(x.reshape(8,3)))
    def test_hold_core_removes_only_expiry_and_keeps_90degree_executor(self):
        from nomad_phase52p.runtime import HoldCore
        from nomad_isaac.async_core import WaypointExecution
        # Execute the actual frozen and HOLD control methods on identical state.
        def core():return SimpleNamespace(control_stride=8,latest=dict(id=3,received_monotonic_ns=0,selected_waypoint_m=[1,0]),
            expired_ids=set(),controller=lambda p:(.2,.1),applied_id=3,pose=np.zeros(3),hz=72)
        a,b=core(),core();ra,_=WaypointExecution.control(a,8,2_000_000_000);rb,_=HoldCore.control(b,8,2_000_000_000)
        self.assertFalse(ra['valid']);self.assertTrue(rb['valid']);self.assertFalse(rb['new_timeout'])
        self.assertIs(runtime.HoldExecution.ec_check,Handoff.ec_check)
    def test_hold_existing_short_path_ec_pass_and_reject(self):
        obj=object.__new__(runtime.HoldExecution);obj.sp=object();obj.follower=SimpleNamespace(path=SimpleNamespace(points=np.array([[0,0],[.1,0]])))
        obj.depth_maps=SimpleNamespace(snapshot=lambda:object());obj.actual_vw=lambda:[.1,0.];obj.ec_cap=None;obj.ec_due=None;obj.ec_pending='old';obj.path_source_id=1
        obj.recovery=SimpleNamespace(decision=lambda mode:None);obj.set_hold=lambda *a:None;obj.record52=lambda *a,**k:None
        obj.ec_check=lambda *a,**k:dict(passed=True,check_id=7)
        self.assertTrue(obj.try_hold(SimpleNamespace(pose=[0,0,0]),dict(simulation_time_s=1.),'TEST'));self.assertEqual(obj.mode,'KEEP_ACTIVE')
        obj.ec_check=lambda *a,**k:dict(passed=False,check_id=8)
        self.assertFalse(obj.try_hold(SimpleNamespace(pose=[0,0,0]),dict(simulation_time_s=1.),'TEST'))
    def test_ours_r3_factory_only_replaces_ec_predicate(self):
        import nomad_phase35.runtime as old
        marker=SimpleNamespace()
        with patch.object(old,'make_execution',return_value=marker) as make:
            obj=runtime.make(dict(night_method='OURS-R3'),None)
        self.assertIs(obj,marker);self.assertIs(obj.ec_check.__func__,Handoff.ec_check);make.assert_called_once()
    def test_all120_configs_and_launcher_arguments_in_real_fresh_modules(self):
        code=r'''
import json,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from nomad_night20261111 import config as c,launch as l,queue as q
from nomad_phase53p import config as old
from nomad_phase40p.launch import bind
class Boundary(Exception):pass
p=c.verify();jobs=q.jobs(c.EXP)[1]+q.jobs(c.EXP,True)[1]
for j in jobs:
 cfg=c.runtime_config(j['method'],j['index'],90,j['scene'])
 scene,condition=c.split(j['scene']);native='GRAPH-HO' if j['method'] in ('GRAPH-HO','GRAPH-HOLD') else 'CUT'
 base=bind(old.runtime_config,INDICES=(95,225,226))(native,j['index'],90,('H1' if scene=='H1-v2' else scene)+'_'+condition)
 allowed={'phase38_jitter','run_id','night_experiment','night_method','night_level'}
 if scene=='H1-v2':allowed|={'scene_variant','h1v2','dynamic_obstacle'}
 if j['method']=='OURS-R3':allowed.add('phase38_method')
 assert {k:v for k,v in cfg.items() if k not in allowed}=={k:v for k,v in base.items() if k not in allowed}
 assert cfg['nomad_goal_stop'] and cfg['phase43p']
 json.dumps(cfg,allow_nan=False)
 fn=l.launcher_main(SimpleNamespace(Popen=lambda *a,**k:(_ for _ in ()).throw(AssertionError('process forbidden'))))
 fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
 args=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
 if j['index']==95:args.append('--smoke')
 with patch.object(sys,'argv',args):
  try:fn()
  except Boundary:pass
  else:raise AssertionError('Parser did not reach boundary')
print(c.EXP,len(jobs)-1)
'''
        for e,n in [('E1',36),('E2',48),('E3',36)]:
            r=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research',NOMAD_NIGHT_EXPERIMENT=e),text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr[-3000:]);self.assertIn(f'{e} {n}',r.stdout)
    def test_deadline_before_retry_does_not_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out1=root/'attempt1';out2=root/'attempt2';j=dict(scene='LC_D075',index=225,method='CUT',key='test',outputs=[str(out1),str(out2)])
            r=dict(j,attempt=1,output=str(out1),exit_code=1,technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)
            queue.base.write(root/'attempt_metrics/test_1.json',r)
            with patch.object(queue.subprocess,'Popen',side_effect=AssertionError('No launch after deadline')):
                with self.assertRaises(queue.DeadlineReached):queue.one_job('E1',root,j,{},deadline=time.time()-1)
            self.assertFalse(out2.exists());self.assertFalse((root/'metrics/test.json').exists())
    def test_smoke_single_attempt_failure_preserved_and_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'attempt1';out.mkdir();j=dict(scene='LC_D075',index=95,method='OURS-R3',key='smoke',outputs=[str(out)])
            with patch.object(queue.subprocess,'Popen',side_effect=AssertionError('No resimulation')):r=queue.one_job('E1',root,j,{},smoke=True)
            self.assertEqual(r['technical_validation'],'FAIL');self.assertEqual(r['attempt_count'],1)
            self.assertEqual(queue.one_job('E1',root,j,{},smoke=True)['attempt_count'],1)
    def test_report_complete_pairs_descriptive_margin_and_exact_p(self):
        rows=[]
        for condition in ('D075','D150'):
            for scene in config.BASE_SCENES:
                for index in (225,226):
                    for method in ('CUT-HOLD','GRAPH-HOLD'):
                        rows.append(dict(scene=scene+'_'+condition,index=index,method=method,technical_validation='PASS',success=True,goal_time_s=30. if method=='CUT-HOLD' else 29.,align_rotate_s=2. if method=='CUT-HOLD' else 1.,graph_attempts=10,graph_applied=8))
        rows[-1]['success']=False
        d=report.decide('E2',rows);self.assertEqual([r['complete_pairs'] for r in d['primary']],[12,12]);self.assertTrue(d['primary'][1]['descriptive_noninferior']);self.assertEqual(d['primary'][1]['goal_delta'],-1)
        self.assertEqual(d['primary'][1]['cut_only_goal'],1);self.assertEqual(len(d['delay_gain_comparison']),12)
        rows[-1]['technical_validation']='FAIL';self.assertEqual(report.decide('E2',rows)['primary'][1]['complete_pairs'],11)
        self.assertEqual(report.exact(0,0),1.);self.assertEqual(report.exact(3,0),.25)
    def test_graph_worker_transport_and_source_unchanged(self):
        from . import worker
        from nomad_phase53p import worker as old
        self.assertIs(worker.Client.solve,old.Client.solve)
        self.assertIn('HoldClearanceGraph as ClearanceGraph',worker.source.replace('from nomad_phase17.graph import ClearanceGraph','from nomad_night20261111.graph import HoldClearanceGraph as ClearanceGraph'))
        for e in config.DEFS:config.verify(e)
if __name__=='__main__':unittest.main()
