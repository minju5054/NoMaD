"""One fixed offline B51 solve. Never imports Isaac, torch, or model inference.

Pose headings are auxiliary segment tangents, not NoMaD yaw. No OLD/FRESH
index correspondence is assumed. Actual post-B51 data are read only after solve.
"""
import argparse
import csv
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import scipy
from scipy.optimize import least_squares

from .common import (ROOT, integrate_se2, local_to_world, original_controller,
                     sha256_file, write_json)
from .clearance import (configured_obstacles, corridor_clearance, obstacle_bounds,
                        point_clearance, segment_clearance, single_obstacle_config,
                        swept_clearance)
from .handoff_audit import path_safety

PROTOCOL = Path(__file__).with_name("minimal_se2_graph_protocol.json")


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


def rigid_alignment(initial, boundary):
    angle = boundary[2] - initial[0, 2]
    aligned = initial.copy()
    aligned[:, :2] = local_to_world(initial[:, :2] - initial[0, :2], np.r_[boundary[:2], angle])
    aligned[:, 2] += angle
    return aligned


def read_inputs(run, protocol):
    # Stop at 51: neither 52/53 nor their outcomes are made available to the solve.
    events = {}
    with (run / "events.jsonl").open() as stream:
        for line in stream:
            row = json.loads(line)
            if row["id"] in (50, 51):
                events[row["id"]] = row
            if row["id"] == 51:
                break
    assert set(events) == {50, 51}
    with (run / "agent_trajectory.csv").open() as stream:
        for row in csv.DictReader(stream):
            if int(row["tick"]) == protocol["boundary_tick"]:
                boundary = np.array([float(row[k]) for k in ("x_m", "y_m", "yaw_rad")])
                assert abs(float(row["simulation_time_s"]) - 1000/72) < 1e-12
                break
        else:
            raise ValueError("B51 missing")
    np.testing.assert_allclose(boundary, events[51]["agent_pose_at_switch"], atol=1e-12, rtol=0)
    np.testing.assert_allclose(boundary, [2.097864810, -.001133875, -.966924877], atol=1e-9, rtol=0)
    config = json.loads((run / "scenario.json").read_text())
    spawn = json.loads((run / "dynamic/spawn.json").read_text())
    assert spawn["tick"] < protocol["boundary_tick"]
    config["obstacles"] = [*config["obstacles"], spawn["obstacle"]]
    assert config["agent_radius_m"] == protocol["radius_m"] == .09
    assert config["required_clearance_m"] == protocol["required_clearance_m"] == .02
    assert config["integration_hz"] == protocol["integration_hz"] == 72
    worlds, locals_ = {}, {}
    for identifier in (50, 51):
        with np.load(run / f"model/derived/{identifier:04d}.npz", allow_pickle=False) as saved:
            assert saved["metric"].shape == (8, 8, 2)
            # No other sample enters this experiment.
            locals_[identifier] = saved["metric"][0].astype(float)
        assert np.isfinite(locals_[identifier]).all()
        worlds[identifier] = local_to_world(locals_[identifier], np.array(events[identifier]["observation_pose"]))
    heading, lengths = derived_headings(worlds[51])
    assert np.all(lengths >= protocol["minimum_heading_segment_m"]), "Invalid initial heading; no solve"
    return events, boundary, config, locals_, worlds, np.column_stack([worlds[51], heading])


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


def minimal_algebra_checks(initial, boundary):
    np.testing.assert_allclose(se2_log(np.array([.2, -.1, 0.])), [.2, -.1, 0.], atol=1e-14)
    angle = .7
    twist = np.array([.13, -.04])
    a, b = np.sin(angle)/angle, (1-np.cos(angle))/angle
    transformed = np.r_[np.array([[a, -b], [b, a]]) @ twist, angle]
    np.testing.assert_allclose(se2_log(transformed), np.r_[twist, angle], atol=1e-14)
    np.testing.assert_allclose(local_point(local_to_world([[.12, -.03]], boundary)[0], boundary), [.12, -.03], atol=1e-14)
    rigid = rigid_alignment(initial, boundary)
    np.testing.assert_allclose(rigid[0], boundary, atol=1e-14)
    error = max(np.max(abs(between(initial[i], initial[i+1]) - between(rigid[i], rigid[i+1]))) for i in range(7))
    assert error < 1e-14
    return {"se2_log_and_inverse_frame": "PASS", "rigid_relative_max_error": float(error)}


