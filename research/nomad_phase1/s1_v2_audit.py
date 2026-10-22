"""S1-v2 preflight and read-only saved-run audit; never launches a policy run."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image

from nomad_isaac.async_report import rows, stats, validate
from nomad_isaac.clearance import corridor_clearance
from nomad_isaac.common import ROOT, local_to_world, sha256_file, write_json
from nomad_isaac.topomap import candidate_range, select_subgoal
from nomad_isaac.topomap_report import validate_map
from nomad_phase0.chunk_execution import protocol as pp_protocol
from nomad_phase0.chunk_report import trace
from nomad_phase0.pure_pursuit import PurePursuit
from .s1_v2 import HERE, protocol, validate_config

ARTIFACTS = ROOT.parent/"artifacts"


def preflight(manifest_path, output):
    manifest, checks = validate_map(manifest_path)
    validate_config(manifest["scenario"])
    assert manifest["spacing_sim_s"] == 2. and manifest["reference_kind"] == "deterministic_centerline"
    render = manifest_path.parent.parent
    assert sha256_file(render/"scene.usda") == manifest["rendered_scene_sha256"]
    render_check = json.loads((render/"render_check.json").read_text())
    assert render_check["status"] == "PASS" and render_check["obstacle_count"] == 0
    assert render_check["straight_corridor_floor_xy_bounds"] == [[-1., -1.5], [9., 1.5]]
    assert sha256_file(ARTIFACTS/"checkpoints/nomad.pth") == protocol()["checkpoint_sha256"]
    # Carry forward the previous preservation inventory, and protect its actual new run logs.
    old = json.loads((ARTIFACTS/"isaac6/phase1_s1_preflight_01/preflight/preflight.json").read_text())
    protected = dict(old["protected_sha256"])
    for name in ["s1_scenario.json", "s1_protocol.json"]:
        path = HERE/name
        protected[str(path)] = sha256_file(path)
    for pilot in ("P0", "P1"):
        run = ARTIFACTS/"isaac6/phase1_s1_preflight_01"/pilot
        for path in list(run.glob("*.json"))+list(run.glob("*.jsonl"))+list(run.glob("*.csv")):
            protected[str(path)] = sha256_file(path)
    assert all(sha256_file(Path(f)) == h for f, h in protected.items())
    frozen = [ROOT/"research/nomad_isaac"/n for n in
              ("launch.py", "simulator.py", "async_runtime.py", "topomap.py", "worker.py", "async_core.py", "delivery_delay.py", "clearance.py")]
    frozen += [ROOT/"research/nomad_phase0"/n for n in ("chunk_execution.py", "pure_pursuit.py", "chunk_pilot_protocol.json")]
    frozen += [HERE/n for n in ("s1_v2.py", "s1_v2_audit.py", "s1_v2_scenario.json", "s1_v2_protocol.json")]
    reference = Path(manifest["source_run"])
    inputs = [manifest_path, render/"scene.usda", render/"render_check.json"]
    inputs += [manifest_path.parent/n["rgb_file"] for n in manifest["nodes"]]
    inputs += [reference/n for n in manifest["reference_sha256"]]
    result = {"status": "PASS", "map_validation": checks, "protocol": protocol(),
              "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path),
              "terminal_reference": manifest["nodes"][-1], "render_check": render_check,
              "protected_sha256": protected, "frozen_source_sha256": {str(f): sha256_file(f) for f in frozen},
              "input_sha256": {str(f): sha256_file(f) for f in inputs},
              "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "checkpoint_sha256": protocol()["checkpoint_sha256"],
              "navigation": "NOT_YET_RUN", "reference_rendering_navigation_count": 0,
              "reference_rendering_inference_count": 0}
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/"preflight.json", result)
    print(json.dumps({"preflight": "PASS", "nodes": manifest["node_count"], "protected_files": len(protected)}))


def audit(run, output, frozen_path):
    frozen = json.loads(frozen_path.read_text())
    for group in ("protected_sha256", "frozen_source_sha256", "input_sha256"):
        assert all(sha256_file(Path(f)) == h for f, h in frozen[group].items()), group
    output.mkdir(parents=True, exist_ok=False)
    runtime = validate(run, ARTIFACTS/"isaac6/two_obstacles_01", output/"runtime", actual_command_override=True)
    summary = json.loads((run/"summary.json").read_text()); config = summary["scenario"]
    validate_config(config)
    assert not json.loads((run/"provenance.json").read_text())["git_status"]
    assert config["topomap_manifest_sha256"] == frozen["manifest_sha256"]
    assert json.loads((run/"model/environment.json").read_text())["checkpoint_sha256"] == frozen["checkpoint_sha256"]
    manifest, map_checks = validate_map(Path(frozen["manifest_path"]))
    received, events, controls, inference = (rows(run/n) for n in
        ("received.jsonl", "events.jsonl", "controller.jsonl", "model/inference.jsonl"))
    records, poses = trace(run)
    actual = np.array([[float(r[k]) for k in ("v_m_s", "w_rad_s")] for r in records])
    byid = {e["id"]: e for e in events}
    follower = None; active = -1; pp_error = 0.
    for c in controls:
        tick = round(c["simulation_time_s"]*72)
        if c["valid"] and c["waypoint_id"] != active:
            active = c["waypoint_id"]; e = byid[active]
            with np.load(run/f"model/derived/{active:04d}.npz", allow_pickle=False) as data:
                world = local_to_world(data["metric"][0], np.array(e["observation_pose"]))
            np.testing.assert_allclose(world, e["chunk"]["world_xy_m"], atol=1e-12, rtol=0)
            follower = PurePursuit(world, pp_protocol()["follower"]) if e["chunk"]["path_valid"] else None
        vw = follower.control(poses[tick])[0] if c["valid"] and follower is not None else (0., 0.)
        pp_error = max(pp_error, float(np.max(abs(np.array(vw)-[c["applied_v_m_s"], c["applied_w_rad_s"]]))))
    assert pp_error < 1e-10
    clearance = rows(run/"clearance.jsonl")
    gaps = []
    for i in range(len(poses)):
        gap = corridor_clearance(poses[max(0, i-1)], poses[i], *actual[i], 1/72 if i else 0., config["corridor"], .09)
        assert abs(gap-clearance[i]["corridor_lower_m"]) < 1e-12
        assert clearance[i]["lower_m"] is None and not clearance[i]["obstacles"]
        gaps.append(gap)
    assert min(gaps) == summary["obstacle_evaluation"]["minimum_corridor_clearance_lower_m"]
    observations = [o for o in rows(run/"observations.jsonl") if "observation_id" in o]
    frames = {}
    for o in observations:
        with Image.open(run/o["rgb_file"]) as im:
            frame = np.array(im)
        assert frame.shape == (240, 320, 3)
        assert hashlib.sha256(frame.tobytes()).hexdigest() == o["frame_sha256"]
        frames[o["observation_id"]] = frame
    closest = 0; subgoal = None; selection = []; delivery = []
    for i, (r, inf) in enumerate(zip(received, inference)):
        history = np.stack([frames[j] for j in r["history_observation_ids"]])
        assert hashlib.sha256(history.tobytes()).hexdigest() == r["history_sha256"] == inf["history_sha256"]
        assert r["additional_delivery_delay_s"] == 0. and r["delivery_delay_mode"] == "uniform"
        packet, release = r["packet_received_monotonic_ns"], r["release_monotonic_ns"]
        assert r["ready_monotonic_ns"] <= packet <= release
        assert r["release_deadline_monotonic_ns"] == packet and r["received_monotonic_ns"] == release
        delivery.append((release-packet)/1e3)
        t = inf["topomap"]
        a, b = candidate_range(closest, manifest["node_count"]-1)
        assert (a, b) == (t["candidate_start"], t["candidate_end_inclusive"])
        assert t["candidate_ids"] == list(range(a, b+1))
        new, chosen, _ = select_subgoal(t["distances"], a)
        assert (new, chosen) == (t["closest_node"], t["selected_subgoal_id"])
        assert t["previous_closest_node"] == closest and t["previous_subgoal_id"] == subgoal
        assert t["closest_moved_backward"] == (new < closest)
        assert t["subgoal_moved_backward"] == (subgoal is not None and chosen < subgoal)
        assert t["diffusion_passes"] == 1 and t["diffusion_steps"] == 10
        hashes = {k: manifest["nodes"][chosen][k] for k in ("rgb_file", "png_sha256", "rgb_sha256")}
        assert hashes == t["selected_subgoal_image"] and inf["goal_sha256"] == hashes["rgb_sha256"]
        assert r["topomap"] == t
        if i in byid:
            assert byid[i]["topomap"] == t
        selection.append({"id": i, "observation_sim_s": r["observation_sim_s"], "observation_x_m": r["observation_pose"][0],
            "observation_y_m": r["observation_pose"][1], "candidate_start": a, "candidate_end": b,
            "closest": new, "subgoal": chosen, "closest_backward": t["closest_moved_backward"],
            "subgoal_backward": t["subgoal_moved_backward"], "distance_scores": json.dumps(t["distances"]),
            "switch_sim_s": byid[i]["application_sim_s"] if i in byid else None})
        closest, subgoal = new, chosen
    with (output/"topomap_selection.csv").open("x") as f:
        w = csv.DictWriter(f, fieldnames=list(selection[0])); w.writeheader(); w.writerows(selection)
    moving = np.abs(actual[1:, 0]) > 1e-12
    distance = float(np.linalg.norm(np.diff(poses[:, :2], axis=0), axis=1).sum())
    assert abs(distance-summary["distance_travelled_m"]) < 1e-10
    assert summary["delivery_delay"]["accepted_count"] == len(received)
    result = {"experiment": "S1-v2 obstacle-free D0 PILOT", "scope": "SE(2) kinematic Isaac Sim; passive oracle corridor evaluation",
        "technical_validation": "PASS" if runtime["async_reproduction"] == "PASS" else "FAIL",
        "execution_git_sha": runtime["execution_git_sha"], "run": str(run), "map_validation": map_checks,
        "scenario_sha256": protocol()["scenario_sha256"], "topomap_sha256": frozen["manifest_sha256"],
        "checkpoint_sha256": frozen["checkpoint_sha256"], "goal_entry": summary["goal_entry"],
        "termination_reason": summary["termination_reason"], "simulation_duration_s": summary["simulation_duration_s"],
        "final_goal_distance_m": summary["final_goal_distance_m"], "minimum_goal_distance_m": summary["minimum_goal_distance_m"],
        "final_pose": summary["final_pose"], "distance_travelled_m": distance,
        "stop_duration_sim_s": float(np.count_nonzero(~moving)/72),
        "obstacle_geometric_overlap": False, "obstacle_clearance": "NOT_APPLICABLE_no_obstacles",
        "corridor_intrusion": min(gaps) <= 0, "minimum_corridor_clearance_m": min(gaps),
        "requests": len(received), "received": len(received), "switches": len(events),
        "terminal_unapplied": runtime["terminal_unapplied_requests"], "waypoint_timeout": runtime["timeout"],
        "warm_inference_ms": runtime["warm_inference_ms"], "cold_inference_ms": runtime["cold_inference_ms"],
        "actual_packet_to_release_us": stats(delivery), "timing": runtime["timing"], "pacing": runtime["pacing"],
        "busy_observation_skips": summary["busy_observation_skips"], "missed_capture_slots": summary["missed_capture_slots"],
        "topomap": {"final_closest": closest, "final_subgoal": subgoal, "goal_node": manifest["node_count"]-1,
            "closest_backward_count": sum(r["closest_backward"] for r in selection),
            "subgoal_backward_count": sum(r["subgoal_backward"] for r in selection),
            "visited_closest_ids": sorted({r["closest"] for r in selection}), "official_selection_verified": True},
        "validation": {"pp_max_command_error": pp_error, "pose_max_error": runtime["validation"]["max_pose_integration_error"],
            "corridor_recomputed": "PASS", "rgb_and_worker_history_hashes": "PASS", "rgb_capture_count": len(frames),
            "normalization_and_metric": "PASS", "checkpoint_parameter_coverage": runtime["validation"]["checkpoint_coverage"]["parameter_coverage"],
            "uniform_delay_all_accepted_results": "PASS", "clean_execution_checkout": True,
            "protected_hashes_unchanged": len(frozen["protected_sha256"]), "frozen_sources_unchanged": len(frozen["frozen_source_sha256"])},
        "limitations": ["One D0 run; no delay robustness or sudden-obstacle evidence", "No PhysX robot dynamics",
                        "No new batch/offset runner; future D x N=5 requires separate protocol and narrow mode extension",
                        "Distance head scores are not metric distances; pose metadata is not policy localization input"]}
    write_json(output/"summary.json", result)
    print(json.dumps({k: result[k] for k in ("technical_validation", "goal_entry", "termination_reason", "simulation_duration_s", "requests", "switches")}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["preflight", "audit"])
    p.add_argument("--manifest", type=Path); p.add_argument("--run", type=Path)
    p.add_argument("--preflight", type=Path); p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.mode == "preflight":
        preflight(a.manifest, a.output)
    else:
        audit(a.run, a.output, a.preflight)
