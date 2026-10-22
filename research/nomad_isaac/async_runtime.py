"""Paced kinematic execution, independent of RTX capture and GPU socket waits."""
from collections import deque
import csv
import hashlib
import json
from pathlib import Path
import socket
import threading
import time
import traceback

import numpy as np
from PIL import Image

from .async_core import AsyncClient, WaypointExecution, deadline_ns
from .clearance import MultiObstacleMonitor
from .common import write_json
from .seed_offset import request_seed


def append(stream, record):
    stream.write(json.dumps(record)+"\n")
    stream.flush()


class ExecutionThread:
    def __init__(self, config, out, oracle_safety_stop=False, online_graph=False, pure_pursuit=False):
        self.config, self.out = config, out
        self.core = WaypointExecution(config["start_pose"], config["integration_hz"], config["controller_hz"])
        self.chunk_executor = None
        self.phase2 = None
        if config.get("experiment_mode") == "phase2_s1_v2":
            from nomad_phase2.execution import Phase2Execution
            self.phase2 = Phase2Execution(config,out)
        if pure_pursuit and self.phase2 is None:
            from nomad_phase0.chunk_execution import ChunkExecution
            assert not oracle_safety_stop and not online_graph
            assert "dynamic_obstacle" not in config or config.get("experiment_mode") == "phase1_s1_forward_ray"
            self.chunk_executor = ChunkExecution()
        self.lock = threading.Lock()
        self.done, self.started, self.cancel = threading.Event(), threading.Event(), threading.Event()
        self.state = {"pose": self.core.pose.tolist(), "sim_s": 0., "monotonic_ns": 0, "tick": 0,
                      "applied_id": -1, "command_valid": False}
        self.error = None
        self.reason = "simulation_timeout"
        self.goal_entry = False
        self.minimum_distance = float(np.linalg.norm(self.core.pose[:2]-config["goal_pose"][:2]))
        self.initial_distance = self.minimum_distance
        self.distance = 0.
        self.events, self.received = [], []
        if config.get("experiment_mode") in ("phase1_s1_v2_straight", "phase2_s1_v2"):
            from nomad_phase1.s1_v2 import CorridorOnlyMonitor
            monitor_config = config
            if self.phase2 is not None:
                monitor_config = json.loads(Path(__file__).parents[1].joinpath("nomad_phase1/s1_v2_scenario.json").read_text())
            self.monitor = CorridorOnlyMonitor(monitor_config, out)
        else:
            self.monitor = MultiObstacleMonitor(config, out)
        self.dynamic = None
        if "dynamic_obstacle" in config:
            from .sudden_obstacle import SuddenObstacleMonitor
            self.dynamic = SuddenObstacleMonitor(config, out)
        self.safety = None
        if oracle_safety_stop:
            from .oracle_safety_stop import OracleSafetyStop
            assert self.dynamic is not None and self.dynamic.adaptive and config.get("goal_mode") == "topomap"
            self.safety = OracleSafetyStop(config, out)
        self.graph = None
        self.latest_sample = None
        if online_graph:
            from .online_graph import GraphRecovery
            assert not oracle_safety_stop and self.dynamic is not None
            self.graph = GraphRecovery(config, out)

    def snapshot(self):
        with self.lock:
            return {**self.state, "pose": list(self.state["pose"])}

    def accept(self, result, sim_time, terminal=False):
        metadata, arrays = result
        assert arrays["metric"].shape == arrays["normalized_diffusion"].shape == (8, 8, 2)
        assert all(np.isfinite(a).all() for a in arrays.values())
        np.testing.assert_array_equal(arrays["selected_waypoint"], arrays["metric"][0, 2])
        row = {**metadata, "latched_sim_s": sim_time, "latched_monotonic_ns": time.monotonic_ns(),
               "selected_waypoint_m": arrays["selected_waypoint"].tolist(), "terminal_unapplied": terminal}
        if self.chunk_executor is not None:
            from nomad_phase0.chunk_execution import describe_chunk
            row["chunk"] = describe_chunk(arrays["metric"][0], row["observation_pose"])
        self.received.append(row)
        append(self.rf, row)
        self.monitor.plan(row["id"], arrays["metric"], row)
        if not terminal:
            self.core.receive(row, arrays["selected_waypoint"])
            if self.phase2 is not None:
                self.phase2.accept(row, arrays["metric"])
            if self.graph is not None:
                self.latest_sample = (row["id"], arrays["metric"][0].copy())

    def start(self, client):
        self.client = client
        self.epoch_ns = time.monotonic_ns()
        self.thread = threading.Thread(target=self.run, name="kinematic-72hz", daemon=True)
        self.thread.start()
        self.started.wait(5)
        assert self.started.is_set()

    def run(self):
        c = self.config
        hz = c["integration_hz"]
        self.rf = (self.out/"received.jsonl").open("x")
        try:
            with (self.out/"agent_trajectory.csv").open("x") as pf, (self.out/"controller.jsonl").open("x") as cf, \
                 (self.out/"events.jsonl").open("x") as ef:
                writer = csv.writer(pf)
                writer.writerow(["simulation_time_s", "x_m", "y_m", "yaw_rad", "v_m_s", "w_rad_s", "goal_distance_m",
                                 "monotonic_ns", "tick", "deadline_monotonic_ns", "pacing_error_s", "incoming_waypoint_id", "incoming_command_valid"])
                for tick in range(round(c["timeout_sim_s"]*hz)+1):
                    deadline = deadline_ns(self.epoch_ns, tick, hz)
                    remaining = (deadline-time.monotonic_ns())/1e9
                    if remaining > 0:
                        self.cancel.wait(remaining)  # Only 1x pacing; never inference latency injection.
                    if self.cancel.is_set():
                        self.reason = "technical_cancel"; break
                    previous = self.core.pose.copy()
                    incoming_v, incoming_w = self.core.v, self.core.w
                    incoming_id, incoming_valid = self.core.applied_id, self.core.command_valid
                    if tick:
                        self.core.integrate()
                    now = time.monotonic_ns()
                    pose = self.core.pose.copy()
                    if self.phase2 is not None:
                        self.phase2.integrate_record(previous,pose)
                    sim_time = tick/hz
                    distance = float(np.linalg.norm(pose[:2]-c["goal_pose"][:2]))
                    self.minimum_distance = min(self.minimum_distance, distance)
                    self.distance += float(np.linalg.norm(pose[:2]-previous[:2]))
                    writer.writerow([sim_time, *pose, incoming_v, incoming_w, distance, now, tick, deadline,
                                     (now-deadline)/1e9, incoming_id, incoming_valid])
                    pf.flush()
                    self.monitor.observe_interval(previous, pose, incoming_v, incoming_w,
                                                  (tick-1)/hz if tick else 0., 1/hz if tick else 0.)
                    dynamic_stop = None
                    if self.dynamic is not None:
                        old_received_ns = self.received[incoming_id]["received_monotonic_ns"] if incoming_id >= 0 else None
                        self.dynamic.observe_tick(tick, previous, pose, incoming_v, incoming_w,
                                                  incoming_id, incoming_valid, now, old_received_ns)
                        dynamic_stop = self.dynamic.stop_reason
                    # Publish this tick only after its placement is resolved. Never hold
                    # the snapshot lock during placement, rendering, or inference.
                    with self.lock:
                        self.state = {"pose": pose.tolist(), "sim_s": sim_time, "monotonic_ns": now, "tick": tick,
                                      "applied_id": incoming_id, "command_valid": incoming_valid}
                        if self.dynamic is not None and self.dynamic.adaptive:
                            self.state.update({"resolved_dynamic_obstacle": self.dynamic.obstacle,
                                "dynamic_placement_status": self.dynamic.placement["status"] if self.dynamic.placement else "PENDING"})
                    self.started.set()
                    if self.monitor.stop_reason or dynamic_stop:
                        self.reason = self.monitor.stop_reason or dynamic_stop; break
                    if distance <= c["goal_tolerance_m"]:
                        self.goal_entry = True; self.reason = "goal_entry"; break
                    if (now-self.epoch_ns)/1e9 > c["timeout_navigation_wall_s"]:
                        self.reason = "navigation_wall_timeout"; break
                    if tick == round(c["timeout_sim_s"]*hz):
                        break
                    result = self.client.poll()
                    if result is not None:
                        self.accept(result, sim_time)
                    if self.phase2 is not None:
                        refresh, switch = self.phase2.control(self.core,tick,time.monotonic_ns())
                    else:
                        refresh, switch = self.core.control(tick, time.monotonic_ns())
                    if refresh is not None and self.chunk_executor is not None:
                        self.chunk_executor.apply(self.core, refresh, switch)
                    if refresh is not None and self.safety is not None:
                        box = self.dynamic.obstacle if self.dynamic.spawn is not None else None
                        self.safety.apply(self.core, refresh, switch, tick, box)
                    if refresh is not None and self.graph is not None:
                        box = self.dynamic.obstacle if self.dynamic.spawn is not None else None
                        self.graph.apply(self.core, refresh, switch, tick, box, self.latest_sample)
                    if refresh:
                        append(cf, refresh)
                    if switch:
                        append(ef, switch); self.events.append(switch)
                    with self.lock:
                        self.state["applied_id"] = self.core.applied_id
                        self.state["command_valid"] = self.core.command_valid
        except BaseException as exc:
            self.error = exc
            (self.out/"async_thread_failure.txt").write_text(traceback.format_exc())
        finally:
            if self.safety is not None:
                self.safety.close()
            self.started.set()
            self.done.set()


