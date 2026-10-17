"""Synthetic activation boundaries, without Isaac/GPU/navigation."""
import json
from pathlib import Path

import numpy as np

from nomad_isaac.sudden_obstacle import SuddenObstacleMonitor, active_at_tick


def scenario():
    config = json.loads((Path(__file__).parents[1]/"nomad_isaac/sudden_obstacle_scenario.json").read_text())
    config["dynamic_obstacle"]["spawn_tick"] = 2
    return config


def test_shared_tick_rule_is_inclusive():
    config = scenario()
    assert not active_at_tick(config, 0)
    assert not active_at_tick(config, 1)
    assert active_at_tick(config, 2)
    assert active_at_tick(config, 3)


def test_hidden_obstacle_does_not_collide_until_exact_spawn(tmp_path):
    config = scenario(); monitor = SuddenObstacleMonitor(config, tmp_path)
    pose = np.array([2.45, -.18, 0.])
    for tick in range(2):
        row = monitor.observe_tick(tick, pose, pose, 0., 0., 7, True, tick)
        assert not row["collision_checked"] and monitor.stop_reason is None
    row = monitor.observe_tick(2, pose, pose, 0., 0., 7, True, 2)
    assert row["checked_duration_s"] == 0
    assert monitor.stop_reason == "geometric_collision"
    assert monitor.spawn["old_id"] == 7 and monitor.spawn["simulation_time_s"] == 2/72
    result = monitor.finish(False)
    assert result["active_checks"] == 1 and result["evaluation"]["geometric_overlap"]


def test_spawn_does_not_retroactively_collide_with_previous_interval(tmp_path):
    config = scenario(); monitor = SuddenObstacleMonitor(config, tmp_path)
    inside = np.array([2.45, -.18, 0.]); outside = np.array([2., -.18, 0.])
    for tick in range(2):
        monitor.observe_tick(tick, inside, inside, 0., 0., 4, True, tick)
    monitor.observe_tick(2, inside, outside, 0., 0., 4, True, 2)
    assert monitor.stop_reason is None and monitor.spawn["footprint_clearance_m"] > .02
    # The next full interval sweeps through the box, including between endpoints.
    end = np.array([2.9, -.18, 0.])
    monitor.observe_tick(3, outside, end, .9*72, 0., 4, True, 3)
    assert monitor.stop_reason == "geometric_collision"
    result = monitor.finish(False)
    assert result["evaluation"]["first_contact"]["interval_start_s"] == 2/72


def test_run_ending_before_spawn_is_not_triggered(tmp_path):
    config = scenario(); monitor = SuddenObstacleMonitor(config, tmp_path)
    monitor.observe_tick(0, [0., 0., 0.], [0., 0., 0.], 0., 0., -1, False, 10)
    result = monitor.finish(False)
    assert result["status"] == "NOT_TRIGGERED" and result["active_checks"] == 0
    assert result["evaluation"]["minimum_swept_clearance_lower_m"] is None
