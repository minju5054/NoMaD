"""Frozen Phase 2 options, axis-aligned appearance, and public geometry."""
import copy
import json
from pathlib import Path
import re
import numpy as np
from nomad_isaac.common import ROOT, sha256_file
from nomad_isaac.clearance import configured_obstacles, point_clearance, segment_clearance

HERE = Path(__file__).parent
MODE = 'phase2_s1_v2'

def protocol():
    return json.loads((HERE/'protocol.json').read_text())

def validate_options(args):
    p = protocol()
    assert args.phase2_method in ('M0','M3','M5')
    assert args.asynchronous and args.pure_pursuit and args.topomap
    assert not any((args.prepare_only,args.s1_mode,args.s1_v2_mode,args.oracle_safety_stop,
                    args.early_obstacle_mode,args.controlled_delivery_delay,args.render_topomap_reference))
    assert args.s1_distance_m is None
    assert args.phase2_distance_m in (None,.6,.8,1.)
    assert args.uniform_delivery_delay_s in (.25,.5,.75)
    assert sha256_file(args.scenario) == p['scenario_sha256']
    assert sha256_file(args.topomap) == p['topomap_sha256']
    assert re.fullmatch(r'P2_(PILOT|BASE|MAIN|HARD)_\d{2}',args.run_id or '')
    i = int(args.run_id[-2:])
    expected = 0 if '_PILOT_' in args.run_id else i*10000
    assert args.seed_offset == expected

def runtime_config(config,args):
    validate_options(args)
    c = copy.deepcopy(config)
    c.update(phase2_method=args.phase2_method, phase2_distance_m=args.phase2_distance_m)
    if args.phase2_distance_m is not None:
        c['dynamic_obstacle'] = {'id':'DynamicObstacle','size_xyz_m':[.35,.35,.8],
            'color_rgb':[.65,.04,.65],'minimum_visible_pixels':20,'spawn_tick':0,
            'placement':{'mode':'phase2_world_x','distance_m':args.phase2_distance_m}}
    return c

def triggered(config,pose):
    return 2.0 <= pose[0] <= 2.1

def place(config,pose):
    p=np.asarray(pose); d=config['phase2_distance_m']; r=config['agent_radius_m']
    center=np.array([p[0]+r+d+.175,np.clip(p[1],-.925,.925)])
    box=copy.deepcopy(config['dynamic_obstacle']); box['center_xy_m']=center.tolist()
    lo,hi=center-.175,center+.175; c=config['corridor']
    gap=point_clearance(p[:2],lo,hi,r)
    wall=float(min(lo[0]-c['xmin'],c['xmax']-hi[0],lo[1]+c['half_width'],c['half_width']-hi[1]))
    conflicts=[]
    for b in configured_obstacles(config):
        bc=np.array(b['center_xy_m']); half=np.array(b['size_xyz_m'][:2])/2
        if np.all(hi>=bc-half) and np.all(bc+half>=lo): conflicts.append(b['id'])
    reasons=(['static_overlap'] if conflicts else [])+(['outside_corridor'] if wall<0 else [])+(['spawn_overlap'] if gap<=0 else [])
    return {'status':'PLACEMENT_INVALID' if reasons else 'PLACED','reasons':reasons,
        'obstacle':box,'spawn_pose':p.tolist(),'configured_d_m':d,
        'measured_world_forward_surface_d_m':float(lo[0]-p[0]-r),
        'y_clipped':bool(center[1]!=p[1]),'y_clip_delta_m':float(center[1]-p[1]),
        'footprint_euclidean_clearance_m':gap,'box_corridor_clearance_m':wall,
        'left_wall_gap_m':float(c['half_width']-hi[1]),'right_wall_gap_m':float(lo[1]+c['half_width']),
        'placement_inputs':'actual pose and fixed geometry only; +world X distance, not heading ray'}

def native_safety(xy,config):
    """Existing segment evaluator, with explicit empty-obstacle-set handling."""
    xy=np.asarray(xy); c=config['corridor']; radius=config['agent_radius_m']
    gaps={}
    for b in configured_obstacles(config):
        center=np.array(b['center_xy_m']); half=np.array(b['size_xyz_m'][:2])/2
        gaps[b['id']]=min(segment_clearance(a,z,center-half,center+half,radius)[0] for a,z in zip(xy[:-1],xy[1:]))
    wall=float(min(np.min(xy[:,0]-c['xmin']),np.min(c['xmax']-xy[:,0]),np.min(c['half_width']-abs(xy[:,1])))-radius)
    return {'obstacles':gaps,'minimum_clearance_m':min(gaps.values()) if gaps else None,
            'corridor_clearance_m':wall,'safe':bool(all(v>=.02 for v in gaps.values()) and wall>0)}

def select(samples,boundary,config):
    scores=[]; safety=[]
    forward=np.array([np.cos(boundary[2]),np.sin(boundary[2])])
    for xy in samples:
        safety.append(native_safety(xy,config))
        scores.append(float((max(0.,.25-(np.array(xy)[-1]-np.array(boundary)[:2])@forward)/.25)**2))
    safe=[i for i,s in enumerate(safety) if s['safe']]
    chosen=0 if safety[0]['safe'] or not safe else min(safe,key=lambda i:(scores[i],i))
    return {'sample0_unsafe':not safety[0]['safe'],'selected_sample':chosen,'all_unsafe':not safe,
            'sample_safety':safety,'selection_scores':scores}
