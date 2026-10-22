"""Offline Graph v3 and dedicated speed/rate PP wrappers; original PP is untouched."""
import numpy as np

from nomad_isaac.clearance import (configured_obstacles, corridor_clearance,
    obstacle_bounds, single_obstacle_config, swept_clearance)
from nomad_isaac.common import integrate_se2
from nomad_isaac.handoff_audit import path_safety
from .graph_v2 import GraphV2
from .pure_pursuit import PurePursuit
from .s0_batch_metrics import corridor_arc_minimum

FLAGS = ("CURVATURE_SATURATED", "ACCEL_LIMITED", "OMEGA_CLIPPED", "RATE_LIMITED")


def curvature(diagnostic):
    x, y = diagnostic["target_local_x_m"], diagnostic["target_local_y_m"]
    return 2*y/(x*x+y*y) if x*x+y*y >= 1e-24 else 0.


def speed_command(kappa, previous_v, settings, dt=1/9):
    """User-fixed hard execution limits; curvature fidelity is soft when saturated."""
    low, high = settings["v_min"], settings["v_max"]
    assert 0 <= previous_v <= high+1e-12
    target = float(np.clip(settings["w_max"]/abs(kappa), low, high)) if kappa else high
    dv = settings["acceleration_max_m_s2"]*dt
    a, b = max(low, previous_v-dv), min(high, previous_v+dv)
    if a > b+1e-12:
        raise ValueError("Previous speed incompatible with minimum speed and acceleration limits")
    v = float(np.clip(target, a, b))
    w = float(np.clip(v*kappa, -settings["w_max"], settings["w_max"]))
    return (v, w), {"v_target_m_s": target,
        "CURVATURE_SATURATED": bool(abs(kappa) > settings["w_max"]/low),
        "ACCEL_LIMITED": bool(abs(v-target) > 1e-12),
        "OMEGA_CLIPPED": bool(abs(w-v*kappa) > 1e-12), "RATE_LIMITED": False}


def rate_command(w, previous_w, maximum_delta=.1):
    return float(np.clip(w, previous_w-maximum_delta, previous_w+maximum_delta))


class DedicatedPP:
    """Same projection/target state as PP; only dedicated speed/rate command differs."""
    def __init__(self, xy, protocol, previous, mode):
        self.pp = PurePursuit(xy, protocol["follower"])
        self.p, self.previous, self.mode = protocol, np.array(previous, dtype=float), mode

    def control(self, pose):
        original, diag = self.pp.control(pose)
        kappa = curvature(diag)
        if diag["endpoint_stop"]:
            # Finish before issuing any zero-speed recovery command.
            return None, {**diag, "kappa_PP_m_inv": kappa, "completion": "ENDPOINT_REACHED"}
        flags = {"CURVATURE_SATURATED": bool(abs(kappa) > 8), "ACCEL_LIMITED": False,
                 "OMEGA_CLIPPED": diag["w_clipped"], "RATE_LIMITED": False, "v_target_m_s": .2}
        command = original
        if self.mode == "speed":
            command, flags = speed_command(kappa, self.previous[0], self.p["variable_speed"])
        elif self.mode == "rate":
            w = rate_command(original[1], self.previous[1], self.p["rate_limit_delta_w_rad_s"])
            command = (original[0], w)
            flags["RATE_LIMITED"] = abs(w-original[1]) > 1e-12
        elif self.mode != "raw":
            raise ValueError(self.mode)
        self.previous = np.array(command)
        return command, {**diag, **flags, "kappa_PP_m_inv": kappa,
                         "actual_unclipped_w_rad_s": command[0]*kappa}


