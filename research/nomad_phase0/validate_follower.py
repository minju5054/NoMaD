"""One S0 offline follower validation; separate replay and passive safety audit."""
import argparse
import csv
import json
import math
from pathlib import Path
import subprocess

import numpy as np

from nomad_isaac.common import ROOT, integrate_se2, sha256_file, write_json
from nomad_isaac.clearance import (
    configured_obstacles, corridor_clearance, obstacle_bounds,
    single_obstacle_config, swept_clearance,
)
from .pure_pursuit import PurePursuit, XYPath

PROTOCOL = Path(__file__).with_name("follower_protocol.json")
REFERENCE = ROOT/"research/results/phase0a_feasibility_20261020/S0.json"
SCENARIO = ROOT/"research/nomad_isaac/two_obstacles_wide_wall_scenario.json"


def table(path, rows):
    with path.open("x", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


class PassiveEvaluation:
    """Only evaluates the interval already integrated; never supplies a command."""
    def __init__(self, config):
        self.config = config
        self.bounds = [(b["id"], *obstacle_bounds(single_obstacle_config(config, b)))
                       for b in configured_obstacles(config)]
        self.minimum = {name: math.inf for name, _, _ in self.bounds}
        self.minimum_upper = dict(self.minimum)
        self.corridor_min = math.inf
        self.overlap = False
        self.first_margin = None

    def interval(self, start, end, v, w, duration, tick):
        gaps = {name: swept_clearance(start, v, w, duration, lo, hi, self.config["agent_radius_m"],
                                      self.config["required_clearance_m"])
                for name, lo, hi in self.bounds}
        corridor = corridor_clearance(start, end, v, w, duration,
                                      self.config["corridor"], self.config["agent_radius_m"])
        for name, g in gaps.items():
            self.minimum[name] = min(self.minimum[name], g["lower_m"])
            self.minimum_upper[name] = min(self.minimum_upper[name], g["upper_m"])
        self.corridor_min = min(self.corridor_min, corridor)
        overlap = any(g["geometric_overlap"] for g in gaps.values())
        self.overlap |= overlap
        low = min(g["lower_m"] for g in gaps.values())
        if low < self.config["required_clearance_m"] and self.first_margin is None:
            self.first_margin = {"tick": tick, "simulation_time_s": tick/72,
                                 "interval_start_s": tick/72-duration, "pose": list(end),
                                 "obstacle_ids": [name for name, g in gaps.items() if g["lower_m"] < .02],
                                 "minimum_clearance_lower_m": low}
        reason = ("GEOMETRIC_COLLISION" if overlap else "CONSERVATIVE_CONTACT_STOP" if low <= 0 else
                  "CORRIDOR_CONTAINMENT_STOP" if corridor <= 0 else None)
        return {**{name+"_lower_m": g["lower_m"] for name, g in gaps.items()},
                "minimum_clearance_lower_m": low, "corridor_lower_m": corridor,
                "geometric_overlap": overlap}, reason

    def result(self):
        return {"minimum_obstacle_clearance_lower_m": self.minimum,
                "minimum_obstacle_clearance_upper_m": self.minimum_upper,
                "minimum_clearance_lower_m": min(self.minimum.values()),
                "margin_0_02_met": min(self.minimum.values()) >= .02,
                "first_margin_violation": self.first_margin, "geometric_overlap": self.overlap,
                "no_contact_certified": min(self.minimum.values()) > 0,
                "corridor_contained": self.corridor_min > 0,
                "minimum_corridor_footprint_clearance_m": self.corridor_min}


def summarize(trace, commands, evaluation, config, reason, method):
    errors = np.array([r["cross_track_error_m"] for r in trace])
    goal_dist = [float(np.linalg.norm([r["x_m"]-config["goal_pose"][0],
                                      r["y_m"]-config["goal_pose"][1]])) for r in trace]
    entry = next((r["simulation_time_s"] for r, d in zip(trace, goal_dist) if d <= .3), None)
    return {"method": method, "termination_reason": reason,
            "cross_track_error_m": {"mean": float(errors.mean()), "RMS": float(np.sqrt(np.mean(errors**2))),
                                   "max": float(errors.max()), "definition": "Unsigned polyline distance, uniform 72Hz poses including endpoints"},
            "goal_entry": entry is not None, "goal_entry_time_s": entry, "final_goal_distance_m": goal_dist[-1],
            "duration_s": trace[-1]["simulation_time_s"],
            "distance_m": sum(abs(r["v_m_s"])/72 for r in trace[1:]),
            "final_pose": [trace[-1][k] for k in ("x_m", "y_m", "yaw_rad")],
            "pose_rows": len(trace), "command_rows": len(commands), "safety": evaluation.result(),
            "saturation": {"denominator": len(commands), "basis": "command records; replay records are original 0.5s primitives",
                           "v_strict_clipping_fraction": float(np.mean([c["v_clipped"] for c in commands])),
                           "w_strict_clipping_fraction": float(np.mean([c["w_clipped"] for c in commands])),
                           "v_at_upper_bound_fraction": float(np.mean([abs(c["v_m_s"]-.2) <= 1e-12 for c in commands])),
                           "w_at_either_bound_fraction": float(np.mean([abs(abs(c["w_rad_s"])-.4) <= 1e-12 for c in commands]))}}


def pose_row(pose, tick, command, path, safety):
    return {"tick": tick, "simulation_time_s": tick/72, "x_m": pose[0], "y_m": pose[1], "yaw_rad": pose[2],
            "v_m_s": command[0], "w_rad_s": command[1],
            "cross_track_error_m": path.project(pose[:2])[1], **safety}


def reference_replay(witness, config, out):
    stored = np.asarray(witness["poses_se2"])
    commands = witness["commands_v_w_duration"]
    # Construct dense geometry from the original continuous primitives, not their chords.
    dense = [stored[0]]
    coarse = PassiveEvaluation(config)
    coarse_pose_error = 0.
    sagitta_max = 0.
    for i, (v, w, duration) in enumerate(commands):
        count = round(duration*72)
        assert abs(count/72-duration) < 1e-12 and count > 0
        end = integrate_se2(stored[i], v, w, duration)
        coarse_pose_error = max(coarse_pose_error, float(np.max(np.abs(end-stored[i+1]))))
        _, reason = coarse.interval(stored[i], end, v, w, duration, (i+1)*count)
        assert reason is None
        dense.extend(integrate_se2(stored[i], v, w, k/72) for k in range(1, count+1))
        turn = abs(w/72)
        sagitta_max = max(sagitta_max, abs(v)/72*2*math.sin(turn/4)**2/turn if turn else 0.)
    errors = [abs(coarse.minimum[k]-v) for k, v in witness["minimum_obstacle_clearance_m"].items()]
    errors.append(abs(coarse.corridor_min-witness["minimum_corridor_footprint_clearance_m"]))
    assert coarse_pose_error < 1e-12 and max(errors) < 1e-12
    dense = np.asarray(dense)
    path = XYPath(dense[:, :2])  # No native yaw or intrinsic waypoint timestamp.
    table(out/"reference_xy.csv", [{"point_index": i, "x_m": p[0], "y_m": p[1]} for i, p in enumerate(path.points)])
    evaluation = PassiveEvaluation(config)
    pose = stored[0].copy()
    safety, reason = evaluation.interval(pose, pose, 0., 0., 0., 0)
    assert reason is None
    trace = [pose_row(pose, 0, (0., 0.), path, safety)]
    records, tick, boundary_error = [], 0, 0.
    for i, (v, w, duration) in enumerate(commands):
        records.append({"primitive_id": i, "tick": tick, "simulation_time_s": tick/72,
                        "v_m_s": v, "w_rad_s": w, "duration_s": duration, "v_clipped": False, "w_clipped": False})
        for _ in range(round(duration*72)):
            start = pose.copy(); pose = integrate_se2(pose, v, w, 1/72); tick += 1
            safety, reason = evaluation.interval(start, pose, v, w, 1/72, tick)
            assert reason is None
            trace.append(pose_row(pose, tick, (v, w), path, safety))
        boundary_error = max(boundary_error, float(np.max(np.abs(pose-stored[i+1]))))
    assert boundary_error < 1e-11
    np.testing.assert_allclose([[r[k] for k in ("x_m", "y_m", "yaw_rad")] for r in trace], dense, rtol=0, atol=1e-11)
    result = summarize(trace, records, evaluation, config, "REFERENCE_REPLAY_COMPLETE", "EXACT_COMMAND_REPLAY")
    result["validation"] = {"status": "PASS", "coarse_primitive_pose_max_error": coarse_pose_error,
                            "original_primitive_clearance_max_error_m": max(errors),
                            "replayed_72Hz_boundary_pose_max_error": boundary_error,
                            "original_primitive_safety": coarse.result(),
                            "sampling_max_spacing_m": max(np.linalg.norm(np.diff(dense[:, :2], axis=0), axis=1)),
                            "sampling_arc_chord_sagitta_max_m": sagitta_max,
                            "clearance_note": "Original 0.5s bounds reproduced separately; finer 1/72s bounds differ in conservatism, not path"}
    table(out/"reference_pose_72hz.csv", trace)
    table(out/"reference_primitive_commands.csv", records)
    write_json(out/"reference_replay.json", result)
    return path, result


def simulate_follower(path, config, protocol, out):
    follower = PurePursuit(path.points, protocol["follower"])
    evaluation = PassiveEvaluation(config)
    pose = np.asarray(config["start_pose"], dtype=float)
    safety, stop = evaluation.interval(pose, pose, 0., 0., 0., 0)
    assert stop is None
    trace = [pose_row(pose, 0, (0., 0.), path, safety)]
    records = []
    reason = "SIMULATION_TIMEOUT"
    ticks = round(protocol["maximum_simulation_s"]*72)
    for tick in range(ticks):
        if tick % 8 == 0:
            command, diagnostic = follower.control(pose)
            records.append({"tick": tick, "simulation_time_s": tick/72,
                            "v_m_s": command[0], "w_rad_s": command[1], **diagnostic})
        # Integrate first. The follower never receives the post-interval geometry result.
        start = pose.copy()
        pose = integrate_se2(pose, *command, 1/72)
        safety, stop = evaluation.interval(start, pose, *command, 1/72, tick+1)
        trace.append(pose_row(pose, tick+1, command, path, safety))
        if stop:
            reason = stop; break
        if np.linalg.norm(pose[:2]-np.asarray(config["goal_pose"][:2])) <= protocol["goal_tolerance_m"]:
            reason = "GOAL_ENTRY"; break
    result = summarize(trace, records, evaluation, config, reason, "PURE_PURSUIT")
    result["classification"] = ("SAFE_GOAL_SUCCESS" if result["goal_entry"] and result["safety"]["margin_0_02_met"]
                                and result["safety"]["corridor_contained"] else
                                "SAFETY_FAILURE" if not result["safety"]["margin_0_02_met"]
                                or not result["safety"]["corridor_contained"] else "GOAL_NOT_REACHED")
    table(out/"pure_pursuit_pose_72hz.csv", trace)
    table(out/"pure_pursuit_commands_9hz.csv", records)
    write_json(out/"pure_pursuit.json", result)
    return result


def run(out):
    protocol = json.loads(PROTOCOL.read_text())
    assert sha256_file(REFERENCE) == protocol["reference_sha256"]
    assert sha256_file(SCENARIO) == protocol["scenario_sha256"]
    config = json.loads(SCENARIO.read_text())
    assert config["controller_hz"] == protocol["controller_hz"] == 9
    assert config["integration_hz"] == protocol["integration_hz"] == protocol["reference_sampling_hz"] == 72
    assert config["goal_tolerance_m"] == protocol["goal_tolerance_m"] == .3
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"follower_settings.json", protocol)
    provenance = {"reference_path": str(REFERENCE), "scenario_path": str(SCENARIO),
                  "reference_sha256": sha256_file(REFERENCE), "scenario_sha256": sha256_file(SCENARIO),
                  "protocol_sha256": sha256_file(PROTOCOL),
                  "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip(),
                  "source_sha256": {name: sha256_file(ROOT/name) for name in (
                      "research/nomad_phase0/pure_pursuit.py", "research/nomad_phase0/validate_follower.py",
                      "research/nomad_isaac/common.py", "research/nomad_isaac/clearance.py")},
                  "navigation_or_inference": False, "pure_pursuit_runs_planned": 1,
                  "safety_scope": "Passive checking after each integrated interval; no geometry in control"}
    write_json(out/"provenance.json", provenance)
    witness = json.loads(REFERENCE.read_text())["unconstrained"]["witness"]
    # Fails before the sole PP simulation if reference/geometry validation fails.
    path, replay = reference_replay(witness, config, out)
    result = simulate_follower(path, config, protocol, out)
    assert sha256_file(REFERENCE) == protocol["reference_sha256"] and sha256_file(SCENARIO) == protocol["scenario_sha256"]
    write_json(out/"output_hashes.json", {p.name: sha256_file(p) for p in out.iterdir() if p.is_file()})
    print(json.dumps({"reference": replay["validation"], "pure_pursuit": result}))


