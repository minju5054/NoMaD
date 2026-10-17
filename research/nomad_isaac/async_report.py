"""Offline validation of real clocks, OLD motion, output semantics and safety."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .common import integrate_se2, local_to_world, original_controller, sha256_file, write_json
from .clearance import (configured_obstacles, obstacle_bounds, planning_diagnostic,
                        single_obstacle_config, swept_clearance)


def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s]


def stats(values):
    a = np.asarray(values, dtype=float)
    return {"n": len(a), "median": float(np.median(a)), "p95": float(np.percentile(a, 95)),
            "min": float(a.min()), "max": float(a.max())} if len(a) else {"n": 0}


def wrapped(a):
    return (a+np.pi) % (2*np.pi)-np.pi


def validate(run, baseline, out):
    out.mkdir(parents=True, exist_ok=False)
    summary = json.loads((run/"summary.json").read_text())
    config = summary["scenario"]
    protocol = json.loads((run/"async_protocol.json").read_text())
    requests, received, events = (rows(run/name) for name in ["requests.jsonl", "received.jsonl", "events.jsonl"])
    observations = rows(run/"observations.jsonl")
    control, planning, inference = (rows(run/name) for name in ["controller.jsonl", "planning.jsonl", "model/inference.jsonl"])
    with (run/"agent_trajectory.csv").open() as f:
        trace = list(csv.DictReader(f))
    pose = np.array([[float(r[k]) for k in ["x_m", "y_m", "yaw_rad"]] for r in trace])
    sim = np.array([float(r["simulation_time_s"]) for r in trace])
    wall_ns = np.array([int(r["monotonic_ns"]) for r in trace], dtype=np.int64)
    epoch = summary["epoch_monotonic_ns"]
    wall = (wall_ns-epoch)/1e9
    dt = 1/config["integration_hz"]
    assert np.all(np.diff(wall_ns)>0)
    np.testing.assert_allclose(sim, np.arange(len(trace))*dt, atol=1e-12, rtol=0)
    incoming = np.array([[float(r["v_m_s"]),float(r["w_rad_s"])] for r in trace])
    incoming_id = np.array([int(r["incoming_waypoint_id"]) for r in trace])
    incoming_valid = np.array([r["incoming_command_valid"] == "True" for r in trace])
    max_integration_error = max(float(np.max(np.abs(integrate_se2(pose[i-1], *incoming[i], dt)-pose[i])))
                                for i in range(1,len(trace)))
    assert max_integration_error < 1e-10
    np.testing.assert_allclose(np.linalg.norm(pose[:,:2]-config["goal_pose"][:2],axis=1),
                               [float(r["goal_distance_m"]) for r in trace], atol=1e-12, rtol=0)
    assert len(received)==len(inference)==len(requests)==summary["inference_count"]
    assert [r["id"] for r in requests] == [r["id"] for r in received] == list(range(len(requests)))
    assert [r["id"] for r in planning] == list(range(len(requests)))
    byid = {e["id"]: e for e in events}
    obs_byid = {r["observation_id"]:r for r in observations if "observation_id" in r}
    last_receive = -1
    for q, r in zip(requests, received):
        assert q["request_submit_monotonic_ns"] > last_receive
        last_receive = r["received_monotonic_ns"]
        assert [obs_byid[i]["observation_sim_s"] for i in q["history_observation_ids"]] == q["history_sim_s"]
        assert [obs_byid[i]["frame_sha256"] for i in q["history_observation_ids"]] == q["history_frame_sha256"]
        assert len(q["history_observation_ids"]) == 4 and np.all(np.diff(q["history_observation_ids"])>0)

    c_ticks = np.array([round(c["simulation_time_s"]*config["integration_hz"]) for c in control])
    assert c_ticks.tolist() == list(range(0, len(trace)-1, config["integration_hz"]//config["controller_hz"]))
    controller = original_controller()
    timeout_episodes = 0
    for c in control:
        if c["latest_received_id"] < 0:
            assert c["status"] == "missing" and not c["valid"]
            expected = [0.,0.]
        else:
            r = received[c["latest_received_id"]]
            age = (c["monotonic_ns"]-r["received_monotonic_ns"])/1e9
            assert abs(age-c["waypoint_age_wall_s"])<1e-12
            assert c["valid"] == (age<1.)
            expected = controller(r["selected_waypoint_m"]) if age<1 else [0.,0.]
        np.testing.assert_allclose(expected,[c["v_m_s"],c["w_rad_s"]],atol=1e-12,rtol=0)
        timeout_episodes += c["new_timeout"]
    assert timeout_episodes == summary["waypoint_timeout_episodes"]
    # Link every incoming interval to the last actual controller refresh.
    for i in range(1,len(trace)):
        ci = (i-1)//(config["integration_hz"]//config["controller_hz"])
        c = control[ci]
        np.testing.assert_allclose(incoming[i], [c["v_m_s"],c["w_rad_s"]],atol=1e-12,rtol=0)
        assert incoming_id[i] == c["waypoint_id"] and incoming_valid[i] == c["valid"]

    timing = []
    mapping_errors, old_distances, old_yaw = [], [], []
    concurrent_ids = []
    switch_tick_errors = []
    peak_initial_pose = 0.
    for r in received:
        i = r["id"]
        chain = [r[k] for k in ["pose_sample_monotonic_ns", "observation_monotonic_ns", "capture_end_monotonic_ns",
                 "request_submit_monotonic_ns", "request_send_monotonic_ns", "inference_start_monotonic_ns",
                 "inference_end_monotonic_ns", "host_output_ready_monotonic_ns", "persistence_end_monotonic_ns", "received_monotonic_ns"]]
        assert np.all(np.diff(np.array(chain,dtype=np.int64))>=0)
        assert r["ready_monotonic_ns"] == r["inference_end_monotonic_ns"]
        obs_tick = round(r["observation_sim_s"]*config["integration_hz"])
        np.testing.assert_allclose(pose[obs_tick], r["observation_pose"], atol=1e-10,rtol=0)
        assert wall_ns[obs_tick] == r["pose_sample_monotonic_ns"]
        receive_tick = round(r["received_sim_s"]*config["integration_hz"])
        np.testing.assert_allclose(pose[receive_tick], r["agent_pose_at_receive"], atol=1e-10,rtol=0)
        assert r["seed"] == config["seed"]+2*i and r["ddpm_seed"]==r["seed"]+1
        with np.load(run/f"model/raw/{i:04d}.npz",allow_pickle=False) as raw, np.load(run/f"model/derived/{i:04d}.npz",allow_pickle=False) as derived:
            z, metric = raw["normalized_diffusion"], derived["metric"]
            assert z.shape == metric.shape == (8,8,2) and metric.dtype == np.float32
            assert all(np.isfinite(a[k]).all() for a in [raw,derived] for k in a.files)
            cumulative = np.cumsum(((z+1)/2)*np.array([7.5,8.])+np.array([-2.5,-4.]),axis=1).astype(np.float32)
            np.testing.assert_array_equal(cumulative,derived["cumulative"])
            np.testing.assert_array_equal(cumulative*np.float32(.05),metric)
            np.testing.assert_array_equal(metric[0,2],r["selected_waypoint_m"])
            np.testing.assert_array_equal(metric[0,2],derived["selected_waypoint"])
            world = local_to_world(metric[0],np.array(r["observation_pose"]))
            np.testing.assert_allclose(world, planning[i]["world_xy_m"],atol=1e-12,rtol=0)
            for box in configured_obstacles(config):
                diag=planning_diagnostic(metric[0],r["observation_pose"],single_obstacle_config(config,box))
                assert abs(diag["polyline_clearance_m"]-planning[i]["obstacles"][box["id"]]["polyline_clearance_m"])<1e-12
        start, end = r["inference_start_monotonic_ns"], r["inference_end_monotonic_ns"]
        wholly_inside = (wall_ns[:-1]>=start)&(wall_ns[1:]<=end)&incoming_valid[1:]&(incoming_id[1:]>=0)&(incoming_id[1:]<i)
        idx = np.flatnonzero(wholly_inside)+1
        distance = float(np.sum(np.abs(incoming[idx,0])*dt))
        yaw = float(np.sum(wrapped(pose[idx,2]-pose[idx-1,2])))
        if i>0:
            old_distances.append(distance); old_yaw.append(abs(yaw))
        if distance>0:
            concurrent_ids.append(i)
        contained = wall_ns[0]<=start<=end<=wall_ns[-1]
        start_sim = float(np.interp((start-epoch)/1e9,wall,sim)) if contained else None
        end_sim = float(np.interp((end-epoch)/1e9,wall,sim)) if contained else None
        mapped_duration = end_sim-start_sim if contained else None
        clock_error = mapped_duration-(end-start)/1e9 if contained else None
        if contained:
            mapping_errors.append(abs(clock_error))
        record = {"request_id":i,"t_obs_sim_s":r["observation_sim_s"],
                  "t_obs_monotonic_ns":r["observation_monotonic_ns"],"t_infer_start_monotonic_ns":start,
                  "t_infer_end_monotonic_ns":end,"t_ready_monotonic_ns":r["ready_monotonic_ns"],
                  "t_received_monotonic_ns":r["received_monotonic_ns"],
                  "t_received_sim_snapshot_s":r["received_sim_s"],
                  "inference_ms":r["inference_ms"],
                  "observation_to_ready_wall_s":(end-r["observation_monotonic_ns"])/1e9,
                  "rgb_available_to_ready_wall_s":(end-r["capture_end_monotonic_ns"])/1e9,
                  "ready_to_received_wall_s":(r["received_monotonic_ns"]-end)/1e9,
                  "render_s":(r["capture_end_monotonic_ns"]-r["observation_monotonic_ns"])/1e9,
                  "request_delay_wall_s":(r["request_submit_monotonic_ns"]-r["observation_monotonic_ns"])/1e9,
                  "dispatch_to_infer_start_wall_s":(start-r["request_submit_monotonic_ns"])/1e9,
                  "pose_age_at_capture_start_s":(r["observation_monotonic_ns"]-r["pose_sample_monotonic_ns"])/1e9,
                  "old_full_intervals":len(idx),"old_full_interval_distance_m":distance,"old_full_interval_signed_yaw_rad":yaw,
                  "old_valid_at_observation":r["old_valid_at_observation"],
                  "timeout_refreshes_during_inference":sum(c["status"]=="expired" and start<=c["monotonic_ns"]<=end for c in control),
                  "infer_start_sim_interpolated_s":start_sim,"ready_sim_interpolated_s":end_sim,
                  "infer_sim_duration_interpolated_s":mapped_duration,"inference_clock_mapping_error_s":clock_error,
                  "switch_applied":i in byid}
        if i in byid:
            e=byid[i]
            tick=round(e["application_sim_s"]*config["integration_hz"])
            np.testing.assert_allclose(pose[tick],e["agent_pose_at_switch"],atol=1e-10,rtol=0)
            matching=[c for c in control if c["latest_received_id"]==i and c["valid"]]
            assert matching and matching[0]["monotonic_ns"]==e["application_monotonic_ns"]
            next_wall_tick=next((c for c in control if c["monotonic_ns"]>=r["received_monotonic_ns"]),None)
            if next_wall_tick and next_wall_tick["monotonic_ns"]!=e["application_monotonic_ns"]:
                switch_tick_errors.append(i)
            record.update({"t_switch_monotonic_ns":e["application_monotonic_ns"],"t_switch_sim_s":e["application_sim_s"],
                           "observation_to_switch_wall_s":(e["application_monotonic_ns"]-r["observation_monotonic_ns"])/1e9,
                           "rgb_available_to_switch_wall_s":(e["application_monotonic_ns"]-r["capture_end_monotonic_ns"])/1e9,
                           "observation_to_switch_sim_s":e["application_sim_s"]-r["observation_sim_s"],
                           "received_to_switch_wall_s":(e["application_monotonic_ns"]-r["received_monotonic_ns"])/1e9,
                           "switch_translation_from_observation_m":float(np.linalg.norm(pose[tick,:2]-np.array(r["observation_pose"][:2]))),
                           "switch_abs_yaw_from_observation_rad":abs(float(wrapped(pose[tick,2]-r["observation_pose"][2]))),
                           "switch_x_m":float(pose[tick,0]),"switch_y_m":float(pose[tick,1]),"switch_yaw_rad":float(pose[tick,2]),
                           "obs_x_m":r["observation_pose"][0],"obs_y_m":r["observation_pose"][1],"obs_yaw_rad":r["observation_pose"][2],
                           "selected_x_m":r["selected_waypoint_m"][0],"selected_y_m":r["selected_waypoint_m"][1],
                           "v_m_s":e["v_m_s"],"w_rad_s":e["w_rad_s"]})
            if i==0:
                peak_initial_pose=float(np.max(np.abs(pose[:tick+1]-config["start_pose"])))
        timing.append(record)
    assert peak_initial_pose==0

    # Re-evaluate each recorded swept interval with the existing exact arc bound.
    safety_minima={}
    for box in configured_obstacles(config):
        lower,upper=obstacle_bounds(single_obstacle_config(config,box))
        minimum=float("inf")
        for i in range(1,len(trace)):
            check=swept_clearance(pose[i-1],*incoming[i],dt,lower,upper,config["agent_radius_m"])
            minimum=min(minimum,check["lower_m"])
        expected=summary["obstacle_evaluation"]["obstacles"][box["id"]]["minimum_swept_clearance_lower_m"]
        assert abs(minimum-expected)<1e-10
        safety_minima[box["id"]]=minimum
    pacing=np.abs(wall-sim)
    factor=float(sim[-1]/wall[-1])
    pacing_pass=bool(np.percentile(pacing,95)<=protocol["pacing_p95_abs_error_max_s"] and pacing.max()<=protocol["pacing_max_abs_error_max_s"]
                     and abs(factor-1)<=protocol["real_time_factor_relative_error_max"])
    mapping_pass=bool(mapping_errors and np.percentile(mapping_errors,95)<=protocol["inference_clock_mapping_p95_abs_error_max_s"])
    environment=json.loads((run/"model/environment.json").read_text())
    coverage=environment["coverage"]
    assert coverage["parameter_coverage"]==1 and not coverage["missing_keys"] and not coverage["unexpected_keys"]
    baseline_summary=json.loads((baseline/"summary.json").read_text())
    base_events=rows(baseline/"events.jsonl")
    with (baseline/"agent_trajectory.csv").open() as f:
        base_poses=list(csv.DictReader(f))
    baseline_delays=[(e["application_monotonic_ns"]-e["observation_monotonic_ns"])/1e9 for e in base_events]
    baseline_shifts=[];baseline_yaw=[]
    for e in base_events:
        p=base_poses[round(e["application_sim_s"]*72)]
        baseline_shifts.append(float(np.linalg.norm(np.array([float(p["x_m"]),float(p["y_m"])])-e["observation_pose"][:2])))
        baseline_yaw.append(abs(float(wrapped(float(p["yaw_rad"])-e["observation_pose"][2]))))
    preservation=json.loads((baseline.parent/"async_baseline_preservation_01.json").read_text())
    assert all(sha256_file(baseline/name)==digest for name,digest in preservation.items())
    ready_pass=bool(len(received)>1 and concurrent_ids and not switch_tick_errors and pacing_pass and mapping_pass)
    report={"async_reproduction":"PASS" if ready_pass else "FAIL", "real_time_pacing_pass":pacing_pass,
            "inference_clock_mapping_pass":mapping_pass,"switch_tick_mismatch_ids":switch_tick_errors,
            "source_run":str(run),"execution_git_sha":json.loads((run/"provenance.json").read_text())["git_sha"],
            "execution_git_status":json.loads((run/"provenance.json").read_text())["git_status"],
            "requests":len(requests),"received":len(received),"switches":len(events),"control_refreshes":len(control),"pose_rows":len(trace),
            "initial_stop_pose_error":peak_initial_pose,"warm_inference_ms":stats([r["inference_ms"] for r in received[1:]]),
            "cold_inference_ms":received[0]["inference_ms"],
            "timing":{k:stats([r[k] for r in timing if k in r]) for k in ["observation_to_ready_wall_s","observation_to_switch_wall_s",
                "observation_to_switch_sim_s","rgb_available_to_ready_wall_s","rgb_available_to_switch_wall_s",
                "ready_to_received_wall_s","received_to_switch_wall_s","render_s","request_delay_wall_s",
                "dispatch_to_infer_start_wall_s","pose_age_at_capture_start_s","switch_translation_from_observation_m","switch_abs_yaw_from_observation_rad"]},
            "old_motion_full_intervals_only":{"distance_m":stats(old_distances),"abs_net_yaw_rad":stats(old_yaw),
                "nonzero_request_count":len(concurrent_ids),"nonzero_request_ids":concurrent_ids,
                "meaning":"Sum of complete executed intervals inside GPU inference wall window, valid previous commands only; excludes first inference"},
            "pacing":{"absolute_pose_error_s":stats(pacing),"real_time_factor":factor,
                "late_more_than_one_tick":int(np.sum(pacing>dt)),"inference_clock_mapping_abs_error_s":stats(mapping_errors),
                "actual_pose_interval_wall_s":stats(np.diff(wall)),
                "actual_control_interval_wall_s":stats(np.diff([c["monotonic_ns"] for c in control])/1e9)},
            "timeout":{"episodes":timeout_episodes,"expired_control_ticks":sum(c["status"]=="expired" for c in control),
                "runtime_status":"EXERCISED" if timeout_episodes else "NOT_EXERCISED_no_natural_timeout","synthetic_exact_timeout":"PASS"},
            "busy_observation_skips":summary["busy_observation_skips"],"missed_capture_slots":summary["missed_capture_slots"],
            "capture_count":len(obs_byid),"terminal_unapplied_requests":[r["id"] for r in received if r["id"] not in byid],
            "goal_entry":summary["goal_entry"],"minimum_goal_distance_m":summary["minimum_goal_distance_m"],
            "termination_reason":summary["termination_reason"],"simulation_duration_s":summary["simulation_duration_s"],
            "navigation_wall_seconds":summary["navigation_wall_seconds"],"obstacle_evaluation":summary["obstacle_evaluation"],
            "validation":{"status":"PASS","max_pose_integration_error":max_integration_error,"normalization_cumsum_metric_selection":"exact",
                "controller_matches_original":True,"observation_world_anchor_matches_planning":True,"checkpoint_coverage":coverage,
                "previous_baseline_hashes_unchanged":len(preservation),"swept_clearance_recomputed":safety_minima},
            "synchronous_baseline":{"requests":len(base_events),"warm_inference_ms":stats([e["inference_ms"] for e in base_events[1:]]),
                "observation_timestamp_note":"Legacy t_obs is assigned AFTER RGB capture; async t_obs is capture start. Compare RGB-available delays for aligned host-time semantics.",
                "observation_to_ready_wall_s":stats([(e["inference_end_monotonic_ns"]-e["observation_monotonic_ns"])/1e9 for e in base_events]),
                "observation_to_switch_wall_s":stats(baseline_delays),
                "observation_to_switch_sim_s":stats([e["application_sim_s"]-e["observation_sim_s"] for e in base_events]),
                "old_motion_during_inference_m":0.,"old_yaw_during_inference_rad":0.,
                "switch_translation_from_observation_m":stats(baseline_shifts),"switch_abs_yaw_from_observation_rad":stats(baseline_yaw),
                "goal_entry":baseline_summary["goal_entry"],"minimum_goal_distance_m":baseline_summary["minimum_goal_distance_m"],
                "obstacle_evaluation":baseline_summary["obstacle_evaluation"]},
            "limitations":["Canonical SE2 executed at 72 Hz; USD camera holds 4 Hz capture snapshots, not independent PhysX dynamics",
                "Timing mapping interpolates existing wall/simulation samples; direct OLD evidence uses only complete measured intervals",
                "One scenario/run; changed observation/seed association prevents causal attribution to asynchrony alone",
                "No native waypoint yaw/timestamps, topomap, graph, video or GUI in this validator",
                "Controlled post-inference delivery delay enabled; received means controller-side release"
                if "delivery_delay" in summary else "No artificial latency injected"]}
    names=list(dict.fromkeys(k for r in timing for k in r))
    with (out/"request_timing.csv").open("x") as f:
        writer=csv.DictWriter(f,fieldnames=names);writer.writeheader();writer.writerows(timing)
    write_json(out/"summary.json",report)
    files=[run/p for p in ["scenario.json","summary.json","provenance.json","async_protocol.json","agent_trajectory.csv",
           "controller.jsonl","events.jsonl","received.jsonl","requests.jsonl","observations.jsonl","planning.jsonl","model/environment.json","model/inference.jsonl"]]
    files+=sorted((run/"model/raw").glob("*.npz"))+sorted((run/"model/derived").glob("*.npz"))
    write_json(out/"input_hashes.json",{str(p.relative_to(run)):sha256_file(p) for p in files})
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run",type=Path,required=True);p.add_argument("--baseline",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(); r=validate(a.run,a.baseline,a.output)
    print(json.dumps({k:r[k] for k in ["async_reproduction","real_time_pacing_pass","requests","goal_entry","termination_reason"]}))
