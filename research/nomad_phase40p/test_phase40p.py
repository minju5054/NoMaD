import copy,io,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase32.policy import CappedNA
from nomad_phase32o.test_exec_cert import field
from .schedule import application_tick,predict,disposition


class TimingTests(unittest.TestCase):
    def test_deadline_first_control_tick_and_late_drop(self):
        for tick in range(0,800,8):
            target=application_tick(tick)
            self.assertEqual(target%8,0);self.assertGreaterEqual(target-tick,54);self.assertLess(target-tick,62)
            j=dict(apply_tick=target);r=dict(parent_received_ns=99,selected_sample=0)
            self.assertEqual(disposition(j,r,target-8,100),'WAIT')
            self.assertEqual(disposition(j,r,target,100),'ACCEPTED')
            self.assertEqual(disposition(j,r,target+8,100),'STALE')
            self.assertEqual(disposition(j,None,target,100),'TIMEOUT')
            self.assertEqual(disposition(j,r,target,98),'TIMEOUT')
            self.assertEqual(disposition(j,r,target-8,100,True),'SUPERSEDED')
    def test_prediction_is_frozen_continuation_not_reinstall(self):
        c=CappedNA();q=np.array([0.,0.,.2]);c.replace_path([[0,0],[.5,.2],[2,.3]],q,.1)
        (v,w),_=c.control(q,.1);other=copy.deepcopy(c);start=(v,w)
        result=predict(c,q,start,16,72)
        for tick in range(16,72):
            if tick>16 and tick%8==0:(v,w),_=other.control(q,v)
            q=integrate_se2(q,v,w,1/72)
        np.testing.assert_array_equal(result['pose'],q)
        self.assertEqual(result['commands'][0],list(start));self.assertEqual(len(result['commands']),56)
        json.dumps(result,allow_nan=False)
    def test_prediction_preserves_rotation_and_cap(self):
        c=CappedNA();c.replace_path([[0,0],[-1,0]],[0,0,0],0);c.control([0,0,0],0)
        c.target_yaw=.4;c.mode='ROTATE';c.speed_cap=.1
        result=predict(c,[0,0,0],[0,.4],0,56)
        self.assertAlmostEqual(result['pose'][0],0);self.assertGreater(result['pose'][2],0)
        self.assertEqual(c.target_yaw,.4);self.assertEqual(c.mode,'ROTATE')
    def test_stopped_prediction_decelerates_without_invented_path(self):
        r=predict(None,[0,0,0],[.1,0],0,56)
        self.assertGreater(r['pose'][0],0);self.assertEqual(r['vw'],[0.,0.])


class SolverRoutingTests(unittest.TestCase):
    def test_vn_unchanged_r2_ve_r3_vn(self):
        from . import pool
        stub=dict(results=[],selected_sample=None)
        with patch.object(pool.r2,'evaluate_job',return_value=stub) as a,patch.object(pool.r3,'evaluate_job',return_value=stub) as b:
            for kind in ('R2','R3'):
                r=pool.evaluate_job(None,dict(kind=kind,dispatch_ns=time.monotonic_ns(),job_id=1))
                self.assertEqual(r['online_variant'],'VN');json.dumps(r)
            self.assertEqual(a.call_args.args[1]['variant'],'VE')
            self.assertEqual(b.call_args.args[1]['variant'],'VN');self.assertFalse(b.call_args.args[1]['soft_policy_map'])
    def test_four_worker_bridge_v2_and_both_frozen_solvers(self):
        from .worker import Worker
        from nomad_phase39o3.test_maps import base_field
        from nomad_phase20d.recent import RecentSnapshot
        from nomad_phase33p.storage import install
        install();f=base_field();f.occupied[:]=False;f.values[:]=5.;f.last_free_tick[:]=0
        snap=RecentSnapshot(f,dict(frame_id=1,sim_s=0))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);worker=Worker(root)
            try:
                for j,kind in enumerate(('R2','R3')):
                    job=dict(job_id=j,kind=kind,B=[0,0,0],u_ref=[1,0],evaluation_tick=0,dispatch_ns=time.monotonic_ns(),
                             samples_world=[[[0,0],[.5,0],[1,0]]]*8)
                    worker.submit(job,snap);deadline=time.monotonic()+30;r=None
                    while r is None and time.monotonic()<deadline:
                        r=worker.poll()
                        if r is None:time.sleep(.01)
                    self.assertIsNotNone(r);self.assertNotIn('error',r);self.assertIsNotNone(r['selected_sample'])
                    self.assertEqual(len(r['results']),8 if kind=='R2' else 7);self.assertEqual(r['online_variant'],'VN')
                    json.dumps(r,allow_nan=False)
                    with np.load(root/'repair_jobs'/f'input_{j:04d}.npz') as z:self.assertNotIn('values',z.files)
                env=json.loads((root/'repair_pool_environment.json').read_text())
                self.assertEqual(len(set(env['pids'])),4)
            finally:worker.close()


