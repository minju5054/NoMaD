"""Offline evidence for one predeclared sudden-obstacle run; no inference."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image

from .async_report import rows, validate
from .async_handoff_audit import selected_point_semantics
from .clearance import obstacle_bounds, single_obstacle_config, swept_clearance, corridor_clearance, point_clearance
from .common import ROOT, local_to_world, sha256_file, write_json
from .handoff_audit import path_safety, correspondence, boundary_entries, classify


def analyze(run, output, rgb_visibility_recovery=False):
    output.mkdir(parents=True, exist_ok=False)
    preserved = json.loads((run.parent/"sudden_obstacle_preservation_01.json").read_text())
    assert all(sha256_file(Path(p)) == h for p, h in preserved.items())
    inputs = sorted(p for p in run.rglob("*") if p.is_file() and
                    (p.parent == run or p.parent.name in ("dynamic", "observations", "raw", "derived", "model"))
                    and p.suffix in (".json", ".jsonl", ".csv", ".png", ".npz", ".usda"))
    hashes = {str(p.relative_to(run)): sha256_file(p) for p in inputs}
    raw = json.loads((run/"summary.json").read_text()); config = raw["scenario"]
    provenance = json.loads((run/"provenance.json").read_text())
    assert provenance["git_status"] == "" and not provenance["controlled_delivery_delay"]
    assert provenance["uniform_delivery_delay_s"] is None and "delivery_delay" not in raw
    for name, digest in provenance["source_sha256"].items():
        contents = subprocess.check_output(["git", "show", f"{provenance['git_sha']}:{name}"], cwd=ROOT)
        assert hashlib.sha256(contents).hexdigest() == digest
    dynamic = config["dynamic_obstacle"]; spawn_tick = dynamic["spawn_tick"]; hz = config["integration_hz"]
    runtime = validate(run, run.parent/"two_obstacles_01", output/"runtime_validation")
    requests, received, events, observations = [rows(run/name) for name in
        ("requests.jsonl", "received.jsonl", "events.jsonl", "observations.jsonl")]
    observations = [o for o in observations if "observation_id" in o]
    obs = {o["observation_id"]: o for o in observations}; by_event = {e["id"]: e for e in events}
    workers = rows(run/"model/inference.jsonl")
    trace = np.genfromtxt(run/"agent_trajectory.csv", delimiter=",", names=True, dtype=None, encoding="utf-8")
    pose = np.column_stack([trace[k] for k in ("x_m", "y_m", "yaw_rad")])
    wall = trace["monotonic_ns"]; times = trace["simulation_time_s"]; epoch = raw["epoch_monotonic_ns"]
    static = rows(run/"clearance.jsonl"); activation = rows(run/"dynamic/activation.jsonl")
    dynamic_clearance = rows(run/"dynamic/clearance.jsonl")
    lower, upper = obstacle_bounds(single_obstacle_config(config, dynamic))
    assert len(activation) == len(pose)
    assert len(dynamic_clearance) == max(0, len(pose)-spawn_tick)
    for i, a in enumerate(activation):
        assert a["tick"] == i and a["active"] == (i >= spawn_tick) == a["collision_checked"]
        assert a["monotonic_ns"] == int(wall[i])
        if i >= spawn_tick:
            duration = 0. if i == spawn_tick else 1/hz
            start = pose[i] if i == spawn_tick else pose[i-1]
            d = dynamic_clearance[i-spawn_tick]
            assert a["checked_duration_s"] == duration
            np.testing.assert_allclose(d["start_pose"], start, atol=1e-12, rtol=0)
            np.testing.assert_allclose(d["end_pose"], pose[i], atol=1e-12, rtol=0)
            check = swept_clearance(start, trace["v_m_s"][i], trace["w_rad_s"][i], duration,
                                    lower, upper, config["agent_radius_m"], config["required_clearance_m"])
            for k in ("lower_m", "upper_m", "geometric_overlap"):
                assert abs(d[k]-check[k]) < 1e-11
        if i:
            c = corridor_clearance(pose[i-1], pose[i], trace["v_m_s"][i], trace["w_rad_s"][i], 1/hz,
                                   config["corridor"], config["agent_radius_m"])
            assert abs(c-static[i]["corridor_lower_m"]) < 1e-11

    image_arrays, rgb_evidence_rows = {}, []
    for o in observations:
        image = np.array(Image.open(run/o["rgb_file"]).convert("RGB"))
        mask = np.array(Image.open(run/o["dynamic_mask_file"])) > 0
        d = o["dynamic"]; tick = round(o["observation_sim_s"]*hz)
        assert d["capture_tick"] == tick and d["active"] == (tick >= spawn_tick)
        assert hashlib.sha256(image.tobytes()).hexdigest() == o["frame_sha256"]
        assert hashlib.sha256(mask.tobytes()).hexdigest() == d["mask_sha256"]
        assert int(mask.sum()) == d["instance_pixels"]
        assert d["visible"] == (int(mask.sum()) >= dynamic["minimum_visible_pixels"])
        if not d["active"]: assert not mask.any()
        rgb = image.astype(float)
        # Same predeclared magenta rule; apply to saved RGB, not the empty instance mask.
        rgb_mask = ((rgb[:, :, 0] > 1.5*rgb[:, :, 1]) & (rgb[:, :, 2] > 1.5*rgb[:, :, 1]) &
                    (rgb[:, :, 0] > 40) & (rgb[:, :, 2] > 40))
        resized = np.array(Image.fromarray(rgb_mask.astype(np.uint8)*255).resize((96, 96), Image.Resampling.NEAREST))
        rgb_evidence_rows.append({"observation_id": o["observation_id"], "simulation_time_s": o["observation_sim_s"],
            "active": d["active"], "recorded_instance_pixels": d["instance_pixels"],
            "rgb_magenta_pixels": int(rgb_mask.sum()), "resized_96_mask_pixels": int(np.count_nonzero(resized)),
            "rgb_file": o["rgb_file"], "frame_sha256": o["frame_sha256"]})
        image_arrays[o["observation_id"]] = image
    for q, worker in zip(requests, workers):
        ids = q["history_observation_ids"]
        assert q["history_dynamic"] == [obs[i]["dynamic"] for i in ids]
        history = np.stack([image_arrays[i] for i in ids])
        assert hashlib.sha256(history.tobytes()).hexdigest() == worker["history_sha256"]
    if rgb_visibility_recovery:
        assert all(o["dynamic"]["instance_pixels"] == 0 for o in observations)
        assert max(r["rgb_magenta_pixels"] for r in rgb_evidence_rows if not r["active"]) == 0
        visible_ids = {r["observation_id"] for r in rgb_evidence_rows if r["active"] and
                       r["rgb_magenta_pixels"] >= dynamic["minimum_visible_pixels"]}
    else:
        visible_ids = {o["observation_id"] for o in observations if o["dynamic"]["visible"]}
    visible = [o for o in observations if o["observation_id"] in visible_ids]
    fresh_requests = [r for r in received if visible_ids.intersection(r["history_observation_ids"])]
    first_visible = visible[0] if visible else None
    fresh = fresh_requests[0] if fresh_requests else None
    spawn = raw["dynamic_obstacle"]["spawn"]
    old = received[spawn["old_id"]] if spawn and spawn["old_id"] >= 0 else None
    if spawn:
        np.testing.assert_allclose(spawn["pose"], pose[spawn_tick], atol=1e-12, rtol=0)
        assert spawn["monotonic_ns"] == int(wall[spawn_tick])
        assert spawn["old_id"] == int(trace["incoming_waypoint_id"][spawn_tick])
    both = {**config, "obstacles": [*config["obstacles"], dynamic]}
    solo = {**config, "obstacles": [dynamic]}
    worlds, locals_, checks, prediction_rows = {}, {}, {}, []
    for r in received:
        j = r["id"]
        with np.load(run/f"model/derived/{j:04d}.npz", allow_pickle=False) as z: local = z["metric"][0].copy()
        world = local_to_world(local, r["observation_pose"])
        worlds[j], locals_[j] = world, local
        checks[j] = {scope: {part: path_safety(points, scenario) for part, points in
                     (("full", world), ("prefix", world[:3]),
                      ("origin_prefix", np.vstack([r["observation_pose"][:2], world[:3]])))}
                     for scope, scenario in (("dynamic_only", solo), ("all_obstacles", both))}
        prediction_rows.append({"id": j, "observation_sim_s": r["observation_sim_s"], "applied": j in by_event,
            "includes_visible_dynamic": bool(visible_ids.intersection(r["history_observation_ids"])),
            **{f"{scope}_{part}_{key}": value for scope, parts in checks[j].items() for part, result in parts.items()
               for key, value in result.items() if key in ("safe", "obstacle_clearance_m", "corridor_clearance_m")}})

    def execution(start, end):
        if end <= start: return {"safe": None, "intervals": 0}
        indices = list(range(start+1, end+1))
        minimum = min(dynamic_clearance[i-spawn_tick]["lower_m"] for i in indices)
        static_min = min(static[i]["lower_m"] for i in indices)
        corridor = min(static[i]["corridor_lower_m"] for i in indices)
        unsafe = [i for i in indices if min(dynamic_clearance[i-spawn_tick]["lower_m"], static[i]["lower_m"]) < .02 or static[i]["corridor_lower_m"] <= 0]
        first = unsafe[0] if unsafe else None
        return {"start_sim_s": float(times[start]), "end_sim_s": float(times[end]), "intervals": len(indices),
                "command_ids": sorted(set(map(int, trace["incoming_waypoint_id"][indices]))),
                "dynamic_minimum_clearance_m": minimum, "static_minimum_clearance_m": static_min,
                "corridor_minimum_clearance_m": corridor,
                "safe": minimum >= .02 and static_min >= .02 and corridor > 0,
                "dynamic_geometric_overlap": any(dynamic_clearance[i-spawn_tick]["geometric_overlap"] for i in indices),
                "distance_m": float(np.sum(np.abs(trace["v_m_s"][indices]))/hz),
                "signed_yaw_deg": float(np.degrees(np.sum((np.diff(pose[start:end+1, 2])+np.pi)%(2*np.pi)-np.pi))),
                "first_unsafe_interval": None if first is None else {"tick": first, "end_sim_s": float(times[first]),
                    "end_pose": pose[first].tolist(), "incoming_id": int(trace["incoming_waypoint_id"][first]),
                    "v_m_s": float(trace["v_m_s"][first]), "w_rad_s": float(trace["w_rad_s"][first])}}

    event = by_event.get(fresh["id"]) if fresh else None
    switch = round(event["application_sim_s"]*hz) if event else None
    boundary = pose[switch] if switch is not None else None
    waiting = execution(spawn_tick, switch if switch is not None else len(pose)-1) if spawn else None
    fresh_execution = None
    if event:
        next_event = next((e for e in events if e["application_sim_s"] > event["application_sim_s"]), None)
        end = round(next_event["application_sim_s"]*hz) if next_event else len(pose)-1
        fresh_execution = execution(switch, end)
    geometry = None
    if old and fresh and event:
        protocol = json.loads(Path(__file__).with_name("async_handoff_protocol.json").read_text())
        overlap = correspondence(worlds[old["id"]], worlds[fresh["id"]], boundary, protocol)
        entry = boundary_entries(worlds[fresh["id"]], boundary, both, protocol)
        label = classify(checks[fresh["id"]]["all_obstacles"]["full"], overlap, entry, protocol)
        geometry = {"classification": label, "overlap": overlap, "entry": entry,
                    "selected_point_semantics": selected_point_semantics(locals_[fresh["id"]][2].tolist(), fresh["observation_pose"], boundary)}
    prediction_case = "INSUFFICIENT_EVIDENCE"
    if old and fresh:
        old_safe = checks[old["id"]]["dynamic_only"]["full"]["safe"]
        fresh_safe = checks[fresh["id"]]["all_obstacles"]["full"]["safe"]
        prediction_case = ("OLD_SAFE_FRESH_SAFE" if old_safe and fresh_safe else
                           "OLD_UNSAFE_FRESH_SAFE" if fresh_safe else
                           "OLD_UNSAFE_FRESH_UNSAFE" if not old_safe else "OLD_SAFE_FRESH_UNSAFE")
    rgb_evidence = bool(first_visible and (rgb_visibility_recovery or
        first_visible["dynamic"]["magenta_pixels"] >= dynamic["minimum_visible_pixels"]))
    verdict = "INSUFFICIENT_EVIDENCE"
    if geometry and rgb_evidence and runtime["async_reproduction"] == "PASS":
        if geometry["classification"] == "POTENTIAL_RECONCILIATION_CASE" and waiting["safe"]:
            verdict = "GEOMETRIC_CANDIDATE_FOUND"
        elif geometry["classification"] != "INSUFFICIENT_EVIDENCE":
            verdict = "NO_QUALIFIED_CANDIDATE"
    timings = {"spawn_sim_s": spawn["simulation_time_s"] if spawn else None,
               "spawn_host_ns": spawn["monotonic_ns"] if spawn else None,
               "first_visible_observation_id": first_visible["observation_id"] if first_visible else None,
               "first_visible_sim_s": first_visible["observation_sim_s"] if first_visible else None,
               "first_visible_capture_host_ns": first_visible["observation_monotonic_ns"] if first_visible else None,
               "first_visible_capture_end_host_ns": first_visible["capture_end_monotonic_ns"] if first_visible else None,
               "fresh_observation_sim_s": fresh["observation_sim_s"] if fresh else None,
               "fresh_observation_host_ns": fresh["observation_monotonic_ns"] if fresh else None,
               "ready_host_ns": fresh["ready_monotonic_ns"] if fresh else None,
               "switch_sim_s": event["application_sim_s"] if event else None,
               "switch_host_ns": event["application_monotonic_ns"] if event else None}
    timings["host_elapsed_s"] = {k:(v-epoch)/1e9 for k,v in timings.items() if k.endswith("host_ns") and v is not None}
    timings["ready_sim_interpolated_s"] = (float(np.interp(fresh["ready_monotonic_ns"]-epoch, wall-epoch, times))
        if fresh and wall[0] <= fresh["ready_monotonic_ns"] <= wall[-1] else None)
    report = {"source_run": str(run), "execution_git_sha": json.loads((run/"provenance.json").read_text())["git_sha"],
        "spawn": spawn, "timing": timings, "old_id": old["id"] if old else None, "fresh_id": fresh["id"] if fresh else None,
        "fresh_applied": event is not None, "boundary_pose": boundary.tolist() if boundary is not None else None,
        "intervening_pre_fresh_switch_ids": [e["id"] for e in events if spawn and
            e["application_sim_s"] >= spawn["simulation_time_s"] and (not event or e["application_sim_s"] < event["application_sim_s"])],
        "old_selected_waypoint_m": old["selected_waypoint_m"] if old else None,
        "fresh_selected_waypoint_m": fresh["selected_waypoint_m"] if fresh else None,
        "fresh_controller_vw": [event["v_m_s"], event["w_rad_s"]] if event else None,
        "first_visible_observation": first_visible, "fresh_history_ids": fresh["history_observation_ids"] if fresh else None,
        "visible_history_ids": [i for i in fresh["history_observation_ids"] if i in visible_ids] if fresh else [],
        "visibility_selection_source": "OFFLINE_RGB_RECOVERY" if rgb_visibility_recovery else "RECORDED_INSTANCE_MASK",
        "rgb_visibility_evidence": rgb_evidence_rows,
        "old_observation_pose": old["observation_pose"] if old else None,
        "fresh_observation_pose": fresh["observation_pose"] if fresh else None,
        "old_world_xy_m": worlds[old["id"]].tolist() if old else None,
        "fresh_world_xy_m": worlds[fresh["id"]].tolist() if fresh else None,
        "old_safety": checks[old["id"]] if old else None, "fresh_safety": checks[fresh["id"]] if fresh else None,
        "pre_fresh_execution": waiting, "fresh_execution": fresh_execution, "geometry": geometry,
        "prediction_case": prediction_case, "graph_verdict": verdict,
        "post_visible_safe_full_prediction_ids": [r["id"] for r in prediction_rows if r["includes_visible_dynamic"] and r["all_obstacles_full_safe"]],
        "post_visible_safe_prefix_prediction_ids": [r["id"] for r in prediction_rows if r["includes_visible_dynamic"] and r["all_obstacles_prefix_safe"]],
        "navigation": {k:raw[k] for k in ("goal_entry", "termination_reason", "simulation_duration_s", "minimum_goal_distance_m", "final_pose", "dynamic_obstacle", "obstacle_evaluation", "combined_avoidance_success")},
        "runtime": {k:runtime[k] for k in ("async_reproduction", "pacing", "warm_inference_ms", "timeout", "requests", "received", "switches", "busy_observation_skips", "missed_capture_slots")},
        "validation": {"all_rgb_history_worker_hashes": "PASS",
            "visibility_evidence": ("RGB_CONFIRMED_MASK_CHANNEL_FAILED" if rgb_visibility_recovery else "PASS") if rgb_evidence else "INSUFFICIENT_EVIDENCE",
            "inactive_before_spawn_and_zero_duration_activation": "PASS", "dynamic_and_corridor_clearance_recomputed": "PASS",
            "input_count": len(hashes), "preserved_previous_inputs": len(preserved)},
        "limitations": ["Fixed-goal adapter; single pilot; no counterfactual execution or Graph",
                        "Appearance keyed to logical simulation timestamp; RGB sampled at 4 Hz",
                        "Paths observation-anchored; no native yaw or waypoint time", "Safe polyline is not a guarantee of original PD execution",
                        "Instance path matching recorded zero IDs; RGB recovery is an explicit offline instrumentation correction, not a successful instance-mask gate"
                        if rgb_visibility_recovery else "Instance-mask gate used without RGB recovery"]}
    with (output/"predictions.csv").open("x") as f:
        writer = csv.DictWriter(f, fieldnames=list(prediction_rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(prediction_rows)
    write_json(output/"summary.json", report)
    assert all(sha256_file(run/name) == h for name, h in hashes.items())
    assert all(sha256_file(Path(p)) == h for p, h in preserved.items())
    write_json(output/"input_hashes.json", hashes)
    print(json.dumps({k: report[k] for k in ("old_id", "fresh_id", "fresh_applied", "prediction_case", "graph_verdict")}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rgb-visibility-recovery", action="store_true", help="Preserve failed masks; use predeclared magenta rule on saved RGB only")
    args = parser.parse_args(); analyze(args.run.resolve(), args.output.resolve(), args.rgb_visibility_recovery)
