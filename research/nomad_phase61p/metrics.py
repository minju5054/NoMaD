"""Frozen outcomes; validate oracle input clock/node/window separately."""
import json
from pathlib import Path
import numpy as np
from nomad_phase40p.launch import bind
from nomad_phase41.metrics import audit as original_outcomes
from nomad_phase47c import metrics as m47
from nomad_phase53p import metrics as m53
from nomad_phase58p import metrics as m58
from nomad_phase24r.online_metrics import rows
from .localization import Localization

def oracle_audit(root):
    root=Path(root);r=original_outcomes(root);c=json.loads((root/'scenario.json').read_text())
    nodes=json.loads(Path(c['topomap_manifest']).read_text())['nodes'];pose=[None]
    loc=Localization([n['world_pose'] for n in nodes],position_provider=lambda:pose[0])
    for event in rows(root/'model/inference.jsonl'):
        pose[0]=event['observation_pose'];loc.window();m=event['topomap'];expected=loc.select(m['distances'])
        assert 'hmm' not in m and m['oracle']['HMM_used'] is False
        for k in ('candidate_ids','closest_node','selected_subgoal_id','topomap_goal_node_reached'):assert m[k]==expected[k],(event['id'],k)
        np.testing.assert_array_equal(m['oracle']['pose'],pose[0])
        assert m['oracle']['analysis_only'] and m['oracle']['observation_tick']==round(event['observation_sim_s']*72)
    return r
_a47=bind(m47.audit,original_audit=oracle_audit)
_a53=bind(m53.audit,frozen_audit=_a47)
_a58=bind(m58.audit,frozen_audit=_a53)

def audit(root):
    r=_a58(root);c=json.loads((Path(root)/'scenario.json').read_text());assert c['phase61p_localization']=='ORACLE_NEAREST_XY'
    assert c['phase47c_method']=='OURS-DETOUR' and not c.get('phase43p')
    assert all(e['abs_error']==0 for e in r['node_errors'])
    checks=json.loads((Path(root)/'summary.json').read_text())['frame_and_rgb_check']
    assert checks['oracle_localization_only'] and checks['oracle_used_for_control'] and checks['oracle_obstacles_for_control'] is False
    r.update(oracle_localization_analysis_only=True,localization='ORACLE_NEAREST_XY',oracle_pose_clock='observation_pose')
    return r
