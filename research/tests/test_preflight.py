"""Numerical contracts, negative coverage cases, and actual checkpoint GPU inference."""
import ast
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image
import pytest
import torch
from torchvision import transforms

from nomad_preflight import native


def test_official_source_hashes_unchanged():
    manifest = json.loads((native.ROOT / "research/results/source_manifest.json").read_text())
    for relative, expected in manifest["sha256"].items():
        if relative.startswith("diffusers=="):
            import diffusers.schedulers.scheduling_ddpm as ddpm
            path = Path(ddpm.__file__)
        else:
            path = native.ROOT / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative


def test_preprocessing_matches_explicit_reference():
    # Synthetic RGB is used only for a unit test, never a performance/behavior claim.
    imgs = [Image.fromarray(np.full((120, 160, 3), v, np.uint8)) for v in [0, 64, 128, 255]]
    out = native.transform_images(imgs, [96, 96], center_crop=False)
    expected = torch.cat([transforms.Normalize([.485, .456, .406], [.229, .224, .225])(
        transforms.ToTensor()(im.resize([96, 96]))).unsqueeze(0) for im in imgs], dim=1)
    assert out.shape == (1, 12, 96, 96)
    assert out.dtype == torch.float32
    torch.testing.assert_close(out, expected, rtol=0, atol=0)


def test_normalization_and_cumsum_known_values():
    raw = torch.tensor([[[-1., -1.], [0., 0.], [1., 1.]]])
    actual = native.get_action(raw)
    # Inverse min/max deltas: (-2.5,-4), (1.25,0), (5,4).
    expected = torch.tensor([[[-2.5, -4.], [-1.25, -4.], [3.75, 0.]]])
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    deltas = native.unnormalize_data(raw.numpy(), native.ACTION_STATS)
    np.testing.assert_allclose(native.normalize_data(deltas, native.ACTION_STATS), raw.numpy(), rtol=0, atol=0)
    # Official scaling is only applied after recovering cumulative displacement.
    torch.testing.assert_close(actual[:, 2] * .05, torch.tensor([[.1875, 0.]]), rtol=0, atol=0)


def test_coverage_rejects_missing_extra_and_wrong_shape():
    model = torch.nn.Linear(2, 3)
    assert native.checkpoint_coverage(model, model.state_dict())["parameter_coverage"] == 1
    damaged = dict(model.state_dict())
    del damaged["bias"]
    damaged["extra"] = torch.zeros(1)
    damaged["weight"] = torch.zeros(1)
    report = native.checkpoint_coverage(model, damaged)
    assert report["missing_keys"] == ["bias"]
    assert report["unexpected_keys"] == ["extra"]
    assert report["shape_mismatch_keys"] == ["weight"]
    assert report["parameter_coverage"] == 0


def test_scheduler_contract():
    s = native.scheduler()
    assert s.timesteps.tolist() == list(range(9, -1, -1))
    assert s.config.beta_schedule == "squaredcos_cap_v2"
    assert s.config.prediction_type == "epsilon"
    assert s.config.variance_type == "fixed_small"
    assert s.config.clip_sample is True


@pytest.fixture(scope="module")
def gpu_model():
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable: GPU verification NOT RUN")
    checkpoint = os.environ.get("NOMAD_CHECKPOINT")
    if not checkpoint:
        pytest.skip("NOMAD_CHECKPOINT unset: checkpoint verification NOT RUN")
    model, coverage = native.load_checked(Path(checkpoint), torch.device("cuda:0"))
    return model, coverage


@pytest.fixture(scope="module")
def real_inputs():
    directory = os.environ.get("NOMAD_INPUTS")
    if not directory:
        pytest.skip("NOMAD_INPUTS unset: real RGB verification NOT RUN")
    p = Path(directory)
    return [Image.open(p / f"obs_{i}.jpg").convert("RGB") for i in range(4)], Image.open(p / "goal.jpg").convert("RGB")


def test_actual_checkpoint_coverage_and_sm120(gpu_model):
    _, coverage = gpu_model
    assert coverage["missing_keys"] == coverage["unexpected_keys"] == coverage["shape_mismatch_keys"] == []
    assert coverage["parameter_coverage"] == 1
    assert coverage["matching_state_tensors"] == coverage["total_state_tensors"]
    assert torch.cuda.get_device_capability() == (12, 0)
    assert "sm_120" in torch.cuda.get_arch_list()
    x = torch.ones(64, 64, device="cuda")
    assert torch.equal(x @ x, torch.full_like(x, 64))


