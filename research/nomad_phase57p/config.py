"""Standard-library registration and frozen scene/method adapters."""
import json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase40p.launch import bind
from nomad_phase47c.config import runtime_config as frozen_config
from nomad_phase53p.config import verify as verify53
HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase57p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase57p_01'
METHODS=('NOMAD_RAW','MIN','MIN+G18');SCENES=('H1-v2','SLW','H2');INDICES=(227,228);ORDER_SEED=20261117

def protocol():return json.loads((HERE/'protocol.json').read_text())
def registered_order():
    rng=random.Random(ORDER_SEED);order=[]
    for s in SCENES:
        for i in INDICES:
            methods=list(METHODS);rng.shuffle(methods)
            order.extend(dict(scene=s,index=i,method=m) for m in methods)
    return order
def runtime_config(method,index,timeout=90,level='H1-v2'):
    assert method in METHODS and index in INDICES and level in SCENES and timeout==90
    base='NOMAD_RAW' if method=='NOMAD_RAW' else 'OURS-DETOUR+HMM'
    c=bind(frozen_config,INDICES=INDICES,protocol=protocol)(base,index,timeout,'H1' if level=='H1-v2' else level)
    if level=='H1-v2':
        from nomad_h1v2.scene import configure
        c=configure(c)
    c.update(phase57p=True,phase57p_method=method,phase57p_level=level,run_id=f'{level}_{index}_{method}')
    return c
def verify():
    verify53();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
