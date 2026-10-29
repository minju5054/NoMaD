import unittest
import numpy as np
from nomad_phase0.graph_v4 import menger
from nomad_phase17.graph import ClearanceGraph
from nomad_phase17.config import scene
from .graph_k import CurvatureGraph
from .speed_profile import make_profile
from .rollout import rollout
from .diagnose import cause

class Field:
    error_bound=.01/np.sqrt(2)
    def query(self,p):return np.ones(len(p)),np.zeros_like(p)
    def exact_clearance(self,p):return 1.

class Tests(unittest.TestCase):
    def test_curvature_residual_and_analytic_jacobian(self):
        xy=np.c_[np.linspace(.03,.6,8),np.linspace(.03,.6,8)**2]
        g=CurvatureGraph(xy,[0,0,0],[.2,0],Field(),variant='K')
        x=g.initial.copy();x[:,1]*=.5;x=x.ravel();r,j=g.curvature_residual(x)
        expected=np.maximum(0,np.abs(menger(xy)[0])-np.abs(menger(x.reshape(8,3)[:,:2])[0]))/.5
        np.testing.assert_allclose(r,expected,atol=1e-12,rtol=0)
        fd=np.column_stack([(g.curvature_residual(x+np.eye(24)[i]*1e-7)[0]-g.curvature_residual(x-np.eye(24)[i]*1e-7)[0])/2e-7 for i in range(24)])
        np.testing.assert_allclose(j,fd,atol=1e-5,rtol=0)

    def test_only_declared_factors_change(self):
        xy=np.c_[np.linspace(.03,.6,8),3*np.linspace(.03,.6,8)**2]
        base=ClearanceGraph(xy,[0,0,0],[.2,0],Field());x=base.initial.ravel()
        for variant in ('CLR','NO_PROGRESS','NO_CLEARANCE','NO_BOTH','K','KP'):
            g=CurvatureGraph(xy,[0,0,0],[.2,0],Field(),variant=variant)
            for a,b in zip(g.constraints(x),base.constraints(x)):np.testing.assert_array_equal(a,b)
            self.assertEqual(g.certificate(base.initial),base.certificate(base.initial));self.assertEqual(g.p,base.p)
            _,_,names,_=g.residual_jacobian(x)
            if variant in ('NO_PROGRESS','NO_BOTH','KP'):self.assertNotIn('endpoint_progress',names)
            if variant in ('NO_CLEARANCE','NO_BOTH'):self.assertNotIn('depth_clearance_preference',names)
            if variant in ('K','KP'):self.assertIn('one_sided_curvature_preservation',names)

    def test_sp_bounds_and_two_passes(self):
        p=make_profile([[0,0],[.1,0],[.2,.03],[.22,.12],[.3,.3]])
        v=np.array(p['v_m_s']);s=np.array(p['s_m']);lim=np.array(p['v_limit_m_s'])
        self.assertTrue(np.all(v<=lim+1e-12));self.assertTrue(np.all(v<=.3))
        self.assertTrue(np.all(np.abs(np.diff(v*v))<=np.diff(s)+1e-12))
        np.testing.assert_allclose(make_profile([[0,0],[.5,0],[1,0]])['v_m_s'],.3)

    def test_fixed_path_rollout_limits_and_initial_pose(self):
        c=scene('CL');xy=np.c_[np.linspace(.05,.5,8),np.linspace(.05,.5,8)**2]
        for rule in ('CURV','SP'):
            r=rollout([0,0,0],xy,.1,rule,c,ticks=16)
            np.testing.assert_array_equal(r['poses'][0],[0,0,0])
            self.assertEqual(len(r['poses']),17)
            commands=r['commands'];v=[.1]+[x['v'] for x in commands]
            self.assertTrue(np.all(np.abs(np.diff(v))<=.5/9+1e-12))
            self.assertTrue(all(.05<=x['v']<=.3 and abs(x['w'])<=.4 for x in commands))

    def test_label_priority(self):
        r=dict(turn=True,curvature_ratio=.7,clearance_push_evidence=True)
        self.assertEqual(cause(r),'UNDERTURN_PATH')
        r.update(curvature_ratio=.9,native_kappa_max=4,mean_speed_m_s=.2,omega_saturation_fraction=.6)
        self.assertEqual(cause(r),'UNDERTURN_EXECUTION')
        r['omega_saturation_fraction']=.2;self.assertEqual(cause(r),'CLEARANCE_PUSH')

if __name__=='__main__':unittest.main()
