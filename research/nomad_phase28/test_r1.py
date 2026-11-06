import time,unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import integrate_se2
from .graph import HandoffGraph
from .graph_r1 import R1Graph,R1Follower,SCALE,na_initial,solve,violations
from .alignment import NoAlignment
from .test_handoff import Field,central

class RevisionTests(unittest.TestCase):
    def test_frozen_cost_and_original_constraint_rows(self):
        args=([0,0,.1],[.2,.05],[[0,0],[.3,.02],[.7,.1]],Field(True),2.)
        old=HandoffGraph(*args);new=R1Graph(*args);x=old.initial();x[9]+=.004
        np.testing.assert_array_equal(old.objective(x)[1],new.objective(x)[1]);self.assertEqual(old.objective(x)[0],new.objective(x)[0])
        g,j=old.constraints(x);ng,nj=new.constraints(x)
        np.testing.assert_array_equal(g,ng[:-4]);np.testing.assert_array_equal(j,nj[:-4])
    def test_scaled_derivatives_and_initial_acceleration(self):
        g=R1Graph([0,0,.1],[.2,.05],[[0,0],[.3,.02],[.7,.1]],Field(True),2.)
        x=HandoffGraph.initial(g);x[8]+=.013;x[6]+=.008;z=x/SCALE
        np.testing.assert_allclose(g.scaled_objective(z)[1],central(lambda y:g.scaled_objective(y)[0],z)[0],atol=1e-5,rtol=1e-6)
        np.testing.assert_allclose(g.scaled_constraints(z)[1],central(lambda y:g.scaled_constraints(y)[0],z),atol=1e-5,rtol=1e-6)
    def test_na_initializer_same72hz_integrator(self):
        path=[[0,0],[1,0]];dt=np.full(10,.1);B=[0,0,0];q,_=na_initial(B,[.1,0],path,dt)
        c=NoAlignment();c.replace_path(path,B,.1);pose=np.array(B,float);v=.1;trace=[pose.copy()]
        for i in range(72):
            if i%8==0:(v,w),_=c.control(pose,v)
            pose=integrate_se2(pose,v,w,1/72);trace.append(pose.copy())
        trace=np.array(trace);times=np.arange(73)/72
        np.testing.assert_allclose(q[:,0],np.interp(np.r_[0.,np.cumsum(dt)],times,trace[:,0]),atol=1e-12)
    def test_short_chunk_stops_without_pose_snapping(self):
        q,meta=na_initial([0,0,0],[.3,0],[[0,0],[.2,0]],np.ones(10)*.5)
        self.assertTrue(meta['endpoint_hold']);np.testing.assert_array_equal(q[-1],q[-2]);self.assertLessEqual(q[:,0].max(),.2+.3/72)
        self.assertTrue(np.all(q[:,1:]==0))
    def test_start_acceleration_replaces_equal_velocity(self):
        g=R1Graph([0,0,0],[0,0],[[0,0],[.1,0]],Field(),2.)
        x=np.r_[np.c_[np.arange(1,11)*.01,np.zeros(10),np.zeros(10)].ravel(),np.full(10,.1)]
        self.assertLess(g.constraints(x)[0][-4],0);self.assertAlmostEqual(g.initial_rates(x)[0],2.)
    def test_init_only_on_solver_failure_and_no_equalities(self):
        captured={}
        def fail(fun,z,**kw):captured.update(kw);return SimpleNamespace(x=z,success=False,status=8,message='Positive directional derivative for linesearch',nit=3)
        with patch('nomad_phase28.graph_r1.minimize',side_effect=fail):r=solve([0,0,0],[.3,0],[[0,0],[1.2,0]],Field(),2.)
        self.assertTrue(r['accepted'],(r['output_type'],r['initial_violation']['dominant']));self.assertEqual(r['output_type'],'INIT_ONLY');self.assertEqual(len(captured['constraints']),1);self.assertEqual(captured['constraints'][0]['type'],'ineq')
        self.assertEqual(captured['options'],dict(maxiter=100,ftol=1e-8));self.assertEqual(r['initial_violation']['dominant'],'NONE_FEASIBLE')
    def test_invalid_init_keeps_na_fallback(self):
        f=Field();f.query=lambda p:(np.full(len(p),.0),np.zeros_like(p))
        def fail(fun,z,**kw):return SimpleNamespace(x=z,success=False,status=4,message='Inequality constraints incompatible',nit=1)
        with patch('nomad_phase28.graph_r1.minimize',side_effect=fail):r=solve([0,0,0],[.3,0],[[0,0],[1,0]],f,2.)
        self.assertFalse(r['accepted']);self.assertEqual(r['output_type'],'FALLBACK');self.assertFalse(r['initial_valid'])
    def test_deadline_remains_hard(self):
        r=solve([0,0,0],[.3,0],[[0,0],[1,0]],Field(),2.,started=time.perf_counter()-1)
        self.assertFalse(r['accepted']);self.assertEqual(r['disposition'],'TIMEOUT')
    def test_explicit_initial_velocity_anchor(self):
        r=dict(poses=[[0,0,0],[.1,0,.05],[.2,0,.1]],dt=[1.,1.],speed=[.2,.2],omega=[.1,.1],initial_vw=[.1,.05],allow_rotation=False)
        c=R1Follower(r,0,2.);out,_=c.control([0,0,0],.1);self.assertEqual(out,(.1,.05))
    def test_stationary_initial_output_has_no_fabricated_path(self):
        r=dict(poses=[[0,0,0]]*11,dt=[.1]*10,speed=[0.]*10,omega=[0.]*10,initial_vw=[0.,0.],allow_rotation=False)
        c=R1Follower(r,0,2.);out,_=c.control([0,0,0],0.);self.assertEqual(out,(0.,0.));self.assertTrue(np.all(c.follower.path.points==0))
    def test_initialization_is_na_with_old_clock_only(self):
        g=R1Graph([0,0,0],[.3,0],[[0,0],[1,0]],Field(),2.);old=HandoffGraph.initial(g);x=g.initial()
        np.testing.assert_array_equal(x[30:],old[30:]);self.assertEqual(g.initialization['integration_ticks'],int(np.ceil(x[30:].sum()*72)))
    def test_gate_boundaries(self):
        from .r1 import gate
        rows=[dict(output_type='OPTIMIZED' if i<140 else 'INIT_ONLY' if i<180 else 'FALLBACK',wall_s=.15) for i in range(200)]
        self.assertTrue(gate(rows)['passed'])
        rows[0]['output_type']='FALLBACK';self.assertFalse(gate(rows)['checks']['optimized'])

if __name__=='__main__':unittest.main()
