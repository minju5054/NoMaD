"""GUI-only USD export of existing poses; no simulator or inference execution."""
import argparse
import ast
import subprocess
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
source = args.run.resolve()
out = args.output.resolve()
assert out != source and source not in out.parents, 'Keep GUI files outside the raw run'
out.mkdir(parents=True, exist_ok=False)
target = out / 'recorded_motion_gui.usda'
assert not target.exists(), 'Never overwrite an existing export'
names = ['scene_gui.usda', 'agent_trajectory.csv', 'scenario.json', 'summary.json', 'provenance.json']
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
before = {name: digest(source / name) for name in names}
rows = list(csv.DictReader((source / 'agent_trajectory.csv').open()))
config = json.loads((source / 'scenario.json').read_text())
hz = config['integration_hz']
original = Usd.Stage.Open(str(source / 'scene_gui.usda'))
original.Export(str(target))
stage = Usd.Stage.Open(str(target))
agent = UsdGeom.Xformable(stage.GetPrimAtPath('/World/Agent'))
translate = next(op for op in agent.GetOrderedXformOps() if op.GetOpType() == UsdGeom.XformOp.TypeTranslate)
rotate = next(op for op in agent.GetOrderedXformOps() if op.GetOpType() == UsdGeom.XformOp.TypeRotateZ)

# Reuse exactly the existing renderer's visual definitions; exclude all RTX,
# MP4, simulation startup and controller/model code.
renderer = root / 'visualnav-transformer/research/nomad_isaac/render_recorded.py'
tree = ast.parse(renderer.read_text())
helpers = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ('material', 'line')]
main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
start = next(i for i, node in enumerate(main.body) if isinstance(node, ast.Expr) and ast.unparse(node).startswith('UsdGeom.Xform.Define'))
end = next(i for i, node in enumerate(main.body) if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'product' for t in node.targets))
exec(compile(ast.Module(body=helpers + main.body[start:end], type_ignores=[]), str(renderer), 'exec'))
# Scale the visual heading with the footprint; the physical collision radius
# comes only from the run scenario. This cannot alter recorded poses.
heading.GetPointsAttr().Set([(x*config['agent_radius_m']/.12, y*config['agent_radius_m']/.12, z)
                             for x, y, z in heading.GetPointsAttr().Get()])
trail.GetPointsAttr().Set([(float(r['x_m']), float(r['y_m']), .009) for r in rows])
trail.GetCurveVertexCountsAttr().Set([len(rows)])
yaws = np.unwrap([float(r['yaw_rad']) for r in rows])
translate.Set(Gf.Vec3d(float(rows[0]['x_m']), float(rows[0]['y_m']), 0))
rotate.Set(math.degrees(float(yaws[0])))
for i, row in enumerate(rows):
    assert abs(float(row['simulation_time_s']) - i / hz) < 1e-10
    translate.Set(Gf.Vec3d(float(row['x_m']), float(row['y_m']), 0), Usd.TimeCode(i))
    rotate.Set(math.degrees(float(yaws[i])), Usd.TimeCode(i))
stage.SetTimeCodesPerSecond(hz)
stage.SetFramesPerSecond(24)
stage.SetStartTimeCode(0)
stage.SetEndTimeCode(len(rows)-1)
stage.SetMetadataByDictKey('customLayerData', 'cameraSettings:boundCamera', str(camera.GetPath()))
stage.GetRootLayer().Save()

maximum_error = 0.
for i, row in enumerate(rows):
    matrix = agent.ComputeLocalToWorldTransform(Usd.TimeCode(i))
    xyz = matrix.ExtractTranslation()
    forward = matrix.TransformDir(Gf.Vec3d(1, 0, 0))
    yaw_error = math.remainder(math.atan2(forward[1], forward[0]) - float(row['yaw_rad']), 2*math.pi)
    maximum_error = max(maximum_error, abs(xyz[0]-float(row['x_m'])), abs(xyz[1]-float(row['y_m'])), abs(yaw_error))
assert maximum_error < 1e-10
original_prims = 0
for prim in original.Traverse():
    actual = stage.GetPrimAtPath(prim.GetPath())
    assert actual and actual.GetTypeName() == prim.GetTypeName()
    for attr in prim.GetAttributes():
        assert actual.GetAttribute(attr.GetName()).Get() == attr.Get(), (str(prim.GetPath()), attr.GetName())
    for rel in prim.GetRelationships():
        assert actual.GetRelationship(rel.GetName()).GetTargets() == rel.GetTargets()
    original_prims += 1
assert before == {name: digest(source / name) for name in names}
manifest = {
    'kind': 'native_gui_replay_of_recorded_execution', 'source_run': str(source),
    'source_sha256': before, 'new_inference_count': 0, 'new_navigation_count': 0,
    'source_pose_count': len(rows), 'time_codes_per_second': hz,
    'simulation_duration_s': float(rows[-1]['simulation_time_s']),
    'max_pose_error': maximum_error, 'original_prims_preserved': original_prims,
    'raw_inputs_unchanged': True, 'scene': str(target), 'scene_sha256': digest(target),
    'existing_visual_source': str(renderer), 'visual_source_sha256': digest(renderer),
    'export_script_sha256': digest(Path(__file__)),
    'source_commit': json.loads((source/'provenance.json').read_text())['git_sha'],
    'export_git_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root/'visualnav-transformer', text=True).strip(),
    'agent_radius_m': config['agent_radius_m'],
    'recorded_outcome': {k: json.loads((source/'summary.json').read_text())[k]
                         for k in ['termination_reason', 'goal_entry']},
    'note': 'All 72 Hz poses retained; full cyan executed trail is a static visual aid. Native timeline loops at simulation time; not a new live navigation run.'
}
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(manifest, indent=2))
