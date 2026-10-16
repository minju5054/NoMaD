"""Synthetic clocks and a memory IPC stub; no inference or navigation."""
import ast
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from nomad_isaac.async_core import AsyncClient, WaypointExecution, deadline_ns
from nomad_isaac.common import ROOT, integrate_se2, original_controller


def result(identifier, received_ns):
    return {"id": identifier, "received_monotonic_ns": received_ns}


def test_timeout_matches_official_rosdata_and_starts_at_receive():
    ns = {"rospy": SimpleNamespace(get_time=lambda: clock[0])}
    node = next(n for n in ast.parse((ROOT/"deployment/src/ros_data.py").read_text()).body if isinstance(n, ast.ClassDef))
    exec(compile(ast.Module(body=[node], type_ignores=[]), "ros_data.py", "exec"), ns)
    clock = [10.]
    official = ns["ROSData"](1)
    core = WaypointExecution([0, 0, 0])
    assert not official.is_valid()
    assert core.control(0, 10_000_000_000)[0]["status"] == "missing"
    official.set([.1, .02]); core.receive(result(0, 10_000_000_000), [.1, .02])
    for i, delta in enumerate([0., .5, .999999, 1., 1.2]):
        clock[0] = 10+delta
        refresh, _ = core.control(8*i, 10_000_000_000+round(delta*1e9))
        assert refresh["valid"] == official.is_valid()
        if delta >= 1:
            assert refresh["v_m_s"] == refresh["w_rad_s"] == 0
    assert len(core.expired_ids) == 1


def test_first_stop_then_old_keeps_moving_before_new_result():
    core = WaypointExecution([0, 0, 0])
    for i in range(5):
        core.integrate()
    np.testing.assert_array_equal(core.pose, [0, 0, 0])
    core.receive(result(0, 0), [.1, .02]); core.control(0, 0)
    before = core.pose.copy()
    v, w = original_controller()([.1, .02])
    for i in range(1, 19):
        core.integrate(); core.control(i, round(i/72*1e9))
    np.testing.assert_allclose(core.pose, integrate_se2(before, v, w, .25), atol=1e-14)
    assert np.linalg.norm(core.pose[:2]-before[:2]) > .04 and core.applied_id == 0


def test_result_switch_only_on_next_control_tick_no_reanchor():
    core = WaypointExecution([1, 2, .3])
    point = np.array([.1, -.02], dtype=np.float32)
    core.receive(result(0, 9_000_000), point)
    assert core.control(1, 14_000_000) == (None, None)
    refresh, switch = core.control(8, 112_000_000)
    np.testing.assert_array_equal(switch["selected_waypoint_m"], point)
    np.testing.assert_array_equal(switch["agent_pose_at_switch"], [1, 2, .3])
    np.testing.assert_allclose([refresh["v_m_s"], refresh["w_rad_s"]], original_controller()(point.tolist()))
    assert core.control(16, 223_000_000)[1] is None
    with pytest.raises(ValueError):
        core.receive(result(2, 230_000_000), point)


def test_deadlines_have_no_cumulative_drift_and_control_is_9hz():
    epoch = 1234567890123
    core = WaypointExecution([0, 0, 0])
    ticks = [i for i in range(72) if core.control(i, deadline_ns(epoch, i, 72))[0] is not None]
    assert ticks == list(range(0, 72, 8))
    assert deadline_ns(epoch, 4320, 72)-epoch == 60_000_000_000


def test_one_outstanding_request_busy_then_ordered_receive(monkeypatch):
    entered, complete = threading.Event(), threading.Event()
    sent = []
    def send(connection, metadata, **arrays):
        sent.append(metadata)
        if metadata["kind"] != "stop": entered.set()
    def receive(connection):
        if sent[-1]["kind"] == "stop": return {"kind":"stopped"}, {}
        assert complete.wait(2)
        return {"id": sent[-1]["id"]}, {"metric": np.zeros((8,8,2))}
    monkeypatch.setattr("nomad_isaac.async_core.send_packet", send)
    monkeypatch.setattr("nomad_isaac.async_core.receive_packet", receive)
    client = AsyncClient(None, lambda:{"sim_s":.1,"pose":[.02,0,0],"monotonic_ns":1})
    assert client.submit({"kind":"infer","id":0})
    assert entered.wait(2)
    assert not client.submit({"kind":"infer","id":1})
    assert client.poll() is None
    complete.set()
    output = client.results.get(timeout=2)
    client.results.put(output)
    assert client.busy and not client.submit({"kind":"infer","id":1})
    assert client.poll()[0]["id"] == 0 and not client.busy
    with pytest.raises(ValueError): client.submit({"kind":"infer","id":2})
    assert client.close() is None
