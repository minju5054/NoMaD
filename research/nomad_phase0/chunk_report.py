"""Saved-data-only audit of the single Phase 0-C Isaac PILOT."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from nomad_isaac.async_report import rows, stats, validate, wrapped
from nomad_isaac.clearance import corridor_clearance, configured_obstacles, obstacle_bounds, single_obstacle_config
from nomad_isaac.common import local_to_world, sha256_file, write_json
from nomad_isaac.topomap import candidate_range, select_subgoal
from nomad_isaac.topomap_report import validate_map
from .chunk_execution import protocol, tangent_at_projection
from .pure_pursuit import PurePursuit


def trace(run):
    with (run/"agent_trajectory.csv").open() as f:
        records = list(csv.DictReader(f))
    poses = np.array([[float(r[k]) for k in ("x_m", "y_m", "yaw_rad")] for r in records])
    return records, poses


def navigation_record(run, actual_override=False):
    summary = json.loads((run/"summary.json").read_text())
    records, poses = trace(run)
    intervals = rows(run/"clearance.jsonl")[1:]
    control = rows(run/"controller.jsonl")
    events = rows(run/"events.jsonl")
    violation = [r for r in intervals if r["lower_m"] < .02]
    dt = 1/summary["scenario"]["integration_hz"]
    stop_time = sum(dt for r in records[1:] if float(r["v_m_s"]) == float(r["w_rad_s"]) == 0)
    safety = summary["obstacle_evaluation"]
    classification = ("SAFETY_FAILURE" if not safety["safety_margin_met"] or
                      not safety["corridor_containment_certified"] or safety["geometric_overlap"]
                      else "SAFE_GOAL_SUCCESS" if summary["goal_entry"] else "NO_GOAL_WITHOUT_SAFETY_FAILURE")
    fields = ("applied_v_m_s", "applied_w_rad_s") if actual_override else ("v_m_s", "w_rad_s")
    return {"classification": classification, "goal_entry": summary["goal_entry"],
            "goal_entry_sim_s": summary["simulation_duration_s"] if summary["goal_entry"] else None,
            "termination": summary["termination_reason"], "duration_s": summary["simulation_duration_s"],
            "final_pose": poses[-1].tolist(), "final_goal_distance_m": summary["final_goal_distance_m"],
            "minimum_goal_distance_m": summary["minimum_goal_distance_m"],
            "distance_m": summary["distance_travelled_m"], "stop_duration_s": stop_time,
            "margin_violation_intervals": len(violation),
            "margin_violation_interval_duration_s": sum(r["end_sim_s"]-r["start_sim_s"] for r in violation),
            "first_margin_violation_interval": violation[0] if violation else None,
            "obstacles": safety,
            "received": summary["received_count"], "switches": len(events), "controller_ticks": len(control),
            "timeout_episodes": summary["waypoint_timeout_episodes"],
            "busy_observation_skips": summary["busy_observation_skips"],
            "missed_capture_slots": summary["missed_capture_slots"],
            "warm_inference_ms": stats([r["inference_ms"] for r in rows(run/"received.jsonl")[1:]]),
            "observation_to_switch_wall_s": stats([(e["application_monotonic_ns"]-e["observation_monotonic_ns"])/1e9 for e in events]),
            "v_upper_bound_occupancy_fraction": sum(abs(c[fields[0]]-.2)<1e-12 for c in control)/len(control),
            "w_bound_occupancy_fraction": sum(abs(abs(c[fields[1]])-.4)<1e-12 for c in control)/len(control)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--pd-baseline", type=Path, required=True)
    parser.add_argument("--preservation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    p = protocol()
    summary = json.loads((args.run/"summary.json").read_text())
    assert summary["pure_pursuit_enabled"] and summary["experiment_label"] == "PILOT"
    assert json.loads((args.run/"chunk_pilot_protocol.json").read_text()) == p
    preservation = json.loads(args.preservation.read_text())
    assert all(sha256_file(Path(name)) == digest for name, digest in preservation["files"].items())
    # Existing validator also preserves its historical synchronous reference.
    runtime = validate(args.run, args.run.parent/"two_obstacles_01", args.out/"runtime_validation",
                       actual_command_override=True)
    manifest, map_validation = validate_map(Path(summary["scenario"]["topomap_manifest"]))
    config = summary["scenario"]
    received, control, events, inference = (rows(args.run/name) for name in
        ("received.jsonl", "controller.jsonl", "events.jsonl", "model/inference.jsonl"))
    observations = {r["observation_id"]: r for r in rows(args.run/"observations.jsonl")}
    records, poses = trace(args.run)
    clearance = rows(args.run/"clearance.jsonl")
    frames = {}
    for identifier, row in observations.items():
        with Image.open(args.run/row["rgb_file"]) as im:
            frame = np.array(im)
        assert hashlib.sha256(frame.tobytes()).hexdigest() == row["frame_sha256"]
        frames[identifier] = frame
    closest = 0
    for r in inference:
        t = r["topomap"]
        a, b = candidate_range(closest, len(manifest["nodes"])-1)
        assert (a, b) == (t["candidate_start"], t["candidate_end_inclusive"])
        closest, subgoal, _ = select_subgoal(t["distances"], a)
        assert (closest, subgoal) == (t["closest_node"], t["selected_subgoal_id"])
        assert t["diffusion_passes"] == 1 and t["diffusion_steps"] == 10
        assert r["goal_sha256"] == manifest["nodes"][subgoal]["rgb_sha256"]
        history = np.stack([frames[i] for i in r["history_observation_ids"]])
        assert hashlib.sha256(history.tobytes()).hexdigest() == r["history_sha256"]
    by_tick = {round(e["application_sim_s"]*72): e for e in events}
    follower = None
    previous_command = np.zeros(2)
    max_command_error = max_corridor_error = 0.
    switches = []
    for c in control:
        tick = round(c["simulation_time_s"]*72)
        pose = poses[tick]
        if tick in by_tick:
            e = by_tick[tick]
            old_path = follower.path if follower is not None else None
            with np.load(args.run/f"model/derived/{e['id']:04d}.npz", allow_pickle=False) as data:
                world = local_to_world(data["metric"][0], np.asarray(e["observation_pose"]))
            np.testing.assert_allclose(world, e["chunk"]["world_xy_m"], atol=1e-12, rtol=0)
            try:
                follower = PurePursuit(world, p["follower"])
            except ValueError:
                follower = None
            assert e["chunk"]["path_valid"] == (follower is not None)
            old_t = tangent_at_projection(old_path, pose[:2], p["diagnostic_tangent_minimum_segment_m"])
            fresh_t = tangent_at_projection(follower.path if follower else None, pose[:2],
                                            p["diagnostic_tangent_minimum_segment_m"])
            transition = e["chunk_transition"]
            for stored, computed in ((transition["old_tangent_at_B"], old_t),
                                     (transition["fresh_tangent_at_B"], fresh_t)):
                assert stored.keys() == computed.keys()
                for key, value in computed.items():
                    if value is None or isinstance(value, (str, bool, int)):
                        assert stored[key] == value
                    else:
                        np.testing.assert_allclose(stored[key], value, atol=1e-12, rtol=0)
            np.testing.assert_allclose(transition["actual_command_before"], previous_command, atol=1e-12, rtol=0)
            remaining = float(follower.path.s[-1]-follower.path.project(pose[:2])[0]) if follower else None
            if remaining is None:
                assert transition["remaining_length_at_switch_m"] is None
            else:
                np.testing.assert_allclose(remaining, transition["remaining_length_at_switch_m"], atol=1e-12, rtol=0)
            switches.append({"id": e["id"], "old_id": transition["old_id"],
                "observation_sim_s": e["observation_sim_s"], "switch_sim_s": e["application_sim_s"],
                "ready_monotonic_ns": e["ready_monotonic_ns"],
                "observation_pose": json.dumps(e["observation_pose"]), "switch_pose": json.dumps(e["agent_pose_at_switch"]),
                "native_length_m": e["chunk"]["native_length_m"], "remaining_length_m": remaining,
                "path_valid": e["chunk"]["path_valid"],
                "endpoint_clamped": e["pure_pursuit"]["endpoint_clamped"],
                "tangent_change_rad": transition["signed_tangent_change_rad"],
                "obs_switch_robot_yaw_change_rad": float(wrapped(pose[2]-e["observation_pose"][2])),
                "delta_v_m_s": transition["actual_command_delta"][0],
                "delta_w_rad_s": transition["actual_command_delta"][1],
                "applied_v_m_s": e["applied_v_m_s"], "applied_w_rad_s": e["applied_w_rad_s"],
                "stop_reason": e["pure_pursuit"]["stop_reason"]})
        command = (0., 0.)
        if c["valid"] and follower is not None:
            command, details = follower.control(pose)
            for key, value in details.items():
                np.testing.assert_allclose(c["pure_pursuit"][key], value, atol=1e-12, rtol=0)
            assert c["pure_pursuit"]["endpoint_clamped"] == (follower.progress+.25 > follower.path.s[-1])
        actual = np.array([c["applied_v_m_s"], c["applied_w_rad_s"]])
        max_command_error = max(max_command_error, float(np.max(np.abs(actual-command))))
        if tick in by_tick:
            np.testing.assert_allclose(by_tick[tick]["chunk_transition"]["actual_command_after"], actual, atol=1e-12, rtol=0)
        previous_command = actual
    assert max_command_error < 1e-12
    for i in range(1, len(records)):
        c = records[i]
        gap = corridor_clearance(poses[i-1], poses[i], float(c["v_m_s"]), float(c["w_rad_s"]),
                                 1/72, config["corridor"], config["agent_radius_m"])
        max_corridor_error = max(max_corridor_error, abs(gap-clearance[i]["corridor_lower_m"]))
    assert max_corridor_error < 1e-12
    # Every new capture pose was matched to the executed trace by the runtime audit.
    # Check that later worker inputs contain captures after actual PP motion.
    feedback = []
    for r in received[1:]:
        prior = [e for e in events if e["application_sim_s"] < r["observation_sim_s"]]
        if prior:
            old = prior[-1]
            displacement = float(np.linalg.norm(np.array(r["observation_pose"][:2])-old["agent_pose_at_switch"][:2]))
            if displacement > 1e-8:
                feedback.append({"fresh_id": r["id"], "previous_applied_id": old["id"],
                                 "pose_displacement_m": displacement, "observation_id": r["observation_id"]})
    assert feedback
    valid_controls = [c["pure_pursuit"] for c in control if c["valid"] and c["pure_pursuit"]["path_valid"]]
    transitions = [s for s in switches if s["old_id"] >= 0]
    tangent = [abs(s["tangent_change_rad"]) for s in transitions if s["tangent_change_rad"] is not None]
    lengths = [r["chunk"]["native_length_m"] for r in received]
    remaining = [s["remaining_length_m"] for s in switches if s["remaining_length_m"] is not None]
    report = {"label": "PILOT", "source_run": str(args.run), "baseline": str(args.pd_baseline),
        "execution_git_sha": runtime["execution_git_sha"], "execution_git_status": runtime["execution_git_status"],
        "protocol_sha256": sha256_file(args.run/"chunk_pilot_protocol.json"),
        "validation": {"status": "PASS", "map": map_validation, "preserved_hashes": len(preservation["files"]),
                       "max_actual_command_error": max_command_error, "max_corridor_error": max_corridor_error,
                       "max_pose_integration_error": runtime["validation"]["max_pose_integration_error"],
                       "normalization_and_observation_anchor": "PASS", "topomap_selection_and_RGB_history": "PASS",
                       "feedback_count": len(feedback), "feedback_first_example": feedback[0]},
        "navigation": navigation_record(args.run, True), "original_pd_reference": navigation_record(args.pd_baseline),
        "runtime": {key: runtime[key] for key in ("async_reproduction", "real_time_pacing_pass",
            "inference_clock_mapping_pass", "pacing", "timeout", "terminal_unapplied_requests")},
        "chunks": {"received": len(received), "switched": len(events), "native_length_m": stats(lengths),
                   "length_below_lookahead_count": sum(x < .25 for x in lengths),
                   "length_below_lookahead_fraction": sum(x < .25 for x in lengths)/len(lengths),
                   "remaining_at_switch_m": stats(remaining),
                   "remaining_below_lookahead_count": sum(x < .25 for x in remaining),
                   "invalid_received_ids": [r["id"] for r in received if not r["chunk"]["path_valid"]],
                   "clamped_control_count": sum(c["endpoint_clamped"] for c in valid_controls),
                   "valid_path_control_count": len(valid_controls),
                   "clamped_control_fraction": sum(c["endpoint_clamped"] for c in valid_controls)/len(valid_controls),
                   "clamped_switch_count": sum(s["endpoint_clamped"] is True for s in switches)},
        "control": {"stop_reason_tick_counts": dict(Counter(c["pure_pursuit"]["stop_reason"] for c in control)),
                    "v_clipping_fraction_all_ticks": sum(c["pure_pursuit"]["v_clipped"] for c in control)/len(control),
                    "w_clipping_fraction_all_ticks": sum(c["pure_pursuit"]["w_clipped"] for c in control)/len(control),
                    "w_clipping_fraction_valid_path_ticks": sum(c["w_clipped"] for c in valid_controls)/len(valid_controls)},
        "transitions": {"pairs": len(transitions), "valid_tangent_pairs": len(tangent),
                        "invalid_tangent_pairs": len(transitions)-len(tangent), "abs_tangent_change_rad": stats(tangent),
                        "abs_delta_v_m_s": stats([abs(s["delta_v_m_s"]) for s in transitions]),
                        "abs_delta_w_rad_s": stats([abs(s["delta_w_rad_s"]) for s in transitions]),
                        "saturated_opposite_turn_switch_ids": [s["id"] for s in transitions if abs(s["delta_w_rad_s"]) >= .8-1e-12]},
        "limitations": ["Single unpaired closed-loop PILOT; no performance superiority or statistical inference",
                       "Fixed 0-B parameters, no rerun/tuning; main executor decision remains open",
                       "Native path tangents are geometric diagnostics, not yaw output, timing or physical correspondence",
                       "Oracle geometry is passive post-interval evaluation; no safety override or reverse recovery",
                       "Original PD values in controller/events are reference-only; actual command uses applied fields",
                       "Canonical SE2 kinematics with real Isaac RGB and GPU NoMaD, not PhysX wheel dynamics",
                       "Violation duration counts full 72Hz inspection intervals, not exact continuous threshold crossing time"]}
    write_json(args.out/"summary.json", report)
    with (args.out/"chunk_switches.csv").open("x") as f:
        writer = csv.DictWriter(f, fieldnames=list(switches[0]))
        writer.writeheader(); writer.writerows(switches)
    plot(args.run, args.pd_baseline, config, report, args.out/"trajectory.png")
    print(json.dumps({"classification": report["navigation"]["classification"], "goal": summary["goal_entry"],
                      "switches": len(events), "validation": "PASS", "out": str(args.out)}))


def plot(run, baseline, config, report, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    _, actual = trace(run)
    _, original = trace(baseline)
    fig, ax = plt.subplots(figsize=(9, 5))
    for box in configured_obstacles(config):
        lo, hi = obstacle_bounds(single_obstacle_config(config, box))
        ax.add_patch(Rectangle(lo, *(hi-lo), color="forestgreen", alpha=.45))
        ax.text(*((lo+hi)/2), box["id"].replace("StaticObstacle", "Obstacle "), ha="center", va="center", fontsize=9)
    ax.plot(original[:, 0], original[:, 1], "--", color=".5", label="Stored original PD (unpaired reference)")
    ax.plot(actual[:, 0], actual[:, 1], color="tab:blue", lw=2, label="Pure Pursuit PILOT (actual)")
    ax.scatter(*actual[0, :2], c="black", marker="o", label="Start")
    ax.scatter(*actual[-1, :2], c="red", marker="x", s=70, label="End")
    ax.add_patch(Circle(config["goal_pose"][:2], config["goal_tolerance_m"], fill=False, color="tab:orange"))
    ax.scatter(*config["goal_pose"][:2], c="tab:orange", marker="*", s=100, label="Goal (0.30 m)")
    for y in (-config["corridor"]["half_width"], config["corridor"]["half_width"]):
        ax.axhline(y, c="black", lw=1)
    ax.set(xlabel="World X [m]", ylabel="World Y [m]",
           title=f"Phase 0-C PILOT — {report['navigation']['classification']}")
    ax.set_aspect("equal"); ax.grid(alpha=.2); ax.legend(loc="best", fontsize=8)
    fig.tight_layout(); fig.savefig(output, dpi=160); plt.close(fig)


if __name__ == "__main__":
    main()
