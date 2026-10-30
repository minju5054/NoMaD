"""Held-out geometry-only spawn depth renderer. No worker, controller or inference."""
import argparse,ast,sys,types
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--index',type=int,required=True);args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
# Bootstrap the exact21 renderer definitions, without its navigation try block.
source=Path(__file__).with_name('simulator.py');sys.argv=[str(source),'--level','L2A','--method','B3_M1','--index',str(args.index),'--delay','0','--socket','/tmp/unused-geometry.sock','--output',str(out),'--portable-root',str(out/'portable')]
tree=ast.parse(source.read_text());prefix=[]
for node in tree.body:
    if isinstance(node,ast.Try):break
    prefix.append(node)
ns=dict(__name__='phase21_geometry_renderer',__file__=str(source));exec(compile(ast.Module(body=prefix,type_ignores=[]),str(source),'exec'),ns)
# SimulationApp now initialized. Numerical imports are safe here.
import json,numpy as np
from nomad_phase21.config import runtime_config,place,protocol
from nomad_phase15.depth_sdf import backproject,camera_to_world,intrinsics
from nomad_isaac.common import write_json
from PIL import Image
try:
    c=runtime_config('B3_M1',args.index,90,'L2A');pose=np.array([3.,0.,0.]);box=place(c,pose)['obstacle'];box['spawn_tick']=0
    set_pose,get_pose,capture=ns['render_functions'](c);set_pose(pose);capture.sync_dynamic(dict(resolved_dynamic_obstacle=box,tick=0,sim_s=0.));capture(0.)
    depth=capture.depth_frame.copy();np.savez_compressed(out/'spawn_depth.npz',depth=depth,camera_to_world=camera_to_world(pose,c['camera']['height_m']))
    scaled=np.clip(np.nan_to_num(depth,nan=0,posinf=0)/5,0,1);Image.fromarray((scaled*255).astype(np.uint8)).save(out/'spawn_depth.png')
    center=np.array(box['center_xy_m']);half=np.array(box['size_xyz_m'][:2])/2;front=center[0]-half[0]
    low,high=-c['corridor']['half_width'],c['corridor']['half_width'];left_gap=high-(center[1]+half[1]);right_gap=center[1]-half[1]-low
    interval=(center[1]+half[1],high) if left_gap>right_gap else (low,center[1]-half[1]);mid=(interval[0]+interval[1])/2
    angle=float(np.degrees(np.arctan2(mid-pose[1],front-pose[0])));fov=abs(angle)<45
    points,ranges,_=backproject(depth,intrinsics(c['camera']),camera_to_world(pose,c['camera']['height_m']),False,None)
    # Measured rays must traverse the gap at the front plane and continue beyond it.
    delta=points-pose[:3];dx=points[:,0]-pose[0];cross_y=pose[1]+(front-pose[0])*(points[:,1]-pose[1])/np.maximum(dx,1e-12)
    visible=(dx>front-pose[0]+.05)&(cross_y>interval[0]+.09)&(cross_y<interval[1]-.09)&np.isfinite(points).all(axis=1)
    placement=place(c,pose);passed=placement['status']=='PLACED' and min(left_gap,right_gap)>0 and fov and bool(visible.any())
    result=dict(passed=passed,scope='geometry/depth only; no method, inference, trajectory or navigation',index=args.index,spawn_pose=pose.tolist(),box=box,wide_gap_interval=interval,wide_gap_center_angle_deg=angle,
        inside_fov=fov,measured_gap_rays=int(visible.sum()),left_gap_m=left_gap,right_gap_m=right_gap,placement=placement,offset_m=protocol()['scenes']['L2A']['offset_m'])
    write_json(out/'geometry.json',result);print(json.dumps(result))
finally:ns['base'].app.close()
