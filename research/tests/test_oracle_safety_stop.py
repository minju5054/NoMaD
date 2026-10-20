"""Only activation/override/resume and original timeout semantics; no navigation."""
import json

import numpy as np

from nomad_isaac.async_core import WaypointExecution
from nomad_isaac.common import ROOT
from nomad_isaac.oracle_safety_stop import OracleSafetyStop, evaluate


def saved_b52():
    run = ROOT.parent/"artifacts/isaac6/topomap_sudden_01"
    config = json.loads((run/"scenario.json").read_text())
    box = json.loads((run/"dynamic/spawn.json").read_text())["obstacle"]
    event = next(json.loads(line) for line in (run/"events.jsonl").read_text().splitlines()
                 if json.loads(line)["id"] == 52)
    return config, box, event


def test_gate_only_overrides_execution_then_resumes_and_preserves_timeout(tmp_path):
    config, box, event = saved_b52()
    core = WaypointExecution(event["agent_pose_at_switch"])
    gate = OracleSafetyStop(config, tmp_path)
    core.receive({"id": 0, "received_monotonic_ns": 0}, event["selected_waypoint_m"])
    try:
        refresh, switch = core.control(968, 100_000_000)
        row = gate.apply(core, refresh, switch, 968, None)
        assert not row["active"] and row["applied_vw"] == row["nominal_vw"]
        refresh, switch = core.control(1016, 200_000_000)
        original = list(core.latest["selected_waypoint_m"])
        row = gate.apply(core, refresh, switch, 1016, box)
        assert row["blocked"] and core.v == core.w == 0
        assert core.latest["selected_waypoint_m"] == original and core.command_valid
        assert refresh["v_m_s"] > 0 and refresh["applied_v_m_s"] == 0
        p = core.pose.copy()
        for _ in range(8):
            core.integrate()
        np.testing.assert_array_equal(core.pose, p)
        # New safe synthetic FRESH is accepted during STOP, without changing its receive clock.
        core.receive({"id": 1, "received_monotonic_ns": 300_000_000}, [.001, .01])
        refresh, switch = core.control(1024, 400_000_000)
        row = gate.apply(core, refresh, switch, 1024, box)
        assert switch["id"] == 1 and row["prediction"]["safe"] and not row["blocked"]
        assert core.v > 0
        core.integrate()
        assert np.linalg.norm(core.pose[:2]-p[:2]) > 0
        refresh, switch = core.control(1032, 1_300_000_000)
        row = gate.apply(core, refresh, switch, 1032, box)
        assert refresh["status"] == "expired" and refresh["new_timeout"]
        assert not row["blocked"] and core.v == core.w == 0
    finally:
        gate.close()


def test_stop_cannot_restore_an_already_violated_margin():
    config, box, event = saved_b52()
    raw = evaluate(config, event["agent_pose_at_switch"], [event["v_m_s"], event["w_rad_s"]], box)
    late_stop = evaluate(config, raw["end_pose"], [0., 0.], box)
    assert late_stop["current_margin_already_violated"] and not late_stop["safe"]
