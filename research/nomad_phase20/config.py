import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file

HERE=ROOT/'research/nomad_phase20'
METHODS=('M1_ROTATE','M2_REPAIR')


def protocol():return json.loads((HERE/'protocol.json').read_text())
def verify_sources():
    p=protocol()
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h,name
    assert sha256_file(ROOT/p['SO']['source_scenario'])==p['SO']['source_scenario_sha256']
    assert sha256_file(p['SO']['topomap'])==p['SO']['topomap_sha256']
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    ready=json.loads((ROOT/'research/results/phase20_preflight_02/readiness.json').read_text());assert ready['label']=='READY'
    from nomad_isaac.topomap import load_map
    images,_=load_map(p['SO']['topomap']);assert len(images)==21
    return p


def runtime_config(method,index,timeout=90):
    assert method in METHODS and (74<=index<=79 or index==901)
    assert timeout in (30,90)
    p=protocol();c=json.loads((ROOT/p['SO']['source_scenario']).read_text())
    c.update(phase20=True,phase20_method=method,phase16_scene='SO',phase15b_method=method,depth_camera=True,
        overnight_phase=9,overnight_method='CURV',phase4c_method='CURV',plant_alpha='inf',execution_v_max_m_s=.3,
        seed_offset=index*10000,run_id=f'SO_{index}',goal_mode='topomap',topomap_manifest=p['SO']['topomap'],
        topomap_manifest_sha256=p['SO']['topomap_sha256'],timeout_sim_s=timeout,synchronous=False,
        phase2_distance_m=1.2,diagnostic_y_offset_m=.15 if index%2 else -.15,oracle_publication=False)
    c['dynamic_obstacle']={'id':'DynamicObstacle','size_xyz_m':[.35,.35,.8],'color_rgb':[.65,.04,.65],
        'minimum_visible_pixels':20,'spawn_tick':0,'placement':{'mode':'phase2_world_x','distance_m':1.2}}
    return c
