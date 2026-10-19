"""Topomap selection and successive FRESH audit around the existing OLD pilot."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

import numpy as np

from .async_report import rows
from .common import local_to_world, original_controller, sha256_file, write_json
from .handoff_audit import boundary_entries, classify, correspondence, path_safety
from .old_rollout_obstacle_report import equivalent, report as old_report
from .old_rollout_placement import place_on_old
from .topomap import candidate_range, select_subgoal
from .topomap_report import validate_map


def table(path, records):
    if not records:
        return
    with path.open("x") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: json.dumps(value, separators=(",", ":")) if isinstance(value, (list, dict)) else value
                         for key, value in record.items()} for record in records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--topomap", type=Path, required=True)
    parser.add_argument("--preservation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    run = args.run.resolve()
    manifest, map_check = validate_map(args.topomap)
    raw = json.loads((run/"summary.json").read_text())
    config = raw["scenario"]
    assert config["goal_mode"] == "topomap"
    assert sha256_file(args.topomap) == config["topomap_manifest_sha256"]
    input_hashes = {str(p.relative_to(run)): sha256_file(p) for p in run.rglob("*")
        if p.is_file() and p.parent.name in (run.name, "dynamic", "model", "raw", "derived", "observations")
        and p.suffix in (".json", ".jsonl", ".npz", ".png", ".csv", ".usda")}
    received, events, workers = [rows(run/name) for name in ("received.jsonl", "events.jsonl", "model/inference.jsonl")]
    assert len(received) == len(workers) == raw["received_count"]
    assert [r["id"] for r in received] == list(range(len(received)))
    assert [w["id"] for w in workers] == [r["id"] for r in received]
    by_event = {event["id"]: event for event in events}
    selections = []
    closest = 0
    for result, worker in zip(received, workers):
        top = result["topomap"]
        assert top == worker["topomap"]
        a, b = candidate_range(closest, len(manifest["nodes"])-1)
        assert top["candidate_ids"] == list(range(a,b+1))
        assert top["previous_closest_node"] == closest
        closest, selected, _ = select_subgoal(top["distances"], a)
        assert (closest, selected) == (top["closest_node"], top["selected_subgoal_id"])
        assert result["goal_sha256"] == manifest["nodes"][selected]["rgb_sha256"]
        if result["id"] in by_event:
            assert by_event[result["id"]]["topomap"] == top
        selections.append({"id": result["id"], "observation_sim_s": result["observation_sim_s"],
            "switch_sim_s": by_event.get(result["id"],{}).get("application_sim_s"),
            "candidate_ids": top["candidate_ids"], "scores": top["distances"], "minimum_score": min(top["distances"]),
            "closest_node": closest, "subgoal_id": selected,
            "parent_reference_node_id": manifest["nodes"][selected]["parent_node_id"],
            "closest_backward": top["closest_moved_backward"], "subgoal_backward": top["subgoal_moved_backward"],
            "subgoal_changed": top["subgoal_changed"], "subgoal_rgb_sha256": result["goal_sha256"]})
    table(args.out/"topomap_selection.csv", selections)
    pilot = old_report(run, args.out/"pilot", args.preservation.resolve())
    result = {"run": str(run), "execution_git_sha": json.loads((run/"provenance.json").read_text())["git_sha"],
        "map": map_check, "topomap_selection_validation": "PASS", "placement_status": pilot["placement_status"],
        "placement": pilot["placement"], "navigation": {key:raw[key] for key in
            ("goal_entry", "termination_reason", "simulation_duration_s", "minimum_goal_distance_m", "final_pose",
             "inference_count", "received_count", "applied_waypoints", "combined_avoidance_success")},
        "scope": "2s static reference Topomap; one navigation; original placement/PD; no correction or reranking",
        "selection_count": len(selections), "classification": [],
        "limitations": ["Single nonpaired pilot; fixed-goal comparison has different RGB/path/seed association/obstacle world position",
            "Native full, prefix and actual PD arc are distinct; no intrinsic waypoint yaw/time",
            "Examined connectors are offline geometric diagnostics, not paths executed by the original PD",
            "Eight-sample safety uses exact scene geometry offline; unselected samples were not executed"]}
    decision = raw["dynamic_obstacle"]["placement"]
    if decision is not None:
        recreated = place_on_old(config, decision["pose"], *decision["old_command_vw"], decision["old_id"],
                                 decision["old_command_valid"], decision["old_remaining_timeout_s"])
        equivalent(recreated, {k:decision[k] for k in recreated})
        result["placement_recomputed"] = "PASS"
    if pilot["placement_status"] != "PLACED":
        result["classification"] = ["PLACEMENT_INFEASIBLE" if pilot["placement_status"] == "PLACEMENT_INFEASIBLE" else "INSUFFICIENT_EVIDENCE"]
        result["reason"] = "No obstacle appearance / visible FRESH handoff to evaluate; no retry"
        result["runtime"] = pilot["runtime"]
    else:
        native = pilot["native_audit"]
        dynamic = decision["obstacle"]
        both = {**config, "obstacles":[*config["obstacles"],dynamic]}
        solo = {**config, "obstacles":[dynamic]}
        controller = original_controller()
        old_id, fresh_id = pilot["old_id"], pilot["fresh_id"]
        result.update({"old_id":old_id, "first_fresh_id":fresh_id, "first_fresh_applied":pilot["fresh_applied"],
            "old_topomap":received[old_id]["topomap"],
            "first_fresh_topomap":received[fresh_id]["topomap"] if fresh_id is not None else None,
            "counterfactual_first_contact":pilot["counterfactual_first_contact"], "timing":native["timing"],
            "old_native_safety":native["old_safety"], "first_fresh_native_safety":native["fresh_safety"],
            "pre_fresh_actual_execution":native["pre_fresh_execution"], "first_fresh_actual_execution":native["fresh_execution"],
            "first_handoff_geometry":native["geometry"], "first_graph_verdict":native["graph_verdict"],
            "first_visible_observation":native["first_visible_observation"], "fresh_history_ids":native["fresh_history_ids"],
            "visible_history_ids":native["visible_history_ids"],
            "fresh_history_sha256":received[fresh_id]["history_sha256"] if fresh_id is not None else None,
            "runtime":native["runtime"], "validation":pilot["validation"],
            "later_execution":pilot["later_execution"], "figure":"pilot/old_rollout_handoff.svg"})
        def native_sample(identifier, sample):
            with np.load(run/f"model/derived/{identifier:04d}.npz",allow_pickle=False) as z:
                assert z["metric"].shape == (8,8,2)
                local = z["metric"][sample].copy()
            world = local_to_world(local, received[identifier]["observation_pose"])
            checks = {scope:{part:path_safety(points, scene) for part,points in (
                ("full",world),("prefix",world[:3]),
                ("origin_prefix",np.vstack([received[identifier]["observation_pose"][:2],world[:3]])))}
                for scope,scene in (("all",both),("dynamic",solo))}
            return local,world,checks
        samples=[]
        if fresh_id is not None:
            for sample in range(8):
                local,world,checks=native_sample(fresh_id,sample)
                v,w=controller(local[2].tolist())
                samples.append({"prediction_id":fresh_id,"sample":sample,"actually_selected":sample==0,
                    "dx_m":float(local[2,0]),"dy_m":float(local[2,1]),"v_m_s":float(v),"w_rad_s":float(w),
                    "turn":"left" if w>0 else "right" if w<0 else "straight",
                    **{f"{scope}_{part}_{key}":value for scope,parts in checks.items() for part,metrics in parts.items()
                       for key,value in metrics.items() if key in ("safe","obstacle_clearance_m","corridor_clearance_m")}})
            result["first_fresh_samples"]={"full_safe":sum(r["all_full_safe"] for r in samples),
                "prefix_safe":sum(r["all_prefix_safe"] for r in samples),
                "origin_prefix_safe":sum(r["all_origin_prefix_safe"] for r in samples),
                "turn_counts":dict(Counter(r["turn"] for r in samples)),"sample0":samples[0]}
            np.testing.assert_array_equal([samples[0]["dx_m"],samples[0]["dy_m"]],received[fresh_id]["selected_waypoint_m"])
        table(args.out/"first_fresh_samples.csv",samples)
        with (run/"agent_trajectory.csv").open() as stream: trace=list(csv.DictReader(stream))
        pose=np.array([[float(r[k]) for k in ("x_m","y_m","yaw_rad")] for r in trace])
        static=rows(run/"clearance.jsonl"); dyn=rows(run/"dynamic/clearance.jsonl")
        hz=config["integration_hz"]; spawn_tick=decision["decision_tick"]
        protocol=json.loads(Path(__file__).with_name("async_handoff_protocol.json").read_text())
        index_by_id={e["id"]:i for i,e in enumerate(events)}
        safety_by_id={}; successive=[]
        visible_ids={r["id"] for r in rows(run/"requests.jsonl") if any(d["visible"] for d in r["history_dynamic"])}
        for rec in received:
            identifier=rec["id"]
            if identifier<old_id:continue
            local,world,checks=native_sample(identifier,0); safety_by_id[identifier]=checks["all"]["full"]["safe"]
            v,w=controller(local[2].tolist()); event=by_event.get(identifier)
            record={"id":identifier,"includes_visible_rgb":identifier in visible_ids,"applied":event is not None,
                "obs_sim_s":rec["observation_sim_s"],"switch_sim_s":event["application_sim_s"] if event else None,
                "closest":rec["topomap"]["closest_node"],"subgoal":rec["topomap"]["selected_subgoal_id"],
                "closest_backward":rec["topomap"]["closest_moved_backward"],"subgoal_backward":rec["topomap"]["subgoal_moved_backward"],
                "v":float(v),"w":float(w),"dx":float(local[2,0]),"dy":float(local[2,1]),
                "observation_pose":rec["observation_pose"],"switch_pose":event["agent_pose_at_switch"] if event else None,
                **{f"{scope}_{part}_{key}":value for scope,parts in checks.items() for part,metrics in parts.items()
                   for key,value in metrics.items() if key in ("safe","obstacle_clearance_m","corridor_clearance_m")},
                "previous_applied_id":None,"turn_reversal":None,"same_subgoal":None,"safe_to_unsafe_native":None,
                "execution_dynamic_clearance_m":None,"execution_static_clearance_m":None,"execution_corridor_clearance_m":None,
                "execution_safe":None,"execution_overlap":None,"handoff_class":None,
                "correspondence_valid":None,"entry_distance_m":None,"entry_heading_deg":None,
                "connector_clearance_m":None,"connector_corridor_m":None,"safe_entries":None}
            if event:
                j=index_by_id[identifier]; start=max(spawn_tick,round(event["application_sim_s"]*hz))
                end=round(events[j+1]["application_sim_s"]*hz) if j+1<len(events) else len(pose)-1
                if end>start:
                    dd=dyn[start-spawn_tick+1:end-spawn_tick+1]; ss=static[start+1:end+1]
                    assert all(int(r["incoming_waypoint_id"])==identifier for r in trace[start+1:end+1])
                    record.update(execution_dynamic_clearance_m=min(r["lower_m"] for r in dd),
                        execution_static_clearance_m=min(r["lower_m"] for r in ss),
                        execution_corridor_clearance_m=min(r["corridor_lower_m"] for r in ss),
                        execution_overlap=any(r["geometric_overlap"] for r in dd+ss))
                    record["execution_safe"]=(min(record["execution_dynamic_clearance_m"],record["execution_static_clearance_m"])>=.02
                                              and record["execution_corridor_clearance_m"]>0)
                if j and identifier!=old_id:
                    previous=events[j-1]; _,old_world,old_checks=native_sample(previous["id"],0)
                    b=np.array(event["agent_pose_at_switch"])
                    entry=boundary_entries(world,b,both,protocol); overlap=correspondence(old_world,world,b,protocol)
                    selected=entry.get("chosen",{})
                    record.update(previous_applied_id=previous["id"],turn_reversal=bool(previous["w_rad_s"]*w<0),
                        same_subgoal=previous["topomap"]["selected_subgoal_id"]==rec["topomap"]["selected_subgoal_id"],
                        safe_to_unsafe_native=bool(old_checks["all"]["full"]["safe"] and not checks["all"]["full"]["safe"]),
                        handoff_class=classify(checks["all"]["full"],overlap,entry,protocol),
                        correspondence_valid=overlap["valid"],entry_distance_m=selected.get("distance_m"),
                        entry_heading_deg=selected.get("boundary_tangent_deg"),connector_clearance_m=selected.get("obstacle_clearance_m"),
                        connector_corridor_m=selected.get("corridor_clearance_m"),safe_entries=entry.get("safe_count"))
            successive.append(record)
        table(args.out/"successive_fresh.csv",successive)
        post=[r for r in successive if r["includes_visible_rgb"]]
        result["successive_summary"]={"received_count":len(post),"applied_count":sum(r["applied"] for r in post),
            "same_subgoal_turn_reversals":[r["id"] for r in post if r["turn_reversal"] and r["same_subgoal"]],
            "changed_subgoal_turn_reversals":[r["id"] for r in post if r["turn_reversal"] and not r["same_subgoal"]],
            "safe_to_unsafe_native_ids":[r["id"] for r in post if r["safe_to_unsafe_native"]],
            "unsafe_full_ids":[r["id"] for r in post if not r["all_full_safe"]],
            "unsafe_prefix_ids":[r["id"] for r in post if not r["all_prefix_safe"]],
            "unsafe_execution_ids":[r["id"] for r in post if r["execution_safe"] is False],
            "safe_native_unsafe_execution_ids":[r["id"] for r in post if r["all_full_safe"] and r["execution_safe"] is False],
            "qualified_geometry_ids":[r["id"] for r in post if r["handoff_class"]=="POTENTIAL_RECONCILIATION_CASE"],
            "terminal_unapplied_ids":[r["id"] for r in post if not r["applied"]]}
        first_safe=pilot["first_fresh_full_safe"]
        result["classification"]=["INSUFFICIENT_EVIDENCE" if first_safe is None else
            "UNSAFE_OLD_SAFE_FRESH" if first_safe else "UNSAFE_OLD_UNSAFE_FRESH"]
        if first_safe and any(r["id"]>fresh_id and not r["all_full_safe"] for r in post):result["classification"].append("LATER_UNSAFE_FRESH")
        if (native["pre_fresh_execution"]["safe"] is False or any(r["execution_safe"] is False for r in post)
                or fresh_id is not None and not pilot["fresh_applied"]):result["classification"].append("HANDOFF_OR_EXECUTION_FAILURE")
    assert all(sha256_file(run/name)==digest for name,digest in input_hashes.items())
    write_json(args.out/"input_hashes.json",input_hashes)
    write_json(args.out/"summary.json",result)
    print(json.dumps({"classification":result["classification"],"navigation":result["navigation"]}))


if __name__ == "__main__":
    main()
