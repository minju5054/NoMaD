"""Only registration labels, matrix and soft target differ from Phase29 G18."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase29.config import runtime_config as original_config,verify as verify_base
HERE=Path(__file__).parent
OUT=ROOT/'research/results/phase30r'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase30r_dev_01'
METHODS=('G18-R',);SCENES=('SLW','LC','L2','H1','H2')
def protocol():return json.loads((HERE/'protocol.json').read_text())
def verify():
    verify_base();p=protocol()
    assert p['status']=='FROZEN' and p['soft_clearance_target_m']==.08
    assert p['methods']==['G18-R'] and p['indices']==[201,202] and len(p['main_order'])==10
    for f,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    return p
def runtime_config(method,index,timeout=90,level='H1'):
    assert method=='G18-R' and index in (201,202)
    c=original_config('G18',index,timeout,level)
    c.update(phase29_method=method,phase30r=True)
    return c
