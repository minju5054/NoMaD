"""S0 saved-log metrics and small-sample intervals; never starts navigation."""
import csv
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np

from nomad_isaac.async_report import rows
from nomad_isaac.common import integrate_se2, original_controller, sha256_file, write_json
from nomad_isaac.seed_offset import request_seed
from .chunk_report import trace


PROTOCOL_PATH = Path(__file__).with_name("s0_batch_protocol.json")
SCOPE = "Oracle geometry evaluation; SE(2) kinematic Isaac Sim"


def protocol():
    return json.loads(PROTOCOL_PATH.read_text())


def classify(goal, overlap, corridor_violation, reason, duration):
    if overlap or corridor_violation:
        return "SAFETY_FAILURE"
    if goal:
        return "SUCCESS"
    if reason == "simulation_timeout" and abs(duration-60.) < 1e-9:
        return "STUCK"
    return "OTHER_TERMINATION"


def corridor_arc_minimum(pose, v, w, dt, corridor, radius):
    """Exact constant-command arc extrema; no command change or new geometry model."""
    times = [0., dt]
    if w != 0:
        a, b = sorted((pose[2], pose[2]+w*dt))
        for k in range(math.floor(a/(math.pi/2)), math.ceil(b/(math.pi/2))+1):
            t = (k*math.pi/2-pose[2])/w
            if 0 < t < dt:
                times.append(t)
    xy = np.array([integrate_se2(pose, v, w, t)[:2] for t in times])
    return float(min(np.min(xy[:, 0]-corridor["xmin"]), np.min(corridor["xmax"]-xy[:, 0]),
                     np.min(corridor["half_width"]-np.abs(xy[:, 1])))-radius)


def pd_unclipped_w(waypoint):
    dx, dy = waypoint
    return float(np.sign(dy)*np.pi/(2*.25) if abs(dx) < 1e-8 else np.arctan(dy/dx)/.25)


def margin_violation_duration(intervals):
    return sum(r["end_sim_s"]-r["start_sim_s"] for r in intervals
               if r["end_sim_s"] > r["start_sim_s"] and r["lower_m"] < .02)


