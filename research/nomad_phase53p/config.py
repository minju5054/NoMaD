import copy,json,random
from pathlib import Path
from types import FunctionType
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase47c.config import runtime_config as frozen_config,verify as verify47
HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase53p'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase53p_01';SMOKE_ROOT=ROOT.parent/'artifacts/isaac6/phase53p_smoke_01'
METHODS=('CUT','GRAPH-HO');INDICES=(221,222);BASE_SCENES=('SLW','LC','L2','H1','H2');CONDITIONS=('D075','D150')
SCENES=tuple(f'{s}_{c}' for c in CONDITIONS for s in BASE_SCENES);ORDER_SEED=20261115

def protocol():return json.loads((HERE/'protocol.json').read_text())
def split(level):
    s,c=level.rsplit('_',1);assert s in BASE_SCENES and c in CONDITIONS
    return s,c

def registered_order():
    rng=random.Random(ORDER_SEED);order=[]
    for condition in CONDITIONS:
        for index in INDICES:
            for scene in BASE_SCENES:
                methods=list(METHODS);rng.shuffle(methods)
                order.extend(dict(scene=f'{scene}_{condition}',index=index,method=m) for m in methods)
    return order

def runtime_config(method,index,timeout=90,level='H1_D075'):
    assert method in METHODS and timeout==90
    assert index in INDICES or (index==95 and method=='GRAPH-HO' and level=='LC_D075')
    s,condition=split(level);fn=frozen_config
    expanded=FunctionType(fn.__code__,dict(fn.__globals__,INDICES=(*INDICES,95)),fn.__name__,fn.__defaults__,fn.__closure__)
    c=expanded('OURS-DETOUR+HMM',index,timeout,s)
    c.update(phase53p=True,phase53p_method=method,phase53p_level=level,phase53p_condition=condition,
             phase53p_delay_s=.75 if condition=='D075' else 1.5,run_id=f'{level}_{index}_{method}')
    return c

def verify():
    verify47();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
