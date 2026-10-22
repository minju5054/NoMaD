"""Frozen S1 placement and observation-gated information metadata, never control."""
import json
from pathlib import Path

import numpy as np

from nomad_isaac.common import ROOT, sha256_file
from nomad_isaac.clearance import configured_obstacles, obstacle_bounds, point_clearance, single_obstacle_config

HERE = Path(__file__).parent


def is_s1(config):
    return config.get("experiment_mode") == "phase1_s1_forward_ray"


def protocol():
    return json.loads((HERE/"s1_protocol.json").read_text())


def validate_options(args):
    p = protocol()
    if (not getattr(args, "s1_mode", False) or not args.pure_pursuit or not args.asynchronous
            or not args.topomap or args.prepare_only or args.oracle_safety_stop or args.early_obstacle_mode
            or args.controlled_delivery_delay or args.render_topomap_reference
            or args.seed_offset or args.run_id is not None
            or args.uniform_delivery_delay_s not in p["delay_candidates_s"]
            or args.s1_distance_m not in p["distance_candidates_m"]):
        raise ValueError("S1 requires frozen PP/Topomap/async, explicit uniform delay and distance; no other mode")
    if json.loads(Path(args.scenario).read_text()) != json.loads((HERE/"s1_scenario.json").read_text()):
        raise ValueError("S1 scenario differs from the frozen template")
    if sha256_file(args.topomap) != p["topomap_manifest_sha256"]:
        raise ValueError("S1 requires the existing 14-node 2s Topomap")
    config = json.loads(Path(args.scenario).read_text())
    base = json.loads((ROOT/"research/nomad_isaac/two_obstacles_wide_wall_scenario.json").read_text())
    assert {k: v for k, v in config.items() if k not in ("name", "dynamic_obstacle", "experiment_mode")} == {k: v for k, v in base.items() if k != "name"}


def triggered(config, pose):
    region = config["dynamic_obstacle"]["placement"]["trigger_region_xy_m"]
    return region["x"][0] <= pose[0] <= region["x"][1] and region["y"][0] <= pose[1] <= region["y"][1]


def ray_surface_distance(pose, lower, upper, radius):
    """Slab intersection along unit yaw ray, measured from circular front edge."""
    u = np.array([np.cos(pose[2]), np.sin(pose[2])])
    near, far = -np.inf, np.inf
    for axis in range(2):
        if abs(u[axis]) < 1e-15:
            if not lower[axis] <= pose[axis] <= upper[axis]:
                return None
        else:
            a, b = sorted(((lower[axis]-pose[axis])/u[axis], (upper[axis]-pose[axis])/u[axis]))
            near, far = max(near, a), min(far, b)
    return float(near-radius) if far >= max(near, 0.) else None


def place_forward(config, pose):
    """Only current pose and frozen geometry; no command/prediction/future inputs."""
    pose = np.asarray(pose, dtype=float)
    box = dict(config["dynamic_obstacle"])
    settings = box["placement"]
    d = settings["forward_clearance_m"]
    assert d in protocol()["distance_candidates_m"]
    u = np.array([np.cos(pose[2]), np.sin(pose[2])])
    half = np.array(box["size_xyz_m"][:2])/2
    half_ray = min(half[i]/abs(u[i]) for i in range(2) if abs(u[i]) > 1e-15)
    center = pose[:2]+u*(config["agent_radius_m"]+d+half_ray)
    box["center_xy_m"] = center.tolist()
    lo, hi = center-half, center+half
    measured = ray_surface_distance(pose, lo, hi, config["agent_radius_m"])
    assert measured is not None and abs(measured-d) < 1e-12
    c = config["corridor"]
    wall_gap = float(min(lo[0]-c["xmin"], c["xmax"]-hi[0], lo[1]+c["half_width"], c["half_width"]-hi[1]))
    overlaps, separations = [], {}
    for static in configured_obstacles(config):
        a, b = obstacle_bounds(single_obstacle_config(config, static))
        if np.all(hi >= a) and np.all(b >= lo):
            overlaps.append(static["id"])
        separations[static["id"]] = float(np.linalg.norm(np.maximum(np.maximum(a-hi, lo-b), 0.)))
    gap = point_clearance(pose[:2], lo, hi, config["agent_radius_m"])
    reasons = (["static_AABB_overlap"] if overlaps else []) + (["box_outside_corridor"] if wall_gap < 0 else [])
    if gap < config["required_clearance_m"]:
        reasons.append("spawn_footprint_margin_violation")
    return {"status": "PLACEMENT_INFEASIBLE" if reasons else "PLACED", "reasons": reasons,
            "obstacle": box, "spawn_pose": pose.tolist(), "configured_d_m": d,
            "measured_forward_ray_d_m": measured, "center_distance_m": float(np.linalg.norm(center-pose[:2])),
            "footprint_euclidean_clearance_m": gap, "box_corridor_clearance_m": wall_gap,
            "overlap_static_ids": overlaps, "static_surface_separation_m": separations,
            "placement_inputs": "current SE2 pose and fixed geometry only",
            "side_feasibility": "PENDING_offline_actual_spawn_search"}


class VisibilityGate:
    """Release metadata after the next *captured* RGB following first visibility."""
    def __init__(self):
        self.first_visible = None
        self.available = None

    def observe(self, record):
        stamp = {k: record[k] for k in ("observation_id", "observation_sim_s", "capture_end_monotonic_ns", "frame_sha256", "rgb_file")}
        if self.first_visible is not None and self.available is None:
            assert record["observation_id"] > self.first_visible["observation_id"]
            self.available = stamp
        if self.first_visible is None and record["dynamic"]["active"] and record["dynamic"]["visible"]:
            self.first_visible = stamp
        return {"geometry_available": self.available is not None,
                "first_visible": self.first_visible, "available_from": self.available,
                "used_for_control": False, "clock": "capture completion host monotonic; sim time is pose snapshot only"}
