"""CPU-only stdin/stdout Graph worker. One unchanged solve per request, no retry."""
import json
from pathlib import Path
import platform
import sys
import time
import traceback

import numpy as np
import scipy
from scipy.optimize import least_squares

from .common import local_to_world, original_controller, write_json
from .online_graph_factors import ChordExperiment, chord_headings, derived_headings, local_point


def solve(job):
    p = json.loads(Path(__file__).with_name("online_graph_factor_protocol.json").read_text())
    local = np.asarray(job["sample0"], dtype=float)
    world = local_to_world(local, job["observation_pose"])
    _, lengths = derived_headings(world)
    candidates = np.flatnonzero(np.cumsum(lengths) >= p["minimum_heading_segment_m"])
    result = {"graph_id": job["graph_id"], "fresh_id": job["fresh_id"],
              "solve_start_monotonic_ns": time.monotonic_ns(), "solver_called": False,
              "input_boundary": job["boundary"], "geometry": job["geometry"],
              "original_world_xy": world.tolist(), "local_waypoint": local[2].tolist()}
    if not len(candidates) or np.any(lengths[1:] < p["minimum_heading_segment_m"]):
        return {**result, "status": "INVALID_HEADING", "reason": "No first chord or short non-first adjacent segment",
                "adjacent_lengths_m": lengths.tolist(), "solve_end_monotonic_ns": time.monotonic_ns()}
    k = 1 if lengths[0] >= p["minimum_heading_segment_m"] else int(candidates[0]+1)
    try:
        headings, _, chord = chord_headings(world, k)
        if chord < p["minimum_heading_segment_m"]:
            return {**result, "status": "INVALID_HEADING", "reason": "Frozen chord shorter than 20mm",
                    "k": k, "chord_m": chord, "solve_end_monotonic_ns": time.monotonic_ns()}
        initial = np.column_stack([world, headings])
        exp = ChordExperiment(initial, np.array(job["boundary"]), job["geometry"], p, k)
        settings = p["solver"]
        cpu = time.process_time()
        result["solver_called"] = True
        solution = least_squares(exp.residual, np.zeros(24), method=settings["method"], jac=settings["jac"],
            ftol=settings["ftol"], xtol=settings["xtol"], gtol=settings["gtol"],
            max_nfev=settings["max_nfev"], x_scale=np.tile(settings["x_scale_per_pose"], 8))
        end = time.monotonic_ns()
        optimized = initial+solution.x.reshape(8, 3)
        point = local_point(optimized[2, :2], np.array(job["boundary"]))
        command = list(map(float, original_controller()(point)))
        factors = exp.groups(optimized)
        return {**result, "status": "CONVERGED" if solution.success else "NOT_CONVERGED",
                "solve_end_monotonic_ns": end, "cpu_process_s": time.process_time()-cpu,
                "k": k, "initial_chord_m": chord, "adjacent_lengths_m": lengths.tolist(),
                "optimized_world_poses": optimized.tolist(), "corrected_B_local_waypoint": point.tolist(),
                "command_vw": command, "cost": float(solution.cost), "nfev": solution.nfev,
                "residual_calls": exp.calls, "solver_status": solution.status, "message": solution.message,
                "factor_costs": {key: .5*float(value@value) for key, value in factors.items()}}
    except Exception as error:
        return {**result, "status": "SOLVER_EXCEPTION", "error": repr(error),
                "traceback": traceback.format_exc(), "solve_end_monotonic_ns": time.monotonic_ns()}


def main():
    out = Path(sys.argv[1])
    print(json.dumps({"ready": True, "python": platform.python_version(), "numpy": np.__version__,
                      "scipy": scipy.__version__}), flush=True)
    for line in sys.stdin:
        job = json.loads(line)
        if job.get("stop"):
            return
        write_json(out/f"input_{job['graph_id']:04d}.json", job)
        result = solve(job)
        write_json(out/f"result_{job['graph_id']:04d}.json", result)
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
