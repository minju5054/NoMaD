import json,os,signal,subprocess,sys,tempfile,time,unittest,multiprocessing as mp
from pathlib import Path
import numpy as np
from nomad_phase19r.test_repair import synthetic
from .runtime import Journal,reconcile,wall_limit,ExecutionTimeout,ExecutionGuardError,managed_pool

def bad_worker():raise ValueError('worker exception sentinel')
def sleeping_worker():time.sleep(10)

class Tests(unittest.TestCase):
    def test_json_list_path_exact_clearance_regression(self):
        from .run import method_record
        q=np.c_[np.linspace(0,1,11),np.full(11,.4),np.zeros(11)]
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'field.npz';synthetic(True).save(file)
            c=dict(case_id='TEST',group='static',scene='TEST',index=0,B=[0,.4,0],previous_vw=[.2,0],old_path=None,snapshot_file=str(file),samples_world=np.repeat(q[None,:,:2],8,0).tolist(),evaluation_direction=[1,0],oracle_config=dict(start_pose=[0,.4,0],goal_pose=[1,.4,0],agent_radius_m=.09,obstacles=[],corridor=dict(xmin=-1,xmax=2,half_width=1)))
            p=dict(accepted=True,path=q[:,:2].tolist(),poses=q.tolist(),dt=[.5]*10,active_candidate=0,disposition='FEASIBLE',compute_s=.01)
            result=method_record(c,'U00',p,dict(policy=dict(rotation_policy='graph_rotation',short_policy='retain')))
            self.assertGreater(result['row']['depth_clearance_m'],0);self.assertIn('EXACT_CLEARANCE',result['row']['execution_timing_s'])
    def test_exception_and_dead_pid_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(ValueError,'failure sentinel'):
                with Journal(root) as j:j.update('ROLLOUT','TS0000','U03');raise ValueError('failure sentinel')
            state=reconcile(root/'state.json');self.assertEqual(state['status'],'FAILED');self.assertEqual(state['combination'],'U03');self.assertEqual(state['error']['type'],'ValueError');self.assertIsNone(state['pid'])
            (root/'state.json').write_text(json.dumps(dict(pid=99999999,stage='TRAINING',case='TS0000')))
            self.assertEqual(reconcile(root/'state.json')['status'],'FAILED')
    def test_signal_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            code="from nomad_phase23.runtime import Journal,ExecutionSignal\nimport time,sys\ntry:\n with Journal(sys.argv[1]) as j:\n  j.update('ROLLOUT','TS0000','U00');time.sleep(30)\nexcept ExecutionSignal as e:sys.exit(128+e.signum)\n"
            p=subprocess.Popen([sys.executable,'-c',code,tmp],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                until=time.monotonic()+5
                while not (Path(tmp)/'state.json').exists() and time.monotonic()<until:time.sleep(.01)
                p.send_signal(signal.SIGTERM);self.assertEqual(p.wait(timeout=5),143)
                s=json.loads((Path(tmp)/'state.json').read_text());self.assertEqual(s['status'],'FAILED');self.assertEqual(s['error']['signal'],15)
            finally:
                if p.poll() is None:p.kill();p.wait()
    def test_worker_exception_and_watchdog_propagate(self):
        ctx=mp.get_context('spawn')
        with self.assertRaisesRegex(ValueError,'worker exception sentinel'):
            with managed_pool(max_workers=1,mp_context=ctx) as pool:pool.submit(bad_worker).result(timeout=5)
        started=time.monotonic()
        with self.assertRaises(ExecutionTimeout):
            with managed_pool(max_workers=1,mp_context=ctx) as pool:
                future=pool.submit(sleeping_worker)
                with wall_limit(.05,'TEST_SOLVE'):future.result()
        self.assertLess(time.monotonic()-started,3.)
    def test_rotation_guard_and_normal_baseline_identity(self):
        from .rollout import GraphFollower,baseline_guarded,baseline_simulate,unified_simulate
        q=np.c_[np.r_[0,0,np.linspace(.1,1,9)],np.zeros(11),np.r_[0,np.full(10,.2)]];dt=np.full(10,.5)
        ctl=GraphFollower(q,dt)
        with self.assertRaises(ExecutionGuardError):
            for _ in range(30):ctl.control(np.zeros(3),0.)  # Frozen pose cannot reach heading.
        path=np.c_[np.linspace(0,1,11),np.linspace(0,.2,11)]
        a=baseline_guarded([0,0,0],path,.2);b=baseline_simulate([0,0,0],path,.2)
        np.testing.assert_array_equal(a['poses'],b['poses']);self.assertLess(len(a['speeds']),a['tick_cap'])
        old=subprocess.check_output(['git','show','4916cbf:research/nomad_phase23/rollout.py'],text=True)
        namespace=dict(__name__='nomad_phase23._old_rollout',__package__='nomad_phase23');exec(compile(old,'frozen_rollout','exec'),namespace)
        case=dict(B=[0.,0.,0.],previous_vw=[0.,0.]);plan=dict(accepted=True,poses=q.tolist(),dt=dt.tolist());policy=dict(rotation_policy='graph_rotation')
        a=unified_simulate(case,plan,policy);b=namespace['unified_simulate'](case,plan,policy)
        np.testing.assert_array_equal(a['poses'],b['poses'])

if __name__=='__main__':unittest.main()
