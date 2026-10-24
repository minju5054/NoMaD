import time
import torch
from nomad_preflight.native import CONFIG
from nomad_isaac.topomap_inference import TopomapPolicy,encode_candidates
from nomad_isaac.topomap import candidate_range,select_subgoal,load_map

class RTCPolicy(TopomapPolicy):
    def __init__(self, manifest_path):
        self.images, self.hashes = load_map(manifest_path)
        self.closest_node, self.previous_subgoal = 0, None
        self.goal_node = len(self.images)-1

    def infer(self, model, observations, noise, scheduler_seed, rtc_target, hard=False):
        previous_closest = self.closest_node
        start, end = candidate_range(previous_closest, self.goal_node, radius=4)
        begin = time.monotonic_ns()
        condition, distance, obs, goals = encode_candidates(model, observations, self.images[start:end+1])
        values = distance.detach().flatten().cpu().numpy()
        self.closest_node, selected_id, sg_idx = select_subgoal(values, start, close_threshold=3)
        selected = condition[sg_idx].unsqueeze(0)
        selection_time = time.monotonic_ns()  # Distance CPU copy synchronizes the encoder/head.
        target=rtc_target
        if hard:
            from .rtc_hard import diffuse
            result=diffuse(model,selected,noise,scheduler_seed,target['Y'],target['W'],target['d'])
        else:
            from nomad_phase7.rtc import diffuse
            result=diffuse(model,selected,noise,scheduler_seed,target['Y'],target['W'])
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
        d=target['d']
        error=(result['metric'][:,:d]-torch.as_tensor(target['target_local_xy_m'][:d],device=noise.device,dtype=noise.dtype)[None]).norm(dim=-1) if d else None
        metadata['rtc']={'label':'RTC hard-masking ablation (DDPM adaptation)' if hard else 'RTC-style (DDPM adaptation)','d':d,'H_old':target['H_old'],'prefix_error_median_m':float(error.median()) if error is not None else None,'prefix_error_max_m':float(error.max()) if error is not None else None}
        self.previous_subgoal = selected_id
        result.update({"condition": selected.detach(), "distance": distance.detach(),
                       "observation": obs, "goal": goals[sg_idx:sg_idx+1]})
        return result, metadata
