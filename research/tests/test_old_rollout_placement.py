"""Placement timing and actual-applied OLD state, without Isaac or inference."""
import json
from pathlib import Path
import time

import numpy as np

from nomad_isaac.async_runtime import ExecutionThread
from nomad_isaac.common import integrate_se2
from nomad_isaac.old_rollout_placement import magenta_mask, place_on_old
from nomad_isaac.sudden_obstacle import SuddenObstacleMonitor


def config():
    return json.loads((Path(__file__).parents[1]/"nomad_isaac/old_rollout_obstacle_scenario.json").read_text())


def test_collision_is_after_reaction_budget_but_before_real_old_expiry():
    c = config(); pose = [2., 0., -np.pi/2]
    decision = place_on_old(c, pose, .2, 0., 5, True, .9)
    assert decision["status"] == "PLACED"
    candidate = decision["candidates"][decision["selected_candidate_index"]]
    np.testing.assert_allclose(decision["obstacle"]["center_xy_m"], [2., -.42], atol=1e-12)
    np.testing.assert_allclose(candidate["spawn_clearance_m"], .155, atol=1e-12)
    assert candidate["reaction_window"]["lower_m"] >= .02
    assert candidate["timeout_clipped_rollout"]["upper_m"] < 0
    assert decision["rollout_offset_s"][-1] == .9
    np.testing.assert_allclose(decision["rollout_pose"][-1], integrate_se2(pose,.2,0,.9))
    assert decision == place_on_old(c, pose, .2, 0., 5, True, .9)


def test_no_valid_placement_does_not_extend_timeout_or_move_obstacle(tmp_path):
    c = config(); c["dynamic_obstacle"]["spawn_tick"] = 1
    monitor = SuddenObstacleMonitor(c, tmp_path)
    pose = [2., 0., -np.pi/2]
    monitor.observe_tick(0, pose, pose, .2, 0., 5, True, 800_000_000, 0)
    monitor.observe_tick(1, pose, pose, .2, 0., 5, True, 900_000_000, 0)
    assert monitor.stop_reason == "placement_infeasible"
    assert monitor.obstacle is None and monitor.spawn is None
    result = monitor.finish(False)
    assert result["status"] == "PLACEMENT_INFEASIBLE" and result["active_checks"] == 0


def test_turning_command_uses_exact_arc_and_rejects_invalid_old():
    c = config(); pose = [2., 0., -np.pi/2]
    d = place_on_old(c, pose, .2, .2, 8, True, .95)
    for candidate in d["candidates"]:
        np.testing.assert_allclose(candidate["center_xy_m"],
                                   integrate_se2(pose,.2,.2,candidate["arc_length_m"]/.2)[:2])
    assert place_on_old(c,pose,.2,0,8,False,.95)["status"] == "PLACEMENT_INFEASIBLE"
    assert place_on_old(c,pose,0,0,8,True,.95)["status"] == "PLACEMENT_INFEASIBLE"


def test_rgb_evidence_is_magenta_not_bgr_or_instance_labels():
    pixels = np.array([[[180,10,180],[10,10,180],[10,180,10],[255,255,255],[0,0,0]]],dtype=np.uint8)
    np.testing.assert_array_equal(magenta_mask(pixels),[[True,False,False,False,False]])


def test_snapshot_publishes_resolved_geometry_using_applied_not_pending_old(tmp_path):
    c = config(); c["start_pose"] = [2.,0.,-np.pi/2]
    c["dynamic_obstacle"]["spawn_tick"] = 2; c["timeout_sim_s"] = 2/72
    engine = ExecutionThread(c,tmp_path)
    now = time.monotonic_ns()
    old = {"id":0,"received_monotonic_ns":now-30_000_000,"observation_pose":c["start_pose"],"observation_sim_s":0.}
    engine.core.receive(old,[.2,0.]); engine.received.append(old)
    class Client:
        calls = 0
        def poll(self):
            self.calls += 1
            if self.calls != 2: return None
            points = np.zeros((8,8,2)); points[...,0] = .2
            return ({**old,"id":1,"received_monotonic_ns":time.monotonic_ns()},
                    {"metric":points,"normalized_diffusion":points,"selected_waypoint":points[0,2]})
    engine.start(Client()); engine.thread.join(2)
    assert not engine.thread.is_alive() and engine.error is None
    snapshot = engine.snapshot(); decision = engine.dynamic.placement
    assert snapshot["tick"] == 2 and snapshot["monotonic_ns"] > 0
    assert decision["old_id"] == 0 and engine.core.latest["id"] == 1
    assert decision["old_received_monotonic_ns"] == old["received_monotonic_ns"]
    assert snapshot["dynamic_placement_status"] == "PLACED"
    assert snapshot["resolved_dynamic_obstacle"] == engine.dynamic.spawn["obstacle"]
    engine.rf.close(); engine.monitor.finish(False); engine.dynamic.finish(False)
