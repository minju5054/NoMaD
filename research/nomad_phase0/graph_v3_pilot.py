"""One frozen offline Graph v3 evaluation; no navigation, inference or restarts."""
import argparse
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy

from nomad_isaac.common import sha256_file, write_json
from nomad_isaac.handoff_audit import path_safety
from .graph_v2 import entry_pose, fixed_entry
from .graph_v2_pilot import distribution, git, write_csv
from .graph_v3 import FLAGS, GraphV3, qualifies, rollout, side_labels
from .graph_v3_data import build_selection

PROTOCOL = Path(__file__).with_name("graph_v3_protocol.json")
METHODS = ("RAW", "RAW+Speed", "RAW+Rate limit", "RIGID", "Graph v2", "Graph v3")


def preflight(out):
    assert not out.exists(), "Never overwrite an existing experiment"
    p = json.loads(PROTOCOL.read_text())
    assert sha256_file(PROTOCOL.with_name("graph_v2_protocol.json")) == p["graph_v2_protocol_sha256"]
    selection = build_selection(p)
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"protocol.json", p)
    write_json(out/"selection.json", selection)
    print(json.dumps({"preflight": "PASS", "cases": selection["count"],
                      "datasets": {k: sum(c["dataset"] == k for c in selection["cases"]) for k in ("a_S0", "b_S1_P0", "c_stress")},
                      "raw_PP_max_error": max(v["raw_first_PP_error"] or 0. for v in selection["verification"])}), flush=True)


def evaluate(xy, case, protocol, mode):
    raw = np.array(case["fresh_world_xy"]); xy = np.array(xy)
    e = fixed_entry(raw, case["boundary"])
    point = (1-e["fraction"])*xy[e["a"]]+e["fraction"]*xy[e["b"]]
    result = {"world_xy_m": xy.tolist(), "xy_rms_m": float(np.sqrt(np.mean(np.sum((xy-raw)**2, axis=1)))),
        "xy_max_m": float(np.max(np.linalg.norm(xy-raw, axis=1))),
        "path_length_ratio": float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum()/np.linalg.norm(np.diff(raw, axis=0), axis=1).sum()),
        "boundary_gap_m": float(np.linalg.norm(point-np.array(case["boundary"])[:2])),
        "fixed_entry_xy_m": point.tolist(), "native_full": path_safety(xy, case["evaluation_config"]),
        "native_prefix": path_safety(xy[:3], case["evaluation_config"]),
        "native_side": side_labels(xy, case["evaluation_config"])}
    for horizon, ticks, chunk in (("H_switch", case["horizon_ticks"], False),
                                 ("H_chunk", round(protocol["chunk_max_s"]*72), True)):
        result[horizon] = rollout(xy, case["boundary"], case["previous_actual_vw"],
                                 case["evaluation_config"], protocol, ticks, mode, chunk)
    command = result["H_switch"]["first_command_vw"]
    result["switch_abs_delta_w_rad_s"] = abs(command[1]-case["previous_actual_vw"][1]) if command else None
    result["switch_sign_reversal"] = bool(command and command[1]*case["previous_actual_vw"][1] < -1e-18)
    return result


def rows_for_case(result, p):
    case, methods = result["case"], result["methods"]
    raw = methods["RAW"]; speed = methods["RAW+Speed"]
    table = []
    for name, method in methods.items():
        converged = name not in ("Graph v2", "Graph v3") or method["solver"]["success"]
        for horizon in ("H_switch", "H_chunk"):
            r = method[horizon]
            raw_comparison = qualifies(method, raw, raw, p, horizon, converged)
            speed_comparison = qualifies(method, speed, raw, p, horizon, converged)
            method.setdefault("qualification", {})[horizon] = {"vs_RAW": raw_comparison, "vs_RAW+Speed": speed_comparison}
            raw_unsafe = not (raw["native_full"]["safe"] and raw[horizon]["safe"])
            safe = method["native_full"]["safe"] and r["safe"]
            completed = r["endpoint_reached"] if horizon == "H_chunk" else r["executed_ticks"] == r["requested_ticks"]
            row = {"case_id": case["case_id"], "dataset": case["dataset"], "fresh_id": case["fresh_id"],
                "horizon": horizon, "method": name, "source_controller": case["source_controller"],
                "right_censored_switch": case["right_censored"], "dynamic_public": "DynamicObstacle" in case["public_obstacle_ids"],
                "switch_abs_dw": method["switch_abs_delta_w_rad_s"], "switch_sign_reversal": method["switch_sign_reversal"],
                "switch_v": r["first_command_vw"][0] if r["first_command_vw"] else None,
                "switch_w": r["first_command_vw"][1] if r["first_command_vw"] else None,
                "xy_rms_m": method["xy_rms_m"], "xy_max_m": method["xy_max_m"],
                "path_length_ratio": method["path_length_ratio"], "boundary_gap_m": method["boundary_gap_m"],
                "native_clearance_m": method["native_full"]["obstacle_clearance_m"],
                "native_corridor_m": method["native_full"]["corridor_clearance_m"], "native_safe": method["native_full"]["safe"],
                "rollout_clearance_m": r["minimum_clearance_m"], "rollout_corridor_m": r["minimum_corridor_m"],
                "rollout_safe": r["safe"], "overlap": r["geometric_overlap"], "corridor_intrusion": r["corridor_intrusion"],
                "joint_safe": safe, "complete_and_joint_safe": safe and completed and converged,
                "raw_unsafe_to_safe": raw_unsafe and safe and completed and converged,
                "raw_joint_unsafe": raw_unsafe, "duration_s": r["duration_s"], "distance_m": r["distance_m"],
                "mean_speed_m_s": r["mean_speed_m_s"], "stop_or_truncated": r["stop_or_truncated"],
                "endpoint_reached": r["endpoint_reached"], "chunk_timeout": r["chunk_timeout"],
                "qualifies_vs_RAW": raw_comparison["qualifies"], "qualifies_vs_Speed": speed_comparison["qualifies"],
                "native_side": json.dumps({k: v["status"] for k, v in method["native_side"].items()}),
                "rollout_side": json.dumps({k: v["status"] for k, v in r["executed_side"].items()}),
                "solver_converged": converged, "solve_wall_s": method.get("solver", {}).get("wall_s"),
                "solve_time_source": "historical_reuse" if name == "Graph v2" else "measured" if name == "Graph v3" else "NOT_APPLICABLE",
                "control_ticks": r["control_ticks"], "integration_intervals": r["executed_ticks"]}
            for flag in FLAGS:
                row[flag+"_control_ticks"] = r["flag_control_ticks"][flag]
                row[flag+"_intervals"] = r["flag_integration_intervals"][flag]
            table.append(row)
    return table


