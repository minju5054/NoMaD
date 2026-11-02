import time,unittest
import numpy as np
from nomad_phase15.depth_sdf import DepthSDF
from nomad_phase0.graph_v4 import menger
from .graph import UnifiedGraph
from .optimized import OptimizedGraph,vectorized_menger

class Tests(unittest.TestCase):
    def graphs(self):
        field=DepthSDF([-2,-2,3,2]);yy,xx=np.indices(field.values.shape);field.values=.11+.02*(field.origin[0]+xx*field.h)+.03*(field.origin[1]+yy*field.h)
        t=np.linspace(0,1.1,11);path=np.c_[t,.08*np.sin(t*2)];candidates=np.array([path+[0,.07*i] for i in range(8)])
        args=([.003,.007,.17],.13,candidates,.07,field,dict(time=.1,goal=4.,curvature=.01),time.monotonic_ns()+30_000_000_000)
        return UnifiedGraph(*args),OptimizedGraph(*args),path
    def test_all_factor_jacobians_and_equivalence(self):
        base,opt,path=self.graphs();x=base.initial(path);x[4]+=.013;x[17]-=.023;x[32]=.83
        eps=1e-7;eye=np.eye(40)
        for fn in ('objective','constraints'):
            value,jac=getattr(opt,fn)(x);other,old=getattr(base,fn)(x)
            np.testing.assert_array_equal(value,other);np.testing.assert_array_equal(jac,old)
            numeric=np.stack([(getattr(opt,fn)(x+eps*d)[0]-getattr(opt,fn)(x-eps*d)[0])/(2*eps) for d in eye],axis=-1)
            np.testing.assert_allclose(jac,numeric,atol=1e-5,rtol=0)
        # F4/F5/F6 individually, with F1/F2/F3 fixed, using analytic differences.
        for weight in ('time','goal','curvature'):
            base,opt,path=self.graphs();opt.weights[weight]=0.;zero=opt.objective(x);opt.objective_cache=None;opt.weights[weight]=1.;one=opt.objective(x)
            analytic=one[1]-zero[1]
            def isolated(z):
                opt.weights[weight]=0.;opt.objective_cache=None;a=opt.objective(z)[0]
                opt.weights[weight]=1.;opt.objective_cache=None;return opt.objective(z)[0]-a
            numeric=np.array([(isolated(x+eps*d)-isolated(x-eps*d))/(2*eps) for d in eye])
            np.testing.assert_allclose(analytic,numeric,atol=1e-5,rtol=0)
    def test_cache_reuse_invalidation_and_deadline(self):
        base,opt,path=self.graphs();x=opt.initial(path)
        opt.objective(x);opt.constraints(x);evaluations=opt.evaluations;constraints=opt.constraint_kernel_calls
        for _ in range(5):opt.objective(x.copy());opt.constraints(x.copy())
        self.assertEqual(opt.evaluations,evaluations);self.assertEqual(opt.constraint_kernel_calls,constraints)
        x[0]+=.01;opt.objective(x);self.assertEqual(opt.evaluations,evaluations+1)
        opt.deadline=time.monotonic_ns()-1
        with self.assertRaises(TimeoutError):opt.objective(x)
    def test_F1_F2_F3_isolated_analytic_gradients(self):
        for factor in ('F1','F2','F3'):
            _,a,path=self.graphs();_,b,_=self.graphs();x=a.initial(path);x[4]+=.013;x[17]-=.023
            if factor=='F1':b.sigma*=2
            elif factor=='F2':b.field.values[:]=100.;b.start_margin=.025
            else:b.nh_sigma*=2
            analytic=a.objective(x)[1]-b.objective(x)[1];eps=1e-7;eye=np.eye(40)
            def f(z):return a.objective(z)[0]-b.objective(z)[0]
            numeric=np.array([(f(x+eps*d)-f(x-eps*d))/(2*eps) for d in eye])
            np.testing.assert_allclose(analytic,numeric,atol=1e-5,rtol=0)
    def test_vectorized_menger_bitwise(self):
        rng=np.random.default_rng(20261102);p=np.cumsum(rng.normal(size=(11,2))*.1,axis=0)
        a,b=menger(p);c,d=vectorized_menger(p);np.testing.assert_array_equal(a,c);np.testing.assert_array_equal(b,d)
    def test_max_mixture_component_change_is_not_cached(self):
        base,opt,path=self.graphs();x=opt.initial(opt.candidates[0]@opt.R.T+opt.B[:2]);a=opt.objective(x)
        y=opt.initial(opt.candidates[7]@opt.R.T+opt.B[:2]);b=opt.objective(y)
        self.assertEqual(opt.active(opt.unpack(x)[0])[0],0);self.assertEqual(opt.active(opt.unpack(y)[0])[0],7)
        np.testing.assert_array_equal(b[1],base.objective(y)[1])

if __name__=='__main__':unittest.main()
