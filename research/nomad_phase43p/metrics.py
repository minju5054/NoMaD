import json
from pathlib import Path
from nomad_phase41.metrics import audit as frozen_audit
from .localization import Localization
from .nodes import node_errors


def audit(root):
    root=Path(root);r=frozen_audit(root);r['method']='OURS-DETOUR+HMM'
    cfg=json.loads((root/'scenario.json').read_text());nodes=json.loads(Path(cfg['topomap_manifest']).read_text())['nodes']
    selector=Localization([n['world_pose'] for n in nodes])
    for line in (root/'model/inference.jsonl').read_text().splitlines():
        if not line.strip():continue
        e=json.loads(line);m=e['topomap'];expected=selector.select(m['distances'],e['hmm_odometry_total_m'])
        for key in ('candidate_ids','closest_node','selected_subgoal_id','topomap_goal_node_reached'):
            assert m[key]==expected[key],(e['id'],key)
        assert e['hmm_odometry_tick']==round(e['observation_sim_s']*72)
        assert m['hmm']['transition_half_width']==expected['hmm']['transition_half_width']
    r['node_errors']=node_errors(root,'Phase43-P')
    summary=json.loads((root/'summary.json').read_text());r['final_pose']=summary['final_pose']
    r['stop_pose']=summary['final_pose'] if r['declared_arrival'] else None
    return r
