"""Exact native-path SELECT; no optimization, origin connector or controller change."""
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_isaac.handoff_audit import path_safety
from nomad_phase0.pure_pursuit import XYPath


def select(samples, observation_pose, boundary, config):
    samples = np.asarray(samples)
    assert samples.shape == (8,8,2) and np.isfinite(samples).all()
    worlds = [local_to_world(xy, np.asarray(observation_pose)) for xy in samples]
    candidates = []
    for i,xy in enumerate(worlds):
        safety = path_safety(xy, config)
        try:
            path = XYPath(xy)
            s,distance = path.project(np.asarray(boundary)[:2])
            remaining = float(path.s[-1]-s)
        except ValueError:
            s = distance = remaining = None
        candidates.append(dict(index=i, **safety, path_valid=remaining is not None,
            projected_arclength_m=s, projection_distance_m=distance, remaining_length_m=remaining))
    safe = [c for c in candidates if c['safe'] and c['path_valid']]
    chosen = min(safe, key=lambda c:(-c['remaining_length_m'], c['index']))['index'] if safe else 0
    return worlds[chosen], dict(selected_sample=chosen, all_unsafe=not bool(safe), candidates=candidates,
        anchor='observation_pose', selection_boundary=np.asarray(boundary).tolist())
