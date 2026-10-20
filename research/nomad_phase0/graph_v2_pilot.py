"""Read-only S0 PP handoff selection, verification, and one-shot offline comparison."""
import argparse
import csv
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import scipy

from nomad_isaac.async_report import rows
from nomad_isaac.common import ROOT, local_to_world, sha256_file, write_json
from .chunk_report import trace
from .graph_v2 import GraphV2, improvement, rollout
from .pure_pursuit import PurePursuit, XYPath
from .s0_batch_metrics import extract_run

PROTOCOL = Path(__file__).with_name("graph_v2_protocol.json")
SOURCE_ROOT = ROOT.parent/"artifacts/isaac6/s0_paired_n10_01"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def command(row):
    return np.array([row["applied_v_m_s"], row["applied_w_rad_s"]], dtype=float)


def distribution(values):
    a = np.asarray(values, dtype=float)
    return {"n": len(a), **({key: float(value) for key, value in
            zip(("mean", "median", "p95", "max", "min"),
                (np.mean(a), np.median(a), np.percentile(a, 95), np.max(a), np.min(a)))} if len(a) else {})}


def write_csv(path, records):
    with path.open("x") as f:
        writer = csv.DictWriter(f, list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def preflight(output):
    output.mkdir(parents=True, exist_ok=False)
    p = json.loads(PROTOCOL.read_text())
    follower = json.loads(PROTOCOL.with_name("chunk_pilot_protocol.json").read_text())["follower"]
    assert all(follower[k] == v for k, v in p["follower"].items())
    prior_verification_path = ROOT/"research/results/phase0d_s0_paired_n10_20261020/verification.json"
    prior = json.loads(prior_verification_path.read_text())
    hashes = {str(PROTOCOL): sha256_file(PROTOCOL),
              str(prior_verification_path): sha256_file(prior_verification_path)}
    # Compare existing immutable batch evidence as well as compute new hashes.
    recorded_hashes = prior["source_file_sha256"]
    assert isinstance(recorded_hashes, dict)
    all_cases, run_records, exclusions = [], [], []
    max_errors = {"world_m": 0., "observation_pose": 0., "boundary_pose": 0.,
                  "first_command": 0., "rollout_pose": 0., "rollout_clearance_m": 0.}

    def check_hash(path):
        value = sha256_file(path)
        hashes[str(path)] = value
        relative = str(path.relative_to(SOURCE_ROOT))
        if relative in recorded_hashes:
            assert value == recorded_hashes[relative], f"Prior input hash changed: {path}"

    for n in range(1, 11):
        run_id = f"S0_{n:02d}"
        run = SOURCE_ROOT/run_id/"PP"
        # Existing loader validates seeds, provenance, commands, poses and safety logs.
        baseline = extract_run(run, "PP", run_id, n*10000)
        files = ["summary.json", "scenario.json", "provenance.json", "events.jsonl",
                 "controller.jsonl", "agent_trajectory.csv", "received.jsonl", "requests.jsonl",
                 "clearance.jsonl", "batch_protocol.json", "model/inference.jsonl"]
        for name in files:
            check_hash(run/name)
        config = json.loads((run/"scenario.json").read_text())
        assert config["agent_radius_m"] == p["radius_m"] and config["required_clearance_m"] == p["required_clearance_m"]
        control, events, received = (rows(run/name) for name in
                                     ("controller.jsonl", "events.jsonl", "received.jsonl"))
        records, poses = trace(run)
        gaps = rows(run/"clearance.jsonl")
        event_ids = {e["id"] for e in events}
        for e in received:
            if e["id"] not in event_ids:
                exclusions.append({"run_id": run_id, "fresh_id": e["id"], "reason": "received_unapplied"})
        event_ticks = [round(e["application_sim_s"]*72) for e in events]
        worlds = {}
        for e, tick in zip(events, event_ticks):
            file = run/f"model/derived/{e['id']:04d}.npz"
            check_hash(file)
            with np.load(file, allow_pickle=False) as data:
                metric = data["metric"]
                assert metric.shape == (8, 8, 2) and np.isfinite(metric).all()
                local = metric[0]
            world = local_to_world(local, np.asarray(e["observation_pose"]))
            worlds[e["id"]] = world
            error = float(np.max(np.abs(world-np.array(e["chunk"]["world_xy_m"]))))
            max_errors["world_m"] = max(max_errors["world_m"], error)
            np.testing.assert_allclose(local, e["chunk"]["native_local_xy_m"], atol=p["verification_atol"], rtol=0)
            obs_tick = round(e["observation_sim_s"]*72)
            max_errors["observation_pose"] = max(max_errors["observation_pose"],
                float(np.max(abs(poses[obs_tick]-e["observation_pose"]))))
            max_errors["boundary_pose"] = max(max_errors["boundary_pose"],
                float(np.max(abs(poses[tick]-e["agent_pose_at_switch"]))))
        candidates = []
        for i, (e, tick) in enumerate(zip(events, event_ticks)):
            index = tick//8
            reason = None
            next_tick = event_ticks[i+1] if i+1 < len(events) else len(poses)-1
            horizon = min(p["horizon_ticks"], next_tick-tick, len(poses)-1-tick)
            if not i:
                reason = "initial_switch_no_OLD"
            elif not control[index]["valid"] or not control[index-1]["valid"]:
                reason = "invalid_or_expired_command"
            elif not e["chunk"]["path_valid"] or not events[i-1]["chunk"]["path_valid"]:
                reason = "invalid_XY_path"
            elif horizon <= 0:
                reason = "no_recorded_horizon"
            if reason:
                exclusions.append({"run_id": run_id, "fresh_id": e["id"], "reason": reason})
                continue
            XYPath(worlds[e["id"]])
            before, after = command(control[index-1]), command(control[index])
            assert e["chunk_transition"]["old_id"] == events[i-1]["id"]
            assert control[index-1]["waypoint_id"] == events[i-1]["id"]
            np.testing.assert_allclose(before, e["chunk_transition"]["actual_command_before"], atol=1e-12, rtol=0)
            np.testing.assert_allclose(after, command(e), atol=1e-12, rtol=0)
            candidates.append({"event_index": i, "fresh_id": e["id"], "old_id": events[i-1]["id"],
                               "abs_dw": abs(float(after[1]-before[1])), "tick": tick, "horizon_ticks": horizon})
        median = float(np.median([c["abs_dw"] for c in candidates]))
        chosen = [min(candidates, key=lambda c: (-c["abs_dw"], c["fresh_id"])),
                  min(candidates, key=lambda c: (abs(c["abs_dw"]-median), c["fresh_id"]))]
        ids = sorted(set(c["fresh_id"] for c in chosen))
        run_records.append({"run_id": run_id, "applied_predictions": len(events),
                            "eligible_pairs": len(candidates), "median_abs_dw": median,
                            "selected_ids": ids, "source_execution_sha": baseline["execution_git_sha"],
                            "source_pose_replay_error": baseline["max_pose_replay_error"],
                            "candidate_rankings": candidates})
        for identifier in ids:
            c = next(c for c in chosen if c["fresh_id"] == identifier)
            i, tick, ticks = c["event_index"], c["tick"], c["horizon_ticks"]
            e, old = events[i], events[i-1]
            boundary = poses[tick]
            raw = rollout(worlds[identifier], boundary, config, p, ticks)
            np.testing.assert_allclose(raw["poses"], poses[tick:tick+ticks+1], atol=p["verification_atol"], rtol=0)
            first_error = float(np.max(abs(np.array(raw["controls"][0]["command_vw"])-command(e))))
            pose_error = float(np.max(abs(np.array(raw["poses"])-poses[tick:tick+ticks+1])))
            max_errors["first_command"] = max(max_errors["first_command"], first_error)
            max_errors["rollout_pose"] = max(max_errors["rollout_pose"], pose_error)
            for r in raw["controls"]:
                actual = control[(tick+r["offset_tick"])//8]
                assert actual["waypoint_id"] == identifier and actual["valid"]
                np.testing.assert_allclose(r["command_vw"], command(actual), atol=p["verification_atol"], rtol=0)
            logged_min = min(r["obstacles"][box]["lower_m"] for r in gaps[tick+1:tick+ticks+1]
                             for box in raw["obstacles"])
            error = abs(raw["minimum_clearance_m"]-logged_min)
            max_errors["rollout_clearance_m"] = max(max_errors["rollout_clearance_m"], error)
            case = {"case_id": f"{run_id}_F{identifier:04d}", "run_id": run_id,
                    "roles": [role for role, selected in zip(p["selection"]["roles"], chosen) if selected["fresh_id"] == identifier],
                    "old_id": old["id"], "fresh_id": identifier, "source_run": str(run),
                    "source_execution_sha": baseline["execution_git_sha"], "config": config,
                    "observation_sim_s": e["observation_sim_s"], "observation_pose": e["observation_pose"],
                    "ready_monotonic_ns": e["ready_monotonic_ns"], "switch_monotonic_ns": e["application_monotonic_ns"],
                    "switch_sim_s": e["application_sim_s"], "boundary": boundary.tolist(),
                    "tick": tick, "horizon_ticks": ticks, "next_switch_tick": next(
                        (t for t in event_ticks if t > tick), None),
                    "old_observation_pose": old["observation_pose"], "old_world_xy": worlds[old["id"]].tolist(),
                    "fresh_local_xy": e["chunk"]["native_local_xy_m"], "fresh_world_xy": worlds[identifier].tolist(),
                    "previous_actual_PP_vw": command(control[tick//8-1]).tolist(),
                    "stored_FRESH_PP_vw": command(e).tolist(),
                    "raw_first_command_error": first_error, "raw_pose_error": pose_error,
                    "raw_clearance_error_m": error}
            all_cases.append(case)
        print(f"preflight {run_id}: {len(candidates)} eligible, selected {ids}", flush=True)
    assert max(max_errors.values()) < p["verification_atol"], max_errors
    for path in [Path(__file__), PROTOCOL.with_name("graph_v2.py"), PROTOCOL.with_name("pure_pursuit.py"),
                 ROOT/"research/nomad_isaac/online_graph_factors.py", ROOT/"research/nomad_isaac/clearance.py",
                 ROOT/"research/nomad_isaac/common.py", ROOT/"research/nomad_isaac/handoff_audit.py"]:
        hashes[str(path)] = sha256_file(path)
    write_json(output/"protocol.json", p)
    write_json(output/"selection.json", {"scope": p["scope"], "selection_git_sha": git("rev-parse", "HEAD"),
        "selection_git_status": git("status", "--porcelain"), "runs": run_records, "exclusions": exclusions,
        "cases": all_cases, "verification_max_errors": max_errors, "input_sha256": hashes})
    print(json.dumps({"selected": len(all_cases), "verification": max_errors}), flush=True)


def execute(output):
    assert not git("status", "--porcelain"), "Commit fixed implementation/protocol before solves"
    p = json.loads(PROTOCOL.read_text())
    assert p == json.loads((output/"protocol.json").read_text())
    selection = json.loads((output/"selection.json").read_text())
    for filename, digest in selection["input_sha256"].items():
        assert sha256_file(Path(filename)) == digest, filename
    (output/"cases").mkdir(exist_ok=False)
    execution = {"git_sha": git("rev-parse", "HEAD"), "python": sys.version,
                 "executable": sys.executable, "numpy": np.__version__, "scipy": scipy.__version__,
                 "platform": platform.platform(), "protocol_sha256": sha256_file(PROTOCOL),
                 "navigation": 0, "inference": 0, "restarts": 0}
    write_json(output/"execution.json", execution)
    records, results = [], []
    for case in selection["cases"]:
        case_id = case["case_id"]
        start = time.perf_counter()
        result = {"case": case, "solver": None, "methods": {}, "rejection": None}
        try:
            graph = GraphV2(np.array(case["fresh_world_xy"]), case["boundary"], case["previous_actual_PP_vw"],
                            case["config"], p, case["horizon_ticks"])
            result["fixed_entry"] = graph.entry
            result["heading_chords"] = graph.chords
            result["methods"]["RAW"] = graph.evaluate("RAW", graph.initial)
            result["methods"]["RIGID"] = graph.evaluate("RIGID", graph.rigid())
            optimized, solver = graph.solve()
            result["solver"] = solver
            result["methods"]["GRAPH"] = graph.evaluate("GRAPH", optimized)
            if not solver["success"]:
                result["rejection"] = "solver_did_not_converge; final iterate is diagnostic only"
        except (ValueError, FloatingPointError) as error:
            result["rejection"] = f"{type(error).__name__}: {error}"
            result["failure_elapsed_s"] = time.perf_counter()-start
            # No restart or substituted success. Preserve RAW even if headings fail.
            if "RAW" not in result["methods"]:
                from nomad_isaac.handoff_audit import path_safety
                xy = np.array(case["fresh_world_xy"])
                raw = rollout(xy, case["boundary"], case["config"], p, case["horizon_ticks"])
                result["RAW_without_auxiliary_headings"] = {"rollout": raw, "native_full": path_safety(xy, case["config"])}
        for name, method in result["methods"].items():
            if name != "RAW":
                method["improvement"] = improvement(method, result["methods"]["RAW"], p,
                    converged=name != "GRAPH" or result["solver"]["success"])
            row = {"case_id": case_id, "roles": "+".join(case["roles"]), "old_id": case["old_id"],
                   "fresh_id": case["fresh_id"], "horizon_ticks": case["horizon_ticks"], "method": name,
                   "switch_abs_dw": method["switch_abs_delta_w_rad_s"], "sign_reversal": method["switch_sign_reversal"],
                   "switch_v": method["switch_command_vw"][0], "switch_w": method["switch_command_vw"][1],
                   "xy_rms_m": method["xy_change_rms_m"], "xy_max_m": method["xy_change_max_m"],
                   "length_ratio": method["length_ratio"], "boundary_gap_m": method["boundary_position_m"],
                   "boundary_heading_rad": method["boundary_heading_rad"],
                   "native_clearance_m": method["native_full"]["obstacle_clearance_m"],
                   "native_safe": method["native_full"]["safe"],
                   "rollout_clearance_m": method["rollout"]["minimum_clearance_m"],
                   "rollout_safe": method["rollout"]["safe"], "overlap": method["rollout"]["geometric_overlap"],
                   "corridor_intrusion": method["rollout"]["corridor_intrusion"],
                   "distance_m": method["rollout"]["distance_m"], "endpoint_stop": method["rollout"]["endpoint_stop"],
                   "qualifies": method.get("improvement", {}).get("qualifies", False),
                   "solver_converged": result["solver"]["success"] if name == "GRAPH" else None,
                   "solve_wall_s": result["solver"]["wall_s"] if name == "GRAPH" else None}
            records.append(row)
        write_json(output/"cases"/f"{case_id}.json", result)
        results.append(result)
        print(json.dumps({"case_id": case_id, "solver": result["solver"], "rejection": result["rejection"],
                          "abs_dw": {k: v["switch_abs_delta_w_rad_s"] for k, v in result["methods"].items()}}), flush=True)
    # Preserve all outcomes, including failures; do not select a best result.
    write_csv(output/"comparison.csv", records)
    summary = {"scope": p["scope"], "execution": execution, "case_count": len(results),
               "eligible_pairs": sum(r["eligible_pairs"] for r in selection["runs"]),
               "verification_max_errors": selection["verification_max_errors"],
               "method_summary": {}, "solve_wall_s": distribution(
                   [r["solver"]["wall_s"] for r in results if r["solver"]]),
               "solver_converged": sum(bool(r["solver"] and r["solver"]["success"]) for r in results),
               "rejections": {r["case"]["case_id"]: r["rejection"] for r in results if r["rejection"]}}
    for name in ("RAW", "RIGID", "GRAPH"):
        subset = [r for r in records if r["method"] == name]
        summary["method_summary"][name] = {
            "n": len(subset),
            **{key: distribution([r[key] for r in subset]) for key in
               ("switch_abs_dw", "xy_rms_m", "boundary_gap_m", "boundary_heading_rad", "length_ratio",
                "native_clearance_m", "rollout_clearance_m", "distance_m")},
            **{key+"_count": sum(r[key] for r in subset) for key in
               ("sign_reversal", "native_safe", "rollout_safe", "overlap", "corridor_intrusion", "endpoint_stop", "qualifies")}}
    assert all(sha256_file(Path(f)) == h for f, h in selection["input_sha256"].items())
    summary["input_hashes_unchanged_after_solves"] = True
    write_json(output/"summary.json", summary)
    print(json.dumps(summary), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    (preflight if args.preflight else execute)(args.output.resolve())


if __name__ == "__main__":
    main()
