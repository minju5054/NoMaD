"""Sensor-only multi-box rendering; use only after SimulationApp exists."""
import json,time,threading,math,hashlib
import numpy as np
from nomad_isaac.common import write_json
from nomad_phase24r.geometry import repair_and_check
from nomad_isaac.old_rollout_placement import magenta_mask

def make(base,config,out):
    stage,agent,translate,rotate,camera,rgb,product=base.build_scene(config)
    geometry=repair_and_check(stage,config,base);write_json(out/'geometry_check.json',geometry)
    stage.GetRootLayer().Export(str(out/'scene.usda'))
    depth=None
    if config['depth_camera']:
        depth=base.rep.AnnotatorRegistry.get_annotator('distance_to_image_plane',device='cpu');depth.attach([product])
    timeline=base.omni.timeline.get_timeline_interface();timeline.pause();base.rep.orchestrator.set_capture_on_play(False)
    displayed={};main_thread=threading.get_ident()
    def sync_dynamic(snapshot):
        assert threading.get_ident()==main_thread
        payload=snapshot.get('resolved_dynamic_obstacle')
        if payload is None:return
        boxes=payload.get('phase26_boxes',[payload])
        for box in boxes:
            identity=box['id']
            if identity in displayed:
                assert displayed[identity]==box;continue
            prim=stage.GetPrimAtPath('/World/'+identity)
            if not prim.IsValid():
                # Copy the original dynamic cube's material and exact geometry
                # representation; keep the first cube visible after box2 spawns.
                cube=base.UsdGeom.Cube.Define(stage,'/World/'+identity);cube.CreateSizeAttr(1.)
                cube.AddTranslateOp();cube.AddScaleOp(precision=base.UsdGeom.XformOp.PrecisionDouble)
                prim=cube.GetPrim();mat=base.UsdShade.Material(stage.GetPrimAtPath('/World/Materials/DynamicObstacle'))
                base.UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)
            prim.GetAttribute('xformOp:translate').Set(base.Gf.Vec3d(*box['center_xy_m'],box['size_xyz_m'][2]/2))
            prim.GetAttribute('xformOp:scale').Set(base.Gf.Vec3d(*box['size_xyz_m']))
            visibility=base.UsdGeom.Imageable(prim).CreateVisibilityAttr();visibility.Set(base.UsdGeom.Tokens.invisible,base.Usd.TimeCode(0));visibility.Set(base.UsdGeom.Tokens.inherited,base.Usd.TimeCode(box['spawn_tick']))
            bounds=base.UsdGeom.BBoxCache(base.Usd.TimeCode(box['spawn_tick']),[base.UsdGeom.Tokens.default_]).ComputeWorldBound(prim).ComputeAlignedRange()
            center=np.array([*box['center_xy_m'],box['size_xyz_m'][2]/2]);half=np.array(box['size_xyz_m'])/2
            np.testing.assert_allclose(bounds.GetMin(),center-half,atol=1e-9,rtol=0);np.testing.assert_allclose(bounds.GetMax(),center+half,atol=1e-9,rtol=0)
            displayed[identity]=dict(box)
            write_json(out/f'dynamic_render_{identity}.json',dict(obstacle=box,snapshot_tick=snapshot['tick'],usd_aabb=[list(bounds.GetMin()),list(bounds.GetMax())],applied_host_ns=time.monotonic_ns()))
            if len(displayed)==1:write_json(out/'dynamic_render_update.json',dict(obstacle=box,snapshot_tick=snapshot['tick']))
    def set_pose(p):translate.Set(base.Gf.Vec3d(float(p[0]),float(p[1]),0.));rotate.Set(float(np.degrees(p[2])))
    def get_pose():
        m=base.UsdGeom.Xformable(agent).ComputeLocalToWorldTransform(0);v=m.ExtractTranslation();f=m.TransformDir(base.Gf.Vec3d(1,0,0));return np.array([v[0],v[1],math.atan2(f[1],f[0])])
    def capture(t):
        timeline.set_current_time(t)
        for _ in range(20):
            base.rep.orchestrator.step(rt_subframes=4,delta_time=0.,pause_timeline=True)
            color=np.asarray(rgb.get_data());d=np.asarray(depth.get_data()) if depth is not None else None
            if color.shape==(240,320,4) and (d is None or (d.shape==(240,320) and np.isfinite(d).any())):break
        assert color.shape==(240,320,4) and color.dtype==np.uint8 and color.std()>5
        if depth is not None:assert d.shape==(240,320) and np.isfinite(d).any();capture.depth_frame=d.copy()
        result=np.ascontiguousarray(color[:,:,:3]);mask=magenta_mask(result);capture.dynamic_mask=mask
        if 'dynamic_obstacle' in config:
            active=[b for b in displayed.values() if b['spawn_tick']<=round(t*72)]
            if not active:assert not mask.any(),'Dynamic object visible before spawn'
            capture.dynamic_metadata=dict(capture_tick=round(t*72),active=bool(active),visible=bool(active and mask.sum()>=20),magenta_pixels=int(mask.sum()),
                mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),evidence_mode='RGB_MAGENTA',rendered_ids=[b['id'] for b in active])
        return result
    if 'dynamic_obstacle' in config:capture.sync_dynamic=sync_dynamic
    capture.stage=stage
    return set_pose,get_pose,capture
