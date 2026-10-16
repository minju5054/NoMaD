"""Validate recorded execution and generate one static world-XY plot (no rerun)."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np

from nomad_isaac.common import integrate_se2, original_controller, sha256_file, write_json
from nomad_isaac.clearance import (corridor_clearance, obstacle_bounds, planning_diagnostic,
                                  swept_clearance, first_contact_bracket)


def verify_obstacle_run(run, summary, trajectory, pose, times):
    config = summary["scenario"]
    lower, upper = obstacle_bounds(config)
    radius = config["agent_radius_m"]
    records = [json.loads(x) for x in (run / "clearance.jsonl").read_text().splitlines()]
    assert len(records) == len(pose)
    for i, row in enumerate(records):
        previous = pose[max(0, i-1)]
        duration = times[i]-times[max(0, i-1)]
        v, w = trajectory["v_m_s"][i], trajectory["w_rad_s"][i]
        np.testing.assert_allclose(row["start_pose"], previous, atol=1e-12, rtol=0)
        np.testing.assert_allclose(row["end_pose"], pose[i], atol=1e-12, rtol=0)
        bound = swept_clearance(previous, v, w, duration, lower, upper, radius, config["required_clearance_m"])
        for key in ["lower_m", "upper_m", "bound_width_m"]:
            np.testing.assert_allclose(row[key], bound[key], atol=1e-11, rtol=0)
        wall = corridor_clearance(previous, pose[i], v, w, duration, config["corridor"], radius)
        np.testing.assert_allclose(row["corridor_lower_m"], wall, atol=1e-11, rtol=0)
        assert bool(row["geometric_overlap"]) == bound["geometric_overlap"]
        if row["lower_m"] <= 0 or row["corridor_lower_m"] <= 0:
            assert i == len(records)-1, "Movement continued after geometric stop"
    evaluation = summary["obstacle_evaluation"]
    assert evaluation["geometric_overlap"] == any(r["geometric_overlap"] for r in records)
    assert evaluation["safety_margin_met"] == all(r["lower_m"] >= config["required_clearance_m"] for r in records)
    assert evaluation["corridor_containment_certified"] == all(r["corridor_lower_m"] > 0 for r in records)
    for key, field in [("minimum_swept_clearance_lower_m", "lower_m"), ("minimum_swept_clearance_upper_m", "upper_m"),
                       ("minimum_corridor_clearance_lower_m", "corridor_lower_m")]:
        np.testing.assert_allclose(evaluation[key], min(r[field] for r in records), rtol=0, atol=1e-11)
    success = (summary["goal_entry"] and not evaluation["geometric_overlap"] and evaluation["safety_margin_met"]
               and evaluation["corridor_containment_certified"] and evaluation["first_contact"] is None)
    assert evaluation["avoidance_success"] == success
    if evaluation["first_contact"] is not None:
        r = records[-1]
        bracket = first_contact_bracket(r["start_pose"], r["v"], r["w"], r["end_sim_s"]-r["start_sim_s"], lower, upper, radius)
        np.testing.assert_allclose(evaluation["first_contact"]["pose_at_bracket_end"], bracket["pose_at_bracket_end"], atol=1e-8, rtol=0)
    plans = [json.loads(x) for x in (run / "planning.jsonl").read_text().splitlines()]
    assert len(plans) == summary["inference_count"]
    for p in plans:
        with np.load(run / "model/derived" / f"{p['id']:04d}.npz") as data:
            actual = planning_diagnostic(data["metric"][0], p["observation_pose"], config)
        for key in ["world_xy_m", "polyline_clearance_m", "through_selected_index_2_clearance_m", "selected_point_clearance_m"]:
            np.testing.assert_allclose(p[key], actual[key], rtol=0, atol=1e-11)
    timings = [json.loads(x)["inference_ms"] for x in (run / "model/inference.jsonl").read_text().splitlines()]
    return plans, {"swept_intervals_verified": len(records), "planning_diagnostics_verified": len(plans),
                   "stop_at_first_detected_interval": True if evaluation["first_contact"] is not None else None,
                   "contact_stop_runtime_status": "observed" if evaluation["first_contact"] is not None else "NOT_EXERCISED_no_contact",
                   "avoidance_success_criteria_verified": True,
                   "first_inference_ms": timings[0], "inference_median_ms": float(np.median(timings)),
                   "inference_p95_ms": float(np.percentile(timings, 95)),
                   "minimum_predicted_sample0_polyline_clearance_m": min(p["polyline_clearance_m"] for p in plans),
                   "predicted_sample0_overlap_count": sum(p["polyline_clearance_m"] <= 0 for p in plans)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = json.loads((args.run / "summary.json").read_text())
    events = [json.loads(line) for line in (args.run / "events.jsonl").read_text().splitlines()]
    trajectory = np.genfromtxt(args.run / "agent_trajectory.csv", delimiter=",", names=True)
    pose = np.column_stack([trajectory["x_m"], trajectory["y_m"], trajectory["yaw_rad"]])
    times = trajectory["simulation_time_s"]
    expected_dt = 1 / summary["scenario"]["integration_hz"]
    np.testing.assert_allclose(np.diff(times), expected_dt, atol=1e-12)
    max_pose_error = 0.
    for i in range(1, len(pose)):
        predicted = integrate_se2(pose[i-1], trajectory["v_m_s"][i], trajectory["w_rad_s"][i], times[i]-times[i-1])
        max_pose_error = max(max_pose_error, float(np.max(np.abs(predicted - pose[i]))))
    assert max_pose_error < 1e-8
    goal = np.array(summary["scenario"]["goal_pose"])
    distances = np.linalg.norm(pose[:, :2] - goal[:2], axis=1)
    tolerance = summary["scenario"]["goal_tolerance_m"]
    assert bool(np.any(distances <= tolerance)) == summary["goal_entry"]
    assert abs(float(distances.min()) - summary["minimum_goal_distance_m"]) < 1e-10
    oracle = original_controller()
    for event in events:
        identifier = event["id"]
        with np.load(args.run / "model/raw" / f"{identifier:04d}.npz") as raw, \
                np.load(args.run / "model/derived" / f"{identifier:04d}.npz") as derived:
            normalized = raw["normalized_diffusion"]
            assert normalized.shape == (8, 8, 2) and np.isfinite(normalized).all()
            deltas = ((normalized + 1) / 2) * np.array([7.5, 8.]) + np.array([-2.5, -4.])
            cumulative = np.cumsum(deltas, axis=1).astype(np.float32)
            np.testing.assert_array_equal(cumulative, derived["cumulative"])
            np.testing.assert_array_equal(cumulative * .05, derived["metric"])
            np.testing.assert_array_equal(derived["metric"][0, 2], derived["selected_waypoint"])
            np.testing.assert_array_equal(derived["selected_waypoint"], event["selected_waypoint_m"])
            np.testing.assert_array_equal(oracle(derived["selected_waypoint"].tolist()), [event["v_m_s"], event["w_rad_s"]])
        np.testing.assert_allclose(np.diff(event["history_sim_s"]), .25, atol=1e-12)
        assert event["received_sim_s"] == event["observation_sim_s"]
        assert 0 <= event["application_sim_s"] - event["observation_sim_s"] < 1/9 + 1e-12
        assert event["application_monotonic_ns"] >= event["inference_end_monotonic_ns"] >= event["observation_monotonic_ns"]
    assert len(list((args.run / "model/raw").glob("*.npz"))) == summary["inference_count"]
    controls = [json.loads(line) for line in (args.run / "controller.jsonl").read_text().splitlines()]
    np.testing.assert_allclose(np.diff([c["simulation_time_s"] for c in controls]), 1/9, atol=1e-12)
    failure = None if summary["goal_entry"] else {
        "category": "navigation_goal_not_reached",
        "adapter_fault_detected": False,
        "evidence": "Rendered RGB/axis/color gate, finite waypoint, source-equivalent controller, immutable selected waypoint and exact integrated USD pose checks passed.",
        "cause_limit": "One fixed scene/run cannot isolate model domain gap, camera intrinsics, or fixed-goal policy limitations."}
    report = {**summary, "run_directory": str(args.run.resolve()),
              "provenance": json.loads((args.run / "provenance.json").read_text()),
              "nomad_environment": json.loads((args.run / "model/environment.json").read_text()),
              "validation": {"status": "PASS", "trajectory_rows": len(pose), "applied_events": len(events),
                             "controller_refreshes": len(controls), "max_pose_integration_error": max_pose_error,
                             "controller_matches_original": True, "normalization_matches_preflight": True,
                             "selected_waypoints_unmodified": True, "history_order_verified": True,
                             "goal_entry_from_world_pose": True},
              "failure_analysis": failure,
              "raw_file_sha256": {p: sha256_file(args.run / p) for p in
                                  ["agent_trajectory.csv", "events.jsonl", "controller.jsonl", "goal.png", "observation_start.png", "observation_final.png"]}}
    if "obstacle_evaluation" in summary:
        plans, checks = verify_obstacle_run(args.run, summary, trajectory, pose, times)
        report["validation"].update(checks)
        report["failure_analysis"] = None if summary["obstacle_evaluation"]["avoidance_success"] else {
            "category": summary["obstacle_evaluation"]["category"], "adapter_fault_detected": False,
            "scope": "Single fixed policy/controller run; planning polylines are separate from executed kinematic motion; no PhysX or general success-rate claim."}
        for p in ["clearance.jsonl", "planning.jsonl", "obstacle_geometry.json", "scene.usda"]:
            report["raw_file_sha256"][p] = sha256_file(args.run / p)
    write_json(args.output / "summary.json", report)
    fig, ax = plt.subplots(figsize=(7, 4.4), constrained_layout=True)
    ax.plot(pose[:, 0], pose[:, 1], color="#1b5e9c", linewidth=2, label="Executed agent trajectory")
    ax.scatter(*pose[0, :2], color="#205a2c", s=55, zorder=5, label="Start")
    ax.scatter(*goal[:2], color="#b24625", marker="*", s=150, zorder=5, label="Goal")
    ax.scatter(*pose[-1, :2], color="#1b5e9c", marker="x", s=70, zorder=5, label="Final pose")
    ax.add_patch(Circle(goal[:2], tolerance, color="#b24625", alpha=.13, label="Goal tolerance (0.30 m)"))
    width = summary["scenario"]["corridor"]["half_width"]
    if "obstacle_evaluation" in summary:
        lower, upper = obstacle_bounds(summary["scenario"])
        ax.add_patch(Rectangle(lower, *(upper-lower), facecolor="#31a354", edgecolor="#14532d", label="Static obstacle"))
        ax.add_patch(Circle(pose[-1, :2], summary["scenario"]["agent_radius_m"], fill=False, edgecolor="#1b5e9c", label="Final footprint (r=0.12 m)"))
        diagnostic = min(plans, key=lambda p: p["polyline_clearance_m"])
        predicted = np.vstack([np.asarray(diagnostic["observation_pose"])[:2], diagnostic["world_xy_m"]])
        ax.plot(predicted[:,0], predicted[:,1], "--", color="#ce7b13", linewidth=1.5,
                label=f"Sample 0 at {diagnostic['observation_sim_s']:.2f}s (prediction only)")
    ax.axhline(width, color=".4", linewidth=1); ax.axhline(-width, color=".4", linewidth=1)
    ax.set(xlabel="World X [m]", ylabel="World Y [m]", aspect="equal",
           xlim=(min(-.4, pose[:, 0].min()-.3), max(2., pose[:, 0].max()+.3)), ylim=(-1.65, 1.65),
           title=f"NoMaD + Isaac Sim 6 | goal entry: {summary['goal_entry']}\nMinimum goal distance: {distances.min():.3f} m")
    ax.grid(alpha=.2); ax.legend(loc="upper left", fontsize=8)
    if "obstacle_evaluation" in summary:
        ax.set_title(f"NoMaD static obstacle | avoidance success: {summary['obstacle_evaluation']['avoidance_success']}\nSwept clearance lower bound: {summary['obstacle_evaluation']['minimum_swept_clearance_lower_m']:.4f} m")
        ax.legend(loc="upper left", fontsize=6.5)
    svg_path = args.output / "world_xy.svg"
    fig.savefig(svg_path)
    # Matplotlib adds trailing spaces inside multiline SVG paths; keep Git clean.
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text().splitlines()) + "\n")
    plt.close(fig)
    print(json.dumps({"goal_entry": summary["goal_entry"], "termination": summary["termination_reason"],
                      "minimum_distance_m": float(distances.min()), "validation": report["validation"]}, indent=2))


if __name__ == "__main__":
    main()