def side_labels(xy, config):
    """World +X crossing, world ±Y side, no inferred native yaw/correspondence."""
    result = {}
    for box in configured_obstacles(config):
        x, y = box["center_xy_m"]
        bound = box["size_xyz_m"][1]/2+config["agent_radius_m"]
        crossings = []; ambiguous = False
        for i, (a, b) in enumerate(zip(xy[:-1], xy[1:])):
            if abs(b[0]-a[0]) <= 1e-12:
                ambiguous |= abs(a[0]-x) <= 1e-12
                continue
            u = (x-a[0])/(b[0]-a[0])
            if 0 <= u <= 1:
                offset = float((1-u)*a[1]+u*b[1]-y)
                crossings.append({"a": i, "b": i+1, "fraction": float(u), "offset_m": offset})
        signs = [1 if c["offset_m"] > bound else -1 if c["offset_m"] < -bound else 0 for c in crossings]
        defined = bool(signs and not ambiguous and 0 not in signs and len(set(signs)) == 1)
        result[box["id"]] = {"status": "LEFT_POSITIVE_Y" if defined and signs[0] > 0 else
                            "RIGHT_NEGATIVE_Y" if defined else "SIDE_UNDEFINED",
                            "sign": signs[0] if defined else None, "minimum_offset_m": bound,
                            "center_y_m": y, "crossings": crossings,
                            "reason": None if defined else "absent_ambiguous_or_not_outside_footprint_expanded_halfwidth"}
    return result


def rollout(xy, boundary, previous, config, protocol, ticks, mode="raw", chunk=False):
    follower = DedicatedPP(xy, protocol, previous, mode)
    boxes = {b["id"]: obstacle_bounds(single_obstacle_config(config, b)) for b in configured_obstacles(config)}
    dt = 1/protocol["integration_hz"]; stride = protocol["integration_hz"]//protocol["controller_hz"]
    radius = protocol["radius_m"]; pose = np.array(boundary, dtype=float)
    per_box = {k: swept_clearance(pose, 0., 0., 0., *bounds, radius)["lower_m"] for k, bounds in boxes.items()}
    overlaps = {k: swept_clearance(pose, 0., 0., 0., *bounds, radius)["geometric_overlap"] for k, bounds in boxes.items()}
    corridor = corridor_clearance(pose, pose, 0., 0., 0., config["corridor"], radius)
    exact_corridor = corridor_arc_minimum(pose, 0., 0., 0., config["corridor"], radius)
    poses = [pose.copy()]; controls = []; distance = 0.; reached = False; count = 0
    flag_ticks = {k: 0 for k in FLAGS}; flag_intervals = dict(flag_ticks)
    command = None; first_overlap = 0 if any(overlaps.values()) else None
    for tick in range(ticks):
        if tick % stride == 0:
            command, diagnostic = follower.control(pose)
            if command is None:
                reached = True
                break
            controls.append({"offset_tick": tick, "pose": pose.tolist(), "command_vw": list(command), **diagnostic})
            for flag in FLAGS:
                flag_ticks[flag] += int(diagnostic[flag])
        end = integrate_se2(pose, *command, dt)
        for key, bounds in boxes.items():
            gap = swept_clearance(pose, *command, dt, *bounds, radius, protocol["required_clearance_m"])
            per_box[key] = min(per_box[key], gap["lower_m"])
            overlaps[key] |= gap["geometric_overlap"]
        if first_overlap is None and any(overlaps.values()):
            first_overlap = tick+1
        corridor = min(corridor, corridor_clearance(pose, end, *command, dt, config["corridor"], radius))
        exact_corridor = min(exact_corridor, corridor_arc_minimum(pose, *command, dt, config["corridor"], radius))
        for flag in FLAGS:
            flag_intervals[flag] += int(diagnostic[flag])
        pose = end; poses.append(pose.copy()); count += 1; distance += command[0]*dt
    minimum = min(per_box.values())
    status = "ENDPOINT_REACHED" if reached else "CHUNK_TIMEOUT" if chunk else "HORIZON_COMPLETE"
    profile = [{"control_ordinal": i, "arclength_m": c["progress_m"], "target_arclength_m": c["target_s_m"],
                "v_m_s": c["command_vw"][0], "v_target_m_s": c["v_target_m_s"],
                "kappa_PP_m_inv": c["kappa_PP_m_inv"]} for i, c in enumerate(controls)]
    return {"status": status, "requested_ticks": ticks, "executed_ticks": count,
        "duration_s": count*dt, "distance_m": distance, "mean_speed_m_s": distance/(count*dt) if count else 0.,
        "endpoint_reached": reached, "stop_or_truncated": reached and not chunk or not count,
        "chunk_timeout": chunk and not reached, "end_pose": pose.tolist(),
        "first_command_vw": controls[0]["command_vw"] if controls else None,
        "minimum_clearance_m": minimum, "obstacles": per_box, "minimum_corridor_m": corridor,
        "geometric_overlap": any(overlaps.values()), "first_overlap_offset_tick": first_overlap,
        "corridor_intrusion": exact_corridor < 0, "corridor_contained": corridor > 0,
        "margin_met": minimum >= protocol["required_clearance_m"],
        "safe": minimum >= protocol["required_clearance_m"] and corridor > 0,
        "control_ticks": len(controls), "flag_control_ticks": flag_ticks, "flag_integration_intervals": flag_intervals,
        "speed_profile": profile, "controls": controls, "poses": np.array(poses).tolist(),
        "executed_side": side_labels(np.array(poses)[:, :2], config)}


