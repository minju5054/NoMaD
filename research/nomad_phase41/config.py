"""Fifteen frozen Phase38 OURS-DETOUR blocks; only the terminal option changes."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase38.config import runtime_config as frozen_config,verify as verify38,SCENES

HERE=Path(__file__).parent
OUT=ROOT/'research/results/phase41'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase41_01'
METHODS=('OURS-DETOUR',)
INDICES=(217,219,220)


def protocol():return json.loads((HERE/'protocol.json').read_text())


def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS and index in INDICES
    c=frozen_config(method,index,timeout,level)
    c.update(phase41=True,nomad_goal_stop=True)
    return c


def verify():
    verify38();p=protocol()
    assert p['status']=='FROZEN' and not p['smoke']['enabled']
    assert p['main_order']==[dict(scene=s,index=i,method='OURS-DETOUR') for i in INDICES for s in SCENES]
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():
        assert sha256_file(ROOT/f)==h,f
    return p