def preservation(run):
    manifest = ROOT / "research/results/isaac6_old_rollout_obstacle_20261018/input_hashes.json"
    hashes = json.loads(manifest.read_text())
    assert all(sha256_file(run / name) == expected for name, expected in hashes.items())
    protected = json.loads((manifest.parent / "independent_review.json").read_text())["protected_source_sha256"]
    assert all(sha256_file(ROOT / name) == expected for name, expected in protected.items())
    return {"raw_inputs_unchanged": len(hashes), "protected_sources_unchanged": len(protected),
            "manifest_sha256": sha256_file(manifest)}


def validate_actual_after_solve(run, exp, raw):
    start = exp.p["boundary_tick"]
    stop = start + exp.p["horizon_ticks"]
    with (run / "agent_trajectory.csv").open() as stream:
        actual = [row for row in csv.DictReader(stream) if start <= int(row["tick"]) <= stop]
    xyz = np.array([[float(row[k]) for k in ("x_m", "y_m", "yaw_rad")] for row in actual])
    pose_error = float(np.max(abs(xyz - np.array(raw["rollout"]["poses"]))))
    assert len(actual) == 17 and pose_error < 1e-12
    # Outgoing RAW51 applies on intervals ending 1001..1016, including B52 arrival.
    with (run / "clearance.jsonl").open() as stream:
        static = [json.loads(line) for line in stream]
    with (run / "dynamic/clearance.jsonl").open() as stream:
        dynamic = [json.loads(line) for line in stream]
    errors = []
    for i, row in enumerate(raw["rollout"]["intervals"], start + 1):
        d = next(r for r in dynamic if abs(r["end_sim_s"] - i/72) < 1e-12)
        s = next(r for r in static if abs(r["end_sim_s"] - i/72) < 1e-12)
        for name, measured in row["obstacles"].items():
            recorded = d if name == "DynamicObstacle" else s["obstacles"][name]
            for key in ("lower_m", "upper_m"):
                errors.append(abs(measured[key] - recorded[key]))
            errors.append(abs(row["corridor_lower_m"] - recorded["corridor_lower_m"]))
    assert max(errors) < 1e-12
    return {"actual_poses": len(actual), "actual_intervals": 16, "pose_max_abs_error": pose_error,
            "swept_and_corridor_max_abs_error_m": max(errors), "future_trace_read_only_after_solve": True}