class RuntimeTests(unittest.TestCase):
    def fake(self):
        from .runtime import Execution
        from nomad_phase32.test_phase32 import WiringTests
        o=object.__new__(Execution);old=WiringTests().fake_execution();o.__dict__.update(old.__dict__)
        o.n_pending=None;o.n_result=None;o.n_after_r2=False;o.n_installing=None
        o.n_escape=None;o.n_escape_jobs={};o.n_last_install_escape=False;o.n_log=io.StringIO();o.n_preview_anchors={}
        o.n_worker=SimpleNamespace(poll=lambda:None,busy=lambda:False,submit=lambda *a:None)
        o.active_id=3;o.next_repair=0;o.detour_count=0;o.no_progress=SimpleNamespace(started=lambda:None)
        o.history=[np.zeros(3)]*400;o.nrecord=lambda e,**kw:json.dumps(dict(event=e,**kw),allow_nan=False)
        o.drecord=lambda *a,**kw:None;o.rlog=lambda *a,**kw:None
        return o
    def test_dispatch_does_not_clear_controller_or_set_wait_mode(self):
        o=self.fake();core=SimpleNamespace(pose=np.zeros(3));refresh=dict(simulation_time_s=0,monotonic_ns=10)
        o.sp=CappedNA();o.sp.replace_path([[0,0],[2,0]],core.pose,0);before=o.sp
        self.assertTrue(o.dispatch(core,refresh,dict(kind='R2',samples_world=[])))
        self.assertIs(o.sp,before);self.assertEqual(o.mode,'NORMAL');self.assertIsNone(o.repair_pending)
        self.assertEqual(o.n_pending['apply_tick'],56)
    def test_result_held_until_tick_and_actual_pose_ec_then_selected(self):
        o=self.fake();job=dict(job_id=0,kind='R3',id=3,apply_tick=56,B=[.1,0,0],u_ref=[1,0],dispatch_ns=10)
        o.n_pending=job
        o.n_result=dict(job_id=0,parent_received_ns=99,selected_sample=0,results=[dict(accepted=True,path=[[.1,0],[1,0]],cB=.2,progress_m=1.,length_m=1.)])
        calls=[];o.ec_check=lambda pose,*a,**kw:(calls.append(pose.copy()) or dict(passed=True,check_id=0))
        o.ec_install=lambda *a,**kw:dict(installed=True)
        core=SimpleNamespace(pose=np.array([.15,.02,0.]));refresh=dict(simulation_time_s=48/72,monotonic_ns=100,valid=True)
        o.poll_job(core,refresh,None);self.assertEqual(calls,[])
        refresh['simulation_time_s']=56/72;o.poll_job(core,refresh,None)
        np.testing.assert_array_equal(calls[0],core.pose);self.assertTrue(o.detour_active);self.assertIsNone(o.n_pending)
    def test_new_fresh_supersedes_r2_and_late_result_cannot_install(self):
        o=self.fake();o.n_pending=dict(job_id=0,kind='R2',id=3,apply_tick=56,dispatch_ns=1)
        o.n_result=dict(parent_received_ns=1,selected_sample=0)
        o.ec_install=lambda *a,**kw:self.fail('Superseded job installed')
        o.poll_job(SimpleNamespace(pose=np.zeros(3)),dict(simulation_time_s=8/72,monotonic_ns=2,valid=True),{'id':4})
        self.assertIsNone(o.n_pending);self.assertFalse(o.n_after_r2)
    def test_waiting_commands_equal_ours_without_detour(self):
        from .runtime import Execution
        from nomad_phase38.ec_normal import RTCWithEC
        f=field();f.observed=np.ones(f.occupied.shape,bool)
        f.metadata=dict(frame_id=0,sim_s=0.,publication_monotonic_ns=0)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'new').mkdir();(root/'old').mkdir()
            worker=SimpleNamespace(poll=lambda:None,busy=lambda:False,submit=lambda *a:None,close=lambda:None)
            with patch('nomad_phase40p.runtime.Worker',return_value=worker):new=Execution(root/'new')
            old=RTCWithEC(root/'old')
            try:
                cores=[]
                for o in (new,old):
                    o.depth_maps=SimpleNamespace(snapshot=lambda:f)
                    o.snapshot=f;cores.append(SimpleNamespace(pose=np.zeros(3),v=0.,w=0.))
                    o.history=[np.zeros(3)]
                new.n_pending=dict(job_id=100,kind='R3',id=0,apply_tick=1000)
                bank=np.repeat(np.array([[[0,0],[.5,0],[1.,0]]]),8,axis=0).tolist()
                switch=dict(id=0,observation_pose=[0,0,0],observation_sim_s=0.,overnight_metric_samples=bank,received_monotonic_ns=time.monotonic_ns())
                for tick in range(128):
                    if tick%8==0:
                        for o,core in zip((new,old),cores):
                            refresh=dict(simulation_time_s=tick/72,monotonic_ns=time.monotonic_ns(),valid=True)
                            event=copy.deepcopy(switch) if tick==0 else None
                            o.apply(core,refresh,event)
                            json.dumps(refresh,allow_nan=False)
                            if event is not None:json.dumps(event,allow_nan=False)
                        self.assertEqual(new.last_command,old.last_command)
                        self.assertNotIn(new.mode,('REPAIR_WAIT','DETOUR_WAIT'))
                    for o,core in zip((new,old),cores):
                        core.pose=integrate_se2(core.pose,core.v,core.w,1/72);o.history.append(core.pose.copy())
                self.assertGreater(cores[0].pose[0],.3)
                for path in (root/'new').glob('*.jsonl'):
                    for line in path.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
            finally:new.close();old.close()

    def test_periodic_rejection_of_planner_path_has_original_route_and_delay(self):
        from .runtime import PlanningBase
        o=self.fake();o.nrecord=lambda *a,**k:None
        o.ec_pending=dict(generation=0,state='R2',check_tick=36,check_id=1,check_started_ns=time.monotonic_ns(),
                          path=np.array([[0,0],[1,0]]),source_id=0)
        o.ec_switch=None;o.path_kind='REPAIR';core=SimpleNamespace(pose=np.zeros(3))
        with patch.object(PlanningBase,'apply'):
            o.apply(core,dict(simulation_time_s=40/72,monotonic_ns=time.monotonic_ns()),None)
        self.assertTrue(o.n_after_r2);self.assertEqual(o.mode,'STOP_WAIT')
        rows=[json.loads(x) for x in o.ec_file.getvalue().splitlines()]
        event=next(x for x in rows if x['event']=='PERIODIC_APPLY')
        self.assertEqual(event['action'],'R2_TO_R3');self.assertEqual(event['delay_ticks'],4)
        self.assertIn('delay_wall_ms',event)
    def test_r2_failure_keeps_r3_transition_until_pool_is_available(self):
        from .runtime import PlanningBase
        from nomad_phase38.ec_normal import RotateOnly
        o=self.fake();o.n_after_r2=True;o.poll_job=lambda *a:None
        core=SimpleNamespace();refresh={};calls=[]
        o.start_detour=lambda *a:(calls.append('busy') or False)
        with patch.object(RotateOnly,'apply'):
            PlanningBase.apply(o,core,refresh,None)
        self.assertTrue(o.n_after_r2)
        o.start_detour=lambda *a:(calls.append('submitted') or True)
        with patch.object(RotateOnly,'apply'):
            PlanningBase.apply(o,core,refresh,None)
        self.assertFalse(o.n_after_r2);self.assertEqual(calls,['busy','submitted'])


