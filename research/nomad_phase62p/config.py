import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase61p import config as base
HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase62p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase62p_01'
METHODS=('UG-GOAL',);SCENES=base.SCENES;INDICES=base.INDICES;ORDER_SEED=base.ORDER_SEED

def protocol():return json.loads((HERE/'protocol.json').read_text())
def registered_order():return [dict(scene=s,index=i,method='UG-GOAL') for s in SCENES for i in INDICES]
def runtime_config(method,index,timeout=90,level='H1-v2'):
    assert method=='UG-GOAL';c=base.runtime_config('CUT',index,timeout,level)
    c.update(phase62p=True,phase62p_method=method,run_id=f'{level}_{index}_{method}')
    return c
def verify():
    base.verify();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
