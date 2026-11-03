import unittest
import numpy as np
from .test_u3 import make
from .diagnose import terms,convert_path

class Tests(unittest.TestCase):
    def test_factor_decomposition_reproduces_objective(self):
        g,x,_=make();r=terms(g,x);self.assertAlmostEqual(r['total'],g.objective(x)[0],places=8)
    def test_xy_conversion_satisfies_hard_motion_limits(self):
        g,_,_=make();path=np.array([[0,0],[.1,.3],[.4,.6],[.8,.7],[1.2,.7]])
        x,info=convert_path(g,path);r=terms(g,x)
        self.assertLessEqual(r['v_max'],.3+1e-12);self.assertLessEqual(r['omega_max'],.4+1e-12)
        self.assertGreaterEqual(r['dt_min'],.05);self.assertLessEqual(r['dt_max'],1.)
        self.assertGreater(info['heading_lag_max_deg'],0.)

if __name__=='__main__':unittest.main()