def extract_run(run, condition, run_id, offset, legacy=False):
    """PP applied fields and PD original fields checked against actual 72Hz commands."""
    run = Path(run)
    s = json.loads((run/"summary.json").read_text())
    c = s["scenario"]
    p = protocol()
    prov = json.loads((run/"provenance.json").read_text())
    pp = condition == "PP"
    assert condition in ("PP", "PD") and bool(s.get("pure_pursuit_enabled")) == pp
    assert not s.get("oracle_safety_stop_enabled") and not s.get("online_graph_enabled")
    assert c.get("seed_offset", 0) == offset and c["seed"] == 101
    assert c["topomap_manifest_sha256"] == p["topomap_manifest_sha256"]
    assert sha256_file(Path(c["topomap_manifest"])) == p["topomap_manifest_sha256"]
    source_hash = prov.get("source_scenario_sha256", prov["source_sha256"].get(p["scenario"]))
    assert source_hash == p["scenario_sha256"]
    assert (c["controller_hz"], c["integration_hz"], c["observation_hz"]) == (9, 72, 4)
    assert c["selected_sample"] == 0 and c["selected_waypoint_index"] == 2
    assert not prov.get("controlled_delivery_delay") and prov.get("uniform_delivery_delay_s") is None
    if not legacy:
        assert c["run_id"] == s["run_id"] == prov["run_id"] == run_id
        assert s["experiment_label"] == "PHASE0_D_S0_BATCH"
        assert prov["seed_offset"] == offset and not prov["git_status"]
        assert json.loads((run/"batch_protocol.json").read_text()) == p
    control, events, received, requests, inference = (rows(run/name) for name in
        ("controller.jsonl", "events.jsonl", "received.jsonl", "requests.jsonl", "model/inference.jsonl"))
    records, poses = trace(run)
    gaps = rows(run/"clearance.jsonl")
    assert len(records) == len(gaps) and len(received) == len(requests) == len(inference)
    seeds = []
    for i, (q, r, model) in enumerate(zip(requests, received, inference)):
        expected = request_seed(c, i)
        assert q["id"] == r["id"] == model["id"] == i
        assert q["seed"] == r["seed"] == model["seed"] == expected
        assert r["ddpm_seed"] == model["ddpm_seed"] == expected+1
        if not legacy:
            assert q["run_id"] == r["run_id"] == model["run_id"] == run_id
            assert q["seed_offset"] == r["seed_offset"] == model["seed_offset"] == offset
        seeds.append({"request_id": i, "seed": expected, "ddpm_seed": expected+1})
    fields = ("applied_v_m_s", "applied_w_rad_s") if pp else ("v_m_s", "w_rad_s")
    actual = np.array([[r[k] for k in fields] for r in control])
    original = original_controller()
    clips = []
    for r, command in zip(control, actual):
        if pp:
            raw_w = r["pure_pursuit"].get("raw_w_rad_s", 0.)
            clipped = abs(raw_w-command[1]) > 1e-12
            assert clipped == r["pure_pursuit"]["w_clipped"]
        elif r["valid"]:
            waypoint = received[r["latest_received_id"]]["selected_waypoint_m"]
            np.testing.assert_allclose(command, original(waypoint), atol=1e-12, rtol=0)
            raw_w = pd_unclipped_w(waypoint)
            np.testing.assert_allclose(command[1], np.clip(raw_w, -.4, .4), atol=1e-12, rtol=0)
            clipped = abs(raw_w-command[1]) > 1e-12
        else:
            np.testing.assert_array_equal(command, [0., 0.])
            clipped = False
        clips.append(bool(clipped))
    max_pose_error = 0.
    min_corridor = math.inf
    dt = 1/72
    stopped = distance = 0.
    for i in range(1, len(records)):
        row = records[i]
        command = [float(row["v_m_s"]), float(row["w_rad_s"])]
        np.testing.assert_allclose(command, actual[(i-1)//8], atol=1e-12, rtol=0)
        max_pose_error = max(max_pose_error, float(np.max(np.abs(integrate_se2(poses[i-1], *command, dt)-poses[i]))))
        assert abs(float(row["simulation_time_s"])-i*dt) < 1e-10
        assert abs(gaps[i]["end_sim_s"]-i*dt) < 1e-10
        assert abs(gaps[i]["start_sim_s"]-(i-1)*dt) < 1e-10
        if command == [0., 0.]:
            stopped += dt
        distance += float(np.linalg.norm(poses[i, :2]-poses[i-1, :2]))
        min_corridor = min(min_corridor, corridor_arc_minimum(poses[i-1], *command, dt, c["corridor"], c["agent_radius_m"]))
    assert max_pose_error < 1e-10
    assert abs(distance-s["distance_travelled_m"]) < 1e-10
    event_ticks = [round(e["application_sim_s"]*72) for e in events]
    deltas, reversals = [], 0
    for e, tick in zip(events, event_ticks):
        assert tick % 8 == 0
        index = tick//8
        assert control[index]["waypoint_id"] == e["id"]
        np.testing.assert_allclose(actual[index], [e[k] for k in fields], atol=1e-12, rtol=0)
        if index and control[index-1]["waypoint_id"] >= 0:
            before, after = actual[index-1, 1], actual[index, 1]
            deltas.append(abs(float(after-before)))
            reversals += int(before*after < 0)
    overlap = any(r["geometric_overlap"] for r in gaps)
    assert overlap == s["obstacle_evaluation"]["geometric_overlap"]
    corridor_violation = min_corridor < 0.
    classification = classify(s["goal_entry"], overlap, corridor_violation, s["termination_reason"], s["simulation_duration_s"])
    record = {"scope": SCOPE, "run_id": run_id, "condition": condition, "seed_offset": offset,
              "source_run": str(run), "legacy_preflight_only": legacy, "execution_git_sha": prov["git_sha"],
              "scenario_sha256": source_hash, "runtime_config_sha256": sha256_file(run/"scenario.json"),
              "topomap_sha256": c["topomap_manifest_sha256"], "classification": classification,
              "termination_reason": s["termination_reason"], "technical_failure": False,
              "success": classification == "SUCCESS", "safety_failure": classification == "SAFETY_FAILURE",
              "goal_entry": s["goal_entry"],
              "timeout": s["termination_reason"] == "simulation_timeout" and abs(s["simulation_duration_s"]-60) < 1e-9,
              "geometric_overlap": overlap, "corridor_violation": corridor_violation,
              "corridor_minimum_exact_arc_m": min_corridor,
              "corridor_containment_certified": s["obstacle_evaluation"]["corridor_containment_certified"],
              "goal_time_s": s["simulation_duration_s"] if s["goal_entry"] else None,
              "duration_s": s["simulation_duration_s"], "stop_time_s": stopped, "distance_m": distance,
              "margin_violation_s": margin_violation_duration(gaps), "switch_abs_dw_median": float(np.median(deltas)) if deltas else None,
              "switch_abs_dw_max": max(deltas) if deltas else None, "switch_sign_reversals": reversals,
              "w_clipping_fraction": sum(clips)/len(clips), "w_clipped_ticks": sum(clips), "control_ticks": len(clips),
              "switch_pairs": len(deltas), "max_pose_replay_error": max_pose_error,
              "requests": len(seeds), "request_seeds": seeds}
    for box in c["obstacles"]:
        key = box["id"]
        minimum = min(g["obstacles"][key]["lower_m"] for g in gaps)
        logged = s["obstacle_evaluation"]["obstacles"][key]
        assert abs(minimum-logged["minimum_swept_clearance_lower_m"]) < 1e-10
        side = logged["passage"]["side"] if logged["passage"] else "not_passed"
        record[key+"_minimum_clearance_m"] = minimum
        record[key+"_passage_side"] = side
        record[key+"_pass_plus_y"] = int(side == "left_positive_y")
        record[key+"_pass_minus_y"] = int(side == "right_negative_y")
        record[key+"_not_passed"] = int(side == "not_passed")
    return record


def wilson(values):
    n = len(values)
    if not n:
        return {"n": 0, "count": 0, "estimate": None, "ci95": [None, None], "method": "Wilson"}
    count = int(sum(values))
    z = protocol()["statistics"]["normal_z"]
    proportion = count/n
    denominator = 1+z*z/n
    center = (proportion+z*z/(2*n))/denominator
    half = z*math.sqrt(proportion*(1-proportion)/n+z*z/(4*n*n))/denominator
    return {"n": n, "count": count, "estimate": proportion,
            "ci95": [max(0., center-half), min(1., center+half)], "method": "Wilson"}


def bootstrap_mean(values):
    settings = protocol()["statistics"]
    a = np.asarray(values, dtype=float)
    if not len(a):
        return {"n": 0, "estimate": None, "ci95": [None, None], "method": "percentile bootstrap mean"}
    assert np.isfinite(a).all()
    rng = np.random.Generator(np.random.PCG64(settings["bootstrap_seed"]))
    means = a[rng.integers(0, len(a), size=(settings["bootstrap_resamples"], len(a)))].mean(axis=1)
    return {"n": len(a), "estimate": float(a.mean()), "ci95": np.percentile(means, [2.5, 97.5]).tolist(),
            "method": "percentile bootstrap mean"}


CONTINUOUS = ["goal_time_s", "duration_s", "stop_time_s", "distance_m", "margin_violation_s",
              "switch_abs_dw_median", "switch_abs_dw_max", "switch_sign_reversals", "w_clipping_fraction",
              "StaticObstacle1_minimum_clearance_m", "StaticObstacle2_minimum_clearance_m"]
BINARY = ["success", "goal_entry", "safety_failure", "timeout", "technical_failure"] + [
    f"StaticObstacle{i}_{suffix}" for i in (1, 2) for suffix in ("pass_plus_y", "pass_minus_y", "not_passed")]


def aggregate(records):
    ids = [(r["run_id"], r["condition"]) for r in records]
    assert len(ids) == len(set(ids)), "Duplicate run/condition would imply a retry"
    conditions = {}
    for condition in ("PP", "PD"):
        group = [r for r in records if r["condition"] == condition]
        estimates = {}
        for metric in BINARY+CONTINUOUS:
            values = [r[metric] for r in group if r.get(metric) is not None]
            estimate = wilson(values) if metric in BINARY else bootstrap_mean(values)
            estimates[metric] = {**estimate, "missing": len(group)-len(values)}
        conditions[condition] = {"attempted": len(group), "metrics": estimates,
            "classification_counts": dict(Counter(r["classification"] for r in group if "classification" in r)),
            "termination_counts": dict(Counter(r.get("termination_reason", "technical_failure") for r in group))}
    pp = {r["run_id"]: r for r in records if r["condition"] == "PP"}
    pd = {r["run_id"]: r for r in records if r["condition"] == "PD"}
    paired = {}
    for metric in BINARY+CONTINUOUS:
        valid = [key for key in sorted(pp.keys() & pd.keys())
                 if pp[key].get(metric) is not None and pd[key].get(metric) is not None]
        assert all(pp[key]["seed_offset"] == pd[key]["seed_offset"] for key in valid)
        differences = [float(pp[key][metric])-float(pd[key][metric]) for key in valid]
        paired[metric] = {**bootstrap_mean(differences), "run_ids": valid,
                          "missing_pairs": protocol()["pairs"]-len(valid)}
    return {"scope": SCOPE, "label": "S0_PAIRED_BATCH_METRICS", "planned_per_condition": 10,
            "attempted": len(records), "conditions": conditions, "paired_PP_minus_PD": paired,
            "protocol": protocol(),
            "missing_goal_time_policy": "null, not 60s; conditional means and complete both-goal pairs"}


def write_csv(path, records):
    names = list(dict.fromkeys(key for r in records for key in r))
    with Path(path).open("x") as f:
        writer = csv.DictWriter(f, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in r.items()} for r in records)


def save_aggregate(out, records):
    out.mkdir(exist_ok=False)
    report = aggregate(records)
    write_json(out/"summary.json", report)
    write_csv(out/"runs.csv", [{k: v for k, v in r.items() if k != "request_seeds"} for r in records])
    table = []
    for condition, group in report["conditions"].items():
        for metric, estimate in group["metrics"].items():
            table.append({"scope": SCOPE, "condition": condition, "metric": metric, **estimate})
    write_csv(out/"conditions.csv", table)
    write_csv(out/"paired_differences.csv",
              [{"scope": SCOPE, "metric": key, **value} for key, value in report["paired_PP_minus_PD"].items()])
