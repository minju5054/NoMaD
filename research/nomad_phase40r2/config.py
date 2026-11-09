"""Same Phase40-P configuration, seeds and jitter; new method/output tag."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase40p.config import runtime_config as frozen_config,verify as verify40p,SCENES,INDICES

HERE=Path(__file__).parent
OUT=ROOT/'research/results/phase40r2'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase40r2_01'
METHODS=('OURS-R2',)


def protocol():return json.loads((HERE/'protocol.json').read_text())


def runtime_config(method,index,timeout=90,level='H1'):
    assert method=='OURS-R2'
    c=frozen_config('OURS-N',index,timeout,level)
    c.update(phase40r2=True,phase40r2_method=method)
    return c


def verify():
    verify40p();p=protocol();assert p['status']=='FROZEN' and p['smoke']['enabled'] is False
    assert p['main_order']==[dict(scene=s,index=i,method='OURS-R2') for i in INDICES for s in SCENES]
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():
        assert sha256_file(ROOT/f)==h,f
    return p
