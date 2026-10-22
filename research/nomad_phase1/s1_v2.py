"""Frozen obstacle-free S1-v2 mode; deterministic reference, passive corridor monitor."""
import csv
import json
from pathlib import Path
import subprocess

import numpy as np

from nomad_isaac.common import ROOT, integrate_se2, local_to_world, sha256_file, write_json
from nomad_isaac.clearance import corridor_clearance

HERE = Path(__file__).parent
MODE = "phase1_s1_v2_straight"


def protocol():
    return json.loads((HERE/"s1_v2_protocol.json").read_text())


def validate_config(config):
    expected = json.loads((HERE/"s1_v2_scenario.json").read_text())
    assert sha256_file(HERE/"s1_v2_scenario.json") == protocol()["scenario_sha256"]
    assert all(config.get(k) == v for k, v in expected.items() if k != "synchronous")
    assert not config["obstacles"] and "dynamic_obstacle" not in config


def validate_options(args):
    if (getattr(args, "s1_mode", False) or args.s1_distance_m is not None or args.seed_offset
            or args.run_id is not None or args.oracle_safety_stop or args.early_obstacle_mode
            or args.controlled_delivery_delay):
        raise ValueError("S1-v2 permits only its frozen obstacle-free baseline")
    if sha256_file(args.scenario) != protocol()["scenario_sha256"]:
        raise ValueError("S1-v2 scenario differs from the frozen corridor")
    if args.prepare_only:
        if not args.render_topomap_reference or args.topomap or args.pure_pursuit or args.uniform_delivery_delay_s is not None:
            raise ValueError("S1-v2 preparation only renders its saved reference, without inference")
        from nomad_isaac.topomap import reference_rows
        reference_rows(args.render_topomap_reference, json.loads(args.scenario.read_text()), 2.)
    else:
        if (not args.asynchronous or not args.pure_pursuit or not args.topomap
                or args.render_topomap_reference or args.uniform_delivery_delay_s != 0.):
            raise ValueError("S1-v2 pilot requires async PP + new Topomap + explicit uniform D=0")
        from nomad_isaac.topomap_report import validate_map
        manifest, _ = validate_map(args.topomap)
        validate_config(manifest["scenario"])
        assert manifest["spacing_sim_s"] == 2. and manifest["reference_kind"] == "deterministic_centerline"


def centerline(config):
    validate_config(config)
    pose = np.array(config["start_pose"], dtype=float)
    result = [pose.copy()]
    for _ in range(round(config["timeout_sim_s"]*72)):
        pose = integrate_se2(pose, .2, 0., 1/72)
        result.append(pose.copy())
        if np.linalg.norm(pose[:2]-config["goal_pose"][:2]) <= config["goal_tolerance_m"]:
            return np.array(result)
    raise ValueError("Reference did not enter goal tolerance")


def create_reference(out):
    config = json.loads((HERE/"s1_v2_scenario.json").read_text())
    poses = centerline(config)
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"scenario.json", config)
    write_json(out/"reference_protocol.json", protocol())
    write_json(out/"provenance.json", {
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True),
        "kind": "deterministic_centerline", "new_navigation_count": 0, "new_inference_count": 0,
        "scenario_sha256": sha256_file(HERE/"s1_v2_scenario.json"), "protocol_sha256": sha256_file(HERE/"s1_v2_protocol.json")})
    with (out/"agent_trajectory.csv").open("x") as stream:
        writer = csv.writer(stream)
        writer.writerow(["simulation_time_s", "x_m", "y_m", "yaw_rad", "v_m_s", "w_rad_s", "goal_distance_m"])
        for tick, pose in enumerate(poses):
            writer.writerow([tick/72, *pose, .2 if tick else 0., 0., float(np.linalg.norm(pose[:2]-config["goal_pose"][:2]))])
    print(json.dumps({"reference_rows": len(poses), "terminal_time_s": (len(poses)-1)/72, "terminal_pose": poses[-1].tolist()}))


class CorridorOnlyMonitor:
    """No obstacle exists: obstacle fields are null, not fabricated infinite clearance."""
    def __init__(self, config, out):
        validate_config(config)
        self.config = config
        self.minimum = float("inf")
        self.stop_reason = None
        self.log = (out/"clearance.jsonl").open("x")
        self.plans = (out/"planning.jsonl").open("x")
        write_json(out/"obstacle_geometry.json", {"obstacles": [], "corridor": config["corridor"],
            "agent_radius_m": config["agent_radius_m"], "required_clearance_m": config["required_clearance_m"],
            "collision": "SE(2) footprint corridor evaluation; obstacle clearance not applicable; no PhysX"})

    def observe_interval(self, start, end, v, w, time_start, duration):
        gap = corridor_clearance(start, end, v, w, duration, self.config["corridor"], self.config["agent_radius_m"])
        self.minimum = min(self.minimum, gap)
        if gap <= 0:
            self.stop_reason = "corridor_footprint_stop"
        record = {"start_sim_s": time_start, "end_sim_s": time_start+duration,
                  "lower_m": None, "upper_m": None, "geometric_overlap": False,
                  "corridor_lower_m": gap, "obstacles": {}}
        self.log.write(json.dumps(record)+"\n"); self.log.flush()
        return record

    def plan(self, identifier, metric, request):
        record = {"id": identifier, "observation_sim_s": request["observation_sim_s"],
                  "observation_pose": request["observation_pose"], "sample": 0,
                  "world_xy_m": local_to_world(metric[0], np.asarray(request["observation_pose"])).tolist(),
                  "polyline_clearance_m": None, "through_selected_index_2_clearance_m": None,
                  "selected_point_clearance_m": None, "obstacles": {},
                  "meaning": "Observation-anchored sample 0 XY; obstacle safety not applicable; not executed path"}
        self.plans.write(json.dumps(record)+"\n"); self.plans.flush()
        return record

    def finish(self, goal_entry):
        self.log.close(); self.plans.close()
        contained = self.minimum > 0
        return {"category": "goal_success" if goal_entry and contained else "corridor_failure" if not contained else "goal_failure",
                "avoidance_success": None, "geometric_overlap": False, "first_contact": None,
                "safety_margin_met": None, "minimum_swept_clearance_lower_m": None,
                "minimum_swept_clearance_upper_m": None, "minimum_corridor_clearance_lower_m": self.minimum,
                "corridor_containment_certified": contained, "passage": {}, "obstacles": {},
                "collision_detection_period_s": 1/72, "obstacle_clearance_status": "NOT_APPLICABLE_empty_obstacle_set"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-reference", type=Path, required=True)
    create_reference(parser.parse_args().create_reference)