def test_gpu_shapes_fixed_noise_and_original_loop(gpu_model, real_inputs):
    model, _ = gpu_model
    observations, goal = real_inputs
    noise = torch.randn((8, 8, 2), device="cuda", generator=torch.Generator(device="cuda").manual_seed(11))
    seen = {}
    handles = []
    for name, module in [("obs", model.vision_encoder.obs_encoder._conv_stem),
                         ("goal", model.vision_encoder.goal_encoder._conv_stem),
                         ("attention", model.vision_encoder.sa_encoder),
                         ("diffusion", model.noise_pred_net)]:
        # Pre-hooks on internal tensors: no upstream changes or tensor substitution.
        if name == "diffusion":
            handles.append(module.register_forward_hook(
                lambda m, args, output: seen.setdefault("diffusion", []).append(tuple(output.shape))))
        else:
            def record(m, args, name=name):
                seen[name] = tuple(args[0].shape)
            handles.append(module.register_forward_pre_hook(record))
    try:
        a = native.infer(model, observations, goal, noise, 22)
    finally:
        for handle in handles:
            handle.remove()
    assert seen["obs"] == (4, 3, 96, 96)
    assert seen["goal"] == (1, 6, 96, 96)
    assert seen["attention"] == (1, 5, 256)
    assert seen["diffusion"] == [(8, 8, 2)] * 10
    b = native.infer(model, observations, goal, noise, 22)
    assert a["condition"].shape == (1, 256)
    assert a["distance"].shape == (1, 1)
    for k in ["normalized_diffusion", "cumulative", "metric"]:
        assert a[k].shape == (8, 8, 2)
        assert a[k].dtype == torch.float32
        assert torch.isfinite(a[k]).all()
        torch.testing.assert_close(a[k], b[k], atol=1e-6, rtol=0)
    assert a["goal"].shape == (1, 3, 96, 96)
    # Execute the unchanged upstream denoising FOR statement as an independent oracle.
    path = native.ROOT / "deployment/src/navigate.py"
    tree = ast.parse(path.read_text())
    loops = [n for n in ast.walk(tree) if isinstance(n, ast.For)
             and isinstance(n.target, ast.Name) and n.target.id == "k"
             and "noise_scheduler.timesteps" in ast.unparse(n.iter)]
    assert len(loops) == 1
    namespace = {"model": model, "noise_scheduler": native.scheduler(), "naction": noise.clone(),
                 "obs_cond": a["condition"].repeat(8, 1)}
    with torch.no_grad(), torch.random.fork_rng(devices=[0]):
        torch.manual_seed(22)
        exec(compile(ast.Module(body=loops, type_ignores=[]), str(path), "exec"), namespace)
    torch.testing.assert_close(a["normalized_diffusion"], namespace["naction"], rtol=0, atol=0)
    torch.testing.assert_close(a["selected_waypoint"], native.get_action(namespace["naction"])[0, 2] * .05, rtol=0, atol=0)
    official_actions = native.get_action(namespace["naction"]).cpu().numpy()
    chosen_waypoint = official_actions[0][2]
    chosen_waypoint[:2] *= native.ROBOT["max_v"] / native.ROBOT["frame_rate"]
    np.testing.assert_array_equal(a["selected_waypoint"].cpu().numpy(), chosen_waypoint)
    changed = native.infer(model, observations, goal, noise, 23)
    assert not torch.equal(a["normalized_diffusion"], changed["normalized_diffusion"])


def test_encoder_original_grad_scope_equivalence(gpu_model, real_inputs):
    # Preserve navigate.py's encoder grad scope, which affects Transformer fast paths.
    model, _ = gpu_model
    observations, goal = real_inputs
    obs = native.transform_images(observations, [96, 96]).cuda()
    target = native.transform_images(goal, [96, 96]).cuda()
    mask = torch.zeros(1, dtype=torch.long, device="cuda")
    reference = model("vision_encoder", obs_img=obs, goal_img=target, input_goal_mask=mask)
    reference_distance = model("dist_pred_net", obsgoal_cond=reference)
    noise = torch.zeros((8, 8, 2), device="cuda")
    actual = native.infer(model, observations, goal, noise, 22)
    torch.testing.assert_close(actual["condition"], reference, atol=0, rtol=0)
    torch.testing.assert_close(actual["distance"], reference_distance, atol=0, rtol=0)


def test_goal_free_mask(gpu_model, real_inputs):
    model, _ = gpu_model
    observations, goal = real_inputs
    noise = torch.randn((8, 8, 2), device="cuda", generator=torch.Generator(device="cuda").manual_seed(11))
    a = native.infer(model, observations, goal, noise, 22, goal_mask=1)
    b = native.infer(model, observations, observations[0], noise, 22, goal_mask=1)
    torch.testing.assert_close(a["condition"], b["condition"], atol=1e-6, rtol=0)
    torch.testing.assert_close(a["normalized_diffusion"], b["normalized_diffusion"], atol=1e-6, rtol=0)
