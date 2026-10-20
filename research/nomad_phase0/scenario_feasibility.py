"""Bounded offline witness search; no model, simulator, controller or recovery."""
import argparse
from dataclasses import dataclass
import heapq
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np

from nomad_isaac.common import ROOT, integrate_se2, sha256_file, write_json
from nomad_isaac.clearance import (
    configured_obstacles, corridor_clearance, obstacle_bounds, point_clearance,
    single_obstacle_config, swept_clearance,
)

PROTOCOL = Path(__file__).with_name("feasibility_protocol.json")


class InvalidScenario(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise InvalidScenario(reason)


class Scene:
    def __init__(self, config, dynamic_state):
        require(isinstance(config, dict), "Scenario must be a JSON object")
        self.config = config
        require(dynamic_state in ("absent", "active"), "Explicit dynamic state required")
        self.radius = float(config["agent_radius_m"])
        self.margin = float(config["required_clearance_m"])
        require(self.radius == .09 and self.margin == .02, "Phase 0-A requires radius .09 / clearance .02 m")
        require(config["max_v"] == .2 and config["max_w"] == .4, "Scenario kinematic bounds differ")
        self.start, self.goal = [np.asarray(config[k], dtype=float) for k in ("start_pose", "goal_pose")]
        require(all(p.shape == (3,) and np.isfinite(p).all() for p in (self.start, self.goal)),
                "Start/goal must be finite SE(2) poses")
        self.tolerance = float(config["goal_tolerance_m"])
        require(math.isfinite(self.tolerance) and self.tolerance > 0, "Invalid goal disk radius")
        self.corridor = config["corridor"]
        x0, x1, h = [float(self.corridor[k]) for k in ("xmin", "xmax", "half_width")]
        require(np.isfinite([x0, x1, h]).all() and x1-x0 > 2*self.radius and h > self.radius,
                "Invalid corridor")
        self.dynamic = config.get("dynamic_obstacle") if dynamic_state == "active" else None
        require(dynamic_state != "active" or self.dynamic is not None, "Active dynamic box missing")
        if self.dynamic:
            require("center_xy_m" in self.dynamic, "Active geometry must have a fixed world center")
        raw_boxes = list(configured_obstacles(config))
        if self.dynamic:
            raw_boxes.append(self.dynamic)
        self.boxes = list(configured_obstacles({"obstacles": raw_boxes}))
        self.bounds = [(b["id"], *obstacle_bounds(single_obstacle_config(config, b))) for b in self.boxes]
        require(self.point_safe(self.start), "Start violates obstacle margin or corridor containment")
        # A goal center need not be safe if another point of the disk is reachable.
        center_domain_lo = np.array([x0+self.radius, -h+self.radius])
        center_domain_hi = np.array([x1-self.radius, h-self.radius])
        require(point_clearance(self.goal[:2], center_domain_lo, center_domain_hi, 0.) < self.tolerance,
                "Goal region has no intersection with corridor center domain")

    def point_safe(self, pose):
        return (corridor_clearance(pose, pose, 0, 0, 0, self.corridor, self.radius) > 0
                and all(point_clearance(pose[:2], lo, hi, self.radius) >= self.margin
                        for _, lo, hi in self.bounds))

    def interval(self, pose, v, w, duration, *, final=False):
        end = integrate_se2(pose, v, w, duration)
        wall = corridor_clearance(pose, end, v, w, duration, self.corridor, self.radius)
        lower, overlap = {}, False
        for name, lo, hi in self.bounds:
            # 1-Lipschitz distance bound safely skips remote boxes in search only.
            bound = point_clearance(pose[:2], lo, hi, self.radius)-abs(v)*duration-1e-12
            if not final and bound >= self.margin:
                lower[name] = bound
            else:
                gap = swept_clearance(pose, v, w, duration, lo, hi, self.radius, self.margin)
                lower[name] = gap["lower_m"]
                overlap |= gap["geometric_overlap"]
        return end, {"safe": bool(wall > 0 and all(x >= self.margin for x in lower.values())),
                     "obstacle_lower_m": lower, "corridor_lower_m": wall, "overlap": overlap}

    def geometry(self):
        goal_gaps = {name: point_clearance(self.goal[:2], lo, hi, self.radius)
                     for name, lo, hi in self.bounds}
        goal_wall = corridor_clearance(self.goal, self.goal, 0, 0, 0, self.corridor, self.radius)
        gaps = []
        for i, (name, lo, hi) in enumerate(self.bounds):
            for other, lo2, hi2 in self.bounds[i+1:]:
                separation = np.maximum(np.maximum(lo2-hi, lo-hi2), 0)
                width = float(np.linalg.norm(separation))
                gaps.append({"boxes": [name, other], "actual_surface_gap_m": width,
                             "axis_separations_m": separation.tolist(),
                             "required_two_obstacle_width_m": 2*(self.radius+self.margin),
                             "width_deficit_m": max(0., 2*(self.radius+self.margin)-width),
                             "interpretation": "Local gap only; not a proof that all routes are blocked"})
        return {"start_pose": self.start.tolist(), "goal_pose_metadata": self.goal.tolist(),
                "goal_region": {"center_xy": self.goal[:2].tolist(), "radius_m": self.tolerance,
                                "yaw_required": False, "center_safe": self.point_safe(self.goal),
                                "entire_disk_certified_safe": bool(goal_wall > self.tolerance and
                                    all(g-self.tolerance >= self.margin for g in goal_gaps.values())),
                                "center_obstacle_clearance_m": goal_gaps},
                "corridor": self.corridor, "agent_radius_m": self.radius,
                "required_obstacle_clearance_m": self.margin,
                "required_corridor_footprint_clearance_m": 0.,
                "obstacles": [{"id": name, "aabb_min_xy_m": lo.tolist(), "aabb_max_xy_m": hi.tolist(),
                               "size_xyz_m": box["size_xyz_m"]}
                              for box, (name, lo, hi) in zip(self.boxes, self.bounds)],
                "dynamic_state": "active" if self.dynamic else "absent",
                "pair_gaps": gaps,
                "scope": "Frozen geometry including active dynamic box; no spawn-time feasibility claim"}


def x_extrema_times(pose, w, duration):
    times = [0., duration]
    if w:
        a, b = sorted((pose[2], pose[2]+w*duration))
        for n in range(math.floor((a-math.pi/2)/math.pi), math.ceil((b-math.pi/2)/math.pi)+1):
            t = (math.pi/2+n*math.pi-pose[2])/w
            if 0 < t < duration:
                times.append(t)
    return times


def side_transition(scene, side, passed, pose, v, w, duration):
    """One-pass topology, not world-X-monotone driving: no center-plane recross."""
    if side is None:
        return passed, None
    lo, hi = obstacle_bounds(single_obstacle_config(scene.config, scene.dynamic))
    plane = float(scene.dynamic["center_xy_m"][0])
    end = integrate_se2(pose, v, w, duration)
    xs = [integrate_se2(pose, v, w, t)[0] for t in x_extrema_times(pose, w, duration)]
    if passed:
        return (True, None) if min(xs) >= plane-1e-12 else (None, None)
    if end[0] <= plane:
        return (False, None) if max(xs) <= plane+1e-12 else (None, None)
    # Endpoints straddle plane and a primitive turns < pi: a unique positive crossing.
    a, b = 0., duration
    for _ in range(42):
        mid = (a+b)/2
        if integrate_se2(pose, v, w, mid)[0] < plane:
            a = mid
        else:
            b = mid
    crossing = integrate_se2(pose, v, w, (a+b)/2)
    q = scene.radius+scene.margin
    valid = crossing[1] >= hi[1]+q if side == "left_positive_y" else crossing[1] <= lo[1]-q
    return (True, crossing.tolist()) if valid else (None, None)


def side_certificate(scene, side):
    """Sufficient axis-aligned trapped-pocket certificate; never gap-only inference.

    Within x >= dynamic center plane, the chosen-side pocket is enclosed by
    dynamic+static inflated boxes, a static box reaching the corridor wall,
    and the no-recross plane. A horizontal section and vertical section are
    explicitly covered by forbidden center positions. Rounded AABB corners
    are not approximated by square inflation: both sections lie inside raw Y.
    """
    d = scene.dynamic
    dl, du = obstacle_bounds(single_obstacle_config(scene.config, d))
    cx, cy = map(float, d["center_xy_m"])
    q = scene.radius+scene.margin
    for name, lo, hi in scene.bounds:
        if name == d["id"] or lo[0] < du[0]:
            continue
        xwall = float((lo[0]+hi[0])/2)
        positive = side == "left_positive_y"
        touches_wall = hi[1] >= scene.corridor["half_width"] if positive else lo[1] <= -scene.corridor["half_width"]
        if not (lo[1] <= cy <= hi[1] and touches_wall and lo[0]-du[0] < 2*q
                and scene.goal[0]-scene.tolerance > xwall):
            continue
        return {"status": "GEOMETRICALLY_BLOCKED", "termination_reason": "CERTIFIED_ONE_PASS_SIDE_POCKET",
                "proof": {"scope": side+" one-pass routes only; not global scene infeasibility",
                          "no_recross_plane_x_m": cx, "horizontal_separator_y_m": cy,
                          "horizontal_forbidden_intervals_x_m": [[cx, float(du[0]+q)],
                                                                 [float(lo[0]-q), xwall]],
                          "strict_interval_overlap_m": float(2*q-(lo[0]-du[0])),
                          "vertical_separator_x_m": xwall,
                          "vertical_raw_obstacle_y_m": [float(lo[1]), float(hi[1])],
                          "closed_corridor_side": "+Y" if positive else "-Y",
                          "static_obstacle": name,
                          "goal_disk_min_x_m": float(scene.goal[0]-scene.tolerance),
                          "argument": "Side crossing enters pocket. Bottom/top section and right section are forbidden, corridor closes outer side, and returning west would violate one-pass. Entire goal disk is beyond right section."},
                "search_executed": False, "goal_reached": False, "witness": None}
    return None


@dataclass
class Node:
    pose: np.ndarray
    parent: int
    primitive: int
    cost: float
    passed: bool


def verify_witness(scene, nodes, end_id, primitives, duration, side, minimum_v=0.):
    ids = []
    while end_id >= 0:
        ids.append(end_id)
        end_id = nodes[end_id].parent
    ids.reverse()
    pose = scene.start.copy()
    passed = False
    crossings, commands, poses = [], [], [pose.tolist()]
    minima = {name: float("inf") for name, _, _ in scene.bounds}
    wall_min = float("inf")
    max_error = 0.
    for identifier in ids[1:]:
        n = nodes[identifier]
        v, w = primitives[n.primitive]
        assert minimum_v <= v <= .2 and abs(w) <= .4
        end, checks = scene.interval(pose, v, w, duration, final=True)
        assert checks["safe"] and not checks["overlap"]
        max_error = max(max_error, float(np.max(np.abs(end-n.pose))))
        passed, cross = side_transition(scene, side, passed, pose, v, w, duration)
        assert passed is not None
        if cross:
            crossings.append(cross)
        for name, value in checks["obstacle_lower_m"].items():
            minima[name] = min(minima[name], value)
        wall_min = min(wall_min, checks["corridor_lower_m"])
        commands.append([v, w, duration])
        poses.append(end.tolist())
        pose = end
    # Include point-only start=goal witnesses without Infinity in JSON.
    if not commands:
        _, checks = scene.interval(pose, 0., 0., 0., final=True)
        minima, wall_min = checks["obstacle_lower_m"], checks["corridor_lower_m"]
    distance = float(np.linalg.norm(pose[:2]-scene.goal[:2]))
    assert distance <= scene.tolerance and max_error <= 1e-12
    if side:
        _, du = obstacle_bounds(single_obstacle_config(scene.config, scene.dynamic))
        assert passed and len(crossings) == 1 and pose[0] >= du[0]+scene.radius+scene.margin
    return {"poses_se2": poses, "commands_v_w_duration": commands, "side_crossing_pose": crossings,
            "minimum_obstacle_clearance_m": minima, "minimum_corridor_footprint_clearance_m": wall_min,
            "goal_distance_m": distance, "goal_reached": True,
            "path_duration_s": sum(c[2] for c in commands),
            "distance_m": sum(abs(c[0])*c[2] for c in commands),
            "pose_reconstruction_max_error": max_error,
            "validation": "Every original continuous arc rechecked by swept_clearance and corridor_clearance"}


def search(scene, settings, side=None):
    start_clock = time.monotonic()
    start_cpu = time.process_time()
    budget_clock = settings.get("time_budget_clock", "wall")
    assert budget_clock in ("wall", "cpu")
    minimum_v = settings.get("minimum_v_m_s", 0.)
    assert minimum_v in (0., -.2)
    primitives, duration = settings["primitives_vw"], settings["primitive_duration_s"]
    assert all(minimum_v <= v <= .2 and abs(w) <= .4 for v, w in primitives)
    nodes = [Node(scene.start.copy(), -1, -1, 0., False)]
    def key(n):
        return (int(math.floor(n.pose[0]/settings["xy_bin_m"])),
                int(math.floor(n.pose[1]/settings["xy_bin_m"])),
                int(math.floor((n.pose[2]+math.pi) % (2*math.pi)/(2*math.pi)*settings["heading_bins"])),
                n.passed)
    def heuristic(p):
        return max(0., np.linalg.norm(p[:2]-scene.goal[:2])-scene.tolerance)/.2
    best = {key(nodes[0]): 0}
    heap = [(settings["heuristic_weight"]*heuristic(scene.start), 0)]
    expanded, generated, reason, witness = 0, 1, "OPEN_SET_EXHAUSTED", None
    while heap:
        if expanded >= settings["max_expansions_per_search"]:
            reason = "EXPANSION_BUDGET"; break
        elapsed = time.process_time()-start_cpu if budget_clock == "cpu" else time.monotonic()-start_clock
        budget = settings["max_cpu_seconds_per_search"] if budget_clock == "cpu" else settings["max_wall_seconds_per_search"]
        if elapsed >= budget:
            reason = "CPU_TIME_BUDGET" if budget_clock == "cpu" else "WALL_TIME_BUDGET"; break
        _, idx = heapq.heappop(heap)
        n = nodes[idx]
        if best.get(key(n)) != idx:
            continue
        if np.linalg.norm(n.pose[:2]-scene.goal[:2]) <= scene.tolerance and (side is None or n.passed):
            witness = verify_witness(scene, nodes, idx, primitives, duration, side, minimum_v)
            reason = "GOAL_WITNESS_REVALIDATED"; break
        expanded += 1
        if n.cost+duration > settings["max_path_duration_s"]:
            continue
        for pi, (v, w) in enumerate(primitives):
            end = integrate_se2(n.pose, v, w, duration)
            if not scene.point_safe(end):
                continue
            passed, _ = side_transition(scene, side, n.passed, n.pose, v, w, duration)
            if passed is None:
                continue
            child = Node(end, idx, pi, n.cost+duration, passed)
            k = key(child)
            if k in best and nodes[best[k]].cost <= child.cost:
                continue
            _, checks = scene.interval(n.pose, v, w, duration)
            if not checks["safe"]:
                continue
            nodes.append(child); child_id = len(nodes)-1; best[k] = child_id
            heapq.heappush(heap, (child.cost+settings["heuristic_weight"]*heuristic(end), child_id))
            generated += 1
    return {"status": "FEASIBLE" if witness else "NO_PATH_FOUND", "termination_reason": reason,
            "search_executed": True, "expanded": expanded, "generated": generated,
            "wall_seconds": time.monotonic()-start_clock, "cpu_seconds": time.process_time()-start_cpu,
            "time_budget_clock": budget_clock, "goal_reached": witness is not None,
            "witness": witness, "no_path_meaning": None if witness else "No witness within this discretized bounded search; not impossibility"}


def check(path, dynamic_state):
    path = Path(path)
    protocol = json.loads(PROTOCOL.read_text())
    report = {"scenario_path": str(path.resolve()), "scenario_sha256": None,
              "protocol": protocol, "protocol_sha256": sha256_file(PROTOCOL),
              "source_sha256": {name: sha256_file(ROOT/name) for name in
                               ("research/nomad_phase0/scenario_feasibility.py",
                                "research/nomad_isaac/common.py", "research/nomad_isaac/clearance.py")},
              "source_git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()}
    try:
        report["scenario_sha256"] = sha256_file(path)
        scene = Scene(json.loads(path.read_text()), dynamic_state)
    except (OSError, ValueError, TypeError, KeyError, AssertionError, OverflowError) as exc:
        return {**report, "status": "INVALID_SCENARIO", "reason": str(exc) or type(exc).__name__}
    report["geometry"] = scene.geometry()
    if not scene.dynamic:
        result = search(scene, protocol["search"])
        return {**report, "status": result["status"], "unconstrained": result,
                "sides": {"left_positive_y": None, "right_negative_y": None},
                "side_scope": "Not applicable: no active dynamic obstacle"}
    dl, du = obstacle_bounds(single_obstacle_config(scene.config, scene.dynamic))
    q = scene.radius+scene.margin
    # Side topology only has a defined meaning for west-to-east scenarios.
    if not (scene.start[0] < dl[0]-q and scene.goal[0]-scene.tolerance > du[0]+q):
        return {**report, "status": "NO_PATH_FOUND", "reason": "SIDE_DOMAIN_UNSUPPORTED",
                "sides": {side: {"status": "NO_PATH_FOUND", "termination_reason": "SIDE_DOMAIN_UNSUPPORTED"}
                          for side in ("left_positive_y", "right_negative_y")}}
    sides = {}
    for side in ("left_positive_y", "right_negative_y"):
        sides[side] = side_certificate(scene, side) or search(scene, protocol["search"], side)
    return {**report, "status": "FEASIBLE" if any(x["status"] == "FEASIBLE" for x in sides.values()) else "NO_PATH_FOUND",
            "sides": sides, "side_scope": protocol["search"]["side_rule"],
            "global_blockage_claim": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--dynamic-state", choices=("absent", "active"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = check(args.scenario, args.dynamic_state)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(json.dumps({"status": result["status"], "sides": {k: v["status"] if v else None
          for k, v in result.get("sides", {}).items()}, "output": str(args.output)}))


if __name__ == "__main__":
    main()
