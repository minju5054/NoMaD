"""Frozen blockage geometry; no oracle geometry enters either controller."""
import copy,json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.clearance import point_clearance,configured_obstacles

HERE=ROOT/'research/nomad_phase20f';METHODS=('M1_ROTATE','M3_DETOUR');LEVELS=('L2',)
def protocol():return json.loads((HERE/'protocol.json').read_text())

def verify_sources():
    p=protocol()
    for f,h in p['protected_sha256'].items():assert sha256_file(ROOT/f)==h,f
    for f,h in p['reused_sha256'].items():assert sha256_file(f)==h,f
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    from nomad_isaac.topomap import load_map
    images,_=load_map(p['SO']['topomap']);assert len(images)==21
    return p

def runtime_config(method,index,timeout=90,level='L2'):
    assert level in LEVELS and method in METHODS and index in (95,96,97,98,99,100,901)
    assert timeout in (60,90)
    p=protocol();c=json.loads((ROOT/p['SO']['source_scenario']).read_text());spec=p['levels'][level]
    c.update(phase20=True,phase20b=True,phase20d=True,phase20f=True,phase20_method=method,blockage_level=level,phase16_scene=level,
        phase15b_method=method,depth_camera=True,overnight_phase=9,overnight_method='CURV',phase4c_method='CURV',plant_alpha='inf',execution_v_max_m_s=.3,
        seed_offset=index*10000,run_id=f'{level}_{index}',goal_mode='topomap',topomap_manifest=p['SO']['topomap'],
        topomap_manifest_sha256=p['SO']['topomap_sha256'],timeout_sim_s=timeout,synchronous=False,phase2_distance_m=1.,
        blockage_center_y_m=0. if level=='L2' else (.3 if index%2==0 else -.3),oracle_publication=False)
    c['dynamic_obstacle']={'id':'DynamicObstacle','size_xyz_m':spec['size_xyz_m'],'color_rgb':[.65,.04,.65],
        'minimum_visible_pixels':20,'spawn_tick':0,'placement':{'mode':'phase2_world_x','distance_m':1.}}
    return c

from nomad_phase20b.config import place
