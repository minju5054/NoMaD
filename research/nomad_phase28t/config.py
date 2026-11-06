"""One excluded smoke, never a campaign; immutable numerical sources checked."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase28.config import runtime_config as original_config,verify as verify_base

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase28t';SMOKE_ROOT=ROOT.parent/'artifacts/isaac6/phase28t_smoke_01'
def protocol():return json.loads((HERE/'protocol.json').read_text())
def runtime_config(method,index,timeout=90,level='H1'):
    assert (method,index,level)==('C0-H',201,'H1') and timeout==90
    c=original_config(method,index,timeout,level);c.update(phase28t=True,phase28t_budget_s=.30,phase28t_apply_ticks=24,phase28t_smoke_excluded=True)
    return c
def verify():
    verify_base();p=protocol();assert p['status']=='FROZEN_SMOKE_ONLY'
    assert p['timing_policy']==dict(budget_s=.30,apply_ticks=24,controller_hz=9,plant_hz=72)
    assert p['gate']['denominator']=='ALL_H_CASES_EXCEPT_DETOUR_STARTED'
    assert p['gate']['excluded_reasons']==['DETOUR_STARTED']
    assert p['gate']['application_fraction_min']==.70 and p['gate']['compute_p95_max_s']==.30
    for f,h in {**p['frozen_numerical_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    return p
