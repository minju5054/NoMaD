import json
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase16.config import runtime_config as base_runtime
HERE=ROOT/'research/nomad_phase17'
METHODS=('FRESHEST-SAFE','FRESHEST-SAFE+HERMITE','FRESHEST-SAFE+TEMPORAL-ENSEMBLE',
         'FRESHEST-SAFE+GRAPH-GF','FRESHEST-SAFE+GRAPH-depth','FRESHEST-SAFE+GRAPH-depth-CLR','TEMPORAL-ENSEMBLE')
SAFE=METHODS[:6]
def protocol():return json.loads((HERE/'protocol.json').read_text())
def scene(name):return json.loads((ROOT/protocol()['scenes'][name]).read_text())
def verify_sources():
    p=protocol()
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h,name
    for name,h in p['scene_sha256'].items():assert sha256_file(ROOT/p['scenes'][name])==h,name
    for name,h in p['reference_sha256'].items():assert sha256_file(ROOT/name)==h,name
    for info in p['topomap_reuse'].values():assert sha256_file(info['manifest'])==info['sha256']
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    return p
def runtime_config(c,method,index,manifest,timeout=90):
    assert method in METHODS
    c=base_runtime(c,method,index,manifest,timeout);c['phase17']=True
    return c
