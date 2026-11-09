"""Sensor-only future preparation. Replay original node poses, no navigation."""
import argparse,ast,sys,types,json
from pathlib import Path

ap=argparse.ArgumentParser();ap.add_argument('--scene',choices=('L2','H2'),required=True);ap.add_argument('--output',type=Path,required=True)
a,extra=ap.parse_known_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
assert not (out/'render_complete.json').exists() and not (out/'isaac_runtime').exists(),'Existing render attempt refused'
source=Path(__file__).parents[1]/'nomad_isaac/simulator.py'
sys.argv=[str(source),'--output',str(out),'--phase15b-method','FRESHEST-SAFE','--depth-camera','--overnight-phase','9',*extra]
tree=ast.parse(source.read_text());prefix=[]
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name=='main':break
    prefix.append(node)
base=types.ModuleType('nomad_phase44p._renderer');base.__file__=str(source)
exec(compile(ast.Module(body=prefix,type_ignores=[]),str(source),'exec'),base.__dict__)

# Kit has been initialized; all numerical/USD imports follow it.
import hashlib,copy,subprocess
import numpy as np
from PIL import Image
from nomad_isaac.common import write_json,sha256_file
from nomad_phase26.rendering import make
from nomad_isaac.old_rollout_placement import magenta_mask
from nomad_phase44p.config import runtime_config,protocol,METHODS,HERE,ROOT
from nomad_phase44p.appearance import apply

try:
    p=protocol();old_path=Path(p['scenes'][a.scene]['original_topomap']);old=json.loads(old_path.read_text())
    c=runtime_config(METHODS[0],217,90,a.scene,maps_required=False)
    set_pose,get_pose,capture=make(base,c,out)
    example=c['phase38_jitter'][0];pose=example['canonical_pose'];box=dict(example['canonical_box'],spawn_tick=0)
    capture.sync_dynamic(dict(tick=0,resolved_dynamic_obstacle=box))
    set_pose(pose)
    for _ in range(3):original=capture(0.)
    before_depth=capture.depth_frame.copy()
    assert magenta_mask(original).sum()>=20
    Image.fromarray(original).save(out/'render_original.png')
    appearance=apply(capture.stage,c,base);write_json(out/'appearance_check.json',appearance)
    for _ in range(3):changed=capture(0.)
    after_depth=capture.depth_frame.copy()
    np.testing.assert_array_equal(np.isfinite(before_depth),np.isfinite(after_depth))
    finite=np.isfinite(before_depth)
    error=float(np.max(np.abs(before_depth[finite]-after_depth[finite])))
    assert error<=1e-6,'Material change altered depth geometry'
    assert float(np.mean(np.abs(original.astype(float)-changed)))>1.,'No visible appearance change'
    assert magenta_mask(changed).sum()>=20
    Image.fromarray(changed).save(out/'render_changed.png')
    # All demonstration nodes must be rendered with every sudden box hidden.
    prim=capture.stage.GetPrimAtPath('/World/'+box['id'])
    visibility=base.UsdGeom.Imageable(prim).CreateVisibilityAttr()
    visibility.Set(base.UsdGeom.Tokens.invisible);visibility.Set(base.UsdGeom.Tokens.invisible,base.Usd.TimeCode(0))
    destination=out/'topomap';(destination/'rgb').mkdir(parents=True)
    nodes=[]
    for node in old['nodes']:
        set_pose(node['world_pose']);np.testing.assert_allclose(get_pose(),node['world_pose'],atol=1e-10,rtol=0)
        capture(node['simulation_time_s']);rgb=capture(node['simulation_time_s'])
        assert not magenta_mask(rgb).any(),'Sudden box/static-magenta contamination in demonstration'
        relative=f"rgb/{node['node_id']:04d}.png";file=destination/relative;Image.fromarray(rgb).save(file)
        nodes.append(dict(node,rgb_file=relative,png_sha256=sha256_file(file),rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest()))
    manifest=copy.deepcopy(old);manifest.update(nodes=nodes,phase44p=True,dynamic_obstacle=False,
        original_manifest=str(old_path),original_manifest_sha256=sha256_file(old_path),
        render_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_sha256=sha256_file(HERE/'protocol.json'),appearance_geometry_sha256=appearance['geometry_sha256'],
        new_navigation_count=0,new_inference_count=0,new_render_count=2*len(nodes)+6,
        reference_capture_calls=2*len(nodes),example_capture_calls=6,
        note='Identical saved reference node IDs/poses/timestamps/spacing; appearance-only RGB regeneration; dynamic objects hidden')
    capture.stage.GetRootLayer().Export(str(out/'scene.usda'));manifest['rendered_scene_sha256']=sha256_file(out/'scene.usda')
    write_json(destination/'manifest.json',manifest)
    write_json(out/'render_complete.json',dict(passed=True,scene=a.scene,node_count=len(nodes),geometry_identical=True,
        example_depth_max_error_m=error,example_pose=pose,example_seed=217,example_box=box,
        protocol_sha256=sha256_file(HERE/'protocol.json'),manifest_sha256=sha256_file(destination/'manifest.json'),
        navigation_runs=0,nomad_inferences=0))
finally:base.app.close()
