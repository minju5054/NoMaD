import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase38.config import runtime_config as ours_config
from nomad_phase43p.config import verify as verify43,SCENES,INDICES

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase45p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase45p_01'
METHODS=('OURS+HMM',)


def protocol():return json.loads((HERE/'protocol.json').read_text())


def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS and index in INDICES
    c=ours_config('OURS',index,timeout,level)
    c.update(phase41=True,nomad_goal_stop=True,phase43p=True,phase43p_method=method,phase45p=True,phase45p_method=method)
    return c


def verify():
    verify43();p=protocol();assert p['status']=='FROZEN' and not p['smoke']['enabled']
    assert p['main_order']==[dict(scene=s,index=i,method=METHODS[0]) for i in INDICES for s in SCENES]
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