def existing_references_after_solve():
    speed_path = ROOT / "research/results/isaac6_b51_speed_feasibility_20261018/comparison.csv"
    samples_path = ROOT / "research/results/isaac6_sample_comparison_20261019/samples_51_52.csv"
    with speed_path.open() as stream:
        speed = next(row for row in csv.DictReader(stream) if row["condition"] == "SPEED_LIMITED_51" and row["horizon"] == "H1")
    with samples_path.open() as stream:
        samples = [row for row in csv.DictReader(stream) if row["prediction_id"] == "51" and row["sample_index"] in ("4", "6", "7")]
    assert len(samples) == 3
    return {"speed_limited_H1": speed, "sample_references": samples, "reoptimized_or_rerolled": False,
            "source_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in (speed_path, samples_path)}}


def write_comparison(out, results):
    rows = []
    for name, r in results.items():
        roll = r["rollout"]
        rows.append({"method": name, "boundary_distance_m": r["boundary_position_m"],
                     "boundary_tangent_angle_deg": r["boundary_tangent_heading_deg"],
                     "trajectory_change_rms_m": r["position_change_rms_m"],
                     "tangent_change_rms_deg": r["tangent_heading_change_rms_deg"],
                     "relative_translation_rms_m": r["relative_translation_error_rms_m"],
                     "native_full_clearance_m": r["native_full"]["obstacle_clearance_m"],
                     "native_prefix_clearance_m": r["native_prefix"]["obstacle_clearance_m"],
                     "local_dx_m": r["controller_local_waypoint"][0], "local_dy_m": r["controller_local_waypoint"][1],
                     "v_m_s": roll["command_vw"][0], "w_rad_s": roll["command_vw"][1],
                     "rollout_clearance_lower_m": roll["minimum_clearance_m"],
                     "rollout_clearance_upper_m": roll["minimum_upper_m"], "margin_met": roll["margin_met"],
                     "geometric_overlap": roll["geometric_overlap"], "corridor_clearance_m": roll["minimum_corridor_m"],
                     "distance_m": roll["distance_m"], "end_x_m": roll["end_pose"][0],
                     "end_y_m": roll["end_pose"][1], "end_yaw_rad": roll["end_pose"][2]})
    with (out / "comparison.csv").open("x") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def plot_comparison(out, exp, worlds, events, results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    plt.rcParams["svg.fonttype"] = "none"
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 6), gridspec_kw={"width_ratios": [1.4, 1]})
    colors = {"RAW": "#d1495b", "RIGID": "#d68b00", "GRAPH": "#007f83"}
    for ax in axes:
        for key, (lo, hi) in exp.boxes.items():
            ax.add_patch(Rectangle(lo, *(hi-lo), color="#bd57ac" if key == "DynamicObstacle" else "#789a77", alpha=.45))
        # True rounded AABB offsets for circular footprint, not expanded-box approximation.
        gx = np.linspace(1.8, 2.8, 360); gy = np.linspace(-.5, .2, 280)
        xx, yy = np.meshgrid(gx, gy)
        lo, hi = exp.boxes["DynamicObstacle"]
        d = np.sqrt(np.maximum(np.maximum(lo[0]-xx, xx-hi[0]), 0)**2 + np.maximum(np.maximum(lo[1]-yy, yy-hi[1]), 0)**2)
        ax.contour(xx, yy, d, levels=[exp.radius, exp.radius+.02], colors=["#952c83", "#952c83"], linestyles=[":", "--"], linewidths=1)
        ax.plot(*exp.boundary[:2], "k*", ms=13, label="B51 fixed", zorder=10)
        ax.set_aspect("equal"); ax.grid(alpha=.18); ax.set_xlabel("World X [m]"); ax.set_ylabel("World Y [m]")
    axes[0].plot(*worlds[50].T, ":", color=".5", lw=1.5, label="OLD50 (context only)")
    for name, r in results.items():
        xy = np.array(r["world_poses"])[:, :2]
        trace = np.array(r["rollout"]["poses"])
        axes[0].plot(*xy.T, "o--", color=colors[name], ms=3,
                     lw=3 if name == "RAW" else 1.5, label=f"{name} future XY")
        axes[0].plot(*xy[2], "s", color=colors[name], ms=6)
        axes[0].plot(*np.vstack([exp.boundary[:2], xy[0]]).T, ":", color=colors[name])
        for ax in axes:
            ax.plot(*trace[:, :2].T, "-", color=colors[name], lw=2.5,
                    label=f"{name} H1 ({100*r['rollout']['minimum_clearance_m']:.3f} cm)" if ax is axes[1] else None)
        axes[1].plot(*trace[-1, :2], "o", color=colors[name], ms=5)
        axes[1].add_patch(Circle(trace[-1, :2], exp.radius, fill=False, color=colors[name], alpha=.65))
    obs = np.array(events[51]["observation_pose"])
    axes[0].plot(*obs[:2], "kx", ms=7, label="FRESH51 observation")
    axes[0].set_xlim(1.84, 2.64); axes[0].set_ylim(-.42, .16)
    axes[1].set_xlim(2.065, 2.255); axes[1].set_ylim(-.15, .10)
    axes[0].set_title("Observation-anchored RAW and explicit corrections")
    axes[1].set_title("Same B51, original PD, 16/72 s")
    axes[0].text(2.4056, -.20, "DynamicObstacle\n0.35 x 0.35 m", ha="center", fontsize=9)
    if all(np.allclose(results[name]["rollout"]["poses"], results["RAW"]["rollout"]["poses"], atol=1e-12, rtol=0)
           for name in ("RIGID", "GRAPH")):
        shortfall = 1000 * (exp.p["required_clearance_m"] - results["RAW"]["rollout"]["minimum_clearance_m"])
        axes[1].text(.04, .04, f"RAW = RIGID = GRAPH\nIdentical PD rollout\nMargin shortfall: {shortfall:.3f} mm",
                     transform=axes[1].transAxes, fontsize=8,
                     bbox={"facecolor": "white", "alpha": .9, "edgecolor": "none"})
    axes[0].legend(fontsize=8, loc="lower left")
    axes[1].legend(fontsize=8, loc="upper left")
    fig.suptitle("OLD50 -> FRESH51 sample 0: offline SE(2) mechanism", fontsize=14)
    fig.text(.5, .025, "Dashed paths: predictions/corrections; squares: index 2; solid arcs: H1 rollouts. Purple dotted/dashed: contact / 2 cm center limits.\nRAW is recorded execution; RIGID and GRAPH are unexecuted counterfactuals. No waypoint timestamps or native yaw.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .09, 1, .94))
    fig.savefig(out / "comparison.svg")
    svg = out / "comparison.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(PROTOCOL.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    write_json(args.out / "protocol.json", p)
    before = preservation(args.run)
    events, boundary, config, locals_, worlds, initial = read_inputs(args.run, p)
    algebra = minimal_algebra_checks(initial, boundary)
    exp = Experiment(initial, boundary, config, p)
    # These are the only optimization inputs. Snapshot before the sole solver invocation.
    input_snapshot = {"protocol_sha256": sha256_file(PROTOCOL),
                      "analysis_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                      "script_sha256": sha256_file(Path(__file__)), "boundary": boundary.tolist(),
                      "initial_fresh_poses": initial.tolist(), "fresh_observation_pose": events[51]["observation_pose"],
                      "obstacles": config["obstacles"], "corridor": config["corridor"],
                      "input_hashes": {name: sha256_file(args.run / name) for name in (
                          "model/derived/0050.npz", "model/derived/0051.npz", "events.jsonl",
                          "agent_trajectory.csv", "scenario.json", "dynamic/spawn.json")},
                      "environment": {"python": platform.python_version(), "scipy": scipy.__version__, "numpy": np.__version__},
                      "pre_solve_checks": {**before, **algebra}, "solve_count": 1}
    write_json(args.out / "solve_inputs.json", input_snapshot)
    print("Inputs and protocol frozen; invoking the single least_squares solve.", flush=True)
    solver = p["solver"]
    start = time.monotonic()
    solution = least_squares(exp.residual, np.zeros(24), method=solver["method"], jac=solver["jac"],
                             ftol=solver["ftol"], xtol=solver["xtol"], gtol=solver["gtol"],
                             max_nfev=solver["max_nfev"], x_scale=np.tile(solver["x_scale_per_pose"], 8))
    duration = time.monotonic() - start
    optimized = initial + solution.x.reshape(8, 3)
    solved = {"success": bool(solution.success), "status": int(solution.status), "message": solution.message,
              "nfev": solution.nfev, "njev": solution.njev, "residual_calls_including_jacobian": exp.calls,
              "wall_s": duration, "cost": solution.cost, "residual_l2": float(np.linalg.norm(solution.fun)),
              "residual_max_abs": float(np.max(abs(solution.fun))), "optimality": solution.optimality,
              "optimized_poses": optimized.tolist(), "residual_vector": solution.fun.tolist()}
    write_json(args.out / "solver.json", solved)  # Preserve nonconvergence too, before any validation.
    print(json.dumps({k: solved[k] for k in ("success", "nfev", "cost", "wall_s")}), flush=True)
    results = {name: exp.evaluate(name, poses, locals_[51][2]) for name, poses in (
        ("RAW", initial), ("RIGID", rigid_alignment(initial, boundary)), ("GRAPH", optimized))}
    actual = validate_actual_after_solve(args.run, exp, results["RAW"])
    refs = existing_references_after_solve()
    after = preservation(args.run)
    # Drop bulky per-tick factor internals; retain all 17 poses and summarized safety.
    for result in results.values():
        result["rollout"].pop("intervals")
    summary = {"scope": p["experiment"], "solver": {k: v for k, v in solved.items() if k not in ("optimized_poses", "residual_vector")},
               "boundary_pose": boundary.tolist(), "boundary_sim_s": 1000/72, "horizon_s": 16/72,
               "initial_clearances_m": {key: point_clearance(boundary[:2], lo, hi, exp.radius) for key, (lo, hi) in exp.boxes.items()},
               "results": results, "stored_references_only": refs, "validation": {**actual, **after, **algebra},
               "limitations": ["Exact simulator geometry: offline oracle", "No OLD/FRESH index correspondence factor",
                               "RAW command retains original local point; corrected methods express world index2 at B51",
                               "Common objective uses corrected-point controller semantics even for RAW; actual RAW safety is separate",
                               "One local solve with clipping/non-smooth safety; no global optimality or hard feasibility guarantee",
                               "Only H1 constant-command mechanism; no navigation, necessity or superiority claim"]}
    write_json(args.out / "summary.json", summary)
    write_comparison(args.out, results)
    plot_comparison(args.out, exp, worlds, events, results)
    print(json.dumps({name: {"command": r["rollout"]["command_vw"], "clearance": r["rollout"]["minimum_clearance_m"],
                             "safe": r["rollout"]["safe"]} for name, r in results.items()}), flush=True)


if __name__ == "__main__":
    main()
