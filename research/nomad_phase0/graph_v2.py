"""Offline PP-aware SE(2) graph. No runtime/controller or environment mutations."""
import time

import numpy as np
from scipy.optimize import least_squares

from nomad_isaac.common import integrate_se2, local_to_world
from nomad_isaac.clearance import (
    configured_obstacles, corridor_clearance, obstacle_bounds, segment_clearance,
    single_obstacle_config, swept_clearance,
)
from nomad_isaac.handoff_audit import path_safety
from nomad_isaac.online_graph_factors import between, se2_log, wrap
from .pure_pursuit import PurePursuit, XYPath
from .s0_batch_metrics import corridor_arc_minimum


def heading_chords(xy, minimum):
    """Choose local outgoing, then incoming chords without inventing native yaw."""
    pairs = []
    for j in range(len(xy)):
        outgoing = [k for k in range(j+1, len(xy))
                    if np.linalg.norm(xy[k]-xy[j]) >= minimum]
        incoming = [k for k in range(j-1, -1, -1)
                    if np.linalg.norm(xy[j]-xy[k]) >= minimum]
        if outgoing:
            pairs.append((j, outgoing[0]))
        elif incoming:
            pairs.append((incoming[0], j))
        else:
            raise ValueError(f"Node {j}: no meaningful adjacent chord >= {minimum}m")
    return pairs


def chord_values(xy, pairs):
    d = np.array([xy[b]-xy[a] for a, b in pairs])
    if np.any(np.linalg.norm(d, axis=1) < 1e-12):
        raise ValueError("Collapsed heading chord")
    return np.arctan2(d[:, 1], d[:, 0]), np.linalg.norm(d, axis=1)


def fixed_entry(xy, boundary):
    path = XYPath(xy)
    s, distance = path.project(boundary[:2])
    i = min(int(np.searchsorted(path.s, s, side="right")-1), len(path.delta)-1)
    kept = np.flatnonzero(np.r_[True, np.linalg.norm(np.diff(xy, axis=0), axis=1) > 1e-12])
    return {"a": int(kept[i]), "b": int(kept[i+1]),
            "fraction": float((s-path.s[i])/path.lengths[i]),
            "raw_arclength_m": s, "raw_distance_m": distance}


def entry_pose(poses, entry):
    a, b, u = poses[entry["a"]], poses[entry["b"]], entry["fraction"]
    return np.r_[(1-u)*a[:2]+u*b[:2], a[2]+u*wrap(b[2]-a[2])]


def rollout(xy, boundary, config, protocol, ticks):
    """Original PP refreshed every 8 ticks; exact SE(2), certified swept bounds."""
    follower = PurePursuit(xy, protocol["follower"])
    boxes = {b["id"]: obstacle_bounds(single_obstacle_config(config, b))
             for b in configured_obstacles(config)}
    poses, controls, intervals = [np.array(boundary, dtype=float)], [], []
    dt, radius = 1/protocol["integration_hz"], protocol["radius_m"]
    stride = protocol["integration_hz"]//protocol["controller_hz"]
    distance = 0.
    for tick in range(ticks):
        if tick % stride == 0:
            command, diagnostic = follower.control(poses[-1])
            controls.append({"offset_tick": tick, "command_vw": list(command), **diagnostic})
        end = integrate_se2(poses[-1], *command, dt)
        gaps = {key: swept_clearance(poses[-1], *command, dt, lo, hi, radius,
                                     protocol["required_clearance_m"])
                for key, (lo, hi) in boxes.items()}
        intervals.append({
            "obstacles": gaps,
            "corridor_lower_m": corridor_clearance(poses[-1], end, *command, dt,
                                                   config["corridor"], radius),
            "corridor_exact_m": corridor_arc_minimum(poses[-1], *command, dt,
                                                     config["corridor"], radius)})
        distance += abs(command[0])*dt
        poses.append(end)
    per_box = {key: min(r["obstacles"][key]["lower_m"] for r in intervals) for key in boxes}
    minimum = min(per_box.values())
    corridor = min(r["corridor_lower_m"] for r in intervals)
    return {"poses": np.array(poses).tolist(), "controls": controls,
            "obstacles": per_box, "minimum_clearance_m": minimum,
            "minimum_corridor_m": corridor,
            "corridor_intrusion": min(r["corridor_exact_m"] for r in intervals) < 0,
            "corridor_contained": corridor > 0,
            "geometric_overlap": any(v["geometric_overlap"] for r in intervals for v in r["obstacles"].values()),
            "margin_met": minimum >= protocol["required_clearance_m"],
            "safe": minimum >= protocol["required_clearance_m"] and corridor > 0,
            "distance_m": distance, "end_pose": poses[-1].tolist(),
            "endpoint_stop": any(c["endpoint_stop"] for c in controls),
            "stopped_ticks": sum((stride if c["offset_tick"]+stride <= ticks else ticks-c["offset_tick"])
                                 for c in controls if c["command_vw"] == [0., 0.]),
            "ticks": ticks}


