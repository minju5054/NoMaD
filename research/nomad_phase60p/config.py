"""Exact Phase59 registration; verified calibration read, never a refit."""
import hashlib,json,math
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase59p.config import METHODS,SCENES,INDICES,ORDER_SEED,registered_order,runtime_config as frozen_config,verify as verify59
HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase60p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase60p_01'
MODEL_FILE=ROOT/'research/results/loc_v2_replay/calibration.json'
MODEL_SHA256='f806c6236bfdf0470faca8578fcb9ab749770d859856de411d4d341f0417c8ca'

def load_model(path=MODEL_FILE):
    raw=Path(path).read_bytes();actual=hashlib.sha256(raw).hexdigest()
    if actual!=MODEL_SHA256:raise ValueError('Frozen SIGN model_sha256 mismatch: '+actual)
    model=json.loads(raw)
    if model['status']!='FROZEN_CALIBRATION' or not model['frozen_before_evaluation']:raise ValueError('SIGN calibration is not frozen')
    if not math.isfinite(model['sigma2']) or model['sigma2']<=0:raise ValueError('Invalid frozen variance')
    return model

def protocol():return json.loads((HERE/'protocol.json').read_text())
def runtime_config(method,index,timeout=90,level='H1-v2'):
    model=load_model();c=frozen_config(method,index,timeout,level)
    c.update(phase60p=True,phase60p_transition='SIGN',phase60p_model_sha256=MODEL_SHA256,phase60p_sigma2=model['sigma2'],phase59p_transition='SIGN')
    return c
def verify():
    model=load_model();verify59();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    assert p['sign_delta']['model_sha256']==MODEL_SHA256 and p['sign_delta']['sigma2']==model['sigma2']
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