class GraphV3(GraphV2):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sides = side_labels(self.xy, self.config)

    def groups(self, poses):
        # Reuse v2 factor implementation unchanged. Its constant-speed PP groups
        # are replaced below, never included in v3's objective.
        g = super().groups(poses)
        p = self.p
        r = rollout(poses[:, :2], self.boundary, self.old_command, self.config, p, self.ticks, "speed")
        _, diagnostic = PurePursuit(poses[:, :2], p["follower"]).control(self.boundary)
        kappa = curvature(diagnostic)
        target = self.old_command[1]/max(self.old_command[0], p["variable_speed"]["v_min"])
        g["pp_unclipped_curvature_continuity"] = np.atleast_1d((kappa-target)/p["pp_unclipped_curvature_sigma_m_inv"])
        first_w = r["first_command_vw"][1] if r["first_command_vw"] else 0.
        g["pp_angular_continuity"] = np.atleast_1d((first_w-self.old_command[1])/p["pp_applied_w_sigma_rad_s"])
        g["pp_obstacle"] = np.maximum(0, p["safety_target_m"]-np.array(list(r["obstacles"].values())))/p["safety_sigma_m"]
        g["pp_corridor"] = np.atleast_1d(max(0, p["corridor_target_m"]-r["minimum_corridor_m"])/p["safety_sigma_m"])
        side_residual = []
        for side in self.sides.values():
            if side["sign"] is None:
                continue
            for crossing in side["crossings"]:
                a, b, u = crossing["a"], crossing["b"], crossing["fraction"]
                offset = (1-u)*poses[a, 1]+u*poses[b, 1]-side["center_y_m"]
                side_residual.append(max(0, side["minimum_offset_m"]-side["sign"]*offset)/p["side_sigma_m"])
        g["definite_side_preservation"] = np.array(side_residual)
        return g


def qualifies(candidate, reference, raw, protocol, horizon, converged=True):
    p = protocol["improvement_rule"]; r = candidate[horizon]; baseline = reference[horizon]
    safe = candidate["native_full"]["safe"] and r["safe"]
    loss = all(candidate["native_full"][k] >= raw["native_full"][k]-p["maximum_raw_clearance_loss_m"]
               for k in ("obstacle_clearance_m", "corridor_clearance_m"))
    loss &= all(r[k] >= raw[horizon][k]-p["maximum_raw_clearance_loss_m"]
                for k in ("minimum_clearance_m", "minimum_corridor_m"))
    cs, rs = candidate["H_switch"], raw["H_switch"]
    progress = (not cs["stop_or_truncated"] and cs["executed_ticks"] == cs["requested_ticks"]
                and cs["distance_m"] >= p["minimum_raw_motion_ratio"]*rs["distance_m"]
                and cs["distance_m"] >= p["minimum_raw_motion_ratio"]*reference["H_switch"]["distance_m"])
    angular = candidate["switch_abs_delta_w_rad_s"] is not None and reference["switch_abs_delta_w_rad_s"] is not None and (
        reference["switch_abs_delta_w_rad_s"]-candidate["switch_abs_delta_w_rad_s"] > p["angular_reduction_epsilon_rad_s"])
    checks = {"converged": converged, "safe_native_and_rollout": safe, "raw_clearance_loss_le_5mm": bool(loss),
              "H_switch_progress_and_no_stop": bool(progress), "angular_reduction": bool(angular),
              "horizon_complete": r["endpoint_reached"] if horizon == "H_chunk" else r["executed_ticks"] == r["requested_ticks"]}
    return {"qualifies": all(checks.values()), "checks": checks}
