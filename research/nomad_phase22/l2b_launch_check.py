"""Spawn-only integration fixture: real method startup, monitor and renderer.

No navigation, inference requests, planning solves or performance summaries.
Invoke through Isaac python with the drive_simulator arguments (index901..903).
"""
import ast,sys
from pathlib import Path

# Reuse the exact production SimulationApp bootstrap and render functions.
# The final navigation try/finally is deliberately not executed.
source=Path(__file__).with_name('drive_simulator.py');tree=ast.parse(source.read_text());prefix=[]
for node in tree.body:
    if isinstance(node,ast.Try):break
    prefix.append(node)
scope=dict(__name__='nomad_phase22._spawn_fixture',__file__=str(source))
exec(compile(ast.Module(body=prefix,type_ignores=[]),str(source),'exec'),scope)

# SimulationApp now exists; numerical imports are safe.
import json,time,traceback
import numpy as np
from PIL import Image
from nomad_isaac.common import write_json,sha256_file,ROOT
from nomad_isaac.sudden_obstacle import SuddenObstacleMonitor
from nomad_phase22.drive_config import runtime_config
from nomad_phase22.drive_execution import install,make_execution
from nomad_phase22.drive_geometry import OrientedMonitor,local_pose,bounds
from nomad_isaac.clearance import swept_clearance

a=scope['a'];out=scope['out'];execution=dynamic=None
try:
    assert a.level=='L2B' and a.index in (901,902,903)
    # Only the fixture's start pose/index differ; use the identical signed scene.
    c=runtime_config(a.method,121 if a.index%2 else 122,90,'L2B')
    c.update(seed_offset=10000*a.index,run_id=f'L2B_LAUNCH_ONLY_{a.index}',start_pose=[2.5,0.,0.])
    set_pose,get_pose,capture=scope['render_functions'](c);install()
    execution=make_execution(c,out)
    dynamic=SuddenObstacleMonitor(c,out);pose=np.array(c['start_pose']);set_pose(pose)
    first=dynamic.observe_tick(0,pose,pose,0.,0.,-1,False,time.monotonic_ns())
    assert dynamic.spawn and first['collision_checked'] and isinstance(dynamic.monitor,OrientedMonitor)
    box=dynamic.obstacle
    capture.sync_dynamic(dict(resolved_dynamic_obstacle=box,tick=0,sim_s=0.));capture(0.)
    depth=capture.depth_frame.copy();mask=capture.dynamic_mask.copy().astype(bool)
    valid=mask&np.isfinite(depth)&(depth>0)&(depth<=3.)
    assert valid.any(),'Spawn box not visible in depth'
    rendered=json.loads((out/'dynamic_render_update.json').read_text());assert rendered['obstacle']==box
    # Exercise post-spawn swept evaluation too, without advancing a policy.
    row=dynamic.monitor.observe_interval(pose,pose,0.,0.,0.,1/72)
    half=np.array(box['size_xyz_m'][:2])/2
    exact=swept_clearance(local_pose(pose,box),0.,0.,1/72,-half,half,c['agent_radius_m'])
    assert abs(row['lower_m']-exact['lower_m'])<1e-12
    np.savez_compressed(out/'spawn_depth.npz',depth=depth,mask=mask)
    Image.fromarray((np.clip(np.nan_to_num(depth,nan=0,posinf=0)/5,0,1)*255).astype(np.uint8)).save(out/'spawn_depth.png')
    write_json(out/'launch_check.json',dict(passed=True,method=a.method,index=a.index,excluded=True,fixture='teleport to spawn plane; no policy advancement',
        navigation=False,inference_requests=0,planner_solves=0,performance_metrics_saved=False,box=box,box_world_bounds=[x.tolist() for x in bounds(box)],
        collision_model=type(dynamic.monitor).__name__,rigid_swept_error_m=abs(row['lower_m']-exact['lower_m']),depth_box_pixels=int(valid.sum()),
        execution_class=type(execution).__module__+'.'+type(execution).__name__,worker_class=type(execution.repair_worker).__module__+'.'+type(execution.repair_worker).__name__,
        geometry_source_sha256=sha256_file(ROOT/'research/nomad_phase22/drive_geometry.py')))
    print(f'[launch-check] {a.method} index{a.index} PASS',flush=True)
except BaseException as exc:
    write_json(out/'launch_check_failed.json',dict(error=repr(exc),traceback=traceback.format_exc()));raise
finally:
    if dynamic is not None:
        dynamic.activation.close()
        if dynamic.monitor is not None:dynamic.monitor.log.close();dynamic.monitor.plans.close()
    if execution is not None:execution.close()
    scope['base'].app.close()
