import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase41.config import runtime_config as frozen_config,verify as verify41,SCENES,INDICES

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase43p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase43p_01'
METHODS=('OURS-DETOUR+HMM',)


def protocol():return json.loads((HERE/'protocol.json').read_text())


def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS
    c=frozen_config('OURS-DETOUR',index,timeout,level)
    c.update(phase43p=True,phase43p_method=method)
    return c


def verify():
    verify41();p=protocol();assert p['status']=='FROZEN' and not p['smoke']['enabled']
    assert p['main_order']==[dict(scene=s,index=i,method=METHODS[0]) for i in INDICES for s in SCENES]
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
