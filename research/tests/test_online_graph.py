"""Focused fake-worker scheduling tests; no navigation or optimizer."""
import json
import queue
from types import SimpleNamespace
import time

import numpy as np
import pytest

from nomad_isaac.async_core import WaypointExecution
from nomad_isaac.common import ROOT, original_controller
from nomad_isaac.early_experiment import validate_early
from nomad_isaac.online_graph import GraphRecovery


def setup(tmp_path):
    run = ROOT.parent/"artifacts/isaac6/topomap_sudden_01"
    c = json.loads((run/"scenario.json").read_text())
    box = json.loads((run/"dynamic/spawn.json").read_text())["obstacle"]
    e = next(json.loads(s) for s in (run/"events.jsonl").read_text().splitlines() if json.loads(s)["id"] == 52)
    core = WaypointExecution(e["agent_pose_at_switch"])
    now = time.monotonic_ns()
    core.receive({**e,"id":0,"received_monotonic_ns":now-200_000_000},e["selected_waypoint_m"])
    data = np.load(run/"model/derived/0052.npz")["metric"][0]
    results = queue.Queue()
    client = SimpleNamespace(jobs=queue.Queue(1),poll=lambda: results.get_nowait() if not results.empty() else None)
    return core, GraphRecovery(c,tmp_path,client), box, data, results, now


def test_stop_while_pending_and_accept_as_separate_expired_input_graph_action(tmp_path):
    core,g,box,data,results,now = setup(tmp_path)
    refresh,switch = core.control(1016,now)
    d=g.apply(core,refresh,switch,1016,box,(0,data))
    assert d["source"]=="GRAPH_WAIT" and (core.v,core.w)==(0,0)
    p=core.pose.copy()
    for _ in range(8):core.integrate()
    np.testing.assert_array_equal(core.pose,p)
    refresh,switch=core.control(1024,now+1_100_000_000)
    assert refresh["status"]=="expired" and refresh["new_timeout"]
    command=list(map(float,original_controller()([.0025,.001])))
    results.put({"graph_id":0,"status":"CONVERGED","command_vw":command,"corrected_B_local_waypoint":[.0025,.001],
                 "solve_start_monotonic_ns":now,"solve_end_monotonic_ns":now+1_000_000_000,
                 "cpu_packet_received_monotonic_ns":now+1_000_000_001})
    d=g.apply(core,refresh,switch,1024,box,(0,data))
    assert d["source"]=="GRAPH" and d["result"]["accepted"] and switch is None
    assert refresh["v_m_s"]==0 and refresh["applied_v_m_s"]>0 and not core.command_valid
    core.integrate()
    assert np.linalg.norm(core.pose[:2]-p[:2])>0
    g.log.close()


def test_changed_boundary_rejects_late_graph_result(tmp_path):
    core,g,box,data,results,now = setup(tmp_path)
    r,s=core.control(1016,now);g.apply(core,r,s,1016,box,(0,data))
    core.pose[0]+=.001
    results.put({"graph_id":0,"status":"CONVERGED","command_vw":[.01,.4],
                 "solve_start_monotonic_ns":now,"solve_end_monotonic_ns":now+1,
                 "cpu_packet_received_monotonic_ns":now+2})
    r,s=core.control(1024,now+100_000_000);d=g.apply(core,r,s,1024,box,(0,data))
    assert not d["result"]["valid_B"] and not d["result"]["accepted"] and d["source"]!="GRAPH"
    g.log.close()


def test_new_mode_cannot_relax_existing_frozen_scenario():
    folder=ROOT/"research/nomad_isaac"
    manifest=ROOT.parent/"artifacts/isaac6/topomap_reference_2s_01/topomap/manifest.json"
    c=json.loads((folder/"early_obstacle_scenario.json").read_text())
    validate_early(c,manifest,True)
    with pytest.raises(ValueError):validate_early(c,manifest,False)
    old=json.loads((folder/"old_rollout_obstacle_scenario.json").read_text())
    with pytest.raises(ValueError):validate_early(old,manifest,True)
