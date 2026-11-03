import time,tempfile,multiprocessing as mp,unittest
from pathlib import Path
import numpy as np
from nomad_phase23o2.test_u2 import FreeField,fd
from nomad_phase23o2.graph import U2Graph
from nomad_phase23.runtime import managed_pool
from nomad_phase20d.pool import initialize,ping
from nomad_phase19r.test_repair import synthetic
from nomad_phase23.rollout import GraphFollower
from .graph import U3Graph,intent_direction,iterate_candidate,choose_output,plan


def make(w7=1.,distance=.4,field=None):
    q=np.c_[np.linspace(0,distance,11),np.zeros(11)];candidates=np.repeat(q[None],8,0)
    weights=dict(time=1.,goal=1.,curvature=.01,u2=dict(c=1.,T_m=1.,ages_s=[0.]*8,w7=w7))
    args=([0,0,0],.2,candidates,.08,field or FreeField(),weights,time.monotonic_ns()+30_000_000_000)
    g=U3Graph(*args);return g,g.initial(q),args

class Tests(unittest.TestCase):
    def test_f7_gradient_and_only_added_factor(self):
        g,x,args=make(w7=2.);base=U2Graph(*args);x[1::3][:9]+=.005*np.arange(9)
        value,j=g.objective(x);v0,j0=base.objective(x);f,jf,_,_=g.f7(x)
        self.assertAlmostEqual(value-v0,f,places=8);np.testing.assert_allclose(j-j0,jf,atol=1e-9)
        self.assertLess(np.max(np.abs(j-fd(lambda z:g.objective(z)[0],x))),1e-5)
        np.testing.assert_array_equal(g.constraints(x)[0],base.constraints(x)[0])
    def test_intent_is_aged_candidate_endpoint_direction(self):
        q=np.zeros((3,11,2));q[0,-1]=[1,0];q[1,-1]=[0,1];q[2,-1]=[-.049,0]
        d,info=intent_direction(q,[0,1,0],1.);expected=np.array([1,np.exp(-1)]);expected/=np.linalg.norm(expected)
        np.testing.assert_allclose(d,expected);self.assertEqual(info['valid_candidates'],2)
        q[:,-1]=0;d,info=intent_direction(q,[0,0,0],1);self.assertFalse(info['enabled'])
        q=np.zeros((2,11,2));q[:,-1]=[[1,0],[-1,0]];self.assertFalse(intent_direction(q,[0,0],1)[1]['enabled'])
    def test_tolerance_never_relaxes_f2(self):
        g,x,_=make();x[30:]=.125
        self.assertLess(g.constraints(x)[0][21:].min(),0.)
        candidate=iterate_candidate(g,x);self.assertIsNotNone(candidate);self.assertAlmostEqual(candidate['v_max'],.32)
        fast=x.copy();fast[30:]=.12;self.assertIsNone(iterate_candidate(g,fast))
        angular=x.copy();angular[2]=.441*.125;self.assertIsNone(iterate_candidate(g,angular))
        dt=x.copy();dt[30]=1.1001;self.assertIsNone(iterate_candidate(g,dt))
        class Tight(FreeField):
            def query(self,q):return np.full(len(q),.024),np.zeros((len(q),2))
        bad,z,_=make(field=Tight());z[30:]=.125;self.assertIsNone(iterate_candidate(bad,z))
    def test_last_iterate_and_feasible_precedence(self):
        def row(cost):return dict(cost=cost,ready_ns=10,output_type='KINEMATIC_TOLERATED')
        delivery=dict(selected=dict(cost=10,index=0),latest={0:dict(last_candidate=row(1),received_ns=20)})
        self.assertEqual(choose_output(delivery,100)['output_type'],'FEASIBLE')
        delivery['selected']=None;self.assertEqual(choose_output(delivery,100)['cost'],1)
        delivery['latest'][0]['last_candidate']=None;self.assertIsNone(choose_output(delivery,100))
        delivery['latest'][1]=dict(last_candidate=row(0),received_ns=101);self.assertIsNone(choose_output(delivery,100))
    def test_executor_clips_tolerated_speed(self):
        q=np.c_[np.linspace(0,.4,11),np.zeros((11,2))];ctl=GraphFollower(q,[.125]*10)
        (v,w),_=ctl.control([0,0,0],.3);self.assertLessEqual(v,.3);self.assertLessEqual(abs(w),.4)
    def test_four_worker_output_and_half_second_application(self):
        ctx=mp.get_context('spawn');queue=ctx.Queue()
        with tempfile.TemporaryDirectory() as tmp,managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
            futures=[pool.submit(ping) for _ in range(4)]
            for _ in range(4):queue.get(timeout=30)
            for f in futures:f.result()
            file=Path(tmp)/'snapshot.npz';synthetic(True).save(file);q=np.c_[np.linspace(0,1,8),np.full(8,.4)]
            c=dict(B=[0,.4,0],tick=0,previous_vw=[.2,0],samples_world=np.repeat(q[None],8,0).tolist(),old_path=q.tolist(),fresh_id=0,memory_sets=[],snapshot_file=str(file))
            result=plan(pool,c,dict(w7=.5,T_m=.5),dict(prediction_mode='existing_rollout'))
            self.assertIn(result['output_type'],('FEASIBLE','KINEMATIC_TOLERATED','STOP'));self.assertEqual(result['application_delay_s'],.5)
            self.assertTrue(result['direction_info']['enabled']);self.assertAlmostEqual(result['direction_world'][0],1.)
            if result['accepted']:np.testing.assert_allclose(result['poses'][0],result['B_pred'],atol=1e-12)


class GateTests(unittest.TestCase):
    def test_registered_selection_and_gate(self):
        from .report import select,gate
        def row(i,passage,stop,p95=.4,collision=0):return dict(index=i,settings={},collisions=collision,sudden_planned_passage_fraction=passage,stop_fraction=stop,static_progress_median=.5,p50=.2,p95=p95)
        winner,_=select([row(0,.2,.01),row(1,.5,.09),row(2,1.,0.,.501)])
        self.assertEqual(winner['index'],1)
        summary=[dict(group=g,method=m,planned_box_passage_fraction=.2 if m=='U3' else .25,collisions=0,stop_fraction=.1,compute_p95_s=.5) for g in ('ALL','sudden') for m in ('U3','C0')]
        self.assertEqual(gate(summary)['label'],'GO_ONLINE');summary[0]['stop_fraction']=.1001;self.assertEqual(gate(summary)['label'],'NO_GO')

if __name__=='__main__':unittest.main()
