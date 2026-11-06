import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.config import runtime_config as baseline
HERE=Path(__file__).parent
OUT=ROOT/'research/results/phase29'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase29_01'
METHODS=('C0','C0-NA','SM','G18');SCENES=('SLW','LC','L2','H1','H2')
def protocol():return json.loads((HERE/'protocol.json').read_text())
def verify():
    p=protocol();assert p['status']=='FROZEN'
    for f,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    for s in p['scenes'].values():
        assert sha256_file(ROOT/s['scenario'])==s['scenario_sha256'];assert sha256_file(s['topomap'])==s['topomap_sha256']
    return p
def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS and index in (201,202,203,204,205) and level in SCENES and timeout==90
    c=baseline('C0',201,90,level)
    c.update(seed_offset=index*10000,run_id=f'{level}_{index}',phase29=True,phase29_method=method,phase29_index=index)
    return c
