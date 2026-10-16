"""GPU-only preflight. Run with PYTHONPATH=research:train:external/diffusion_policy."""
import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import time
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image
import torch

from .native import CONFIG, DP_SHA, ROOT, UPSTREAM_SHA, infer, load_checked, scheduler


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(tensor):
    return {"shape": list(tensor.shape), "dtype": str(tensor.dtype),
            "device": str(tensor.device), "finite": bool(torch.isfinite(tensor).all())}


def difference(a, b):
    d = (a - b).abs()
    return {"bitwise_equal": bool(torch.equal(a, b)), "max_abs": d.max().item(),
            "mean_abs": d.mean().item()}


def save_result(directory, label, result):
    raw_keys = ["observation", "goal", "condition", "distance", "initial_noise", "normalized_diffusion"]
    for category, keys in [("raw", raw_keys), ("derived", ["cumulative", "metric", "selected_waypoint"])]:
        with (directory / category / f"{label}.npz").open("xb") as f:
            np.savez_compressed(f, **{k: result[k].detach().cpu().numpy() for k in keys})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--observations", type=Path, nargs=4, required=True)
    parser.add_argument("--goal", type=Path, required=True)
    parser.add_argument("--alternate-observations", type=Path, nargs=4)
    parser.add_argument("--output", type=Path, required=True, help="New directory; refuses overwrite")
    parser.add_argument("--repeats", type=int, default=30)
    args = parser.parse_args()
    if args.repeats < 2:
        parser.error("--repeats must be at least 2")
    args.output.mkdir(parents=True, exist_ok=False)
    for category in ["raw", "derived"]:
        (args.output / category).mkdir()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no CPU fallback or false GPU PASS")
    device = torch.device("cuda:0")
    capability = torch.cuda.get_device_capability(device)
    arch = torch.cuda.get_arch_list()
    assert capability == (12, 0) and "sm_120" in arch, (capability, arch)
    # Real CUDA kernels, checked against an exact known answer.
    x = torch.ones((64, 64), device=device)
    y = x @ x
    torch.cuda.synchronize()
    assert torch.equal(y, torch.full_like(y, 64))
    del x, y
    start = time.perf_counter()
    model, coverage = load_checked(args.checkpoint, device)
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - start
    observations = [Image.open(p).convert("RGB") for p in args.observations]
    goal = Image.open(args.goal).convert("RGB")
    # Preserve actual submitted image bytes, independent of later external file edits.
    import shutil
    for i, path in enumerate([*args.observations, args.goal, *(args.alternate_observations or [])]):
        shutil.copyfile(path, args.output / "raw" / f"input_{i:02d}{path.suffix}")
    noise = torch.randn((8, 8, 2), generator=torch.Generator(device=device).manual_seed(101), device=device)
    torch.cuda.reset_peak_memory_stats(device)
    baseline = torch.cuda.memory_allocated(device)

    def timed():
        torch.cuda.synchronize()
        t = time.perf_counter()
        result = infer(model, observations, goal, noise, 202)
        torch.cuda.synchronize()
        return result, (time.perf_counter() - t) * 1000

    cold, cold_ms = timed()
    cold_peak = torch.cuda.max_memory_allocated(device)
    warm = cold
    for _ in range(5):
        warm, _ = timed()
    torch.cuda.reset_peak_memory_stats(device)
    times = []
    for _ in range(args.repeats):
        warm, elapsed = timed()
        times.append(elapsed)
    warm_peak = torch.cuda.max_memory_allocated(device)
    warm_reserved = torch.cuda.max_memory_reserved(device)
    repeat = infer(model, observations, goal, noise, 202)
    other_noise = torch.randn((8, 8, 2), generator=torch.Generator(device=device).manual_seed(303), device=device)
    other_seed = infer(model, observations, goal, other_noise, 404)
    initial_only = infer(model, observations, goal, noise, 405)
    goal_free = infer(model, observations, goal, noise, 202, goal_mask=1)
    # Goal masking is also verified with a different *real* input image.
    masked_other_goal = infer(model, observations, observations[0], noise, 202, goal_mask=1)
    alternate = None
    if args.alternate_observations:
        alternate = infer(model, [Image.open(p).convert("RGB") for p in args.alternate_observations],
                          goal, noise, 202)
    cases = {"goal_conditioned": cold, "fixed_noise_repeat": repeat, "different_seed": other_seed,
             "fixed_initial_only": initial_only, "goal_free": goal_free,
             "goal_free_changed_goal": masked_other_goal}
    if alternate is not None:
        cases["different_observations"] = alternate
    for name, result in cases.items():
        save_result(args.output, name, result)
    shapes = {name: {k: describe(v) for k, v in result.items()} for name, result in cases.items()}
    assert all(v["finite"] for result in shapes.values() for v in result.values())
    assert cold["normalized_diffusion"].shape == (8, 8, 2)
    reproducibility = difference(cold["normalized_diffusion"], repeat["normalized_diffusion"])
    # Same software/device/process, with all DDPM random draws reset.
    assert reproducibility["max_abs"] <= 1e-6, reproducibility
    seed_diff = difference(cold["normalized_diffusion"], other_seed["normalized_diffusion"])
    assert seed_diff["max_abs"] > 0
    report = {
        "status": "PASS", "time_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "upstream_sha": UPSTREAM_SHA, "diffusion_policy_sha": DP_SHA,
        "checkpoint": {"path": str(args.checkpoint.resolve()), "bytes": args.checkpoint.stat().st_size,
                       "sha256": digest(args.checkpoint), "source_folder": "https://drive.google.com/drive/folders/1a9yWR2iooXFAqjQHetz263--4_2FFggg",
                       "file_id": "1YJhkkMJAYOiKNyCaelbS_alpUpAJsOUb", "coverage": coverage},
        "environment": {"python": platform.python_version(), "torch": torch.__version__,
                        "torch_cuda_runtime": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
                        "gpu": torch.cuda.get_device_name(), "capability": capability, "arch_list": arch,
                        "cuda_kernel_check": "PASS", "packages": {p: importlib.metadata.version(p) for p in
                        ["torchvision", "numpy", "Pillow", "diffusers", "huggingface-hub", "efficientnet-pytorch", "einops"]},
                        "cudnn_benchmark": torch.backends.cudnn.benchmark,
                        "cudnn_deterministic": torch.backends.cudnn.deterministic,
                        "matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
                        "cudnn_allow_tf32": torch.backends.cudnn.allow_tf32,
                        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                        "cpu_threads": torch.get_num_threads(),
                        "nvidia_smi": subprocess.check_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], text=True).strip()},
        "inputs": [{"path": str(p.resolve()), "sha256": digest(p)} for p in
                   [*args.observations, args.goal, *(args.alternate_observations or [])]],
        "configuration": {"model": CONFIG, "num_samples": 8, "timesteps": scheduler().timesteps.tolist(),
                          "scheduler": dict(scheduler().config), "initial_noise_seed": 101, "ddpm_seed": 202,
                          "different_seed": [303, 404], "fixed_initial_only_ddpm_seed": 405},
        "measurements": {"load_seconds": load_seconds, "cold_inference_ms": cold_ms,
                         "warmup_runs": 5, "warm_runs": len(times), "warm_median_ms": float(np.median(times)),
                         "warm_p95_ms": float(np.percentile(times, 95)), "warm_ms": times,
                         "baseline_allocated_bytes": baseline, "cold_peak_allocated_bytes": cold_peak,
                         "warm_peak_allocated_bytes": warm_peak, "warm_peak_reserved_bytes": warm_reserved,
                         "timing_scope": "First/warm infer: PIL preprocessing, H2D, encoder, distance, 10 DDPM steps, official CPU normalization/cumsum, metric scaling, CUDA synchronization. Excludes imports, CUDA initialization, weights/image disk IO and initial noise creation."},
        "tensor_shapes": shapes,
        "fixed_all_noise_reproducibility": reproducibility,
        "different_seed_difference": seed_diff,
        "fixed_initial_noise_only_difference": difference(cold["normalized_diffusion"], initial_only["normalized_diffusion"]),
        "goal_free_changed_goal_difference": difference(goal_free["normalized_diffusion"], masked_other_goal["normalized_diffusion"]),
        "different_observations_difference": difference(cold["normalized_diffusion"], alternate["normalized_diffusion"]) if alternate is not None else {"status": "NOT_RUN"},
        "sample0_selected_waypoint_m": cold["selected_waypoint"].cpu().tolist(),
        "limitations": ["One selected goal, no topomap search or robot/controller execution", "No obstacle avoidance or success-rate evaluation", "No native yaw or intrinsic timestamps", "Same-device repeatability only; no cross-version/hardware claim"],
    }
    with (args.output / "summary.json").open("x") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({k: report[k] for k in ["status", "measurements", "fixed_all_noise_reproducibility", "sample0_selected_waypoint_m"]}, indent=2))


if __name__ == "__main__":
    main()
