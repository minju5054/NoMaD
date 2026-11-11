"""Exact Phase58 order, geometry, jitter and methods; NET provenance only."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase58p.config import METHODS,SCENES,INDICES,ORDER_SEED,registered_order,runtime_config as frozen_config,verify as verify58
HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase59p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase59p_01'
def protocol():return json.loads((HERE/'protocol.json').read_text())
def runtime_config(method,index,timeout=90,level='H1-v2'):
    c=frozen_config(method,index,timeout,level)
    c.update(phase59p=True,phase59p_transition='NET')
    return c
def verify():
    verify58();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
