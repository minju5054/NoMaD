"""Selection and launcher plumbing only: no simulator, solver or log replay."""
import json,inspect,time,tempfile,unittest,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import config,campaign,launch,runtime,report,figures,metrics
from nomad_phase32o.test_exec_cert import field
from nomad_phase32.runtime import path_key
from nomad_phase32.policy import CappedNA

class Tests(unittest.TestCase):
    def options(self,angles,lengths=None,B=None,ref=None):
        B=np.zeros(3) if B is None else np.array(B,float);lengths=lengths or [1.]*len(angles);items=[]
        for i,(angle,length) in enumerate(zip(angles,lengths)):
            delta=length*np.array([np.cos(angle),np.sin(angle)]);path=np.array([B[:2],B[:2]+delta])
            items.append(dict(index=i,key=path_key(path),path=path,rank=i+1,kind='SAFE'))
        primary=dict(items[-1],_cons_B=B,_cons_reference_endpoint=ref)
        return primary,items
    def test_angle_then_length_then_index(self):
        p,o=self.options([.3,-.3,1.],[1.,1.5,2.])
        r=runtime.select_cons(p,o,lambda *a:{'passed':True});self.assertEqual(r['item']['index'],1)
        p,o=self.options([0.,0.],[1.,1.]);r=runtime.select_cons(p,o,lambda *a:{'passed':True});self.assertEqual(r['item']['index'],0)
    def test_backward_allowed_only_after_passing_forward_unavailable(self):
        p,o=self.options([2.5,.2,-.3],[3.,1.,1.]);seen=[]
        r=runtime.select_cons(p,o,lambda x,c:(seen.append((x['index'],c)) or {'passed':True}))
        self.assertEqual(r['item']['index'],1);self.assertEqual(seen,[(1,None)])
        seen=[];r=runtime.select_cons(p,o,lambda x,c:(seen.append((x['index'],c)) or {'passed':x['index']==0}))
        self.assertEqual(r['item']['index'],0);self.assertEqual([x[0] for x in seen],[1,2,0])
    def test_reference_is_current_B_to_last_installed_endpoint(self):
        p,o=self.options([0.,np.pi/2],B=[1.,0.,0.],ref=[1.,2.])
        r=runtime.select_cons(p,o,lambda *a:{'passed':True});self.assertEqual(r['item']['index'],1)
        p,o=self.options([0.,np.pi/2],B=[1.,0.,np.pi/2],ref=None)
        self.assertEqual(runtime.select_cons(p,o,lambda *a:{'passed':True})['item']['index'],1)
    def test_frozen_slow_tier_and_rejected_primary_mapping(self):
        p,o=self.options([0.,.5],[1.,2.]);calls=[]
        r=runtime.select_cons(p,o,lambda x,c:(calls.append((x['index'],c)) or {'passed':c==.1}))
        self.assertEqual(calls,[(0,None),(1,None),(0,.1)]);self.assertEqual(r['cap'],.1)
        calls=[];r=runtime.select_cons(p,o,lambda x,c:(calls.append((x['index'],c)) or {'passed':True}),primary_rejected=True)
        self.assertEqual(r['item']['index'],0);self.assertEqual(calls,[(0,None)])
        calls=[];runtime.select_cons(p,o,lambda x,c:(calls.append((x['index'],c)) or {'passed':False}),retained_cap=.1)
        self.assertTrue(all(c==.1 for _,c in calls))
    def test_alignment_cap_and_endpoint_latch_all_preserved(self):
        p=runtime.LatchedProfile();p.replace_path([[0,0],[-1,0]],[0,0,0],0.)
        self.assertTrue(p.trigger_S);self.assertEqual(p.mode,'BRAKE');self.assertEqual(p.alignment_threshold_deg,90.)
        p.replace_path([[0,0],[.1,0]],[0,0,0],.1);p.speed_cap=.1
        _,d=p.control(np.array([.1,0,0]),.1);self.assertTrue(d['completed'])
        for _ in range(3):
            command,d=p.control(np.array([.3,0,0]),.1);self.assertEqual(command,(0.,0.));self.assertEqual(d['ec_speed_cap_m_s'],.1);json.dumps(d,allow_nan=False)
        p.replace_path([[.3,0],[1,0]],[.3,0,0],0.);self.assertFalse(p.endpoint_latched)
        self.assertIs(runtime.ConsExecution.use_fallback,runtime.Handoff.use_fallback)
    def test_real_launcher18_and_unchanged_config(self):
        self.assertEqual(len(campaign.jobs()),18)
        class Boundary(Exception):pass
        for j in campaign.jobs():
            c=config.runtime_config(j['method'],j['index'],90,j['scene']);self.assertTrue(c['nomad_goal_stop']);self.assertTrue(c['phase43p']);self.assertEqual(c['phase38_method'],'OURS-DETOUR')
            if j['scene']=='H1-v2':self.assertEqual(c['h1v2']['requested_target']['y_m'],1.10)
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No processes')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            with patch.object(sys,'argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]),self.assertRaises(Boundary):fn()
            with patch('subprocess.Popen',return_value=SimpleNamespace()) as popen:
                p=launch.Processes();p.Popen(['python','-m','nomad_isaac.worker']);self.assertIn('nomad_phase43p.worker',popen.call_args.args[0])
                p.Popen(['isaac',str(config.ROOT/'research/nomad_phase26/simulator.py')]);self.assertIn(str(config.HERE/'simulator.py'),popen.call_args.args[0])
    def test_actual_apply_chain_and_graph_endpoint_reference(self):
        for method in config.METHODS:
            with tempfile.TemporaryDirectory() as tmp:
                f=field();f.observed=np.ones_like(f.occupied);f.metadata=dict(frame_id=1,sim_s=1.,publication_monotonic_ns=1)
                paths=[]
                for i in range(8):
                    endpoint=np.array([1+i*.07,i*.04]);paths.append(np.linspace([.1,0],endpoint,8))
                calls=[]
                def solve(job):
                    calls.append(job);xy=np.asarray(job['world_xy']).copy();xy[-1,1]+=.05
                    return dict(accepted=True,reason='ACCEPTED',poses=np.c_[xy,np.zeros(8)].tolist(),solver={'feasible':True,'boundary_curvature_dropped':True},solve_s=.01)
                worker=SimpleNamespace(solve=solve,close=lambda:None)
                e=runtime.ConsExecution(method,Path(tmp),worker);e.depth_maps=SimpleNamespace(snapshot=lambda:f);e.ec_check=lambda *a,**k:dict(passed=True,check_id=1)
                core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.)
                packet=dict(id=0,observation_pose=[0,0,0],overnight_metric_samples=np.asarray(paths),received_monotonic_ns=time.monotonic_ns())
                try:
                    e.apply(core,dict(simulation_time_s=1.,monotonic_ns=time.monotonic_ns(),valid=True),packet)
                    self.assertEqual(e.active_sample,7 if method=='CUT' else 0);self.assertIsInstance(e.sp,runtime.LatchedProfile)
                    self.assertNotIn('depth_filter_disabled',packet['phase16']['selection'])
                    expected=np.array(paths[7 if method=='CUT' else 0][-1]);expected[1]+=.05 if method=='CONS+G18' else 0.
                    np.testing.assert_allclose(e.cons_endpoint,expected)
                    self.assertEqual(len(calls),int(method=='CONS+G18'))
                    for p in Path(tmp).glob('*.jsonl'):
                        for line in p.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
                    records=[json.loads(x) for x in (Path(tmp)/'graph_ho.jsonl').read_text().splitlines() if json.loads(x)['event']=='INSTALL']
                    self.assertIsNone(records[0]['reference_endpoint_before']);self.assertEqual(records[0]['reference_endpoint_after'],e.cons_endpoint)
                finally:e.close()
    def test_frozen_graph_drop_only_and_original_expiry(self):
        from nomad_night20261111.graph import drop_boundary,HoldClearanceGraph
        from nomad_phase17.graph import ClearanceGraph
        self.assertIs(HoldClearanceGraph.__bases__[0],ClearanceGraph)
        self.assertTrue(drop_boundary([.019,0.]));self.assertTrue(drop_boundary([.02,.17]));self.assertFalse(drop_boundary([.02,.16]))
        from nomad_isaac.async_core import WaypointExecution
        self.assertIn('age < 1.0',inspect.getsource(WaypointExecution.control))
        self.assertIn('nomad_night20261111.worker',inspect.getsource(runtime.Execution.__init__))
    def test_selection_counts(self):
        events=[]
        for i,angle in enumerate([.5,-.5,2.5]):
            events.append(dict(tick=i,id=i,pose=[0,0,0],reference_endpoint_before=[1,0],original_candidate_world=[[0,0],[np.cos(angle),np.sin(angle)]]))
        r=metrics.choice_metrics(events);self.assertEqual(r['left_right_switches'],2);self.assertEqual(r['backward_reference_selections'],1)
    def test_report_baseline_columns_and18_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();baseline=root/'baseline.json'
            baseline.write_text(json.dumps([dict(scene='SLW',index=227,method='MIN',technical_validation='PASS',success=True,goal_time_s=12.)]))
            for i,j in enumerate(config.registered_order()):
                (root/'metrics'/f'{i}.json').write_text(json.dumps(dict(j,key=f'{i}',technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)))
            with patch.object(report,'BASELINE',baseline),patch.object(figures,'generate',return_value=[]) as fig:
                doc=report.generate(root,root/'out',root/'report.md');self.assertEqual(len(fig.call_args.args[0]),18)
            self.assertIn('P57_NOMAD_RAW',doc.read_text());self.assertIn('P57_MIN',doc.read_text());self.assertIn('—',doc.read_text())
            self.assertEqual(json.loads((root/'out/status.json').read_text())['phase57_baseline_records'],1)
if __name__=='__main__':unittest.main()
