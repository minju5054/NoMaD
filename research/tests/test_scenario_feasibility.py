"""Minimal Phase 0-A geometry and route-label checks; no inference/navigation."""
import copy
import json
from pathlib import Path
import unittest

import numpy as np

from nomad_isaac.clearance import corridor_clearance, point_clearance, swept_clearance
from nomad_isaac.common import integrate_se2
from nomad_phase0.scenario_feasibility import (
    InvalidScenario, Scene, side_certificate, side_transition,
)

ROOT = Path(__file__).resolve().parents[2]


class FeasibilityGeometryTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT/"research/nomad_isaac/early_obstacle_scenario.json").read_text())
        self.scene = Scene(self.config, "active")

    def test_original_continuous_arc_and_corridor_bounds(self):
        pose = np.array([2.0, -.4, .3])
        end, result = self.scene.interval(pose, .2, .4, .5, final=True)
        np.testing.assert_array_equal(end, integrate_se2(pose, .2, .4, .5))
        for name, lo, hi in self.scene.bounds:
            self.assertEqual(result["obstacle_lower_m"][name],
                             swept_clearance(pose, .2, .4, .5, lo, hi, .09, .02)["lower_m"])
        self.assertEqual(result["corridor_lower_m"],
                         corridor_clearance(pose, end, .2, .4, .5, self.scene.corridor, .09))

    def test_endpoint_safe_does_not_imply_interval_safe(self):
        c = copy.deepcopy(self.config)
        c["obstacles"] = [{"id": "ThinBox", "center_xy_m": [0., 0.], "size_xyz_m": [.05, .2, .8]}]
        c["start_pose"] = [-.25, 0., 0.]
        s = Scene(c, "absent")
        self.assertTrue(s.point_safe(s.start))
        self.assertTrue(s.point_safe([.25, 0., 0.]))
        _, result = s.interval(s.start, .2, 0., 2.5, final=True)
        self.assertFalse(result["safe"])
        self.assertTrue(result["overlap"])

    def test_gap_and_one_pass_blockage_certificate(self):
        gap = next(g for g in self.scene.geometry()["pair_gaps"]
                   if set(g["boxes"]) == {"StaticObstacle2", "DynamicObstacle"})
        self.assertAlmostEqual(gap["actual_surface_gap_m"], .202720458, places=12)
        self.assertEqual(gap["required_two_obstacle_width_m"], .22)
        cert = side_certificate(self.scene, "left_positive_y")
        self.assertEqual(cert["status"], "GEOMETRICALLY_BLOCKED")
        self.assertAlmostEqual(cert["proof"]["strict_interval_overlap_m"], .017279542, places=12)
        # At the raw overlapping Y section, midpoint cannot satisfy both margins.
        x = (2.547279542+2.75)/2
        for name, lo, hi in self.scene.bounds:
            if name in ("StaticObstacle2", "DynamicObstacle"):
                self.assertLess(point_clearance([x, .110674603], lo, hi, .09), .02)
        self.assertIsNone(side_certificate(self.scene, "right_negative_y"))

    def test_left_pass_then_return_is_rejected(self):
        cx, cy = self.scene.dynamic["center_xy_m"]
        pose = np.array([cx-.05, cy+.4, 0.])
        passed, cross = side_transition(self.scene, "left_positive_y", False, pose, .2, 0., .5)
        self.assertTrue(passed)
        self.assertAlmostEqual(cross[0], cx, places=12)
        returned, _ = side_transition(self.scene, "left_positive_y", True,
                                     [cx+.05, cy+.4, np.pi], .2, 0., .5)
        self.assertIsNone(returned)
        wrong_side, _ = side_transition(self.scene, "right_negative_y", False, pose, .2, 0., .5)
        self.assertIsNone(wrong_side)

    def test_invalid_start_and_inactive_dynamic(self):
        c = copy.deepcopy(self.config)
        c["start_pose"] = [*c["dynamic_obstacle"]["center_xy_m"], 0.]
        with self.assertRaises(InvalidScenario):
            Scene(c, "active")
        self.assertIsNone(Scene(c, "absent").dynamic)
        c["goal_pose"] = [-2.2, 1.7, 0.]
        with self.assertRaises(InvalidScenario):
            Scene(c, "absent")  # Disk misses the corridor corner despite axis overlap.


if __name__ == "__main__":
    unittest.main()
