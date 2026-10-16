"""Passive geometric measurement only: never changes a waypoint or command."""
import json
import math
import numpy as np

from .common import integrate_se2, local_to_world, write_json


def obstacle_bounds(config):
    box = config["obstacle"]
    center = np.array(box["center_xy_m"], dtype=float)
    half = np.array(box["size_xyz_m"][:2], dtype=float) / 2
    return center - half, center + half


def point_clearance(point, lower, upper, radius):
    """Outside distance to closed AABB minus radius; inside center returns -radius."""
    return float(np.linalg.norm(np.maximum(np.maximum(lower - point, point - upper), 0)) - radius)


def segment_clearance(start, end, lower, upper, radius):
    """Exact segment/AABB distance by piecewise quadratic minimization; returns t in [0,1]."""
    start, end = np.asarray(start), np.asarray(end)
    delta = end - start
    breaks = [0., 1.]
    for axis in range(2):
        if delta[axis] != 0:
            breaks += [float((edge - start[axis]) / delta[axis]) for edge in [lower[axis], upper[axis]]
                       if 0 < (edge - start[axis]) / delta[axis] < 1]
    breaks = sorted(set(breaks))
    candidates = list(breaks)
    for a, b in zip(breaks[:-1], breaks[1:]):
        mid = start + (a + b) / 2 * delta
        active = (mid < lower) | (mid > upper)
        if active.any():
            edge = np.where(mid < lower, lower, upper)
            slope = delta[active]
            denom = float(slope @ slope)
            if denom > 0:
                t = -float((start - edge)[active] @ slope) / denom
                candidates.append(float(np.clip(t, a, b)))
    values = [point_clearance(start + t * delta, lower, upper, radius) for t in candidates]
    i = int(np.argmin(values))
    return values[i], candidates[i]


def swept_clearance(pose, v, w, duration, lower, upper, radius, threshold=.02):
    """Certified arc/chord bound, refined near decision thresholds (not just pose sampling).

    A constant-command arc lies within its chord's sagitta. Distance to a closed
    set is 1-Lipschitz, so chord_min - sagitta bounds the whole arc from below.
    Evaluating the actual arc at the chord minimizer gives an upper bound.
    Numeric slack is 1e-12 m. Fixed maximum refinement is 256 pieces.
    """
    assert abs(w * duration) <= math.pi
    pieces = 1
    while True:
        lows, highs, witnesses = [], [], []
        h = duration / pieces
        turn = abs(w * h)
        sagitta = abs(v) * h * (2 * math.sin(turn / 4)**2 / turn) if turn else 0.
        for i in range(pieces):
            a = integrate_se2(pose, v, w, i * h)[:2]
            b = integrate_se2(pose, v, w, (i + 1) * h)[:2]
            chord_gap, fraction = segment_clearance(a, b, lower, upper, radius)
            witness_time = (i + fraction) * h
            witness = integrate_se2(pose, v, w, witness_time)
            lows.append(chord_gap - sagitta - 1e-12)
            highs.append(point_clearance(witness[:2], lower, upper, radius))
            witnesses.append((witness_time, witness))
        lo, hi = min(lows), min(highs)
        uncertain = any(lo <= boundary < hi for boundary in [0., threshold])
        if not uncertain or hi - lo <= 1e-9 or pieces == 256:
            i = int(np.argmin(highs))
            return {"lower_m": float(lo), "upper_m": float(hi), "bound_width_m": float(hi-lo),
                    "pieces": pieces, "witness_offset_s": float(witnesses[i][0]),
                    "witness_pose": witnesses[i][1].tolist(), "geometric_overlap": bool(hi <= 0)}
        pieces *= 2


def first_contact_bracket(pose, v, w, duration, lower, upper, radius):
    """Earliest possible swept contact bracket, conservative to geometric/numeric bound."""
    lo, hi = 0., duration
    for _ in range(32):
        mid = (lo + hi) / 2
        bound = swept_clearance(pose, v, w, mid, lower, upper, radius)
        if bound["lower_m"] > 0:
            lo = mid
        else:
            hi = mid
    return {"offset_bracket_s": [lo, hi], "pose_at_bracket_end": integrate_se2(pose, v, w, hi).tolist(),
            "meaning": "earliest possible contact within conservative spatial bound; not PhysX contact"}


def corridor_clearance(start_pose, end_pose, v, w, duration, corridor, radius):
    gaps = [min(p[0]-corridor["xmin"], corridor["xmax"]-p[0], corridor["half_width"]-abs(p[1])) - radius
            for p in [start_pose, end_pose]]
    turn = abs(w * duration)
    sagitta = abs(v) * duration * 2 * math.sin(turn/4)**2 / turn if turn else 0.
    return float(min(gaps) - sagitta - 1e-12)


