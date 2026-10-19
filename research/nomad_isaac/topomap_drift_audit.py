"""Stored-data-only Topomap drift diagnosis. No rendering, inference, or plots."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .async_report import rows
from .clearance import (configured_obstacles, corridor_clearance, obstacle_bounds,
                        single_obstacle_config, swept_clearance)
from .common import ROOT, integrate_se2, local_to_world, original_controller, sha256_file, write_json
from .handoff_audit import angle, arc_coordinates, path_safety
from .topomap import candidate_range, select_subgoal
from .topomap_report import validate_map


class ReferenceProjection:
    """Global nearest segment; no time alignment or policy/world-pose feedback."""
    def __init__(self, xy):
        self.arc = arc_coordinates(xy)
        delta = np.diff(xy, axis=0)
        length = np.linalg.norm(delta, axis=1)
        self.indices = np.flatnonzero(length > 1e-9)
        self.a = xy[:-1][self.indices]
        self.d = delta[self.indices]
        self.length = length[self.indices]

    def __call__(self, point):
        u = np.clip(np.sum((point - self.a) * self.d, axis=1) / self.length**2, 0, 1)
        projected = self.a + u[:, None] * self.d
        distance = np.linalg.norm(point - projected, axis=1)
        i = int(np.argmin(distance))  # Earliest segment on an exact tie.
        s = self.arc[self.indices] + u * self.length
        tangent = self.d[i] / self.length[i]
        residual = point - projected[i]
        near = distance <= distance[i] + .001
        spread = float(np.ptp(s[near]))
        return {"distance_m": float(distance[i]),
                "signed_lateral_m": float(tangent[0]*residual[1] - tangent[1]*residual[0]),
                "longitudinal_residual_m": float(tangent @ residual),
                "reference_arc_m": float(s[i]), "projection_xy": projected[i].tolist(),
                "reference_segment_row": int(self.indices[i]),
                "tangent_rad": float(np.arctan2(tangent[1], tangent[0])),
                "near_equal_projection_arc_spread_m": spread,
                "ambiguous": spread > .10}


def read_trace(path):
    with path.open() as stream:
        records = list(csv.DictReader(stream))
    pose = np.array([[float(r[k]) for k in ("x_m", "y_m", "yaw_rad")] for r in records])
    return records, pose


def table(path, records):
    with path.open("x") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({k: json.dumps(v, separators=(",", ":")) if isinstance(v, (list, dict)) else v
                             for k, v in record.items()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--topomap", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists(), "Never overwrite an existing analysis"
    run = args.run.resolve()
    manifest, map_check = validate_map(args.topomap)
    reference = Path(manifest["source_run"])
    old_results = ROOT / "research/results/isaac6_topomap_20261019"
    previous_hashes = json.loads((run.parent/"topomap_static_01_validation/runtime_validation/input_hashes.json").read_text())
    inputs = {str(run/name): digest for name, digest in previous_hashes.items()}
    for path in [run/"clearance.jsonl", args.topomap, reference/"agent_trajectory.csv",
                 *old_results.glob("*"), *(run/"observations").glob("*.png"),
                 *(args.topomap.parent/"rgb").glob("*.png")]:
        inputs[str(path.resolve())] = sha256_file(path)
    assert all(sha256_file(path) == digest for path, digest in inputs.items())
    review = json.loads((old_results/"review.json").read_text())
    for name, digest in review["result_sha256"].items():
        assert sha256_file(old_results/name) == digest

    config = json.loads((run/"scenario.json").read_text())
    summary_run = json.loads((run/"summary.json").read_text())
    records, poses = read_trace(run/"agent_trajectory.csv")
    _, reference_poses = read_trace(reference/"agent_trajectory.csv")
    projection = ReferenceProjection(reference_poses[:, :2])
    projected = [projection(p[:2]) for p in poses]
    times = np.array([float(r["simulation_time_s"]) for r in records])
    hz = config["integration_hz"]
    np.testing.assert_allclose(times, np.arange(len(times))/hz, atol=1e-12, rtol=0)
    distances = np.array([p["distance_m"] for p in projected])
    crossing = int(np.flatnonzero((times <= 12) & (distances > .20))[0])
    events, observations, inference, received, controls, clearance = (
        rows(run/name) for name in ("events.jsonl", "observations.jsonl", "model/inference.jsonl",
                                   "received.jsonl", "controller.jsonl", "clearance.jsonl"))
    with (old_results/"topomap_selection.csv").open() as stream:
        saved_selection = list(csv.DictReader(stream))
    assert [e["id"] for e in events] == list(range(len(events)))
    assert len(events) == len(inference) == len(saved_selection)
    controller = original_controller()
    nodes = np.array([n["world_pose"] for n in manifest["nodes"]])
    node_arc = projection.arc[[n["reference_pose_row"] for n in manifest["nodes"]]]
    frames = {}
    for obs in observations:
        with Image.open(run/obs["rgb_file"]) as image:
            frame = np.asarray(image).copy()
        assert hashlib.sha256(frame.tobytes()).hexdigest() == obs["frame_sha256"]
        frames[obs["observation_id"]] = frame
    max_pose_error = max_clearance_error = max_controller_error = 0.
    for tick in range(1, len(records)):
        v, w = (float(records[tick][k]) for k in ("v_m_s", "w_rad_s"))
        expected = integrate_se2(poses[tick-1], v, w, 1/hz)
        max_pose_error = max(max_pose_error, float(np.max(abs(expected-poses[tick]))))
        corridor = corridor_clearance(poses[tick-1], poses[tick], v, w, 1/hz,
                                       config["corridor"], config["agent_radius_m"])
        max_clearance_error = max(max_clearance_error, abs(corridor-clearance[tick]["corridor_lower_m"]))
        for obstacle in configured_obstacles(config):
            lo, hi = obstacle_bounds(single_obstacle_config(config, obstacle))
            swept = swept_clearance(poses[tick-1], v, w, 1/hz, lo, hi, config["agent_radius_m"])
            max_clearance_error = max(max_clearance_error,
                abs(swept["lower_m"]-clearance[tick]["obstacles"][obstacle["id"]]["lower_m"]))
    for control in controls:
        expected = controller(received[control["waypoint_id"]]["selected_waypoint_m"]) if control["valid"] else (0., 0.)
        max_controller_error = max(max_controller_error,
            float(np.max(abs(np.asarray(expected)-[control["v_m_s"], control["w_rad_s"]]))))

    predictions, details = [], {}
    focus = set(range(26, 39)) | {21, 22, 23, 24, 25, 39, 40, 41, 42, 43, 44}
    previous_closest = 0
    for index, event in enumerate(events):
        identifier = event["id"]
        obs = np.array(event["observation_pose"])
        boundary = np.array(event["agent_pose_at_switch"])
        obs_tick = round(event["observation_sim_s"]*hz)
        start = round(event["application_sim_s"]*hz)
        end = round(events[index+1]["application_sim_s"]*hz) if index+1 < len(events) else len(records)-1
        np.testing.assert_array_equal(obs, poses[obs_tick])
        np.testing.assert_array_equal(boundary, poses[start])
        assert all(int(r["incoming_waypoint_id"]) == identifier for r in records[start+1:end+1])
        top = event["topomap"]
        assert top == inference[index]["topomap"] == received[index]["topomap"]
        a, b = candidate_range(previous_closest, len(nodes)-1)
        assert top["candidate_ids"] == list(range(a, b+1))
        closest, subgoal, _ = select_subgoal(top["distances"], a)
        assert closest == top["closest_node"] == int(saved_selection[index]["closest_node"])
        assert subgoal == top["selected_subgoal_id"] == int(saved_selection[index]["subgoal_id"])
        np.testing.assert_array_equal(top["distances"], json.loads(saved_selection[index]["distance_scores"]))
        previous_closest = closest
        history = np.stack([frames[i] for i in event["history_observation_ids"]])
        assert hashlib.sha256(history.tobytes()).hexdigest() == event["history_sha256"]
        with np.load(run/f"model/derived/{identifier:04d}.npz", allow_pickle=False) as data:
            assert data["metric"].shape == (8, 8, 2) and np.isfinite(data["metric"]).all()
            local = data["metric"][0].copy()
            np.testing.assert_array_equal(data["selected_waypoint"], local[2])
            np.testing.assert_array_equal(data["metric"], data["cumulative"]*.05)
        np.testing.assert_array_equal(local[2], event["selected_waypoint_m"])
        v, w = controller(event["selected_waypoint_m"])
        np.testing.assert_allclose([v, w], [event["v_m_s"], event["w_rad_s"]], atol=1e-12, rtol=0)
        for tick in range(start+1, end+1):
            np.testing.assert_allclose([float(records[tick][k]) for k in ("v_m_s", "w_rad_s")], [v, w], atol=1e-12, rtol=0)
        dx, dy = event["selected_waypoint_m"]
        v_raw = dx/.25 if abs(dx) >= 1e-8 else 0.
        w_raw = float(np.arctan(dy/dx)/.25) if abs(dx) >= 1e-8 else float(np.sign(dy)*np.pi/.5)
        world = local_to_world(local, obs)
        native_projection = [projection(point) for point in world]
        po, ps, pe = projected[obs_tick], projected[start], projected[end]
        nearest_distance = np.linalg.norm(nodes[:, :2]-obs[:2], axis=1)
        nearest = int(np.argmin(nearest_distance))
        nearest_ids = np.flatnonzero(nearest_distance <= nearest_distance[nearest]+.001).tolist()
        rel = nodes[subgoal, :2]-obs[:2]
        tangent = np.array([np.cos(po["tangent_rad"]), np.sin(po["tangent_rad"])])
        forward = np.array([np.cos(obs[2]), np.sin(obs[2])])
        native_full = path_safety(world, config)
        native_prefix = path_safety(np.vstack([obs[:2], world[:3]]), config)
        old = events[index-1] if index else None
        row = {"id": identifier, "observation_sim_s": event["observation_sim_s"],
               "ready_wall_since_epoch_s": (event["ready_monotonic_ns"]-summary_run["epoch_monotonic_ns"])/1e9,
               "switch_sim_s": event["application_sim_s"], "end_sim_s": float(times[end]),
               "observation_pose": obs.tolist(), "switch_pose": boundary.tolist(),
               "obs_cross_track_m": po["signed_lateral_m"], "switch_cross_track_m": ps["signed_lateral_m"],
               "end_cross_track_m": pe["signed_lateral_m"],
               "execution_cross_track_change_m": pe["signed_lateral_m"]-ps["signed_lateral_m"],
               "closest_node": closest, "subgoal_id": subgoal,
               "previous_closest": top["previous_closest_node"], "previous_subgoal": top["previous_subgoal_id"],
               "closest_backward": top["closest_moved_backward"], "subgoal_backward": top["subgoal_moved_backward"],
               "closest_pose": nodes[closest].tolist(), "subgoal_pose": nodes[subgoal].tolist(),
               "offline_nearest_node_ids_1mm": nearest_ids, "offline_nearest_node_distance_m": float(nearest_distance[nearest]),
               "candidate_ids": top["candidate_ids"], "distance_scores": top["distances"],
               "minimum_score": min(top["distances"]),
               "nearest_node_score_if_candidate": top["distances"][nearest-a] if a <= nearest <= b else None,
               "subgoal_arc_ahead_observation_m": float(node_arc[subgoal]-po["reference_arc_m"]),
               "subgoal_arc_ahead_switch_m": float(node_arc[subgoal]-ps["reference_arc_m"]),
               "subgoal_ref_tangent_forward_m": float(rel @ tangent),
               "subgoal_body_forward_m": float(rel @ forward),
               "subgoal_body_left_m": float(rel @ np.array([-forward[1], forward[0]])),
               "reference_heading_at_switch_deg": float(np.degrees(ps["tangent_rad"])),
               "robot_minus_reference_heading_deg": float(np.degrees(angle(boundary[2], ps["tangent_rad"]))),
               "dx_m": dx, "dy_m": dy, "v_unclipped": v_raw, "w_unclipped": w_raw,
               "v_m_s": float(v), "w_rad_s": float(w), "v_clipped": bool(v_raw != v), "w_clipped": bool(w_raw != w),
               "turn_reversal": bool(old and old["w_rad_s"]*w < 0),
               "same_subgoal_as_previous": bool(old and old["topomap"]["selected_subgoal_id"] == subgoal),
               "observation_displacement_m": float(np.linalg.norm(obs[:2]-np.array(old["observation_pose"])[:2])) if old else None,
               "observation_yaw_change_deg": float(np.degrees(angle(obs[2], old["observation_pose"][2]))) if old else None,
               "observation_rgb_l1_change_0_255": float(np.abs(frames[event["observation_id"]].astype(float)-frames[old["observation_id"]].astype(float)).mean()) if old else None,
               "seed": event["seed"], "history_ids": event["history_observation_ids"],
               "native_selected_cross_track_m": native_projection[2]["signed_lateral_m"],
               "native_final_cross_track_m": native_projection[-1]["signed_lateral_m"],
               "native_full_clearance_m": native_full["obstacle_clearance_m"],
               "native_full_corridor_m": native_full["corridor_clearance_m"],
               "native_origin_prefix_clearance_m": native_prefix["obstacle_clearance_m"],
               "execution_obstacle_clearance_m": min(c["lower_m"] for c in clearance[start+1:end+1]),
               "execution_corridor_clearance_m": min(c["corridor_lower_m"] for c in clearance[start+1:end+1]),
               "obs_to_switch_xy_m": float(np.linalg.norm(boundary[:2]-obs[:2])),
               "obs_to_switch_yaw_deg": float(np.degrees(angle(boundary[2], obs[2]))),
               "projection_ambiguous": po["ambiguous"] or ps["ambiguous"]}
        predictions.append(row)
        if identifier in focus:
            details[str(identifier)] = {"sample0_local_xy_m": local.tolist(), "sample0_observation_anchored_world_xy_m": world.tolist(),
                "native_point_cross_track_m": [p["signed_lateral_m"] for p in native_projection],
                "native_full_safety": native_full, "native_observation_origin_prefix_safety": native_prefix,
                "history_rgb_sha256": event["history_sha256"], "subgoal_rgb_sha256": event["goal_sha256"],
                "executed_trace_row_range_inclusive": [start, end], "executed_end_pose": poses[end].tolist(),
                "note": "Stored actual PD arc is trace[start:end+1]; native polyline is not that arc."}

    assert max_pose_error < 1e-12 and max_controller_error < 1e-12 and max_clearance_error < 1e-12
    before = max((e for e in events if e["application_sim_s"] <= times[crossing]), key=lambda e: e["application_sim_s"])
    after = min((e for e in events if e["application_sim_s"] > times[crossing]), key=lambda e: e["application_sim_s"])
    ob_before = max((o for o in observations if o["observation_sim_s"] <= times[crossing]), key=lambda o:o["observation_sim_s"])
    ob_after = min((o for o in observations if o["observation_sim_s"] > times[crossing]), key=lambda o:o["observation_sim_s"])
    active = predictions[before["id"]]
    tick_ns = int(records[crossing]["monotonic_ns"])
    received_at_crossing = [e["id"] for e in received if e["received_monotonic_ns"] <= tick_ns]
    checkpoints = sorted(set(range(0, len(records), hz//config["controller_hz"])) |
                         {crossing-1, crossing, len(records)-1} | set(range(0, len(records), hz)))
    trace_table = [{"tick": i, "simulation_time_s": float(times[i]), "pose": poses[i].tolist(),
        "incoming_prediction_id": int(records[i]["incoming_waypoint_id"]), **projected[i]} for i in checkpoints]
    # Inclusive trace boundary row stores the preceding incoming command, not the command newly switched there.
    report = {"status": "OFFLINE_NUMERICAL_VALIDATION_PASS", "causal_attribution": "INSUFFICIENT_EVIDENCE",
        "protocol": {"deviation_threshold_m": .20, "primary_interval_sim_s": [0,12], "focus_interval_sim_s": [7,12],
            "projection": "Global nearest point on all nonzero reference 72Hz polyline segments; earliest exact tie; no equal-time matching",
            "sign": "Left of reference travel tangent is positive; threshold uses Euclidean point-to-polyline distance",
            "ambiguity_rule": "Projections within 0.001m of minimum spanning >0.10m of reference arclength",
            "zero_segment_epsilon_m": 1e-9, "native_world_anchor": "each prediction observation pose",
            "scores": "Learned distance-head units; not metric distance", "nearest_node": "offline geometric diagnostic, not policy ground truth",
            "ready_clock": "Host monotonic elapsed since epoch; not inferred simulation time",
            "evaluation_only": "No new navigation, inference, counterfactual rollout, plot, test, model/controller/scenario/parameter change"},
        "first_exceedance": {"simulation_s": float(times[crossing]), "tick": crossing, "pose": poses[crossing].tolist(),
            "projection": projected[crossing], "previous_tick_sim_s": float(times[crossing-1]),
            "previous_tick_distance_m": float(distances[crossing-1]), "applied_prediction_id": before["id"],
            "active_prediction": active, "next_switch_id": after["id"], "next_switch_sim_s": after["application_sim_s"],
            "observation_before": ob_before, "observation_after": ob_after,
            "latest_received_prediction_at_crossing": received_at_crossing[-1],
            "remaining_samples_to_12s": int(sum((times>=times[crossing]) & (times<=12))),
            "all_remaining_samples_to_12s_above_threshold": bool(np.all(distances[(times>=times[crossing]) & (times<=12)] > .20)),
            "all_remaining_samples_to_end_above_threshold": bool(np.all(distances[crossing:] > .20)),
            "at_12s_m": float(distances[12*hz]), "at_end_m": float(distances[-1])},
        "closest_backward_events": [{k:r[k] for k in ("id", "observation_sim_s", "switch_sim_s", "previous_closest", "closest_node", "switch_cross_track_m")}
                                    for r in predictions if r["closest_backward"]],
        "subgoal_backward_events": [{k:r[k] for k in ("id", "switch_sim_s", "previous_subgoal", "subgoal_id", "switch_cross_track_m")}
                                    for r in predictions if r["subgoal_backward"]],
        "same_subgoal_turn_reversal_ids": [r["id"] for r in predictions if r["turn_reversal"] and r["same_subgoal_as_previous"]],
        "ambiguity": {"all_trace_ambiguous_count": sum(p["ambiguous"] for p in projected),
            "primary_ambiguous_count": sum(p["ambiguous"] for p,t in zip(projected,times) if t<=12),
            "maximum_near_equal_arc_spread_m": max(p["near_equal_projection_arc_spread_m"] for p in projected),
            "maximum_primary_longitudinal_projection_residual_m": max(abs(p["longitudinal_residual_m"]) for p,t in zip(projected,times) if t<=12),
            "zero_length_reference_segments_skipped": len(reference_poses)-1-len(projection.indices),
            "node_0_1_coincident": bool(np.array_equal(nodes[0], nodes[1]))},
        "validation": {"map": map_check, "previous_run_hashes_verified": len(previous_hashes),
            "all_input_hashes_preserved": len(inputs), "pose_integration_max_error": max_pose_error,
            "original_pd_max_error": max_controller_error, "swept_and_corridor_max_error_m": max_clearance_error,
            "selection_history_hashes_and_sample0_index2": "PASS", "actual_prediction_intervals": len(events),
            "existing_figure": str(old_results/"topomap_navigation.svg")},
        "inputs_sha256": inputs}
    assert all(sha256_file(path) == digest for path, digest in inputs.items())
    args.out.mkdir(parents=True, exist_ok=False)
    table(args.out/"prediction_diagnosis.csv", predictions)
    table(args.out/"reference_projection_checkpoints.csv", trace_table)
    write_json(args.out/"summary.json", report)
    write_json(args.out/"focused_native_paths.json", details)
    print(json.dumps({"first_exceedance_s": float(times[crossing]), "prediction_id": before["id"],
                      "max_pose_error": max_pose_error, "max_pd_error": max_controller_error,
                      "max_clearance_error": max_clearance_error, "out": str(args.out)}))


if __name__ == "__main__":
    main()
