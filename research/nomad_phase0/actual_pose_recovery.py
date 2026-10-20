"""Twelve saved-pose offline searches using the existing Phase 0-A Hybrid A*."""
import argparse
import copy
import csv
import json
from pathlib import Path
import subprocess

import numpy as np

from nomad_isaac.common import ROOT, integrate_se2, sha256_file, write_json
from nomad_isaac.clearance import corridor_clearance, obstacle_bounds, point_clearance, single_obstacle_config
from .scenario_feasibility import PROTOCOL as ORIGINAL_PROTOCOL, Scene, search

PROTOCOL = Path(__file__).with_name("actual_pose_recovery_protocol.json")
SCOPE = "Oracle geometry; offline SE(2) kinematic feasibility"


def action_sets(protocol):
    a = protocol["actions"]
    b0 = a["B0"]
    b1 = b0 + a["B1_add"]
    b2 = b1 + a["B2_add"]
    assert set(map(tuple, b0)) < set(map(tuple, b1)) < set(map(tuple, b2))
    assert (len(b0), len(b1), len(b2)) == (5, 7, 12)
    return {"B0": b0, "B1": b1, "B2": b2}


def read_json(path):
    return json.loads(Path(path).read_text())


def load_inputs(protocol):
    """Exact raw/committed-summary match; rounded prompt is a tolerance check only."""
    original = read_json(ORIGINAL_PROTOCOL)["search"]
    for key in ("xy_bin_m", "heading_bins", "primitive_duration_s", "heuristic_weight",
                "max_expansions_per_search", "max_path_duration_s"):
        assert original[key] == protocol["search"][key]
    assert original["primitives_vw"] == action_sets(protocol)["B0"]
    states, hashes = [], {}
    for item in protocol["inputs"]:
        run, tracked = ROOT.parent/item["run"], ROOT/item["tracked_summary"]
        scenario, raw, spawn = (read_json(run/name) for name in
                               ("scenario.json", "summary.json", "dynamic/spawn.json"))
        published = read_json(tracked)
        if item["summary_key"]:
            published = published[item["summary_key"]]
        recorded_spawn = published.get("spawn", published.get("placement", {}).get("spawn"))
        assert spawn == recorded_spawn
        assert raw["scenario"] == scenario and raw["final_pose"] == published["navigation"]["final_pose"]
        with (run/"agent_trajectory.csv").open() as f:
            rows = list(csv.DictReader(f))
        by_tick = {int(r["tick"]): r for r in rows}
        assert len(by_tick) == len(rows) and spawn["tick"] == item["spawn_tick"]
        box = spawn["obstacle"]
        np.testing.assert_allclose(box["center_xy_m"], item["expected_dynamic_center"],
                                   atol=protocol["rounded_input_absolute_tolerance"], rtol=0)
        assert box["size_xyz_m"] == [.35, .35, .8] and spawn["active"]
        dynamic_geometry = read_json(run/"dynamic/obstacle_geometry.json")
        assert dynamic_geometry["center_xy_m"] == box["center_xy_m"]
        assert dynamic_geometry["size_xyz_m"] == box["size_xyz_m"]
        static_geometry = read_json(run/"obstacle_geometry.json")
        for actual, expected in zip(static_geometry["obstacles"], scenario["obstacles"]):
            assert all(actual[k] == expected[k] for k in ("id", "center_xy_m", "size_xyz_m"))
        assert len(static_geometry["obstacles"]) == len(scenario["obstacles"]) == 2
        assert scenario["goal_pose"] == [4.5, 0., 0.] and scenario["goal_tolerance_m"] == .3
        for label, row in (("spawn", by_tick[item["spawn_tick"]]), ("final", rows[-1])):
            pose = [float(row[k]) for k in ("x_m", "y_m", "yaw_rad")]
            np.testing.assert_array_equal(pose, spawn["pose"] if label == "spawn" else raw["final_pose"])
            np.testing.assert_allclose(pose, item[f"expected_{label}_pose"],
                                       atol=protocol["rounded_input_absolute_tolerance"], rtol=0)
            config = copy.deepcopy(scenario)
            config["start_pose"], config["dynamic_obstacle"] = pose, copy.deepcopy(box)
            bounds = [(b["id"], *obstacle_bounds(single_obstacle_config(config, b)))
                      for b in config["obstacles"]+[box]]
            gaps = {name: point_clearance(pose[:2], lo, hi, config["agent_radius_m"])
                    for name, lo, hi in bounds}
            wall = corridor_clearance(pose, pose, 0., 0., 0., config["corridor"], config["agent_radius_m"])
            states.append({"id": f"{item['id']}_{label}", "source_run": str(run),
                "tracked_summary": str(tracked.relative_to(ROOT)), "source_tick": int(row["tick"]),
                "source_sim_s": float(row["simulation_time_s"]), "pose": pose, "config": config,
                "start_obstacle_clearance_m": gaps, "start_corridor_clearance_m": wall,
                "valid_start": bool(min(gaps.values()) >= .02 and wall > 0),
                "raw_summary_pose_max_error": 0.,
                "rounded_prompt_pose_max_error": float(np.max(np.abs(np.array(pose)-item[f"expected_{label}_pose"])))})
        for name in ("agent_trajectory.csv", "scenario.json", "summary.json", "provenance.json",
                     "obstacle_geometry.json", "dynamic/spawn.json", "dynamic/obstacle_geometry.json"):
            hashes[str(run/name)] = sha256_file(run/name)
        hashes[str(tracked)] = sha256_file(tracked)
    return states, hashes


