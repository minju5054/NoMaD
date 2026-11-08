"""Frozen run evaluation with local method tags and additional telemetry."""
import json
from pathlib import Path
from nomad_phase35.metrics import audit as frozen_audit
from nomad_phase32.report import lines

def audit(root):
    root=Path(root);r=frozen_audit(root);c=json.loads((root/'scenario.json').read_text())
    r['method']=c['phase38_method'];r['placement_jitter']=c['phase38_jitter']
    checks=lines(root/'exec_cert.jsonl');r['ec_checks']=sum(e['event']=='CHECK' for e in checks)
    r['ec_rejects']=sum(e['event']=='CHECK' and not e['passed'] for e in checks)
    if c['phase38_method'] in ('TE+EC','RTC+EC'):
        from nomad_phase32.report import audit as ec_audit
        r.update({k:v for k,v in ec_audit(root).items() if k.startswith('ec_')})
    care=lines(root/'care.jsonl');r['care_corrections']=sum(e['event']=='CORRECTION' for e in care)
    r['care_safe_fov_commands']=sum(e['event']=='SAFE_FOV' for e in care)
    return r