def aggregate(table, results, p, selection, execution):
    summary = {"scope": p["scope"], "execution": execution, "cases": len(results),
        "dataset_counts": {d: sum(c["dataset"] == d for c in selection["cases"]) for d in ("a_S0", "b_S1_P0", "c_stress")},
        "verification": selection["verification"], "comparison": {},
        "graph_v3_solve_wall_s": distribution([r["solver"]["wall_s"] for r in results if r["solver"]]),
        "graph_v3_over_100ms_count": sum(r["solver"]["wall_s"] > .1 for r in results if r["solver"]),
        "graph_v3_attempt_count": sum(r["solve_attempted"] for r in results),
        "graph_v3_converged": sum(bool(r["solver"] and r["solver"]["success"]) for r in results),
        "rejections": {r["case"]["case_id"]: r["rejections"] for r in results if r["rejections"]},
        "public_dynamic_denied_cases": [c["case_id"] for c in selection["cases"] if c["geometry_information"] and "DynamicObstacle" not in c["public_obstacle_ids"]],
        "right_censored_cases": [c["case_id"] for c in selection["cases"] if c["right_censored"]],
        "graph_v2_missing": [r["case"]["case_id"] for r in results if "Graph v2" not in r["methods"]]}
    n = summary["graph_v3_solve_wall_s"]["n"]
    summary["graph_v3_over_100ms_ratio"] = summary["graph_v3_over_100ms_count"]/n if n else None
    for dataset in summary["dataset_counts"]:
        summary["comparison"][dataset] = {}
        for horizon in ("H_switch", "H_chunk"):
            methods = {}
            for name in METHODS:
                subset = [r for r in table if r["dataset"] == dataset and r["horizon"] == horizon and r["method"] == name]
                entry = {"n": len(subset), "status": "EVALUATED" if subset else "NOT_AVAILABLE"}
                for key in ("switch_abs_dw", "xy_rms_m", "path_length_ratio", "boundary_gap_m", "native_clearance_m",
                            "rollout_clearance_m", "distance_m", "mean_speed_m_s", "duration_s"):
                    entry[key] = distribution([r[key] for r in subset if r[key] is not None])
                for key in ("native_safe", "rollout_safe", "overlap", "corridor_intrusion", "joint_safe", "complete_and_joint_safe",
                            "raw_unsafe_to_safe", "raw_joint_unsafe", "stop_or_truncated", "endpoint_reached", "chunk_timeout",
                            "qualifies_vs_RAW", "qualifies_vs_Speed", "switch_sign_reversal"):
                    entry[key+"_count"] = sum(bool(r[key]) for r in subset)
                entry["flags"] = {}
                for flag in FLAGS:
                    count = sum(r[flag+"_control_ticks"] for r in subset); ticks = sum(r["control_ticks"] for r in subset)
                    intervals = sum(r[flag+"_intervals"] for r in subset); total = sum(r["integration_intervals"] for r in subset)
                    entry["flags"][flag] = {"control_ticks": count, "control_total": ticks, "control_ratio": count/ticks if ticks else None,
                        "integration_intervals": intervals, "integration_total": total, "integration_ratio": intervals/total if total else None}
                methods[name] = entry
            summary["comparison"][dataset][horizon] = methods
    summary["plateau"] = [r for r in table if r["case_id"] in p["plateau_case_ids"] and r["method"] in ("RAW", "RAW+Speed", "Graph v3")]
    summary["limitations"] = ["Fixed saved B, no solve-time motion or online application",
        "S0 selected maxima/median, S1 contiguous window, six selected historical failures: not unbiased performance samples",
        "Stress RAW is PP counterfactual after actual PD OLD; no assertion that PP reproduces the historical PD collision",
        "Graph v2 S0 paths reused from16-tick solves, re-evaluated at new horizons; no v2 result for S1/stress",
        "H_chunk is unexecuted frozen-path continuation without future FRESH or1s timeout, max60s",
        "Flags diagnose curvature/acceleration limits; safety comes from native geometry and actual swept rollout, not flags",
        "Arclength speed samples depend on B and previous speed; repeated arclength entries are preserved, not native timestamps"]
    return summary


