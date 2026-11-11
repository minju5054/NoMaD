"""Unmodified Phase18 audit, success rule and checkpoint; RAW-only validation."""
import json
from pathlib import Path
import numpy as np
from nomad_phase18.metrics import audit as frozen_audit
from nomad_phase17 import metrics as parent
from .config import METHOD,protocol

def audit(root):
    root=Path(root);p=protocol();cfg=json.loads((root/'scenario.json').read_text())
    assert cfg['phase18raw'] and cfg['phase15b_method']==METHOD
    assert p['raw_goal_rule']=='PHASE18_GEOMETRIC' and cfg['goal_tolerance_m']==.3
    assert cfg['nomad_goal_stop'] is False and not (root/'declared_arrival.json').exists()
    r=frozen_audit(root)
    for e in parent.rows(root/'events.jsonl'):
        assert e['phase18raw']==dict(sample=0,depth_filter=False,graph=False,EC=False,recovery=False)
        np.testing.assert_array_equal(e['chunk']['native_local_xy_m'],e['overnight_metric_samples'][0])
    assert r['graph_calls']==0 and r['recovery_count']==0
    assert not (root/'exec_cert.jsonl').exists()
    r.update(method=METHOD,raw_goal_rule=p['raw_goal_rule'],safety_failure=bool(r['collision'] or r['corridor']),timeout=bool(r['stuck']))
    return r
