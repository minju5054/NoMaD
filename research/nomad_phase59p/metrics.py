"""Frozen outcome audits; NET replaces only expected localization during audit."""
import csv,json
from pathlib import Path
import numpy as np
from nomad_phase40p.launch import bind
from nomad_phase43p import metrics as m43
from nomad_phase47c import metrics as m47
from nomad_phase53p import metrics as m53
from nomad_phase58p import metrics as m58
from nomad_phase24r.online_metrics import rows
from nomad_phase42l.analyze import nearest
from .localization import Localization

def net_audit(root):
    root=Path(root);events=rows(root/'model/inference.jsonl');positions=iter([e['observation_pose'][:2] for e in events])
    def factory(nodes):return Localization(nodes,position_provider=lambda:next(positions))
    result=bind(m43.audit,Localization=factory)(root)
    for e in events:
        assert e['topomap']['hmm']['transition_model']=='NET'
        assert all(v==0. for v in e['topomap']['hmm']['memory_log_factors'])
        np.testing.assert_array_equal(e['topomap']['hmm']['odometry_xy_m'],e['observation_pose'][:2])
    return result

# Only localization replay validation changes; frozen geometry, arrival,
# timeout, command/EC and Phase58 latch/choice audits remain unchanged.
_a47=bind(m47.audit,hmm_audit=net_audit)
_a53=bind(m53.audit,frozen_audit=_a47)
_a58=bind(m58.audit,frozen_audit=_a53)

def localization_metrics(root,record):
    root=Path(root);c=json.loads((root/'scenario.json').read_text());manifest=json.loads(Path(c['topomap_manifest']).read_text())
    nodes=np.asarray([n['world_pose'] for n in manifest['nodes']],float);goal=len(nodes)-1
    with (root/'agent_trajectory.csv').open() as stream:tr=list(csv.DictReader(stream))
    dist=[float(x['goal_distance_m']) for x in tr];minimum=min(dist)
    stop=json.loads((root/'declared_arrival.json').read_text()) if (root/'declared_arrival.json').exists() else None
    estimates=record.get('node_errors',[])
    if not estimates:
        from nomad_phase43p.nodes import node_errors
        estimates=node_errors(root,'Phase59 saved-report-only')
    false=[e for e in estimates if e['closest_node']==goal and e['true_node']<goal-2]
    return dict(minimum_actual_goal_distance_m=float(minimum),reached_goal_0p7=minimum<=.7,reached_goal_0p5=minimum<=.5,
        arrived_without_declaration=minimum<=.7 and stop is None,arrived_0p5_without_declaration=minimum<=.5 and stop is None,
        declaration_estimated_node=stop['closest_node'] if stop else None,declaration_true_node=nearest(nodes,stop['pose']) if stop else None,
        goal_node=goal,false_goal_count=len(false),false_goal_inference_ids=[e['inference_id'] for e in false],
        transition_zero_width_count=sum(e.get('transition_K')==0 for e in estimates))

def audit(root):
    r=_a58(root);cfg=json.loads((Path(root)/'scenario.json').read_text());assert cfg['phase59p_transition']=='NET'
    r.update(localization_metrics(root,r));return r
