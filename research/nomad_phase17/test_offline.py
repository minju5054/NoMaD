import unittest
import numpy as np
from nomad_phase15b.graph import DepthGraph
from .graph import ClearanceGraph


class AffineField:
    error_bound = .01/np.sqrt(2)
    def query(self, xy):
        return xy[:, 1]+.4*xy[:, 0]+.04, np.tile([.4, 1.], (len(xy), 1))
    def exact_clearance(self, xy):
        return float(self.query(xy)[0].min())


class OfflineTests(unittest.TestCase):
    def make(self, cls=ClearanceGraph):
        xy=np.c_[np.linspace(.03, .6, 8), np.zeros(8)]
        return cls(xy, [0.,0.,0.], [.2,0.], AffineField())

    def test_clearance_value_and_analytic_jacobian(self):
        g=self.make(); x=g.initial.ravel(); r,j=g.clearance_residual(x)
        d=g.field.query(g.sample_matrix@g.xy)[0]
        np.testing.assert_allclose(r, np.maximum(0,.15-d)/.05)
        fd=np.column_stack([(g.clearance_residual(x+np.eye(24)[i]*1e-7)[0]-
                             g.clearance_residual(x-np.eye(24)[i]*1e-7)[0])/2e-7 for i in range(24)])
        np.testing.assert_allclose(j,fd,rtol=0,atol=1e-5)
        self.assertTrue(np.any(r>0));self.assertTrue(np.any(r==0))
        np.testing.assert_array_equal(j[r==0],0.)

    def test_only_residual_changes(self):
        g=self.make(); old=self.make(DepthGraph); x=g.initial.ravel()
        for a,b in zip(g.constraints(x),old.constraints(x)):np.testing.assert_array_equal(a,b)
        r,j,n,s=g.residual_jacobian(x); r0,j0,n0,s0=old.residual_jacobian(x)
        np.testing.assert_array_equal(r[:len(r0)],r0);np.testing.assert_array_equal(j[:len(r0)],j0)
        self.assertEqual(n[:-1],n0);self.assertEqual(s[:-1],s0)
        self.assertEqual(g.certificate(g.initial),old.certificate(old.initial));self.assertEqual(g.p,old.p)

    def test_readiness_boundaries(self):
        from .offline import readiness
        self.assertEqual(readiness(.8,.9,.15),'READY')
        self.assertEqual(readiness(.799,.9,.15),'NOT_READY')
        self.assertEqual(readiness(.8,.9,.151),'NOT_READY')


if __name__=='__main__':unittest.main()
