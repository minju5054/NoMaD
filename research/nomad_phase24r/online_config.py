"""Phase24-R opt-in matrix; original scenarios, maps and model hashes reused."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase24.online_config import runtime_config as previous_config
HERE=Path(__file__).parent;METHODS=('G','C0','C1');SCENES=('L2','SLW')
def protocol():return json.loads((HERE/'online_protocol.json').read_text())
def runtime_config(method,index,timeout=90,level='L2'):
    p=protocol();assert method in METHODS and level in SCENES and index in [95,*p['indices']]
    c=previous_config(method,95,timeout,level)
    c.update(phase24r=True,phase24r_method=method,seed_offset=index*10000,run_id=f'{level}_{index}')
    assert c['goal_tolerance_m']==.3
    return c
def verify():
    p=protocol()
    for name,h in {**p['preserved_sources'],**p.get('source_sha256',{})}.items():assert sha256_file(ROOT/name)==h,name
    for s in p['scenes'].values():
        assert sha256_file(ROOT/s['scenario'])==s['scenario_sha256'];assert sha256_file(s['topomap'])==s['topomap_sha256']
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    return p
