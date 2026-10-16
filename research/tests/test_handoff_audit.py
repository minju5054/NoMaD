"""Synthetic audit checks only: no saved run, model, GPU, or simulator is opened."""
import json

import numpy as np

from nomad_isaac.common import local_to_world, read_scenario
from nomad_isaac.handoff_audit import (PROTOCOL, boundary_entries, classify,
                                     correspondence, path_safety)


def setup():
    protocol = json.loads(PROTOCOL.read_text())
    config = read_scenario(PROTOCOL.with_name("two_obstacles_scenario.json"))
    return protocol, config


def test_same_spatial_path_with_different_waypoint_indices():
    protocol, _ = setup()
    old = np.column_stack([np.arange(8)*.04+.04, np.zeros(8)])
    fresh = old + [.04, 0]
    result = correspondence(old, fresh, np.zeros(3), protocol)
    assert result["valid"]
    assert np.linalg.norm(old-fresh) > .1  # Same-index residual would be wrong.
    assert result["progress_spatial_rmse_m"] < 1e-14
    np.testing.assert_allclose(result["common_forward_overlap_m"], .24)


def test_parallel_shift_and_world_rotation():
    protocol, _ = setup()
    old = np.column_stack([np.arange(8)*.04+.04, np.zeros(8)])
    fresh = old + [0, .03]
    pose = np.array([2., 3., np.pi/2])
    result = correspondence(local_to_world(old, pose), local_to_world(fresh, pose), pose, protocol)
    assert result["valid"]
    np.testing.assert_allclose(result["progress_lateral_mean_m"], .03, atol=1e-14)
    assert result["progress_longitudinal_rms_m"] < 1e-14
    assert result["progress_heading_rms_deg"] < 1e-12


def test_short_segments_and_fold_are_not_valid_heading_correspondence():
    protocol, _ = setup()
    x = np.array([.04, .045, .05, .055, .06, .065, .07, .25])
    path = np.column_stack([x, np.zeros(8)])
    # Short samples remain invalid even when the overall path is long enough.
    result = correspondence(path, path, np.zeros(3), protocol)
    assert result["station_heading_invalid_samples"] > 0
    folded = path.copy(); folded[3, 0] = .03
    assert correspondence(folded, path, np.zeros(3), protocol)["reason"] == "nonmonotone_forward_station"
    short = np.column_stack([np.arange(8)*.01+.01, np.zeros(8)])
    assert not correspondence(short, short, np.zeros(3), protocol)["valid"]


def test_large_revision_alone_is_not_a_reconciliation_candidate():
    protocol, config = setup()
    fresh = np.column_stack([np.arange(8)*.04+.04, np.zeros(8)])
    old = fresh + [0, .3]
    b = np.zeros(3)
    overlap = correspondence(old, fresh, b, protocol)
    assert overlap["progress_spatial_rmse_m"] > .29
    assert classify(path_safety(fresh, config), overlap, boundary_entries(fresh, b, config, protocol), protocol) == "ALREADY_CONSISTENT"


def test_yaw_mismatch_can_use_rotation_staging():
    protocol, config = setup()
    d = np.array([.5, np.sqrt(3)/2])
    fresh = np.arange(1, 9)[:, None]*.04*d
    b = np.zeros(3)
    overlap = correspondence(fresh, fresh, b, protocol)
    entries = boundary_entries(fresh, b, config, protocol)
    assert overlap["valid"] and entries["safe_count"] > 0
    assert classify(path_safety(fresh, config), overlap, entries, protocol) == "STAGING_SUFFICIENT"


def test_safe_fresh_with_blocked_connection_and_unsafe_fresh_separate():
    protocol, config = setup()
    config["obstacles"] = [{"id": "wall", "center_xy_m": [.5, 0], "size_xyz_m": [.2, .6, .8]}]
    fresh = np.column_stack([np.arange(8)*.1+1., np.zeros(8)])
    b = np.zeros(3)
    overlap = correspondence(fresh, fresh, b, protocol)
    entries = boundary_entries(fresh, b, config, protocol)
    assert path_safety(fresh, config)["safe"] and entries["safe_count"] == 0
    assert classify(path_safety(fresh, config), overlap, entries, protocol) == "POTENTIAL_RECONCILIATION_CASE"
    unsafe = fresh - [.8, 0]
    assert classify(path_safety(unsafe, config), overlap, entries, protocol) == "UNSAFE_FRESH"


def test_entry_projection_uses_observation_world_path_without_reanchoring():
    protocol, config = setup()
    local = np.column_stack([np.arange(8)*.04+.04, np.zeros(8)])
    observation = np.array([0., .2, .1])
    fresh = local_to_world(local, observation)
    before = fresh.copy()
    boundary = np.array([.015, .202, .12])
    entry = boundary_entries(fresh, boundary, config, protocol)["nearest"]
    np.testing.assert_array_equal(fresh, before)
    np.testing.assert_allclose(entry["xy_m"], fresh[0])
    assert np.linalg.norm(local_to_world(local, boundary)[0]-entry["xy_m"]) > .01
