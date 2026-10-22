"""Analytic derivatives and whole-segment certificate checks; no optimizer runs."""
import json
from pathlib import Path
import unittest

import numpy as np

from nomad_isaac.clearance import obstacle_bounds, segment_clearance, single_obstacle_config
from nomad_phase0.graph_v4 import GraphV4, SignedDistanceField, menger, previous_stencil, selection_score


class GraphV4Checks(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((Path(__file__).parents[1]/"nomad_phase0/graph_v4_protocol.json").read_text())
        self.config = {"corridor":{"xmin":-2., "xmax":6., "half_width":1.5}, "agent_radius_m":.09,
            "required_clearance_m":.02, "obstacles":[{"id":"Box", "center_xy_m":[2., .3], "size_xyz_m":[.4, .5, .8]}]}
        self.field = SignedDistanceField(self.config, .01, 2.)
        self.xy = np.column_stack([np.linspace(.0337, .4047, 8), .0143+np.linspace(.012, .069, 8)**2])

    def test_analytic_objective_and_constraints(self):
        graph = GraphV4(self.xy, [0., 0., .07], [.2, .1], self.config, self.p, self.field,
                        previous_xy=self.xy+[-.02, .01])
        x = graph.initial.ravel().copy()
        r, j, _, _ = graph.residual_jacobian(x)
        g, gj, e, ej = graph.constraints(x)
        # Complex-step checks have no subtraction/finite-difference quotient.
        # Production SLSQP exclusively receives the explicit analytic Jacobians.
        for i in range(24):
            z = x.astype(complex); z[i] += 1e-30j
            np.testing.assert_allclose(graph.residual_jacobian(z)[0].imag/1e-30, j[:, i], atol=2e-8, rtol=1e-8)
            gz, _, ez, _ = graph.constraints(z)
            np.testing.assert_allclose(gz.imag/1e-30, gj[:, i], atol=2e-7, rtol=1e-8)
            np.testing.assert_allclose(ez.imag/1e-30, ej[:, i], atol=2e-8, rtol=1e-8)
        self.assertTrue(np.isfinite(r).all() and np.isfinite(g).all() and np.isfinite(e).all())

    def test_circle_curvature_and_invariants(self):
        a = np.linspace(.1, .9, 8); xy = .25*np.column_stack([np.cos(a), np.sin(a)])
        k, jac = menger(xy)
        np.testing.assert_allclose(k, 4., atol=1e-12)
        np.testing.assert_allclose(jac.sum(axis=1), 0., atol=1e-12)
        np.testing.assert_allclose(np.einsum('ijk,jk->i', jac, xy), -k, atol=1e-11)

    def test_sdf_bilinear_gradient_and_conservative_segment_bound(self):
        points = np.array([[1.537, -.317], [2.313, .731], [2.411, .119]])
        value, gradient = self.field.query(points)
        for axis in range(2):
            z = points.astype(complex); z[:, axis] += 1e-30j
            np.testing.assert_allclose(self.field.query(z)[0].imag/1e-30, gradient[:, axis], atol=1e-12)
        lo, hi = obstacle_bounds(single_obstacle_config(self.config, self.config['obstacles'][0]))
        rng = np.random.default_rng(417)
        for _ in range(25):
            a, b = rng.uniform([1., -.7], [2.8, 1.1], (2, 2))
            samples = (1-np.linspace(0,1,9)[:,None])*a+np.linspace(0,1,9)[:,None]*b
            lower = np.min(self.field.query(samples)[0]-self.field.error_bound-np.linalg.norm(b-a)/16)
            exact = segment_clearance(a, b, lo, hi, .09)[0]
            self.assertLessEqual(lower, exact+1e-12)

    def test_previous_prior_and_selection_have_no_future_inputs(self):
        prior = previous_stencil(self.xy, [0.1, .02, 0], self.xy)
        self.assertEqual(prior.shape, (8, 2))
        np.testing.assert_allclose(prior[-1], self.xy[-1])
        score = selection_score(self.xy, self.xy, [0,0,0], self.p)
        self.assertEqual(score['modification'], 0.)
        self.assertEqual(score['progress_cost'], 0.)


if __name__ == '__main__':
    unittest.main()
