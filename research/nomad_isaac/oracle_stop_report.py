"""Validate one oracle STOP run using saved logs; never starts inference/navigation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .async_report import rows, stats, validate
from .clearance import configured_obstacles, corridor_clearance, obstacle_bounds, single_obstacle_config, swept_clearance
from .common import ROOT, sha256_file, write_json
from .old_rollout_obstacle_report import equivalent
from .old_rollout_placement import place_on_old
from .oracle_safety_stop import evaluate
from .topomap import candidate_range, select_subgoal
from .topomap_report import validate_map
from .topomap_sudden_report import table


def report(run, out):
    out.mkdir(parents=True, exist_ok=False)
    summary = json.loads((run/"summary.json").read_text())
    config = summary["scenario"]
    provenance = json.loads((run/"provenance.json").read_text())
    assert provenance["git_status"] == "" and provenance["oracle_safety_stop"]
    assert summary["oracle_safety_stop_enabled"]
    # The original audit still checks nominal PD. Only its integration link reads actual override fields.
    runtime = validate(run, run.parent/"two_obstacles_01", out/"runtime", actual_command_override=True)
    manifest, map_check = validate_map(Path(config["topomap_manifest"]))
    received, workers, requests, controls, gates, events = [rows(run/name) for name in
        ("received.jsonl", "model/inference.jsonl", "requests.jsonl", "controller.jsonl", "safety_stop.jsonl", "events.jsonl")]
    observations = [o for o in rows(run/"observations.jsonl") if "observation_id" in o]
    trace = np.genfromtxt(run/"agent_trajectory.csv", delimiter=",", names=True)
    poses = np.column_stack([trace[k] for k in ("x_m", "y_m", "yaw_rad")])
    spawn = summary["dynamic_obstacle"]["spawn"]
    box = spawn["obstacle"] if spawn else None
    assert len(gates) == len(controls)
    first_active = next((g for g in gates if g["active"]), None)
    max_prediction_error = 0.
    for control, gate in zip(controls, gates):
        tick = gate["tick"]
        np.testing.assert_array_equal(gate["pose"], poses[tick])
        nominal = [control["v_m_s"], control["w_rad_s"]]
        assert nominal == gate["nominal_vw"]
        assert gate["active"] == (box is not None and tick >= box["spawn_tick"])
        if gate["active"]:
            check = evaluate(config, poses[tick], nominal, box)
            equivalent(check, gate["prediction"])
            max_prediction_error = max(max_prediction_error,
                abs(check["minimum_clearance_lower_m"]-gate["prediction"]["minimum_clearance_lower_m"]))
        assert gate["blocked"] == bool(gate["active"] and control["valid"] and not gate["prediction"]["safe"])
        assert gate["applied_vw"] == ([0., 0.] if gate["blocked"] else nominal)
        assert gate["applied_vw"] == [control["applied_v_m_s"], control["applied_w_rad_s"]]
    # Verify every actual interval's original monitoring, including the zero-duration activation tick.
    static = rows(run/"clearance.jsonl")
    dynamic = rows(run/"dynamic/clearance.jsonl") if spawn else []
    activation = rows(run/"dynamic/activation.jsonl")
    max_clearance_error = 0.
    for i, a in enumerate(activation):
        assert a["tick"] == i and a["active"] == bool(spawn and i >= spawn["tick"])
        assert a["collision_checked"] == a["active"]
        if a["active"]:
            duration = 0. if i == spawn["tick"] else 1/72
            start = poses[i] if duration == 0 else poses[i-1]
            command = [trace["v_m_s"][i], trace["w_rad_s"][i]]
            check = swept_clearance(start, *command, duration, *obstacle_bounds(single_obstacle_config(config, box)), .09)
            saved = dynamic[i-spawn["tick"]]
            max_clearance_error = max(max_clearance_error, abs(check["lower_m"]-saved["lower_m"]))
            assert check["geometric_overlap"] == saved["geometric_overlap"]
        duration = 1/72 if i else 0.
        gap = corridor_clearance(poses[max(0, i-1)], poses[i], trace["v_m_s"][i],
                                 trace["w_rad_s"][i], duration, config["corridor"], .09)
        max_clearance_error = max(max_clearance_error, abs(gap-static[i]["corridor_lower_m"]))
    assert max_clearance_error < 1e-12
    decision = summary["dynamic_obstacle"]["placement"]
    if decision:
        recreated = place_on_old(config, decision["pose"], *decision["old_command_vw"],
                                 decision["old_id"], decision["old_command_valid"], decision["old_remaining_timeout_s"])
        equivalent(recreated, {k: decision[k] for k in recreated})
    if spawn:
        update = json.loads((run/"dynamic_render_update.json").read_text())
        assert update["obstacle"] == box == decision["obstacle"]
        lower, upper = obstacle_bounds(single_obstacle_config(config, box))
        np.testing.assert_allclose(update["usd_aabb"], [[*lower, 0], [*upper, .8]], atol=1e-12, rtol=0)
    frames, visible = {}, []
    for o in observations:
        image = np.asarray(Image.open(run/o["rgb_file"]).convert("RGB"))
        assert hashlib.sha256(image.tobytes()).hexdigest() == o["frame_sha256"]
        frames[o["observation_id"]] = image
        rgb = image.astype(float)
        magenta = (rgb[:,:,0] > 1.5*rgb[:,:,1]) & (rgb[:,:,2] > 1.5*rgb[:,:,1]) & (rgb[:,:,0] > 40) & (rgb[:,:,2] > 40)
        assert int(magenta.sum()) == o["dynamic"]["magenta_pixels"]
        if not o["dynamic"]["active"]:
            assert not magenta.any()
        if o["dynamic"]["visible"]:
            visible.append(o)
    closest = 0
    for r, worker, q in zip(received, workers, requests):
        top = r["topomap"]
        assert top == worker["topomap"]
        a, b = candidate_range(closest, 13)
        assert top["candidate_ids"] == list(range(a, b+1)) and top["previous_closest_node"] == closest
        closest, selected, _ = select_subgoal(top["distances"], a)
        assert (closest, selected) == (top["closest_node"], top["selected_subgoal_id"])
        assert r["goal_sha256"] == manifest["nodes"][selected]["rgb_sha256"]
        history = np.stack([frames[i] for i in q["history_observation_ids"]])
        assert hashlib.sha256(history.tobytes()).hexdigest() == worker["history_sha256"]
    # Episode intervals use simulation time; receipt/capture counts use separate monotonic endpoints.
    episodes = []
    active_episode = None
    for gate in gates:
        if gate["blocked"] and active_episode is None:
            active_episode = {"start_sim_s": gate["simulation_time_s"], "start_host_ns": gate["decision_end_monotonic_ns"],
                "start_tick": gate["tick"], "pose": gate["pose"], "waypoint_id_at_stop": gate["waypoint_id"],
                "current_clearance_m": min(gate["prediction"]["current_obstacle_clearance_m"].values()),
                "nominal_predicted_min_m": gate["prediction"]["minimum_clearance_lower_m"]}
        if active_episode is not None and not gate["blocked"]:
            active_episode.update(end_sim_s=gate["simulation_time_s"], end_host_ns=gate["decision_end_monotonic_ns"],
                end_tick=gate["tick"], resumed_motion=bool(np.any(np.array(gate["applied_vw"]) != 0)),
                end_waypoint_id=gate["waypoint_id"], end_reason="safe_command" if gate["waypoint_status"] == "valid" else gate["waypoint_status"])
            episodes.append(active_episode)
            active_episode = None
    if active_episode is not None:
        active_episode.update(end_sim_s=summary["simulation_duration_s"], end_host_ns=int(trace["monotonic_ns"][-1]),
            end_tick=len(trace)-1, resumed_motion=False, end_waypoint_id=gates[-1]["waypoint_id"], end_reason="run_termination")
        episodes.append(active_episode)
    for e in episodes:
        e["duration_sim_s"] = e["end_sim_s"]-e["start_sim_s"]
        e["duration_wall_s"] = (e["end_host_ns"]-e["start_host_ns"])/1e9
        e["received_fresh_ids"] = [r["id"] for r in received if e["start_host_ns"] <= r["received_monotonic_ns"] < e["end_host_ns"]]
        e["observed_frame_ids"] = [o["observation_id"] for o in observations if e["start_host_ns"] <= o["observation_monotonic_ns"] < e["end_host_ns"]]
        e["switched_fresh_ids"] = [v["id"] for v in events if e["start_sim_s"] <= v["application_sim_s"] < e["end_sim_s"]]
        actual = poses[e["start_tick"]:e["end_tick"]+1]
        e["stopped_pose_max_error"] = float(np.max(np.abs(actual-actual[0])))
        assert e["stopped_pose_max_error"] == 0.
    table(out/"stop_episodes.csv", episodes)
    static_eval = summary["obstacle_evaluation"]
    dynamic_eval = summary["dynamic_obstacle"]["evaluation"] if spawn else None
    safe = bool(spawn and static_eval["safety_margin_met"] and static_eval["corridor_containment_certified"]
                and dynamic_eval["safety_margin_met"] and dynamic_eval["corridor_containment_certified"])
    category = ("INCONCLUSIVE" if not spawn else "SAFETY_FAILURE" if not safe else
                "SAFE_GOAL_SUCCESS" if summary["goal_entry"] else
                "SAFE_BUT_STUCK" if gates[-1]["blocked"] else "INCONCLUSIVE")
    baseline = json.loads((run.parent/"topomap_sudden_01/summary.json").read_text())
    preserved = 0
    for source, root in [(run.parent/"topomap_sudden_preservation_01.json", Path("/")),
                         (run.parent/"topomap_sudden_01_validation/input_hashes.json", run.parent/"topomap_sudden_01")]:
        for name, digest in json.loads(source.read_text()).items():
            assert sha256_file(root/name) == digest
            preserved += 1
    result = {"classification": category, "run": str(run), "execution_git_sha": provenance["git_sha"],
        "clean_execution": True, "navigation": {k: summary[k] for k in
            ("goal_entry", "termination_reason", "simulation_duration_s", "minimum_goal_distance_m", "final_pose",
             "distance_travelled_m", "inference_count", "received_count", "applied_waypoints", "waypoint_timeout_episodes")},
        "placement": {"status": decision["status"] if decision else None, "spawn": spawn},
        "safety": {"static": static_eval, "dynamic": dynamic_eval, "all_actual_margins_met": safe},
        "stop": {"active_checks": sum(g["active"] for g in gates), "blocked_ticks": sum(g["blocked"] for g in gates),
            "first_active_tick": first_active["tick"] if first_active else None, "episodes": episodes,
            "total_sim_s": sum(e["duration_sim_s"] for e in episodes),
            "total_wall_s": sum(e["duration_wall_s"] for e in episodes),
            "resume_count": sum(e["resumed_motion"] for e in episodes),
            "fresh_received_during_stop": sum(len(e["received_fresh_ids"]) for e in episodes),
            "frames_captured_during_stop": sum(len(e["observed_frame_ids"]) for e in episodes),
            "already_violated_current_margin_ticks": [g["tick"] for g in gates if g["active"] and g["prediction"]["current_margin_already_violated"]],
            "evaluation_wall_ms": stats([g["evaluation_wall_ms"] for g in gates if g["active"]])},
        "timing": {key: runtime[key] for key in ("async_reproduction", "warm_inference_ms", "pacing", "timeout", "busy_observation_skips",
                                                "missed_capture_slots", "terminal_unapplied_requests")},
        "validation": {"status": "PASS", "map": map_check, "prior_hashes_preserved": preserved,
            "pose_max_abs_error": runtime["validation"]["max_pose_integration_error"], "clearance_max_abs_error": max_clearance_error,
            "gate_prediction_max_abs_error": max_prediction_error, "topomap_selection_and_worker_history": "PASS",
            "original_nominal_PD_and_actual_override_link": "PASS", "placement_and_render_geometry": "PASS",
            "first_visible_observation_id": visible[0]["observation_id"] if visible else None,
            "first_visible_sim_s": visible[0]["observation_sim_s"] if visible else None},
        "baseline": {key: baseline[key] for key in ("goal_entry", "termination_reason", "simulation_duration_s", "minimum_goal_distance_m", "final_pose")},
        "baseline_dynamic_center_xy_m": baseline["dynamic_obstacle"]["spawn"]["obstacle"]["center_xy_m"],
        "baseline_dynamic_min_clearance_m": baseline["dynamic_obstacle"]["evaluation"]["minimum_swept_clearance_lower_m"],
        "limitations": ["Exact-geometry oracle; not camera-based safety perception", "SE(2) kinematic RGB closed loop, not PhysX/real robot",
                       "One run, no retry; changed RGB/seed association/adaptive placement make baseline comparison nonpaired",
                       "No recovery, reranking, Graph or modified nominal PD; safe short rollout does not guarantee future progress"]}
    write_json(out/"summary.json", result)
    files = [p for p in run.rglob("*") if p.is_file() and p.suffix in (".json", ".jsonl", ".npz", ".png", ".csv", ".usda")
             and p.parent.name in (run.name, "dynamic", "model", "raw", "derived", "observations")]
    write_json(out/"input_hashes.json", {str(p.relative_to(run)): sha256_file(p) for p in files})
    plot(config, poses, box, episodes, result, out)
    print(json.dumps({k: result[k] for k in ("classification", "navigation")}))
    return result


def plot(config, poses, box, episodes, result, out):
    """One XY figure, same geometry/footprint conventions as existing recorded-run plots."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none", "svg.hashsalt": "oracle-stop"})
    fig, ax = plt.subplots(figsize=(10, 5))
    for b in configured_obstacles(config)+([box] if box else []):
        low, high = obstacle_bounds(single_obstacle_config(config, b))
        dynamic = b["id"] == "DynamicObstacle"
        ax.add_patch(Rectangle(low, *(high-low), fc="#ce8abf" if dynamic else "#a8cf9d", ec="#555555", alpha=.8))
        ax.text(*b["center_xy_m"], "Dynamic" if dynamic else b["id"].replace("StaticObstacle", "O"), ha="center", va="center", fontsize=9)
    for y in (-1.5, 1.5):
        ax.axhline(y, color="#555555")
        ax.axhline(y-np.sign(y)*.09, color="#777777", ls="--", lw=.7)
    ax.plot(*poses[:,:2].T, color="#215dac", lw=2, label="Actual executed center path")
    ax.scatter(*poses[0,:2], c="black", label="Start", zorder=5)
    ax.scatter(*poses[-1,:2], marker="x", c="#cc3344", label="Final pose", zorder=6)
    ax.add_patch(Circle(poses[-1,:2], .09, fill=False, ec="#cc3344"))
    goal = config["goal_pose"][:2]
    ax.add_patch(Circle(goal, .3, fc="#f5deb1", alpha=.5))
    ax.scatter(*goal, marker="*", s=140, c="#b47b0c", label="Goal / 0.30 m tolerance")
    for i, e in enumerate(episodes):
        ax.scatter(*e["pose"][:2], marker="s", s=45, facecolors="white", edgecolors="#d45a00", zorder=7,
                   label="Safety Stop positions" if i == 0 else None)
    ax.set(xlim=(-.3,4.9), ylim=(-1.65,1.65), xlabel="World X (m)", ylabel="World Y (m)")
    ax.set_aspect("equal"); ax.grid(alpha=.15)
    ax.set_title(f"Topomap + Oracle Safety Stop | {result['classification']}\n"
                 f"End {result['navigation']['simulation_duration_s']:.3f} s | "
                 f"Stopped {result['stop']['total_sim_s']:.3f} s | Resumes {result['stop']['resume_count']}")
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out/"navigation_xy.svg", metadata={"Date": None})
    svg = out/"navigation_xy.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    fig.savefig(out/"navigation_xy.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report(args.run.resolve(), args.out.resolve())