def run_async(config, out, socket_path, goal, capture, set_pose, get_pose, render_check,
              controlled_delivery_delay=False, uniform_delivery_delay_s=None, oracle_safety_stop=False, online_graph=False,
              pure_pursuit=False):
    if controlled_delivery_delay and uniform_delivery_delay_s is not None:
        raise ValueError("Single-trigger and uniform delivery delays are mutually exclusive")
    phase2 = config.get("experiment_mode") == "phase2_s1_v2"
    s1 = phase2 or config.get("experiment_mode") == "phase1_s1_forward_ray"
    if s1:
        assert pure_pursuit and not oracle_safety_stop and not online_graph and not controlled_delivery_delay
        assert uniform_delivery_delay_s in (0., .25, .5, .75)
    if "dynamic_obstacle" in config and not s1 and (controlled_delivery_delay or uniform_delivery_delay_s not in (None, 0.)):
        raise ValueError("Sudden-obstacle pilot requires zero additional latency")
    protocol = json.loads(Path(__file__).with_name("async_protocol.json").read_text())
    delay = None
    if controlled_delivery_delay:
        from .delivery_delay import SingleDeliveryDelay
        delay_protocol = json.loads(Path(__file__).with_name("controlled_latency_protocol.json").read_text())
        write_json(out/"delivery_delay_protocol.json", delay_protocol)
        delay = SingleDeliveryDelay(delay_protocol)
        protocol["post_inference_result_delivery_delay_s"] = delay_protocol["additional_delivery_delay_s"]
        protocol["waypoint_timeout_clock"] = "host_monotonic_since_controller_side_result_release"
    elif uniform_delivery_delay_s is not None:
        from .delivery_delay import UniformDeliveryDelay
        delay_protocol = json.loads(Path(__file__).with_name("uniform_latency_protocol.json").read_text())
        assert uniform_delivery_delay_s in delay_protocol["conditions_delay_s"].values()
        delay_protocol = {**delay_protocol, "mode": "uniform", "configured_additional_s": uniform_delivery_delay_s}
        write_json(out/"delivery_delay_protocol.json", delay_protocol)
        delay = UniformDeliveryDelay(delay_protocol)
        protocol["post_inference_result_delivery_delay_s"] = uniform_delivery_delay_s
        protocol["waypoint_timeout_clock"] = "host_monotonic_since_controller_side_result_release"
    write_json(out/"async_protocol.json", protocol)
    if oracle_safety_stop:
        assert not controlled_delivery_delay and uniform_delivery_delay_s is None
    engine = ExecutionThread(config, out, oracle_safety_stop=oracle_safety_stop, online_graph=online_graph,
                             pure_pursuit=pure_pursuit)
    if pure_pursuit:
        write_json(out/"chunk_pilot_protocol.json", (engine.phase2 or engine.chunk_executor).settings)
    history, times, hashes, frame_ids = (deque(maxlen=4) for _ in range(4))
    dynamic_history = deque(maxlen=4)
    oracle_gate = None
    if s1 and engine.dynamic is not None:
        from nomad_phase1.s1 import VisibilityGate
        oracle_gate = VisibilityGate()
    save_observations = engine.dynamic is not None or config.get("goal_mode") == "topomap"
    if save_observations:
        (out/"observations").mkdir(exist_ok=False)
    observation_id = request_id = 0
    busy_skips = missed_slots = 0
    with socket.socket(socket.AF_UNIX) as connection, (out/"observations.jsonl").open("x") as obs_log, \
         (out/"requests.jsonl").open("x") as req_log:
        connection.settimeout(60)
        connection.connect(socket_path)
        client = AsyncClient(connection, engine.snapshot, delivery_delay=delay)
        engine.start(client)
        slot = 0
        try:
            while not engine.done.is_set():
                target = deadline_ns(engine.epoch_ns, slot, config["observation_hz"])
                remaining = (target-time.monotonic_ns())/1e9
                if remaining > 0 and engine.done.wait(remaining):
                    break
                snap = engine.snapshot()
                if engine.done.is_set():
                    break
                set_pose(snap["pose"])
                np.testing.assert_allclose(get_pose(), snap["pose"], atol=1e-10, rtol=0)
                if hasattr(capture, "sync_dynamic"):
                    capture.sync_dynamic(snap)
                capture_start = time.monotonic_ns()
                rgb = capture(snap["sim_s"])
                capture_end = time.monotonic_ns()
                np.testing.assert_allclose(get_pose(), snap["pose"], atol=1e-10, rtol=0)
                digest = hashlib.sha256(rgb.tobytes()).hexdigest()
                history.append(rgb); times.append(snap["sim_s"]); hashes.append(digest); frame_ids.append(observation_id)
                record = {"observation_id": observation_id, "slot": slot, "scheduled_monotonic_ns": target,
                          "observation_sim_s": snap["sim_s"], "observation_monotonic_ns": capture_start,
                          "observation_pose": snap["pose"], "pose_sample_monotonic_ns": snap["monotonic_ns"],
                          "capture_end_monotonic_ns": capture_end, "render_ms": (capture_end-capture_start)/1e6,
                          "frame_sha256": digest}
                if save_observations:
                    record["rgb_file"] = f"observations/{observation_id:04d}.png"
                if engine.dynamic is not None:
                    diagnostic = dict(capture.dynamic_metadata)
                    assert diagnostic["capture_tick"] == snap["tick"]
                    record.update({"dynamic": diagnostic, "rgb_file": f"observations/{observation_id:04d}.png",
                                   "dynamic_mask_file": f"observations/{observation_id:04d}_mask.png"})
                    dynamic_history.append(diagnostic)
                if oracle_gate is not None:
                    record["oracle_information"] = oracle_gate.observe(record)
                    if engine.phase2 is not None:
                        engine.phase2.publish(record["oracle_information"], engine.dynamic.obstacle)
                if len(history) == 4 and not engine.done.is_set():
                    request = {**record, "kind": "infer", "id": request_id, "seed": request_seed(config, request_id),
                               "history_sim_s": list(times), "history_frame_sha256": list(hashes),
                               "history_observation_ids": list(frame_ids), "old_id_at_observation": snap["applied_id"],
                               "old_valid_at_observation": snap["command_valid"], "request_submit_monotonic_ns": time.monotonic_ns()}
                    if config.get("seed_offset") or config.get("run_id") is not None:
                        request.update(run_id=config.get("run_id"), seed_offset=config.get("seed_offset", 0))
                    if engine.dynamic is not None:
                        request["history_dynamic"] = list(dynamic_history)
                    inputs = {"history": np.stack(history)}
                    if config.get("goal_mode") != "topomap":
                        inputs["goal"] = goal
                    submitted = client.submit(request, **inputs)
                    record["status"] = "submitted" if submitted else "busy_history_only"
                    if submitted:
                        record["request_id"] = request_id
                        append(req_log, request); request_id += 1
                    else:
                        busy_skips += 1
                else:
                    record["status"] = "history_warmup" if len(history)<4 else "terminal_history_only"
                if save_observations:
                    Image.fromarray(rgb).save(out/record["rgb_file"])
                if engine.dynamic is not None:
                    Image.fromarray(capture.dynamic_mask.astype(np.uint8)*255).save(out/record["dynamic_mask_file"])
                append(obs_log, record)
                if slot % (5*config["observation_hz"]) == 0:
                    Image.fromarray(rgb).save(out/f"observation_{observation_id:04d}.png")
                observation_id += 1
                slot += 1
                elapsed = (time.monotonic_ns()-engine.epoch_ns)/1e9
                next_available = int(np.ceil(elapsed*config["observation_hz"]))
                if next_available > slot:
                    append(obs_log, {"status": "missed_capture_slots", "first_slot": slot,
                                     "count": next_available-slot, "monotonic_ns": time.monotonic_ns()})
                    missed_slots += next_available-slot
                    slot = next_available
            engine.thread.join(5)
            if engine.error:
                raise RuntimeError("Kinematic execution thread failed") from engine.error
            leftover = client.close()
            if leftover is not None:
                engine.accept(leftover, engine.snapshot()["sim_s"], terminal=True)
        finally:
            engine.cancel.set()
            engine.thread.join(5)
            engine.rf.close()
            if engine.phase2 is not None:
                engine.phase2.close()
            if engine.graph is not None:
                engine.graph.close()  # After navigation; pending result cannot move the agent.
        state = engine.snapshot()
        set_pose(state["pose"])
        if hasattr(capture, "sync_dynamic"):
            capture.sync_dynamic(state)
        final_rgb = capture(state["sim_s"])
        final_capture_end = time.monotonic_ns()
        Image.fromarray(final_rgb).save(out/"observation_final.png")
        if oracle_gate is not None:
            final_record = {"observation_id": observation_id, "status": "terminal_capture_no_request",
                "observation_sim_s": state["sim_s"], "observation_pose": state["pose"],
                "capture_end_monotonic_ns": final_capture_end, "rgb_file": "observation_final.png",
                "frame_sha256": hashlib.sha256(final_rgb.tobytes()).hexdigest(),
                "dynamic": dict(capture.dynamic_metadata)}
            final_record["oracle_information"] = oracle_gate.observe(final_record)
            append(obs_log, final_record)
            write_json(out/"oracle_information.json", final_record["oracle_information"])
    obstacle_result = engine.monitor.finish(engine.goal_entry)
    dynamic_result = engine.dynamic.finish(engine.goal_entry) if engine.dynamic is not None else None
    summary = {"integration_success": bool(engine.events) and engine.distance > 0,
               "execution_mode": "asynchronous_realtime_kinematic", "scenario": config,
               "epoch_monotonic_ns": engine.epoch_ns, "simulation_duration_s": state["sim_s"],
               "navigation_wall_seconds": (state["monotonic_ns"]-engine.epoch_ns)/1e9,
               "goal_entry": engine.goal_entry, "termination_reason": engine.reason,
               "minimum_goal_distance_m": engine.minimum_distance, "initial_goal_distance_m": engine.initial_distance,
               "final_pose": state["pose"], "final_goal_distance_m": float(np.linalg.norm(np.array(state["pose"][:2])-config["goal_pose"][:2])),
               "distance_travelled_m": engine.distance, "inference_count": request_id, "received_count": len(engine.received),
               "applied_waypoints": len(engine.events), "busy_observation_skips": busy_skips, "missed_capture_slots": missed_slots,
               "waypoint_timeout_episodes": len(engine.core.expired_ids), "simulation_paused_during_inference": False,
               "all_outputs_finite": True, "frame_and_rgb_check": render_check, "obstacle_evaluation": obstacle_result,
               "raw_model_output_directory": "model/raw", "derived_trajectory_directory": "model/derived",
               "note": "Pacing and concurrent OLD movement require offline validation; this file alone is not a realtime PASS."}
    if oracle_safety_stop:
        summary["oracle_safety_stop_enabled"] = True
        summary["command_semantics"] = "controller/events v,w are nominal PD; applied_v,w and 72Hz trace are actual"
    if pure_pursuit:
        summary["pure_pursuit_enabled"] = True
        summary["experiment_label"] = "PILOT"
        summary["command_semantics"] = "controller/events v,w are original index-2 PD reference ONLY; applied_v,w and 72Hz trace are actual Pure Pursuit commands"
    if online_graph:
        summary["online_graph_enabled"] = True
        summary["graph_submitted_requests"] = engine.graph.next_id
        summary["command_semantics"] = "controller/events remain nominal; actual overrides and separate Graph actions are in graph_control.jsonl"
    if config.get("run_id") is not None:
        summary.update(experiment_label="PHASE0_D_S0_BATCH", run_id=config["run_id"],
                       seed_offset=config.get("seed_offset", 0))
    if dynamic_result is not None:
        summary["dynamic_obstacle"] = dynamic_result
        summary["obstacle_evaluation_scope"] = "Original static obstacles only; dynamic evaluation is separate"
        summary["combined_avoidance_success"] = bool(obstacle_result["avoidance_success"] and
            dynamic_result["status"] == "SPAWNED" and dynamic_result["evaluation"]["avoidance_success"])
    if uniform_delivery_delay_s is not None:
        summary["delivery_delay"] = {"mode": "uniform", "accepted_count": delay.accepted_count,
                                     "configured_additional_s": uniform_delivery_delay_s}
    elif delay is not None:
        summary["delivery_delay"] = {"triggered_id": delay.triggered_id,
                                     "status": "TRIGGERED" if delay.triggered_id is not None else "NOT_TRIGGERED",
                                     "configured_additional_s": delay.protocol["additional_delivery_delay_s"]}
    if s1:
        summary["experiment_label"] = "PHASE2_EXPLORATORY" if phase2 else "PHASE1_S1_PREFLIGHT_PILOT"
    write_json(out/"summary.json", summary)
    print("ASYNC_NAVIGATION_RESULT "+json.dumps(summary), flush=True)
