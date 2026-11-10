"""Frozen static appearance; add one time-sampled USD cylinder after Kit init."""
import copy,json,time,threading
import numpy as np
from nomad_isaac.common import write_json
from nomad_phase26.rendering import make as frozen_make
from .motion import center_at,travel_duration

def make(base,c,out):
    static=copy.deepcopy(c);static.pop('dynamic_obstacle',None)
    set_pose,get_pose,original=frozen_make(base,static,out);stage=original.stage
    stage.SetTimeCodesPerSecond(72);stage.SetFramesPerSecond(72);stage.SetStartTimeCode(0);stage.SetEndTimeCode(c['timeout_sim_s']*72)
    cylinder=base.UsdGeom.Cylinder.Define(stage,'/World/MovingPerson');cylinder.CreateRadiusAttr(.2);cylinder.CreateHeightAttr(1.7);cylinder.CreateAxisAttr('Z')
    translate=cylinder.AddTranslateOp();translate.Set(base.Gf.Vec3d(0.,0.,.85))
    mat=base.UsdShade.Material.Define(stage,'/World/Materials/MovingPerson')
    shader=base.UsdShade.Shader.Define(stage,mat.GetPath().AppendChild('Shader'));shader.CreateIdAttr('UsdPreviewSurface')
    shader.CreateInput('diffuseColor',base.Sdf.ValueTypeNames.Color3f).Set(base.Gf.Vec3f(.65,.04,.65))
    shader.CreateInput('roughness',base.Sdf.ValueTypeNames.Float).Set(.85)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');base.UsdShade.MaterialBindingAPI.Apply(cylinder.GetPrim()).Bind(mat)
    visibility=base.UsdGeom.Imageable(cylinder.GetPrim()).CreateVisibilityAttr();visibility.Set(base.UsdGeom.Tokens.invisible);visibility.Set(base.UsdGeom.Tokens.invisible,base.Usd.TimeCode(0))
    state={'spawn':None};main_thread=threading.get_ident();log=(out/'person_render.jsonl').open('x')
    def sync(snapshot):
        assert threading.get_ident()==main_thread
        person=snapshot.get('resolved_dynamic_obstacle')
        if person is None:return
        if state['spawn'] is None:
            state['spawn']=person['spawn_sim_s'];state['exit']=person['exit_sim_s']
            for t,q in ((state['spawn'],person['start_xy']),(state['exit'],person['end_xy'])):
                translate.Set(base.Gf.Vec3d(*q,.85),base.Usd.TimeCode(t*72))
            visibility.Set(base.UsdGeom.Tokens.inherited,base.Usd.TimeCode(state['spawn']*72))
            visibility.Set(base.UsdGeom.Tokens.invisible,base.Usd.TimeCode(state['exit']*72))
            write_json(out/'person_render_setup.json',dict(shape='UsdGeom.Cylinder',radius_m=.2,height_m=1.7,
                spawn_s=state['spawn'],exit_s=state['exit'],static_renderer='nomad_phase26.rendering.make',oracle_publication=False))
        tick=snapshot['tick'];q=center_at(c['phase50p_moving'],snapshot['sim_s']-state['spawn'])
        actual=translate.Get(base.Usd.TimeCode(tick));np.testing.assert_allclose(actual,[*q,.85],atol=1e-9,rtol=0)
        bounds=base.UsdGeom.BBoxCache(base.Usd.TimeCode(tick),[base.UsdGeom.Tokens.default_]).ComputeWorldBound(cylinder.GetPrim()).ComputeAlignedRange()
        if state['spawn']<=snapshot['sim_s']<state['exit']:
            np.testing.assert_allclose(bounds.GetMin(),[q[0]-.2,q[1]-.2,0],atol=1e-6,rtol=0)
            np.testing.assert_allclose(bounds.GetMax(),[q[0]+.2,q[1]+.2,1.7],atol=1e-6,rtol=0)
        log.write(json.dumps(dict(tick=tick,simulation_time_s=snapshot['sim_s'],center_xy_m=q.tolist(),visible=person['active']),allow_nan=False)+'\n');log.flush()
    def capture(t):
        result=original(t);capture.depth_frame=original.depth_frame;capture.dynamic_mask=original.dynamic_mask
        active=state['spawn'] is not None and state['spawn']<=t<state['exit']
        capture.dynamic_metadata=dict(capture_tick=round(t*72),active=bool(active),visible=bool(active and original.dynamic_mask.sum()>=20),
            magenta_pixels=int(original.dynamic_mask.sum()),evidence_mode='RGB_MAGENTA',shape='cylinder')
        return result
    capture.sync_dynamic=sync;capture.stage=stage;capture.close=log.close
    stage.GetRootLayer().Export(str(out/'scene.usda'))
    return set_pose,get_pose,capture
