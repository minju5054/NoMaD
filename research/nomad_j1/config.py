"""J1 registration and asset routing; existing J0 common files stay frozen."""
import json
import random
from pathlib import Path
from types import FunctionType
from nomad_isaac.common import ROOT,sha256_file
from . import common

HERE=Path(__file__).parent
OUT=ROOT/'research/results/j1'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/j1_01'
SMOKE_ROOT=ROOT.parent/'artifacts/isaac6/j1_smoke_01'
METHODS=('NOMAD_RAW','RTC-hard','OURS','OURS-noGRAPH','OURS-noEC')
SCENES=('SLW-v2','H1-v3','LC')
INDICES=tuple(range(231,244))
ORDER_SEED=20261112

def bind(fn,**kwargs):return FunctionType(fn.__code__,dict(fn.__globals__,**kwargs),fn.__name__,fn.__defaults__,fn.__closure__)
def protocol():return json.loads((HERE/'protocol.json').read_text())

def order():
    rng=random.Random(ORDER_SEED);out=[]
    for i in INDICES:
        block=[dict(scene=s,index=i,method=m,delay=.75) for s in SCENES for m in METHODS]
        rng.shuffle(block);out.extend(block)
    return out

def scene_config(name):
    if name=='SLW-v2':
        from nomad_slwv2.config import scene_config,verify_assets
        verify_assets();return scene_config(name)
    if name=='H1-v3':
        from nomad_h1v3.config import scene_config
        return scene_config(name)
    return common.scene_config(name)

def checkpoint_spec(name):
    if name=='SLW-v2':
        from nomad_slwv2.config import checkpoint_spec
        return checkpoint_spec(name)
    if name=='H1-v3':
        from nomad_h1v3.config import checkpoint_spec
        return checkpoint_spec(name)
    return common.checkpoint_spec(name)

def verify():
    p=protocol();assert p['status']=='FROZEN' and p['main_order']==order()
    for path,digest in p['source_sha256'].items():assert sha256_file(ROOT/path)==digest,path
    for path,digest in p['asset_sha256'].items():assert sha256_file(path)==digest,path
    return p

def runtime_config(method,index,timeout=90,level='LC'):
    assert method in METHODS and level in SCENES
    assert (index in INDICES and timeout==90) or (index==95 and timeout==30 and method=='OURS' and level=='LC')
    c=bind(common.runtime_config,scene_config=scene_config,checkpoint_spec=checkpoint_spec)(common.METHOD,index,90,level)
    c.update(j1=True,j_method=method,phase15b_method=method,phase18raw=method=='NOMAD_RAW',
             phase4c_method='GRAPH' if method in ('OURS','OURS-noEC') else 'CURV',
             overnight_method='RTC-hard' if method=='RTC-hard' else 'CURV',timeout_sim_s=timeout)
    assert c['sdf_registration']==protocol()['scenes'][level]['sdf_registration']
    return c
