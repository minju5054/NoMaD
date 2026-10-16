"""NoMaD GPU worker, launched with the existing Python 3.11 .venv."""
import argparse
import hashlib
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
    args = parser.parse_args()
    for part in ["raw", "derived"]:
        (args.output / part).mkdir(parents=True, exist_ok=False)
    assert torch.cuda.is_available()
    device = torch.device("cuda:0")
    model, coverage = load_checked(args.checkpoint, device)
    write_json(args.output / "environment.json", {
        "python": sys.version, "executable": sys.executable, "torch": torch.__version__,
        "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(),
        "checkpoint_sha256": sha256_file(args.checkpoint), "coverage": coverage,
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
                goal = data["goal"]
                assert history.shape == (4, 240, 320, 3) and history.dtype == np.uint8
                assert goal.shape == (240, 320, 3) and goal.dtype == np.uint8
                seed = metadata["seed"]
                noise = torch.randn((8, 8, 2), device=device,
                                    generator=torch.Generator(device=device).manual_seed(seed))
                start_ns = time.monotonic_ns()
                result = infer(model, [Image.fromarray(frame) for frame in history],
                               Image.fromarray(goal), noise, seed + 1, goal_mask=0)
                torch.cuda.synchronize()
                finish_ns = time.monotonic_ns()
                assert all(bool(torch.isfinite(value).all()) for value in result.values())
                arrays = {k: result[k].cpu().numpy() for k in
                          ["normalized_diffusion", "cumulative", "metric", "selected_waypoint"]}
                # No predicted point is adjusted, averaged, smoothed, or selected again.
                with (args.output / "raw" / f"{identifier:04d}.npz").open("xb") as f:
                    np.savez_compressed(f, initial_noise=noise.cpu().numpy(), normalized_diffusion=arrays["normalized_diffusion"])
                with (args.output / "derived" / f"{identifier:04d}.npz").open("xb") as f:
                    np.savez_compressed(f, **{k: v for k, v in arrays.items() if k != "normalized_diffusion"})
                response = {"id": identifier, "seed": seed, "ddpm_seed": seed + 1,
                            "inference_start_monotonic_ns": start_ns, "inference_end_monotonic_ns": finish_ns,
                            "inference_ms": (finish_ns - start_ns) / 1e6,
                            "history_sha256": hashlib.sha256(history.tobytes()).hexdigest(),
                            "goal_sha256": hashlib.sha256(goal.tobytes()).hexdigest(), "finite": True}
                log.write(json.dumps({**metadata, **response}) + "\n"); log.flush()
                send_packet(connection, response, **arrays)


if __name__ == "__main__":
    main()
