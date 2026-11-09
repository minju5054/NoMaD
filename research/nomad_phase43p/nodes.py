"""Saved inference node errors; true robot pose is evaluation-only."""
import json
from pathlib import Path
import numpy as np


def node_errors(root,cohort):
    root=Path(root);cfg=json.loads((root/'scenario.json').read_text())
    nodes=json.loads(Path(cfg['topomap_manifest']).read_text())['nodes']
    xy=np.asarray([n['world_pose'][:2] for n in nodes],float);rows=[];previous=None
    for line in (root/'model/inference.jsonl').read_text().splitlines():
        if not line.strip():continue
        e=json.loads(line);m=e['topomap'];truth=int(np.argmin(np.linalg.norm(xy-np.asarray(e['observation_pose'])[:2],axis=1)))
        closest=int(m['closest_node']);ids=m['candidate_ids'];values=m['distances'];raw=int(ids[int(np.argmin(values))])
        rows.append(dict(cohort=cohort,scene=cfg['phase16_scene'],seed=cfg['seed_offset']//10000,inference_id=e['id'],
            observation_s=e['observation_sim_s'],closest_node=closest,true_node=truth,signed_error=closest-truth,abs_error=abs(closest-truth),
            raw_argmin_node=raw,raw_argmin_abs_error=abs(raw-truth),truth_outside_window=truth not in ids,
            jump=abs(closest-previous)>=3 if previous is not None else None,
            transition_K=(m.get('hmm') or {}).get('transition_half_width')))
        previous=closest
    return rows