def plot(out):
    """Read saved traces only; no simulation. Uses existing system matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    target = out/"path_comparison.svg"
    preview = out/"path_comparison.png"
    if target.exists() or preview.exists():
        raise FileExistsError(target)
    provenance = json.loads((out/"provenance.json").read_text())
    scenario = Path(provenance["scenario_path"])
    assert sha256_file(scenario) == provenance["scenario_sha256"]
    c = json.loads(scenario.read_text())
    r = np.genfromtxt(out/"reference_xy.csv", delimiter=",", names=True)
    p = np.genfromtxt(out/"pure_pursuit_pose_72hz.csv", delimiter=",", names=True)
    result = json.loads((out/"pure_pursuit.json").read_text())
    plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "phase0b"})
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for b in configured_obstacles(c):
        lo, hi = obstacle_bounds(single_obstacle_config(c, b))
        ax.add_patch(Rectangle(lo, *(hi-lo), fc="#afc3a4", ec="#56684e", alpha=.7))
        ax.text(*((lo+hi)/2), b["id"], ha="center", va="center", fontsize=9, rotation=90)
    ax.plot(r["x_m"], r["y_m"], color="#296bb1", lw=2, label="Dense exact-command reference")
    ax.plot(p["x_m"], p["y_m"], color="#d46131", lw=1.8, ls="--", label="Pure Pursuit: actual offline execution")
    ax.scatter(p["x_m"][0], p["y_m"][0], color="black", s=25, label="Start")
    ax.scatter(p["x_m"][-1], p["y_m"][-1], color="#9b302d", marker="x", s=50, label="Final pose")
    ax.add_patch(Circle((p["x_m"][-1], p["y_m"][-1]), c["agent_radius_m"], fill=False, ec="#9b302d"))
    ax.add_patch(Circle(c["goal_pose"][:2], .3, color="#e8cc82", alpha=.5, label="Goal region"))
    first = result["safety"]["first_margin_violation"]
    if first:
        ax.scatter(*first["pose"][:2], marker="D", color="#8f49a3", s=35, label="First 2cm margin violation")
    for y in (-c["corridor"]["half_width"], c["corridor"]["half_width"]):
        ax.axhline(y, color="#666666", lw=1)
    ax.set(xlim=(-.2, 4.9), ylim=(-1.6, 1.6), xlabel="World X (m)", ylabel="World Y (m)",
           title=f"Phase 0-B / S0 only / {result['classification']}\nGeometric reference and independent Pure Pursuit (not Isaac navigation)")
    ax.set_aspect("equal"); ax.grid(alpha=.2); ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(target, metadata={"Date": None})
    target.write_text("\n".join(line.rstrip() for line in target.read_text().splitlines())+"\n")
    fig.savefig(preview, dpi=170)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("run", "plot"))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    (run if a.action == "run" else plot)(a.output)


if __name__ == "__main__":
    main()
