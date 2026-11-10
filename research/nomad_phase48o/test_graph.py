import unittest
import numpy as np
from .graph import Problem,FixedLag


def observation(i,delta=.2,off=False,travel=.2,z=.4):
    nodes=np.arange(8)*.4
    return dict(id=i,time_s=float(i),node_s=nodes.tolist(),candidate_ids=list(range(8)),
        distances=(abs(nodes-i*.2)*5).tolist(),edge=dict(projected_delta_m=delta,off_path=off,travel_m=travel,noise_z=z))


class Tests(unittest.TestCase):
    def test_analytic_gradient_for_hard_and_noisy_models(self):
        data=[observation(0),observation(1),observation(2,off=True,travel=.15)]
        for noisy in (False,True):
            p=Problem(data,.4,2.8,noisy);z=np.full(p.M.shape[1],.15);z[0]=.6
            value,grad=p.objective(z);eye=np.eye(len(z));h=1e-6
            fd=np.array([(p.objective(z+h*v)[0]-p.objective(z-h*v)[0])/(2*h) for v in eye])
            np.testing.assert_allclose(grad,fd,atol=1e-5,rtol=1e-6)
    def test_exact_increment_elimination_and_off_path_bound(self):
        p=Problem([observation(0),observation(1,delta=-.1),observation(2,delta=2.,off=True,travel=.2)],.4,2.8)
        self.assertEqual(p.M.shape,(3,2))
        s=p.states(np.array([2.,.5]))
        self.assertAlmostEqual(s[1]-s[0],-.1);self.assertAlmostEqual(s[2]-s[1],.2)
        self.assertAlmostEqual(p.bounds.ub[1],.5)
        # Off-reference projected delta2m is not used as an equality/initial
        # increment; only the recorded0.2m travel bound enters this model.
        self.assertAlmostEqual(p.offset[2],-.1)
    def test_fixed_lag_latest_output_and_no_future_truth_input(self):
        graph=FixedLag(np.arange(8)*.4,.4)
        for i in range(8):
            node,detail=graph.step(observation(i))
            self.assertIsNotNone(node);self.assertLessEqual(detail['max_hard_equality_error_m'],1e-12)
        self.assertEqual(detail['window_n'],6)
        self.assertTrue(all(x['time_s']>=2 for x in graph.window))
    def test_noisy_sigma_zero_is_exact_and_noise_is_reused(self):
        a=observation(1,delta=0.);b=observation(2,delta=.2,z=1.)
        p=Problem([observation(0),a,b],.4,2.8,True)
        self.assertEqual(p.M.shape[1],2)
        self.assertAlmostEqual(p.parameters[0]['sigma'],.004)
        self.assertAlmostEqual(p.offset[-1],.204)
        q=Problem([observation(0),a,b],.4,2.8,True)
        np.testing.assert_array_equal(p.offset,q.offset)


if __name__=='__main__':unittest.main()
