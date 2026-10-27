"""Dedicated Phase16 entry point; reuses protected Isaac camera and async core."""
import argparse,ast,csv,hashlib,json,sys,time,traceback,types
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--scene',required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--mode',required=True)
ap.add_argument('--topomap',type=Path);ap.add_argument('--method');ap.add_argument('--index',type=int);ap.add_argument('--delay',type=float);ap.add_argument('--socket');ap.add_argument('--timeout',type=float,default=90)
a,extra=ap.parse_known_args();out=a.output.resolve()
# The protected simulator is a script with an unconditional main at its end.
# Execute only its unchanged initialization + build_scene prefix via AST;
# never execute its old scenario validation/main/finally. Source hash is frozen.
sys.argv=[sys.argv[0],'--output',str(out),'--phase15b-method','FRESHEST-SAFE','--depth-camera',*extra]
original=Path(__file__).parents[1]/'nomad_isaac/simulator.py'
tree=ast.parse(original.read_text());prefix=[]
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name=='main':break
    prefix.append(node)
assert any(isinstance(n,ast.FunctionDef) and n.name=='build_scene' for n in prefix)
base=types.ModuleType('nomad_phase16._renderer_base');base.__file__=str(original)
exec(compile(ast.Module(body=prefix,type_ignores=[]),str(original),'exec'),base.__dict__)
import numpy as np
from PIL import Image
from nomad_isaac.common import ROOT,write_json,sha256_file
from nomad_phase16.config import scene,protocol,runtime_config
from nomad_phase16.geometry import rect,reference_rollout,point_box_distance

def set_box(stage,name,position,size):
    prim=stage.GetPrimAtPath('/World/'+name)
    if not prim.IsValid():
        prim=base.UsdGeom.Cube.Define(stage,'/World/'+name).GetPrim();prim.GetAttribute('size').Set(1.)
        base.UsdGeom.Xformable(prim).AddTranslateOp();base.UsdGeom.Xformable(prim).AddScaleOp()
        base.UsdGeom.Gprim(prim).CreateDisplayColorAttr().Set([base.Gf.Vec3f(.76,.77,.79)])
    prim.GetAttribute('xformOp:translate').Set(base.Gf.Vec3d(*position))
    attr=prim.GetAttribute('xformOp:scale');attr.Set(base.Gf.Vec3f(*size))

def build(c):
    stage,agent,translate,rotate,camera,rgb,product=base.build_scene(c)
    xmin,xmax,ymin,ymax=rect(c);cx=(xmin+xmax)/2;cy=(ymin+ymax)/2;length=xmax-xmin;width=ymax-ymin
    set_box(stage,'Floor',(cx,cy,-.05),(length,width,.1))
    set_box(stage,'LeftWall',(cx,ymax+.05,1.3),(length,.1,2.6));set_box(stage,'RightWall',(cx,ymin-.05,1.3),(length,.1,2.6))
    set_box(stage,'EndWall',(xmax+.05,cy,1.3),(.1,width+.2,2.6));set_box(stage,'StartWall',(xmin-.05,cy,1.3),(.1,width+.2,2.6))
    set_box(stage,'EndDoor',(xmax-.002,cy+.15,1.1),(.004,.9,2.2))
    for prim in stage.Traverse():
        if not prim.IsA(base.UsdGeom.Cube):continue
        name=prim.GetName()
        if name.startswith('FloorSeam'):
            x=float(prim.GetAttribute('xformOp:translate').Get()[0]);set_box(stage,name,(x,cy,.001),(.012,width,.002))
            if not xmin<x<xmax:base.UsdGeom.Imageable(prim).MakeInvisible()
        if name.startswith('Panel'):
            x=float(prim.GetAttribute('xformOp:translate').Get()[0]);side=ymax-.002 if name.endswith('_L') else ymin+.002
            set_box(stage,name,(x,side,1.15),(.65,.004,1.7))
            if not xmin+.325<x<xmax-.325:base.UsdGeom.Imageable(prim).MakeInvisible()
    depth=base.rep.AnnotatorRegistry.get_annotator('distance_to_image_plane',device='cpu');depth.attach([product])
    timeline=base.omni.timeline.get_timeline_interface();timeline.pause();base.rep.orchestrator.set_capture_on_play(False)
    def set_pose(p):translate.Set(base.Gf.Vec3d(float(p[0]),float(p[1]),0.));rotate.Set(float(np.degrees(p[2])))
    def get_pose():
        matrix=base.UsdGeom.Xformable(agent).ComputeLocalToWorldTransform(0);v=matrix.ExtractTranslation();forward=matrix.TransformDir(base.Gf.Vec3d(1,0,0));return np.array([v[0],v[1],np.arctan2(forward[1],forward[0])])
    def capture(t):
        timeline.set_current_time(t)
        for _ in range(20):
            base.rep.orchestrator.step(rt_subframes=4,delta_time=0.,pause_timeline=True)
            color=np.asarray(rgb.get_data());d=np.asarray(depth.get_data())
            if color.shape==(240,320,4) and d.shape==(240,320) and np.isfinite(d).any():break
        assert color.shape==(240,320,4) and color.dtype==np.uint8 and color.std()>5
        assert d.shape==(240,320) and np.isfinite(d).any()
        capture.depth_frame=d.copy();return np.ascontiguousarray(color[:,:,:3])
    stage.GetRootLayer().Export(str(out/'scene.usda'))
    return set_pose,get_pose,capture

