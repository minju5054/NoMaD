"""Unchanged required SE(2) factor definitions extracted from commit 3a60531.

Source AST equality is checked before execution; no offline driver is imported.
"""
import numpy as np
from .common import integrate_se2, local_to_world, original_controller
from .clearance import (configured_obstacles, corridor_clearance, obstacle_bounds,
                        segment_clearance, single_obstacle_config, swept_clearance)
from .handoff_audit import path_safety

def wrap(a):
    return (np.asarray(a) + np.pi) % (2 * np.pi) - np.pi

def local_point(world, frame):
    c, s = np.cos(frame[2]), np.sin(frame[2])
    return (np.asarray(world) - frame[:2]) @ np.array([[c, -s], [s, c]])

def between(a, b):
    return np.r_[local_point(b[:2], a), wrap(b[2] - a[2])]

def se2_log(pose):
    """SE(2) logarithm: V(theta)^-1 translation, wrapped rotation."""
    angle = float(wrap(pose[2]))
    a = np.sinc(angle / np.pi)
    b = angle / 2 * np.sinc(angle / (2 * np.pi))**2
    return np.r_[np.array([[a, b], [-b, a]]) @ pose[:2] / (a*a + b*b), angle]

def derived_headings(xy):
    delta = np.diff(xy, axis=0)
    headings = np.unwrap(np.arctan2(delta[:, 1], delta[:, 0]))
    return np.r_[headings, headings[-1]], np.linalg.norm(delta, axis=1)

