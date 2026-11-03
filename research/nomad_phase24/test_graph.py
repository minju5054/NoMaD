import time,tempfile,unittest,multiprocessing as mp
from pathlib import Path
from unittest.mock import patch
import numpy as np
from nomad_phase23o2.test_u2 import FreeField,fd
from nomad_phase23.runtime import managed_pool
from nomad_phase20d.pool import initialize,ping
from nomad_phase19r.test_repair import synthetic
from nomad_phase20c.detour import DetourGraph,ANGLES
from .graph import GraphG,normal_inputs,fan_paths,plan

class Tests(unittest.TestCase):
    def test_both_mode_analytic_derivatives(self):
        q=np.c_[np.linspace(0,1.1,11),.05*np.sin(np.linspace(0,1,11))]
        for mode in ('NORMAL','DETOUR'):
            g=GraphG([0,0,0],.03,q[None],.08,FreeField(),dict(mode=mode,u_ref=[1.,0.]),time.monotonic_ns()+60_000_000_000)
            x=g.initial(q);x[30]=.37
            _,j=g.objective(x);self.assertLess(np.max(np.abs(j-fd(lambda z:g.objective(z)[0],x))),1e-5)
            h,k=g.constraints(x);self.assertEqual(len(h),51);self.assertLess(np.max(np.abs(k-fd(lambda z:g.constraints(z)[0],x))),1e-5)
    def test_detour_has_no_reference_or_goal_prior(self):
        q=np.c_[np.linspace(0,1.2,11),np.zeros(11)];p=q.copy();p[:,1]=.7
        args=([0,0,0],.2,None,.03,FreeField(),dict(mode='DETOUR',u_ref=[1.,0.]),time.monotonic_ns()+5_000_000_000)
        a=GraphG(*args[:2],q[None],*args[3:]);b=GraphG(*args[:2],p[None],*args[3:]);x=a.initial(q)
        self.assertEqual(a.objective(x)[0],b.objective(x)[0]);np.testing.assert_array_equal(a.objective(x)[1],b.objective(x)[1]);self.assertEqual(a.weights['goal'],0.)
    def test_freshest_safe_and_all_unsafe_selection(self):
        samples=np.repeat(np.c_[np.linspace(0,1,8),np.zeros(8)][None],8,0);case=dict(samples_world=samples,old_path=None)
        candidates=[dict(index=i,remaining_length_m=1-i*.1,safe=i in (1,2,3),clearance_m=i) for i in range(8)]
        with patch('nomad_phase24.graph.evaluate_samples',return_value=(None,dict(candidates=candidates))):
            r=normal_inputs(case,[0,0,0],None);self.assertEqual(r['selected_sample'],1);self.assertEqual(r['names'],['REFERENCE','SAFE_2','SAFE_3'])
        for row in candidates:row['safe']=False
        with patch('nomad_phase24.graph.evaluate_samples',return_value=(None,dict(candidates=candidates))):
            r=normal_inputs(case,[0,0,0],None);self.assertEqual(r['selected_sample'],0);self.assertTrue(r['all_unsafe']);self.assertEqual(len(r['starts']),1)
    def test_astar_old_excluded_and_fan_unchanged(self):
        samples=np.repeat(np.c_[np.linspace(0,.2,8),np.zeros(8)][None],8,0);c=dict(samples_world=samples,old_path=[[0,0],[1,0]],U_old_withheld_ASTAR=True)
        details=[dict(index=i,remaining_length_m=.2,safe=True) for i in range(8)]
        with patch('nomad_phase24.graph.evaluate_samples',return_value=(None,dict(candidates=details))):
            r=normal_inputs(c,[0,0,0],None);self.assertNotIn('OLD_REMAINDER',r['names']);self.assertTrue(all(not f['supplemented'] for f in r['candidate_flags']))
        field=FreeField();field.error_bound=field.h/np.sqrt(2)
        for angle,path in zip(ANGLES,fan_paths([0,0,0],[1,0])):np.testing.assert_array_equal(path,DetourGraph([0,0,0],[1,0],field,angle).initial_path)
    def test_shared_output_policy_and_half_second_prefix(self):
        ctx=mp.get_context('spawn');queue=ctx.Queue()
        with tempfile.TemporaryDirectory() as tmp,managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
            ff=[pool.submit(ping) for _ in range(4)]
            for _ in range(4):queue.get(timeout=30)
            for f in ff:f.result()
            file=Path(tmp)/'field.npz';synthetic(True).save(file);q=np.c_[np.linspace(0,1,8),np.full(8,.4)]
            c=dict(B=[0,.4,0],tick=0,previous_vw=[.2,0],samples_world=np.repeat(q[None],8,0).tolist(),old_path=q.tolist(),snapshot_file=str(file))
            for mode in ('NORMAL','DETOUR'):
                r=plan(pool,c,mode,[1.,0.],dict(prediction_mode='existing_rollout'));self.assertIn(r['output_type'],('FEASIBLE','KINEMATIC_TOLERATED','STOP'));self.assertTrue(r['accepted']);self.assertEqual(r['application_delay_s'],.5)
                if r['accepted']:np.testing.assert_allclose(r['poses'][0],r['B_pred'],atol=1e-12)
                self.assertLessEqual(len(r['initializations']),4 if mode=='NORMAL' else 7)

class GateTests(unittest.TestCase):
    def test_post_passage_never_satisfies_gate(self):
        from .report import gate
        rows=[]
        for group in ('STATIC','PRE_PASSAGE','PRE_SPAWN','ALREADY_PASSED'):
            for method in ('G','C0'):
                rows.append(dict(input_stage=group,method=method,oracle_collision=False,planned_box_passage=(method=='C0' and group=='PRE_PASSAGE') or group=='ALREADY_PASSED',output_type='STOP' if group=='ALREADY_PASSED' else 'FEASIBLE',compute_s=9. if group=='ALREADY_PASSED' else .1))
        for scope,n in [('STATIC_AND_PRE_PASSAGE',2),('PRE_PASSAGE_ONLY',1)]:
            result=gate(rows,scope);self.assertEqual(result['label'],'NO_GO');self.assertEqual(result['stop_timing_n'],n)
            self.assertFalse(result['conditions']['passage']);self.assertTrue(result['conditions']['stop']);self.assertTrue(result['conditions']['timing'])

if __name__=='__main__':unittest.main()
