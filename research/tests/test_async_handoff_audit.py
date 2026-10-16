"""Minimal offline checks for applied IDs, clock windows, and point frames."""
import numpy as np

from nomad_isaac.async_handoff_audit import applied_pairs, motion, selected_point_semantics
from nomad_isaac.common import local_to_world


def test_handoff_pairs_follow_applications_and_exclude_unswitched_predictions():
    events = [{"id": 0, "application_monotonic_ns": 10},
              {"id": 2, "application_monotonic_ns": 30}]
    received = [{"id": i} for i in range(4)]
    pairs, excluded = applied_pairs(events, received)
    assert [(a["id"], b["id"]) for a,b in pairs] == [(0,2)]
    assert [r["id"] for r in excluded] == [1,3]


def test_motion_counts_actual_old_intervals_and_wrapped_yaw_with_host_bounds():
    trace = {"pose": np.array([[0,0,np.pi-.1],[0,0,-np.pi+.1],
                               [0,0,-np.pi+.2],[0,0,-np.pi+.1]]),
             "command": np.array([[0,0],[1,0],[2,0],[3,0]]), "dt": .1,
             "wall": np.array([0,100,200,300],dtype=np.int64),
             "id": np.array([-1,0,0,1]), "valid": np.array([False,True,True,True])}
    total = motion(trace,0,3)
    old = motion(trace,0,3,0)
    complete = motion(trace,0,3,0,(50,250))
    np.testing.assert_allclose([total["distance_m"],old["distance_m"],old["signed_yaw_rad"]],[.6,.3,.3],atol=1e-12)
    assert complete["interval_count"] == 1
    np.testing.assert_allclose([complete["distance_m"],complete["signed_yaw_rad"]],[.2,.1],atol=1e-12)
    assert motion(trace,3,3)["distance_m"] == 0


def test_controller_local_point_is_distinct_from_observation_anchored_point():
    local = np.array([.2,.1]); observation = np.array([1.,2.,np.pi/2])
    boundary = np.array([1.03,2.04,np.pi/2+.2])
    result = selected_point_semantics(local,observation,boundary)
    np.testing.assert_allclose(result["anchored_world_point_m"],[.9,2.2],atol=1e-12)
    reconstructed = local_to_world(np.array([result["anchored_point_expressed_in_B_local_m"]]),boundary)[0]
    np.testing.assert_allclose(reconstructed,result["anchored_world_point_m"],atol=1e-12)
    np.testing.assert_array_equal(local,[.2,.1])
    assert result["offset_m"] > .01
    assert selected_point_semantics(local,observation,observation)["offset_m"] < 1e-12