class Experiment:
    def __init__(self, initial, boundary, config, protocol):
        self.initial, self.boundary, self.config, self.p = initial, boundary, config, protocol
        self.controller = original_controller()
        self.boxes = {box["id"]: obstacle_bounds(single_obstacle_config(config, box))
                      for box in configured_obstacles(config)}
        self.relative = [between(a, b) for a, b in zip(initial[:-1], initial[1:])]
        self.radius = protocol["radius_m"]
        self.dt = 1 / protocol["integration_hz"]
        self.calls = 0

    def rollout(self, command):
        v, w = map(float, command)
        poses, intervals = [self.boundary.copy()], []
        for _ in range(self.p["horizon_ticks"]):
            end = integrate_se2(poses[-1], v, w, self.dt)
            boxes = {key: swept_clearance(poses[-1], v, w, self.dt, lo, hi, self.radius,
                                         self.p["required_clearance_m"])
                     for key, (lo, hi) in self.boxes.items()}
            corridor = corridor_clearance(poses[-1], end, v, w, self.dt, self.config["corridor"], self.radius)
            intervals.append({"obstacles": boxes, "corridor_lower_m": corridor})
            poses.append(end)
        per_box = {key: min(row["obstacles"][key]["lower_m"] for row in intervals) for key in self.boxes}
        upper = min(row["obstacles"][key]["upper_m"] for row in intervals for key in self.boxes)
        corridor = min(row["corridor_lower_m"] for row in intervals)
        minimum = min(per_box.values())
        return {"command_vw": [v, w], "minimum_clearance_m": minimum, "minimum_upper_m": upper,
                "obstacles": per_box, "minimum_corridor_m": corridor,
                "margin_met": minimum >= self.p["required_clearance_m"],
                "geometric_overlap": any(r["obstacles"][key]["geometric_overlap"] for r in intervals for key in self.boxes),
                "safe": minimum >= self.p["required_clearance_m"] and corridor > 0,
                "distance_m": abs(v) * self.p["horizon_ticks"] * self.dt,
                "end_pose": poses[-1].tolist(), "poses": np.array(poses).tolist(), "intervals": intervals}

    def groups(self, poses):
        p = self.p
        scale = lambda name: np.array([p[name+"_sigma_xy_m"], p[name+"_sigma_xy_m"],
                                       np.radians(p[name+"_sigma_yaw_deg"])])
        group = {}
        group["fresh_prior"] = np.concatenate([se2_log(between(f, x)) / scale("prior")
                                               for f, x in zip(self.initial, poses)])
        group["relative_pose"] = np.concatenate([se2_log(between(z, between(a, b))) / scale("relative")
                                                 for z, a, b in zip(self.relative, poses[:-1], poses[1:])])
        group["boundary"] = se2_log(between(self.boundary, poses[0])) / scale("boundary")
        tangents, lengths = derived_headings(poses[:, :2])
        group["heading_tangent"] = wrap(poses[:, 2] - tangents) / np.radians(p["tangent_consistency_sigma_deg"])
        group["minimum_segment"] = np.maximum(0, p["minimum_heading_segment_m"] - lengths) / p["minimum_segment_sigma_m"]
        chain = np.vstack([self.boundary[:2], poses[:, :2]])
        gaps = [segment_clearance(a, b, lo, hi, self.radius)[0]
                for a, b in zip(chain[:-1], chain[1:]) for lo, hi in self.boxes.values()]
        group["native_obstacle"] = np.maximum(0, p["safety_target_m"] - np.array(gaps)) / p["safety_sigma_m"]
        c = self.config["corridor"]
        corridor = np.minimum.reduce([chain[:, 0]-c["xmin"], c["xmax"]-chain[:, 0],
                                      c["half_width"]-np.abs(chain[:, 1])]) - self.radius
        group["native_corridor"] = np.maximum(0, p["corridor_target_m"] - corridor) / p["safety_sigma_m"]
        command = self.controller(local_point(poses[2, :2], self.boundary))
        rollout = self.rollout(command)
        group["controller_obstacle"] = np.maximum(0, p["safety_target_m"] - np.array(list(rollout["obstacles"].values()))) / p["safety_sigma_m"]
        group["controller_corridor"] = np.atleast_1d(max(0, p["corridor_target_m"] - rollout["minimum_corridor_m"]) / p["safety_sigma_m"])
        return group

    def residual(self, increments):
        self.calls += 1
        return np.concatenate(list(self.groups(self.initial + increments.reshape(8, 3)).values()))

    def evaluate(self, name, poses, raw_point):
        controller_point = raw_point if name == "RAW" else local_point(poses[2, :2], self.boundary)
        rollout = self.rollout(self.controller(controller_point))
        tangent, length = derived_headings(poses[:, :2])
        valid = np.r_[length >= self.p["minimum_heading_segment_m"], length[-1] >= self.p["minimum_heading_segment_m"]]
        delta = poses[:, :2] - self.initial[:, :2]
        relative_delta = [se2_log(between(z, between(a, b))) for z, a, b in zip(self.relative, poses[:-1], poses[1:])]
        heading_delta = np.degrees(wrap(tangent - self.initial[:, 2]))
        group = self.groups(poses)
        return {"method": name, "world_poses": poses.tolist(), "controller_local_waypoint": controller_point.tolist(),
                "selected_world_waypoint": poses[2, :2].tolist(), "rollout": rollout,
                "native_full": path_safety(poses[:, :2], self.config),
                "native_prefix": path_safety(poses[:3, :2], self.config),
                "boundary_prefix": path_safety(np.vstack([self.boundary[:2], poses[:3, :2]]), self.config),
                "boundary_position_m": float(np.linalg.norm(poses[0, :2] - self.boundary[:2])),
                "boundary_pose_heading_deg": float(abs(np.degrees(wrap(poses[0, 2] - self.boundary[2])))),
                "boundary_tangent_heading_deg": float(abs(np.degrees(wrap(tangent[0] - self.boundary[2])))) if valid[0] else None,
                "heading_valid": valid.tolist(), "segment_lengths_m": length.tolist(),
                "position_change_rms_m": float(np.sqrt(np.mean(np.sum(delta**2, axis=1)))),
                "position_change_max_m": float(np.max(np.linalg.norm(delta, axis=1))),
                "pose_heading_change_rms_deg": float(np.sqrt(np.mean(np.degrees(wrap(poses[:, 2]-self.initial[:, 2]))**2))),
                "tangent_heading_change_rms_deg": float(np.sqrt(np.mean(heading_delta[valid]**2))) if valid.any() else None,
                "relative_translation_error_rms_m": float(np.sqrt(np.mean(np.sum(np.array(relative_delta)[:, :2]**2, axis=1)))),
                "relative_heading_error_rms_deg": float(np.sqrt(np.mean(np.degrees(np.array(relative_delta)[:, 2])**2))),
                "tangent_pose_disagreement_max_deg": float(np.max(abs(np.degrees(wrap(tangent[valid]-poses[valid, 2]))))) if valid.any() else None,
                "common_graph_objective_cost": float(sum(.5 * float(r @ r) for r in group.values())),
                "factor_costs": {key: .5 * float(r @ r) for key, r in group.items()}}

def chord_headings(xy, k):
    heading, lengths = derived_headings(xy)
    chord = xy[k] - xy[0]
    chord_length = float(np.linalg.norm(chord))
    if chord_length == 0:
        raise ValueError("Undefined first chord tangent: zero X0->Xk chord")
    # Only the first heading changes. Wrapping inside factors handles the yaw chart.
    heading[0] = np.arctan2(chord[1], chord[0])
    return heading, lengths, chord_length

class ChordExperiment(Experiment):

    def __init__(self, initial, boundary, config, protocol, k):
        super().__init__(initial, boundary, config, protocol)
        self.k = k

    def groups(self, poses):
        group = super().groups(poses)
        tangent, _, _ = chord_headings(poses[:, :2], self.k)
        group['heading_tangent'][0] = wrap(poses[0, 2] - tangent[0]) / np.radians(self.p['tangent_consistency_sigma_deg'])
        return group
