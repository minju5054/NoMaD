"""L2/SLW pilot scene reuse; solver parameters stay in the frozen offline protocol."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase21.config import runtime_config as phase21_config
HERE=Path(__file__).parent
METHODS=('G','C0','C1');SCENES=('L2','SLW')
def protocol():return json.loads((HERE/'online_protocol.json').read_text())
def runtime_config(method,index,timeout=90,level='L2'):
    p=protocol();assert method in METHODS and level in SCENES and timeout==90
    assert index in [95,*p['indices']]
    alias={'C0':'M3_GRAPH','C1':'B4_ASTAR','G':'M3_GRAPH'}[method]
    c=phase21_config(alias,95,90,level='L2')
    if level=='SLW':
        geometry=json.loads((ROOT/p['scenes']['SLW']['scenario']).read_text());c.update(geometry)
        for key in ('dynamic_obstacle','experiment_mode','phase2_distance_m','blockage_center_y_m'):c.pop(key,None)
    c.update(phase24=True,phase24_method=method,phase21_method=alias,phase15b_method=method,
        phase16_scene=level,blockage_level=level,seed_offset=index*10000,run_id=f'{level}_{index}',
        topomap_manifest=p['scenes'][level]['topomap'],topomap_manifest_sha256=p['scenes'][level]['topomap_sha256'],
        overnight_phase=9,overnight_method='CURV',phase4c_method='CURV',plant_alpha='inf',execution_v_max_m_s=.3,
        depth_camera=True,timeout_sim_s=90,goal_mode='topomap',synchronous=False,oracle_publication=False)
    return c

def verify():
    p=protocol();offline=json.loads((HERE/'protocol.json').read_text());gate=json.loads((ROOT/'research/results/phase24_offline/gate.json').read_text())
    assert gate['label']=='GO_ONLINE' and offline['status']=='FROZEN'
    assert sha256_file(HERE/'protocol.json')==p['offline_protocol_sha256']
    for name,h in offline['frozen_sources'].items():assert sha256_file(ROOT/name)==h,name
    for info in p['scenes'].values():
        assert sha256_file(ROOT/info['scenario'])==info['scenario_sha256'];assert sha256_file(info['topomap'])==info['topomap_sha256']
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    from .storage import operational_hash,verify_storage_sources
    for name,h in p.get('source_sha256',{}).items():assert sha256_file(ROOT/name)==operational_hash(name,h),name
    verify_storage_sources()
    return p
