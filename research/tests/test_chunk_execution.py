"""Minimum non-GPU checks for observation anchoring, switch state and timeout."""
import numpy as np

from nomad_isaac.async_core import WaypointExecution
from nomad_isaac.common import local_to_world
from nomad_phase0.chunk_execution import ChunkExecution, describe_chunk


def receive(core, identifier, local, obs, now=0):
    core.receive({"id": identifier, "received_monotonic_ns": now,
                  "observation_pose": obs, "chunk": describe_chunk(local, obs)}, local[2])


def control(core, follower, tick, now):
    refresh, switch = core.control(tick, now)
    if refresh is not None:
        follower.apply(core, refresh, switch)
    return refresh, switch


def test_observation_anchor_and_progress_persist_until_next_switch():
    core, follower = WaypointExecution([1.4, 2, 0]), ChunkExecution()
    local = np.column_stack([np.linspace(0, 1, 8), np.zeros(8)])
    obs = [1., 2., 0.]
    receive(core, 0, local, obs)
    assert control(core, follower, 1, 0) == (None, None)
    _, event = control(core, follower, 8, 1)
    np.testing.assert_array_equal(follower.follower.path.points, local_to_world(local, np.array(obs)))
    np.testing.assert_allclose(event["chunk_transition"]["remaining_length_at_switch_m"], .6)
    np.testing.assert_allclose(follower.follower.progress, .4)
    instance = follower.follower
    core.pose[0] = 1.2
    assert control(core, follower, 16, 2)[1] is None
    assert follower.follower is instance
    np.testing.assert_allclose(follower.follower.progress, .4)
    receive(core, 1, local, obs, 3)
    control(core, follower, 24, 3)
    assert follower.follower is not instance
    np.testing.assert_allclose(follower.follower.progress, .2)


def test_short_chunk_clamps_and_short_tangent_is_invalid():
    core, follower = WaypointExecution([0, 0, 0]), ChunkExecution()
    local = np.column_stack([np.linspace(.03, .1, 8), np.zeros(8)])
    receive(core, 0, local, [0, 0, 0])
    refresh, event = control(core, follower, 0, 0)
    assert refresh["pure_pursuit"]["endpoint_clamped"]
    assert not event["chunk_transition"]["fresh_tangent_at_B"]["valid"]
    np.testing.assert_allclose([refresh["pure_pursuit"]["target_x_m"], core.v, core.w], [.1, .2, 0])
    assert len(event["chunk"]["world_xy_m"]) == 8  # No observation origin/extension.


def test_missing_timeout_degenerate_stop_and_new_valid_chunk_recovery():
    core, follower = WaypointExecution([0, 0, 0]), ChunkExecution()
    assert control(core, follower, 0, 0)[0]["pure_pursuit"]["stop_reason"] == "missing"
    line = np.column_stack([np.linspace(.1, .8, 8), np.zeros(8)])
    receive(core, 0, line, [0, 0, 0])
    control(core, follower, 8, 999_999_999)
    assert core.v == .2
    refresh, _ = control(core, follower, 16, 1_000_000_000)
    assert refresh["new_timeout"] and refresh["pure_pursuit"]["stop_reason"] == "expired"
    assert (core.v, core.w) == (0., 0.)
    receive(core, 1, np.zeros((8, 2)), [0, 0, 0], 1_000_000_001)
    refresh, _ = control(core, follower, 24, 1_000_000_002)
    assert refresh["valid"] and refresh["pure_pursuit"]["stop_reason"] == "invalid_chunk"
    assert (core.v, core.w) == (0., 0.)
    receive(core, 2, line, [0, 0, 0], 1_000_000_003)
    control(core, follower, 32, 1_000_000_004)
    assert (core.v, core.w) == (.2, 0.)
