import socket

import numpy as np

from nomad_isaac.common import (controller_2d, integrate_se2, local_to_world,
                                original_controller, read_scenario, receive_packet, send_packet)


def test_controller_against_original_2d():
    oracle = original_controller()
    cases = np.array([[0, 0], [0, 1], [0, -1], [1e-10, 1], [1, 0], [.01, .001],
                      [.1, -.3], [-.1, .3], [-1, -1]], dtype=np.float32)
    cases = np.concatenate([cases, np.random.default_rng(0).uniform(-2, 2, (100, 2)).astype(np.float32)])
    for point in cases:
        np.testing.assert_array_equal(controller_2d(point), oracle(point))
    np.testing.assert_array_equal(controller_2d([1., 0.]), [.2, 0.])
    np.testing.assert_array_equal(controller_2d([0., 1.]), [0., .4])
    np.testing.assert_array_equal(controller_2d([0., -1.]), [0., -.4])


def test_frame_and_unicycle():
    np.testing.assert_allclose(integrate_se2([0, 0, 0], .2, 0, .25), [.05, 0, 0], atol=1e-14)
    np.testing.assert_allclose(integrate_se2([0, 0, np.pi/2], .2, 0, .25), [0, .05, np.pi/2], atol=1e-14)
    np.testing.assert_allclose(integrate_se2([0, 0, 0], .2, .4, 1), [.5*np.sin(.4), .5*(1-np.cos(.4)), .4], atol=1e-14)
    np.testing.assert_allclose(local_to_world([[1, 0], [0, 1]], np.array([2, 3, np.pi/2])), [[2, 4], [1, 3]], atol=1e-14)


def test_ipc_and_history_round_trip():
    left, right = socket.socketpair()
    try:
        history = np.stack([np.full((4, 4, 3), i, dtype=np.uint8) for i in range(4)])
        metadata = {"id": 7, "history_sim_s": [0., .25, .5, .75]}
        send_packet(left, metadata, history=history)
        received, arrays = receive_packet(right)
        assert received == metadata
        np.testing.assert_array_equal(arrays["history"], history)
        assert arrays["history"].dtype == np.uint8
    finally:
        left.close(); right.close()


def test_fixed_schedule():
    c = read_scenario()
    assert c["integration_hz"] % c["observation_hz"] == 0
    assert c["integration_hz"] % c["controller_hz"] == 0
    assert c["controller_dt_s"] == 1 / 4  # Not controller refresh interval 1/9.
    assert c["selected_sample"] == 0 and c["selected_waypoint_index"] == 2
    assert c["goal_tolerance_m"] == .3 and c["timeout_sim_s"] == 30
