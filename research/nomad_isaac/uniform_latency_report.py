"""Audit every actual handoff, including unsuccessful and terminal-pending runs."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from .common import ROOT, local_to_world, sha256_file, write_json
from .async_report import rows, stats, validate
from .async_handoff_audit import applied_pairs, motion, selected_point_semantics
from .handoff_audit import correspondence, boundary_entries, path_safety, classify
from .clearance import corridor_clearance, configured_obstacles

CLASSES = ["OLD_EXECUTION_RISK", "UNSAFE_FRESH", "ALREADY_CONSISTENT", "STAGING_SUFFICIENT",
           "POTENTIAL_RECONCILIATION_CASE", "INSUFFICIENT_EVIDENCE"]
PROTOCOL = Path(__file__).with_name("uniform_latency_protocol.json")


def csv_file(path, records):
    with path.open("x") as stream:
        if records:
            keys = list(dict.fromkeys(k for r in records for k in r))
            writer = csv.DictWriter(stream, fieldnames=keys, lineterminator="\n")
            writer.writeheader(); writer.writerows(records)


def combined_class(geometric, old_safety):
    return "OLD_EXECUTION_RISK" if old_safety.get("safe") is False else geometric


def old_window_indices(wall, incoming_id, identifier, start_ns, end_ns):
    """Conservatively intersect physical intervals; never include incoming FRESH."""
    i = np.arange(1, len(wall))
    return i[(wall[i-1] < end_ns) & (wall[i] > start_ns) & (incoming_id[i] >= 0) & (incoming_id[i] < identifier)]


def analyze(condition, run, baseline, output):
    output.mkdir(parents=True, exist_ok=False)
    protocol = json.loads(PROTOCOL.read_text())
    geometric = json.loads(Path(__file__).with_name("async_handoff_protocol.json").read_text())
    delay = protocol["conditions_delay_s"][condition]
    if not (run/"summary.json").exists():
        report = {"condition": condition, "source_run": str(run), "execution_status": "TECHNICAL_EXECUTION_FAILURE",
                  "verdict": "INSUFFICIENT_EVIDENCE", "configured_delay_s": delay}
        write_json(output/"summary.json", report)
        return report
    raw = json.loads((run/"summary.json").read_text()); config = raw["scenario"]
    assert config == json.loads((baseline/"scenario.json").read_text())
    provenance = json.loads((run/"provenance.json").read_text())
    assert provenance["git_status"] == ""
    for name, digest in provenance["source_sha256"].items():
        source = subprocess.check_output(["git", "show", f"{provenance['git_sha']}:{name}"], cwd=ROOT)
        assert hashlib.sha256(source).hexdigest() == digest
    if condition != "D0":
        assert provenance["uniform_delivery_delay_s"] == delay
        policy = json.loads((run/"delivery_delay_protocol.json").read_text())
        assert policy == {**protocol, "mode": "uniform", "configured_additional_s": delay}
    preserved = json.loads((baseline.parent/"uniform_latency_preservation_01.json").read_text())
    assert all(sha256_file(baseline.parent/r/n) == h for r, files in preserved.items() for n, h in files.items())
    paths = sorted(p for p in run.iterdir() if p.suffix in (".json", ".jsonl", ".csv", ".png", ".usd", ".usda"))
    paths += sorted((run/"model").glob("*.json*")) + sorted((run/"model/raw").glob("*.npz")) + sorted((run/"model/derived").glob("*.npz"))
    hashes = {str(p.relative_to(run)): sha256_file(p) for p in paths}
    environment = json.loads((run/"model/environment.json").read_text())
    assert environment["checkpoint_sha256"] == json.loads((baseline/"model/environment.json").read_text())["checkpoint_sha256"]
    runtime = validate(run, baseline.parent/"two_obstacles_01", output/"runtime_validation")
    received, events, control, clearance = (rows(run/name) for name in
        ("received.jsonl", "events.jsonl", "controller.jsonl", "clearance.jsonl"))
    pairs, unapplied = applied_pairs(events, received)
    with (run/"agent_trajectory.csv").open() as stream: records = list(csv.DictReader(stream))
    pose = np.array([[float(r[k]) for k in ("x_m", "y_m", "yaw_rad")] for r in records])
    wall = np.array([int(r["monotonic_ns"]) for r in records], dtype=np.int64)
    sim = np.array([float(r["simulation_time_s"]) for r in records])
    trace = {"pose": pose, "wall": wall, "dt": 1/config["integration_hz"],
             "command": np.array([[float(r[k]) for k in ("v_m_s", "w_rad_s")] for r in records]),
             "id": np.array([int(r["incoming_waypoint_id"]) for r in records]),
             "valid": np.array([r["incoming_command_valid"] == "True" for r in records])}
    assert len(clearance) == len(pose)
    for i in range(1, len(pose)):
        gap = corridor_clearance(pose[i-1], pose[i], *trace["command"][i], trace["dt"], config["corridor"], config["agent_radius_m"])
        assert abs(gap-clearance[i]["corridor_lower_m"]) < 1e-10
    def tick(seconds):
        i = round(seconds*config["integration_hz"])
        assert abs(sim[i]-seconds) < 1e-10
        return i
    def safety(indices):
        if not len(indices): return {"safe": None, "interval_count": 0}
        per_box = {box["id"]: min(clearance[i]["obstacles"][box["id"]]["lower_m"] for i in indices)
                   for box in configured_obstacles(config)}
        minimum = min(per_box.values()); corridor = min(clearance[i]["corridor_lower_m"] for i in indices)
        violations = [int(i) for i in indices if clearance[i]["lower_m"] < config["required_clearance_m"] or clearance[i]["corridor_lower_m"] <= 0]
        witness = None
        if violations:
            i = violations[0]
            witness = {"end_tick": i, "start_sim_s": sim[i-1], "end_sim_s": sim[i], "start_pose": pose[i-1].tolist(),
                       "end_pose": pose[i].tolist(), "incoming_waypoint_id": int(trace["id"][i]),
                       "command": trace["command"][i].tolist(), "command_valid": bool(trace["valid"][i]),
                       "swept_lower_m": clearance[i]["lower_m"], "corridor_lower_m": clearance[i]["corridor_lower_m"]}
        return {"safe": minimum >= config["required_clearance_m"] and corridor > 0,
                "interval_count": len(indices), "obstacles": per_box, "minimum_clearance_m": minimum,
                "corridor_clearance_m": corridor, "first_unsafe_interval": witness,
                "incoming_ids": sorted(set(map(int, trace["id"][indices]))),
                "invalid_intervals": int(np.sum(~trace["valid"][indices]))}
    def old_motion(start, end, identifier, window=None):
        ids = sorted(set(int(v) for v in trace["id"][start+1:end+1] if 0 <= v < identifier))
        parts = [motion(trace, start, end, waypoint_id=i, host_window=window) for i in ids]
        result = {key: sum(p[key] for p in parts) for key in ("interval_count", "distance_m", "signed_yaw_rad", "absolute_turn_rad")}
        result["abs_net_yaw_rad"] = abs(result["signed_yaw_rad"])
        result["ids"] = ids
        return result

    worlds, local, path_checks, waiting = {}, {}, {}, {}
    by_event = {e["id"]: e for e in events}
    timing = []
    for r in received:
        j = r["id"]; start = tick(r["observation_sim_s"])
        release = r["received_monotonic_ns"]
        packet = r.get("packet_received_monotonic_ns", release)
        if condition != "D0":
            assert r["delivery_delay_mode"] == "uniform" and r["delivery_delay_triggered"]
            assert r["additional_delivery_delay_s"] == delay
            assert r["release_monotonic_ns"] == release >= r["release_deadline_monotonic_ns"]
            assert r["release_deadline_monotonic_ns"] == packet + round(delay*1e9)
            assert r["persistence_end_monotonic_ns"] <= packet
            pt = tick(r["packet_received_sim_s"])
            np.testing.assert_allclose(pose[pt], r["agent_pose_at_packet_receive"], atol=1e-12, rtol=0)
            assert wall[pt] == r["packet_pose_sample_monotonic_ns"]
        event = by_event.get(j)
        end = tick(event["application_sim_s"]) if event else len(pose)-1
        old_idx = old_window_indices(wall, trace["id"], j, r["observation_monotonic_ns"], min(release, int(wall[-1])))
        pre_release = safety(old_idx)
        after_release_idx = old_window_indices(wall, trace["id"], j, release,
            event["application_monotonic_ns"] if event else int(wall[-1]))
        wait = old_motion(start, end, j)
        gpu = old_motion(start, end, j, (r["inference_start_monotonic_ns"], r["inference_end_monotonic_ns"]))
        hold = old_motion(start, end, j, (packet, release))
        waiting[j] = {"pre_release_old_safety": pre_release, "release_to_switch_old_safety": safety(after_release_idx),
                      "old_wait_motion": wait, "gpu_window_old_motion": gpu, "delivery_hold_old_motion": hold}
        with np.load(run/f"model/derived/{j:04d}.npz", allow_pickle=False) as data: local[j] = data["metric"][0].copy()
        worlds[j] = local_to_world(local[j], r["observation_pose"])
        origin = np.vstack([r["observation_pose"][:2], worlds[j]])
        path_checks[j] = {"native_full": path_safety(worlds[j], config), "native_prefix": path_safety(worlds[j][:3], config),
                          "origin_full": path_safety(origin, config), "origin_prefix": path_safety(origin[:4], config)}
        timing.append({"id": j, "applied": event is not None, "initialization": j == events[0]["id"],
            "t_obs_monotonic_ns": r["observation_monotonic_ns"], "t_ready_monotonic_ns": r["ready_monotonic_ns"],
            "t_packet_monotonic_ns": packet, "t_release_monotonic_ns": release,
            "t_switch_monotonic_ns": event["application_monotonic_ns"] if event else None,
            "inference_ms": r["inference_ms"], "packet_to_release_s": (release-packet)/1e9,
            "delivery_deadline_overshoot_s": (release-packet)/1e9-delay if condition != "D0" else None,
            "observation_to_ready_s": (r["ready_monotonic_ns"]-r["observation_monotonic_ns"])/1e9,
            "observation_to_release_s": (release-r["observation_monotonic_ns"])/1e9,
            "observation_to_switch_s": (event["application_monotonic_ns"]-r["observation_monotonic_ns"])/1e9 if event else None,
            "old_wait_distance_m": wait["distance_m"], "old_wait_signed_yaw_deg": float(np.degrees(wait["signed_yaw_rad"])),
            "old_wait_abs_yaw_deg": float(np.degrees(wait["abs_net_yaw_rad"])),
            "old_delivery_hold_distance_m": hold["distance_m"], "old_gpu_distance_m": gpu["distance_m"],
            "old_execution_risk": pre_release["safe"] is False})
    if condition != "D0": assert raw["delivery_delay"]["accepted_count"] == len(received) == len(timing)
    pair_rows, details = [], []
    for index, (old, fresh) in enumerate(pairs):
        k, j = old["id"], fresh["id"]
        start = tick(fresh["observation_sim_s"]); switch = tick(fresh["application_sim_s"])
        end = tick(events[index+2]["application_sim_s"]) if index+2 < len(events) else len(pose)-1
        b = pose[switch]
        overlap = correspondence(worlds[k], worlds[j], b, geometric)
        entry = boundary_entries(worlds[j], b, config, geometric)
        label = classify(path_checks[j]["native_full"], overlap, entry, geometric)
        combined = combined_class(label, waiting[j]["pre_release_old_safety"])
        execution = safety(np.arange(switch+1, end+1))
        assert np.all(trace["id"][switch+1:end+1] == j)
        sem = selected_point_semantics(local[j][2].tolist(), pose[start], b)
        before = next(c for c in reversed(control) if c["monotonic_ns"] < fresh["application_monotonic_ns"])
        near, chosen = entry.get("nearest", {}), entry.get("chosen", {})
        row = {"old_id": k, "fresh_id": j, "class": combined, "geometric_class": label,
            "correspondence_valid": overlap["valid"], "correspondence_reason": overlap["reason"],
            **{key: value for key, value in overlap.items() if key not in ("valid", "reason")},
            "t_obs_sim_s": fresh["observation_sim_s"], "t_switch_sim_s": fresh["application_sim_s"],
            "boundary_x_m": b[0], "boundary_y_m": b[1], "boundary_yaw_rad": b[2],
            "switch_translation_m": float(np.linalg.norm(b[:2]-pose[start,:2])),
            "switch_abs_yaw_deg": float(np.degrees(abs((b[2]-pose[start,2]+np.pi)%(2*np.pi)-np.pi))),
            "old_wait_distance_m": waiting[j]["old_wait_motion"]["distance_m"],
            "old_wait_abs_yaw_deg": float(np.degrees(waiting[j]["old_wait_motion"]["abs_net_yaw_rad"])),
            "boundary_entry_distance_m": near.get("distance_m"), "boundary_tangent_deg": near.get("boundary_tangent_deg"),
            "boundary_connector_deg": near.get("boundary_connector_deg"), "chosen_entry_distance_m": chosen.get("distance_m"),
            "connector_clearance_m": chosen.get("obstacle_clearance_m"), "connector_corridor_m": chosen.get("corridor_clearance_m"),
            "safe_entry_count": entry.get("safe_count", 0), "entry_count": entry["candidate_count"],
            "old_execution_risk": waiting[j]["pre_release_old_safety"]["safe"] is False,
            "old_wait_clearance_m": waiting[j]["pre_release_old_safety"].get("minimum_clearance_m"),
            "actual_fresh_clearance_m": execution.get("minimum_clearance_m"), "actual_fresh_corridor_m": execution.get("corridor_clearance_m"),
            "actual_fresh_safe": execution["safe"], "actual_interval_end_sim_s": float(sim[end]),
            "controller_point_anchor_offset_m": sem["offset_m"], "previous_v_m_s": before["v_m_s"], "previous_w_rad_s": before["w_rad_s"],
            "fresh_v_m_s": fresh["v_m_s"], "fresh_w_rad_s": fresh["w_rad_s"]}
        for part, check in path_checks[j].items():
            row[f"fresh_{part}_safe"] = check["safe"]
            row[f"fresh_{part}_clearance_m"] = check["obstacle_clearance_m"]
        pair_rows.append(row)
        details.append({"old_id": k, "fresh_id": j, "class": combined, "geometric_class": label,
            "old_observation_pose": old["observation_pose"], "fresh_observation_pose": fresh["observation_pose"], "boundary_pose": b.tolist(),
            "old_world_xy_m": worlds[k].tolist(), "fresh_world_xy_m": worlds[j].tolist(), "overlap": overlap, "entry": entry,
            "old_paths": path_checks[k], "fresh_paths": path_checks[j], "actual_fresh_execution": execution,
            "selected_point_semantics": sem, **waiting[j]})
    excluded = [{"id": r["id"], "reason": "received_without_actual_switch", "switch": None,
                 "classification": "OLD_EXECUTION_RISK" if waiting[r["id"]]["pre_release_old_safety"]["safe"] is False else "INSUFFICIENT_EVIDENCE",
                 "fresh_paths": path_checks[r["id"]], **waiting[r["id"]]} for r in unapplied]
    counts = Counter(r["class"] for r in pair_rows); gcounts = Counter(r["geometric_class"] for r in pair_rows)
    candidates = [d for d in details if d["class"] == "POTENTIAL_RECONCILIATION_CASE"]
    classifiable = len(pair_rows)-gcounts["INSUFFICIENT_EVIDENCE"]
    fraction = classifiable/len(pair_rows) if pair_rows else 0.
    verdict = ("GEOMETRIC_CANDIDATE_FOUND" if candidates else "NO_QUALIFIED_CANDIDATE"
               if fraction >= geometric["minimum_classifiable_fraction_for_negative_verdict"] else "INSUFFICIENT_EVIDENCE")
    if runtime["async_reproduction"] != "PASS": verdict = "INSUFFICIENT_EVIDENCE"
    invalid_metrics = ("progress_spatial_rmse_m", "progress_heading_rms_deg", "progress_lateral_rms_m", "progress_longitudinal_rms_m")
    metrics = {key: stats([r[key] for r in pair_rows if r.get(key) is not None and (key not in invalid_metrics or r["correspondence_valid"])]) for key in
        (*invalid_metrics, "switch_translation_m", "switch_abs_yaw_deg", "old_wait_distance_m", "old_wait_abs_yaw_deg", "boundary_entry_distance_m",
         "boundary_tangent_deg", "boundary_connector_deg", "connector_clearance_m", "actual_fresh_clearance_m", "controller_point_anchor_offset_m")}
    timing_stats = {key: stats([r[key] for r in timing if r[key] is not None and (not key.startswith("old_") or not r["initialization"])]) for key in
        ("packet_to_release_s", "delivery_deadline_overshoot_s", "observation_to_ready_s", "observation_to_release_s", "observation_to_switch_s",
         "old_wait_distance_m", "old_wait_abs_yaw_deg", "old_delivery_hold_distance_m", "old_gpu_distance_m")}
    report = {"condition": condition, "source_run": str(run), "configured_delay_s": delay, "execution_status": "COMPLETED",
        "execution_git_sha": provenance["git_sha"], "verdict": verdict, "actual_handoffs": len(pair_rows),
        "initialization_id": events[0]["id"], "received_without_switch_ids": [r["id"] for r in unapplied],
        "classes": {k: counts[k] for k in CLASSES}, "geometric_classes": {k: gcounts[k] for k in CLASSES[1:]},
        "valid_correspondence": sum(r["correspondence_valid"] for r in pair_rows), "classifiable_fraction": fraction,
        "invalid_correspondence_reasons": dict(Counter(r["correspondence_reason"] for r in pair_rows if not r["correspondence_valid"])),
        "candidate_fresh_ids": [d["fresh_id"] for d in candidates], "metrics": metrics, "timing": timing_stats,
        "warm_inference_ms": runtime["warm_inference_ms"], "cold_inference_ms": runtime["cold_inference_ms"],
        "requests": runtime["requests"], "received": runtime["received"], "switches": runtime["switches"],
        "busy_observation_skips": runtime["busy_observation_skips"], "missed_capture_slots": runtime["missed_capture_slots"],
        "timeout": runtime["timeout"], "pacing": runtime["pacing"], "async_reproduction": runtime["async_reproduction"],
        "real_time_pacing_pass": runtime["real_time_pacing_pass"], "inference_clock_mapping_pass": runtime["inference_clock_mapping_pass"],
        "navigation": {k: raw[k] for k in ("goal_entry", "minimum_goal_distance_m", "simulation_duration_s", "termination_reason", "final_pose", "obstacle_evaluation")},
        "old_risk_applied_fresh_ids": [r["fresh_id"] for r in pair_rows if r["old_execution_risk"]],
        "old_risk_unapplied_fresh_ids": [r["id"] for r in excluded if r["classification"] == "OLD_EXECUTION_RISK"],
        "unsafe_fresh_prediction_ids": [r["fresh_id"] for r in pair_rows if not r["fresh_native_full_safe"]],
        "unsafe_fresh_actual_execution_ids": [r["fresh_id"] for r in pair_rows if r["actual_fresh_safe"] is False],
        "uniform_delay_verification": "ALL_ACCEPTED_RESULTS_VERIFIED" if condition != "D0" else "LEGACY_BASELINE_NO_INJECTION",
        "validation": {"raw_outputs_and_original_controller": runtime["validation"]["status"],
            "max_pose_integration_error": runtime["validation"]["max_pose_integration_error"],
            "baseline_files_preserved": sum(map(len, preserved.values())), "new_run_inputs_preserved": len(hashes),
            "scenario_and_checkpoint_unchanged": True, "historical_execution_source_hashes_verified": True,
            "all_corridor_intervals_recomputed": True, "switch_tick_mismatch_ids": runtime["switch_tick_mismatch_ids"]},
        "limitations": ["D0 is a historical reference, not a paired causal no-delay trial",
            "One run per condition; RGB, sampling association and accepted request rate can differ",
            "Legacy D0 packet and release alias its received timestamp; no separate hold instrumentation",
            "All paths are observation-anchored; no native yaw or waypoint times",
            "Geometric connector safety is offline and is not executed by original PD"]}
    assert all(sha256_file(run/n) == h for n, h in hashes.items())
    assert all(sha256_file(baseline.parent/r/n) == h for r, files in preserved.items() for n, h in files.items())
    issues = [d for d in details if d["class"] in ("OLD_EXECUTION_RISK", "UNSAFE_FRESH", "POTENTIAL_RECONCILIATION_CASE")
              or d["actual_fresh_execution"]["safe"] is False]
    for name, value in (("summary", report), ("input_hashes", hashes), ("pair_details", details), ("unapplied", excluded), ("issues", issues)):
        write_json(output/f"{name}.json", value)
    csv_file(output/"pairs.csv", pair_rows); csv_file(output/"timing.csv", timing)
    print(json.dumps({k: report[k] for k in ("condition", "actual_handoffs", "classes", "verdict")}))
    return report


def compare(inputs, output):
    output.mkdir(parents=True, exist_ok=False)
    summaries = [json.loads((p/"summary.json").read_text()) for p in inputs]
    table = []
    for s in summaries:
        row = {k: s[k] for k in ("condition", "configured_delay_s", "execution_status", "verdict")}
        if s["execution_status"] == "COMPLETED":
            n = s["navigation"]; safety = n["obstacle_evaluation"]
            row.update({k: n[k] for k in ("goal_entry", "minimum_goal_distance_m", "simulation_duration_s", "termination_reason")})
            row.update({"collision": safety["geometric_overlap"], "corridor_containment": safety["corridor_containment_certified"],
                "safety_margin_met": safety["safety_margin_met"], "obstacle1_clearance_m": safety["obstacles"]["StaticObstacle1"]["minimum_swept_clearance_lower_m"],
                "obstacle2_clearance_m": safety["obstacles"]["StaticObstacle2"]["minimum_swept_clearance_lower_m"],
                "inference_warm_median_ms": s["warm_inference_ms"]["median"], "inference_warm_p95_ms": s["warm_inference_ms"]["p95"],
                "timeout_episodes": s["timeout"]["episodes"], "pacing_p95_ms": s["pacing"]["absolute_pose_error_s"]["p95"]*1000,
                "pacing_max_ms": s["pacing"]["absolute_pose_error_s"]["max"]*1000, "rtf": s["pacing"]["real_time_factor"]})
            for k in ("requests", "received", "switches", "actual_handoffs", "valid_correspondence", "busy_observation_skips", "missed_capture_slots", "async_reproduction"):
                row[k] = s[k]
            for source in ("timing", "metrics"):
                for k, distribution in s[source].items():
                    for q in ("median", "p95", "max"):
                        row[f"{k}_{q}"] = distribution.get(q)
            row.update(s["classes"])
        table.append(row)
    csv_file(output/"comparison.csv", table)
    write_json(output/"summary.json", {s["condition"]: s for s in summaries})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=["D0", "D250", "D500", "D750"])
    parser.add_argument("--run", type=Path); parser.add_argument("--baseline", type=Path)
    parser.add_argument("--compare", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.compare: compare(args.compare, args.output)
    else: analyze(args.condition, args.run.resolve(), args.baseline.resolve(), args.output.resolve())
