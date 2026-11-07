import json, unittest
from unittest.mock import patch
import numpy as np
from nomad_phase20.repair import RepairGraphR2, initialize, solve_sample as original
from nomad_phase20c.detour import DetourGraph
from nomad_phase20d import pool as frozen_pool
from nomad_phase32o.evaluate import clean
from .repair import RepairGraphCLR, solve_sample
from . import pool


class AffineField:
    error_bound = .01 / np.sqrt(2)
    def query(self, xy):
        xy = np.asarray(xy)
        return .09 + .03*xy[:, 0] + .2*xy[:, 1], np.tile([.03, .2], (len(xy), 1))
    def exact_clearance(self, xy):
        return float(self.query(xy)[0].min())


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.B = [0., 0., .03]
        self.q = np.c_[np.linspace(0, .9, 8), .015*np.sin(np.linspace(0, np.pi, 8))]
        self.base = RepairGraphR2(self.q, self.B, AffineField())
        self.clr = RepairGraphCLR(self.q, self.B, AffineField())

    def test_only_residual_is_overridden(self):
        self.assertEqual(set(RepairGraphCLR.__dict__) - {'__module__', '__doc__'}, {'residual_jacobian'})
        for name in ('solve', 'constraints', 'thresholds', 'certificate', 'points', 'objective'):
            self.assertIs(getattr(RepairGraphCLR, name), getattr(RepairGraphR2, name))
        self.assertIs(solve_sample.__code__, original.__code__)
        self.assertIs(solve_sample.__globals__['initialize'], initialize)

    def test_original_factors_constraints_bounds_identical(self):
        x = self.base.initial.copy(); x[5] += .004
        r, j = self.base.residual_jacobian(x); rc, jc = self.clr.residual_jacobian(x)
        np.testing.assert_array_equal(r, rc[:27]); np.testing.assert_array_equal(j, jc[:27])
        for a, b in zip(self.base.constraints(x), self.clr.constraints(x)):
            np.testing.assert_array_equal(a, b)
        for name in ('initial', 'lengths', 'sample_matrix'):
            np.testing.assert_array_equal(getattr(self.base, name), getattr(self.clr, name))
        np.testing.assert_array_equal(self.base.bounds.lb, self.clr.bounds.lb)
        np.testing.assert_array_equal(self.base.bounds.ub, self.clr.bounds.ub)
        self.assertEqual(self.base.certificate(self.q), self.clr.certificate(self.q))

    def test_clr_identical_to_r3_definition(self):
        graph = DetourGraph(self.B, [1., 0.], AffineField(), 0)
        r, j = self.clr.residual_jacobian(self.clr.initial)
        # Evaluate original R3 at matching inspection coordinates, preserving
        # its exact frozen residual implementation (90 samples vs R2's 63).
        gr, gj = graph.residual_jacobian(graph.initial)
        d, grad = graph.field.query(graph.M @ graph.points(graph.initial))
        np.testing.assert_array_equal(gr[19:109], np.maximum(0., .15-d)/.05)
        d, _ = self.clr.field.query(self.clr.sample_matrix @ self.q)
        np.testing.assert_array_equal(r[27:], np.maximum(0., .15-d)/.05)
        self.assertAlmostEqual(self.clr.objective(self.clr.initial)[0] - self.base.objective(self.base.initial)[0], .5*float(r[27:]@r[27:]))

    def test_analytic_jacobian_and_objective(self):
        x = self.clr.initial.copy(); eps = 1e-6
        r, j = self.clr.residual_jacobian(x)
        numerical = np.column_stack([(self.clr.residual_jacobian(x+np.eye(len(x))[i]*eps)[0]-self.clr.residual_jacobian(x-np.eye(len(x))[i]*eps)[0])/(2*eps) for i in range(len(x))])
        self.assertLess(float(np.max(abs(j-numerical))), 1e-5)
        g = self.clr.objective(x)[1]
        ng = np.array([(self.clr.objective(x+np.eye(len(x))[i]*eps)[0]-self.clr.objective(x-np.eye(len(x))[i]*eps)[0])/(2*eps) for i in range(len(x))])
        self.assertLess(float(np.max(abs(g-ng))), 1e-5)

    def test_solve_json_and_original_shape(self):
        for fn in (original, solve_sample):
            r = fn(self.q, self.B, AffineField())
            self.assertTrue(r['accepted'], r)
            self.assertEqual(np.shape(r['path']), (8, 2))
            json.dumps(clean(r), allow_nan=False)

    def test_negative_start_and_short_path_unchanged(self):
        for fn in (original, solve_sample):
            r = fn([[0, 0], [.1, 0]], self.B, AffineField())
            self.assertEqual(r['disposition'], 'SHORT_REMAINING')
            r = fn(self.q, [0, -1, 0], AffineField())
            self.assertEqual(r['disposition'], 'NEGATIVE_DEPTH_AT_B')

    def test_eight_samples_same_selector_and_job_timing(self):
        class FakePool:
            def map(self, fn, args):
                args = list(args)
                assert len(args) == 8 and [a[1] for a in args] == list(range(8))
                return [dict(accepted=i in (2, 3), mean_edit_m=.02, attempt_wall_s=.001) for i in range(8)]
        job = dict(kind='R2', job_id=4, dispatch_ns=0, snapshot_file='unused', variant='R2_CLR')
        r = pool.evaluate_job(FakePool(), job)
        self.assertEqual(r['selected_sample'], 2)
        self.assertEqual(len(r['results']), 8)
        self.assertGreater(r['pool_wall_s'], 0)
        self.assertIs(pool.evaluate_job.__code__, frozen_pool.evaluate_job.__code__)
        json.dumps(r, allow_nan=False)


class MeasurementTests(unittest.TestCase):
    def test_ec_missing_is_not_false_success_or_dropped_denominator(self):
        from .report import summary
        def row(solution, ec):
            return dict(solution=solution,ec_pass=ec,plan_clearance_m=.05 if solution else None,pool_wall_s=.1)
        s=summary([row(True,True),row(True,None),row(False,False),row(True,False)])
        self.assertEqual(s['solution_rate'],.75)
        self.assertEqual(s['ec_conditional_lower'],1/3)
        self.assertEqual(s['ec_conditional_upper'],2/3)
        self.assertEqual(s['joint_EC_lower'],.25)
        self.assertEqual(s['joint_EC_upper'],.5)

    def test_gate_thresholds_and_missing_bounds(self):
        from .report import gate
        base=dict(solution_rate=.8,joint_EC_lower=.4,joint_EC_upper=.4,pool_p95_s=.1)
        new=dict(solution_rate=.75,joint_EC_lower=.6,joint_EC_upper=.6,pool_p95_s=.13)
        self.assertEqual(gate(base,new)['label'],'OFFLINE_OK')
        self.assertEqual(gate(base,dict(new,pool_p95_s=.131))['label'],'OFFLINE_FAIL')
        self.assertEqual(gate(base,dict(new,solution_rate=.749))['label'],'OFFLINE_FAIL')
        self.assertEqual(gate(base,dict(new,joint_EC_lower=.5))['label'],'INDETERMINATE_MISSING_EC')
        self.assertEqual(gate(base,dict(new,joint_EC_lower=.5,joint_EC_upper=.59))['label'],'OFFLINE_FAIL')


if __name__ == '__main__':
    unittest.main()
