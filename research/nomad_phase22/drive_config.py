"""Phase22 drive-only registration; offline protocol/weights remain untouched."""
import copy,json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20b.config import place as original_place
from .drive_geometry import bounds,point_gap,ray_distance,corners
HERE=ROOT/'research/nomad_phase22';METHODS=('P0_ASTAR','P1_GRAPH','P2F_ASTAR_GRAPH');SCENES=('L2','L2B')
def protocol():return json.loads((HERE/'drive_protocol.json').read_text())
def verify_sources():
    p=protocol()
    for f,h in p['protected_sha256'].items():assert sha256_file(ROOT/f)==h,f
    for f,h in p['reused_sha256'].items():assert sha256_file(f)==h,f
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    from nomad_isaac.topomap import load_map
    images,_=load_map(p['SO']['topomap']);assert len(images)==21;return p

def runtime_config(method,index,timeout=90,level='L2'):
    p=protocol();assert method in METHODS and level in SCENES and index in (95,121,122,123,124) and timeout==90
    c=json.loads((ROOT/p['SO']['source_scenario']).read_text());s=p['scenes'][level]
    c.update(phase22_drive=True,phase21=True,phase21_method='B4_ASTAR' if method!='P1_GRAPH' else 'M3_GRAPH',phase22_method=method,
        phase20=True,phase20b=True,phase20d=True,phase20f=True,phase20_method='M3_DETOUR',blockage_level=level,phase16_scene=level,phase15b_method=method,depth_camera=True,
        overnight_phase=9,overnight_method='CURV',phase4c_method='CURV',plant_alpha='inf',execution_v_max_m_s=.3,seed_offset=10000*index,run_id=f'{level}_{index}',goal_mode='topomap',
        topomap_manifest=p['SO']['topomap'],topomap_manifest_sha256=p['SO']['topomap_sha256'],timeout_sim_s=90,synchronous=False,phase2_distance_m=s['d_m'],
        blockage_center_y_m=0 if level=='L2' else s['offset_m']*(1 if index%2 else -1),oracle_publication=False)
    c['dynamic_obstacle']=dict(id='DynamicObstacle',size_xyz_m=s['size_xyz_m'],color_rgb=[.65,.04,.65],minimum_visible_pixels=20,spawn_tick=0,
        yaw_deg=0. if level=='L2' else (20. if index%2 else -20.),placement=dict(mode='phase2_world_x',distance_m=s['d_m']))
    return c

def place(c,pose):
    if c['blockage_level']=='L2':return original_place(c,pose)
    b=copy.deepcopy(c['dynamic_obstacle']);b['center_xy_m']=[0.,0.];lo,hi=bounds(b);extent=hi[0]
    b['center_xy_m']=[float(pose[0]+c['agent_radius_m']+c['phase2_distance_m']+extent),float(c['blockage_center_y_m'])]
    lo,hi=bounds(b);half=c['corridor']['half_width'];gap=point_gap(np.asarray(pose)[:2],b,c['agent_radius_m']);wall=min(lo[0]-c['corridor']['xmin'],c['corridor']['xmax']-hi[0],lo[1]+half,half-hi[1]);reasons=[]
    if wall<0:reasons.append('outside_corridor')
    if gap<=0:reasons.append('spawn_overlap')
    return dict(status='PLACEMENT_INVALID' if reasons else 'PLACED',reasons=reasons,obstacle=b,spawn_pose=list(pose),configured_d_m=c['phase2_distance_m'],measured_world_forward_surface_d_m=float(lo[0]-pose[0]-c['agent_radius_m']),
        forward_ray_surface_d_m=ray_distance(pose,b,c['agent_radius_m']),left_wall_gap_m=float(half-hi[1]),right_wall_gap_m=float(lo[1]+half),box_corridor_clearance_m=float(wall),footprint_euclidean_clearance_m=float(gap),world_corners=corners(b).tolist(),
        placement_inputs='Current x and frozen world-frame y/yaw only. Distance preserves Phase21 world-X front-support convention; ray distance separately recorded.',blockage_level='L2B')
def triggered(c,pose):
    lo=2. if c['blockage_level']=='L2' else 2.5;return lo<=pose[0]<=lo+.1
