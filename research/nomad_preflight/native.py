"""Execute selected upstream function definitions without ROS/training imports.

AST extraction preserves the entire original function body and source line numbers.
Only the import namespace is supplied here. No upstream file is modified.
"""
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image as PILImage
import torch
from torch import nn
from torchvision import transforms
import torchvision.transforms.functional as TF
import yaml
from diffusers.schedulers.scheduling_ddpm import DDPMScheduler
from diffusion_policy.model.diffusion.conditional_unet1d import ConditionalUnet1D
from vint_train.models.nomad.nomad import NoMaD, DenseNetwork
from vint_train.models.nomad.nomad_vint import NoMaD_ViNT, replace_bn_with_gn
from vint_train.data.data_utils import IMAGE_ASPECT_RATIO

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_SHA = "dca79815b704e5aa9c6bdc3082351f9e3b2848c2"
DP_SHA = "548a52bbb105518058e27bf34dcf90bf6f73681a"
CONFIG = yaml.safe_load((ROOT / "train/config/nomad.yaml").read_text())
ROBOT = yaml.safe_load((ROOT / "deployment/config/robot.yaml").read_text())
ACTION_STATS = {k: np.array(v) for k, v in yaml.safe_load(
    (ROOT / "train/vint_train/data/data_config.yaml").read_text())["action_stats"].items()}


def upstream_functions(relative_path, names):
    path = ROOT / relative_path
    tree = ast.parse(path.read_text(), filename=str(path))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise RuntimeError(f"Upstream functions changed: {path}: {names}")
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), globals())


upstream_functions("deployment/src/utils.py", ["load_model", "transform_images"])
upstream_functions("train/vint_train/visualizing/visualize_utils.py", ["to_numpy", "from_numpy"])
upstream_functions("train/vint_train/training/train_utils.py",
                   ["normalize_data", "unnormalize_data", "get_action"])


def checkpoint_coverage(model, state):
    expected = model.state_dict()
    matching = {k for k in expected.keys() & state.keys()
                if expected[k].shape == state[k].shape}
    parameters = dict(model.named_parameters())
    total = sum(p.numel() for p in parameters.values())
    covered = sum(p.numel() for k, p in parameters.items() if k in matching)
    return {
        "missing_keys": sorted(expected.keys() - state.keys()),
        "unexpected_keys": sorted(state.keys() - expected.keys()),
        "shape_mismatch_keys": sorted(k for k in expected.keys() & state.keys()
                                      if expected[k].shape != state[k].shape),
        "matching_state_tensors": len(matching), "total_state_tensors": len(expected),
        "covered_parameter_elements": covered, "total_parameter_elements": total,
        "parameter_coverage": covered / total,
    }


def load_checked(checkpoint, device):
    # Official loader is used verbatim (including strict=False). Independently audit it.
    model = load_model(str(checkpoint), CONFIG, device).eval()
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    coverage = checkpoint_coverage(model, state)
    if (coverage["parameter_coverage"] != 1 or coverage["missing_keys"]
            or coverage["unexpected_keys"] or coverage["shape_mismatch_keys"]):
        raise RuntimeError(f"Incomplete checkpoint: {coverage}")
    return model, coverage


def scheduler():
    result = DDPMScheduler(num_train_timesteps=CONFIG["num_diffusion_iters"],
                          beta_schedule="squaredcos_cap_v2", clip_sample=True,
                          prediction_type="epsilon")
    result.set_timesteps(CONFIG["num_diffusion_iters"])
    return result


def infer(model, observations, goal, initial_noise, scheduler_seed, goal_mask=0):
    """One selected goal; no topomap localization, ROS, or controller execution.

    Full trajectory metric scaling is a derived extension of official selected-point
    scaling. RNG reset is measurement instrumentation; DDPM step remains unchanged.
    """
    if len(observations) != CONFIG["context_size"] + 1:
        raise ValueError("Expected four RGB images ordered oldest to newest")
    if any(im.mode != "RGB" for im in [*observations, goal]):
        raise ValueError("Inputs must be decoded RGB PIL images")
    if initial_noise.ndim != 3 or tuple(initial_noise.shape[1:]) != (8, 2):
        raise ValueError("Initial noise must have shape (samples, 8, 2)")
    device = next(model.parameters()).device
    obs = transform_images(observations, CONFIG["image_size"], center_crop=False).to(device)
    goal_tensor = transform_images(goal, CONFIG["image_size"], center_crop=False).to(device)
    mask = torch.tensor([goal_mask], dtype=torch.long, device=device)
    # navigate.py encodes with grad enabled; explore.py encodes under no_grad.
    # Preserve this scope: PyTorch 2.7 Transformer fast paths change numerics.
    with torch.set_grad_enabled(goal_mask == 0):
        cond = model("vision_encoder", obs_img=obs, goal_img=goal_tensor, input_goal_mask=mask)
        distance = model("dist_pred_net", obsgoal_cond=cond)
    naction = initial_noise.to(device).clone()
    schedule = scheduler()
    devices = [device.index or 0] if device.type == "cuda" else []
    with torch.no_grad(), torch.random.fork_rng(devices=devices):
        repeated_cond = cond.repeat(initial_noise.shape[0], 1)
        torch.manual_seed(scheduler_seed)
        for k in schedule.timesteps[:]:
            noise_pred = model("noise_pred_net", sample=naction, timestep=k,
                               global_cond=repeated_cond)
            naction = schedule.step(model_output=noise_pred, timestep=k,
                                    sample=naction).prev_sample
    cumulative = get_action(naction)  # Official NumPy float64 arithmetic -> torch float32.
    metric = cumulative * (ROBOT["max_v"] / ROBOT["frame_rate"])
    return {"observation": obs, "goal": goal_tensor, "condition": cond.detach(),
            "distance": distance.detach(), "initial_noise": initial_noise,
            "normalized_diffusion": naction, "cumulative": cumulative,
            "metric": metric, "selected_waypoint": metric[0, 2].clone()}
