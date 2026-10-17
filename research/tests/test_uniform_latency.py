"""Virtual deadlines only; original single-trigger regression remains separate."""
import pytest
import numpy as np

from nomad_isaac.delivery_delay import UniformDeliveryDelay
from nomad_isaac.uniform_latency_report import combined_class, old_window_indices


@pytest.mark.parametrize("delay_s", [0., .25, .5, .75])
def test_every_accepted_result_held_even_without_old_or_trigger_position(delay_s):
    now = [1_000_000_000]
    def wait(seconds):
        now[0] += round(seconds * 1e9)
    policy = UniformDeliveryDelay({"configured_additional_s": delay_s}, lambda: now[0], wait)
    for identifier, x, valid in [(0, 0., False), (1, 2.2, True), (2, 4.4, False)]:
        request = {"id": identifier, "observation_pose": [x, 0., 0.],
                   "old_valid_at_observation": valid, "old_id_at_observation": identifier-1}
        policy.annotate_accepted_request(request)
        assert request["additional_delivery_delay_s"] == delay_s
        assert request["delivery_delay_mode"] == "uniform"
        packet = now[0]
        deadline = policy.hold_until_deadline(request, packet)
        assert deadline == now[0] == packet + round(delay_s*1e9)
    assert policy.accepted_count == 3


@pytest.mark.parametrize("delay_s", [-.1, float("nan"), float("inf")])
def test_invalid_delay_rejected(delay_s):
    with pytest.raises(AssertionError):
        UniformDeliveryDelay({"configured_additional_s": delay_s})


def test_pending_window_includes_straddling_old_but_excludes_fresh():
    wall = np.array([0, 10, 20, 30, 40])
    incoming = np.array([-1, 4, 4, 5, 5])
    # Release at 25 overlaps interval 20..30, but it already carries FRESH 5.
    np.testing.assert_array_equal(old_window_indices(wall, incoming, 5, 5, 25), [1, 2])
    np.testing.assert_array_equal(old_window_indices(wall, incoming, 5, 10, 20), [2])


def test_observed_risk_is_separate_from_insufficient_correspondence():
    assert combined_class("INSUFFICIENT_EVIDENCE", {"safe": True}) == "INSUFFICIENT_EVIDENCE"
    assert combined_class("INSUFFICIENT_EVIDENCE", {"safe": None}) == "INSUFFICIENT_EVIDENCE"
    assert combined_class("INSUFFICIENT_EVIDENCE", {"safe": False}) == "OLD_EXECUTION_RISK"
    assert combined_class("UNSAFE_FRESH", {"safe": True}) == "UNSAFE_FRESH"
