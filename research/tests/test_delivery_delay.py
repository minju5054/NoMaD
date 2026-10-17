"""Synthetic delivery deadlines and controller behavior; no GPU or simulation."""
import json
from pathlib import Path
import threading

import numpy as np
import pytest

from nomad_isaac.async_core import AsyncClient, WaypointExecution
from nomad_isaac.delivery_delay import SingleDeliveryDelay
from nomad_isaac.controlled_latency_report import first_control_after

PROTOCOL = json.loads((Path(__file__).parents[1]/"nomad_isaac/controlled_latency_protocol.json").read_text())


def test_B0_is_first_recorded_tick_without_skipping_an_invalid_old():
    control = [{"monotonic_ns": n, "valid": valid} for n, valid in ((10, True), (20, False), (30, True))]
    assert first_control_after(control, 11) is control[1]
    assert first_control_after(control, 20) is control[1]
    assert first_control_after(control, 21) is control[2]
    assert first_control_after(control, 31) is None


def request(i, x, valid=True, old=0):
    return {"kind": "infer", "id": i, "observation_pose": [x, 0., 0.],
            "old_valid_at_observation": valid, "old_id_at_observation": old}


@pytest.mark.parametrize("edge", [2.1, 2.4])
def test_trigger_inclusive_first_valid_and_once_not_id(edge):
    delay = SingleDeliveryDelay(PROTOCOL)
    for q in (request(40, 2.0999), request(41, 2.4001), request(42, 2.2, valid=False), request(43, 2.2, old=-1)):
        delay.annotate_accepted_request(q)
        assert not q["delivery_delay_triggered"]
    chosen = request(44, edge)
    delay.annotate_accepted_request(chosen)
    assert chosen["delivery_delay_triggered"] and chosen["additional_delivery_delay_s"] == .5
    following = request(45, 2.2)
    delay.annotate_accepted_request(following)
    assert not following["delivery_delay_triggered"] and delay.triggered_id == 44


def test_monotonic_deadline_handles_early_wake_and_does_not_add_gpu_time():
    now = [1_020_000_000]  # 20 ms of normal packet handling already elapsed.
    waits = []
    def wait(seconds):
        waits.append(seconds)
        now[0] += min(120_000_000, round(seconds*1e9))
    delay = SingleDeliveryDelay(PROTOCOL, clock_ns=lambda: now[0], wait=wait)
    deadline = delay.hold_until_deadline({"additional_delivery_delay_s": .5}, 1_000_000_000)
    assert deadline == now[0] == 1_500_000_000
    assert waits == [.48, .36, .24, .12]
    delay.hold_until_deadline({"additional_delivery_delay_s": 0.}, 1_000_000_000)
    assert len(waits) == 4


def test_pending_fresh_does_not_refresh_old_timeout_and_release_resets_fresh_age():
    core = WaypointExecution([0, 0, 0])
    core.receive({"id": 0, "received_monotonic_ns": 0}, [.1, .02])
    core.control(0, 0)
    before = core.pose.copy()
    # IPC holds FRESH independently. Only the OLD receive time can affect control.
    for tick in range(1, 73):
        core.integrate()
        core.control(tick, round(tick/72*1e9))
    assert np.linalg.norm(core.pose[:2]-before[:2]) > .19
    assert core.expired_ids == {0} and (core.v, core.w) == (0., 0.)
    release = 1_500_000_000
    core.receive({"id": 1, "packet_received_monotonic_ns": 1_000_000_000,
                  "release_monotonic_ns": release, "received_monotonic_ns": release}, [.1, -.02])
    refresh, switch = core.control(112, release)
    assert refresh["valid"] and refresh["waypoint_age_wall_s"] == 0. and switch["id"] == 1
    assert core.control(120, release+999_999_999)[0]["valid"]
    assert not core.control(128, release+1_000_000_000)[0]["valid"]


def test_ipc_hold_keeps_busy_and_does_not_consume_skipped_trigger(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    sent = []
    def send(connection, metadata, **arrays):
        sent.append(metadata)
    def receive(connection):
        if sent[-1]["kind"] == "stop":
            return {"kind": "stopped"}, {}
        return {"id": sent[-1]["id"]}, {"selected_waypoint": np.array([.1, .02])}
    monkeypatch.setattr("nomad_isaac.async_core.send_packet", send)
    monkeypatch.setattr("nomad_isaac.async_core.receive_packet", receive)
    delay = SingleDeliveryDelay(PROTOCOL)
    def gate(metadata, packet_ns):
        if metadata["delivery_delay_triggered"]:
            entered.set()
            assert release.wait(2)
        return packet_ns  # Queue isolation test; numerical deadline tested separately.
    monkeypatch.setattr(delay, "hold_until_deadline", gate)
    client = AsyncClient(None, lambda: {"sim_s": .1, "pose": [.02, 0, 0], "monotonic_ns": 1}, delay)
    assert client.submit(request(0, 1.))
    output = client.results.get(timeout=2); client.results.put(output)
    skipped = request(1, 2.1)
    assert not client.submit(skipped) and delay.triggered_id is None
    assert "delivery_delay_triggered" not in skipped
    assert client.poll()[0]["id"] == 0
    assert client.submit(request(1, 2.2)) and entered.wait(2)
    assert client.poll() is None and client.busy and not client.submit(request(2, 2.3))
    # Control is independent and can advance while IPC is held.
    core = WaypointExecution([0, 0, 0])
    core.receive({"id": 0, "received_monotonic_ns": 0}, [.1, 0])
    core.control(0, 0)
    for i in range(1, 37):
        core.integrate(); core.control(i, round(i/72*1e9))
    np.testing.assert_allclose(core.pose, [.1, 0., 0.], atol=1e-14)
    release.set()
    output = client.results.get(timeout=2); client.results.put(output)
    record = client.poll()[0]
    assert record["id"] == 1 and record["delivery_delay_triggered"]
    assert record["received_monotonic_ns"] == record["release_monotonic_ns"] >= record["packet_received_monotonic_ns"]
    assert client.close() is None