def planning_diagnostic(metric_sample, observation_pose, config):
    lower, upper = obstacle_bounds(config)
    radius = config["agent_radius_m"]
    world = local_to_world(metric_sample, np.asarray(observation_pose))
    path = np.vstack([np.asarray(observation_pose)[:2], world])
    gaps = [segment_clearance(a, b, lower, upper, radius)[0] for a, b in zip(path[:-1], path[1:])]
    return {"sample": 0, "world_xy_m": world.tolist(), "polyline_clearance_m": float(min(gaps)),
            "through_selected_index_2_clearance_m": float(min(gaps[:3])),
            "selected_point_clearance_m": point_clearance(world[2], lower, upper, radius),
            "meaning": "sample 0 polyline at observation pose; diagnostic only; no waypoint times or execution claim"}


class ObstacleMonitor:
    def __init__(self, config, out):
        self.config, self.out = config, out
        self.lower, self.upper = obstacle_bounds(config)
        self.radius = config["agent_radius_m"]
        self.log = (out / "clearance.jsonl").open("x")
        self.plans = (out / "planning.jsonl").open("x")
        self.minimum = float("inf")
        self.minimum_upper = float("inf")
        self.corridor_minimum = float("inf")
        self.first_contact = None
        self.overlap = False
        self.margin_met = True
        self.stop_reason = None
        self.crossing = None
        write_json(out / "obstacle_geometry.json", {**config["obstacle"], "aabb_min_xy_m": self.lower.tolist(),
                   "aabb_max_xy_m": self.upper.tolist(), "agent_radius_m": self.radius,
                   "required_clearance_m": config["required_clearance_m"], "collision": "geometry only; no PhysX"})

    def observe_interval(self, start, end, v, w, time_start, duration):
        gap = swept_clearance(start, v, w, duration, self.lower, self.upper, self.radius,
                              self.config["required_clearance_m"])
        corridor_gap = corridor_clearance(start, end, v, w, duration, self.config["corridor"], self.radius)
        self.minimum = min(self.minimum, gap["lower_m"])
        self.minimum_upper = min(self.minimum_upper, gap["upper_m"])
        self.corridor_minimum = min(self.corridor_minimum, corridor_gap)
        self.overlap |= gap["geometric_overlap"]
        self.margin_met &= gap["lower_m"] >= self.config["required_clearance_m"]
        if gap["lower_m"] <= 0 and self.first_contact is None:
            self.first_contact = {"interval_start_s": time_start, "detected_sim_s": time_start + duration,
                                  "detected_pose": list(end), **gap,
                                  **first_contact_bracket(start, v, w, duration, self.lower, self.upper, self.radius)}
            self.stop_reason = "geometric_collision" if gap["geometric_overlap"] else "conservative_contact_stop"
        elif corridor_gap <= 0:
            self.stop_reason = "corridor_footprint_stop"
        # Passage is completed only when the whole circle clears the far X face.
        far_x = self.upper[0] + self.radius
        if self.crossing is None and start[0] < far_x <= end[0]:
            side = "left_positive_y" if end[1] > self.upper[1] else "right_negative_y" if end[1] < self.lower[1] else "center"
            self.crossing = {"side": side, "simulation_time_s": time_start + duration, "pose": list(end)}
        self.log.write(json.dumps({"start_sim_s": time_start, "end_sim_s": time_start+duration,
                                  "start_pose": list(start), "end_pose": list(end), "v": v, "w": w,
                                  "corridor_lower_m": corridor_gap, **gap}) + "\n")
        self.log.flush()

    def plan(self, identifier, metric, request):
        diagnostic = planning_diagnostic(metric[0], request["observation_pose"], self.config)
        self.plans.write(json.dumps({"id": identifier, "observation_sim_s": request["observation_sim_s"],
                                    "observation_pose": request["observation_pose"], **diagnostic}) + "\n")
        self.plans.flush()

    def finish(self, goal_entry):
        self.log.close(); self.plans.close()
        compliant = self.margin_met and self.corridor_minimum > 0 and self.first_contact is None
        category = ("avoidance_and_goal_success" if goal_entry and compliant else
                    "collision_or_safety_margin_failure" if not compliant else "no_collision_goal_failure")
        return {"category": category, "avoidance_success": bool(goal_entry and compliant),
                "geometric_overlap": bool(self.overlap), "first_contact": self.first_contact,
                "minimum_swept_clearance_lower_m": self.minimum, "minimum_swept_clearance_upper_m": self.minimum_upper,
                "safety_margin_met": bool(self.margin_met), "minimum_corridor_clearance_lower_m": self.corridor_minimum,
                "corridor_containment_certified": self.corridor_minimum > 0,
                "passage": self.crossing, "collision_detection_period_s": 1/self.config["integration_hz"]}
