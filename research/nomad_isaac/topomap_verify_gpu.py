"""Pre-navigation equivalence checks using actual map RGB; no simulator movement."""
import argparse
import ast
import json
from pathlib import Path
import time

import numpy as np
import torch

from nomad_preflight.native import CONFIG, infer, load_checked, transform_images, to_numpy
from .common import ROOT, sha256_file, write_json
from .topomap import load_map
from .topomap_inference import TopomapPolicy, diffuse_condition, encode_candidates


class CountingModel:
    def __init__(self, model):
        self.model, self.counts = model, {}

    def parameters(self):
        return self.model.parameters()

    def __call__(self, component, **kwargs):
        self.counts[component] = self.counts.get(component, 0)+1
        return self.model(component, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topomap", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    images, _ = load_map(args.topomap)
    model, coverage = load_checked(ROOT.parent / "artifacts/checkpoints/nomad.pth", torch.device("cuda:0"))
    noise = torch.randn((8, 8, 2), device="cuda:0", generator=torch.Generator(device="cuda:0").manual_seed(101))
    observations, goal = images[:4], images[4]
    original = infer(model, observations, goal, noise, 102, goal_mask=0)
    same_condition = diffuse_condition(model, original["condition"], noise, 102)
    errors = {}
    for key in same_condition:
        errors[key] = float((same_condition[key]-original[key]).abs().max())
        assert torch.equal(same_condition[key], original[key]), (key, errors[key])
    one_condition, one_distance, _, _ = encode_candidates(model, observations, [goal])
    assert torch.equal(one_condition.detach(), original["condition"])
    assert torch.equal(one_distance.detach(), original["distance"])
    policy = TopomapPolicy(args.topomap)
    counted = CountingModel(model)
    begin = time.monotonic_ns()
    result, selection = policy.infer(counted, observations, noise, 102)
    assert counted.counts == {"vision_encoder": 1, "dist_pred_net": 1, "noise_pred_net": 10}
    # Execute original encoder/head statements verbatim, with the same candidate tensors.
    tree = ast.parse((ROOT / "deployment/src/navigate.py").read_text())
    statements = sorted((n for n in ast.walk(tree) if isinstance(n, ast.Assign)), key=lambda n: n.lineno)
    original_encoder = next(n for n in statements if isinstance(n.targets[0], ast.Name) and n.targets[0].id == "obsgoal_cond")
    original_distance = next(n for n in statements if isinstance(n.targets[0], ast.Name) and n.targets[0].id == "dists")
    a, b = selection["candidate_start"], selection["candidate_end_inclusive"]
    namespace = {"model": model, "obs_images": original["observation"],
                 "goal_image": torch.cat([transform_images(im, CONFIG["image_size"], center_crop=False).cuda()
                                           for im in images[a:b+1]], dim=0),
                 "mask": torch.zeros(1, dtype=torch.long, device="cuda:0")}
    with torch.set_grad_enabled(True):
        exec(compile(ast.Module(body=[original_encoder, original_distance], type_ignores=[]), "original_navigate_head", "exec"), namespace)
    official_distances = to_numpy(namespace["dists"].flatten())
    np.testing.assert_array_equal(official_distances, selection["distances"])
    official_condition = namespace["obsgoal_cond"][selection["selected_subgoal_id"]-a].unsqueeze(0).detach()
    assert torch.equal(result["condition"], official_condition)
    expected = diffuse_condition(model, official_condition, noise, 102)
    for key in expected:
        assert torch.equal(expected[key], result[key]), key
    torch.cuda.synchronize()
    report = {"status": "PASS", "map_manifest_sha256": sha256_file(args.topomap), "checkpoint_coverage": coverage,
              "same_condition_noise_ddpm_seed_max_abs_error": errors,
              "single_goal_encoder_and_distance": "bitwise_equal",
              "batched_official_encoder_and_distance": "bitwise_equal",
              "selected_condition_diffusion": "bitwise_equal", "topomap_component_calls": counted.counts,
              "sample_shape": list(result["metric"].shape), "selection_example": selection,
              "torch": torch.__version__, "gpu": torch.cuda.get_device_name(),
              "peak_torch_allocated_bytes": torch.cuda.max_memory_allocated(),
              "validation_wall_s": (time.monotonic_ns()-begin)/1e9,
              "input_note": "map nodes0..3 as chronological RGB test history, node4 for fixed-goal equality; not navigation or a 4Hz observation-performance experiment",
              "new_navigation_count": 0}
    write_json(args.out/"gpu_equivalence.json", report)
    print(json.dumps({k: report[k] for k in ("status", "same_condition_noise_ddpm_seed_max_abs_error", "topomap_component_calls", "sample_shape")}), flush=True)


if __name__ == "__main__":
    main()
