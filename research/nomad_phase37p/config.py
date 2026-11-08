"""Standard-library registration; no SciPy/Graph imports in the launcher."""
import json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase35.config import runtime_config as frozen_config

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase37p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase37p_01'
METHODS=('OURS','OURS+PROV');SCENES=('SLW','LC','L2','H1','H2');INDICES=(215,216);ORDER_SEED=20261110

def registered_order():
    rng=random.Random(ORDER_SEED);blocks=[];order=[]
    for index in INDICES:
        for scene in SCENES:
            methods=list(METHODS);rng.shuffle(methods);blocks.append(dict(scene=scene,index=index,methods=methods))
            order.extend(dict(scene=scene,index=index,method=m) for m in methods)
    return blocks,order

def protocol():return json.loads((HERE/'protocol.json').read_text())

def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS and index in INDICES and level in SCENES and timeout==90
    c=frozen_config('OURS',212,90,level)
    c.update(seed_offset=index*10000,run_id=f'{level}_{index}',phase35_index=index,phase29_index=index,phase32_index=index,
             phase37p=True,phase37p_method=method,phase37p_index=index)
    return c

def verify():
    from nomad_phase35.config import verify as baseline_verify
    baseline_verify();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()[1]
    for f,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    for scene in p['scenes'].values():
        assert sha256_file(ROOT/scene['scenario'])==scene['scenario_sha256']
        assert sha256_file(scene['topomap'])==scene['topomap_sha256']
    return p
