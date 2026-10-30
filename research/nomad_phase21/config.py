"""Registered common stack, two fixed scenes and compact method dispatch."""
import copy,json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20b.config import place as old_place
HERE=ROOT/'research/nomad_phase21'
METHODS=('B0_NOMAD_RAW','B1_SAFE_TE','B2_SAFE_RTC','B3_M1','B4_ASTAR','M3_GRAPH')
PRIMARY=METHODS[1:]
SCENES=('L2','L2A')
def protocol():return json.loads((HERE/'protocol.json').read_text())
def verify_sources():
    p=protocol()
    for f,h in p['protected_sha256'].items():assert sha256_file(ROOT/f)==h,f
    for f,h in p['reused_sha256'].items():assert sha256_file(f)==h,f
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    return p
def runtime_config(method,index,timeout=90,level='L2'):
    p=protocol();assert method in METHODS and level in SCENES and index in [95,*range(111,116)] and timeout==90
    c=json.loads((ROOT/p['SO']['source_scenario']).read_text())
    c.update(phase21=True,phase21_method=method,phase20=True,phase20b=True,phase20d=True,phase20f=True,phase20_method='M3_DETOUR' if method in ('B4_ASTAR','M3_GRAPH') else 'M1_ROTATE',
        blockage_level=level,phase16_scene=level,phase15b_method=method if method!='B0_NOMAD_RAW' else None,depth_camera=method!='B0_NOMAD_RAW',overnight_phase=9,
        overnight_method='RTC-hard' if method=='B2_SAFE_RTC' else 'CURV',phase4c_method='CURV',plant_alpha='inf',execution_v_max_m_s=.3,
        seed_offset=index*10000,run_id=f'{level}_{index}',goal_mode='topomap',topomap_manifest=p['SO']['topomap'],topomap_manifest_sha256=p['SO']['topomap_sha256'],timeout_sim_s=90,synchronous=False,phase2_distance_m=1.,
        blockage_center_y_m=0. if level=='L2' else (p['scenes']['L2A']['offset_m'] if index%2 else -p['scenes']['L2A']['offset_m']),oracle_publication=False)
    c['dynamic_obstacle']={'id':'DynamicObstacle','size_xyz_m':[.4,1.2,.8],'color_rgb':[.65,.04,.65],'minimum_visible_pixels':20,'spawn_tick':0,'placement':{'mode':'phase2_world_x','distance_m':1.}}
    return c
def place(c,pose):return old_place(c,pose)
def triggered(c,pose):
    lo=2. if c['blockage_level']=='L2' else 3.;return lo<=pose[0]<=lo+.1
