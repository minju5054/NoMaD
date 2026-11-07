import json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.config import runtime_config as frozen_config

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase35'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase35_01'
METHODS=('OURS','ASTAR+EC','SAFE_TE','SAFE_RTC','NOMAD_RAW')
SMOKE_METHODS=METHODS[1:];SCENES=('SLW','LC','L2','H1','H2');INDICES=(212,213,214)
ORDER_SEED=20261109
ALIASES={'OURS':'C0','ASTAR+EC':'B4_ASTAR','SAFE_TE':'B1_SAFE_TE','SAFE_RTC':'B2_SAFE_RTC','NOMAD_RAW':'B0_NOMAD_RAW'}

def registered_order():
    rng=random.Random(ORDER_SEED);blocks=[];order=[]
    for index in INDICES:
        for scene in SCENES:
            methods=list(METHODS);rng.shuffle(methods)
            blocks.append(dict(scene=scene,index=index,methods=methods))
            order.extend(dict(scene=scene,index=index,method=m) for m in methods)
    return blocks,order

def protocol():return json.loads((HERE/'protocol.json').read_text())

def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS and index in (*INDICES,95) and timeout==90 and level in SCENES
    c=frozen_config(ALIASES[method],95 if index==95 else 201,90,level)
    c.update(seed_offset=index*10000,run_id=f'{level}_{index}',phase35=True,phase35_method=method,
             phase35_index=index,storage_version=2)
    if method in ('OURS','ASTAR+EC'):
        c.update(phase29=True,phase29_method='C0-NA',phase29_index=index,
                 phase32=True,phase32_method='C0-NA+EC',phase32_index=index)
    return c

def verify():
    from nomad_phase32.config import verify as old_verify
    old_verify();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()[1]
    for f,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    for scene in p['scenes'].values():
        assert sha256_file(ROOT/scene['scenario'])==scene['scenario_sha256']
        assert sha256_file(scene['topomap'])==scene['topomap_sha256']
    return p
