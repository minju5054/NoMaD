"""No solver calls: analytic-coordinate and command/timing preflight only."""
import unittest
import numpy as np
from .test_phase4 import Tests as V5Fixtures
from .graph_v5 import GraphV5
from .graph_v51 import GraphV51
from .v51_policy import candidates,expected_tick,command_policy,decision
from .execution import command_policy as v5_command


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V5Fixtures.setUpClass();cls.gp=V5Fixtures.gp;cls.c=V5Fixtures.c;cls.field=V5Fixtures.field

    def make(self,warm=None):
        xy=np.column_stack([np.linspace(.112,.812,8),.013+np.linspace(0,.7,8)**2*.07])
        return GraphV51(xy,[0,0,.01],[.2,.03],self.c,self.gp,self.field,warm_start=warm)

    def test_same_physical_problem_and_jacobians(self):
        g=self.make();z=g.normalized_initial.copy();z[24:]=np.linspace(.4,.8,8);x=g.physical(z)
        self.assertTrue(np.all(g.normalized_bounds.lb[24:]==0));self.assertTrue(np.all(g.normalized_bounds.ub[24:]==1))
        v,j=g.normalized_objective(z);v0,j0=GraphV5.objective(g,x)
        self.assertEqual(v,v0);np.testing.assert_allclose(j,j0*g.scale)
        gg,jg,e,je=g.normalized_constraints(z);g0,jg0,e0,je0=GraphV5.constraints(g,x)
        np.testing.assert_array_equal(gg,g0);np.testing.assert_array_equal(e,e0)
        np.testing.assert_allclose(jg,jg0*g.scale);np.testing.assert_allclose(je,je0*g.scale)
        for i in range(32):
            zz=z.astype(complex);zz[i]+=1e-25j
            np.testing.assert_allclose(g.normalized_objective(zz)[0].imag/1e-25,j[i],atol=1e-6,rtol=1e-6)
            q=g.normalized_constraints(zz)
            np.testing.assert_allclose(q[0].imag/1e-25,jg[:,i],atol=1e-6,rtol=1e-6)
            np.testing.assert_allclose(q[2].imag/1e-25,je[:,i],atol=1e-6,rtol=1e-6)

    def test_warm_start_changes_guess_not_prior_or_constraints(self):
        base=self.make();pose=base.initial.copy();pose[:,0]+=.03;pose[:,2]+=2*np.pi
        warm={'poses':pose.tolist(),'speed_profile':{'v_m_s':[.3]*8}}
        g=self.make(warm);self.assertTrue(g.warm_start_used)
        np.testing.assert_array_equal(g.initial,base.initial)
        self.assertEqual(g.initial_vector[24],g.v0)
        self.assertFalse(np.array_equal(g.initial_vector,base.initial_vector))
        np.testing.assert_allclose(g.objective(base.initial_vector)[0],base.objective(base.initial_vector)[0])
        np.testing.assert_allclose(g.constraints(base.initial_vector)[0],base.constraints(base.initial_vector)[0])

    def test_fallback_identity_and_profile_acceleration(self):
        profile={'s_m':[0,1],'v_m_s':[.3,.05]}
        for k in (-20,-4,0,4,20):
            for previous in (0,.05,.2,.3):
                cmd,flags=command_policy(k,previous)
                self.assertEqual(cmd,v5_command('CURV-SPEED',k,previous)[0])
                self.assertEqual(flags['execution_policy'],'CURV-SPEED_FALLBACK')
                for s in (0.,.5,1.):
                    (v,w),f=command_policy(k,previous,profile,s)
                    self.assertTrue(.05<=v<=.3 and abs(w)<=.4)
                    self.assertLessEqual(abs(v-previous),.5/9+1e-12)
                    self.assertFalse(f['temporal_acceleration_exceeds_limit'])

    def test_causal_tick_and_distance_decision(self):
        cand=candidates([0,0,0],[.3,0]);self.assertAlmostEqual(cand['1'][0],.3/9);self.assertAlmostEqual(cand['2'][0],.6/9)
        self.assertEqual(expected_tick([])[0],1);self.assertEqual(expected_tick([.15])[0],2)
        r={'id':0,'worker_start_ns':0,'worker_end_ns':140_000_000,'accepted':True,'solver':{'success':True}}
        self.assertEqual(decision(r,0,True,cand['1'],cand,1)[0],'ACCEPTED')
        self.assertEqual(decision(r,0,True,cand['2'],cand,2)[0],'ACCEPTED')
        self.assertEqual(decision(r,0,True,[.1,0,0],cand,3)[0],'APP_MISMATCH')
        self.assertEqual(decision(r,0,True,[.1,0,0],cand,2)[0],'APP_MISMATCH')
        self.assertEqual(decision(r,1,True,cand['2'],cand,2)[0],'SUPERSEDED')
        self.assertEqual(decision({**r,'worker_end_ns':310_000_000},0,True,cand['2'],cand,2)[0],'STALE')

if __name__=='__main__':unittest.main()
