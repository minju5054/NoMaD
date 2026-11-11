import unittest
import numpy as np
from .dynamics import step,trajectory,N
from .inputs import uniform_indices

class Tests(unittest.TestCase):
    def test_step_analytic_jacobians(self):
        for w in (0.,.4,-.4,1e-8):
            x=np.array([1.,-2.,.73,.18]);u=np.array([-.27,w]);_,fx,fu=step(x,u);eps=1e-6
            nx=np.column_stack([(step(x+np.eye(4)[j]*eps,u)[0]-step(x-np.eye(4)[j]*eps,u)[0])/(2*eps) for j in range(4)])
            nu=np.column_stack([(step(x,u+np.eye(2)[j]*eps)[0]-step(x,u-np.eye(2)[j]*eps)[0])/(2*eps) for j in range(2)])
            np.testing.assert_allclose(fx,nx,atol=1e-8,rtol=0);np.testing.assert_allclose(fu,nu,atol=1e-8,rtol=0)
    def test_exact_straight_acceleration_and_rotation(self):
        x,_,_=step([0,0,0,.2],[.5,0])
        np.testing.assert_allclose(x,[.0225,0,0,.25],atol=1e-15,rtol=0)
        x,_,_=step([1,2,.3,0],[0,.4]);np.testing.assert_allclose(x,[1,2,.34,0],atol=1e-15,rtol=0)
    def test_condensed_full_trajectory_derivative(self):
        initial=np.array([.2,-.1,.3,.1]);u=np.zeros((N,2));u[:,0]=np.linspace(-.05,.02,N);u[:,1]=np.linspace(-.3,.3,N)
        x,j=trajectory(initial,u);flat=u.ravel();eps=1e-6
        for k in (0,1,12,25,48,49):
            d=np.zeros(2*N);d[k]=eps;numeric=(trajectory(initial,flat+d)[0]-trajectory(initial,flat-d)[0])/(2*eps)
            np.testing.assert_allclose(j[:,:,k],numeric,atol=1e-8,rtol=0)
        np.testing.assert_array_equal(x[0],initial);self.assertTrue((j[0]==0).all())
    def test_uniform_selection_before_availability(self):
        for n in (0,1,17,40,41,200):
            selected=uniform_indices(n);self.assertEqual(len(selected),min(n,40));self.assertEqual(len(set(selected)),len(selected))
            if n:self.assertEqual(selected[0],0);self.assertEqual(selected[-1],n-1)
if __name__=='__main__':unittest.main()