class GraphV2:
    def __init__(self, xy, boundary, old_command, config, protocol, ticks):
        self.xy = np.asarray(xy, dtype=float)
        self.boundary = np.asarray(boundary, dtype=float)
        self.old_command, self.config, self.p, self.ticks = old_command, config, protocol, ticks
        self.entry = fixed_entry(self.xy, self.boundary)
        self.chords = heading_chords(self.xy, protocol["minimum_heading_chord_m"])
        heading, self.chord_lengths = chord_values(self.xy, self.chords)
        self.initial = np.column_stack([self.xy, heading])
        self.lengths = np.linalg.norm(np.diff(self.xy, axis=0), axis=1)
        self.relative = [between(a, b) for a, b in zip(self.initial[:-1], self.initial[1:])]
        self.boxes = {b["id"]: obstacle_bounds(single_obstacle_config(config, b))
                      for b in configured_obstacles(config)}
        self.calls = 0

    def rigid(self):
        angle = float(wrap(self.boundary[2]-self.initial[0, 2]))
        xy = local_to_world(self.xy-self.xy[0], [*self.boundary[:2], angle])
        return np.column_stack([xy, self.initial[:, 2]+angle])

    def groups(self, poses):
        p = self.p
        scale = lambda name: np.array([p[name+"_sigma_xy_m"], p[name+"_sigma_xy_m"],
                                       np.radians(p[name+"_sigma_yaw_deg"])])
        g = {}
        # Same SE(2) log definitions as the existing graph, without its PD factors.
        g["fresh_prior"] = np.concatenate([se2_log(between(f, x))/scale("prior")
                                           for f, x in zip(self.initial, poses)])
        g["relative_pose"] = np.concatenate([se2_log(between(z, between(a, b)))/scale("relative")
                                             for z, a, b in zip(self.relative, poses[:-1], poses[1:])])
        entry = entry_pose(poses, self.entry)
        g["boundary"] = se2_log(between(self.boundary, entry))/scale("boundary")
        headings, chord_lengths = chord_values(poses[:, :2], self.chords)
        g["heading_tangent"] = wrap(poses[:, 2]-headings)/np.radians(p["tangent_consistency_sigma_deg"])
        lengths = np.linalg.norm(np.diff(poses[:, :2], axis=0), axis=1)
        g["anti_shrink"] = np.maximum(0, np.r_[
            p["minimum_segment_ratio"]*self.lengths-lengths,
            p["minimum_total_length_ratio"]*sum(self.lengths)-sum(lengths),
            p["minimum_chord_ratio"]*self.chord_lengths-chord_lengths])/p["shrink_sigma_m"]
        segments = list(zip(poses[:-1, :2], poses[1:, :2])) + [(self.boundary[:2], entry[:2])]
        gaps = [segment_clearance(a, b, lo, hi, p["radius_m"])[0]
                for a, b in segments for lo, hi in self.boxes.values()]
        g["native_obstacle"] = np.maximum(0, p["safety_target_m"]-np.array(gaps))/p["safety_sigma_m"]
        chain = np.vstack([self.boundary[:2], poses[:, :2]])
        c = self.config["corridor"]
        gaps = np.minimum.reduce([chain[:, 0]-c["xmin"], c["xmax"]-chain[:, 0],
                                  c["half_width"]-np.abs(chain[:, 1])])-p["radius_m"]
        g["native_corridor"] = np.maximum(0, p["corridor_target_m"]-gaps)/p["safety_sigma_m"]
        result = rollout(poses[:, :2], self.boundary, self.config, p, self.ticks)
        g["pp_angular_continuity"] = np.atleast_1d(
            (result["controls"][0]["command_vw"][1]-self.old_command[1])/p["pp_applied_w_sigma_rad_s"])
        g["pp_obstacle"] = np.maximum(0, p["safety_target_m"]-np.array(list(result["obstacles"].values())))/p["safety_sigma_m"]
        g["pp_corridor"] = np.atleast_1d(max(0, p["corridor_target_m"]-result["minimum_corridor_m"])/p["safety_sigma_m"])
        return g

    def residual(self, increment):
        self.calls += 1
        return np.concatenate(list(self.groups(self.initial+increment.reshape(8, 3)).values()))

    def solve(self):
        settings = {k: self.p["solver"][k] for k in
                    ("method", "jac", "ftol", "xtol", "gtol", "max_nfev", "loss")}
        start = time.perf_counter()
        solution = least_squares(self.residual, np.zeros(24),
                                 x_scale=np.tile(self.p["solver"]["x_scale_per_pose"], 8), **settings)
        elapsed = time.perf_counter()-start
        poses = self.initial+solution.x.reshape(8, 3)
        groups = self.groups(poses)
        return poses, {"success": bool(solution.success), "status": int(solution.status),
                       "message": solution.message, "wall_s": elapsed, "nfev": solution.nfev,
                       "residual_calls": self.calls, "optimality": float(solution.optimality),
                       "cost": float(solution.cost), "residual_l2": float(np.linalg.norm(solution.fun)),
                       "factor_costs": {key: .5*float(r@r) for key, r in groups.items()}}

    def evaluate(self, method, poses):
        result = rollout(poses[:, :2], self.boundary, self.config, self.p, self.ticks)
        entry = entry_pose(poses, self.entry)
        delta = poses[:, :2]-self.xy
        relative = np.array([se2_log(between(z, between(a, b)))
                             for z, a, b in zip(self.relative, poses[:-1], poses[1:])])
        w = result["controls"][0]["command_vw"][1]
        return {
            "method": method, "world_xy_m": poses[:, :2].tolist(),
            "auxiliary_heading_rad": poses[:, 2].tolist(),
            "switch_command_vw": result["controls"][0]["command_vw"],
            "switch_abs_delta_w_rad_s": abs(w-self.old_command[1]),
            "switch_sign_reversal": bool(w*self.old_command[1] < -1e-18),
            "xy_change_rms_m": float(np.sqrt(np.mean(np.sum(delta**2, axis=1)))),
            "xy_change_max_m": float(np.max(np.linalg.norm(delta, axis=1))),
            "length_ratio": float(np.sum(np.linalg.norm(np.diff(poses[:, :2], axis=0), axis=1))/sum(self.lengths)),
            "fixed_entry_world_pose": entry.tolist(),
            "boundary_position_m": float(np.linalg.norm(entry[:2]-self.boundary[:2])),
            "boundary_heading_rad": float(abs(wrap(entry[2]-self.boundary[2]))),
            "relative_translation_rms_m": float(np.sqrt(np.mean(np.sum(relative[:, :2]**2, axis=1)))),
            "relative_heading_rms_rad": float(np.sqrt(np.mean(relative[:, 2]**2))),
            "native_full": path_safety(poses[:, :2], self.config),
            "native_prefix": path_safety(poses[:3, :2], self.config),
            "entry_connector": path_safety(np.array([self.boundary[:2], entry[:2]]), self.config),
            "rollout": result}


