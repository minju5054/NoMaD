"""Offline Topomap audit, existing runtime validation, and one XY figure."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .async_report import validate, rows, stats
from .clearance import corridor_clearance, configured_obstacles, obstacle_bounds, single_obstacle_config
from .common import ROOT, local_to_world, sha256_file, write_json
from .topomap import candidate_range, select_subgoal, load_map, reference_rows


def validate_map(path):
    manifest = json.loads(path.read_text())
    images, _ = load_map(path)
    reference = Path(manifest["source_run"])
    for name, digest in manifest["reference_sha256"].items():
        assert sha256_file(reference/name) == digest
    expected = reference_rows(reference, manifest["scenario"])
    assert len(expected) == len(images) == 26
    for node, (index, row) in zip(manifest["nodes"], expected):
        assert node["reference_pose_row"] == index
        assert node["simulation_time_s"] == float(row["simulation_time_s"])
        np.testing.assert_array_equal(node["world_pose"], [float(row[k]) for k in ("x_m", "y_m", "yaw_rad")])
        assert node["usd_pose_max_error"] < 1e-10
    return manifest, {"nodes": len(images), "rgb_file_and_pixel_hashes": "PASS",
                      "pose_and_tick_correspondence": "PASS", "reference_source_hashes": "PASS",
                      "maximum_usd_pose_error": max(r["usd_pose_max_error"] for r in manifest["nodes"])}


def comparison_record(run):
    summary = json.loads((run/"summary.json").read_text())
    inference = rows(run/"model/inference.jsonl")
    events = rows(run/"events.jsonl")
    switches = np.array([r["application_sim_s"] for r in events])
    return {"run": str(run), "goal_entry": summary["goal_entry"], "termination": summary["termination_reason"],
            "minimum_goal_distance_m": summary["minimum_goal_distance_m"],
            "duration_sim_s": summary["simulation_duration_s"], "inferences": len(inference), "switches": len(events),
            "warm_inference_ms": stats([r["inference_ms"] for r in inference[1:]]),
            "switch_interval_sim_s": stats(np.diff(switches)),
            "switch_frequency_hz_after_first": (len(switches)-1)/(switches[-1]-switches[0]) if len(switches)>1 else None,
            "observation_to_switch_wall_ms": stats([(e["application_monotonic_ns"]-e["observation_monotonic_ns"])/1e6 for e in events]),
            "obstacle_evaluation": summary["obstacle_evaluation"],
            "timeout_episodes": summary["waypoint_timeout_episodes"], "busy_skips": summary["busy_observation_skips"],
            "missed_slots": summary["missed_capture_slots"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--topomap", type=Path, required=True)
    parser.add_argument("--gpu-validation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest, map_check = validate_map(args.topomap)
    gpu_check = json.loads(args.gpu_validation.read_text())
    assert gpu_check["status"] == "PASS" and gpu_check["map_manifest_sha256"] == sha256_file(args.topomap)
    runtime = validate(args.run, ROOT.parent/"artifacts/isaac6/two_obstacles_01", args.out/"runtime_validation")
    inference = rows(args.run/"model/inference.jsonl")
    received = rows(args.run/"received.jsonl")
    events = rows(args.run/"events.jsonl")
    observations = {r["observation_id"]: r for r in rows(args.run/"observations.jsonl") if "observation_id" in r}
    config = json.loads((args.run/"scenario.json").read_text())
    assert config["goal_mode"] == "topomap" and "dynamic_obstacle" not in config
    assert config["topomap_manifest_sha256"] == sha256_file(args.topomap)
    with (args.run/"agent_trajectory.csv").open() as stream:
        trace = list(csv.DictReader(stream))
    poses = np.array([[float(r[k]) for k in ("x_m", "y_m", "yaw_rad")] for r in trace])
    clearance = rows(args.run/"clearance.jsonl")
    corridor_error = 0.
    for i in range(1, len(trace)):
        v, w = float(trace[i]["v_m_s"]), float(trace[i]["w_rad_s"])
        gap = corridor_clearance(poses[i-1], poses[i], v, w, 1/72, config["corridor"], config["agent_radius_m"])
        corridor_error = max(corridor_error, abs(gap-clearance[i]["corridor_lower_m"]))
    assert corridor_error < 1e-12
    # Reconstruct every actual worker input from saved RGB, independently of its metadata.
    frame_cache = {}
    for identifier, row in observations.items():
        with Image.open(args.run/row["rgb_file"]) as image:
            frame = np.array(image)
        assert hashlib.sha256(frame.tobytes()).hexdigest() == row["frame_sha256"]
        frame_cache[identifier] = frame
    closest, previous_subgoal = 0, None
    table, goal_events = [], []
    event_by_id = {r["id"]:r for r in events}
    for i, row in enumerate(inference):
        t = row["topomap"]
        a, b = candidate_range(closest, len(manifest["nodes"])-1)
        assert (a,b) == (t["candidate_start"], t["candidate_end_inclusive"])
        assert t["candidate_ids"] == list(range(a,b+1)) and len(t["distances"]) == b-a+1
        new_closest, selected, _ = select_subgoal(t["distances"], a)
        assert new_closest == t["closest_node"] and selected == t["selected_subgoal_id"]
        assert t["previous_closest_node"] == closest and t["previous_subgoal_id"] == previous_subgoal
        assert t["closest_moved_backward"] == (new_closest<closest)
        assert t["subgoal_changed"] == (selected!=previous_subgoal)
        assert t["subgoal_moved_backward"] == (previous_subgoal is not None and selected<previous_subgoal)
        assert t["topomap_goal_node_reached"] == (new_closest==len(manifest["nodes"])-1)
        assert t["diffusion_passes"] == 1 and t["diffusion_steps"] == 10
        expected_hashes = {k: manifest["nodes"][selected][k] for k in ("rgb_file", "png_sha256", "rgb_sha256")}
        assert expected_hashes == t["selected_subgoal_image"]
        assert row["goal_sha256"] == expected_hashes["rgb_sha256"]
        assert received[i]["topomap"] == t
        if i in event_by_id:
            assert event_by_id[i]["topomap"] == t
        history = np.stack([frame_cache[index] for index in row["history_observation_ids"]])
        assert hashlib.sha256(history.tobytes()).hexdigest() == row["history_sha256"]
        assert row["inference_start_monotonic_ns"] <= t["selection_monotonic_ns"] <= row["ready_monotonic_ns"]
        table.append({"request_id":i,"observation_sim_s":row["observation_sim_s"],
                      "candidate_start":a,"candidate_end":b,"distance_scores":json.dumps(t["distances"]),
                      "closest_node":new_closest,"subgoal_id":selected,"subgoal_changed":t["subgoal_changed"],
                      "closest_backward":t["closest_moved_backward"],"subgoal_backward":t["subgoal_moved_backward"],
                      "selection_monotonic_ns":t["selection_monotonic_ns"],
                      "switch_sim_s":event_by_id[i]["application_sim_s"] if i in event_by_id else None,
                      "subgoal_rgb_sha256":expected_hashes["rgb_sha256"],"inference_ms":row["inference_ms"]})
        if t["topomap_goal_node_reached"]:
            goal_events.append({"id":i,"observation_sim_s":row["observation_sim_s"],"applied":i in event_by_id})
        closest, previous_subgoal = new_closest, selected
    with (args.out/"topomap_selection.csv").open("x") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(table[0]),lineterminator="\n")
        writer.writeheader();writer.writerows(table)
    # Descriptive executed-command changes: selected targets, never physical waypoint correspondence.
    revisions, obstacle_changes = [], {"StaticObstacle1":[],"StaticObstacle2":[]}
    for old, fresh in zip(events[:-1],events[1:]):
        points=[]
        for e in (old,fresh):
            with np.load(args.run/f"model/derived/{e['id']:04d}.npz",allow_pickle=False) as data:
                points.append(local_to_world(data["metric"][0],np.array(e["observation_pose"]))[2])
        reversal = bool(old["w_rad_s"]*fresh["w_rad_s"]<0)
        change={"old_id":old["id"],"fresh_id":fresh["id"],"switch_sim_s":fresh["application_sim_s"],
                "switch_pose":fresh["agent_pose_at_switch"],"old_w":old["w_rad_s"],"fresh_w":fresh["w_rad_s"],
                "turn_sign_reversal":reversal,"selected_world_target_revision_m":float(np.linalg.norm(points[1]-points[0])),
                "old_subgoal":old["topomap"]["selected_subgoal_id"],"fresh_subgoal":fresh["topomap"]["selected_subgoal_id"]}
        revisions.append(change)
        x=fresh["agent_pose_at_switch"][0]
        for key,lower,upper in (("StaticObstacle1",1.,2.),("StaticObstacle2",2.5,3.6)):
            if lower<=x<=upper:
                obstacle_changes[key].append(change)
    fixed=comparison_record(Path(manifest["source_run"]))
    current=comparison_record(args.run)
    report={"topomap_technical_validation":"PASS" if runtime["async_reproduction"]=="PASS" else "LIMITED_RUNTIME",
            "map":map_check,"gpu_equivalence":gpu_check,"runtime_validation":runtime["validation"],
            "runtime_async_reproduction":runtime["async_reproduction"],"pacing":runtime["pacing"],
            "clock_mapping_pass":runtime["inference_clock_mapping_pass"],"switch_tick_mismatch_ids":runtime["switch_tick_mismatch_ids"],
            "old_motion_during_inference":runtime["old_motion_full_intervals_only"],
            "topomap_selection_validation":"PASS", "all_worker_history_rgb_hashes":"PASS",
            "corridor_recompute_max_error_m":corridor_error,"topomap_goal_node_events":goal_events,
            "last_closest_node":closest,"goal_node":len(manifest["nodes"])-1,
            "subgoal_update_count":sum(r["subgoal_changed"] for r in table),
            "closest_backward_count":sum(r["closest_backward"] for r in table),
            "subgoal_backward_count":sum(r["subgoal_backward"] for r in table),
            "candidate_count":stats([r["candidate_end"]-r["candidate_start"]+1 for r in table]),
            "warm_candidate_encode_selection_ms":stats([r["topomap"]["candidate_encoding_and_selection_ms"] for r in inference[1:]]),
            "warm_diffusion_action_ms":stats([r["topomap"]["diffusion_and_action_ms"] for r in inference[1:]]),
            "fixed_goal_reference":fixed,"topomap_run":current,
            "executed_turn_sign_reversals":sum(r["turn_sign_reversal"] for r in revisions),
            "selected_world_target_revision_m":stats([r["selected_world_target_revision_m"] for r in revisions]),
            "obstacle_neighborhoods":{k:{"pairs":len(v),"reversals":[r for r in v if r["turn_sign_reversal"]],
                "target_revision_m":stats([r["selected_world_target_revision_m"] for r in v])} for k,v in obstacle_changes.items()},
            "runtime_source_sha":json.loads((args.run/"provenance.json").read_text())["git_sha"],
            "limitations":["Reference route from prior successful static execution; not unseen-scene generalization",
                "Learned distance scores are not metric world distance; fixed 1s map cadence/threshold uncalibrated",
                "Different RGB/observation timing and seed association: whole-run change is not a paired causal comparison",
                "Target revision is a control-target change, not same-index physical trajectory correspondence",
                "No dynamic obstacle, graph, recovery, reranking, smoothing or new controller"]}
    write_json(args.out/"summary.json",report)
    # One scientific figure: reference node XY and actual executed path.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    plt.rcParams["svg.fonttype"]="none"
    fig,ax=plt.subplots(figsize=(11,5))
    for box in configured_obstacles(config):
        lower,upper=obstacle_bounds(single_obstacle_config(config,box))
        ax.add_patch(Rectangle(lower,*(upper-lower),facecolor="#6f9e75",alpha=.6))
        ax.text(*((lower+upper)/2),box["id"].replace("StaticObstacle","Obstacle "),ha="center",fontsize=9)
    nodes=np.array([r["world_pose"] for r in manifest["nodes"]])
    ax.plot(*nodes[:,:2].T,"o--",color="#9180b4",ms=4,lw=1,label="Reference Topomap nodes (1 s + final)")
    for node in manifest["nodes"]:
        x,y,_=node["world_pose"]
        ax.annotate(str(node["node_id"]),(x,y),xytext=(0,9 if node["node_id"]%2 else -12),textcoords="offset points",ha="center",fontsize=7)
    ax.plot(*poses[:,:2].T,color="#087e8b",lw=2.2,label="Actual Topomap navigation")
    ax.plot(*poses[0,:2],"ko",ms=6,label="Start")
    ax.plot(*poses[-1,:2],"x",color="#d1495b",ms=9,mew=2,label="Actual end")
    ax.add_patch(Circle(config["goal_pose"][:2],.3,fill=False,color="#e69724",lw=1.5,label="World goal tolerance 0.30 m"))
    ax.axhline(1.5,color=".5",lw=1);ax.axhline(-1.5,color=".5",lw=1)
    ax.set(xlabel="World X [m]",ylabel="World Y [m]",xlim=(-.25,5.1),ylim=(-1.65,1.65),aspect="equal",
           title=f"NoMaD Topomap: {current['termination']} | goal={current['goal_entry']} | {current['duration_sim_s']:.3f} s")
    ax.grid(alpha=.15);ax.legend(loc="lower left",fontsize=8)
    fig.tight_layout();fig.savefig(args.out/"topomap_navigation.svg");plt.close(fig)
    svg=args.out/"topomap_navigation.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    print(json.dumps({"technical":report["topomap_technical_validation"],"goal":current["goal_entry"],
                      "termination":current["termination"],"last_closest":closest,"switches":len(events)}))


if __name__=="__main__":
    main()
