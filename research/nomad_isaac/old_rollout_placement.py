"""One deterministic scene-placement decision from current OLD state, never a planner."""
import math

import numpy as np

from .clearance import (configured_obstacles, corridor_clearance, obstacle_bounds,
                        point_clearance, segment_clearance, single_obstacle_config, swept_clearance)
from .common import integrate_se2


def magenta_mask(rgb):
    rgb = np.asarray(rgb, dtype=float)
    return ((rgb[..., 0] > 1.5*rgb[..., 1]) & (rgb[..., 2] > 1.5*rgb[..., 1]) &
            (rgb[..., 0] > 40) & (rgb[..., 2] > 40))


def wall_gap(lower, upper, corridor):
    return float(min(lower[0]-corridor["xmin"], corridor["xmax"]-upper[0],
                     lower[1]+corridor["half_width"], corridor["half_width"]-upper[1]))


def free_strips(lower, upper, static_bounds, config):
    p = config["dynamic_obstacle"]["placement"]
    width, extension = p["bypass_strip_width_m"], p["bypass_strip_end_extension_m"]
    strips = []
    for axis in (0, 1):
        for side in (-1, 1):
            lo, hi = lower.copy(), upper.copy()
            lo[1-axis] -= extension; hi[1-axis] += extension
            lo[axis], hi[axis] = ((upper[axis], upper[axis]+width) if side > 0 else
                                  (lower[axis]-width, lower[axis]))
            overlap = any(np.all(lo < b) and np.all(hi > a) for a, b in static_bounds)
            clear = wall_gap(lo, hi, config["corridor"]) >= 0 and not overlap
            strips.append({"side": ("X" if axis == 0 else "Y")+("+" if side > 0 else "-"),
                           "lower_xy_m": lo.tolist(), "upper_xy_m": hi.tolist(), "free": bool(clear)})
    return strips


def place_on_old(config, pose, v, w, old_id, old_valid, remaining_s):
    """Inputs contain no prediction, FRESH, future pose, or goal outcome."""
    dynamic = config["dynamic_obstacle"]; rule = dynamic["placement"]
    pose = np.asarray(pose, dtype=float)
    result = {"status": "PLACEMENT_INFEASIBLE", "pose": pose.tolist(), "old_id": old_id,
              "old_command_vw": [float(v), float(w)], "old_command_valid": bool(old_valid),
              "old_remaining_timeout_s": float(remaining_s), "candidates": [], "obstacle": None,
              "meaning": "Counterfactual unchanged OLD command, clipped to current receive-based timeout; not actual future motion"}
    if not old_valid or old_id < 0 or remaining_s <= rule["reaction_budget_s"] or v < rule["minimum_speed_m_s"]:
        result["reason"] = "invalid_old_or_insufficient_timeout_or_speed"
        return result
    assert 0 < remaining_s <= 1.0
    radius, margin = config["agent_radius_m"], config["required_clearance_m"]
    static_bounds = [obstacle_bounds(single_obstacle_config(config, box)) for box in configured_obstacles(config)]
    static_gap = min(swept_clearance(pose, v, w, remaining_s, lo, hi, radius, margin)["lower_m"]
                     for lo, hi in static_bounds)
    end = integrate_se2(pose, v, w, remaining_s)
    corridor = corridor_clearance(pose, end, v, w, remaining_s, config["corridor"], radius)
    for distance in rule["lookahead_arc_lengths_m"]:
        duration = distance/v
        center = integrate_se2(pose, v, w, duration)[:2]
        box = {k: value for k, value in dynamic.items() if k != "placement"}
        box["center_xy_m"] = center.tolist()
        lower, upper = obstacle_bounds(single_obstacle_config(config, box))
        delta = center-pose[:2]; c, s = np.cos(pose[2]), np.sin(pose[2])
        local = delta @ np.array([[c, -s], [s, c]])
        bearing = float(np.degrees(np.arctan2(local[1], local[0])))
        spawn_gap = point_clearance(pose[:2], lower, upper, radius)
        reaction = swept_clearance(pose, v, w, rule["reaction_budget_s"], lower, upper, radius, margin)
        rollout = swept_clearance(pose, v, w, remaining_s, lower, upper, radius, margin)
        separation = min(float(np.linalg.norm(np.maximum(np.maximum(a-upper, lower-b), 0))) for a, b in static_bounds)
        sight_gap = min(segment_clearance(pose[:2], center, a, b, 0.)[0] for a, b in static_bounds)
        strips = free_strips(lower, upper, static_bounds, config)
        checks = {"bounded_lookahead": duration <= rule["maximum_center_lookahead_s"],
                  "spawn_reaction_distance": spawn_gap >= rule["minimum_spawn_clearance_m"],
                  "reaction_window_safe": reaction["lower_m"] >= margin,
                  "collision_before_old_timeout": rollout["geometric_overlap"],
                  "static_old_continuation_safe": static_gap >= margin and corridor > 0,
                  "camera_center_in_front": local[0] > 0 and abs(bearing) <= rule["maximum_center_bearing_deg"],
                  "unoccluded_center_ray": sight_gap > 0,
                  "static_box_separation": separation >= rule["minimum_box_separation_m"],
                  "box_wall_separation": wall_gap(lower, upper, config["corridor"]) >= rule["minimum_box_separation_m"],
                  "local_bypass_space": any(strip["free"] for strip in strips)}
        candidate = {"arc_length_m": distance, "center_lookahead_s": float(duration), "center_xy_m": center.tolist(),
                     "relative_center_forward_left_m": local.tolist(), "center_bearing_deg": bearing,
                     "spawn_clearance_m": spawn_gap, "reaction_window": reaction, "timeout_clipped_rollout": rollout,
                     "static_rollout_clearance_m": static_gap, "rollout_corridor_clearance_m": corridor,
                     "box_static_separation_m": separation, "bypass_strips": strips,
                     "checks": {k: bool(value) for k, value in checks.items()}}
        result["candidates"].append(candidate)
        if all(checks.values()):
            ts = np.r_[np.arange(0., remaining_s, 1/config["integration_hz"]), remaining_s]
            result.update({"status": "PLACED", "reason": "first_valid_candidate", "obstacle": box,
                           "selected_candidate_index": len(result["candidates"])-1,
                           "rollout_offset_s": ts.tolist(),
                           "rollout_pose": [integrate_se2(pose, v, w, t).tolist() for t in ts]})
            return result
    result["reason"] = "no_candidate_passed_all_fixed_checks"
    return result
