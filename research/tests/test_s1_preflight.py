"""Minimum S1 combination, ray geometry, tick activation and RGB information tests."""
import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from nomad_isaac.common import ROOT
from nomad_isaac.sudden_obstacle import SuddenObstacleMonitor
from nomad_phase0.chunk_execution import validate_mode
from nomad_phase1.s1 import HERE, VisibilityGate, place_forward, ray_surface_distance, validate_options


def config():
    return json.loads((HERE/"s1_scenario.json").read_text())


def options():
    return SimpleNamespace(s1_mode=True, pure_pursuit=True, asynchronous=True,
        topomap=ROOT.parent/"artifacts/isaac6/topomap_reference_2s_01/topomap/manifest.json",
        prepare_only=False, oracle_safety_stop=False, early_obstacle_mode=None,
        controlled_delivery_delay=False, render_topomap_reference=None, seed_offset=0,
        run_id=None, uniform_delivery_delay_s=.75, s1_distance_m=.8, scenario=HERE/"s1_scenario.json")


def test_frozen_combinations_and_old_S0_gate():
    args = options()
    for delay in [0., .25, .5, .75]:
        args.uniform_delivery_delay_s = delay
        validate_mode(args)
    for key, value in [("seed_offset", 10000), ("pure_pursuit", False), ("oracle_safety_stop", True)]:
        bad = copy.copy(args); setattr(bad, key, value)
        with pytest.raises(ValueError):
            validate_options(bad)
    args.s1_mode = False
    args.scenario = ROOT/"research/nomad_isaac/two_obstacles_wide_wall_scenario.json"
    with pytest.raises(ValueError):
        validate_mode(args)  # Existing S0 still forbids uniform delay.
    args.uniform_delivery_delay_s = None
    validate_mode(args)


def test_forward_ray_distance_oblique_and_invalid_geometry():
    c = config(); pose = [1.900725092, .362094053, -.677639354]
    for d in [.8, 1., 1.2, 1.5]:
        c["dynamic_obstacle"]["placement"]["forward_clearance_m"] = d
        result = place_forward(c, pose)
        assert result["status"] == "PLACED"
        assert abs(result["measured_forward_ray_d_m"]-d) < 1e-12
    # Direct oblique slab intersection, independent of placement formula.
    gap = ray_surface_distance([0., 0., np.pi/4], np.array([1., 1.]), np.array([2., 2.]), .09)
    assert abs(gap-(np.sqrt(2)-.09)) < 1e-12
    assert place_forward(c, [5.8, 0., 0.])["status"] == "PLACEMENT_INFEASIBLE"
    c["dynamic_obstacle"]["placement"]["forward_clearance_m"] = .8
    assert place_forward(c, [1.9, .75, 0.])["overlap_static_ids"] == ["StaticObstacle2"]


def test_first_region_entry_only_no_prespawn_collision(tmp_path):
    c = config(); monitor = SuddenObstacleMonitor(c, tmp_path)
    before = np.array([1.899, .362, -.678]); at = np.array([1.901, .36, -.678])
    assert not monitor.observe_tick(0, before, before, .2, .1, 4, True, 0)["active"]
    assert monitor.monitor is None
    row = monitor.observe_tick(1, before, at, .2, .1, 4, True, 1)
    assert row["active"] and row["checked_duration_s"] == 0
    original_box = dict(monitor.obstacle)
    monitor.observe_tick(2, at, at, 0., 0., 5, False, 2)
    assert monitor.obstacle == original_box and monitor.spawn["tick"] == 1
    assert monitor.finish(False)["status"] == "SPAWNED"


def test_oracle_waits_next_actual_capture_not_clock_slot():
    gate = VisibilityGate()
    def observation(i, active, visible):
        return {"observation_id": i, "observation_sim_s": i/4, "capture_end_monotonic_ns": i*250000000,
                "rgb_file": f"{i}.png", "frame_sha256": str(i), "dynamic": {"active": active, "visible": visible}}
    assert not gate.observe(observation(0, False, False))["geometry_available"]
    first = gate.observe(observation(4, True, True))
    assert first["first_visible"]["observation_id"] == 4 and not first["geometry_available"]
    second = gate.observe(observation(8, True, False))
    assert second["geometry_available"] and second["available_from"]["observation_id"] == 8
    assert not second["used_for_control"]
    unseen = VisibilityGate()
    assert not unseen.observe(observation(10, True, False))["geometry_available"]