def execute(out):
    assert not git("status", "--porcelain"), "Commit code and protocol before the one execution"
    p = json.loads(PROTOCOL.read_text())
    assert p == json.loads((out/"protocol.json").read_text())
    selection = json.loads((out/"selection.json").read_text())
    assert all(sha256_file(Path(f)) == h for f, h in selection["input_sha256"].items())
    (out/"cases").mkdir(exist_ok=False)
    execution = {"git_sha": git("rev-parse", "HEAD"), "git_status": "", "python": sys.version,
        "executable": sys.executable, "numpy": np.__version__, "scipy": scipy.__version__, "platform": platform.platform(),
        "protocol_sha256": sha256_file(PROTOCOL), "navigation": 0, "inference": 0, "restarts": 0}
    write_json(out/"execution.json", execution)
    results = []; table = []
    for case in selection["cases"]:
        start = time.perf_counter()
        result = {"case": case, "methods": {}, "solver": None, "solve_attempted": False, "rejections": {}}
        raw = np.array(case["fresh_world_xy"])
        paths = {"RAW": (raw, "raw"), "RAW+Speed": (raw, "speed"), "RAW+Rate limit": (raw, "rate")}
        graph = None
        try:
            graph = GraphV3(raw, case["boundary"], case["previous_actual_vw"], case["public_config"], p, case["horizon_ticks"])
            result.update(fixed_entry=graph.entry, heading_chords=graph.chords, public_side_factors=graph.sides)
            paths["RIGID"] = (graph.rigid()[:, :2], "raw")
            result["solve_attempted"] = True
            solve_start = time.perf_counter()
            corrected, result["solver"] = graph.solve()  # Exactly once; never restart/tune.
            paths["Graph v3"] = (corrected[:, :2], "speed")
            result["graph_v3_auxiliary_headings"] = corrected[:, 2].tolist()
            if not result["solver"]["success"]:
                result["rejections"]["Graph v3"] = "NONCONVERGED_final_iterate_diagnostic_only"
        except (ValueError, FloatingPointError) as exc:
            result["rejections"]["Graph v3"] = str(exc)
            result["failed_solve_wall_s"] = time.perf_counter()-solve_start if result["solve_attempted"] else None
        if case["graph_v2_saved_path"]:
            saved = json.loads(Path(case["graph_v2_saved_path"]).read_text())
            if "GRAPH" in saved["methods"]:
                paths["Graph v2"] = (np.array(saved["methods"]["GRAPH"]["world_xy_m"]), "raw")
                result["graph_v2_original_horizon_ticks"] = saved["case"]["horizon_ticks"]
        for name, (xy, mode) in paths.items():
            method = evaluate(xy, case, p, mode)
            if name == "Graph v3":
                method["solver"] = result["solver"]
            elif name == "Graph v2":
                method["solver"] = saved["solver"]
            result["methods"][name] = method
        table.extend(rows_for_case(result, p))
        # Preserve exact control states/flags at9Hz and speed-profile samples.
        # Dense virtual poses are reproducible from those commands, not needed in JSON.
        for method in result["methods"].values():
            for horizon in ("H_switch", "H_chunk"):
                method[horizon].pop("poses")
        write_json(out/"cases"/(case["case_id"]+".json"), result)
        results.append(result)
        print(json.dumps({"case": case["case_id"], "completed": len(results), "total": len(selection["cases"]),
            "solve_wall_s": result["solver"]["wall_s"] if result["solver"] else None,
            "converged": result["solver"]["success"] if result["solver"] else False,
            "elapsed_s": time.perf_counter()-start, "rejections": result["rejections"]}), flush=True)
    write_csv(out/"comparison.csv", table)
    summary = aggregate(table, results, p, selection, execution)
    assert all(sha256_file(Path(f)) == h for f, h in selection["input_sha256"].items())
    summary["input_hashes_unchanged"] = True
    write_json(out/"summary.json", summary)
    write_csv(out/"plateau.csv", summary["plateau"])
    print(json.dumps({"finished": True, "cases": len(results), "converged": summary["graph_v3_converged"],
                      "solve_wall_s": summary["graph_v3_solve_wall_s"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["preflight", "execute"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    (preflight if args.mode == "preflight" else execute)(args.output)
