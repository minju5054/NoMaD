import math,time,unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase15b.depth import Snapshot
from nomad_isaac.common import integrate_se2
from .graph import HandoffGraph,solve,backward,certificate
from .tracking import clip_command,predict,apply_tick,TimedFollower
from .alignment import NoAlignment
from .config import angular_limit

class Field(Snapshot):
    def __init__(self,affine=False):
        self.origin=np.array([-2.,-2.]);self.h=.01;self.radius=.09;self.error_bound=self.h/np.sqrt(2)
        self.values=np.ones((401,401));self.occupied=np.zeros((401,401),bool);self.observed=np.ones_like(self.occupied);self.metadata={};self.affine=affine
    def query(self,p):
        p=np.asarray(p);g=np.zeros_like(p);g[:,1]=.03 if self.affine else 0.
        return (.13+.03*p[:,1] if self.affine else np.ones(len(p))),g

def central(fn,x):
    out=[]
    for i in range(len(x)):
        d=np.zeros_like(x);d[i]=1e-6;out.append((np.atleast_1d(fn(x+d))-np.atleast_1d(fn(x-d)))/2e-6)
    return np.array(out).T

class HandoffTests(unittest.TestCase):
    def test_analytic_objective_constraints_boundary(self):
        g=HandoffGraph([0.,0.,.1],[.15,.1],[[0.,0.],[.3,.05],[.7,.1]],Field(True),2.)
        x=g.initial();x[6]+=.012;x[10]+=.006
        np.testing.assert_allclose(g.objective(x)[1],central(lambda z:g.objective(z)[0],x)[0],atol=1e-5,rtol=1e-6)
        np.testing.assert_allclose(g.constraints(x)[1],central(lambda z:g.constraints(z)[0],x),atol=1e-5,rtol=1e-6)
        np.testing.assert_allclose(g.boundary(x)[1],central(lambda z:g.boundary(z)[0],x),atol=1e-5,rtol=1e-6)
    def test_boundary_pose_speed_and_yaw_rate_exact(self):
        for vw in ([.1,.2],[0.,0.]):
            g=HandoffGraph([.1,.2,.3],vw,[[.1,.2],[.4,.3],[.7,.3]],Field(),2.)
            x=g.initial();r=g.result(x)
            self.assertLess(np.max(abs(g.boundary(x)[0])),1e-12)
            self.assertLess(r['start_pose_error'],1e-12);self.assertLess(r['start_speed_error'],1e-12);self.assertLess(r['start_omega_error'],1e-12)
    def test_hard_rows_reject_excess_rates(self):
        g=HandoffGraph([0,0,0],[.1,0],[[0,0],[.8,0]],Field(),2.);x=g.initial();x[30:]=.1;x[8]=.5
        self.assertLess(g.constraints(x)[0].min(),0.)
    def test_final_feedback_clipping_and_continuity(self):
        previous=[.1,.1]
        for raw in ([3.,8.],[-5.,-7.],[.1,.1]):
            out,flags=clip_command(raw,previous,2.)
            self.assertTrue(0<=out[0]<=.3);self.assertLessEqual(abs(out[1]),.4)
            self.assertLessEqual(abs(out[0]-previous[0]),.5/9+1e-12);self.assertLessEqual(abs(out[1]-previous[1]),2/9+1e-12)
        r=dict(poses=[[0,0,0],[.1,0,0],[.2,0,0]],dt=[1.,1.],speed=[.1,.1],omega=[0.,0.],allow_rotation=False)
        c=TimedFollower(r,0,2.);out,d=c.control([0,0,0],.1);self.assertEqual(out,(.1,0.));self.assertFalse(d['any_clipped'])
    def test_rotation_ninety_rule(self):
        self.assertFalse(backward([[0,0],[0,.2]],[0,0,0]));self.assertTrue(backward([[0,0],[-.2,.01]],[0,0,0]))
    def test_timeout_is_not_accepted(self):
        r=solve([0,0,0],[.1,0],[[0,0],[.5,0]],Field(),2.,started=time.perf_counter()-1)
        self.assertFalse(r['accepted']);self.assertEqual(r['disposition'],'TIMEOUT')
    def test_free_scene_solution_limits(self):
        r=solve([0,0,0],[.15,0],[[0,0],[.6,0]],Field(),2.)
        self.assertTrue(r['accepted'],r)
        self.assertLessEqual(r['max_abs_w'],.4+1e-7);self.assertLessEqual(r['max_abs_a'],.5+1e-7)
        self.assertLessEqual(r['max_abs_angular_acceleration'],2.+1e-7)
        self.assertLess(r['start_speed_error'],1e-7);self.assertLess(r['start_omega_error'],1e-7)
    def test_certificate_rejects_blocked_path(self):
        f=Field();f.occupied[200,220]=True;f.values[:]=.01
        with patch.object(f,'query',lambda p:(np.full(len(p),.01),np.zeros_like(p))):self.assertFalse(certificate([[0,0],[.5,0]],f)['passed'])
    def test_prediction_uses_same_controller_and_tick(self):
        c=NoAlignment();c.replace_path([[0,0],[1,0]],[0,0,0],.1)
        r=predict([0,0,0],[.1,0],c,0)
        self.assertEqual(r['apply_tick'],16);self.assertEqual(apply_tick(1),16)
        q=np.zeros(3);v=.1
        for i in range(16):
            if i%8==0:(v,w),_=c.control(q,v)
            q=integrate_se2(q,v,w,1/72)
        np.testing.assert_array_equal(q,r['pose'])
    def test_plant_limit_selection(self):
        self.assertEqual(angular_limit({'plant_alpha':'inf'}),(2.,'NO_FINITE_PLANT_LIMIT_FALLBACK_2'))
        self.assertEqual(angular_limit({'plant_alpha':1.}),(1.,'EXISTING_FINITE_PLANT_LIMIT'))
    def test_failure_falls_back_without_changing_R2_R3(self):
        from .handoff import HExecution
        from .runtime import NAExecution
        o=object.__new__(HExecution);events=[];o.hrecord=lambda e,**kw:events.append((e,kw))
        job=dict(job_id=4,id=5,path=[[0,0],[1,0]])
        with patch.object(NAExecution,'new_path') as install:
            o.fallback_h(job,SimpleNamespace(),{'simulation_time_s':2.},'CERTIFICATE_FAILURE')
            self.assertEqual(install.call_args.args[-1],'SAFE');self.assertEqual(events[0][1]['reason'],'CERTIFICATE_FAILURE')

if __name__=='__main__':unittest.main()
