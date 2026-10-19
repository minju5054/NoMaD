"""Topological node rules and reference RGB manifest; no model or pose-based selection."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image

from .common import ROOT, sha256_file, write_json

PROTOCOL = Path(__file__).with_name("topomap_protocol.json")


def candidate_range(closest_node, goal_node, radius=4):
    # Official NoMaD branch has +radius+1 AND an inclusive end slice.
    return max(closest_node - radius, 0), min(closest_node + radius + 1, goal_node)


def select_subgoal(distances, start, close_threshold=3):
    distances = np.asarray(distances)
    assert distances.ndim == 1 and len(distances) and np.isfinite(distances).all()
    min_idx = int(np.argmin(distances))
    sg_idx = min(min_idx + int(distances[min_idx] < close_threshold), len(distances) - 1)
    return start + min_idx, start + sg_idx, sg_idx


def reference_rows(reference, config):
    source = json.loads((reference / "scenario.json").read_text())
    assert "dynamic_obstacle" not in source and "dynamic_obstacle" not in config
    for key in ("obstacles", "camera", "corridor", "start_pose", "goal_pose", "agent_radius_m",
                "required_clearance_m", "integration_hz"):
        assert config[key] == source[key], key
    with (reference / "agent_trajectory.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    hz = config["integration_hz"]
    assert hz == 72 and len(rows) == 1771
    times = np.array([float(row["simulation_time_s"]) for row in rows])
    np.testing.assert_allclose(times, np.arange(len(rows))/hz, atol=1e-12, rtol=0)
    indices = list(range(0, len(rows), hz))
    if indices[-1] != len(rows)-1:
        indices.append(len(rows)-1)
    return [(i, rows[i]) for i in indices]


def render_reference(reference, out, config, capture, set_pose, get_pose):
    """Called on Isaac's main thread; only teleport to previously recorded poses."""
    reference = reference.resolve()
    destination = out / "topomap"
    destination.mkdir(exist_ok=False)
    (destination / "rgb").mkdir()
    reference_hashes = {name: sha256_file(reference/name) for name in
                        ("agent_trajectory.csv", "scenario.json", "scene.usda", "provenance.json")}
    records = []
    for node, (tick, row) in enumerate(reference_rows(reference, config)):
        pose = np.array([float(row[k]) for k in ("x_m", "y_m", "yaw_rad")])
        sim_time = float(row["simulation_time_s"])
        set_pose(pose)
        np.testing.assert_allclose(get_pose(), pose, atol=1e-10, rtol=0)
        rgb = capture(sim_time)
        np.testing.assert_allclose(get_pose(), pose, atol=1e-10, rtol=0)
        path = destination / "rgb" / f"{node:04d}.png"
        Image.fromarray(rgb).save(path)
        with Image.open(path) as image:
            np.testing.assert_array_equal(np.asarray(image), rgb)
        records.append({"node_id": node, "reference_pose_row": tick, "simulation_time_s": sim_time,
                        "world_pose": pose.tolist(), "rgb_file": str(path.relative_to(destination)),
                        "png_sha256": sha256_file(path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
                        "rgb_shape": list(rgb.shape), "usd_pose_max_error": float(np.max(abs(get_pose()-pose)))})
    assert all(sha256_file(reference/name) == digest for name, digest in reference_hashes.items())
    provenance = json.loads((reference / "provenance.json").read_text())
    manifest = {"source_run": str(reference), "reference_execution_sha": provenance["git_sha"],
                "render_git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "protocol_sha256": sha256_file(PROTOCOL), "reference_sha256": reference_hashes,
                "scenario": config, "node_count": len(records), "nodes": records,
                "spacing_sim_s": 1., "include_start_and_final": True,
                "dynamic_obstacle": False, "new_navigation_count": 0, "new_inference_count": 0,
                "note": "Static reference-route RGB at saved 72Hz poses; last image is recorded goal-entry pose, not an invented pose at exact goal"}
    write_json(destination / "manifest.json", manifest)
    return manifest


def load_map(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["dynamic_obstacle"] is False
    assert manifest["node_count"] == len(manifest["nodes"]) > 0
    images, hashes = [], []
    for i, row in enumerate(manifest["nodes"]):
        assert row["node_id"] == i
        path = manifest_path.parent / row["rgb_file"]
        assert sha256_file(path) == row["png_sha256"]
        with Image.open(path) as image:
            assert image.mode == "RGB" and image.size == (320, 240)
            image = image.copy()
        assert hashlib.sha256(np.asarray(image).tobytes()).hexdigest() == row["rgb_sha256"]
        images.append(image)
        hashes.append({key: row[key] for key in ("rgb_file", "png_sha256", "rgb_sha256")})
    # Intentionally do not expose map world poses to the policy selection code.
    return images, hashes
