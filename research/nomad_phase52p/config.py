"""Frozen Phase47 environment and localization, registered Phase52 policies."""
import json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase47c.config import runtime_config as frozen_config,verify as verify47
HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase52p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase52p_01'
METHODS=('CUT-HOLD','GRAPH-REC');INDICES=(221,222);BASE_SCENES=('SLW','LC','L2','H1','H2');CONDITIONS=('D075','D150')
SCENES=tuple(f'{s}_{k}' for s in BASE_SCENES for k in CONDITIONS);ORDER_SEED=20261115

def protocol():return json.loads((HERE/'protocol.json').read_text())
def split(level):
    s,k=level.rsplit('_',1);assert s in BASE_SCENES and k in CONDITIONS;return s,k

def registered_order():
    rng=random.Random(ORDER_SEED);order=[]
    for condition in CONDITIONS:
        for index in INDICES:
            for scene in BASE_SCENES:
                methods=list(METHODS);rng.shuffle(methods)
                order.extend(dict(scene=f'{scene}_{condition}',index=index,method=m) for m in methods)
    return order

def runtime_config(method,index,timeout=90,level='H1_D075'):
    assert method in METHODS and index in INDICES and timeout==90
    scene,condition=split(level);c=frozen_config('OURS-DETOUR+HMM',index,90,scene)
    c.update(phase52p=True,phase52p_method=method,phase52p_level=level,phase52p_condition=condition,
        phase52p_delay_s=.75 if condition=='D075' else 1.5,run_id=f'{level}_{index}_{method}')
    return c

def verify():
    verify47();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