class EscapeTests(unittest.TestCase):
    def test_projected_arclength_first_crossing_and_absolute_deadline(self):
        from .escape import installation_anchor
        from nomad_phase0.pure_pursuit import XYPath
        p=[[0,0],[.4,0],[1,0]]
        a,tr=installation_anchor(2,.01,12.,[.01,0,0],[.2,0],p,field(),None)
        curve=XYPath(p);s=(.03-.01)/.5
        first=next(i for i,q in enumerate(tr['poses']) if curve.project(q[:2])[0]>=s)
        self.assertEqual(a['t_escape_s'],first/72);self.assertEqual(a['escape_deadline_sim_s'],12+first/72)
        self.assertEqual(a['time_reason'],'PROJECTED_S_ESCAPE');self.assertFalse(a['cap_applied'])
        # Already projected past s_esc at installation: no new escape window.
        b,_=installation_anchor(3,.01,12.,[.1,0,0],[0,0],p,field())
        self.assertEqual(b['t_escape_s'],0.)
    def test_rotation_cap_all_two_seconds_are_low_threshold(self):
        from .escape import installation_anchor,certify_escape
        f=field([.1,0]);p=[[0,0],[-1,0]]
        a,tr=installation_anchor(2,.0,7.,[0,0,0],[0,0],p,f)
        self.assertEqual(a['t_escape_s'],2.);self.assertEqual(a['escape_deadline_sim_s'],9.)
        self.assertTrue(a['cap_applied'])
        r=certify_escape([0,0,0],[0,0],p,f,a,7.,trace=tr)
        self.assertTrue(r['passed']);self.assertEqual(r['thresholds'],[a['c0']])
        r=certify_escape([0,0,0],[0,0],p,f,a,9.)
        self.assertFalse(r['passed']);self.assertEqual(r['thresholds'],[.025])
    def test_short_endpoint_before_escape_uses_endpoint_time(self):
        from .escape import installation_anchor
        a,tr=installation_anchor(2,-.2,7.,[0,0,0],[0,0],[[0,0],[.2,0]],field())
        self.assertTrue(tr['endpoint_reached']);self.assertLess(a['path_length_m'],a['s_escape_m'])
        self.assertEqual(a['time_reason'],'ENDPOINT_BEFORE_S_ESCAPE')
        self.assertEqual(a['t_escape_s'],tr['duration_s']);self.assertFalse(a['cap_applied'])
    def test_job_reinstallation_keeps_original_anchor_and_periodic_clock(self):
        from .runtime import Execution
        from nomad_phase32.runtime import path_key
        o=RuntimeTests().fake();log=[];o.nrecord=lambda e,**k:log.append(dict(event=e,**k))
        f=field([.1,0]);f.metadata={'frame_id':0,'sim_s':0};o.depth_maps=SimpleNamespace(snapshot=lambda:f)
        path=[[0,0],[-1,0]];job={'job_id':9};candidate=dict(cB=0.,path=path)
        o.n_installing=(job,candidate);q=np.zeros(3);core=SimpleNamespace(pose=q)
        check=o.ec_check(q,[0,0],path,f,1.,'R2','INSTALL_CANDIDATE',None)
        self.assertTrue(check['passed']);o.ec_tokens.add((72,path_key(path)))
        o.ec_install(path,core,dict(simulation_time_s=1.,monotonic_ns=1),0,'REPAIR')
        first=copy.deepcopy(o.n_escape);self.assertEqual(first['escape_deadline_sim_s'],3.)
        # A fresh snapshot and a later installation of the SAME job must not
        # reset c0 or the absolute deadline.
        check=o.ec_check(q,[0,0],path,f,1.5,'R2','INSTALL_CANDIDATE',None)
        self.assertFalse(check['passed'])  # Strict tail after original deadline.
        self.assertEqual(o.n_preview_anchors[(9,path_key(path))],first)
        periodic=o.ec_check(q,[0,0],path,f,3.,'NORMAL','PERIODIC',None,o.sp)
        self.assertFalse(periodic['passed']);self.assertFalse(periodic['escape_active'])
        for line in o.ec_file.getvalue().splitlines():json.dumps(json.loads(line),allow_nan=False)
        self.assertEqual(log[0]['event'],'ESCAPE_INSTALL');self.assertFalse(log[0]['consecutive'])
    def test_subtick_arc_cut_matches_integrator(self):
        from .escape import slice_trace
        q=np.array([0.,0.,.2]);cmd=np.array([[.3,.4]]*3)
        poses=[q]
        for v,w in cmd:poses.append(integrate_se2(poses[-1],v,w,1/72))
        p,c=slice_trace(dict(poses=np.array(poses),commands=cmd),.005,.032)
        x=integrate_se2(q,.3,.4,.005)
        np.testing.assert_allclose(p[0],x,atol=1e-14)
        for i,(v,w) in enumerate(c):
            x=integrate_se2(x,v,w,1/72);np.testing.assert_allclose(p[i+1],x,atol=1e-14)
    def test_escape_uses_latest_map_and_does_not_extend_clock(self):
        from .escape import check_trace
        from nomad_phase32o.exec_cert import rollout
        trace=rollout([0,0,0],[0,0],[[0,0],[-1,0]])
        f=field([.1,0]);early=check_trace(f,trace,.005,3.,0)
        self.assertTrue(early['passed'])
        expired=check_trace(f,trace,.005,3.,3.)
        self.assertFalse(expired['passed']);self.assertFalse(expired['escape_active'])
        newer=field([.09,0]);self.assertFalse(check_trace(newer,trace,.005,3.,0)['passed'])
        json.dumps(early,allow_nan=False)
    def test_crossing_requires_strict_clearance_after_deadline(self):
        from .escape import check_trace
        from nomad_phase32o.exec_cert import rollout
        trace=rollout([0,0,0],[0,0],[[0,0],[-1,0]])
        result=check_trace(field([.1,0]),trace,.005,1.,.5)
        self.assertFalse(result['passed']);self.assertEqual(result['thresholds'],[.005,.025])


