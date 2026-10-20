import json
from pathlib import Path

import numpy as np

from nomad_phase0.pure_pursuit import PurePursuit, XYPath

SETTINGS = json.loads((Path(__file__).resolve().parents[1] /
                      "nomad_phase0/follower_protocol.json").read_text())["follower"]


def test_projection_and_interpolation_are_geometric():
    path = XYPath([[0, 0], [0, 0], [1, 0], [1, 1]])
    np.testing.assert_allclose(path.project([.4, .3]), [.4, .3], atol=1e-15)
    np.testing.assert_allclose(path.at(1.25), [1, .25], atol=1e-15)


def test_pure_pursuit_formula_and_signed_clipping():
    straight = PurePursuit([[0, 0], [2, 0]], SETTINGS)
    cmd, d = straight.control([.1, 0, 0])
    np.testing.assert_allclose(cmd, [.2, 0])
    np.testing.assert_allclose([d["target_x_m"], d["target_y_m"]], [.35, 0])
    for sign in (-1, 1):
        f = PurePursuit([[0, 0], [0, sign]], SETTINGS)
        cmd, d = f.control([0, 0, 0])
        np.testing.assert_allclose(d["raw_w_rad_s"], sign*1.6)
        np.testing.assert_allclose(cmd, [.2, sign*.4])
        assert d["w_clipped"] and not d["v_clipped"]


def test_progress_never_decreases_and_endpoint_stop_is_path_only():
    follower = PurePursuit([[0, 0], [1, 0]], SETTINGS)
    follower.control([.6, 0, 0])
    _, d = follower.control([.4, .01, 0])
    np.testing.assert_allclose(d["progress_m"], .6)
    cmd, d = follower.control([.995, 0, 0])
    assert cmd == (0., 0.) and d["endpoint_stop"]
