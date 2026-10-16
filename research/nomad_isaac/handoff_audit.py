"""Read-only audit of stored predictions; imports neither Isaac nor the model."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from .common import ROOT, integrate_se2, local_to_world, original_controller, sha256_file, write_json
from .clearance import (configured_obstacles, obstacle_bounds, planning_diagnostic,
                        segment_clearance, single_obstacle_config, swept_clearance,
                        corridor_clearance)

PROTOCOL = Path(__file__).with_name("handoff_protocol.json")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def angle(a, b):
    return float((a - b + np.pi) % (2 * np.pi) - np.pi)


def degrees(a, b):
    return abs(float(np.degrees(angle(a, b))))


def grid(length, step):
    return np.linspace(0, length, max(1, int(np.ceil(length / step))) + 1)


def arc_coordinates(points):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]


def interpolate(points, coordinates, values):
    """Exact polyline interpolation, with outgoing tangent at an interior vertex."""
    values = np.asarray(values)
    index = np.clip(np.searchsorted(coordinates, values, side="right") - 1, 0, len(points) - 2)
    span = coordinates[index + 1] - coordinates[index]
    fraction = np.divide(values - coordinates[index], span, out=np.zeros_like(values), where=span > 0)
    delta = points[index + 1] - points[index]
    return (points[index] + fraction[:, None] * delta,
            np.arctan2(delta[:, 1], delta[:, 0]), np.linalg.norm(delta, axis=1))


def rms(values):
    return float(np.sqrt(np.mean(np.square(values)))) if len(values) else None


def correspondence(old, fresh, boundary, protocol):
    """Station overlap and equal-distance registration, never equal-index matching."""
    e = np.array([np.cos(boundary[2]), np.sin(boundary[2])])
    n = np.array([-e[1], e[0]])
    stations = [(p - boundary[:2]) @ e for p in (old, fresh)]
    if any(np.any(np.diff(u) <= protocol["forward_monotonic_epsilon_m"]) for u in stations):
        return {"valid": False, "reason": "nonmonotone_forward_station"}
    lower = max(0., *(u[0] for u in stations))
    upper = min(u[-1] for u in stations)
    span = float(upper - lower)
    if span < protocol["minimum_common_forward_overlap_m"]:
        return {"valid": False, "reason": "short_common_overlap", "common_forward_overlap_m": span}
    queries = lower + grid(span, protocol["spatial_sampling_step_m"])
    a, ah, al = interpolate(old, stations[0], queries)
    b, bh, bl = interpolate(fresh, stations[1], queries)
    valid = (al >= protocol["minimum_heading_segment_m"]) & (bl >= protocol["minimum_heading_segment_m"])
    lateral = (b - a) @ n
    heading = np.degrees((bh - ah + np.pi) % (2 * np.pi) - np.pi)

    # Clip each original polyline to the common forward interval. Keep original
    # segment lengths for heading validity even if clipping makes an end tiny.
    starts, ends = [], []
    for p, u in zip((old, fresh), stations):
        s = arc_coordinates(p)
        starts.append(float(np.interp(lower, u, s)))
        ends.append(float(np.interp(upper, u, s)))
    length = min(end - start for start, end in zip(starts, ends))
    progress = grid(length, protocol["spatial_sampling_step_m"])
    ap, aph, apl = interpolate(old, arc_coordinates(old), starts[0] + progress)
    bp, bph, bpl = interpolate(fresh, arc_coordinates(fresh), starts[1] + progress)
    progress_valid = ((apl >= protocol["minimum_heading_segment_m"])
                      & (bpl >= protocol["minimum_heading_segment_m"]))
    residual = bp - ap
    tangent = np.column_stack([np.cos(aph), np.sin(aph)])
    normal = np.column_stack([-np.sin(aph), np.cos(aph)])
    longitudinal = np.sum(residual * tangent, axis=1)[progress_valid]
    cross_track = np.sum(residual * normal, axis=1)[progress_valid]
    progress_angle = np.degrees((bph - aph + np.pi) % (2*np.pi) - np.pi)[progress_valid]
    valid_fraction = min(float(valid.mean()), float(progress_valid.mean()))
    return {"valid": valid_fraction >= protocol["minimum_heading_valid_fraction"],
            "reason": "ok" if valid_fraction >= protocol["minimum_heading_valid_fraction"] else "short_segment_heading",
            "common_forward_overlap_m": span, "common_arclength_m": float(length),
            "station_samples": len(queries), "station_heading_invalid_samples": int((~valid).sum()),
            "progress_samples": len(progress), "progress_heading_invalid_samples": int((~progress_valid).sum()),
            "heading_valid_fraction": valid_fraction,
            "station_lateral_rms_m": rms(lateral),
            "station_lateral_max_abs_m": float(np.max(np.abs(lateral))),
            "station_heading_rms_deg": rms(heading[valid]),
            "progress_spatial_rmse_m": float(np.sqrt(np.mean(np.sum(residual**2, axis=1)))),
            "progress_longitudinal_rms_m": rms(longitudinal),
            "progress_lateral_rms_m": rms(cross_track),
            "progress_longitudinal_mean_m": float(longitudinal.mean()) if len(longitudinal) else None,
            "progress_lateral_mean_m": float(cross_track.mean()) if len(cross_track) else None,
            "progress_heading_rms_deg": rms(progress_angle),
            "progress_heading_max_abs_deg": float(np.max(np.abs(progress_angle))) if len(progress_angle) else None}


def path_safety(points, config):
    per_box = {}
    for box in configured_obstacles(config):
        lower, upper = obstacle_bounds(single_obstacle_config(config, box))
        per_box[box["id"]] = min(segment_clearance(a, b, lower, upper, config["agent_radius_m"])[0]
                                     for a, b in zip(points[:-1], points[1:]))
    c = config["corridor"]
    corridor = float(min(np.min(points[:, 0] - c["xmin"]), np.min(c["xmax"] - points[:, 0]),
                         np.min(c["half_width"] - np.abs(points[:, 1]))) - config["agent_radius_m"])
    minimum = min(per_box.values())
    return {"obstacle_clearance_m": float(minimum), "obstacles": per_box, "corridor_clearance_m": corridor,
            "safe": minimum >= config["required_clearance_m"] and corridor > 0}


def boundary_entries(fresh, boundary, config, protocol):
    candidates = []
    arclength = arc_coordinates(fresh)
    for i in range(protocol["entry_last_waypoint_index"]):
        a, b = fresh[i:i+2]
        d = b - a
        length = float(np.linalg.norm(d))
        if length < protocol["minimum_heading_segment_m"]:
            continue
        projected = float(np.clip(np.dot(boundary[:2] - a, d) / length**2, 0., 1.))
        fractions = sorted(set([projected, *(grid(length, protocol["spatial_sampling_step_m"]) / length)]))
        for f in fractions:
            entry = a + f*d
            tangent = float(np.arctan2(d[1], d[0]))
            distance = float(np.linalg.norm(entry-boundary[:2]))
            connector_heading = float(np.arctan2(*(entry-boundary[:2])[::-1])) if distance > 1e-9 else tangent
            safety = path_safety(np.vstack([boundary[:2], entry]), config)
            candidates.append({"xy_m": entry.tolist(), "segment_index": i,
                               "progress_m": float(arclength[i]+f*length), "distance_m": distance,
                               "tangent_rad": tangent, "boundary_tangent_deg": degrees(boundary[2], tangent),
                               "boundary_connector_deg": degrees(boundary[2], connector_heading),
                               "connector_tangent_deg": degrees(connector_heading, tangent), **safety})
    candidates.sort(key=lambda c: (c["distance_m"], c["progress_m"], c["segment_index"]))
    if not candidates:
        return {"valid": False, "reason": "no_valid_prefix_heading", "candidate_count": 0}
    safe = [c for c in candidates if c["safe"]]
    nearest, chosen = candidates[0], safe[0] if safe else candidates[0]
    return {"valid": True, "candidate_count": len(candidates), "safe_count": len(safe),
            "nearest": nearest, "chosen": chosen,
            "best_connector_clearance_m": max(c["obstacle_clearance_m"] for c in candidates),
            "invalid_prefix_segments": int(sum(np.linalg.norm(d) < protocol["minimum_heading_segment_m"]
                                               for d in np.diff(fresh[:3], axis=0)))}


def classify(fresh_safety, overlap, entries, protocol):
    if not fresh_safety["safe"]:
        return "UNSAFE_FRESH"
    if not overlap["valid"] or not entries["valid"]:
        return "INSUFFICIENT_EVIDENCE"
    near = entries["nearest"]
    if (near["safe"] and near["distance_m"] <= protocol["consistent_entry_distance_m"]
        and max(near[k] for k in ["boundary_tangent_deg", "boundary_connector_deg", "connector_tangent_deg"])
            <= protocol["consistent_angle_deg"]):
        return "ALREADY_CONSISTENT"
    return "STAGING_SUFFICIENT" if entries["safe_count"] else "POTENTIAL_RECONCILIATION_CASE"


def distribution(values):
    x = np.asarray([v for v in values if v is not None], dtype=float)
    if not len(x):
        return {"count": 0}
    return {"count": len(x), "min": float(x.min()), "median": float(np.median(x)),
            "p95": float(np.percentile(x, 95)), "max": float(x.max())}


def group_summary(rows):
    metrics = ["common_forward_overlap_m", "progress_spatial_rmse_m", "station_lateral_rms_m",
               "progress_longitudinal_rms_m", "progress_lateral_rms_m", "progress_heading_rms_deg",
               "boundary_entry_distance_m", "boundary_tangent_deg", "delta_selected_local_m",
               "delta_selected_world_m", "delta_v_abs_m_s", "delta_w_abs_rad_s",
               "old_clearance_m", "fresh_clearance_m", "connector_clearance_m",
               "observation_to_application_sim_s", "observation_to_application_distance_m",
               "inference_ms", "applied_interval_clearance_m"]
    return {"count": len(rows), "classes": dict(Counter(r["class"] for r in rows)),
            "metrics": {k: distribution([r.get(k) for r in rows]) for k in metrics}}


def run_audit(run, output, protocol_path=PROTOCOL):
    protocol = json.loads(protocol_path.read_text())
    output.mkdir(parents=True, exist_ok=False)
    config = json.loads((run / "scenario.json").read_text())
    events = read_jsonl(run / "events.jsonl")
    control = read_jsonl(run / "controller.jsonl")
    plans = read_jsonl(run / "planning.jsonl")
    worker = read_jsonl(run / "model/inference.jsonl")
    with (run / "agent_trajectory.csv").open() as f:
        poses = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]
    times = np.array([p["simulation_time_s"] for p in poses])
    pose_array = np.array([[p[k] for k in ["x_m", "y_m", "yaw_rad"]] for p in poses])
    goal_distances = np.linalg.norm(pose_array[:, :2] - config["goal_pose"][:2], axis=1)
    np.testing.assert_allclose(goal_distances, [p["goal_distance_m"] for p in poses], atol=1e-12, rtol=0)
    cutoff_index = int(np.argmin(goal_distances))
    cutoff = float(times[cutoff_index])
    eligible = [e for e in events if max(e["observation_sim_s"], e["application_sim_s"]) <= cutoff + 1e-9]
    assert [e["id"] for e in events] == list(range(len(events)))
    assert len(events) == len(plans) == len(worker)
    assert [e["id"] for e in eligible] == list(range(len(eligible)))
    for kind in ["raw", "derived"]:
        assert sorted(p.name for p in (run / "model" / kind).glob("*.npz")) == [f"{i:04d}.npz" for i in range(len(events))]

    input_paths = ["events.jsonl", "controller.jsonl", "agent_trajectory.csv", "planning.jsonl",
                   "scenario.json", "obstacle_geometry.json", "provenance.json", "model/environment.json", "model/inference.jsonl"]
    input_paths += [f"model/{kind}/{e['id']:04d}.npz" for e in eligible for kind in ["raw", "derived"]]
    hashes = {p: sha256_file(run / p) for p in input_paths}
    write_json(output / "input_hashes.json", {"source_run": str(run), "sha256_before_analysis": hashes,
               "npz_inventory_count_each": len(events),
               "note": "NPZ/events/controller/planning hashes are a new audit baseline, not independently recorded at execution."})
    provenance = json.loads((run / "provenance.json").read_text())
    source_checks = {}
    for name, expected in provenance["source_sha256"].items():
        historical = subprocess.check_output(["git", "show", f"{provenance['git_sha']}:{name}"], cwd=ROOT)
        assert hashlib.sha256(historical).hexdigest() == expected == sha256_file(ROOT / name), name
        source_checks[name] = expected
    previous = json.loads((ROOT / "research/results/isaac6_two_obstacles_20261016/video.json").read_text())
    historical_data = {}
    for name in ["agent_trajectory.csv", "scenario.json"]:
        expected = previous["manifest"]["source_sha256"][name]
        assert hashes[name] == expected
        historical_data[name] = expected
    assert provenance["git_status"] == "" and not provenance["prepare_only"]
    assert config == json.loads((ROOT / "research/nomad_isaac/two_obstacles_scenario.json").read_text())
    geometry = json.loads((run / "obstacle_geometry.json").read_text())
    for box, saved in zip(configured_obstacles(config), geometry["obstacles"]):
        lo, hi = obstacle_bounds(single_obstacle_config(config, box))
        np.testing.assert_allclose(lo, saved["aabb_min_xy_m"], atol=1e-12)
        np.testing.assert_allclose(hi, saved["aabb_max_xy_m"], atol=1e-12)
    write_json(output / "protocol.json", protocol)

    def pose_at(t):
        i = int(round(t * config["integration_hz"]))
        assert abs(times[i] - t) < 1e-9
        return pose_array[i].copy()

    # Controller CSV records the command that produced the incoming integration
    # interval; controller.jsonl gives the refreshed command for the next interval.
    max_integration_error = 0.
    for i in range(1, cutoff_index + 1):
        predicted = integrate_se2(pose_array[i-1], poses[i]["v_m_s"], poses[i]["w_rad_s"], times[i]-times[i-1])
        max_integration_error = max(max_integration_error, float(np.max(np.abs(predicted-pose_array[i]))))
    assert max_integration_error < 1e-10
    controller = original_controller()
    worlds, timing = {}, {}
    max_normalization_error = 0.
    for e in eligible:
        i = e["id"]
        for key, value in worker[i].items():
            assert e[key] == value
        assert e["received_sim_s"] == e["observation_sim_s"]
        assert (e["observation_monotonic_ns"] <= e["inference_start_monotonic_ns"] < e["inference_end_monotonic_ns"]
                <= e["received_monotonic_ns"] <= e["application_monotonic_ns"])
        observation = pose_at(e["observation_sim_s"])
        np.testing.assert_allclose(observation, e["observation_pose"], atol=1e-10, rtol=0)
        boundary = pose_at(e["application_sim_s"])
        np.testing.assert_allclose(np.diff(e["history_sim_s"]), .25, atol=1e-12, rtol=0)
        assert e["history_sim_s"][-1] == e["observation_sim_s"]
        assert e["seed"] == config["seed"] + 2*i and e["ddpm_seed"] == e["seed"]+1
        with np.load(run / f"model/raw/{i:04d}.npz", allow_pickle=False) as raw, \
             np.load(run / f"model/derived/{i:04d}.npz", allow_pickle=False) as derived:
            z, metric = raw["normalized_diffusion"], derived["metric"]
            assert z.shape == metric.shape == (8, 8, 2) and z.dtype == metric.dtype == np.float32
            assert all(np.isfinite(a[k]).all() for a in [raw, derived] for k in a.files)
            # NumPy expression preserves the original float32 -> float64 promotion.
            cumulative = np.cumsum(((z+1)/2) * np.array([7.5, 8.]) + np.array([-2.5, -4.]), axis=1).astype(np.float32)
            max_normalization_error = max(max_normalization_error, float(np.max(np.abs(cumulative-derived["cumulative"]))))
            np.testing.assert_array_equal(cumulative, derived["cumulative"])
            np.testing.assert_array_equal(cumulative*np.float32(.05), metric)
            np.testing.assert_array_equal(derived["selected_waypoint"], metric[0, 2])
            np.testing.assert_array_equal(metric[0, 2], e["selected_waypoint_m"])
            worlds[i] = local_to_world(metric[0], np.array(e["observation_pose"]))
            np.testing.assert_allclose(worlds[i], plans[i]["world_xy_m"], atol=1e-12, rtol=0)
            for box in configured_obstacles(config):
                recomputed = planning_diagnostic(metric[0], e["observation_pose"], single_obstacle_config(config, box))
                for key in ["polyline_clearance_m", "through_selected_index_2_clearance_m", "selected_point_clearance_m"]:
                    assert abs(recomputed[key] - plans[i]["obstacles"][box["id"]][key]) < 1e-12
        np.testing.assert_allclose(controller(e["selected_waypoint_m"]), [e["v_m_s"], e["w_rad_s"]], atol=1e-12, rtol=0)
        refreshes = [c for c in control if c["waypoint_id"] == i]
        assert refreshes and abs(refreshes[0]["simulation_time_s"]-e["application_sim_s"]) < 1e-9
        for c in refreshes:
            np.testing.assert_allclose([c["v_m_s"], c["w_rad_s"]], [e["v_m_s"], e["w_rad_s"]], atol=1e-12, rtol=0)
        delay = e["application_sim_s"]-e["received_sim_s"]
        assert -1e-9 <= delay < 1/config["controller_hz"]
        if i:
            previous_event = events[i-1]
            np.testing.assert_allclose(integrate_se2(observation, previous_event["v_m_s"], previous_event["w_rad_s"], delay),
                                       boundary, atol=1e-10, rtol=0)
        timing[i] = {"observation_to_application_sim_s": delay,
                     "observation_to_application_distance_m": float(np.linalg.norm(boundary[:2]-observation[:2])),
                     "observation_to_application_yaw_deg": degrees(boundary[2], observation[2]),
                     "inference_ms": e["inference_ms"], "inference_sim_elapsed_s": 0.}

    rows, details = [], []
    for old_event, fresh_event in zip(events[:-1], events[1:]):
        k, j = old_event["id"], fresh_event["id"]
        row = {"old_id": k, "fresh_id": j, "old_observation_sim_s": old_event["observation_sim_s"],
               "fresh_observation_sim_s": fresh_event["observation_sim_s"],
               "application_sim_s": fresh_event["application_sim_s"]}
        if j not in worlds:
            rows.append({**row, "primary": False, "class": "EXCLUDED_AFTER_PRIMARY_WINDOW"})
            continue
        old, fresh = worlds[k], worlds[j]
        boundary = pose_at(fresh_event["application_sim_s"])
        overlap = correspondence(old, fresh, boundary, protocol)
        entries = boundary_entries(fresh, boundary, config, protocol)
        old_safety, fresh_safety = path_safety(old, config), path_safety(fresh, config)
        label = classify(fresh_safety, overlap, entries, protocol)
        chosen = entries.get("chosen", {})
        # Actual constant PD command until the next recorded application, clipped
        # to the analysis horizon. This is not a hypothetical staging execution.
        end_time = min(events[j+1]["application_sim_s"] if j+1 < len(events) else cutoff, cutoff)
        duration = end_time - fresh_event["application_sim_s"]
        v, w = fresh_event["v_m_s"], fresh_event["w_rad_s"]
        expected_end = integrate_se2(boundary, v, w, duration)
        np.testing.assert_allclose(expected_end, pose_at(end_time), atol=1e-10, rtol=0)
        actual = {box["id"]: swept_clearance(boundary, v, w, duration,
                    *obstacle_bounds(single_obstacle_config(config, box)), config["agent_radius_m"])
                  for box in configured_obstacles(config)}
        actual_corridor = corridor_clearance(boundary, expected_end, v, w, duration,
                                             config["corridor"], config["agent_radius_m"])
        local_delta = np.array(fresh_event["selected_waypoint_m"])-old_event["selected_waypoint_m"]
        world_delta = fresh[2]-old[2]
        old_selected_at_B = local_to_world(np.array([old_event["selected_waypoint_m"]]), boundary)[0]
        fresh_selected_at_B = local_to_world(np.array([fresh_event["selected_waypoint_m"]]), boundary)[0]
        row.update({"primary": True, "class": label, "correspondence_valid": overlap["valid"],
                    "correspondence_reason": overlap["reason"], **{a:b for a,b in overlap.items() if a not in ["valid", "reason"]},
                    **timing[j], "boundary_x_m": float(boundary[0]), "boundary_y_m": float(boundary[1]),
                    "boundary_yaw_rad": float(boundary[2]), "boundary_entry_distance_m": chosen.get("distance_m"),
                    "boundary_tangent_deg": chosen.get("boundary_tangent_deg"),
                    "connector_clearance_m": chosen.get("obstacle_clearance_m"),
                    "safe_entry_count": entries.get("safe_count", 0), "entry_count": entries["candidate_count"],
                    "old_clearance_m": old_safety["obstacle_clearance_m"],
                    "fresh_clearance_m": fresh_safety["obstacle_clearance_m"],
                    "old_origin_inclusive_clearance_m": plans[k]["polyline_clearance_m"],
                    "fresh_origin_inclusive_clearance_m": plans[j]["polyline_clearance_m"],
                    "delta_selected_local_m": float(np.linalg.norm(local_delta)),
                    "delta_selected_world_m": float(np.linalg.norm(world_delta)),
                    "delta_v_abs_m_s": abs(v-old_event["v_m_s"]), "delta_w_abs_rad_s": abs(w-old_event["w_rad_s"]),
                    "old_v_m_s": old_event["v_m_s"], "old_w_rad_s": old_event["w_rad_s"],
                    "fresh_v_m_s": v, "fresh_w_rad_s": w,
                    "controller_world_target_offset_from_anchored_fresh_m": float(np.linalg.norm(fresh_selected_at_B-fresh[2])),
                    "applied_interval_end_sim_s": end_time,
                    "applied_interval_clearance_m": min(a["lower_m"] for a in actual.values()),
                    "applied_interval_corridor_clearance_m": actual_corridor})
        for box in configured_obstacles(config):
            box_id = box["id"]
            row[f"old_{box_id}_clearance_m"] = old_safety["obstacles"][box_id]
            row[f"fresh_{box_id}_clearance_m"] = fresh_safety["obstacles"][box_id]
        rows.append(row)
        details.append({"old_id": k, "fresh_id": j, "class": label, "boundary_pose": boundary.tolist(),
                        "old_observation_pose": old_event["observation_pose"], "fresh_observation_pose": fresh_event["observation_pose"],
                        "old_world_xy_m": old.tolist(), "fresh_world_xy_m": fresh.tolist(),
                        "old_selected_world_m": old[2].tolist(), "fresh_selected_world_m": fresh[2].tolist(),
                        "controller_old_local_point_expressed_at_B_m": old_selected_at_B.tolist(),
                        "controller_fresh_local_point_expressed_at_B_m": fresh_selected_at_B.tolist(),
                        "old_safety": old_safety, "fresh_safety": fresh_safety, "overlap": overlap, "entry": entries,
                        "actual_command_interval": {"end_sim_s": end_time, "obstacles": actual, "corridor_lower_m": actual_corridor}})
    primary = [r for r in rows if r["primary"]]
    counts = Counter(r["class"] for r in primary)
    classifiable = len(primary)-counts["INSUFFICIENT_EVIDENCE"]
    candidates = sorted((d for d in details if d["class"] == "POTENTIAL_RECONCILIATION_CASE"),
                        key=lambda d: (d["entry"]["best_connector_clearance_m"], d["fresh_id"]))[:protocol["maximum_candidates"]]
    verdict = ("GEOMETRIC_CANDIDATE_FOUND" if candidates else "NO_QUALIFIED_CANDIDATE"
               if primary and classifiable/len(primary) >= protocol["minimum_classifiable_fraction_for_negative_verdict"]
               else "INSUFFICIENT_EVIDENCE")
    windows = {}
    for box in configured_obstacles(config):
        lo, hi = obstacle_bounds(single_obstacle_config(config, box))
        near, far = lo[0]-config["agent_radius_m"], hi[0]+config["agent_radius_m"]
        width = protocol["obstacle_window_m"]
        for phase in ["approach", "pass", "departure"]:
            subset = [r for r in primary if (near-width <= r["boundary_x_m"] < near if phase == "approach" else
                      near <= r["boundary_x_m"] <= far if phase == "pass" else far < r["boundary_x_m"] <= far+width)]
            windows[f"{box['id']}_{phase}"] = {"near_far_expanded_x_m": [float(near), float(far)],
                "fresh_ids": [r["fresh_id"] for r in subset], **group_summary(subset)}
    summary = {"verdict": verdict, "source_run": str(run), "base_commit": protocol["base_commit"],
               "execution_commit": provenance["git_sha"], "protocol_sha256": sha256_file(protocol_path),
               "audit_source_sha256": sha256_file(Path(__file__)),
               "analysis_git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "python": sys.version, "numpy": np.__version__,
               "primary_end_sim_s": cutoff, "minimum_goal_distance_m": float(goal_distances[cutoff_index]),
               "saved_predictions": len(events), "total_successive_pairs": len(rows), "primary_pairs": len(primary),
               "excluded_after_primary_window": len(rows)-len(primary), "classifiable_pairs": classifiable,
               "insufficient_pairs": counts["INSUFFICIENT_EVIDENCE"],
               "valid_correspondence_pairs": sum(r["correspondence_valid"] for r in primary),
               "safe_fresh_with_connection_problem_pairs": counts["POTENTIAL_RECONCILIATION_CASE"],
               "chosen_candidate_fresh_ids": [d["fresh_id"] for d in candidates],
               "primary": group_summary(primary), "obstacle_windows": windows,
               "short_heading_segments_old_fresh": sum(int(np.sum(np.linalg.norm(np.diff(w, axis=0), axis=1)
                        < protocol["minimum_heading_segment_m"])) for w in worlds.values()),
               "timing_all_primary_predictions": {k: distribution([v[k] for v in timing.values()]) for k in next(iter(timing.values()))},
               "controller_world_target_offset_m": distribution([r["controller_world_target_offset_from_anchored_fresh_m"] for r in primary]),
               "new_inference_count": 0, "new_navigation_count": 0, "graph_implemented": False,
               "graph_necessity_demonstrated": False, "asynchronous_need_demonstrated": False,
               "limitations": ["Different initial and DDPM seeds confound observation and sampling effects",
                   "Station/arclength registration is automatic geometry, not physical or oracle correspondence",
                   "No intrinsic waypoint yaw or timestamp; headings are derived",
                   "Entry/rotation-straight-rotation connections are offline diagnostics, not executed controllers",
                   "Single synchronous run; finite early-entry family; no graph superiority or necessity proof"]}
    names = list(dict.fromkeys(k for r in rows for k in r))
    with (output / "pairs.csv").open("x") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader(); writer.writerows(rows)
    write_json(output / "summary.json", summary)
    # Full small numeric detail retained locally; only candidate details need Git.
    write_json(output / "pair_details.json", details)
    write_json(output / "candidates.json", candidates)
    validation = {"status": "PASS", "input_count": len(hashes), "input_hashes_unchanged": all(sha256_file(run/p) == v for p,v in hashes.items()),
                  "historical_data_hashes_verified": historical_data, "historical_source_hashes_verified": source_checks,
                  "historical_individual_prediction_hashes_available": False,
                  "prediction_raw_derived_checked": len(eligible), "normalization_max_abs_error": max_normalization_error,
                  "planning_world_and_clearance_match": True, "source_pose_and_controller_match": True,
                  "max_actual_pose_reintegration_error": max_integration_error,
                  "inference_sim_time_advance_s": 0., "checkpoint_provenance_only_not_reloaded": True}
    assert validation["input_hashes_unchanged"]
    write_json(output / "validation.json", validation)
    if candidates:
        plot_candidates(candidates, config, output / "candidates.svg")
    return summary


def plot_candidates(candidates, config, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    fig, axes = plt.subplots(1, len(candidates), figsize=(6*len(candidates), 5), squeeze=False)
    for ax, d in zip(axes[0], candidates):
        for box in configured_obstacles(config):
            lo, hi = obstacle_bounds(single_obstacle_config(config, box))
            ax.add_patch(Rectangle(lo, *(hi-lo), facecolor="green", alpha=.3))
        for key, color in [("old_world_xy_m", "#d97706"), ("fresh_world_xy_m", "#2563eb")]:
            p = np.asarray(d[key]); ax.plot(*p.T, "o-", color=color, label=key.split("_")[0].upper())
        b = np.array(d["boundary_pose"]); e = np.array(d["entry"]["chosen"]["xy_m"])
        ax.add_patch(Circle(b[:2], config["agent_radius_m"], fill=False, color="black"))
        ax.scatter(*b[:2], marker="x", color="black", label="B")
        ax.arrow(*b[:2], .1*np.cos(b[2]), .1*np.sin(b[2]), head_width=.02, color="black")
        ax.plot(*np.vstack([b[:2], e]).T, "r--", label="diagnostic connector")
        ax.scatter(*e, marker="*", color="red", label="entry")
        ax.set(title=f"OLD {d['old_id']} / FRESH {d['fresh_id']}", xlabel="world x (m)", ylabel="world y (m)")
        ax.axis("equal"); ax.grid(alpha=.2); ax.legend()
    fig.tight_layout(); fig.savefig(destination); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = run_audit(args.run.resolve(), args.output.resolve())
    print(json.dumps({k: summary[k] for k in ["verdict", "primary_pairs", "classifiable_pairs", "chosen_candidate_fresh_ids"]}))


if __name__ == "__main__":
    main()
