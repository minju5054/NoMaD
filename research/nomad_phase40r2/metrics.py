from nomad_phase40p.metrics import audit as frozen_audit


def audit(root):
    row=frozen_audit(root);row['method']='OURS-R2'
    assert row['planner_installations'].get('R3',0)==0
    assert row['detour_trigger_count']==row['detour_applied_count']==0
    return row
