"""Ten new H runs; frozen smoke executor and historical paired baselines."""
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase28.config import runtime_config as base_config,verify as verify_r1
from .report import read

HERE=Path(__file__).parent
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase28t_main_01'
OUT=ROOT/'research/results/phase28t/main'
METHODS=('C0-H',)
SCENES=('SLW','LC','L2','H1','H2')

def protocol():return read(HERE/'protocol_main.json')

def verify():
    verify_r1();p=protocol()
    assert p['status']=='FROZEN' and p['methods']==['C0-H'] and p['indices']==[201,202] and len(p['main_order'])==10
    assert {(r['scene'],r['index'],r['method']) for r in p['main_order']}=={(s,i,'C0-H') for s in SCENES for i in (201,202)}
    assert p['timing_policy']==dict(budget_s=.30,apply_ticks=24,controller_hz=9,plant_hz=72)
    assert sha256_file(ROOT/p['smoke_gate_file'])==p['smoke_gate_sha256']
    gate=read(ROOT/p['smoke_gate_file']);assert gate['gate']['label']=='GATE_PASS' and gate['technical_validation']=='PASS'
    for f,h in {**p['source_sha256'],**p['reused_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    return p

def runtime_config(method,index,timeout=90,level='H1'):
    assert method=='C0-H' and index in (201,202) and level in SCENES and timeout==90
    c=base_config(method,index,timeout,level)
    c.update(phase28t=True,phase28t_budget_s=.30,phase28t_apply_ticks=24,phase28t_smoke_excluded=False)
    return c
