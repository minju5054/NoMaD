"""CPU-only protocol/metric tests. No simulator or inference subprocess is permitted."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from nomad_isaac.common import ROOT, integrate_se2, original_controller
from nomad_isaac.seed_offset import request_seed, validate_seed_options
from nomad_phase0 import s0_batch
from nomad_phase0.s0_batch_metrics import (aggregate, bootstrap_mean, classify, corridor_arc_minimum,
                                         extract_run, margin_violation_duration, pd_unclipped_w, protocol, wilson)


def test_zero_offset_identity_and_static_only_guard():
    for i in range(721):
        assert request_seed({"seed": 101}, i) == request_seed({"seed": 101, "seed_offset": 0}, i) == 101+2*i
    p = protocol()
    args = SimpleNamespace(seed_offset=10000, run_id="S0_01", scenario=ROOT/p["scenario"],
        topomap=ROOT.parent/p["topomap"], asynchronous=True, prepare_only=False, oracle_safety_stop=False,
        early_obstacle_mode=None, controlled_delivery_delay=False, uniform_delivery_delay_s=None,
        render_topomap_reference=None)
    validate_seed_options(args)
    args.asynchronous = False
    with pytest.raises(ValueError): validate_seed_options(args)
    args.asynchronous = True
    args.run_id = "S0_02"
    with pytest.raises(ValueError): validate_seed_options(args)
    args.run_id = None
    args.scenario = ROOT/"research/nomad_isaac/early_obstacle_scenario.json"
    with pytest.raises(ValueError): validate_seed_options(args)


def test_twenty_jobs_pair_offsets_unique_seed_streams_and_safe_dry_run(tmp_path, monkeypatch):
    plan = s0_batch.build_plan(tmp_path/"never_created")
    assert len(plan["jobs"]) == 20
    streams = []
    for pair in range(10):
        pp, pd = plan["jobs"][2*pair:2*pair+2]
        assert [pp["condition"], pd["condition"]] == ["PP", "PD"]
        assert pp["run_id"] == pd["run_id"] == f"S0_{pair+1:02d}"
        assert pp["seed_offset"] == pd["seed_offset"] == (pair+1)*10000
        assert "--pure-pursuit" in pp["argv"] and "--pure-pursuit" not in pd["argv"]
        assert pp["request_0_seed"] == pd["request_0_seed"] == 101+(pair+1)*10000
        # 180s wall bound x 4Hz, even if simulation pacing were slower than nominal.
        streams.append({request_seed({"seed": 101, "seed_offset": pp["seed_offset"]}, i)+d
                        for i in range(721) for d in (0, 1)})
    assert all(not a & b for i, a in enumerate(streams) for b in streams[i+1:])
    monkeypatch.setattr(s0_batch, "launch_one", lambda *args: pytest.fail("dry-run launched a child"))
    monkeypatch.setattr("sys.argv", ["s0_batch", "--dry-run", "--run-root", str(tmp_path/"never_created"),
                                     "--output", str(tmp_path/"plan")])
    s0_batch.main()
    assert not (tmp_path/"never_created").exists()
    assert len(json.loads((tmp_path/"plan/plan.json").read_text())["jobs"]) == 20


def test_margin_is_independent_and_uncertain_contact_not_collision():
    margin = margin_violation_duration([
        {"start_sim_s": 0., "end_sim_s": 0., "lower_m": .001},
        {"start_sim_s": 0., "end_sim_s": 1/72, "lower_m": .019},
        {"start_sim_s": 1/72, "end_sim_s": 2/72, "lower_m": .02}])
    assert margin == 1/72
    assert classify(True, False, False, "goal_entry", 25.) == "SUCCESS"
    assert classify(False, False, False, "conservative_contact_stop", 12.) == "OTHER_TERMINATION"
    assert classify(False, False, False, "simulation_timeout", 60.) == "STUCK"
    assert classify(True, True, False, "goal_entry", 25.) == "SAFETY_FAILURE"
    assert classify(False, False, True, "corridor_footprint_stop", 5.) == "SAFETY_FAILURE"


def test_corridor_arc_and_pd_clipping_are_evaluation_only():
    corridor = {"xmin": -2, "xmax": 6, "half_width": 1.5}
    pose = np.array([0., 1.40001, .04])
    gap = corridor_arc_minimum(pose, .2, -.4, .2, corridor, .09)
    dense = np.array([integrate_se2(pose, .2, -.4, t) for t in np.linspace(0, .2, 1001)])
    np.testing.assert_allclose(gap, 1.5-dense[:, 1].max()-.09, atol=1e-12)
    original = original_controller()
    for point in ([0., 1.], [0., 0.], [.1, .002], [.01, -.1], [-.1, .1]):
        np.testing.assert_allclose(np.clip(pd_unclipped_w(point), -.4, .4), original(point)[1], atol=1e-12)


def test_wilson_and_paired_bootstrap_keep_pairs_and_missing_goal_times():
    np.testing.assert_allclose(wilson([True]*10)["ci95"], [.7224672001371107, 1.], atol=1e-12)
    assert wilson([])["estimate"] is None
    assert bootstrap_mean([1, 3, 7]) == bootstrap_mean([1, 3, 7])
    records = []
    for i in range(10):
        for condition in ("PP", "PD"):
            records.append({"run_id": str(i), "condition": condition, "seed_offset": (i+1)*10000,
                "success": i != 9, "technical_failure": False, "safety_failure": False, "timeout": i == 9,
                "goal_time_s": None if i == 9 else i*10+(1 if condition == "PP" else 0),
                "stop_time_s": i*100+(1 if condition == "PP" else 0)})
    result = aggregate(records)
    assert result["conditions"]["PP"]["metrics"]["goal_time_s"]["n"] == 9
    paired = result["paired_PP_minus_PD"]
    assert paired["goal_time_s"]["n"] == 9 and paired["goal_time_s"]["ci95"] == [1., 1.]
    assert paired["stop_time_s"]["n"] == 10 and paired["stop_time_s"]["ci95"] == [1., 1.]
    records[0].update(technical_failure=True, success=False, safety_failure=None, timeout=None, goal_time_s=None)
    result = aggregate(records)
    assert result["conditions"]["PP"]["metrics"]["success"]["n"] == 10
    assert result["conditions"]["PP"]["metrics"]["safety_failure"]["n"] == 9


def test_serial_attempts_failure_preserved_no_retry_and_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(s0_batch, "git_state", lambda: {"git_sha": "synthetic", "git_status": ""})
    plan = s0_batch.build_plan(tmp_path/"runs")
    visited = []
    def fake_launch(job, log):
        visited.append((job["run_id"], job["condition"]))
        return 7 if len(visited) == 1 else 0
    monkeypatch.setattr(s0_batch, "launch_one", fake_launch)
    monkeypatch.setattr(s0_batch, "extract_run", lambda path, condition, run_id, offset: {
        "scope": "synthetic only", "run_id": run_id, "condition": condition, "seed_offset": offset,
        "classification": "SUCCESS", "success": True, "technical_failure": False})
    out = tmp_path/"synthetic"
    out.mkdir()
    records = s0_batch.execute_jobs(plan, out)
    assert visited == [(j["run_id"], j["condition"]) for j in plan["jobs"]]
    assert len(records) == 20 and records[0]["classification"] == "TECHNICAL_FAILURE"
    assert records[0]["launcher_exit_code"] == 7 and records[0]["safety_failure"] is None
    journal = [json.loads(line) for line in (out/"execution.jsonl").read_text().splitlines()]
    assert [r["event"] for r in journal] == ["START", "END"]*20
    monkeypatch.setattr(s0_batch, "ROOT", tmp_path/"fake_repo")
    with s0_batch.exclusive_batch():
        with pytest.raises(RuntimeError):
            with s0_batch.exclusive_batch():
                pytest.fail("Concurrent batch acquired lock")


def test_existing_pp_pd_metrics_are_json_serializable_and_use_actual_commands():
    root = ROOT.parent/"artifacts/isaac6"
    pp = extract_run(root/"phase0c_pure_pursuit_01", "PP", "LEGACY_REFERENCE", 0, legacy=True)
    pd = extract_run(root/"topomap_static_2s_01", "PD", "LEGACY_REFERENCE", 0, legacy=True)
    assert json.loads(json.dumps([pp, pd])) == [pp, pd]
    assert [r["w_clipped_ticks"] for r in (pp, pd)] == [19, 66]
    assert all(r["classification"] == "SUCCESS" and r["max_pose_replay_error"] == 0 for r in (pp, pd))
