import unittest
import numpy as np
from nomad_phase19r.repair import RepairGraph,initialize
from nomad_phase19r.test_repair import synthetic
from nomad_phase19s.srg import simulate
from nomad_phase17.config import scene
from .repair import RepairGraphR2,split_arclength,solve_sample
from .execution import SPAlignment,rollout


class Affine:
    error_bound=.01/np.sqrt(2)
    def query(self,p):return .01+.15*p[:,0]+.20*p[:,1],np.tile([.15,.20],(len(p),1))
    def exact_clearance(self,p):return float(self.query(p)[0].min())


class Tests(unittest.TestCase):
    def test_r2_zone_and_analytic_jacobian(self):
        B=[.003,.004,.17];xy=np.c_[np.linspace(.003,.733,8),.004+.08*np.linspace(0,.73,8)**2]
        q,_=initialize(xy,B);g=RepairGraphR2(q,B,Affine());base=RepairGraph(q,B,Affine());x=g.initial.copy();x[3]+=.003
        thresholds,s=g.thresholds(x);self.assertTrue(np.any(s<=.30) and np.any(s>.30))
        np.testing.assert_allclose(g.constraints(x)[0][63:],base.constraints(x)[0][63:],atol=0,rtol=0)
        np.testing.assert_allclose(g.constraints(x)[0][:63]-base.constraints(x)[0][:63],.025-thresholds,atol=1e-15,rtol=0)
        for f in (g.residual_jacobian,g.constraints):
            _,j=f(x);fd=np.column_stack([(f(x+e*1e-7)[0]-f(x-e*1e-7)[0])/(2e-7) for e in np.eye(14)])
            np.testing.assert_allclose(j,fd,atol=1e-5,rtol=0)
        np.testing.assert_array_equal(g.residual_jacobian(x)[0],base.residual_jacobian(x)[0])

    def test_certificate_splits_continuous_path(self):
        p=np.c_[np.linspace(0,.7,8),np.zeros(8)];g=RepairGraphR2(p,[0,0,0],Affine())
        near,far=split_arclength(p);np.testing.assert_allclose(near[-1],[.3,0]);np.testing.assert_array_equal(near[-1],far[0])
        r=g.certificate(p);self.assertTrue(r['certificate_pass']);self.assertLess(r['near_exact_clearance_m'],.025)
        self.assertGreaterEqual(r['far_exact_clearance_m'],.025)
        self.assertTrue(solve_sample(p,[0,0,0],synthetic())['accepted'])

    def test_sp_path_replacement_and_braking_profile(self):
        c=SPAlignment();c.replace_path([[0,0],[.4,0],[.8,0]],[0,0,0],.3)
        (v,w),_=c.control([0,0,0],.3);self.assertEqual(v,.3);self.assertEqual(w,0.)
        c.replace_path([[0,0],[.28,0],[.3,0],[.3,.02],[.3,.2]],[0,0,0],.3)
        self.assertEqual(c.plan_generation,2);self.assertLess(c.plan['v_m_s'][1],.3)

    def test_start_alignment_conditions_and_no_pivot(self):
        c=SPAlignment();xy=[[0,0],[0,.15],[0,.3]]
        c.replace_path(xy,[0,0,0],0.);self.assertTrue(c.trigger_S)
        (v,w),_=c.control([0,0,0],0.);self.assertEqual(v,0.);self.assertEqual(w,.4)
        c.replace_path(xy,[0,0,0],.01);self.assertFalse(c.trigger_S)
        c.replace_path([[0,0],[.1,0],[.1,.1]],[0,0,0],0.);self.assertFalse(c.trigger_S)

    def test_s_only_matches_protected_s_without_pivots(self):
        for xy,v in [([[0,0],[.15,0],[.3,0]],.1),([[0,0],[0,.15],[0,.3]],0.)]:
            r=rollout([0,0,0],xy,v,scene('CL'))
            old=simulate([0,0,0],xy,v,'SRG',ticks=108)
            np.testing.assert_array_equal(r['poses'],old['poses'])
            self.assertEqual(r['trigger_P'],0)


if __name__=='__main__':unittest.main()
