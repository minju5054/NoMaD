"""Optional exact-geometry STOP gate; never edits a waypoint or nominal PD."""
import argparse
import csv
import json
from pathlib import Path
import time

import numpy as np

from .clearance import (configured_obstacles, corridor_clearance, obstacle_bounds,
                        point_clearance, single_obstacle_config, swept_clearance)
from .common import integrate_se2, original_controller, sha256_file, write_json

PROTOCOL = Path(__file__).with_name("oracle_safety_stop_protocol.json")


def evaluate(config, pose, command, dynamic_box):
    """16 exact 72 Hz intervals, conservative swept bounds including start pose."""
    assert config["integration_hz"] == 72
    assert config["agent_radius_m"] == .09 and config["required_clearance_m"] == .02
    pose = np.asarray(pose, dtype=float)
    v, w = map(float, command)
    assert np.isfinite([*pose, v, w]).all()
    boxes = configured_obstacles(config) + ([dynamic_box] if dynamic_box else [])
    bounds = {box["id"]: obstacle_bounds(single_obstacle_config(config, box)) for box in boxes}
    current = {key: point_clearance(pose[:2], *bound, .09) for key, bound in bounds.items()}
    minima = {key: float("inf") for key in bounds}
    upper = dict(minima)
    corridor = float("inf")
    p = pose.copy()
    for _ in range(16):
        q = integrate_se2(p, v, w, 1/72)
        for key, bound in bounds.items():
            gap = swept_clearance(p, v, w, 1/72, *bound, .09, .02)
            minima[key] = min(minima[key], gap["lower_m"])
            upper[key] = min(upper[key], gap["upper_m"])
        corridor = min(corridor, corridor_clearance(p, q, v, w, 1/72, config["corridor"], .09))
        p = q
    reasons = [key + ":clearance_below_0.02m" for key, gap in minima.items() if gap < .02]
    if corridor <= 0:
        reasons.append("corridor_not_contained")
    return {"safe": not reasons, "reasons": reasons, "horizon_ticks": 16, "horizon_s": 16/72,
            "obstacle_lower_m": minima, "obstacle_upper_m": upper,
            "minimum_clearance_lower_m": min(minima.values()),
            "corridor_lower_m": corridor, "current_obstacle_clearance_m": current,
            "current_margin_already_violated": any(gap < .02 for gap in current.values()),
            "current_corridor_lower_m": corridor_clearance(pose, pose, 0., 0., 0., config["corridor"], .09),
            "end_pose": p.tolist()}


class OracleSafetyStop:
    def __init__(self, config, out):
        self.config = config
        self.stream = (out/"safety_stop.jsonl").open("x")
        write_json(out/"oracle_safety_stop_protocol.json", json.loads(PROTOCOL.read_text()))

    def apply(self, core, refresh, switch, tick, dynamic_box):
        start = time.monotonic_ns()
        active = dynamic_box is not None and tick >= self.config["dynamic_obstacle"]["spawn_tick"]
        nominal = [core.v, core.w]  # freshly recomputed by WaypointExecution.control
        check = evaluate(self.config, core.pose, nominal, dynamic_box) if active else None
        blocked = bool(active and refresh["valid"] and not check["safe"])
        actual = [0., 0.] if blocked else nominal
        core.v, core.w = actual
        end = time.monotonic_ns()
        row = {"tick": tick, "simulation_time_s": tick/72,
               "controller_monotonic_ns": refresh["monotonic_ns"],
               "decision_start_monotonic_ns": start, "decision_end_monotonic_ns": end,
               "evaluation_wall_ms": (end-start)/1e6, "pose": core.pose.tolist(),
               "waypoint_id": core.applied_id, "waypoint_status": refresh["status"],
               "waypoint_age_wall_s": refresh["waypoint_age_wall_s"],
               "active": active, "blocked": blocked,
               "nominal_vw": nominal, "applied_vw": actual, "prediction": check}
        # Existing v_m_s/w_rad_s retain their nominal meaning; trace records actual integration.
        fields = {"applied_v_m_s": actual[0], "applied_w_rad_s": actual[1],
                  "safety_stop_active": active, "safety_stop_blocked": blocked,
                  "command_decision_monotonic_ns": end}
        refresh.update(fields)
        if switch is not None:
            switch.update(fields)
        self.stream.write(json.dumps(row)+"\n")
        self.stream.flush()
        return row

    def close(self):
        self.stream.close()


def validate_b52(run, out):
    """Saved-data gate, no inference/navigation. Also checks RAW replay and STOP."""
    config = json.loads((run/"scenario.json").read_text())
    spawn = json.loads((run/"dynamic/spawn.json").read_text())
    events = [json.loads(line) for line in (run/"events.jsonl").read_text().splitlines()]
    event = next(e for e in events if e["id"] == 52)
    with (run/"agent_trajectory.csv").open() as stream:
        trace = list(csv.DictReader(stream))
    pose = np.array([float(trace[1016][key]) for key in ("x_m", "y_m", "yaw_rad")])
    np.testing.assert_array_equal(pose, event["agent_pose_at_switch"])
    nominal = original_controller()(np.asarray(event["selected_waypoint_m"]))
    np.testing.assert_array_equal(nominal, [event["v_m_s"], event["w_rad_s"]])
    raw = evaluate(config, pose, nominal, spawn["obstacle"])
    stop = evaluate(config, pose, [0., 0.], spawn["obstacle"])
    assert not raw["safe"] and stop["safe"] and not raw["current_margin_already_violated"]
    np.testing.assert_allclose(raw["minimum_clearance_lower_m"], .002653804024105354, atol=1e-12, rtol=0)
    errors = []
    p = pose.copy()
    for row in trace[1017:1033]:
        p = integrate_se2(p, *nominal, 1/72)
        errors.append(float(np.max(np.abs(p-[float(row[k]) for k in ("x_m", "y_m", "yaw_rad")]))))
    assert max(errors) < 1e-12
    result = {"status": "PASS", "source_run": str(run.resolve()), "B52_pose": pose.tolist(),
              "nominal_vw": list(map(float, nominal)), "RAW": raw, "STOP": stop,
              "raw_pose_max_abs_error": max(errors),
              "source_sha256": {name: sha256_file(run/name) for name in
                                ("scenario.json", "events.jsonl", "agent_trajectory.csv", "dynamic/spawn.json")},
              "protocol_sha256": sha256_file(PROTOCOL)}
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"b52_validation.json", result)
    print(json.dumps({"status": "PASS", "RAW_min_m": raw["minimum_clearance_lower_m"],
                      "STOP_min_m": stop["minimum_clearance_lower_m"], "pose_error": max(errors)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate the gate against saved B52, without navigation.")
    parser.add_argument("--validate-b52", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    validate_b52(args.validate_b52, args.out)