class PreparationTests(unittest.TestCase):
    def test_campaign_engine_wiring_does_not_start_processes(self):
        from .config import ROOT
        code='''
import sys
from unittest.mock import patch
from nomad_phase40p import campaign as c
from nomad_phase40p.config import RUN_ROOT,SMOKE_ROOT
def halt():
 smoke='--smoke-only' in sys.argv
 plan=c.base.jobs(SMOKE_ROOT if smoke else RUN_ROOT)
 assert len(plan)==(1 if smoke else20)
 assert len(plan[0]['outputs'])==(1 if smoke else2)
 assert c.base.run_job.__globals__['subprocess'].__class__ is c.Routes
 assert c.base.protocol()['status']=='FROZEN'
 print('ENGINE_WIRING_OK_NO_EXECUTION')
c.base.main=halt
if '--smoke' in sys.argv:c.main()
else:
 p=c.protocol()
 with patch('pathlib.Path.exists',return_value=True),patch('pathlib.Path.glob',return_value=[SMOKE_ROOT/'metrics'/'fake.json']),patch('pathlib.Path.read_text',return_value='{"technical_validation":"PASS"}'):
  with patch.object(c,'verify',return_value=p),patch.object(c,'protocol',return_value=p):c.main()
assert not RUN_ROOT.exists() and not SMOKE_ROOT.exists()
'''
        # Add spaces to keep the compact embedded conditional valid Python.
        code=code.replace('else20','else 20').replace('else2','else 2')
        for flags in (['--smoke'],[]):
            r=subprocess.run(['/usr/bin/python3','-c',code,*flags],cwd=ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr[-2000:]);self.assertIn('ENGINE_WIRING_OK_NO_EXECUTION',r.stdout)
    def test_same_twenty_blocks_exact_frozen_jitter(self):
        from .config import runtime_config,SCENES,INDICES
        from nomad_phase38.config import runtime_config as frozen
        for s in SCENES:
            for i in INDICES:
                c=runtime_config('OURS-N',i,90,s);b=frozen('OURS',i,90,s)
                self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase40p')},b)
    def test_launch_arguments_stop_before_any_process_or_directory(self):
        from . import campaign,launch,config
        class Stop(Exception):pass
        for smoke in (False,True):
            plan=campaign.jobs(config.SMOKE_ROOT if smoke else config.RUN_ROOT,smoke)
            self.assertEqual(len(plan),1 if smoke else 20)
            for j in plan:
                fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**k:self.fail('Process forbidden')))
                fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Stop())
                argv=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]+(['--smoke'] if smoke else [])
                with patch.object(sys,'argv',argv),self.assertRaises(Stop):fn()
        self.assertFalse(config.RUN_ROOT.exists());self.assertFalse(config.SMOKE_ROOT.exists())
    def test_decision_fixed_thresholds_and_pairs(self):
        from .report import analyze
        from .config import SCENES,INDICES
        rows=[]
        for i,(s,k) in enumerate((s,k) for s in SCENES for k in INDICES):
            for m in ('OURS-N','OURS-DETOUR','OURS','ASTAR+EC'):
                rows.append(dict(method=m,scene=s,index=k,technical_validation='PASS',success=i<(17 if m=='OURS-N' else 14),collision=False,goal_time_s=50.,distance_m=8.))
        d,tests,pp=analyze(rows);self.assertEqual(d['pilot_label'],'PILOT_OK');self.assertEqual(d['graph_label'],'GRAPH_GAIN');self.assertEqual(len(tests),6)
        self.assertEqual(analyze(rows[1:])[0]['pilot_label'],'NOT_EVALUATED')
    def test_report_fake_data(self):
        from .report import generate
        from .config import SCENES,INDICES
        base=[]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,(s,k) in enumerate((s,k) for s in SCENES for k in INDICES):
                r=dict(method='OURS-N',scene=s,index=k,technical_validation='PASS',success=True,collision=False,goal_time_s=40.,distance_m=8.)
                (root/'metrics'/f'{i}.json').write_text(json.dumps(r))
                base.extend(dict(r,method=m,success=i<14) for m in ('OURS-DETOUR','OURS','ASTAR+EC'))
            doc=generate(root,root/'results',root/'report.md',base)
            self.assertIn('GRAPH_GAIN',doc.read_text());self.assertTrue((root/'results/paired.csv').exists())


if __name__=='__main__':unittest.main()
