"""S1 preflight and saved-log audit only. Never launches navigation/inference."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image

from nomad_isaac.async_report import rows, stats, validate, wrapped
from nomad_isaac.clearance import obstacle_bounds, single_obstacle_config, point_clearance, swept_clearance, corridor_clearance
from nomad_isaac.common import ROOT, local_to_world, sha256_file, write_json
from nomad_isaac.old_rollout_placement import magenta_mask
from nomad_isaac.topomap_report import validate_map
from nomad_phase0.chunk_execution import protocol as pp_protocol
from nomad_phase0.chunk_report import trace
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.scenario_feasibility import Scene, search, InvalidScenario
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from .s1 import HERE, VisibilityGate, place_forward, protocol, triggered

ARTIFACTS = ROOT.parent/"artifacts"
TOPOMAP = ARTIFACTS/"isaac6/topomap_reference_2s_01/topomap/manifest.json"


def preflight(output):
    output.mkdir(parents=True, exist_ok=False)
    p = protocol()
    manifest, map_checks = validate_map(TOPOMAP)
    assert manifest["node_count"] == 14 and manifest["spacing_sim_s"] == 2
    assert sha256_file(TOPOMAP) == p["topomap_manifest_sha256"]
    checkpoint = ARTIFACTS/"checkpoints/nomad.pth"
    assert sha256_file(checkpoint) == p["checkpoint_sha256"]
    c = json.loads((HERE/"s1_scenario.json").read_text())
    reference = ARTIFACTS/"isaac6/phase0c_pure_pursuit_01"
    records, poses = trace(reference)
    i = next(i for i, pose in enumerate(poses) if triggered(c, pose))
    checks = []
    for d in p["distance_candidates_m"]:
        c["dynamic_obstacle"]["placement"]["forward_clearance_m"] = d
        result = place_forward(c, poses[i])
        assert result["status"] == "PLACED", result
        checks.append(result)
    protected = [checkpoint, TOPOMAP, reference/"agent_trajectory.csv",
                 ROOT/"research/nomad_isaac/two_obstacles_wide_wall_scenario.json",
                 ROOT/"research/nomad_isaac/old_rollout_obstacle_scenario.json",
                 ROOT/"research/nomad_phase0/pure_pursuit.py", ROOT/"research/nomad_phase0/chunk_pilot_protocol.json",
                 ROOT/"research/nomad_isaac/delivery_delay.py", ROOT/"research/nomad_isaac/async_core.py",
                 ROOT/"deployment/src/pd_controller.py", ROOT/"research/nomad_preflight/native.py"]
    protected += [TOPOMAP.parent/n["rgb_file"] for n in manifest["nodes"]]
    prior = json.loads((ROOT/"research/results/phase0d_s0_paired_n10_20261020/verification.json").read_text())
    for rel, digest in prior["source_file_sha256"].items():
        file = ARTIFACTS/"isaac6/s0_paired_n10_01"/rel
        assert sha256_file(file) == digest
        protected.append(file)
    fixed_sources = list(HERE.glob("*.py"))+list(HERE.glob("*.json"))
    fixed_sources += [ROOT/"research/nomad_isaac"/n for n in ["launch.py","simulator.py","async_runtime.py","sudden_obstacle.py"]]
    fixed_sources += [ROOT/"research/nomad_phase0/chunk_execution.py"]
    result = {"status": "PASS", "scope": "Offline preflight, not actual S1 spawn feasibility or visibility proof",
        "protocol": p, "map_validation": map_checks, "reference_pose": poses[i].tolist(),
        "reference_tick": i, "geometry_at_saved_reference_pose": checks,
        "camera_center_bearing_rad": 0., "actual_rgb_gate": "PENDING_pilots",
        "protected_sha256": {str(f): sha256_file(f) for f in protected},
        "frozen_source_sha256": {str(f): sha256_file(f) for f in fixed_sources},
        "source_sha": subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()}
    write_json(output/"preflight.json", result)
    print(json.dumps({"preflight": "PASS", "reference_tick": i, "geometry_d": p["distance_candidates_m"]}))


def audit(run, output, preflight_path):
    output.mkdir(parents=True, exist_ok=False)
    frozen = json.loads(preflight_path.read_text())
    assert all(sha256_file(Path(f)) == h for f,h in frozen["frozen_source_sha256"].items())
    runtime = validate(run, ARTIFACTS/"isaac6/two_obstacles_01", output/"runtime", actual_command_override=True)
    s = json.loads((run/"summary.json").read_text()); c = s["scenario"]
    received, events, control = (rows(run/name) for name in ["received.jsonl","events.jsonl","controller.jsonl"])
    observations = [r for r in rows(run/"observations.jsonl") if "observation_id" in r]
    records, poses = trace(run)
    commands = np.array([[float(r[k]) for k in ["v_m_s","w_rad_s"]] for r in records])
    events_byid = {e["id"]: e for e in events}
    # Original PP is re-evaluated at the actual 9Hz poses, retaining within-chunk progress.
    follower = None; active = -1; max_pp_error = 0.
    for row in control:
        tick = round(row["simulation_time_s"]*72)
        if row["valid"] and row["waypoint_id"] != active:
            active = row["waypoint_id"]
            e = events_byid[active]
            with np.load(run/f"model/derived/{active:04d}.npz",allow_pickle=False) as data:
                world = local_to_world(data["metric"][0],np.array(e["observation_pose"]))
            np.testing.assert_allclose(world,e["chunk"]["world_xy_m"],atol=1e-12,rtol=0)
            follower = PurePursuit(world,pp_protocol()["follower"]) if e["chunk"]["path_valid"] else None
        vw = follower.control(poses[tick])[0] if row["valid"] and follower is not None else (0.,0.)
        max_pp_error = max(max_pp_error,float(np.max(abs(np.array(vw)-[row["applied_v_m_s"],row["applied_w_rad_s"]]))))
    assert max_pp_error < 1e-10
    # Replay visibility on unmodified saved RGB, including the final captured frame.
    gate = VisibilityGate(); images = {}; byobs = {}
    for o in observations:
        rgb = np.array(Image.open(run/o["rgb_file"]).convert("RGB"))
        assert hashlib.sha256(rgb.tobytes()).hexdigest() == o["frame_sha256"]
        mask = magenta_mask(rgb); diagnostic = o["dynamic"]
        assert int(mask.sum()) == diagnostic["magenta_pixels"]
        assert diagnostic["visible"] == (diagnostic["active"] and int(mask.sum()) >= 20)
        if not diagnostic["active"]:
            assert not mask.any()
        assert gate.observe(o) == o["oracle_information"]
        images[o["observation_id"]] = rgb; byobs[o["observation_id"]] = o
    assert json.loads((run/"oracle_information.json").read_text()) == observations[-1]["oracle_information"]
    requested_d = s["delivery_delay"]["configured_additional_s"]
    delivery, first_fresh = [], None
    for r in received:
        assert hashlib.sha256(np.stack([images[i] for i in r["history_observation_ids"]]).tobytes()).hexdigest() == r["history_sha256"]
        assert r["history_dynamic"] == [byobs[i]["dynamic"] for i in r["history_observation_ids"]]
        assert r["additional_delivery_delay_s"] == requested_d and r["delivery_delay_mode"] == "uniform"
        packet, release = r["packet_received_monotonic_ns"], r["release_monotonic_ns"]
        assert r["ready_monotonic_ns"] <= packet <= release
        assert r["release_deadline_monotonic_ns"] == packet+round(requested_d*1e9)
        assert release >= r["release_deadline_monotonic_ns"] and r["received_monotonic_ns"] == release
        delivery.append((release-packet)/1e9)
        if first_fresh is None and any(byobs[i]["dynamic"]["visible"] for i in r["history_observation_ids"]):
            first_fresh = r
    # All clocks below stay in their own domain; simulation stamps are pose snapshots.
    dynamic = s["dynamic_obstacle"]; spawn = dynamic["spawn"]
    side_results = {}; minimum_dynamic = None; first_fresh_record = None
    if spawn:
        spawn_tick = spawn["tick"]
        assert spawn_tick == next(i for i,pose in enumerate(poses) if triggered(c,pose))
        np.testing.assert_array_equal(poses[spawn_tick],spawn["pose"])
        placement = place_forward(c,poses[spawn_tick])
        assert placement["status"] == "PLACED"
        np.testing.assert_array_equal(placement["obstacle"]["center_xy_m"],spawn["obstacle"]["center_xy_m"])
        render = json.loads((run/"dynamic_render_update.json").read_text())
        assert render["obstacle"] == spawn["obstacle"] and render["visibility_source_tick"] == spawn_tick
        lo,hi = obstacle_bounds(single_obstacle_config(c,spawn["obstacle"]))
        np.testing.assert_allclose(render["usd_aabb"],[[*lo,0.],[*hi,.8]],atol=1e-12,rtol=0)
        activations = rows(run/"dynamic/activation.jsonl")
        assert all(a["active"] == (a["tick"] >= spawn_tick) for a in activations)
        for o in observations:
            assert o["dynamic"]["active"] == (o["dynamic"]["capture_tick"] >= spawn_tick)
        logged = rows(run/"dynamic/clearance.jsonl"); lower=[]
        for i in range(spawn_tick,len(poses)):
            check = swept_clearance(poses[i] if i==spawn_tick else poses[i-1], *commands[i],
                                    0. if i==spawn_tick else 1/72,lo,hi,.09,.02)
            assert abs(check["lower_m"]-logged[i-spawn_tick]["lower_m"]) < 1e-10
            assert check["geometric_overlap"] == logged[i-spawn_tick]["geometric_overlap"]
            lower.append(check["lower_m"])
        minimum_dynamic = min(lower)
        if first_fresh:
            r=first_fresh; event=events_byid.get(r["id"]); a=round(r["observation_sim_s"]*72)
            b=round(event["application_sim_s"]*72) if event else None
            first_fresh_record={"id":r["id"],"history_ids":r["history_observation_ids"],
                "history_sha256":r["history_sha256"],"history_frame_sha256":r["history_frame_sha256"],
                "A":r["observation_pose"],"B":event["agent_pose_at_switch"] if event else None,
                "t_obs_sim_s":r["observation_sim_s"],"t_switch_sim_s":event["application_sim_s"] if event else None,
                "t_obs_host_ns":r["observation_monotonic_ns"],"t_ready_host_ns":r["ready_monotonic_ns"],
                "t_packet_host_ns":r["packet_received_monotonic_ns"],"t_release_host_ns":r["release_monotonic_ns"],
                "t_switch_host_ns":event["application_monotonic_ns"] if event else None,
                "applied":event is not None, "observation_to_switch_OLD_distance_m":float(np.sum(abs(commands[a+1:b+1,0]))/72) if b else None,
                "observation_to_switch_yaw_rad":float(np.sum(wrapped(np.diff(poses[a:b+1,2])))) if b else None,
                "dynamic_clearance_at_A_m":point_clearance(poses[a,:2],lo,hi,.09),
                "dynamic_clearance_at_B_m":point_clearance(poses[b,:2],lo,hi,.09) if b else None,
                "minimum_OLD_window_clearance_m":min(lower[a-spawn_tick:b-spawn_tick+1]) if b else None,
                "intervening_OLD_ids":sorted(set(int(x["incoming_waypoint_id"]) for x in records[a+1:b+1])) if b else [],
                "terminal_unapplied":r["terminal_unapplied"]}
        settings=json.loads((ROOT/"research/nomad_phase0/feasibility_protocol.json").read_text())["search"]
        actual={**c,"start_pose":spawn["pose"],"dynamic_obstacle":spawn["obstacle"]}
        try:
            scene=Scene(actual,"active")
            for side in ["left_positive_y","right_negative_y"]:
                side_results[side]=search(scene,settings,side)
        except InvalidScenario as error:
            side_results={"status":"INVALID_START","reason":str(error)}
        write_json(output/"side_feasibility.json",{"scope":"Oracle geometry, actual spawn pose; frozen forward-only one-pass +Y/-Y checker, not PP feasibility or impossibility proof",
            "search_settings":settings,"geometry":actual,"results":side_results})
    static_overlap=s["obstacle_evaluation"]["geometric_overlap"]
    dyn_overlap=bool(spawn and dynamic["evaluation"]["geometric_overlap"])
    min_corridor=min(corridor_arc_minimum(poses[i-1],*commands[i],1/72,c["corridor"],.09) for i in range(1,len(poses)))
    collision=static_overlap or dyn_overlap
    handoff=("APPLIED" if first_fresh_record and first_fresh_record["applied"] else
             "PRE_HANDOFF_FAILURE" if collision else "NO_VISIBLE_FRESH_APPLIED")
    checks={"runtime":runtime["async_reproduction"]=="PASS","exact_PP_replay":max_pp_error<1e-10,
        "spawn_and_USD":spawn is not None,"visible_RGB":gate.first_visible is not None,
        "oracle_next_capture":gate.available is not None,"uniform_all_results":len(delivery)==len(received),
        "inputs_preserved":all(sha256_file(Path(f))==h for f,h in frozen["protected_sha256"].items())}
    result={"scope":protocol()["scope"],"technical_validation":"PASS" if all(checks.values()) else "INCONCLUSIVE",
        "checks":checks,"execution_git_sha":json.loads((run/"provenance.json").read_text())["git_sha"],
        "run":str(run),"D_s":requested_d,"configured_d_m":c["dynamic_obstacle"]["placement"]["forward_clearance_m"],
        "spawn":spawn,"placement":dynamic["placement"],"first_visible":gate.first_visible,"oracle_available_from":gate.available,
        "oracle_used_for_control":False,"first_visible_FRESH":first_fresh_record,"handoff_status":handoff,
        "first_FRESH_unapplied":first_fresh is not None and first_fresh["id"] not in events_byid,
        "collision_before_first_visible_FRESH_switch":collision and handoff=="PRE_HANDOFF_FAILURE",
        "goal_entry":s["goal_entry"],"goal_success":s["goal_entry"] and not collision and min_corridor>=0,
        "geometric_collision":collision,"corridor_intrusion":min_corridor<0,"minimum_corridor_m":min_corridor,
        "minimum_dynamic_clearance_m":minimum_dynamic,"static_obstacle_evaluation":s["obstacle_evaluation"],
        "dynamic_evaluation":dynamic["evaluation"],"duration_sim_s":s["simulation_duration_s"],
        "termination_reason":s["termination_reason"],"timeout":s["termination_reason"]=="simulation_timeout",
        "stop_duration_s":float(np.sum(np.all(commands[1:]==0,axis=1))/72),"travel_distance_m":s["distance_travelled_m"],
        "requests":len(received),"switches":len(events),"busy_skips":s["busy_observation_skips"],
        "missed_capture_slots":s["missed_capture_slots"],"waypoint_timeout_episodes":s["waypoint_timeout_episodes"],
        "actual_delivery_s":stats(delivery),"delivery_overshoot_s":stats(np.array(delivery)-requested_d),
        "warm_inference_ms":runtime["warm_inference_ms"],"pacing":runtime["pacing"],
        "PP_command_max_error":max_pp_error,"pose_integration_max_error":runtime["validation"]["max_pose_integration_error"],
        "side_feasibility":{k:v.get("status") for k,v in side_results.items() if isinstance(v,dict)}}
    write_json(output/"summary.json",result)
    write_json(output/"input_hashes.json",{str(f.relative_to(run)):sha256_file(f) for f in run.rglob('*') if f.is_file() and
        (f.suffix in ('.json','.jsonl','.csv','.npz') or f.parent==run/'observations') and not any(k in str(f.relative_to(run)).split('/') for k in ['cache','config','isaac_runtime','portable','model_cache'])})
    print(json.dumps({k:result[k] for k in ['technical_validation','goal_entry','geometric_collision','termination_reason','handoff_status']}),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--run',type=Path)
    parser.add_argument('--preflight-json',type=Path)
    a=parser.parse_args()
    if a.preflight:preflight(a.output)
    else:audit(a.run,a.output,a.preflight_json if a.preflight_json else a.output.parent/'preflight/preflight.json')


if __name__=='__main__':main()
