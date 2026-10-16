"""Validate recorded execution and generate one static world-XY plot (no rerun)."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np

from nomad_isaac.common import integrate_se2, original_controller, sha256_file, write_json


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
    write_json(args.output / "summary.json", report)
    fig, ax = plt.subplots(figsize=(7, 4.4), constrained_layout=True)
    ax.plot(pose[:, 0], pose[:, 1], color="#1b5e9c", linewidth=2, label="Executed agent trajectory")
    ax.scatter(*pose[0, :2], color="#205a2c", s=55, zorder=5, label="Start")
    ax.scatter(*goal[:2], color="#b24625", marker="*", s=150, zorder=5, label="Goal")
    ax.scatter(*pose[-1, :2], color="#1b5e9c", marker="x", s=70, zorder=5, label="Final pose")
    ax.add_patch(Circle(goal[:2], tolerance, color="#b24625", alpha=.13, label="Goal tolerance (0.30 m)"))
    width = summary["scenario"]["corridor"]["half_width"]
    ax.axhline(width, color=".4", linewidth=1); ax.axhline(-width, color=".4", linewidth=1)
    ax.set(xlabel="World X [m]", ylabel="World Y [m]", aspect="equal",
           xlim=(min(-.4, pose[:, 0].min()-.3), max(2., pose[:, 0].max()+.3)), ylim=(-1.65, 1.65),
           title=f"NoMaD + Isaac Sim 6 | goal entry: {summary['goal_entry']}\nMinimum goal distance: {distances.min():.3f} m")
    ax.grid(alpha=.2); ax.legend(loc="upper left", fontsize=8)
    fig.savefig(args.output / "world_xy.svg")
    plt.close(fig)
    print(json.dumps({"goal_entry": summary["goal_entry"], "termination": summary["termination_reason"],
                      "minimum_distance_m": float(distances.min()), "validation": report["validation"]}, indent=2))


if __name__ == "__main__":
    main()
