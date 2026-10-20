"""Stored-route geometry and one saved B52 CPU-worker validation, no navigation."""
import ast
import json
from pathlib import Path
import subprocess
import time

import numpy as np

from .clearance import configured_obstacles, obstacle_bounds, point_clearance, segment_clearance, single_obstacle_config
from .common import ROOT, sha256_file, write_json
from .early_experiment import validate_early
from .old_rollout_placement import wall_gap
from .online_graph import CPUClient
from .online_graph_factors import local_point
from .oracle_safety_stop import evaluate


def main():
    out = ROOT.parent/"artifacts/isaac6/early_graph_preflight_01"
    out.mkdir(exist_ok=False)
    base = ROOT/"research/nomad_isaac"
    config = json.loads((base/"early_obstacle_scenario.json").read_text())
    manifest = ROOT.parent/"artifacts/isaac6/topomap_reference_2s_01/topomap/manifest.json"
    validate_early(config, manifest, True)
    extracted = {n.name:n for n in ast.parse((base/"online_graph_factors.py").read_text()).body
                 if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    equality = []
    for source in ("minimal_se2_graph.py", "topomap_b52_chord_graph.py"):
        text = subprocess.check_output(["git", "show", "3a60531:research/nomad_isaac/"+source], cwd=ROOT, text=True)
        for node in ast.parse(text).body:
            if not isinstance(node, (ast.FunctionDef, ast.ClassDef)) or node.name not in extracted:
                continue
            if node.name == "ChordExperiment":
                node.body = [n for n in node.body if isinstance(n, ast.FunctionDef) and n.name in ("__init__", "groups")]
            assert ast.dump(node, include_attributes=False) == ast.dump(extracted[node.name], include_attributes=False), node.name
            equality.append(node.name)
    assert len(equality) == 8
    box = config["dynamic_obstacle"]
    lower, upper = obstacle_bounds(single_obstacle_config(config, box))
    static = [obstacle_bounds(single_obstacle_config(config, b)) for b in configured_obstacles(config)]
    separation = min(float(np.linalg.norm(np.maximum(np.maximum(a-upper, lower-b), 0))) for a,b in static)
    assert separation >= .02 and wall_gap(lower, upper, config["corridor"]) >= .02
    geometry = []
    for name in ("topomap_static_2s_01", "topomap_sudden_01"):
        path = out.parent/name/"agent_trajectory.csv"
        trace = np.genfromtxt(path, delimiter=",", names=True)
        pose = np.array([trace[k][792] for k in ("x_m","y_m","yaw_rad")])
        local = local_point(np.array(box["center_xy_m"]), pose)
        bearing = float(np.degrees(np.arctan2(local[1],local[0])))
        gap = point_clearance(pose[:2], lower, upper, .09)
        sight = min(segment_clearance(pose[:2],box["center_xy_m"],a,b,0.)[0] for a,b in static)
        assert gap >= .02 and local[0] > 0 and abs(bearing) < 45 and sight > 0
        geometry.append({"reference":name,"pose":pose.tolist(),"clearance_m":gap,"bearing_deg":bearing,
                         "center_sight_ray_clearance_m":sight,"trajectory_sha256":sha256_file(path)})
    # This is one saved-data CPU solve, not a third navigation or fresh model sample.
    run = out.parent/"topomap_sudden_01"
    event = next(json.loads(x) for x in (run/"events.jsonl").read_text().splitlines() if json.loads(x)["id"]==52)
    old_config = json.loads((run/"scenario.json").read_text())
    dynamic = json.loads((run/"dynamic/spawn.json").read_text())["obstacle"]
    with np.load(run/"model/derived/0052.npz") as data:
        sample = data["metric"][0].astype(float)
    job = {"graph_id":0,"fresh_id":52,"sample0":sample.tolist(),"observation_pose":event["observation_pose"],
           "boundary":event["agent_pose_at_switch"],"geometry":{**old_config,"obstacles":[*old_config["obstacles"],dynamic]}}
    client = CPUClient(out/"cpu_worker")
    try:
        client.jobs.put_nowait(job)
        result = client.results.get(timeout=120)
    finally:
        client.close()
    assert result["status"] == "CONVERGED" and result["k"] == 2
    recorded = json.loads((out.parent/"topomap_b52_chord_graph_01/summary.json").read_text())["methods"]["GRAPH"]
    np.testing.assert_allclose(result["command_vw"],recorded["rollout"]["command_vw"],atol=1e-9,rtol=0)
    np.testing.assert_allclose(result["optimized_world_poses"],recorded["world_poses"],atol=1e-9,rtol=0)
    safe = evaluate(old_config, job["boundary"], result["command_vw"], dynamic)
    assert safe["safe"] and result["command_vw"][0] > 0
    result = {"status":"PASS","factor_ast_equal":equality,"factor_protocol_sha256":sha256_file(base/"online_graph_factor_protocol.json"),
              "early_geometry":geometry,"static_box_separation_m":separation,"visibility_scope":"Stored-pose geometric FOV/occlusion check; actual RGB checked during runs",
              "B52_worker_solve":{"k":result["k"],"status":result["status"],"command_vw":result["command_vw"],
                    "cost":result["cost"],"nfev":result["nfev"],"safe":safe["safe"],
                    "clearance_m":safe["minimum_clearance_lower_m"],"matches_prior_solution_atol":1e-9,
                    "solve_wall_s":(result["solve_end_monotonic_ns"]-result["solve_start_monotonic_ns"])/1e9}}
    write_json(out/"summary.json",result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
