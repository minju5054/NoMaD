"""Standard-library registration, same 20 Phase38 blocks and exact jitter."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT, sha256_file
from nomad_phase38.config import runtime_config as frozen_config, verify as verify38

HERE=Path(__file__).parent
OUT=ROOT/'research/results/phase40p'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase40p_01'
SMOKE_ROOT=ROOT.parent/'artifacts/isaac6/phase40p_smoke_01'
METHODS=('OURS-N',)
SCENES=('SLW','LC','L2','H1','H2')
INDICES=(217,218,219,220)


def protocol():
    return json.loads((HERE/'protocol.json').read_text())


def runtime_config(method,index,timeout=90,level='H1'):
    assert method=='OURS-N' and index in INDICES and timeout==90 and level in SCENES
    c=frozen_config('OURS',index,timeout,level)
    c.update(phase40p=True,phase40p_method=method)
    return c


def verify():
    verify38()
    p=protocol()
    assert p['status']=='FROZEN' and not p.get('pending_questions')
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():
        assert sha256_file(ROOT/f)==h,f
    return p
