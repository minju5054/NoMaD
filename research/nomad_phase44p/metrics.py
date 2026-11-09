import json
from pathlib import Path
from nomad_phase43p.metrics import audit as frozen_audit


def audit(root):
    r=frozen_audit(root)
    appearance=json.loads((Path(root)/'appearance_check.json').read_text())
    assert appearance['geometry_identical']
    r['appearance_geometry_sha256']=appearance['geometry_sha256']
    for e in r['node_errors']:e['cohort']='Phase44-P'
    return r
