import json
from pathlib import Path
from types import FunctionType
from nomad_isaac.common import ROOT,sha256_file
from nomad_j1 import common

HERE=Path(__file__).parent
OUT=ROOT/'research/results/h1v3_j0'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/h1v3_j0_01'
SCENES=('H1-v3',)
INDICES=(221,222)
DELAYS=(0.,.75)
METHOD=common.METHOD

def bind(fn,**kwargs):
    return FunctionType(fn.__code__,dict(fn.__globals__,**kwargs),fn.__name__,fn.__defaults__,fn.__closure__)

def protocol():return json.loads((HERE/'protocol.json').read_text())

def verify():
    p=protocol();assert p['status']=='FROZEN' and p['main_order']==order()
    from nomad_j0.config import verify as base_verify
    base_verify()
    for f,h in p['source_sha256'].items():assert sha256_file(ROOT/f)==h,f
    from .scene import load_spec
    assert load_spec()['status']=='GEOMETRY_PREPARED'
    return p

def scene_config(name):
    assert name=='H1-v3'
    from .scene import configure
    c,manifest=common.scene_config('H1-v2')
    return configure(c),manifest

def checkpoint_spec(name):
    c,_=scene_config(name);b=c['dynamic_obstacle']
    return dict(axis=1,direction=1,box_id=b['id'],dynamic=False,
        threshold_m=float(b['center_xy_m'][1]+common.half_extent(b,1)+.30),
        formula='box center along +y + projected half extent + 0.30')

def runtime_config(method,index,timeout=90,level='H1-v3'):
    assert method==METHOD and index in INDICES and level=='H1-v3' and timeout==90
    build=bind(common.runtime_config,scene_config=scene_config,checkpoint_spec=checkpoint_spec)
    c=build(method,index,timeout,level);c['j0']=True;c['h1v3_screen']=True
    assert c['sdf_registration']==protocol()['scenes']['H1-v3']['sdf_registration']
    return c

def order():return [dict(scene='H1-v3',index=i,method=METHOD,delay=d) for d in DELAYS for i in INDICES]
