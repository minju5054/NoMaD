"""Standard-library configuration; numerical imports stay in the simulator."""
import json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase29.config import runtime_config as frozen_config

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase34p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase34p_01'
METHODS=('C0-NA+EC','C0-NA+EC-R2');SCENES=('SLW','LC','L2','H1','H2');INDICES=(210,211);ORDER_SEED=20261108

def registered_order():
    rng=random.Random(ORDER_SEED);blocks=[];order=[]
    for index in INDICES:
        for scene in SCENES:
            methods=list(METHODS);rng.shuffle(methods);blocks.append(dict(scene=scene,index=index,methods=methods));order.extend(dict(scene=scene,index=index,method=m) for m in methods)
    return blocks,order

def protocol():return json.loads((HERE/'protocol.json').read_text())

def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS and index in INDICES and level in SCENES and timeout==90
    c=frozen_config('C0-NA',201,90,level)
    c.update(seed_offset=index*10000,run_id=f'{level}_{index}',phase29_index=index,
             phase32=True,phase32_method='C0-NA+EC',phase32_index=index,
             phase34=True,phase34_method=method,phase34_index=index,storage_version=2)
    return c

def verify():
    from nomad_phase32.config import verify as frozen_verify
    frozen_verify();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()[1]
    for file,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/file)==h,file
    for scene in p['scenes'].values():
        assert sha256_file(ROOT/scene['scenario'])==scene['scenario_sha256'];assert sha256_file(scene['topomap'])==scene['topomap_sha256']
    return p
