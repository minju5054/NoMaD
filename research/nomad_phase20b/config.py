"""Frozen blockage geometry; no oracle geometry enters either controller."""
import copy,json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.clearance import point_clearance,configured_obstacles

HERE=ROOT/'research/nomad_phase20b';METHODS=('M1_ROTATE','M2_REPAIR');LEVELS=('L2','L3')
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
    assert level in LEVELS and method in METHODS and index in (80,81,82,901,902)
    assert timeout in (30,40,90)
    p=protocol();c=json.loads((ROOT/p['SO']['source_scenario']).read_text());spec=p['levels'][level]
    c.update(phase20=True,phase20b=True,phase20_method=method,blockage_level=level,phase16_scene=level,
        phase15b_method=method,depth_camera=True,overnight_phase=9,overnight_method='CURV',phase4c_method='CURV',plant_alpha='inf',execution_v_max_m_s=.3,
        seed_offset=index*10000,run_id=f'{level}_{index}',goal_mode='topomap',topomap_manifest=p['SO']['topomap'],
        topomap_manifest_sha256=p['SO']['topomap_sha256'],timeout_sim_s=timeout,synchronous=False,phase2_distance_m=1.,
        blockage_center_y_m=0. if level=='L2' else (.3 if index%2==0 else -.3),oracle_publication=False)
    c['dynamic_obstacle']={'id':'DynamicObstacle','size_xyz_m':spec['size_xyz_m'],'color_rgb':[.65,.04,.65],
        'minimum_visible_pixels':20,'spawn_tick':0,'placement':{'mode':'phase2_world_x','distance_m':1.}}
    return c

def place(config,pose):
    p=np.asarray(pose);box=copy.deepcopy(config['dynamic_obstacle']);hx,hy=np.array(box['size_xyz_m'][:2])/2
    center=np.array([p[0]+config['agent_radius_m']+1.+hx,config['blockage_center_y_m']]);box['center_xy_m']=center.tolist()
    lo,hi=center-[hx,hy],center+[hx,hy];c=config['corridor'];r=config['agent_radius_m']
    gap=point_clearance(p[:2],lo,hi,r);wall=float(min(lo[0]-c['xmin'],c['xmax']-hi[0],lo[1]+c['half_width'],c['half_width']-hi[1]))
    conflicts=[]
    for b in configured_obstacles(config):
        bc=np.array(b['center_xy_m']);half=np.array(b['size_xyz_m'][:2])/2
        if np.all(hi>=bc-half) and np.all(bc+half>=lo):conflicts.append(b['id'])
    reasons=(['static_overlap'] if conflicts else [])+(['outside_corridor'] if wall<0 else [])+(['spawn_overlap'] if gap<=0 else [])
    return dict(status='PLACEMENT_INVALID' if reasons else 'PLACED',reasons=reasons,obstacle=box,spawn_pose=p.tolist(),configured_d_m=1.,
        measured_world_forward_surface_d_m=float(lo[0]-p[0]-r),y_clipped=False,y_clip_delta_m=0.,intended_y_offset_m=config['blockage_center_y_m'],
        footprint_euclidean_clearance_m=gap,box_corridor_clearance_m=wall,left_wall_gap_m=float(c['half_width']-hi[1]),right_wall_gap_m=float(lo[1]+c['half_width']),
        placement_inputs='actual x and frozen geometry only; center y fixed in corridor frame to preserve specified gaps',blockage_level=config['blockage_level'])
