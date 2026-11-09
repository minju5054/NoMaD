import json,random
from pathlib import Path
from types import FunctionType
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase38 import config as baseline
from nomad_phase43p.config import verify as verify43

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase47c';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase47c_01'
METHODS=('NOMAD_RAW','OURS-DETOUR','OURS-DETOUR+HMM')
SCENES=baseline.SCENES;INDICES=(221,222,223,224);ORDER_SEED=20261111


def protocol():return json.loads((HERE/'protocol.json').read_text())


def registered_order():
    rng=random.Random(ORDER_SEED);blocks=[];order=[]
    for index in INDICES:
        for scene in SCENES:
            methods=list(METHODS);rng.shuffle(methods)
            blocks.append(dict(scene=scene,index=index,methods=methods))
            order.extend(dict(scene=scene,index=index,method=m) for m in methods)
    return blocks,order


def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS and index in INDICES
    fn=baseline.runtime_config
    expanded=FunctionType(fn.__code__,dict(fn.__globals__,INDICES=INDICES,protocol=protocol),fn.__name__,fn.__defaults__,fn.__closure__)
    source='OURS-DETOUR' if method=='OURS-DETOUR+HMM' else method
    c=expanded(source,index,timeout,level)
    c.update(phase41=True,nomad_goal_stop=True,phase47c=True,phase47c_method=method)
    if method=='OURS-DETOUR+HMM':c.update(phase43p=True,phase43p_method=method)
    return c


def verify():
    verify43();p=protocol();assert p['status']=='FROZEN' and not p['smoke']['enabled']
    assert p['main_order']==registered_order()[1]
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
