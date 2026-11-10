import ast,copy,inspect,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase32o.test_exec_cert import field
from nomad_phase20.repair import RepairGraphR2,initialize
from nomad_phase40p.schedule import application_tick,predict
from nomad_phase32.policy import CappedNA
from nomad_isaac.common import integrate_se2
from . import config,launch,campaign,runtime,report
from .graph import ReconstructionGraph,solve_sample,select

class FakeWorker:
    def __init__(self):self.jobs=[];self.results=[]
    def submit(self,job,field):self.jobs.append(copy.deepcopy(job))
    def poll(self):return self.results.pop(0) if self.results else None
    def close(self):pass

def map_field():
    f=field();f.observed=np.ones_like(f.occupied);f.metadata={'frame_id':0,'sim_s':0.,'publication_monotonic_ns':0};return f

def fresh(index=0,t=0.):
    bank=np.array([np.c_[np.linspace(.1,1.4,8),np.full(8,i*.002)] for i in range(8)])
    return dict(id=index,observation_sim_s=t-.75,observation_pose=[0,0,0],received_monotonic_ns=0,overnight_metric_samples=bank.tolist())

class Tests(unittest.TestCase):
    def test_graph_gradient_original_constraints_and_short_old_factor(self):
        f=map_field();B=[0,0,0];q,_=initialize([[0,0],[.4,.1],[1,.15]],B);old=[[0,.05],[.6,.05],[1.2,.05]]
        g=ReconstructionGraph(q,B,f,old);base=RepairGraphR2(q,B,f);x=g.initial+np.linspace(-.001,.002,14)
        val,grad=g.objective(x);eps=1e-6;numeric=[]
        for i in range(14):
            h=np.zeros(14);h[i]=eps;numeric.append((g.objective(x+h)[0]-g.objective(x-h)[0])/(2*eps))
        np.testing.assert_allclose(grad,numeric,atol=1e-5,rtol=0)
        for a,b in zip(g.constraints(x),base.constraints(x)):np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(g.bounds.lb,base.bounds.lb);np.testing.assert_array_equal(g.bounds.ub,base.bounds.ub)
        self.assertEqual(g.certificate(g.points(x)),base.certificate(g.points(x)))
        none=ReconstructionGraph(q,B,f,None);self.assertEqual(none.objective(x)[0],base.objective(x)[0])
        short=ReconstructionGraph(q,B,f,[[0,0],[.1,0]]);self.assertEqual(np.count_nonzero(short.old_weights[1:]),0)
        self.assertEqual(g.old_weights[0],1);self.assertTrue(np.all(g.old_weights[g.q.shape[0]-2:]==0))
        result=solve_sample([[0,0],[.5,0],[1,0]],B,f,None);self.assertTrue(result['accepted']);json.dumps(result,allow_nan=False)

    def test_hold_core_has_no_age_expiry_and_preserves_fresh(self):
        core=runtime.HoldCore([0,0,0]);core.receive({'id':0,'received_monotonic_ns':0},[1,0])
        first,switch=core.control(0,0);self.assertIsNotNone(switch)
        later,switch=core.control(800,10_000_000_000);self.assertTrue(later['valid']);self.assertFalse(later['new_timeout']);self.assertIsNone(switch);self.assertEqual(core.expired_ids,set())
        core.receive({'id':1,'received_monotonic_ns':11_000_000_000},[1,.1]);later,switch=core.control(808,11_000_000_001);self.assertEqual(switch['id'],1)
        json.dumps(later,allow_nan=False)

    def test_prediction_is_frozen_controller_integrator_and_exact_target(self):
        c=CappedNA();pose=np.array([0.,0.,.1]);c.replace_path([[0,0],[.5,.1],[1.5,.2]],pose,.1)
        vw,_=c.control(pose,.1);other=copy.deepcopy(c);target=application_tick(16);r=predict(c,pose,vw,16,target);v,w=vw
        for tick in range(16,target):
            if tick>16 and tick%8==0:(v,w),_=other.control(pose,v)
            pose=integrate_se2(pose,v,w,1/72)
        np.testing.assert_array_equal(pose,r['pose']);self.assertEqual(target,72);self.assertEqual(len(r['commands']),56)

    def setup_execution(self,out,method='GRAPH-REC'):
        worker=FakeWorker() if method=='GRAPH-REC' else None;e=runtime.Execution(method,out,worker=worker);f=map_field();e.depth_maps=SimpleNamespace(snapshot=lambda:f)
        core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.,latest={'id':0},applied_id=0)
        return e,worker,core
    def test_immediate_cut_dispatch_then_minimum_cost_ec_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            e,w,core=self.setup_execution(Path(td));now=time.monotonic_ns();refresh=dict(simulation_time_s=0.,monotonic_ns=now,valid=True)
            try:
                e.apply(core,refresh,fresh());self.assertEqual(e.path_kind,'SAFE');self.assertEqual(len(w.jobs),1)
                job=w.jobs[0];self.assertEqual(job['dispatch_tick'],0);self.assertEqual(job['apply_tick'],56);self.assertIsNone(job['old_path'])
                np.testing.assert_allclose(job['dispatch_vw'],[core.v,core.w]);self.assertGreater(job['B'][0],core.pose[0])
                B=np.array(job['B']);paths=[(B[:2]+np.c_[np.linspace(0,1,8),np.zeros(8)]).tolist()]*2
                w.results.append(dict(job_id=job['job_id'],parent_received_ns=now+1,selected_sample=1,results=[dict(accepted=True,objective=c,path=p) for c,p in zip((3.,1.),paths)]))
                original=e.follower.path.points.copy();e.apply(core,dict(simulation_time_s=48/72,monotonic_ns=now+100,valid=True),None)
                np.testing.assert_array_equal(e.follower.path.points,original)
                core.pose=B.copy();e.apply(core,dict(simulation_time_s=56/72,monotonic_ns=now+1000,valid=True),None)
                self.assertEqual(e.path_kind,'GRAPH_REC');self.assertEqual(e.active_sample,1);self.assertIsNone(e.rec_pending)
                records=[json.loads(s) for s in (Path(td)/'reconstruction.jsonl').read_text().splitlines()];r=next(x for x in records if x['event']=='RESULT')
                self.assertEqual(r['prediction_error_m'],0);self.assertTrue(r['applied']);self.assertEqual(r['tick'],56)
                for record in records:json.dumps(record,allow_nan=False)
            finally:e.close()

    def test_late_superseded_and_ec_failed_keep_current_cut(self):
        for case in ('LATE','SUPERSEDED','EC_REJECT'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as td:
                e,w,core=self.setup_execution(Path(td));now=time.monotonic_ns()
                try:
                    e.apply(core,dict(simulation_time_s=0.,monotonic_ns=now,valid=True),fresh());path=e.follower.path.points.copy();job=w.jobs[0]
                    if case!='LATE':w.results.append(dict(job_id=0,parent_received_ns=now+1,selected_sample=0,results=[dict(accepted=True,objective=0.,path=path.tolist())]))
                    if case=='EC_REJECT':e.ec_check=lambda *a,**kw:dict(passed=False,check_id=99)
                    switch=fresh(1,.5) if case=='SUPERSEDED' else None
                    # Inspect the scheduling hook alone: a newer chunk is
                    # separately immediately installed by the common parent.
                    e.poll_reconstruction(core,dict(simulation_time_s=56/72,monotonic_ns=now+100,valid=True),switch)
                    np.testing.assert_array_equal(path,e.follower.path.points);self.assertIsNone(e.rec_pending)
                    result=[json.loads(s) for s in (Path(td)/'reconstruction.jsonl').read_text().splitlines() if '"RESULT"' in s][-1]
                    self.assertEqual(result['disposition'],{'LATE':'TIMEOUT','SUPERSEDED':'SUPERSEDED','EC_REJECT':'EXEC_CERT_REJECT'}[case]);self.assertFalse(result['applied'])
                finally:e.close()

    def test_short_active_path_kept_on_exhaustion_both_methods(self):
        for method in config.METHODS:
            with tempfile.TemporaryDirectory() as td:
                e,_,core=self.setup_execution(Path(td),method);refresh=dict(simulation_time_s=0.,monotonic_ns=time.monotonic_ns(),valid=True)
                try:
                    e.ec_context=(core,refresh);e.ec_switch={'id':0,'observation_sim_s':-.75};p=np.array([[0,0],[.15,0]])
                    e.ec_samples[0]=dict(worlds=np.repeat(p[None],8,axis=0));e.new_path(p,core,refresh,0,'SAFE');e.ec_switch=None
                    profile=e.sp;e.ec_stop(refresh,'NORMAL_NO_EC_SAFE_CANDIDATE')
                    self.assertIs(e.sp,profile);self.assertEqual(e.mode,'KEEP_ACTIVE');self.assertTrue(e.hold_rejected)
                    e.ec_check=lambda *a,**kw:dict(passed=False,check_id=0);e.ec_stop(refresh,'NORMAL_NO_EC_SAFE_CANDIDATE')
                    self.assertIsNone(e.sp);self.assertEqual(e.mode,'STOP_WAIT');self.assertFalse(e.hold_rejected)
                finally:e.close()

    def test_four_worker_transport_v2_and_eight_candidates(self):
        from .worker import Worker
        from nomad_phase33p.storage import install
        from nomad_phase20d.recent import RecentSnapshot
        from nomad_phase39o3.test_maps import base_field
        install();f=base_field();f.occupied[:]=False;f.values[:]=5.;snap=RecentSnapshot(f,dict(frame_id=0,sim_s=0))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);worker=Worker(root)
            try:
                for i in range(2):worker.submit(dict(job_id=i,kind='REC',B=[0,0,0],old_path=None,dispatch_ns=time.monotonic_ns(),samples_world=[[[0,0],[.5,0],[1,0]]]*8),snap)
                results=[];deadline=time.monotonic()+30
                while len(results)<2 and time.monotonic()<deadline:
                    r=worker.poll()
                    if r is not None:results.append(r)
                    else:time.sleep(.01)
                self.assertEqual(len(results),2)
                for r in results:self.assertNotIn('error',r);self.assertEqual(len(r['results']),8);self.assertIsNotNone(r['selected_sample']);json.dumps(r,allow_nan=False)
                for f in (root/'reconstruction_jobs').glob('input_*.npz'):
                    with np.load(f) as z:self.assertNotIn('values',z.files)
                self.assertEqual(json.loads((root/'reconstruction_environment.json').read_text())['workers'],4)
            finally:worker.close()

    def test_hold_past_one_second_periodic_ec_and_all_records_json(self):
        for method in config.METHODS:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);e,w,_=self.setup_execution(root,method);core=runtime.HoldCore([0,0,0]);core.receive(fresh(),[1,0]);commands=[]
                try:
                    for tick in range(161):
                        before=core.pose.copy()
                        if tick:e.plant.integrate(core,tick)
                        e.integrate_record(before,core.pose)
                        refresh,switch=core.control(tick,10_000_000_000+round(tick/72*1e9))
                        if refresh is not None:
                            e.apply(core,refresh,switch);json.dumps(refresh,allow_nan=False)
                            if switch is not None:json.dumps(switch,allow_nan=False)
                            commands.append(refresh)
                    self.assertTrue(all(x['applied_command_source']!='WAYPOINT_TIMEOUT' for x in commands))
                    self.assertGreater(core.pose[0],.3);self.assertEqual(core.expired_ids,set())
                    self.assertIsNotNone(e.follower)
                finally:e.close()
                for file in root.glob('*.jsonl'):
                    for line in file.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
                checks=[json.loads(s) for s in (root/'exec_cert.jsonl').read_text().splitlines()]
                self.assertEqual([x['check_tick'] for x in checks if x['event']=='CHECK' and x['scope']=='PERIODIC'],[36,72,108,144])

    def test_forty_argument_checks_order_and_frozen_environment(self):
        from nomad_phase47c.config import runtime_config as old
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        class Boundary(Exception):pass
        plan=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(plan),40)
        for j in plan:
            scene,condition=config.split(j['scene']);c=config.runtime_config(j['method'],j['index'],90,j['scene']);before=old('OURS-DETOUR+HMM',j['index'],90,scene)
            self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase52p') and k!='run_id'},{k:v for k,v in before.items() if k!='run_id'})
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No launch')));fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            for out in j['outputs']:self.assertLess(validate_socket_path(socket_path_for_run(Path(out))),100)
            with patch.object(sys,'argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]),self.assertRaises(Boundary):fn()
            args=launch.Processes.route(['python','simulator.py','--level',j['scene'],'--delay','.75']);self.assertEqual(args[-1],'1.5' if condition=='D150' else '.75')
        code='''
from nomad_phase52p import campaign as c
from nomad_phase52p.config import RUN_ROOT
def halt():
 assert len(c.frozen.base.jobs(RUN_ROOT))==40
 assert c.frozen.base.run_job.__globals__['subprocess'].__class__ is c.Routes
c.frozen.base.main=halt
c.main()
assert not RUN_ROOT.exists()
'''
        p=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr[-2000:])
    def test_fake_report_no_navigation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir();doc=report.generate(root,root/'empty',root/'empty.md')
            self.assertEqual(json.loads((root/'empty/analysis.json').read_text())['completed'],0)
            baseline=json.loads((config.OUT/'preparation/baselines.json').read_text())
            for i,j in enumerate(config.registered_order()):
                s,k=config.split(j['scene']);b=next(r for r in baseline if r['historical_group']=='Phase47_D075' and r['scene']==s and r['index']==j['index'])
                r=dict(b,**j,base_scene=s,condition=k);r.pop('historical_group',None)
                (root/'metrics'/f'{i}.json').write_text(json.dumps(r))
            report.generate(root,root/'full',root/'full.md');self.assertEqual(json.loads((root/'full/analysis.json').read_text())['completed'],40)

if __name__=='__main__':unittest.main()
