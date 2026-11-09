import unittest
import numpy as np
from .filter import WindowHMM
from .analyze import cause,nearest


class Tests(unittest.TestCase):
    def test_forward_window_distance_and_jump_constraint(self):
        h=WindowHMM(10,.4);n,d=h.step([0,1,2],[0.,2.,4.],0.)
        self.assertEqual(n,0);self.assertEqual(d['transition_half_width'],1)
        n,d=h.step([0,1,2,3,4],[6.,5.,4.,3.,0.],.01)
        self.assertLessEqual(n,3);self.assertTrue(np.isneginf(h.logp[4]));self.assertFalse(d['window_reset'])
        n,d=h.step([7,8,9],[1.,0.,2.],0.)
        self.assertTrue(d['window_reset']);self.assertEqual(n,8)
        self.assertTrue(np.isneginf(h.logp[:7]).all())
        _,d=h.step([5,6,7,8,9],[5.,4.,3.,2.,1.],1.)
        self.assertEqual(d['transition_half_width'],3)
    def test_nearest_and_success_precedence(self):
        nodes=np.array([[0,0,0],[1,0,0],[2,0,0]])
        self.assertEqual(nearest(nodes,[.5,0,2.]),0)
        self.assertEqual(cause(dict(success=True,technical_validation='PASS',primary_cause='NEAR_GOAL_HOVER')),'SUCCESS')
        self.assertEqual(cause(dict(success=False,technical_validation='PASS',primary_cause='STATIC_NARROW_STUCK')),'STATIC_NARROW')


if __name__=='__main__':unittest.main()
