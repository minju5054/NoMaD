import json
from pathlib import Path
from nomad_isaac.common import ROOT, sha256_file
from nomad_j1.common import METHOD, runtime_config as shared_config

HERE = Path(__file__).parent
OUT = ROOT/'research/results/j0'
RUN_ROOT = ROOT.parent/'artifacts/isaac6/j0_01'
SCENES = ('H1-v2','SLW','H2','LC','CL')
INDICES = (221,222)
DELAYS = (0.,.75)

def protocol():
    return json.loads((HERE/'protocol.json').read_text())

def order():
    return [dict(scene=s,index=i,method=METHOD,delay=d) for d in DELAYS for i in INDICES for s in SCENES]

def verify():
    p=protocol()
    assert p['status']=='FROZEN' and p['main_order']==order() and p['planned']==20
    for path,digest in p['source_sha256'].items():
        assert sha256_file(ROOT/path)==digest,path
    for path,digest in p['asset_sha256'].items():
        assert sha256_file(Path(path))==digest,path
    return p

def runtime_config(method,index,timeout=90,level='SLW'):
    assert method==METHOD and index in INDICES and level in SCENES and timeout==90
    c=shared_config(method,index,timeout,level)
    c['j0']=True
    return c
