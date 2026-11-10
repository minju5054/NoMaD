"""Standard-library launcher configuration; numerical scene imports are deferred."""
import json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase53p.config import runtime_config as phase53_config,verify as verify53
HERE=Path(__file__).parent;OUT=ROOT/'research/results/h1v2_trial';RUN_ROOT=ROOT.parent/'artifacts/isaac6/h1v2_trial_01'
METHODS=('CUT','GRAPH-HO');CONDITIONS=('D075','D150');INDICES=(221,)
SCENES=tuple('H1-v2_'+x for x in CONDITIONS);ORDER_SEED=20261116

def protocol():return json.loads((HERE/'protocol.json').read_text())
def split(level):
    assert level in SCENES
    return level.rsplit('_',1)
def registered_order():
    rows=[dict(scene='H1-v2_'+c,index=221,method=m) for c in CONDITIONS for m in METHODS]
    random.Random(ORDER_SEED).shuffle(rows);return rows

def runtime_config(method,index,timeout=90,level='H1-v2_D075'):
    assert method in METHODS and index==221 and timeout==90
    _,condition=split(level)
    from nomad_h1v2.scene import configure
    c=configure(phase53_config(method,index,timeout,'H1_'+condition))
    c.update(h1v2_trial=True,h1v2_trial_level=level,run_id=f'{level}_{index}_{method}')
    return c

def verify():
    verify53();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order() and p['smoke']['enabled'] is False
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
