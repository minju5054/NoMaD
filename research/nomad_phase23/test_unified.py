import ast,inspect,time,unittest
from unittest.mock import patch
import numpy as np
from nomad_phase19r.test_repair import synthetic
from . import graph

class Tests(unittest.TestCase):
    def fixture(self):
        q=np.c_[np.linspace(0,1.2,11),.02*np.sin(np.linspace(0,np.pi,11))];c=np.repeat(q[None],8,axis=0)
        return graph.UnifiedGraph([0,0,.1],.2,c,.1,synthetic(),dict(time=1.,goal=1.,curvature=.01),time.monotonic_ns()+10_000_000_000),q
    def test_max_mixture_switches_without_filter(self):
        g,q=self.fixture();g.candidates[1,:,1]+=.5
        self.assertEqual(g.active(g.candidates[0])[0],0);self.assertEqual(g.active(g.candidates[1])[0],1);self.assertEqual(len(g.candidates),8)
    def test_derivatives_and_kinematic_limits(self):
        g,q=self.fixture();x=g.initial(q);x[4]+=.013;x[32]=.8
        eps=1e-7;eye=np.eye(40)
        f,j=g.objective(x);fd=np.array([(g.objective(x+eps*e)[0]-g.objective(x-eps*e)[0])/(2*eps) for e in eye]);np.testing.assert_allclose(j,fd,atol=1e-5,rtol=1e-6)
        f,j=g.constraints(x);fd=np.column_stack([(g.constraints(x+eps*e)[0]-g.constraints(x-eps*e)[0])/(2*eps) for e in eye]);np.testing.assert_allclose(j,fd,atol=1e-5,rtol=1e-6)
        fast=x.copy();fast[30:]=.05;self.assertLess(g.constraints(fast)[0].min(),0)
    def test_deadline_and_shape(self):
        g,q=self.fixture();r=graph.solve_start([0,0,0],.2,np.repeat(q[None],8,0),.1,synthetic(),g.weights,q,time.monotonic_ns()-1)
        self.assertFalse(r['accepted']);self.assertEqual(r['disposition'],'TIMEOUT')
        r=graph.solve_start([0,0,0],.2,np.repeat(q[None],8,0),.1,synthetic(),g.weights,q,time.monotonic_ns()+200_000_000)
        self.assertTrue(r['accepted'],r);self.assertEqual(np.shape(r['poses']),(11,3));self.assertEqual(len(r['dt']),10)
    def test_side_initializations_do_not_search(self):
        q=np.c_[np.linspace(0,1.5,11),np.full(11,-.12)];B=[0,-.12,0];c=np.repeat(q[None],8,axis=0)
        paths,info=graph.side_initializations(c,B,synthetic(True));self.assertEqual(len(paths),2)
        self.assertEqual(paths[0].shape,(11,2));self.assertGreater(paths[0][:,1].max(),paths[1][:,1].max())
        imports=[n for n in ast.walk(ast.parse(inspect.getsource(graph))) if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertFalse(any('astar' in ast.unparse(n).lower() for n in imports))
    def test_graph_speed_rollout_reproducible(self):
        from .rollout import unified_simulate
        q=np.c_[np.linspace(0,1,11),np.zeros((11,2))];plan=dict(accepted=True,poses=q,dt=np.full(10,.5));c=dict(B=[0.,0.,0.],previous_vw=[.2,0.]);policy=dict(rotation_policy='graph_rotation')
        a=unified_simulate(c,plan,policy);b=unified_simulate(c,plan,policy)
        np.testing.assert_array_equal(a['poses'],b['poses']);self.assertTrue(a['completed']);self.assertLessEqual(abs(a['poses'][-1,0]-1),.1+1e-9)
        self.assertTrue(all(abs(w)<=.4 for w in a['omegas']))

if __name__=='__main__':unittest.main()
