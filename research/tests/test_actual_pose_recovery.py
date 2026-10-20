"""Minimal reverse/spin kinematics and existing continuous-safety checks."""
import copy
import unittest

import numpy as np

from nomad_isaac.common import integrate_se2
from nomad_phase0.actual_pose_recovery import PROTOCOL, action_sets, read_json
from nomad_phase0.scenario_feasibility import ROOT, Node, Scene, verify_witness


class ActualPoseRecoveryTests(unittest.TestCase):
    def test_nested_actions_and_exact_spin_reverse(self):
        sets = action_sets(read_json(PROTOCOL))
        self.assertTrue(set(map(tuple, sets["B0"])) < set(map(tuple, sets["B1"])) < set(map(tuple, sets["B2"])))
        pose = np.array([1.1, -.3, 3.1])
        for v, w in sets["B2"]:
            end = integrate_se2(pose, v, w, .5)
            yaw = (pose[2]+w*.5+np.pi) % (2*np.pi)-np.pi
            if v == 0:
                np.testing.assert_array_equal(end[:2], pose[:2])
                self.assertAlmostEqual(end[2], yaw, places=14)
            if v < 0:
                expected = (pose[:2]+v/w*np.array([np.sin(pose[2]+w*.5)-np.sin(pose[2]),
                                                   np.cos(pose[2])-np.cos(pose[2]+w*.5)])
                            if w else pose[:2]+v*.5*np.array([np.cos(pose[2]), np.sin(pose[2])]))
                np.testing.assert_allclose(end[:2], expected, atol=1e-14, rtol=0)
                np.testing.assert_allclose(integrate_se2(end, -v, -w, .5), pose, atol=1e-14, rtol=0)

    def test_reverse_continuous_collision_and_spin_clearance(self):
        c = read_json(ROOT/"research/nomad_isaac/two_obstacles_wide_wall_scenario.json")
        c["obstacles"] = [{"id": "ThinBox", "center_xy_m": [0., 0.], "size_xyz_m": [.05, .2, .8]}]
        c["start_pose"] = [.25, 0., 0.]
        scene = Scene(c, "absent")
        self.assertTrue(scene.point_safe([-.25, 0., 0.]))
        _, gap = scene.interval(scene.start, -.2, 0., 2.5, final=True)
        self.assertTrue(gap["overlap"])
        self.assertFalse(gap["safe"])
        end, spin = scene.interval(scene.start, 0., .4, .5, final=True)
        np.testing.assert_array_equal(end[:2], scene.start[:2])
        self.assertTrue(spin["safe"])

    def test_reverse_witness_distance_and_no_one_pass_restriction(self):
        c = read_json(ROOT/"research/nomad_isaac/early_obstacle_scenario.json")
        c["start_pose"], c["goal_pose"], c["goal_tolerance_m"] = [2.42, -.5, 0.], [2.32, -.5, 0.], .001
        scene = Scene(copy.deepcopy(c), "active")
        end = integrate_se2(scene.start, -.2, 0., .5)
        nodes = [Node(scene.start, -1, -1, 0., False), Node(end, 0, 0, .5, False)]
        # Returns west across the dynamic center plane; no side constraint in Phase B.
        w = verify_witness(scene, nodes, 1, [[-.2, 0.]], .5, None, minimum_v=-.2)
        self.assertAlmostEqual(w["distance_m"], .1)
        self.assertTrue(w["goal_reached"])
        with self.assertRaises(AssertionError):
            verify_witness(scene, nodes, 1, [[-.2, 0.]], .5, None)  # Phase 0-A default still forward only.


if __name__ == "__main__":
    unittest.main()