def inspect(c,set_pose,capture):
    from nomad_phase15.occupancy import make_field
    from nomad_phase15.depth_sdf import intrinsics,camera_to_world,backproject
    from nomad_phase15b.depth import Snapshot
    field=make_field(protocol()['depth_bounds_m'],'V1');set_pose(c['start_pose']);stats=[]
    for i in range(3):
        rgb=capture(i/4);d=capture.depth_frame.copy()
        if i==0:
            Image.fromarray(rgb).save(out/'start_rgb.png');np.savez_compressed(out/'start_depth.npz',depth=d)
            points,ranges,_=backproject(d,intrinsics(c['camera']),camera_to_world(c['start_pose'],c['camera']['height_m']))
            points=points[(points[:,2]>.03)&(points[:,2]<=.6)&(ranges<=3.)]
            box_hits={b['id']:int(np.sum(np.abs(point_box_distance(points[:,:2],b))<.025)) for b in c['obstacles']}
            x0,x1,y0,y1=rect(c);wall_hits=int(np.sum(np.minimum.reduce([abs(points[:,0]-x0),abs(points[:,0]-x1),abs(points[:,1]-y0),abs(points[:,1]-y1)])<.025))
            assert sum(box_hits.values())>0 and wall_hits>0,'Start depth must show an obstacle and an outer wall'
        stats.append(field.update(d,intrinsics(c['camera']),camera_to_world(c['start_pose'],c['camera']['height_m']),True,np.random.default_rng(np.random.SeedSequence([20261027,0,i]))))
    Snapshot(field,dict(sim_s=.5,frame_id=2)).save(out/'start_occupancy.npz')
    assert field.occupied.any(),'No depth occupancy observed after 3 stationary captures'
    write_json(out/'inspection.json',dict(scene=c['phase16_scene'],stationary_captures=3,displayed_depth_frame=0,noise='sigma=.01*d^2',occupied_cells=int(field.occupied.sum()),stats=stats,pose=c['start_pose'],box_depth_hits=box_hits,outer_wall_depth_hits=wall_hits,
        occlusion_note='Not all objects must be visible at start; LC AfterCorner is expected to be occluded. Oracle surface labels are used only in this sensor validation.'))

