import json

import numpy as np

from nomad_isaac.clearance import (MultiObstacleMonitor, configured_obstacles,
                                  planning_diagnostic, single_obstacle_config)
from nomad_isaac.common import SCENARIO_PATH, read_scenario, replay_frame_indices


def configuration():
    return read_scenario(SCENARIO_PATH.with_name("two_obstacles_scenario.json"))


def test_two_box_scenario_preserves_policy_and_increases_start_gap():
    base = read_scenario(SCENARIO_PATH.with_name("obstacle_scenario.json"))
    changed = configuration()
    for key, value in base.items():
        if key not in ["name", "obstacle", "goal_pose", "timeout_sim_s"]:
            assert changed[key] == value
    boxes = configured_obstacles(changed)
    assert len(boxes) == 2
    assert boxes[0]["center_xy_m"] == [1.5, 0.]
    assert boxes[1]["center_xy_m"] == [3., .35]
    assert boxes[0]["size_xyz_m"] != boxes[1]["size_xyz_m"]
    gap = boxes[0]["center_xy_m"][0] - boxes[0]["size_xyz_m"][0]/2 - changed["agent_radius_m"]
    np.testing.assert_allclose(gap, 1.18)
    assert changed["goal_pose"] == [4.5, 0., 0.]
    assert changed["timeout_sim_s"] == 60


def test_second_obstacle_collision_is_not_ignored(tmp_path):
    monitor = MultiObstacleMonitor(configuration(), tmp_path)
    pose = [3., .35, 0.]
    row = monitor.observe_interval(pose, pose, 0., 0., 0., 0.)
    assert row["obstacles"]["StaticObstacle1"]["lower_m"] > 0
    assert row["obstacles"]["StaticObstacle2"]["geometric_overlap"]
    assert monitor.stop_reason == "geometric_collision"
    result = monitor.finish(True)
    assert result["first_contact"]["obstacle_id"] == "StaticObstacle2"
    assert result["geometric_overlap"] and not result["avoidance_success"]
    assert result["category"] == "collision_or_safety_margin_failure"


def test_earliest_contact_does_not_depend_on_obstacle_order(tmp_path):
    config = configuration()
    config["obstacles"].reverse()
    monitor = MultiObstacleMonitor(config, tmp_path)
    # Synthetic geometry test: a long segment crosses both boxes, unlike 72 Hz execution.
    monitor.observe_interval([0, 0, 0], [4, 0, 0], .2, 0., 0., 20.)
    result = monitor.finish(False)
    assert result["first_contact"]["obstacle_id"] == "StaticObstacle1"
    np.testing.assert_allclose(result["first_contact"]["pose_at_bracket_end"][:2], [1.18, 0], atol=1e-8)
    assert all(r["geometric_overlap"] for r in result["obstacles"].values())


def test_planning_and_execution_minimum_include_every_box(tmp_path):
    config = configuration()
    monitor = MultiObstacleMonitor(config, tmp_path)
    sample = np.column_stack([np.linspace(.4, 3.2, 8), np.zeros(8)])
    request = {"observation_pose": [0, 0, 0], "observation_sim_s": .75}
    plan = monitor.plan(0, np.stack([sample]*8), request)
    individual = [planning_diagnostic(sample, request["observation_pose"], single_obstacle_config(config, box))
                  for box in configured_obstacles(config)]
    for key in ["polyline_clearance_m", "through_selected_index_2_clearance_m", "selected_point_clearance_m"]:
        assert plan[key] == min(p[key] for p in individual)
    monitor.observe_interval([0, 0, 0], [0, 0, 0], 0, 0, 0, 0)
    result = monitor.finish(False)
    assert result["safety_margin_met"] and not result["geometric_overlap"]
    assert result["category"] == "no_collision_goal_failure"
    assert len(json.loads((tmp_path / "clearance.jsonl").read_text())["obstacles"]) == 2


def test_video_sampling_keeps_non_grid_terminal_pose():
    assert replay_frame_indices(1, 72) == [0]
    assert replay_frame_indices(7, 72) == [0, 3, 6]
    assert replay_frame_indices(8, 72) == [0, 3, 6, 7]
    assert replay_frame_indices(9, 72) == [0, 3, 6, 8]
    assert replay_frame_indices(2161, 72)[-1] == 2160
