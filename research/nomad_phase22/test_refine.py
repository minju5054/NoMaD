import time,unittest
import numpy as np
from nomad_phase19r.test_repair import synthetic
from nomad_phase20d.recent import CachedField
from nomad_phase20.execution import rollout as old_rollout
from .refine import RefineGraph,tube,graph_refine,resample
from .rollout import simulate

SETTINGS=dict(sigma_k=.5,sigma_delta=1.,sigma_heading=.52,sigma_lateral=.3)
class Tests(unittest.TestCase):
    def fields(self):
        base=synthetic(False);strict=object.__new__(CachedField);strict.__dict__.update(base.__dict__);return base,strict
    def test_tube_and_analytic_jacobian(self):
        base,strict=self.fields();path=np.c_[np.linspace(0,1.5,11),.05*np.sin(np.linspace(0,np.pi,11))]
        g=RefineGraph([0,0,0],[1,0],base,strict,path,[0,0],SETTINGS,time.monotonic_ns()+5_000_000_000);x=g.initial.copy();x[3]+=.04
        for function in (g.residual_jacobian,g.constraints):
            r,j=function(x);numeric=np.zeros_like(j);eps=1e-7
            for i in range(len(x)):
                a=x.copy();b=x.copy();a[i]+=eps;b[i]-=eps;numeric[:,i]=(function(a)[0]-function(b)[0])/(2*eps)
            self.assertLess(float(np.max(np.abs(numeric-j))),1e-5)
        p=path.copy();p[5,1]+=.31;h,_=tube(p,path);self.assertLess(h[5],0)
    def test_shape_and_deadline(self):
        base,strict=self.fields();path=np.c_[np.linspace(0,1.5,11),np.zeros(11)]
        r=graph_refine([0,0,0],[1,0],base,strict,path,[0,0],SETTINGS,time.monotonic_ns()+1_000_000_000)
        self.assertTrue(r['accepted'],r);self.assertEqual(np.shape(r['path']),(11,2))
        r=graph_refine([0,0,0],[1,0],base,strict,path,[0,0],SETTINGS,time.monotonic_ns()-1);self.assertEqual(r['disposition'],'TIMEOUT')
    def test_controller_reproduction(self):
        from unittest.mock import patch
        path=np.c_[np.linspace(0,1.5,11),np.linspace(0,.4,11)]
        with patch('nomad_phase20.execution.evaluate',lambda r,c:r):old=old_rollout([0,0,0],path,.2,{},108)
        new=simulate([0,0,0],path,.2,108);np.testing.assert_array_equal(old['poses'],new['poses']);np.testing.assert_array_equal(old['speeds'],new['speeds']);np.testing.assert_array_equal(old['omegas'],new['omegas'])
if __name__=='__main__':unittest.main()
