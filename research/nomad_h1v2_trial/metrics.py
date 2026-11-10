"""Unchanged Phase53 audit/outcomes, environment provenance and report names."""
import json
from pathlib import Path
import numpy as np
from nomad_phase53p.metrics import audit as frozen_audit
from nomad_phase24r.online_metrics import rows
from nomad_h1v2.scene import project

def audit(root):
    root=Path(root);r=frozen_audit(root);c=json.loads((root/'scenario.json').read_text());assert c['h1v2_trial'] and c['scene_variant']=='H1-v2'
    assert c['h1v2']['requested_target']['y_m']==1.10
    summary=json.loads((root/'summary.json').read_text());dynamic=summary.get('dynamic_obstacle') or {};spawn=dynamic.get('spawn')
    r['spawn_time_s']=spawn['simulation_time_s'] if spawn else None
    r['passage_side']=r['boxes'][0].get('side') if r.get('boxes') else None
    if spawn:
        np.testing.assert_array_equal(spawn['obstacle']['center_xy_m'],c['h1v2']['box']['center_xy_m'])
        np.testing.assert_array_equal(spawn['obstacle']['size_xyz_m'],[.5,.4,.8])
        assert len(dynamic.get('boxes',[]))==1
        assert project(c['h1v2']['topomap_nodes_xy_m'],spawn['pose'])[0]>=c['h1v2']['spawn']['arc_m']
    r.update(base_scene='H1-v2',scene=c['h1v2_trial_level'])
    r['graph_rejection_reasons']={k:v for k,v in r['graph_reasons'].items() if k!='ACCEPTED'}
    return r
