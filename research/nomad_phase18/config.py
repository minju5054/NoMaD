import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.config import runtime_config as original_runtime

HERE=ROOT/'research/nomad_phase18'
SCENES=('SLW','LC','CL')
METHODS=('FRESHEST-SAFE','FRESHEST-SAFE+HERMITE','FRESHEST-SAFE+TEMPORAL-ENSEMBLE',
         'FRESHEST-SAFE+RTC-hard','FRESHEST-SAFE+GRAPH-depth','FRESHEST-SAFE+GRAPH-depth-CLR')
RTC=METHODS[3];PROPOSED=METHODS[5]
def protocol():return json.loads((HERE/'protocol.json').read_text())
def scene(name):return json.loads((ROOT/protocol()['scenes'][name]).read_text())
def verify_sources():
    p=protocol()
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h,name
    for name,h in p['reused_sha256'].items():assert sha256_file(name)==h,name
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    from nomad_isaac.topomap import load_map
    for sc,info in p['topomaps'].items():
        images,_=load_map(info['manifest']);assert len(images)==info['node_count']
    gates=[json.loads(Path(file).read_text()) for file in p['gate_metric_files']]
    assert len(gates)==6 and all(g['success'] and g['technical_validation']=='PASS' for g in gates)
    return p
def runtime_config(c,method,index,manifest,timeout=90):
    assert method in METHODS
    c=original_runtime(c,METHODS[0] if method==RTC else method,index,manifest,timeout)
    c.update(phase18=True,phase15b_method=method)
    if method==RTC:c['overnight_method']='RTC-hard'
    return c
