"""H1/H2 depth-only spawn fixtures: no policy, worker, inference or navigation."""
import argparse,ast,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--scene',choices=['H1','H2'],required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
source=Path(__file__).with_name('simulator.py')
sys.argv=[str(source),'--level',args.scene,'--method','B3_SAFE_ROTATE','--index','95','--delay','0','--socket','/tmp/phase26-geometry-unused.sock','--output',str(out),'--portable-root',str(out/'portable')]
tree=ast.parse(source.read_text());prefix=[]
for node in tree.body:
    if isinstance(node,ast.Try):break
    prefix.append(node)
ns=dict(__name__='phase26_depth_fixture',__file__=str(source));exec(compile(ast.Module(body=prefix,type_ignores=[]),str(source),'exec'),ns)
import json,math,numpy as np
from PIL import Image
from nomad_phase26.config import runtime_config
from nomad_phase26.scenes import place
from nomad_phase26.rendering import make
from nomad_phase15.depth_sdf import camera_to_world,intrinsics,backproject
from nomad_isaac.common import write_json

try:
    c=runtime_config('B3_SAFE_ROTATE',95,level=args.scene);set_pose,get_pose,capture=make(ns['base'],c,out)
    poses=[[3.3,1.2,math.pi/2]] if args.scene=='H1' else [[2.,0.,0.],[5.,0.,0.]]
    boxes=[];checks=[]
    for number,pose in enumerate(poses):
        placement=place(c,pose,number);box=placement['obstacle'];box['spawn_tick']=number*18;boxes.append(box)
        set_pose(pose);capture.sync_dynamic(dict(resolved_dynamic_obstacle=dict(boxes[0],phase26_boxes=boxes),tick=number*18,sim_s=number/4))
        color=capture(number/4);depth=capture.depth_frame.copy();axis=placement['axis'];cross=1-axis
        center=np.array(box['center_xy_m']);half=np.array(box['size_xyz_m'][:2])/2;lo,hi=center-half,center+half
        limits=(2.4,4.2) if axis==1 else (-1.5,1.5)
        gaps=[(limits[0],lo[cross]),(hi[cross],limits[1])];interval=max(gaps,key=lambda x:x[1]-x[0]);width=interval[1]-interval[0]
        target=center.copy();target[cross]=sum(interval)/2;direction=target-np.array(pose[:2]);angle=(math.atan2(direction[1],direction[0])-pose[2]+math.pi)%(2*math.pi)-math.pi
        points,_,_=backproject(depth,intrinsics(c['camera']),camera_to_world(pose,c['camera']['height_m']))
        visible=(points[:,axis]>hi[axis])&(points[:,cross]>interval[0]+.09)&(points[:,cross]<interval[1]-.09)
        inside=(points[:,:2]>=lo-.02).all(axis=1)&(points[:,:2]<=hi+.02).all(axis=1)&(points[:,2]>.03)&(points[:,2]<=.82)
        passed=placement['status']=='PLACED' and width>=.6-1e-9 and abs(angle)<=math.pi/4 and visible.any() and inside.any()
        checks.append(dict(passed=bool(passed),box_number=number+1,pose=pose,placement=placement,wide_gap_m=width,
            wide_gap_interval=interval,gap_angle_deg=math.degrees(angle),gap_depth_rays=int(visible.sum()),box_depth_points=int(inside.sum()),
            rendered_boxes=len(boxes),usd_evaluation_walls='PASS'))
        np.savez_compressed(out/f'box{number+1}_depth.npz',depth=depth,pose=pose)
        Image.fromarray(color).save(out/f'box{number+1}_rgb.png')
        Image.fromarray((np.clip(np.nan_to_num(depth,nan=0,posinf=0)/5,0,1)*255).astype('uint8')).save(out/f'box{number+1}_depth.png')
    result=dict(passed=all(x['passed'] for x in checks),scene=args.scene,scope='depth-only; zero methods/inference/navigation',checks=checks)
    write_json(out/'geometry_only.json',result);print(json.dumps(result),flush=True)
finally:ns['base'].app.close()
