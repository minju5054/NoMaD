import copy,json,tempfile,threading,time,unittest,multiprocessing as mp
from pathlib import Path
import numpy as np
from nomad_isaac.common import integrate_se2,ROOT
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_phase23.runtime import managed_pool
from nomad_phase20d.pool import initialize,ping
from nomad_phase19r.test_repair import synthetic
from .live import ControlState,POLICIES,DecisionGraphExecution,stop_result
from types import SimpleNamespace
from nomad_phase17.recovery import Recovery
from .online_worker import Worker
from .online_pool import solve_job
from .online_config import runtime_config


def result(B=(0,0,0)):
    q=np.c_[np.linspace(0,1.5,11),np.zeros((11,2))];q[:,:2]+=np.asarray(B)[:2]
    return dict(accepted=True,output_type='FEASIBLE',poses=q.tolist(),path=q[:,:2].tolist(),dt=[.5]*10)

class Tests(unittest.TestCase):
    def test_fake_report_and_registered_labels(self):
        from .online_report import generate,decision
        c=dict(scene='L2',success=2,collision=0,min_clearance_median_m=.1,omega_saturation_median=.4)
        self.assertEqual(decision(dict(c,success=3,min_clearance_median_m=.14),c)['label'],'PILOT_G_HELPS')
        self.assertEqual(decision(dict(c,success=0),c)['label'],'PILOT_G_HURTS')
        self.assertEqual(decision(c,c)['label'],'PILOT_G_INCONCLUSIVE')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();doc=root/'report.md';doc.write_text('# Preserved offline check\n')
            for scene in ('L2','SLW'):
                for index in range(131,135):
                    for method in ('G','C0','C1'):
                        value=dict(scene=scene,index=index,method=method,technical_validation='PASS',success=True,classification='SUCCESS',collision=False,corridor=False,box_passage=scene=='L2',minimum_clearance_m=.2,omega_saturation_fraction=.1,output=str(root))
                        (root/'metrics'/f'{scene}_{index}_{method}.json').write_text(json.dumps(value))
            result=generate(root,root/'out',doc,figures=False);self.assertEqual(len(result),2)
            self.assertIn('Preserved offline check',doc.read_text());self.assertTrue((root/'out/paired.csv').exists())
    def test_no_output_transitions_once_and_ignores_old_mode_jobs(self):
        e=object.__new__(DecisionGraphExecution);e.clock=ControlState(POLICIES[0]);e.epoch=0;e.mode='NORMAL';e.recovery=Recovery();e.events_seen=[]
        e.record_event=lambda event,**kw:e.events_seen.append((event,kw))
        e.worker=SimpleNamespace(result=lambda *_:None)
        e.jobs=[dict(job_id=0,epoch=0,due_tick=36,dispatch_tick=0,dispatch_ns=time.monotonic_ns(),fresh_id=1,prediction=dict(B_pred=[0,0,0]),mode='NORMAL',reason='FRESH')]
        entered=[];e.enter_detour=lambda *args:entered.append(args)
        e.apply_due(SimpleNamespace(pose=np.zeros(3)),35);self.assertEqual(len(entered),0)
        e.apply_due(SimpleNamespace(pose=np.zeros(3)),36);self.assertEqual(len(entered),1);self.assertEqual(e.clock.plan['output_type'],'STOP')
        self.assertEqual(e.events_seen[-1][1]['application_delay_s'],.5)
        e.jobs=[dict(job_id=1,epoch=-1,due_tick=36)];e.apply_due(SimpleNamespace(pose=np.zeros(3)),36);self.assertEqual(e.events_seen[-1][0],'MODE_SUPERSEDED')
    def test_braking_and_rotation_preserve_executor_limits(self):
        ctl=ControlState(POLICIES[0]);ctl.last_command=[.3,0.];ctl.install(stop_result(),0)
        for tick in range(0,64,8):
            prior=ctl.last_command[0];ctl.update(np.zeros(3),tick);self.assertLessEqual(abs(ctl.last_command[0]-prior),.5/9+1e-12)
        self.assertEqual(ctl.last_command[0],0.)
        rec=Recovery();rec.decision('STOP_WAIT');rec.decision('STOP_WAIT');self.assertTrue(rec.eligible(0));rec.start(SimpleNamespace(query=lambda p:(np.ones(len(p)),np.zeros_like(p))),[0,.4,0]);pose=np.array([0.,.4,0.]);initial=pose.copy()
        while rec.state=='RECOVER_ROTATE':
            v,w=rec.interval_command();pose=integrate_se2(pose,v,w,1/72);rec.integrated(w)
        np.testing.assert_array_equal(pose[:2],initial[:2]);self.assertEqual(rec.count,1)
    def test_prediction_matches_same_live_executor(self):
        for policy in POLICIES:
            c=ControlState(policy);c.install(result(),0);pose=np.zeros(3);c.update(pose,0)
            for t in range(1,25):pose=integrate_se2(pose,*c.last_command,1/72);c.update(pose,t)
            predicted=c.predict(pose,24);other=copy.deepcopy(c);actual=pose.copy()
            for t in range(25,61):
                actual=integrate_se2(actual,*other.last_command,1/72)
                if t<60:other.update(actual,t)
            np.testing.assert_array_equal(actual,predicted['B_pred']);self.assertEqual(len(predicted['speeds']),36)
    def test_prediction_includes_waypoint_expiration(self):
        c=ControlState(POLICIES[0]);c.install(result(),0);c.last_command=[.3,0.];c.last_tick=16;c.next_tick=24
        pose=np.zeros(3);prediction=c.predict(pose,24,valid_until_tick=32);other=copy.deepcopy(c);other.update(pose,24,True)
        for tick in range(25,61):
            pose=integrate_se2(pose,*other.last_command,1/72)
            if tick<60:other.update(pose,tick,tick<=32)
        np.testing.assert_array_equal(pose,prediction['B_pred']);self.assertLess(prediction['previous_vw'][0],.3)
    def test_application_phase_choices_and_acceleration(self):
        for policy in POLICIES:
            c=ControlState(policy);c.last_tick=32;c.next_tick=40;c.last_command=[.1,0.];c.install(result(),36)
            due=40 if policy=='PATH_AT_0P5_NEXT_9HZ' else 36;self.assertEqual(c.next_tick,due)
            changed=c.update([0,0,0],36);self.assertEqual(changed,policy=='COMMAND_AT_0P5_RESET_9HZ')
            if changed:self.assertLessEqual(abs(c.last_command[0]-.1),.5*4/72+1e-12)
    def test_anytime_late_final_does_not_erase_available_update(self):
        w=object.__new__(Worker);w.error=None;w.process=type('Process',(),dict(poll=lambda self:None))();w.lock=threading.Lock();w.latest={0:[dict(parent_received_ns=20,kind='UPDATE'),dict(parent_received_ns=80,kind='FINAL')]}
        self.assertEqual(w.result(0,50)['parent_received_ns'],20);self.assertEqual(w.result(0,100)['parent_received_ns'],80)
    def test_scene_hash_reuse_seed_and_socket_lengths(self):
        sockets=[]
        for scene in ('L2','SLW'):
            for method in ('G','C0','C1'):
                c=runtime_config(method,134,level=scene);self.assertEqual(c['seed_offset'],1340000)
                self.assertEqual('dynamic_obstacle' in c,scene=='L2');self.assertEqual(c['integration_hz'],72);self.assertEqual(c['controller_hz'],9)
                sock=socket_path_for_run(ROOT.parent/f'artifacts/isaac6/phase24_online_01/main/{scene}_134_{method}');self.assertLess(validate_socket_path(sock),100);sockets.append(str(sock))
        self.assertEqual(len(set(sockets)),6)
    def test_streaming_pool_returns_graph_results(self):
        ctx=mp.get_context('spawn');queue=ctx.Queue()
        with tempfile.TemporaryDirectory() as tmp,managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
            futures=[pool.submit(ping) for _ in range(4)]
            for _ in range(4):queue.get(timeout=30)
            for f in futures:f.result()
            file=Path(tmp)/'field.npz';synthetic(True).save(file);q=np.c_[np.linspace(0,1,8),np.full(8,.4)]
            case=dict(B=[0,.4,0],previous_vw=[0,0],tick=0,fresh_id=0,samples_world=np.repeat(q[None],8,0).tolist(),old_path=None,memory_sets=[],snapshot_file=str(file))
            job=dict(job_id=0,dispatch_ns=time.monotonic_ns(),case=case,prediction=dict(B_pred=[0,.4,0],previous_vw=[0,0]),mode='NORMAL',u_ref=None);messages=[];solve_job(pool,job,messages.append)
            self.assertTrue(messages);self.assertFalse(any(m['kind']=='ERROR' for m in messages));self.assertEqual(messages[-1]['kind'],'FINAL')
            self.assertTrue(any(m['result']['accepted'] for m in messages));self.assertTrue(all(m['result']['late_results_used'] is False for m in messages))
if __name__=='__main__':unittest.main()
