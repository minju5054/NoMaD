import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase18 import config as base
HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase18raw';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase18raw_01'
METHODS=('NOMAD_RAW',);METHOD='NOMAD_RAW';SCENES=base.SCENES;INDICES=tuple(range(66,74));RTC=base.RTC
BASELINES=(base.PROPOSED,base.RTC)

def protocol():return json.loads((HERE/'protocol.json').read_text())
def scene(name):return base.scene(name)
def registered_order():return [dict(index=i,scene=s,method=METHOD) for i in INDICES for s in SCENES]
def runtime_config(c,method,index,manifest,timeout=90):
    assert method==METHOD and index in INDICES and timeout==90
    c=base.runtime_config(c,base.METHODS[0],index,manifest,timeout)
    c.update(phase18raw=True,phase15b_method=METHOD,raw_sample_index=0,nomad_goal_stop=False)
    return c
def verify_sources():
    base.verify_sources();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    assert p['raw_goal_rule']=='PHASE18_GEOMETRIC'
    assert p['raw_comparison_alpha']==base.protocol()['statistics']['main_alpha']
    assert p['methods']==list(METHODS)
    for f,h in {**p['source_sha256'],**p['extra_frozen_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    return p
