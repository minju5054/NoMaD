"""Standard-library-only registration and frozen scene adapters."""
import copy,json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase53p.config import runtime_config as cut_config,verify as verify53
HERE=Path(__file__).parent
OUT=ROOT/'research/results/phase55p'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase55p_01'
METHODS=('U-GRAPH',);INDICES=(221,222)
BASE_SCENES=('SLW','LC','L2','H1','H2','H1-v2');CONDITIONS=('D075','D150')
SCENES=tuple(s+'_'+d for d in CONDITIONS for s in BASE_SCENES)
def split(level):
    s,d=level.rsplit('_',1);assert s in BASE_SCENES and d in CONDITIONS
    return s,d
def registered_order():
    return [dict(scene=s+'_'+d,index=i,method='U-GRAPH') for d in CONDITIONS for i in INDICES for s in BASE_SCENES]
def protocol():return json.loads((HERE/'protocol.json').read_text())
def runtime_config(method,index,timeout=90,level='H1_D075'):
    assert method in METHODS and index in INDICES and timeout==90
    s,d=split(level);c=cut_config('CUT',index,timeout,('H1' if s=='H1-v2' else s)+'_'+d)
    if s=='H1-v2':
        from nomad_h1v2.scene import configure
        c=configure(c)
    c.update(phase55p=True,phase55p_method=method,phase55p_level=level,phase55p_condition=d,run_id=f'{level}_{index}_{method}')
    return c
def verify():
    verify53();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
