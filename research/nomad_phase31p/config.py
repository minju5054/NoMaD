"""New seed metadata only; numerical/runtime definitions belong to frozen phases."""
import json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.config import runtime_config as c0_config
from nomad_phase28.config import runtime_config as na_config
from nomad_phase30r.config import runtime_config as r_config

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase31p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase31p_01'
METHODS=('G18-R','C0','C0-NA');SCENES=('SLW','LC','L2','H1','H2');INDICES=(206,207)
ORDER_SEED=20261107

def registered_order():
    rng=random.Random(ORDER_SEED);blocks=[];order=[]
    for index in INDICES:
        for scene in SCENES:
            methods=list(METHODS);rng.shuffle(methods)
            blocks.append(dict(scene=scene,index=index,methods=methods))
            order.extend(dict(scene=scene,index=index,method=method) for method in methods)
    return blocks,order

def protocol():return json.loads((HERE/'protocol.json').read_text())

def verify():
    from nomad_phase27r.config import verify as verify_c0
    from nomad_phase28.config import verify as verify_na
    from nomad_phase30r.config import verify as verify_r
    verify_c0();verify_na();verify_r()
    p=protocol();assert p['status']=='FROZEN' and p['methods']==list(METHODS) and p['indices']==list(INDICES)
    blocks,order=registered_order();assert p['blocks']==blocks and p['main_order']==order
    assert p['order_seed']==ORDER_SEED and p['planned']==30 and p['disk_min_bytes']==30_000_000_000
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['historical_sources']}.items():assert sha256_file(ROOT/f)==h,f
    for s in p['scenes'].values():
        assert sha256_file(ROOT/s['scenario'])==s['scenario_sha256'];assert sha256_file(s['topomap'])==s['topomap_sha256']
    return p

def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS and index in INDICES and level in SCENES and timeout==90
    # Old factories intentionally restrict their registered seeds. Construct
    # their unchanged config using a permitted seed, then set only new seed/ID.
    if method=='G18-R':c=r_config(method,201,timeout,level)
    elif method=='C0-NA':c=na_config(method,201,timeout,level)
    else:c=c0_config(method,201,timeout,level)
    c.update(seed_offset=index*10000,run_id=f'{level}_{index}',phase31p=True,phase31p_method=method,phase31p_index=index)
    if 'phase29_index' in c:c['phase29_index']=index
    return c
