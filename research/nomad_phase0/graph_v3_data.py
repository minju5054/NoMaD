"""Read-only fixed handoff set and RGB-derived information availability."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from nomad_isaac.async_report import rows
from nomad_isaac.common import ROOT, integrate_se2, local_to_world, original_controller, sha256_file
from nomad_isaac.old_rollout_placement import magenta_mask
from nomad_phase1.s1 import VisibilityGate
from .chunk_report import trace
from .graph_v3 import rollout

ARTIFACTS = ROOT.parent/"artifacts/isaac6"
V2 = ROOT/"research/results/graph_v2_offline_pilot_20261020"


def visible_at_boundary(information, boundary_host_ns):
    available = information["available_from"]
    return available is not None and available["capture_end_monotonic_ns"] <= boundary_host_ns


def visibility(run, track):
    gate = VisibilityGate()
    for obs in rows(track(run/"observations.jsonl")):
        if "observation_id" not in obs:
            continue
        file = track(run/obs["rgb_file"])
        rgb = np.array(Image.open(file).convert("RGB"))
        assert hashlib.sha256(rgb.tobytes()).hexdigest() == obs["frame_sha256"]
        mask = magenta_mask(rgb)
        assert int(mask.sum()) == obs["dynamic"]["magenta_pixels"]
        assert obs["dynamic"]["visible"] == (obs["dynamic"]["active"] and mask.sum() >= 20)
        info = gate.observe(obs)
        if "oracle_information" in obs:
            assert info == obs["oracle_information"]
    assert info["first_visible"] is not None and info["available_from"] is not None
    return info


def build_selection(protocol):
    hashes = {}; cache = {}; verification = []; cases = []

    def track(path):
        path = Path(path).resolve()
        if str(path) not in hashes:
            hashes[str(path)] = sha256_file(path)  # Missing input aborts, never regenerate.
        return path

    def existing_hashes(path, source=None):
        for file, digest in json.loads(track(path).read_text()).items():
            f = (source/file if source else Path(file)).resolve()
            assert sha256_file(f) == digest, str(f)
            track(f)

    s0 = json.loads(track(V2/"selection.json").read_text())
    for file, digest in s0["input_sha256"].items():
        assert sha256_file(file) == digest, file
        track(file)
    published = [
        (ROOT/"research/results/phase1_s1_preflight_20261022/P0/input_hashes.json", ARTIFACTS/"phase1_s1_preflight_01/P0"),
        (ROOT/"research/results/isaac6_old_rollout_obstacle_20261018/input_hashes.json", ARTIFACTS/"old_rollout_obstacle_01"),
        (ARTIFACTS/"topomap_sudden_01_validation/input_hashes.json", ARTIFACTS/"topomap_sudden_01"),
        (ARTIFACTS/"early_graph_comparison_02/EARLY-RAW/input_hashes.json", ARTIFACTS/"early_raw_01")]
    for path, source in published:
        existing_hashes(path, source)

    def load_run(run):
        run = Path(run)
        if str(run) in cache:
            return cache[str(run)]
        for name in ("scenario.json", "summary.json", "provenance.json", "events.jsonl", "controller.jsonl",
                     "agent_trajectory.csv", "received.jsonl", "requests.jsonl", "model/inference.jsonl", "clearance.jsonl"):
            track(run/name)
        config = json.loads((run/"scenario.json").read_text())
        summary = json.loads((run/"summary.json").read_text())
        event, control, received = (rows(run/n) for n in ("events.jsonl", "controller.jsonl", "received.jsonl"))
        records, poses = trace(run)
        info = visibility(run, track) if "dynamic_obstacle" in config else None
        cache[str(run)] = (config, summary, event, control, received, records, poses, info)
        return cache[str(run)]

    def case(run, identifier, dataset, case_id, reused=None):
        config, summary, events, control, received, records, poses, info = load_run(run)
        run = Path(run)
        i = next(j for j, e in enumerate(events) if e["id"] == identifier)
        assert i > 0
        e, old = events[i], events[i-1]
        tick = round(e["application_sim_s"]*72)
        next_tick = round(events[i+1]["application_sim_s"]*72) if i+1 < len(events) else None
        end_tick = next_tick if next_tick is not None else len(poses)-1
        ticks = end_tick-tick
        assert ticks > 0 and tick % 8 == 0
        before, after = control[tick//8-1], control[tick//8]
        assert before["valid"] and after["valid"]
        assert before["waypoint_id"] == old["id"] and after["waypoint_id"] == identifier
        pp = summary.get("pure_pursuit_enabled", False)
        fields = ("applied_v_m_s", "applied_w_rad_s") if pp else ("v_m_s", "w_rad_s")
        previous = [before[k] for k in fields]
        actual = [after[k] for k in fields]
        for ev in (old, e):
            np.testing.assert_array_equal(poses[round(ev["observation_sim_s"]*72)], ev["observation_pose"])
        np.testing.assert_array_equal(poses[tick], e["agent_pose_at_switch"])
        worlds = []
        for ev in (old, e):
            path = track(run/f"model/derived/{ev['id']:04d}.npz")
            track(run/f"model/raw/{ev['id']:04d}.npz")
            with np.load(path, allow_pickle=False) as data:
                assert data["metric"].shape == (8, 8, 2) and np.isfinite(data["metric"]).all()
                local = data["metric"][0].copy()
                world = local_to_world(local, np.array(ev["observation_pose"]))
            if pp:
                np.testing.assert_allclose(world, ev["chunk"]["world_xy_m"], atol=1e-12, rtol=0)
            worlds.append(world)
        true_config = {**config, "obstacles": list(config["obstacles"])}
        public_config = {**true_config, "obstacles": list(config["obstacles"])}
        if info:
            box = summary["dynamic_obstacle"]["spawn"]["obstacle"]
            assert tick >= box["spawn_tick"]
            true_config["obstacles"].append(box)
            if visible_at_boundary(info, e["application_monotonic_ns"]):
                public_config["obstacles"].append(box)
        raw = rollout(worlds[1], poses[tick], previous, true_config, protocol, ticks)
        pose_error = 0.
        for j in range(tick+1, end_tick+1):
            stored = [float(records[j][k]) for k in ("v_m_s", "w_rad_s")]
            expected = [control[(j-1)//8][k] for k in fields]
            np.testing.assert_allclose(stored, expected, atol=1e-12, rtol=0)
            pose_error = max(pose_error, float(np.max(abs(integrate_se2(poses[j-1], *stored, 1/72)-poses[j]))))
        assert pose_error < 1e-10
        if pp:
            np.testing.assert_allclose(raw["first_command_vw"], actual, atol=1e-10, rtol=0)
            np.testing.assert_allclose(raw["poses"], poses[tick:end_tick+1], atol=1e-10, rtol=0)
            pp_error = float(np.max(abs(np.array(raw["first_command_vw"])-actual)))
            static_log = rows(run/"clearance.jsonl")[tick+1:end_tick+1]
            for box in config["obstacles"]:
                gap = min(row["obstacles"][box["id"]]["lower_m"] for row in static_log)
                assert abs(gap-raw["obstacles"][box["id"]]) < 1e-10
        else:
            selected = received[identifier]["selected_waypoint_m"]
            np.testing.assert_allclose(original_controller()(selected), actual, atol=1e-12, rtol=0)
            pp_error = None
        record = {"case_id": case_id, "dataset": dataset, "source_run": str(run), "old_id": old["id"],
            "fresh_id": identifier, "source_controller": "PP" if pp else "PD_COUNTERFACTUAL_PP_EVALUATION",
            "source_execution_sha": json.loads((run/"provenance.json").read_text())["git_sha"],
            "observation_pose": e["observation_pose"], "observation_sim_s": e["observation_sim_s"],
            "boundary": poses[tick].tolist(), "switch_sim_s": e["application_sim_s"],
            "switch_monotonic_ns": e["application_monotonic_ns"], "tick": tick, "next_switch_tick": next_tick,
            "horizon_ticks": ticks, "right_censored": next_tick is None,
            "terminal_reason_if_censored": summary["termination_reason"] if next_tick is None else None,
            "fresh_local_xy": local.tolist(), "fresh_world_xy": worlds[1].tolist(), "old_world_xy": worlds[0].tolist(),
            "previous_actual_vw": previous, "stored_FRESH_command": actual,
            "evaluation_config": true_config, "public_config": public_config, "geometry_information": info,
            "public_obstacle_ids": [b["id"] for b in public_config["obstacles"]],
            "graph_v2_saved_path": str(reused) if reused else None}
        if reused:
            result = json.loads(track(reused).read_text())
            np.testing.assert_allclose(result["case"]["fresh_world_xy"], worlds[1], atol=1e-12, rtol=0)
            np.testing.assert_array_equal(result["case"]["boundary"], poses[tick])
        verification.append({"case_id": case_id, "raw_first_PP_error": pp_error,
            "stored_actual_pose_replay_error": pose_error, "PP_actual_replay": pp,
            "raw_PP_vs_saved_PD": "NOT_APPLICABLE_counterfactual" if not pp else "PASS"})
        cases.append(record)

    for c in s0["cases"]:
        case(c["source_run"], c["fresh_id"], "a_S0", c["case_id"], V2/"cases"/(c["case_id"]+".json"))
    p0 = ARTIFACTS/"phase1_s1_preflight_01/P0"
    _, summary, events, *_ = load_run(p0)
    passage = summary["dynamic_obstacle"]["evaluation"]["passage"]
    assert passage is not None
    for e in events:
        if e["id"] >= 43 and e["application_sim_s"] <= passage["simulation_time_s"]:
            case(p0, e["id"], "b_S1_P0", f"S1_P0_F{e['id']:04d}")
    for name, ids in protocol["selection"]["c"].items():
        for identifier in ids:
            case(ARTIFACTS/name, identifier, "c_stress", f"{name}_F{identifier:04d}")
    assert len(cases) == 59
    assert [c["fresh_id"] for c in cases if c["dataset"] == "b_S1_P0"] == list(range(43, 76))
    assert "DynamicObstacle" not in next(c for c in cases if c["case_id"] == "S1_P0_F0043")["public_obstacle_ids"]
    assert all("DynamicObstacle" in c["public_obstacle_ids"] for c in cases if c["dataset"] == "b_S1_P0" and c["fresh_id"] > 43)
    for path in [Path(__file__), ROOT/"research/nomad_phase0/graph_v3.py", ROOT/"research/nomad_phase0/graph_v3_pilot.py",
                 ROOT/"research/nomad_phase0/graph_v3_protocol.json", ROOT/"research/nomad_phase1/s1.py"]:
        track(path)
    return {"cases": cases, "verification": verification, "input_sha256": hashes,
        "selection": protocol["selection"], "S1_passage": passage, "count": len(cases),
        "selection_uses_graph_results": False, "stress_is_counterfactual_PP": True}
