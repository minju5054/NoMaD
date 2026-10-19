"""Official NoMaD candidate encoding/distance selection, then ONE diffusion decode."""
import time

import torch

from nomad_preflight.native import CONFIG, ROBOT, transform_images, scheduler, get_action
from .topomap import candidate_range, select_subgoal, load_map


def diffuse_condition(model, condition, initial_noise, scheduler_seed):
    """Same selected-condition DDPM/RNG/action path as the verified native.infer."""
    device = next(model.parameters()).device
    naction = initial_noise.to(device).clone()
    schedule = scheduler()
    devices = [device.index or 0] if device.type == "cuda" else []
    with torch.no_grad(), torch.random.fork_rng(devices=devices):
        repeated = condition.repeat(initial_noise.shape[0], 1) if condition.ndim == 2 else condition.repeat(initial_noise.shape[0], 1, 1)
        torch.manual_seed(scheduler_seed)
        for k in schedule.timesteps[:]:
            predicted = model("noise_pred_net", sample=naction, timestep=k, global_cond=repeated)
            naction = schedule.step(model_output=predicted, timestep=k, sample=naction).prev_sample
    cumulative = get_action(naction)
    metric = cumulative * (ROBOT["max_v"] / ROBOT["frame_rate"])
    return {"normalized_diffusion": naction, "cumulative": cumulative, "metric": metric,
            "selected_waypoint": metric[0, 2].clone()}


def encode_candidates(model, observations, images):
    assert len(observations) == CONFIG["context_size"] + 1
    assert all(image.mode == "RGB" for image in [*observations, *images])
    device = next(model.parameters()).device
    obs = transform_images(observations, CONFIG["image_size"], center_crop=False).to(device)
    # Retain official split/cat and individual image preprocessing.
    obs = torch.cat(torch.split(obs, 3, dim=1), dim=1)
    goals = torch.cat([transform_images(image, CONFIG["image_size"], center_crop=False).to(device)
                       for image in images], dim=0)
    mask = torch.zeros(1, dtype=torch.long, device=device)
    # Official navigate.py encodes with autograd enabled; preserve Transformer path.
    with torch.set_grad_enabled(True):
        condition = model("vision_encoder", obs_img=obs.repeat(len(goals), 1, 1, 1),
                          goal_img=goals, input_goal_mask=mask.repeat(len(goals)))
        distances = model("dist_pred_net", obsgoal_cond=condition)
    return condition, distances, obs, goals


class TopomapPolicy:
    def __init__(self, manifest_path):
        self.images, self.hashes = load_map(manifest_path)
        self.closest_node, self.previous_subgoal = 0, None
        self.goal_node = len(self.images)-1

    def infer(self, model, observations, noise, scheduler_seed):
        previous_closest = self.closest_node
        start, end = candidate_range(previous_closest, self.goal_node, radius=4)
        begin = time.monotonic_ns()
        condition, distance, obs, goals = encode_candidates(model, observations, self.images[start:end+1])
        values = distance.detach().flatten().cpu().numpy()
        self.closest_node, selected_id, sg_idx = select_subgoal(values, start, close_threshold=3)
        selected = condition[sg_idx].unsqueeze(0)
        selection_time = time.monotonic_ns()  # Distance CPU copy synchronizes the encoder/head.
        result = diffuse_condition(model, selected, noise, scheduler_seed)
        torch.cuda.synchronize()
        end_ns = time.monotonic_ns()
        metadata = {"candidate_start": start, "candidate_end_inclusive": end,
                    "candidate_ids": list(range(start, end+1)), "distances": values.tolist(),
                    "previous_closest_node": previous_closest, "closest_node": self.closest_node,
                    "previous_subgoal_id": self.previous_subgoal, "selected_subgoal_id": selected_id,
                    "subgoal_changed": self.previous_subgoal != selected_id,
                    "closest_moved_backward": self.closest_node < previous_closest,
                    "subgoal_moved_backward": self.previous_subgoal is not None and selected_id < self.previous_subgoal,
                    "selection_monotonic_ns": selection_time,
                    "goal_node": self.goal_node, "topomap_goal_node_reached": self.closest_node == self.goal_node,
                    "selected_subgoal_image": self.hashes[selected_id],
                    "candidate_encoding_and_selection_ms": (selection_time-begin)/1e6,
                    "diffusion_and_action_ms": (end_ns-selection_time)/1e6,
                    "diffusion_passes": 1, "diffusion_steps": CONFIG["num_diffusion_iters"]}
        self.previous_subgoal = selected_id
        result.update({"condition": selected.detach(), "distance": distance.detach(),
                       "observation": obs, "goal": goals[sg_idx:sg_idx+1]})
        return result, metadata
