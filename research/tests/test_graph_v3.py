"""Minimum speed/curvature/rate/oracle/RAW checks; no optimization or GPU work."""
import json
from pathlib import Path
import unittest

import numpy as np

from nomad_isaac.common import integrate_se2
from nomad_phase0.graph_v3 import DedicatedPP, curvature, rate_command, speed_command
from nomad_phase0.graph_v3_data import visible_at_boundary
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase1.s1 import VisibilityGate


class GraphV3Checks(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((Path(__file__).parents[1]/"nomad_phase0/graph_v3_protocol.json").read_text())

    def test_curvature_limits_and_acceleration_without_termination(self):
        previous = .2
        for kappa in [10., 10., 10., 4., -4., 0., -100., -100., 1.]:
            (v, w), flags = speed_command(kappa, previous, self.p["variable_speed"])
            self.assertGreaterEqual(v, .05); self.assertLessEqual(v, .2)
            self.assertLessEqual(abs(w), .4)
            self.assertLessEqual(abs(v-previous), .5/9+1e-12)
            self.assertEqual(flags["CURVATURE_SATURATED"], abs(kappa) > 8.)
            self.assertEqual(flags["OMEGA_CLIPPED"], abs(w-v*kappa) > 1e-12)
            self.assertEqual(flags["ACCEL_LIMITED"], abs(v-flags["v_target_m_s"]) > 1e-12)
            previous = v
        (v, w), flags = speed_command(10., .05, self.p["variable_speed"])
        self.assertEqual((v, w), (.05, .4))
        self.assertTrue(flags["CURVATURE_SATURATED"] and flags["OMEGA_CLIPPED"])
        self.assertFalse(flags["ACCEL_LIMITED"])

    def test_variable_wrapper_uses_unclipped_PP_curvature(self):
        xy = np.array([[.01, .03], [.03, .08], [.06, .12], [.1, .15]])
        f = DedicatedPP(xy, self.p, [.2, -.4], "speed")
        command, d = f.control([0., 0., 0.])
        self.assertGreater(d["kappa_PP_m_inv"], 2.)
        np.testing.assert_allclose(command, speed_command(curvature(d), .2, self.p["variable_speed"])[0], atol=1e-12)
        # Finite difference is nonzero before clipping even on an applied-w plateau.
        other = dict(d, target_local_y_m=d["target_local_y_m"]+1e-5)
        self.assertGreater(abs(curvature(other)-curvature(d)), 1e-8)

    def test_rate_limiter_per_controller_tick(self):
        w = .4
        for expected in [.3, .2, .1, 0., -.1, -.2, -.3, -.4, -.4]:
            actual = rate_command(-.4, w, .1)
            self.assertLessEqual(abs(actual-w), .1+1e-12)
            self.assertAlmostEqual(actual, expected)
            w = actual

    def test_oracle_after_next_actual_RGB_completion(self):
        gate = VisibilityGate()
        def row(i, visible):
            return {"observation_id": i, "observation_sim_s": i/4, "capture_end_monotonic_ns": i*100,
                    "frame_sha256": str(i), "rgb_file": f"{i}.png", "dynamic": {"active": True, "visible": visible}}
        info = gate.observe(row(10, True))
        self.assertFalse(visible_at_boundary(info, 999999))
        info = gate.observe(row(14, False))
        self.assertFalse(visible_at_boundary(info, 1399))
        self.assertTrue(visible_at_boundary(info, 1400))

    def test_RAW_original_PP_reproduction(self):
        xy = np.column_stack([np.linspace(.02, .45, 8), np.linspace(.01, .08, 8)])
        original = PurePursuit(xy, self.p["follower"])
        wrapper = DedicatedPP(xy, self.p, [.2, -.4], "raw")
        pose = np.array([0., 0., .2])
        for tick in range(24):
            if tick % 8 == 0:
                command, d = original.control(pose)
                actual, copied = wrapper.control(pose)
                np.testing.assert_array_equal(actual, command)
                self.assertEqual(copied["progress_m"], d["progress_m"])
            pose = integrate_se2(pose, *command, 1/72)


if __name__ == "__main__":
    unittest.main()
