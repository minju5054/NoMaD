import unittest
import numpy as np
from nomad_phase32o.test_exec_cert import field
from .graph import Graph,solve_start,shifted_prior
from .dynamics import N,DT
from .certificate import validate

class Tests(unittest.TestCase):
    def samples(self):return np.array([np.c_[np.linspace(.1,.9,8),np.full(8,i*.13)] for i in range(8)])
    def test_objective_and_constraints_analytic_jacobian(self):
        f=field();yy,xx=np.indices(f.values.shape);f.values=.2+.03*(f.origin[0]+xx*f.h)+.02*(f.origin[1]+yy*f.h)
        old=dict(time_s=0.,states=np.c_[np.linspace(0,.6,26),np.full(26,.02),np.zeros(26),np.zeros(26)].tolist())
        g=Graph([.01,.02,.2,.1],.03,self.samples(),f,old,time_s=.2);z=g.initial_controls(0);z[::2]=np.linspace(.01,-.04,25);z[1::2]=np.linspace(.03,.12,25)
        f0,gradient=g.objective(z);jac=g.inequality_jac(z).copy();eq=g.equality_jac(z).copy();eps=1e-6
        for k in range(50):
            d=np.zeros(50);d[k]=eps
            numeric=(g.objective(z+d)[0]-g.objective(z-d)[0])/(2*eps)
            self.assertAlmostEqual(gradient[k],numeric,delta=1e-5)
            np.testing.assert_allclose(jac[:,k],(g.inequality(z+d)-g.inequality(z-d))/(2*eps),atol=1e-5,rtol=0)
            np.testing.assert_allclose(eq[:,k],(g.equality(z+d)-g.equality(z-d))/(2*eps),atol=1e-7,rtol=0)
    def test_mixture_transition_and_world_fixed_references(self):
        samples=self.samples();g=Graph([0,0,0,0],0,samples,field());z=g.initial_controls(0)
        first=g.values(z)['active'];shifted=samples.copy();shifted[[0,7]]=shifted[[7,0]]
        other=Graph([0,0,0,0],0,shifted,field());self.assertEqual(first,0);self.assertEqual(other.values(z)['active'],7)
        np.testing.assert_array_equal(g.ref[:,-1],samples[:,-1])
    def test_synthetic_solve_hard_constraints_and_independent_tail(self):
        g=Graph([0,0,0,0],0,self.samples(),field());r=solve_start(g,0)
        self.assertTrue(r['hard_feasible'],r['message']);self.assertLessEqual(abs(r['terminal_v']),1e-7)
        self.assertEqual(r['controls'][0][1],0.)
        cert=validate(dict(pose=[0,0,0],v=0.,omega=0.),r,field());self.assertTrue(cert['passed']);self.assertEqual(cert['terminal_vw'],[0.,0.]);self.assertFalse(cert['graph_velocity_used'])
    def test_initial_omega_hard_fixed_and_eleven_starts(self):
        g=Graph([0,0,.1,.2],.3,self.samples(),field())
        self.assertEqual(g.bounds.lb[1],.3);self.assertEqual(g.bounds.ub[1],.3)
        for i in range(11):
            z=g.initial_controls(i);self.assertEqual(z.shape,(50,));self.assertEqual(z[1],.3)
            r=g.values(z);self.assertLessEqual(np.max(abs(r['states'][:,3])),.3+1e-12);self.assertAlmostEqual(r['terminal'],0.,delta=1e-12)
    def test_stationary_circle_certification_without_epsilon_path(self):
        states=np.zeros((26,4));states[:,2]=np.linspace(0,.9,26)
        cert=validate(dict(pose=[0,0,0],v=0.,omega=0.),dict(states=states.tolist()),field([.2,0]))
        self.assertTrue(cert['passed']);self.assertEqual(cert['model'],'STATIONARY_CIRCULAR_FOOTPRINT_ENDPOINT');self.assertEqual(cert['duration_s'],0.)
        bad=validate(dict(pose=[0,0,0],v=0.,omega=0.),dict(states=states.tolist()),field([.1,0]));self.assertFalse(bad['passed'])
    def test_real_worker_transport_and_json(self):
        import multiprocessing as mp,json,tempfile
        from pathlib import Path
        from concurrent.futures import ProcessPoolExecutor
        from nomad_isaac.common import sha256_file
        from nomad_ugraph.evaluate import worker,atomic
        f=field();f.observed=np.zeros_like(f.occupied);f.metadata={'frame_id':0,'sim_s':0.}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'snapshot.npz';f.save(path)
            payload=dict(snapshot_file=str(path),snapshot_sha256=sha256_file(path),state=dict(pose=[0,0,0],v=0.,omega=0.,time_s=0.),samples=self.samples().tolist(),previous=None,index=0)
            with ProcessPoolExecutor(max_workers=1,mp_context=mp.get_context('spawn')) as pool:r=pool.submit(worker,payload).result(timeout=30)
            self.assertTrue(r['hard_feasible']);json.dumps(r,allow_nan=False)
            target=Path(tmp)/'result.json';atomic(target,r);self.assertEqual(json.loads(target.read_text())['start_index'],0)
    def test_prior_only_time_overlap_no_terminal_extension(self):
        old=dict(time_s=1.,states=np.c_[np.arange(26)*.1,np.zeros((26,3))].tolist())
        p,m=shifted_prior(old,2.);self.assertTrue(m[0]);self.assertFalse(m[-1]);self.assertAlmostEqual(p[0,0],1.)
        self.assertEqual(shifted_prior(old,4.),(None,None))
if __name__=='__main__':unittest.main()
