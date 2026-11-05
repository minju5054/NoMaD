"""Frozen methods plus scene/allocation metadata. Standard-library only."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase21.config import runtime_config as phase21

HERE=Path(__file__).parent
METHODS=('B0_NOMAD_RAW','B1_SAFE_TE','B2_SAFE_RTC','B3_SAFE_ROTATE','B4_ASTAR','C0')
PRIMARY=METHODS[1:]
SCENES=('SLW','LC','L2','H1','H2')
ALIASES=dict(zip(METHODS,('B0_NOMAD_RAW','B1_SAFE_TE','B2_SAFE_RTC','B3_M1','B4_ASTAR','M3_GRAPH')))

def protocol():return json.loads((HERE/'protocol.json').read_text())

def runtime_config(method,index,timeout=90,level='L2'):
    p=protocol();assert method in METHODS and level in SCENES and index in (95,201,202)
    assert timeout==90
    c=phase21(ALIASES[method],95,90,'L2')
    if level in ('SLW','LC','H1'):
        c.update(json.loads((ROOT/p['scenes'][level]['scenario']).read_text()))
        for k in ('dynamic_obstacle','experiment_mode','phase2_distance_m','blockage_center_y_m'):c.pop(k,None)
    if level=='H1':
        c.update(experiment_mode='phase2_s1_v2',phase26_dynamic=True)
        c['dynamic_obstacle']=dict(id='DynamicObstacle',size_xyz_m=[1.,.4,.8],color_rgb=[.65,.04,.65],minimum_visible_pixels=20,spawn_tick=0,placement={'mode':'phase26_h1'})
    elif level=='H2':
        c['dynamic_obstacle']['size_xyz_m']=[.4,1.,.8];c['phase26_dynamic']=True
    c.update(phase26=True,phase26_method=method,phase24=True,phase24_method=method,phase24r=True,phase24r_method=method,
        phase16_scene=level,blockage_level=level,seed_offset=index*10000,run_id=f'{level}_{index}',
        topomap_manifest=p['scenes'][level]['topomap'],topomap_manifest_sha256=p['scenes'][level]['topomap_sha256'],
        phase21_method=ALIASES[method],phase15b_method=None if method=='B0_NOMAD_RAW' else method,
        overnight_method='RTC-hard' if method=='B2_SAFE_RTC' else 'CURV',overnight_phase=9,
        depth_camera=method!='B0_NOMAD_RAW',timeout_sim_s=90,synchronous=False,oracle_publication=False,
        phase4c_method='CURV',execution_v_max_m_s=.3,plant_alpha='inf')
    if level in ('H1','H2'):c['phase26_spawn']=p['scenes'][level]['spawn']
    return c

def verify():
    p=protocol()
    for f,h in {**p['frozen_sources'],**p.get('source_sha256',{})}.items():assert sha256_file(ROOT/f)==h,f
    for s in p['scenes'].values():
        assert sha256_file(ROOT/s['scenario'])==s['scenario_sha256']
        assert sha256_file(s['topomap'])==s['topomap_sha256']
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    return p
