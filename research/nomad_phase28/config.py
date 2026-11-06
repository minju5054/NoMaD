"""Registered Phase28 definitions; no simulator imports."""
import json,math
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.config import runtime_config as baseline_config
from nomad_phase27r.config import verify as verify_baseline

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase28';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase28_pilot_01'
METHODS=('C0-NA','C0-H');SCENES=('SLW','LC','L2','H1','H2')
PARAMETERS=dict(nodes_after_B=10,dt_min=.1,dt_max=1.,reference_sigma=.05,nonholonomic_sigma=.03,smoothing_sigma=.03,
    clearance_preference=.15,clearance_sigma=.05,hard_clearance=.025,time_weight=.1,v_max=.3,w_max=.4,a_max=.5,
    deadline_s=.15,feedback_x=.5,feedback_y=1.,feedback_heading=.5,maxiter=100,ftol=1e-8,tolerance=1e-7)

def angular_limit(config):
    value=float(config.get('plant_alpha','inf'))
    return (value,'EXISTING_FINITE_PLANT_LIMIT') if math.isfinite(value) else (2.,'NO_FINITE_PLANT_LIMIT_FALLBACK_2')
def protocol():return json.loads((HERE/'protocol.json').read_text())
def runtime_config(method,index,timeout=90,level='L2'):
    assert method in METHODS and index in (201,202) and level in SCENES
    c=baseline_config('C0',index,timeout,level);limit,source=angular_limit(c)
    c.update(phase28_method=method,phase28=True,phase28_alpha=limit,phase28_alpha_source=source)
    return c
def verify():
    verify_baseline();p=protocol();assert p['status']=='FROZEN'
    assert p['parameters']==PARAMETERS
    for f,h in p['source_sha256'].items():assert sha256_file(ROOT/f)==h,f
    assert sha256_file(OUT/'preparation/sample_manifest.json')==p['sample_manifest_sha256']
    return p