def main():
    c=scene(a.scene);set_pose,get_pose,capture=build(c)
    if a.mode in ('inspect','reference'):inspect(c,set_pose,capture)
    if a.mode=='inspect':return
    if a.mode=='reference':
        p=protocol();assert p['reference']['center_to_obstacle_m']==.25 and p['reference']['center_to_wall_m']==.25
        reference=ROOT/c['reference_file'];assert sha256_file(reference)==c['reference_sha256']
        frozen=json.loads(reference.read_text());path=np.array(frozen['world_xy']);grid=frozen['geometry']
        poses,commands,result=reference_rollout(c,path)
        for key in ('duration_s','minimum_center_distance_m','minimum_footprint_clearance_m','execution_distance_m'):
            assert abs(result[key]-frozen['offline_pp'][key])<1e-9,key
        write_json(out/'reference_status.json',dict(**result,grid=grid,role='oracle-guided human-demonstration preparation; not NoMaD evaluation'))
        np.save(out/'reference_path.npy',path)
        with (out/'agent_trajectory.csv').open('x') as f:
            w=csv.writer(f);w.writerow(['simulation_time_s','x_m','y_m','yaw_rad']);w.writerows([i/72,*pose] for i,pose in enumerate(poses))
        write_json(out/'reference_commands.json',commands)
        if not result['goal']:raise RuntimeError(result['reason'])
        folder=out/'topomap';(folder/'rgb').mkdir(parents=True);nodes=[];ticks=list(range(0,len(poses),144))
        if ticks[-1]!=len(poses)-1:ticks.append(len(poses)-1)
        for i,tick in enumerate(ticks):
            set_pose(poses[tick]);np.testing.assert_allclose(get_pose(),poses[tick],atol=1e-10,rtol=0);rgb=capture(tick/72);file=folder/f'rgb/{i:04d}.png';Image.fromarray(rgb).save(file)
            nodes.append(dict(node_id=i,reference_pose_row=tick,simulation_time_s=tick/72,world_pose=poses[tick].tolist(),rgb_file=f'rgb/{i:04d}.png',png_sha256=sha256_file(file),rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),rgb_shape=list(rgb.shape)))
        write_json(folder/'manifest.json',dict(dynamic_obstacle=False,node_count=len(nodes),nodes=nodes,spacing_sim_s=2.,scenario=c,
            reference_role='frozen clearance-weighted smoothed oracle route + fixed PP human-demonstration analogue, no NoMaD inference',reference_result=result,source_run=str(out),
            reference_execution_sha=json.loads((out/'provenance.json').read_text())['git_sha'],reference_path_sha256=c['reference_sha256'],protocol_sha256=sha256_file(ROOT/'research/nomad_phase16/protocol.json')))
        from nomad_isaac.topomap import load_map
        load_map(folder/'manifest.json');return
    from nomad_phase16.execution import install_runtime_adapters
    from nomad_isaac.async_runtime import run_async
    install_runtime_adapters();c=runtime_config(c,a.method,a.index,a.topomap,a.timeout)
    write_json(out/'scenario.json',c);write_json(out/'phase16_protocol.json',protocol())
    set_pose(c['goal_pose']);goal=capture(0.);Image.fromarray(goal).save(out/'goal.png');set_pose(c['start_pose']);start=capture(0.);Image.fromarray(start).save(out/'observation_start.png')
    checks=dict(status='PASS',rgb_shape=list(start.shape),depth_shape=list(capture.depth_frame.shape),scene=a.scene,oracle_used_for_control=False)
    summary=run_async(c,out,a.socket,goal,capture,set_pose,get_pose,checks,uniform_delivery_delay_s=a.delay,pure_pursuit=True)
    # run_async writes its own summary; only extra identity is stored separately.
    write_json(out/'phase16_complete.json',dict(scene=a.scene,method=a.method,index=a.index,delay_s=a.delay))

try:
    main()
except BaseException as exc:
    write_json(out/'FAILED.json',dict(error=repr(exc),traceback=traceback.format_exc()));raise
finally:base.app.close()
