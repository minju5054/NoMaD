"""Initialize Kit before any numerical imports, then use frozen live methods."""
import argparse,ast,sys,types,os
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--level',required=True);ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--method',required=True);ap.add_argument('--index',type=int,required=True);ap.add_argument('--delay',type=float,required=True)
ap.add_argument('--socket',required=True);ap.add_argument('--timeout',type=float,default=90.)
a,extra=ap.parse_known_args();out=a.output.resolve()
source=Path(__file__).parents[1]/'nomad_isaac/simulator.py';sys.path[0]=str(source.parent)
sys.argv=[str(source),'--output',str(out),'--phase15b-method','FRESHEST-SAFE','--depth-camera','--overnight-phase','9',*extra]
tree=ast.parse(source.read_text());prefix=[]
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name=='main':break
    prefix.append(node)
base=types.ModuleType('nomad_phase26._renderer');base.__file__=str(source)
exec(compile(ast.Module(body=prefix,type_ignores=[]),str(source),'exec'),base.__dict__)
# SimulationApp is now initialized.
import traceback
from PIL import Image
from nomad_isaac.common import write_json
from nomad_phase26.config import runtime_config
from nomad_phase26.execution import install,run_without_oracle
from nomad_phase26.rendering import make

try:
    c=runtime_config(a.method,a.index,a.timeout,a.level)
    set_pose,get_pose,capture=make(base,c,out);install(c);write_json(out/'scenario.json',c)
    set_pose(c['goal_pose']);goal=capture(0.)
    if os.environ.get('NOMAD_PHASE24_FULL_FRAMES','1')=='1':Image.fromarray(goal).save(out/'goal.png')
    set_pose(c['start_pose']);start=capture(0.)
    if os.environ.get('NOMAD_PHASE24_FULL_FRAMES','1')=='1':Image.fromarray(start).save(out/'observation_start.png')
    checks=dict(status='PASS',rgb_shape=list(start.shape),depth_shape=list(capture.depth_frame.shape) if c['depth_camera'] else None,scene=a.level,oracle_used_for_control=False)
    run_without_oracle(c,out,a.socket,goal,capture,set_pose,get_pose,checks,uniform_delivery_delay_s=a.delay,pure_pursuit=True)
    write_json(out/'phase26_complete.json',dict(scene=a.level,method=a.method,index=a.index,delay_s=a.delay))
except BaseException as exc:
    write_json(out/'FAILED.json',dict(error=repr(exc),traceback=traceback.format_exc()));raise
finally:base.app.close()
