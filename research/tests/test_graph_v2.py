"""Small geometry/projection checks; no optimization or inference."""
import json
from pathlib import Path
import unittest

import numpy as np

from nomad_isaac.common import local_to_world
from nomad_isaac.online_graph_factors import between
from nomad_phase0.graph_v2 import GraphV2, chord_values, fixed_entry, heading_chords
from nomad_phase0.pure_pursuit import XYPath


class GraphV2Checks(unittest.TestCase):
    def test_chords_and_fixed_projection(self):
        xy = np.array([[0., 0.], [.01, 0.], [.03, .01], [.03, .01],
                       [.07, .02], [.1, .03], [.13, .04], [.16, .05]])
        chords = heading_chords(xy, .02)
        self.assertEqual(chords[0], (0, 2))
        self.assertTrue(np.isfinite(chord_values(xy, chords)[0]).all())
        entry = fixed_entry(xy, np.array([.035, -.01, .1]))
        projected = (1-entry["fraction"])*xy[entry["a"]]+entry["fraction"]*xy[entry["b"]]
        np.testing.assert_allclose(projected, XYPath(xy).at(entry["raw_arclength_m"]), atol=1e-12)
        with self.assertRaises(ValueError):
            heading_chords(np.zeros((8, 2)), .02)

    def test_rigid_preserves_relative_and_observation_anchor(self):
        root = Path(__file__).resolve().parents[1]
        p = json.loads((root/"nomad_phase0/graph_v2_protocol.json").read_text())
        config = json.loads((root/"nomad_isaac/two_obstacles_wide_wall_scenario.json").read_text())
        local = np.column_stack([np.linspace(.01, .3, 8), np.linspace(0., .06, 8)])
        world = local_to_world(local, np.array([.5, .2, -.3]))
        untouched = world.copy()
        graph = GraphV2(world, [.53, .19, -.25], [.2, -.1], config, p, 16)
        rigid = graph.rigid()
        np.testing.assert_allclose(rigid[0], graph.boundary, atol=1e-12)
        for i in range(7):
            np.testing.assert_allclose(between(rigid[i], rigid[i+1]), graph.relative[i], atol=1e-12)
        np.testing.assert_array_equal(world, untouched)


if __name__ == "__main__":
    unittest.main()
