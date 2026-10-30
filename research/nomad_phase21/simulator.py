"""SO renderer: protected setup/build/capture functions; no heavy import before Kit."""
import argparse,ast,sys,types
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--level',choices=['L2','L2A'],required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--method',required=True)
ap.add_argument('--index',type=int,required=True);ap.add_argument('--delay',type=float,required=True)
ap.add_argument('--socket',required=True);ap.add_argument('--timeout',type=float,default=90.)
a,extra=ap.parse_known_args();out=a.output.resolve()
source=Path(__file__).parents[1]/'nomad_isaac/simulator.py';sys.path[0]=str(source.parent)
sys.argv=[str(source),'--output',str(out),'--phase15b-method','FRESHEST-SAFE','--depth-camera','--overnight-phase','9',*extra]
tree=ast.parse(source.read_text());prefix=[]
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name=='main':break
    prefix.append(node)
base=types.ModuleType('nomad_phase20._renderer');base.__file__=str(source)
exec(compile(ast.Module(body=prefix,type_ignores=[]),str(source),'exec'),base.__dict__)
# Kit is initialized. Numerical/depth/repair imports are now safe.
import json,time,threading,traceback
import numpy as np
from PIL import Image
from nomad_isaac.common import write_json
from nomad_isaac.clearance import obstacle_bounds,single_obstacle_config
from nomad_isaac.sudden_obstacle import active_at_tick
from nomad_phase21.config import runtime_config
from nomad_phase21.execution import install,run_without_oracle


def render_functions(config):
    stage,agent,translate,rotate,camera,annotator,product=base.build_scene(config)
    stage.GetRootLayer().Export(str(out/'scene.usda'))
    depth_annotator=None
    if config.get('depth_camera'):
        depth_annotator=base.rep.AnnotatorRegistry.get_annotator('distance_to_image_plane',device='cpu');depth_annotator.attach([product])
    timeline=base.omni.timeline.get_timeline_interface();timeline.pause();base.rep.orchestrator.set_capture_on_play(False)
    # Compile these unchanged nested functions together in their original closure.
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    functions=[n for n in main.body if isinstance(n,ast.FunctionDef) and n.name in ('sync_dynamic','set_pose','get_pose','capture')]
    assert len(functions)==4
    pre=ast.parse("resolved_dynamic=None\nmain_thread_id=threading.get_ident()\nadaptive=True\ndynamic_annotator=None\ndynamic_prim=stage.GetPrimAtPath('/World/DynamicObstacle')\n").body
    ret=ast.parse('capture.sync_dynamic=sync_dynamic\nreturn set_pose,get_pose,capture\n').body
    factory=ast.FunctionDef(name='factory',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=k) for k in ('config','stage','agent','translate','rotate','camera','annotator','product','depth_annotator','timeline')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=pre+functions+ret,decorator_list=[])
    ns=dict(base.__dict__);ns.update(out=out,obstacle_bounds=obstacle_bounds,single_obstacle_config=single_obstacle_config,active_at_tick=active_at_tick)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[factory],type_ignores=[])),str(source),'exec'),ns)
    return ns['factory'](config,stage,agent,translate,rotate,camera,annotator,product,depth_annotator,timeline)


try:
    c=runtime_config(a.method,a.index,a.timeout,level=a.level);set_pose,get_pose,capture=render_functions(c);install()
    write_json(out/'scenario.json',c)
    set_pose(c['goal_pose']);goal=capture(0.);Image.fromarray(goal).save(out/'goal.png')
    set_pose(c['start_pose']);start=capture(0.);Image.fromarray(start).save(out/'observation_start.png')
    checks=dict(status='PASS',rgb_shape=list(start.shape),depth_shape=list(capture.depth_frame.shape) if c['depth_camera'] else None,scene=a.level,oracle_used_for_control=False)
    run_without_oracle(c,out,a.socket,goal,capture,set_pose,get_pose,checks,uniform_delivery_delay_s=a.delay,pure_pursuit=True)
    write_json(out/'phase21_complete.json',dict(scene=a.level,method=a.method,index=a.index,delay_s=a.delay))
except BaseException as exc:
    write_json(out/'FAILED.json',dict(error=repr(exc),traceback=traceback.format_exc()));raise
finally:base.app.close()
