import unittest
import numpy as np
from nomad_phase24r2.test_phase24r2 import field
from nomad_phase20c.detour_known import KnownDetourGraph
from .lm import LMGraph,solve_start,SCALES,ANGLES,ANGLES13


class LinearField:
    error_bound=.01/np.sqrt(2)
    def query(self,q):
        q=np.asarray(q);return .007+.013*q[:,0]-.017*q[:,1],np.tile([.013,-.017],(len(q),1))
    def unknown_fraction(self,q):return 0.


class Tests(unittest.TestCase):
    def test_complete_lm_analytic_jacobian_central_difference(self):
        g=LMGraph([.13,-.09,.2],[1.,0.],LinearField(),LinearField(),30)
        # All hinge boundaries and arclength field switches are avoided. This
        # state activates obstacle, curvature, both length and disk penalties.
        rng=np.random.default_rng(2501)
        p=g.B[:2]+np.c_[np.linspace(.07,1.8,10),rng.normal(0,.04,10)]
        p[2]=p[1]+[.045,.005];x=p.ravel()
        for scale in SCALES:
            residual,jac=g.lm_residual(x,scale);eps=1e-5
            # Richardson-extrapolated central differences avoid cancellation
            # after the fixed 1e4 penalty scaling; no solver value is changed.
            def central(step):
                return np.column_stack([(g.lm_residual(x+np.eye(20)[i]*step,scale)[0]-g.lm_residual(x-np.eye(20)[i]*step,scale)[0])/(2*step) for i in range(20)])
            numeric=(4*central(eps/2)-central(eps))/3
            self.assertLess(float(np.max(np.abs(jac-numeric))),1e-5)
            self.assertEqual(residual.shape,(170,));self.assertEqual(jac.shape,(170,20))

    def test_original_cost_constraints_initializers_unchanged(self):
        base,wrapped=field();a=LMGraph([0,0,0],[1,0],base,base,30)
        b=KnownDetourGraph([0,0,0],[1,0],base,base,30)
        np.testing.assert_array_equal(a.initial,b.initial)
        x=a.initial.copy();x[-1]+=.01
        np.testing.assert_array_equal(a.residual_jacobian(x)[0],b.residual_jacobian(x)[0])
        np.testing.assert_array_equal(a.residual_jacobian(x)[1],b.residual_jacobian(x)[1])
        np.testing.assert_array_equal(a.constraints(x)[0],b.constraints(x)[0])
        self.assertEqual(len(ANGLES),7);self.assertEqual(set(ANGLES13),set(range(-90,91,15)))

    def test_continuation_and_final_frozen_certificate(self):
        base,_=field()
        r=solve_start([0,0,0],[1,0],base,base,0,'L7')
        self.assertTrue(r['accepted'],r.get('failures'))
        self.assertEqual([s['scale'] for s in r['stages']],list(SCALES))
        self.assertTrue(all(s['nfev']<=50 for s in r['stages']))
        self.assertEqual(np.shape(r['path']),(11,2))
        self.assertTrue(r['final_certificate']['passed'])
        self.assertLessEqual(r['constraint_violation'],1e-7)

    def test_sparse_penalty_cannot_bypass_dense_acceptance(self):
        from .lm import validate
        base,_=field(blocked=True);g=LMGraph([0,0,0],[1,0],base,base,0)
        p=np.c_[np.linspace(0,1.5,11),np.zeros(11)]
        r=validate(dict(accepted=True,solver_success=True,disposition='ACCEPTED',path=p.tolist(),progress_m=1.5),g)
        self.assertFalse(r['accepted']);self.assertIn('OBSTACLE',r['failures'])
        self.assertFalse(r['final_certificate']['passed'])

    def test_registered_gate_and_both_pass_selection(self):
        from .report import gate
        s=dict(variant='S7',adoption_rate=.8,compute_p95_s=.2,passage_plans=3,clearance_median_m=.10)
        a=dict(s,variant='L7',adoption_rate=.75,compute_p95_s=.1,clearance_median_m=.09)
        b=dict(a,variant='L13',passage_plans=4)
        self.assertEqual(gate([s,a,b])['selected'],'L13')
        b['passage_plans']=3;self.assertEqual(gate([s,a,b])['selected'],'L7')
        a['compute_p95_s']=.1001;b['adoption_rate']=.74
        self.assertEqual(gate([s,a,b])['label'],'NO_GO')


if __name__=='__main__':unittest.main()
