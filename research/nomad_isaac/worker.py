"""NoMaD GPU worker, launched with the existing Python 3.11 .venv."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import socket
import sys
import time

import numpy as np
from PIL import Image
import torch

from nomad_preflight.native import CONFIG, infer, load_checked
from .common import receive_packet, send_packet, sha256_file, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--topomap", type=Path)
    parser.add_argument("--diagnostic", action="store_true")
    args = parser.parse_args()
    for part in ["raw", "derived"]:
        (args.output / part).mkdir(parents=True, exist_ok=False)
    assert torch.cuda.is_available()
    device = torch.device("cuda:0")
    model, coverage = load_checked(args.checkpoint, device)
    policy = None
    if args.topomap:
        from .topomap_inference import TopomapPolicy
        if args.diagnostic:
            from nomad_diagnostic.inference import DiagnosticPolicy
            policy = DiagnosticPolicy(args.topomap)
        else:
            policy = TopomapPolicy(args.topomap)
    write_json(args.output / "environment.json", {
        "python": sys.version, "executable": sys.executable, "torch": torch.__version__,
        "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(),
        "numpy": np.__version__, "torchvision": version("torchvision"), "diffusers": version("diffusers"),
        "checkpoint_sha256": sha256_file(args.checkpoint), "coverage": coverage,
        "goal_mode": "topomap" if policy else "fixed_goal",
        "topomap_manifest_sha256": sha256_file(args.topomap) if args.topomap else None,
        "config": {k: CONFIG[k] for k in ["context_size", "image_size", "num_diffusion_iters", "len_traj_pred"]}})
    with socket.socket(socket.AF_UNIX) as listener, (args.output / "inference.jsonl").open("x") as log:
        listener.bind(args.socket)
        listener.listen(1)
        listener.settimeout(480)
        with listener.accept()[0] as connection:
            connection.settimeout(180)
            while True:
                metadata, data = receive_packet(connection)
                if metadata["kind"] == "stop":
                    send_packet(connection, {"kind": "stopped"})
                    return
                identifier = metadata["id"]
                history = data["history"]
                assert history.shape == (4, 240, 320, 3) and history.dtype == np.uint8
                if policy is None:
                    goal = data["goal"]
                    assert goal.shape == (240, 320, 3) and goal.dtype == np.uint8
                seed = metadata["seed"]
                noise = torch.randn((8, 8, 2), device=device,
                                    generator=torch.Generator(device=device).manual_seed(seed))
                start_ns = time.monotonic_ns()
                if policy is None:
                    result = infer(model, [Image.fromarray(frame) for frame in history],
                                   Image.fromarray(goal), noise, seed + 1, goal_mask=0)
                    goal_digest = hashlib.sha256(goal.tobytes()).hexdigest()
                    topomap_record = None
                else:
                    options = {"goal_mask": metadata["diagnostic_mode"]["goal_mask"]} if args.diagnostic else {}
                    result, topomap_record = policy.infer(model, [Image.fromarray(frame) for frame in history], noise, seed+1, **options)
                    goal_digest = topomap_record["selected_subgoal_image"]["rgb_sha256"]
                torch.cuda.synchronize()
                finish_ns = time.monotonic_ns()
                assert all(bool(torch.isfinite(value).all()) for value in result.values())
                arrays = {k: result[k].cpu().numpy() for k in
                          ["normalized_diffusion", "cumulative", "metric", "selected_waypoint"]}
                host_output_ready_ns = time.monotonic_ns()
                # No predicted point is adjusted, averaged, smoothed, or selected again.
                with (args.output / "raw" / f"{identifier:04d}.npz").open("xb") as f:
                    condition = {"selected_condition": result["condition"].cpu().numpy()} if policy else {}
                    np.savez_compressed(f, initial_noise=noise.cpu().numpy(), normalized_diffusion=arrays["normalized_diffusion"], **condition)
                with (args.output / "derived" / f"{identifier:04d}.npz").open("xb") as f:
                    np.savez_compressed(f, **{k: v for k, v in arrays.items() if k != "normalized_diffusion"})
                response = {"id": identifier, "seed": seed, "ddpm_seed": seed + 1,
                            "inference_start_monotonic_ns": start_ns, "inference_end_monotonic_ns": finish_ns,
                            "ready_monotonic_ns": finish_ns,
                            "host_output_ready_monotonic_ns": host_output_ready_ns,
                            "persistence_end_monotonic_ns": time.monotonic_ns(),
                            "inference_ms": (finish_ns - start_ns) / 1e6,
                            "history_sha256": hashlib.sha256(history.tobytes()).hexdigest(),
                            "goal_sha256": goal_digest, "finite": True}
                if topomap_record is not None:
                    response["topomap"] = topomap_record
                log.write(json.dumps({**metadata, **response}) + "\n"); log.flush()
                send_packet(connection, response, **arrays)


if __name__ == "__main__":
    main()