def improvement(candidate, raw, protocol, converged=True):
    r = protocol["improvement_rule"]
    tolerance = r["clearance_numeric_tolerance_m"]
    safety_not_degraded = all(
        candidate[group][key]+tolerance >= raw[group][key]
        for group, keys in (("native_full", ("obstacle_clearance_m", "corridor_clearance_m")),
                            ("rollout", ("minimum_clearance_m", "minimum_corridor_m")))
        for key in keys)
    checks = {
        "converged": converged,
        "angular_reduction": raw["switch_abs_delta_w_rad_s"]-candidate["switch_abs_delta_w_rad_s"]
                             >= r["minimum_abs_delta_w_reduction_rad_s"],
        "safe": candidate["native_full"]["safe"] and candidate["rollout"]["safe"],
        "safety_not_degraded": safety_not_degraded,
        "motion_retained": candidate["rollout"]["distance_m"] >= r["minimum_RAW_distance_ratio"]*raw["rollout"]["distance_m"],
        "no_added_endpoint_stop": not candidate["rollout"]["endpoint_stop"] or raw["rollout"]["endpoint_stop"],
        "length_retained": candidate["length_ratio"] >= r["minimum_RAW_path_length_ratio"]}
    return {"qualifies": all(checks.values()), "checks": checks}
