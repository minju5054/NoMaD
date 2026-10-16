"""Offline applied-handoff audit; no Isaac, model, checkpoint, or GPU imports."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from .common import ROOT, integrate_se2, local_to_world, original_controller, sha256_file, write_json
from .clearance import (configured_obstacles, obstacle_bounds, single_obstacle_config,
                        swept_clearance, corridor_clearance)
from .async_report import wrapped
from .handoff_audit import (read_jsonl, correspondence, boundary_entries, path_safety,
                            classify, distribution)

PROTOCOL = Path(__file__).with_name("async_handoff_protocol.json")
CLASSES = ["ALREADY_CONSISTENT", "STAGING_SUFFICIENT", "UNSAFE_FRESH",
           "POTENTIAL_RECONCILIATION_CASE", "INSUFFICIENT_EVIDENCE"]
SPATIAL = ["progress_spatial_rmse_m", "progress_longitudinal_rms_m", "progress_lateral_rms_m",
           "progress_heading_rms_deg", "progress_heading_max_abs_deg", "station_lateral_rms_m",
           "common_forward_overlap_m"]
METRICS = SPATIAL + ["boundary_entry_distance_m", "boundary_tangent_deg", "boundary_connector_deg",
    "connector_tangent_deg", "chosen_entry_distance_m", "connector_clearance_m", "connector_corridor_m",
    "observation_to_switch_wall_s", "observation_to_ready_wall_s", "observation_pose_to_switch_sim_s",
    "observation_pose_to_switch_distance_m", "old_pose_to_switch_distance_m", "old_pose_to_switch_abs_yaw_deg",
    "capture_to_switch_whole_tick_old_distance_m", "inference_whole_tick_old_distance_m",
    "switch_translation_m", "switch_abs_yaw_deg", "pose_age_at_capture_start_s",
    "delta_selected_local_m", "delta_selected_anchored_world_m", "delta_v_abs_m_s", "delta_w_abs_rad_s",
    "old_full_clearance_m", "fresh_full_clearance_m", "old_prefix_clearance_m", "fresh_prefix_clearance_m",
    "applied_interval_clearance_m", "applied_interval_corridor_m", "controller_point_anchor_offset_m",
    "old_origin_prefix_clearance_m", "fresh_origin_prefix_clearance_m",
    "old_origin_full_clearance_m", "fresh_origin_full_clearance_m",
    "fresh_native_full_StaticObstacle2_clearance_m", "fresh_native_prefix_StaticObstacle2_clearance_m",
    "applied_interval_StaticObstacle2_clearance_m"]


def applied_pairs(events, received):
    """Pair actual applications, never infer application from request IDs."""
    assert events and len({e["id"] for e in events}) == len(events)
    assert all(b["application_monotonic_ns"] > a["application_monotonic_ns"]
               for a, b in zip(events[:-1], events[1:]))
    applied = {e["id"] for e in events}
    assert applied <= {r["id"] for r in received}
    return list(zip(events[:-1], events[1:])), [r for r in received if r["id"] not in applied]


def motion(trace, start, end, waypoint_id=None, host_window=None):
    """Sum saved incoming integration intervals, optionally only complete host ticks."""
    indices = np.arange(start + 1, end + 1, dtype=int)
    if waypoint_id is not None:
        indices = indices[(trace["id"][indices] == waypoint_id) & trace["valid"][indices]]
    if host_window is not None:
        lo, hi = host_window
        indices = indices[(trace["wall"][indices-1] >= lo) & (trace["wall"][indices] <= hi)]
    yaw = wrapped(trace["pose"][indices, 2] - trace["pose"][indices-1, 2])
    return {"interval_count": len(indices),
            "distance_m": float(np.sum(np.abs(trace["command"][indices, 0])*trace["dt"])),
            "signed_yaw_rad": float(np.sum(yaw)), "abs_net_yaw_rad": abs(float(np.sum(yaw))),
            "absolute_turn_rad": float(np.sum(np.abs(yaw)))}


def selected_point_semantics(local_point, observation_pose, boundary):
    anchored = local_to_world(np.array([local_point]), observation_pose)[0]
    controller_world = local_to_world(np.array([local_point]), boundary)[0]
    c, s = np.cos(boundary[2]), np.sin(boundary[2])
    anchored_at_b = (anchored-boundary[:2]) @ np.array([[c, -s], [s, c]])
    residual_local = np.asarray(local_point)-anchored_at_b
    np.testing.assert_allclose(np.linalg.norm(residual_local), np.linalg.norm(controller_world-anchored), atol=1e-12)
    return {"anchored_world_point_m": anchored.tolist(), "original_controller_local_point_m": list(local_point),
            "controller_local_point_expressed_at_B_world_m": controller_world.tolist(),
            "anchored_point_expressed_in_B_local_m": anchored_at_b.tolist(),
            "controller_minus_anchored_in_B_local_m": residual_local.tolist(),
            "offset_m": float(np.linalg.norm(residual_local))}


def group(rows):
    counts = Counter(r["class"] for r in rows)
    return {"count": len(rows), "classes": {k: counts[k] for k in CLASSES},
            "valid_correspondence": sum(r["correspondence_valid"] for r in rows),
            "metrics": {key: distribution([r.get(key) for r in rows
                           if key not in SPATIAL or r["correspondence_valid"]]) for key in METRICS}}


def draw_candidates(candidates, config, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    fig, axes = plt.subplots(1, len(candidates), figsize=(6*len(candidates), 5), squeeze=False)
    for ax, d in zip(axes[0], candidates):
        for box in configured_obstacles(config):
            lo, hi = obstacle_bounds(single_obstacle_config(config, box))
            ax.add_patch(Rectangle(lo, *(hi-lo), color="green", alpha=.25))
        for name, color in [("old", "#d97706"), ("fresh", "#2563eb")]:
            p = np.array(d[name+"_world_xy_m"]); o = np.array(d[name+"_observation_pose"])
            ax.plot(*p.T, "o-", color=color, label=name.upper())
            ax.scatter(*o[:2], marker="s", color=color, label=name+" observation")
            ax.arrow(*o[:2], .08*np.cos(o[2]), .08*np.sin(o[2]), color=color, head_width=.015)
        b = np.array(d["boundary_pose"]); entry = d["entry"]["chosen"]["xy_m"]
        ax.add_patch(Circle(b[:2], config["agent_radius_m"], fill=False, color="black"))
        ax.scatter(*b[:2], marker="x", color="black", label="B / switch")
        ax.plot(*np.vstack([b[:2], entry]).T, "r--", label="offline connector")
        ax.scatter(*entry, marker="*", color="red", label="entry")
        ax.set(title=f"OLD {d['old_id']} / FRESH {d['fresh_id']}", xlabel="world x (m)", ylabel="world y (m)")
        ax.axis("equal"); ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def run_audit(run, output):
    protocol = json.loads(PROTOCOL.read_text())
    assert run.name == protocol["source_run"]
    output.mkdir(parents=True, exist_ok=False)
    prior_dir = ROOT/"research/results/isaac6_async_wide_wall_20261016"
    prior_hashes = json.loads((prior_dir/"input_hashes.json").read_text())
    prior_report = json.loads((prior_dir/"summary.json").read_text())
    for name in ["input_hashes.json", "summary.json", "review.json"]:
        recorded = subprocess.check_output(["git", "show", f"{protocol['base_commit']}:{(prior_dir/name).relative_to(ROOT)}"], cwd=ROOT)
        assert hashlib.sha256(recorded).hexdigest() == sha256_file(prior_dir/name)
    assert all(sha256_file(run/name) == expected for name, expected in prior_hashes.items())
    names = sorted(set(prior_hashes) | {"clearance.jsonl", "obstacle_geometry.json"})
    hashes = {name: sha256_file(run/name) for name in names}
    provenance = json.loads((run/"provenance.json").read_text())
    assert provenance["git_status"] == "" and provenance["asynchronous"]
    source_hashes = {}
    for name in list(provenance["source_sha256"]) + ["deployment/src/pd_controller.py"]:
        source = subprocess.check_output(["git", "show", f"{provenance['git_sha']}:{name}"], cwd=ROOT)
        expected = hashlib.sha256(source).hexdigest()
        assert expected == sha256_file(ROOT/name)
        if name in provenance["source_sha256"]:
            assert expected == provenance["source_sha256"][name]
        source_hashes[name] = expected
    config = json.loads((run/"scenario.json").read_text())
    raw_summary = json.loads((run/"summary.json").read_text())
    expected_config = json.loads((ROOT/"research/nomad_isaac/two_obstacles_wide_wall_scenario.json").read_text())
    assert config == {**expected_config, "synchronous": False}
    assert raw_summary["goal_entry"] and raw_summary["obstacle_evaluation"]["avoidance_success"]
    events, received, requests, control, plans, inference, clearance = [read_jsonl(run/name) for name in
        ["events.jsonl", "received.jsonl", "requests.jsonl", "controller.jsonl", "planning.jsonl", "model/inference.jsonl", "clearance.jsonl"]]
    pairs, unapplied = applied_pairs(events, received)
    by_id = {r["id"]: r for r in received}; plan_by_id = {p["id"]: p for p in plans}
    assert [r["id"] for r in requests] == [r["id"] for r in received] == list(range(len(received)))
    assert len(received) == len(plans) == len(inference) == prior_report["requests"]
    assert len(events) == prior_report["switches"]
    with (run/"agent_trajectory.csv").open() as stream:
        trace_rows = list(csv.DictReader(stream))
    hz = config["integration_hz"]; dt = 1/hz
    trace = {"pose": np.array([[float(r[k]) for k in ["x_m", "y_m", "yaw_rad"]] for r in trace_rows]),
             "command": np.array([[float(r[k]) for k in ["v_m_s", "w_rad_s"]] for r in trace_rows]),
             "wall": np.array([int(r["monotonic_ns"]) for r in trace_rows], dtype=np.int64),
             "id": np.array([int(r["incoming_waypoint_id"]) for r in trace_rows]),
             "valid": np.array([r["incoming_command_valid"] == "True" for r in trace_rows]), "dt": dt}
    sim = np.array([float(r["simulation_time_s"]) for r in trace_rows]); pose = trace["pose"]
    np.testing.assert_allclose(sim, np.arange(len(sim))/hz, atol=1e-12, rtol=0)
    assert np.all(np.diff(trace["wall"]) > 0) and len(clearance) == len(sim)
    def tick(seconds):
        i = round(seconds*hz)
        assert abs(sim[i]-seconds) < 1e-10
        return i
    controller = original_controller(); max_error = 0.; safety = [None]
    for i in range(1, len(sim)):
        v, w = trace["command"][i]
        max_error = max(max_error, float(np.max(np.abs(integrate_se2(pose[i-1], v, w, dt)-pose[i]))))
        c = control[(i-1)//(hz//config["controller_hz"])]
        np.testing.assert_allclose([v,w], [c["v_m_s"],c["w_rad_s"]], atol=1e-12, rtol=0)
        assert trace["id"][i] == c["waypoint_id"] and trace["valid"][i] == c["valid"]
        per_box = {}
        for box in configured_obstacles(config):
            lo, hi = obstacle_bounds(single_obstacle_config(config, box))
            bound = swept_clearance(pose[i-1], v, w, dt, lo, hi, config["agent_radius_m"])
            per_box[box["id"]] = bound["lower_m"]
            assert abs(bound["lower_m"]-clearance[i]["obstacles"][box["id"]]["lower_m"]) < 1e-10
        corridor = corridor_clearance(pose[i-1], pose[i], v, w, dt, config["corridor"], config["agent_radius_m"])
        assert abs(corridor-clearance[i]["corridor_lower_m"]) < 1e-10
        safety.append({"obstacles": per_box, "corridor": corridor})
    assert max_error < 1e-10
    for c in control:
        expected = controller(by_id[c["waypoint_id"]]["selected_waypoint_m"]) if c["valid"] else [0.,0.]
        np.testing.assert_allclose(expected, [c["v_m_s"],c["w_rad_s"]], atol=1e-12, rtol=0)
        if c["latest_received_id"] >= 0:
            assert c["valid"] == ((c["monotonic_ns"]-by_id[c["latest_received_id"]]["received_monotonic_ns"])/1e9 < 1.)
    worlds, local, paths = {}, {}, {}
    for kind in ["raw", "derived"]:
        assert sorted(p.name for p in (run/"model"/kind).glob("*.npz")) == [f"{i:04d}.npz" for i in by_id]
    for request, record in zip(requests, received):
        j = record["id"]; obs_tick = tick(record["observation_sim_s"])
        assert all(record[key] == value for key, value in request.items())
        assert record["seed"] == config["seed"]+2*j and record["ddpm_seed"] == record["seed"]+1
        np.testing.assert_allclose(pose[obs_tick], record["observation_pose"], atol=1e-12, rtol=0)
        assert trace["wall"][obs_tick] == record["pose_sample_monotonic_ns"]
        chain = [record[k] for k in ["pose_sample_monotonic_ns", "observation_monotonic_ns", "inference_start_monotonic_ns",
                                    "inference_end_monotonic_ns", "ready_monotonic_ns", "received_monotonic_ns"]]
        assert np.all(np.diff(np.array(chain, dtype=np.int64)) >= 0)
        assert record["ready_monotonic_ns"] == record["inference_end_monotonic_ns"]
        with np.load(run/f"model/raw/{j:04d}.npz", allow_pickle=False) as raw, np.load(run/f"model/derived/{j:04d}.npz", allow_pickle=False) as derived:
            z, metric = raw["normalized_diffusion"], derived["metric"]
            assert z.shape == metric.shape == (8,8,2) and z.dtype == metric.dtype == np.float32
            assert all(np.isfinite(d[k]).all() for d in [raw, derived] for k in d.files)
            cum = np.cumsum(((z+1)/2)*np.array([7.5,8.])+np.array([-2.5,-4.]), axis=1).astype(np.float32)
            np.testing.assert_array_equal(cum, derived["cumulative"])
            np.testing.assert_array_equal(cum*np.float32(.05), metric)
            np.testing.assert_array_equal(metric[0,2], record["selected_waypoint_m"])
            np.testing.assert_array_equal(metric[0,2], derived["selected_waypoint"])
            local[j] = metric[0].copy(); worlds[j] = local_to_world(local[j], pose[obs_tick])
        np.testing.assert_allclose(worlds[j], plan_by_id[j]["world_xy_m"], atol=1e-12, rtol=0)
        origin = np.vstack([pose[obs_tick,:2], worlds[j]])
        paths[j] = {"native_full": path_safety(worlds[j], config), "native_prefix": path_safety(worlds[j][:3], config),
                    "origin_full": path_safety(origin, config), "origin_prefix": path_safety(origin[:4], config)}
        for box in configured_obstacles(config):
            saved = plan_by_id[j]["obstacles"][box["id"]]
            for name, key in [("origin_full", "polyline_clearance_m"), ("origin_prefix", "through_selected_index_2_clearance_m")]:
                assert abs(paths[j][name]["obstacles"][box["id"]]-saved[key]) < 1e-12
    switches = {e["id"]: tick(e["application_sim_s"]) for e in events}
    for e in events:
        assert all(e[key] == value for key,value in by_id[e["id"]].items())
        np.testing.assert_allclose(pose[switches[e["id"]]], e["agent_pose_at_switch"], atol=1e-12, rtol=0)
        assert e["application_monotonic_ns"] >= e["received_monotonic_ns"]
        first_tick = next(c for c in control if c["monotonic_ns"] >= e["received_monotonic_ns"])
        assert first_tick["monotonic_ns"] == e["application_monotonic_ns"] and first_tick["waypoint_id"] == e["id"]
    assert np.all(pose[:switches[events[0]["id"]]+1] == config["start_pose"])
    rows, details = [], []
    for pair_number, (old_event, fresh_event) in enumerate(pairs):
        k, j = old_event["id"], fresh_event["id"]
        start = tick(fresh_event["observation_sim_s"]); switch = switches[j]
        end = switches[events[pair_number+2]["id"]] if pair_number+2 < len(events) else len(pose)-1
        boundary = pose[switch]; old, fresh = worlds[k], worlds[j]
        overlap = correspondence(old, fresh, boundary, protocol)
        entries = boundary_entries(fresh, boundary, config, protocol)
        label = classify(paths[j]["native_full"], overlap, entries, protocol)
        near, chosen = entries.get("nearest", {}), entries.get("chosen", {})
        obs_motion = motion(trace, start, switch); old_motion = motion(trace, start, switch, k)
        complete_motion = motion(trace, start, switch, k, (fresh_event["observation_monotonic_ns"], fresh_event["application_monotonic_ns"]))
        infer_motion = motion(trace, start, switch, k, (fresh_event["inference_start_monotonic_ns"], fresh_event["inference_end_monotonic_ns"]))
        sem = selected_point_semantics(local[j][2].tolist(), pose[start], boundary)
        actual = {"obstacles": {box["id"]: min(safety[i]["obstacles"][box["id"]] for i in range(switch+1,end+1))
                                 for box in configured_obstacles(config)},
                  "corridor_clearance_m": min(safety[i]["corridor"] for i in range(switch+1,end+1)),
                  "end_sim_s": float(sim[end]), "interval_count": end-switch}
        actual["clearance_m"] = min(actual["obstacles"].values())
        actual["safe"] = actual["clearance_m"] >= config["required_clearance_m"] and actual["corridor_clearance_m"] > 0
        assert np.all(trace["id"][switch+1:end+1] == j)
        before = next(c for c in reversed(control) if c["monotonic_ns"] < fresh_event["application_monotonic_ns"])
        assert before["waypoint_id"] == k
        record = {"old_id": k, "fresh_id": j, "class": label,
            "correspondence_valid": overlap["valid"], "correspondence_reason": overlap["reason"],
            **{key:value for key,value in overlap.items() if key not in ["valid", "reason"]},
            "old_observation_sim_s": old_event["observation_sim_s"], "fresh_observation_sim_s": fresh_event["observation_sim_s"],
            "t_obs_monotonic_ns": fresh_event["observation_monotonic_ns"], "t_ready_monotonic_ns": fresh_event["ready_monotonic_ns"],
            "t_switch_monotonic_ns": fresh_event["application_monotonic_ns"], "t_switch_sim_s": fresh_event["application_sim_s"],
            "observation_to_switch_wall_s": (fresh_event["application_monotonic_ns"]-fresh_event["observation_monotonic_ns"])/1e9,
            "observation_to_ready_wall_s": (fresh_event["ready_monotonic_ns"]-fresh_event["observation_monotonic_ns"])/1e9,
            "pose_age_at_capture_start_s": (fresh_event["observation_monotonic_ns"]-fresh_event["pose_sample_monotonic_ns"])/1e9,
            "observation_pose_to_switch_sim_s": float(sim[switch]-sim[start]),
            "observation_pose_to_switch_distance_m": obs_motion["distance_m"], "old_pose_to_switch_distance_m": old_motion["distance_m"],
            "old_pose_to_switch_abs_yaw_deg": float(np.degrees(old_motion["abs_net_yaw_rad"])),
            "old_pose_to_switch_signed_yaw_deg": float(np.degrees(old_motion["signed_yaw_rad"])),
            "old_pose_to_switch_absolute_turn_deg": float(np.degrees(old_motion["absolute_turn_rad"])),
            "capture_to_switch_whole_tick_old_distance_m": complete_motion["distance_m"],
            "inference_whole_tick_old_distance_m": infer_motion["distance_m"],
            "other_or_invalid_intervals_obs_to_switch": obs_motion["interval_count"]-old_motion["interval_count"],
            "switch_translation_m": float(np.linalg.norm(boundary[:2]-pose[start,:2])),
            "switch_abs_yaw_deg": abs(float(np.degrees(wrapped(boundary[2]-pose[start,2])))),
            "boundary_x_m": float(boundary[0]), "boundary_y_m": float(boundary[1]), "boundary_yaw_rad": float(boundary[2]),
            "boundary_entry_distance_m": near.get("distance_m"), "boundary_tangent_deg": near.get("boundary_tangent_deg"),
            "boundary_connector_deg": near.get("boundary_connector_deg"), "connector_tangent_deg": near.get("connector_tangent_deg"),
            "chosen_entry_distance_m": chosen.get("distance_m"), "connector_clearance_m": chosen.get("obstacle_clearance_m"),
            "connector_corridor_m": chosen.get("corridor_clearance_m"), "safe_entry_count": entries.get("safe_count",0),
            "entry_count": entries["candidate_count"], "nearest_connector_safe": near.get("safe"),
            "old_full_clearance_m": paths[k]["native_full"]["obstacle_clearance_m"],
            "fresh_full_clearance_m": paths[j]["native_full"]["obstacle_clearance_m"],
            "old_prefix_clearance_m": paths[k]["native_prefix"]["obstacle_clearance_m"],
            "fresh_prefix_clearance_m": paths[j]["native_prefix"]["obstacle_clearance_m"],
            "fresh_full_safe": paths[j]["native_full"]["safe"], "fresh_prefix_safe": paths[j]["native_prefix"]["safe"],
            "old_v_m_s": before["v_m_s"], "old_w_rad_s": before["w_rad_s"],
            "fresh_v_m_s": fresh_event["v_m_s"], "fresh_w_rad_s": fresh_event["w_rad_s"],
            "delta_v_abs_m_s": abs(fresh_event["v_m_s"]-before["v_m_s"]),
            "delta_w_abs_rad_s": abs(fresh_event["w_rad_s"]-before["w_rad_s"]),
            "delta_selected_local_m": float(np.linalg.norm(local[j][2]-local[k][2])),
            "delta_selected_anchored_world_m": float(np.linalg.norm(fresh[2]-old[2])),
            "controller_point_anchor_offset_m": sem["offset_m"],
            "applied_interval_end_sim_s": actual["end_sim_s"], "applied_interval_clearance_m": actual["clearance_m"],
            "applied_interval_corridor_m": actual["corridor_clearance_m"], "applied_interval_safe": actual["safe"]}
        for role, identifier in [("old",k),("fresh",j)]:
            for part, values in paths[identifier].items():
                record[f"{role}_{part}_clearance_m"] = values["obstacle_clearance_m"]
                record[f"{role}_{part}_corridor_m"] = values["corridor_clearance_m"]
                record[f"{role}_{part}_safe"] = values["safe"]
                for box_id, value in values["obstacles"].items():
                    record[f"{role}_{part}_{box_id}_clearance_m"] = value
        for box_id, value in actual["obstacles"].items():
            record[f"applied_interval_{box_id}_clearance_m"] = value
        rows.append(record)
        details.append({"old_id":k, "fresh_id":j, "class":label, "old_observation_pose":old_event["observation_pose"],
            "fresh_observation_pose":fresh_event["observation_pose"], "boundary_pose":boundary.tolist(),
            "old_world_xy_m":old.tolist(), "fresh_world_xy_m":fresh.tolist(), "overlap":overlap, "entry":entries,
            "old_paths":paths[k], "fresh_paths":paths[j], "observation_pose_to_switch_motion":obs_motion,
            "old_pose_to_switch_motion":old_motion, "capture_to_switch_complete_old_motion":complete_motion,
            "inference_complete_old_motion":infer_motion, "actual_executed_interval":actual, "selected_point_semantics":sem})
    counts = Counter(r["class"] for r in rows); classifiable = len(rows)-counts["INSUFFICIENT_EVIDENCE"]
    candidates = sorted((d for d in details if d["class"] == "POTENTIAL_RECONCILIATION_CASE"),
                        key=lambda d:(d["entry"]["best_connector_clearance_m"],d["fresh_id"]))[:protocol["maximum_candidates"]]
    verdict = "GEOMETRIC_CANDIDATE_FOUND" if candidates else ("NO_QUALIFIED_CANDIDATE"
        if rows and classifiable/len(rows)>=protocol["minimum_classifiable_fraction_for_negative_verdict"] else "INSUFFICIENT_EVIDENCE")
    windows = {}
    for box in configured_obstacles(config):
        lo,hi = obstacle_bounds(single_obstacle_config(config,box)); near,far=lo[0]-config["agent_radius_m"],hi[0]+config["agent_radius_m"]
        for phase in ["approach","pass","departure"]:
            width=protocol["obstacle_window_m"]
            subset=[r for r in rows if (near-width<=r["boundary_x_m"]<near if phase=="approach" else
                    near<=r["boundary_x_m"]<=far if phase=="pass" else far<r["boundary_x_m"]<=far+width)]
            windows[box["id"]+"_"+phase]={"fresh_ids":[r["fresh_id"] for r in subset],"expanded_near_far_x_m":[float(near),float(far)],**group(subset)}
    excluded=[{"id":r["id"],"reason":"received_without_switch", "observation_sim_s":r["observation_sim_s"],
               "t_obs_monotonic_ns":r["observation_monotonic_ns"],"t_ready_monotonic_ns":r["ready_monotonic_ns"],
               "t_received_monotonic_ns":r["received_monotonic_ns"],"t_switch":None} for r in unapplied]
    summary={"verdict":verdict,"source_run":str(run),"base_commit":protocol["base_commit"],"execution_commit":provenance["git_sha"],
        "analysis_git_sha":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "protocol_sha256":sha256_file(PROTOCOL),"source_sha256":sha256_file(Path(__file__)),
        "saved_predictions":len(received),"actual_switches":len(events),"initialization_ids":[events[0]["id"]],
        "actual_handoffs":len(rows),"unapplied_predictions":excluded,"classifiable_pairs":classifiable,
        "valid_correspondence_pairs":sum(r["correspondence_valid"] for r in rows),
        "invalid_correspondence_reasons":dict(Counter(r["correspondence_reason"] for r in rows if not r["correspondence_valid"])),
        "all_handoffs":group(rows),"obstacle_windows":windows,
        "safe_fresh_connection_problem_pairs":counts["POTENTIAL_RECONCILIATION_CASE"],
        "safe_fresh_nearest_connector_unsafe_count":sum(r["fresh_full_safe"] and r["nearest_connector_safe"] is False for r in rows),
        "fresh_full_unsafe_prefix_safe_count":sum(not r["fresh_full_safe"] and r["fresh_prefix_safe"] for r in rows),
        "fresh_full_unsafe_actual_execution_safe_count":sum(not r["fresh_full_safe"] and r["applied_interval_safe"] for r in rows),
        "actual_execution_unsafe_handoffs":[r["fresh_id"] for r in rows if not r["applied_interval_safe"]],
        "chosen_candidate_fresh_ids":[d["fresh_id"] for d in candidates],
        "baseline_goal_entry":raw_summary["goal_entry"],"baseline_obstacle_evaluation":raw_summary["obstacle_evaluation"],
        "new_navigation_count":0,"new_inference_count":0,"graph_implemented":False,"graph_necessity_demonstrated":False,
        "fixed_goal_adapter":True,"topomap_added":False,
        "limitations":["Different initial/DDPM seeds confound observation and sampling effects",
            "Station/arclength correspondence is an automatic spatial proxy, not physical/oracle matching",
            "Native yaw/timestamps absent; only sufficiently long segment tangents provide heading",
            "Rotation-straight-rotation connectors are unexecuted finite diagnostics, not the actual PD path",
            "One successful fixed-goal kinematic baseline; no controlled latency, graph performance or superiority test"]}
    assert all(sha256_file(run/name)==digest for name,digest in hashes.items())
    validation={"status":"PASS","historical_input_hashes_verified":len(prior_hashes),"all_inputs_unchanged":True,
        "input_count":len(hashes),"historical_source_hashes_verified":source_hashes,"raw_derived_predictions_checked":len(received),
        "max_pose_reintegration_error":max_error,"actual_controller_matches_official":True,
        "observation_world_anchor_and_planning_match":True,"actual_swept_clearance_recomputed":True,
        "checkpoint_not_loaded":True,"scenario_unchanged":True}
    fieldnames=list(dict.fromkeys(k for r in rows for k in r))
    with (output/"pairs.csv").open("x") as f:
        writer=csv.DictWriter(f,fieldnames=fieldnames);writer.writeheader();writer.writerows(rows)
    for name,value in [("summary",summary),("protocol",protocol),("validation",validation),("pair_details",details),
                       ("candidates",candidates),("unapplied_predictions",excluded)]:
        write_json(output/(name+".json"),value)
    write_json(output/"input_hashes.json",{"sha256":hashes,"historical_hash_names":list(prior_hashes),
               "new_hash_baseline_names":sorted(set(hashes)-set(prior_hashes))})
    if candidates:
        draw_candidates(candidates,config,output/"candidates.svg")
    return summary


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();result=run_audit(args.run.resolve(),args.output.resolve())
    print(json.dumps({k:result[k] for k in ["verdict","actual_handoffs","valid_correspondence_pairs","chosen_candidate_fresh_ids"]}))