def witness_usage(witness):
    commands = witness["commands_v_w_duration"]
    elapsed, segments = 0., []
    for i, (v, w, dt) in enumerate(commands):
        mode = "reverse" if v < 0 else "in_place_rotation" if v == 0 and w != 0 else "forward"
        if mode != "forward":
            segments.append({"primitive_index": i, "mode": mode, "start_path_s": elapsed,
                             "end_path_s": elapsed+dt, "v_m_s": v, "w_rad_s": w,
                             "start_pose": witness["poses_se2"][i], "end_pose": witness["poses_se2"][i+1]})
        elapsed += dt
    return {"special_segments": segments,
            "in_place_rotation_s": sum(dt for v, w, dt in commands if v == 0 and w != 0),
            "in_place_absolute_rotation_rad": sum(abs(w)*dt for v, w, dt in commands if v == 0),
            "reverse_s": sum(dt for v, w, dt in commands if v < 0),
            "reverse_distance_m": sum(abs(v)*dt for v, w, dt in commands if v < 0)}


def run(output):
    p = read_json(PROTOCOL)
    states, hashes = load_inputs(p)
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if status:
        raise RuntimeError("Commit the fixed protocol and implementation before the 12 searches")
    output.mkdir(parents=True, exist_ok=False)
    preflight = {"scope": SCOPE, "protocol": p, "protocol_sha256": sha256_file(PROTOCOL),
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_status": status, "input_sha256": hashes, "states": states, "action_sets": action_sets(p),
        "source_sha256": {str(f.relative_to(ROOT)): sha256_file(f) for f in
            (Path(__file__), Path(__file__).with_name("scenario_feasibility.py"),
             ROOT/"research/nomad_isaac/common.py", ROOT/"research/nomad_isaac/clearance.py")}}
    write_json(output/"preflight.json", preflight)
    comparisons = []
    with (output/"execution.jsonl").open("x") as journal:
        for state in states:
            for method, primitives in action_sets(p).items():
                key = f"{state['id']}_{method}"
                journal.write(json.dumps({"event": "START", "id": key})+"\n"); journal.flush()
                settings = {**p["search"], "primitives_vw": primitives,
                            "minimum_v_m_s": -.2 if method == "B2" else 0.}
                if not state["valid_start"]:
                    result = {"status": "INVALID_START", "termination_reason": "INITIAL_CLEARANCE_OR_CORRIDOR",
                              "expanded": 0, "generated": 0, "cpu_seconds": 0., "wall_seconds": 0.,
                              "search_executed": False, "goal_reached": False, "witness": None}
                else:
                    # Direct unconstrained search: no Phase 0-A side gate or certificate.
                    result = search(Scene(state["config"], "active"), settings, side=None)
                if result["witness"]:
                    result["witness"].update(witness_usage(result["witness"]))
                write_json(output/f"{key}.json", {"scope": SCOPE, "state_id": state["id"],
                           "method": method, "settings": settings, **result})
                row = {"scope": SCOPE, "state_id": state["id"], "method": method,
                       **{k: result[k] for k in ("status", "termination_reason", "expanded", "generated",
                                                "cpu_seconds", "wall_seconds", "goal_reached")}}
                w = result["witness"]
                for field in ("path_duration_s", "distance_m", "goal_distance_m", "in_place_rotation_s",
                              "reverse_s", "reverse_distance_m", "minimum_corridor_footprint_clearance_m"):
                    row[field] = w[field] if w else None
                row["minimum_obstacle_clearance_m"] = min(w["minimum_obstacle_clearance_m"].values()) if w else None
                comparisons.append(row)
                journal.write(json.dumps({"event": "END", "id": key, "status": result["status"]})+"\n"); journal.flush()
                print(json.dumps(row), flush=True)
    assert all(sha256_file(Path(f)) == digest for f, digest in hashes.items())
    write_json(output/"summary.json", {"scope": SCOPE, "results": comparisons,
        "input_hashes_preserved": True, "search_conditions": 12, "retries": 0,
        "online_reverse_enabled": False, "one_pass_rules_used": False,
        "interpretation": p["interpretation"]})
    with (output/"comparison.csv").open("x") as f:
        writer = csv.DictWriter(f, fieldnames=list(comparisons[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(comparisons)


def plot(output):
    """One figure, saved witnesses only; no search or navigation."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    target = output/"witnesses_xy.png"
    if target.exists():
        raise FileExistsError(target)
    data = read_json(output/"preflight.json")
    colors = {"B0": "#444444", "B1": "#196db5", "B2": "#d66a16"}
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True, sharey=True)
    for ax, state in zip(axes.flat, data["states"]):
        c, start = state["config"], np.array(state["pose"])
        for box in c["obstacles"]+[c["dynamic_obstacle"]]:
            lo, hi = obstacle_bounds(single_obstacle_config(c, box))
            ax.add_patch(Rectangle(lo, *(hi-lo), facecolor="#c24d9b" if box["id"]=="DynamicObstacle" else "#a9adb4",
                                   edgecolor="#555555", alpha=.55))
        for y in (-c["corridor"]["half_width"], c["corridor"]["half_width"]):
            ax.axhline(y, color="#333333", lw=1.5)
        ax.add_patch(Circle(c["goal_pose"][:2], .3, facecolor="#c8e8ce", edgecolor="#348348"))
        for method, color in colors.items():
            r = read_json(output/f"{state['id']}_{method}.json")
            w = r["witness"]
            if not w:
                ax.plot([], [], color=color, label=f"{method}: {r['status']}")
                continue
            pose = start.copy(); points = [pose[:2].copy()]
            reverse, rotations = [], []
            for v, turn, dt in w["commands_v_w_duration"]:
                arc = np.array([integrate_se2(pose, v, turn, t)[:2] for t in np.linspace(0, dt, 37)])
                points.extend(arc[1:]); pose = integrate_se2(pose, v, turn, dt)
                if v < 0: reverse.append(arc)
                if v == 0: rotations.append(arc[0])
            points = np.array(points)
            ax.plot(points[:, 0], points[:, 1], color=color, lw=1.6,
                    label=f"{method}: {w['path_duration_s']:.1f}s / {min(w['minimum_obstacle_clearance_m'].values())*1000:.1f}mm")
            for arc in reverse:
                ax.plot(arc[:, 0], arc[:, 1], color=color, lw=3.0, ls=":")
            if rotations:
                xy = np.unique(np.round(rotations, 10), axis=0)
                ax.scatter(xy[:, 0], xy[:, 1], s=35, facecolors="none", edgecolors=color, zorder=5)
        ax.scatter(*start[:2], marker="*", s=100, color="black", zorder=6)
        ax.add_patch(Circle(start[:2], .09, fill=False, color="black", lw=.8))
        ax.arrow(*start[:2], .22*np.cos(start[2]), .22*np.sin(start[2]), width=.008, color="black", zorder=6)
        ax.set_title(state["id"].replace("_", " ")+f" | source t={state['source_sim_s']:.3f}s", fontsize=10)
        ax.set_aspect("equal"); ax.grid(alpha=.15); ax.legend(fontsize=7, loc="lower left")
        ax.set_xlabel("World X (m)"); ax.set_ylabel("World Y (m)")
        ax.set_xlim(c["corridor"]["xmin"], c["corridor"]["xmax"]); ax.set_ylim(-1.65, 1.65)
    fig.suptitle("Phase B: actual-pose recovery witnesses\nOracle geometry | offline SE(2) kinematic feasibility", fontsize=13)
    fig.text(.5, .015, "Star/arrow: actual start pose and yaw | open circles: in-place turns | dotted segments: reverse\n"
             "Paths are offline witnesses, not executed navigation; NO_PATH_FOUND is not an impossibility proof.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .07, 1, .93))
    fig.savefig(target, dpi=170); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "run", "plot"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "preflight":
        states, hashes = load_inputs(read_json(PROTOCOL))
        print(json.dumps({"scope": SCOPE, "inputs_checked": len(hashes),
            "states": [{k:s[k] for k in ("id", "pose", "valid_start", "start_obstacle_clearance_m",
                                       "start_corridor_clearance_m")} for s in states]}, indent=2))
    else:
        if args.output is None:
            parser.error("--output required")
        (run if args.action == "run" else plot)(args.output.resolve())


if __name__ == "__main__":
    main()
