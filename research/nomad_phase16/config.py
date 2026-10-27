import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
HERE=ROOT/'research/nomad_phase16'
METHODS=('FRESHEST-SAFE','FRESHEST-SAFE+HERMITE','FRESHEST-SAFE+TEMPORAL-ENSEMBLE','FRESHEST-SAFE+GRAPH-GF','FRESHEST-SAFE+GRAPH-depth','TEMPORAL-ENSEMBLE')
SAFE=METHODS[:5]
def protocol():return json.loads((HERE/'protocol.json').read_text())
def verify_sources():
    p=protocol()
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h,name
    for scene,h in p['scene_sha256'].items():assert sha256_file(ROOT/p['scenes'][scene])==h,scene
    for name,h in p.get('reference_sha256',{}).items():assert sha256_file(ROOT/name)==h,name
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    return p
def scene(name):return json.loads((ROOT/protocol()['scenes'][name]).read_text())
def runtime_config(c,method,index,manifest,timeout=90):
    c=json.loads(json.dumps(c));c.update(phase16=True,phase15b_method=method,depth_camera=True,overnight_phase=8,overnight_method='CURV',
        phase4c_method='GRAPH' if 'GRAPH' in method else 'CURV',plant_alpha='inf',execution_v_max_m_s=.3,
        seed_offset=index*10000,run_id=f"{c['phase16_scene']}_{index}",goal_mode='topomap',topomap_manifest=str(Path(manifest).resolve()),
        topomap_manifest_sha256=sha256_file(manifest),timeout_sim_s=timeout,synchronous=False)
    return c
