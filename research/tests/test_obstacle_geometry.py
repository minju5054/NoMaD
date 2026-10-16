import json
from pathlib import Path

import numpy as np

from nomad_isaac.common import SCENARIO_PATH, integrate_se2, read_scenario
from nomad_isaac.clearance import (first_contact_bracket, obstacle_bounds, planning_diagnostic,
                                  point_clearance, segment_clearance, swept_clearance)


def test_obstacle_config_preserves_baseline():
    base = read_scenario()
    obstacle = read_scenario(SCENARIO_PATH.with_name("obstacle_scenario.json"))
    for key, value in base.items():
        if key != "name":
            assert obstacle[key] == value
    assert obstacle["obstacle"]["center_xy_m"] == [.75, 0.]
    assert obstacle["obstacle"]["size_xyz_m"] == [.3, .4, .8]
    assert obstacle["agent_radius_m"] == .12
    assert obstacle["required_clearance_m"] == .02


def test_segment_detects_tunnelling_and_rounded_corner():
    lo, hi = np.array([.6, -.2]), np.array([.9, .2])
    assert point_clearance(np.array([0., 0.]), lo, hi, .12) > 0
    assert point_clearance(np.array([1.5, 0.]), lo, hi, .12) > 0
    gap, t = segment_clearance([0., 0.], [1.5, 0.], lo, hi, .12)
    np.testing.assert_allclose(gap, -.12, atol=1e-14)
    assert .4-1e-14 <= t <= .6+1e-14
    # Expanded rectangular AABB would give a false collision at this corner.
    gap, _ = segment_clearance([.5, -.3], [.5, -.3], lo, hi, .12)
    np.testing.assert_allclose(gap, np.sqrt(.02)-.12, atol=1e-14)
    gap, _ = segment_clearance([0., .34], [1.5, .34], lo, hi, .12)
    np.testing.assert_allclose(gap, .02, atol=1e-14)


def test_arc_bounds_against_dense_actual_arc():
    # Geometry tests only, not extra NoMaD/scene experiments or seed sweeps.
    lo, hi = np.array([.6, -.2]), np.array([.9, .2])
    for pose, v, w, duration in [([.45, .1, .2], .2, .4, 1.), ([.4, -.34, 0.], .2, -.4, 1.),
                                  ([.47, 0., 0.], .2, 0., .1), ([.4, .34, 0.], .2, 1e-9, 1.),
                                  ([0., 0., 0.], 0., .4, 1.)]:
        bound = swept_clearance(pose, v, w, duration, lo, hi, .12)
        points = [integrate_se2(pose, v, w, t)[:2] for t in np.linspace(0, duration, 2001)]
        dense_min = min(point_clearance(p, lo, hi, .12) for p in points)
        assert bound["lower_m"] <= dense_min + 1e-12
        # Dense samples approximate the true minimum from above; the reported
        # upper bound is another actual arc witness, not necessarily the minimum.
        assert dense_min <= bound["upper_m"] + abs(v)*duration/2000 + 1e-12
        assert bound["upper_m"] >= bound["lower_m"] - 1e-12


def test_first_contact_and_safe_vs_unsafe_margin():
    lo, hi = np.array([.6, -.2]), np.array([.9, .2])
    # x=.48 is first circular-footprint contact with the near face.
    bracket = first_contact_bracket([.47, 0., 0.], .2, 0., .1, lo, hi, .12)
    np.testing.assert_allclose(bracket["pose_at_bracket_end"][:2], [.48, 0], atol=1e-9)
    assert swept_clearance([.4, .33, 0.], .2, 0., 1., lo, hi, .12)["lower_m"] < .02
    assert swept_clearance([.4, .341, 0.], .2, 0., 1., lo, hi, .12)["lower_m"] > .02


def test_planning_polyline_uses_observation_frame_and_full_sample():
    config = read_scenario(SCENARIO_PATH.with_name("obstacle_scenario.json"))
    local = np.column_stack([np.linspace(.1, .8, 8), np.zeros(8)])
    result = planning_diagnostic(local, [0, 0, 0], config)
    assert result["polyline_clearance_m"] < 0
    assert result["through_selected_index_2_clearance_m"] > 0
    result = planning_diagnostic(local, [0, 0, np.pi/2], config)
    np.testing.assert_allclose(np.array(result["world_xy_m"])[:, 0], 0, atol=1e-14)
    assert result["polyline_clearance_m"] > 0
