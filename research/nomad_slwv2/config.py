import copy
import json
from pathlib import Path
from types import FunctionType
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase18.config import scene as old_scene
from nomad_j1 import common
from nomad_j1.depth import registration

HERE=Path(__file__).parent
OUT=ROOT/'research/results/slwv2_j0'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/slwv2_j0_01'
REFERENCE_ROOT=RUN_ROOT/'reference'
TOPOMAP=REFERENCE_ROOT/'topomap/manifest.json'
SCENES=('SLW-v2',)
INDICES=(221,222)
DELAYS=(0.,.75)
METHOD=common.METHOD
COLORS=((.85,.08,.08),(.08,.20,.85),(.95,.80,.04))

def bind(fn,**kwargs):return FunctionType(fn.__code__,dict(fn.__globals__,**kwargs),fn.__name__,fn.__defaults__,fn.__closure__)
def protocol():return json.loads((HERE/'protocol.json').read_text())
def order():return [dict(scene='SLW-v2',index=i,method=METHOD,delay=d) for d in DELAYS for i in INDICES]

def build_scene():
    c=copy.deepcopy(old_scene('SLW'))
    c['name']='SLW-v2';c['phase16_scene']='SLW-v2';c['scene_variant']='SLW-v2'
    c['start_pose'][0]=-1.;c['corridor']['xmin']-=1.
    for obj,color in zip(c['obstacles'],COLORS):obj['color_rgb']=list(color)
    # These describe the old demonstration, not physical scene geometry.
    for key in list(c):
        if key.startswith('reference_') or key=='grid_feasibility':c.pop(key)
    return c

def verify(require_assets=False):
    from nomad_j0.config import verify as base_verify
    base_verify();p=protocol();assert p['status']=='FROZEN' and p['main_order']==order()
    for f,h in p['source_sha256'].items():assert sha256_file(ROOT/f)==h,f
    assert p['publish_branch']=='research/phase0-infrastructure'
    if require_assets:verify_assets()
    return p

def verify_assets():
    p=protocol();file=RUN_ROOT/'resolved_assets.json'
    assert file.exists(),'New reference/Topomap must be prepared first by campaign'
    resolved=json.loads(file.read_text());assert resolved['protocol_sha256']==sha256_file(HERE/'protocol.json')
    for f,h in resolved['sha256'].items():assert sha256_file(f)==h,f
    assert resolved['topomap_manifest']==str(TOPOMAP) and resolved['spacing_sim_s']==2.
    return resolved

def scene(name):
    assert name=='SLW-v2'
    return json.loads((RUN_ROOT/'reference_definition/scenario.json').read_text())

def checkpoint_spec(name):
    assert name=='SLW-v2'
    return dict(axis=0,direction=1,box_id='Slalom3',dynamic=False,threshold_m=4.6,
                formula='last box +x far face +0.30; identical to SLW')

def scene_config(name):return scene(name),str(TOPOMAP)

def runtime_config(method,index,timeout=90,level='SLW-v2'):
    assert method==METHOD and index in INDICES and level=='SLW-v2' and timeout==90
    verify_assets()
    c=bind(common.runtime_config,scene_config=scene_config,checkpoint_spec=checkpoint_spec)(method,index,timeout,level)
    c['j0']=True;c['slwv2_screen']=True
    assert c['sdf_registration']==protocol()['scenes']['SLW-v2']['sdf_registration']
    return c
