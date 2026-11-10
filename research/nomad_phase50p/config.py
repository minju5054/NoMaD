"""Standard-library setup only; never import scipy/torch before Kit."""
import copy,json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase47c.config import runtime_config as frozen_config,verify as verify47

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase50p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase50p_01'
METHODS=('OURS-DETOUR+HMM',);INDICES=(221,222,223);BASE_SCENES=('H1','L2');SPEEDS=(.5,1.)
SCENES=tuple(f'{s}_V{round(v*100):03d}' for s in BASE_SCENES for v in SPEEDS)
RANDOM_SEED=20261113

def protocol():return json.loads((HERE/'protocol.json').read_text())
def condition(level):
    scene,speed=level.split('_V');assert scene in BASE_SCENES and level in SCENES
    return scene,int(speed)/100

def registered_order():
    rng=random.Random(RANDOM_SEED);order=[]
    for index in INDICES:
        for scene in BASE_SCENES:
            levels=[f'{scene}_V{round(v*100):03d}' for v in SPEEDS];rng.shuffle(levels)
            order.extend(dict(scene=level,index=index,method=METHODS[0]) for level in levels)
    return order

def runtime_config(method,index,timeout=90,level='H1_V050'):
    assert method==METHODS[0] and index in INDICES and timeout==90
    scene,speed=condition(level);c=frozen_config(method,index,timeout,scene)
    p=protocol();moving=copy.deepcopy(p['placements'][f'{scene}_{index}']);moving['speed_m_s']=speed
    c.update(phase50p=True,phase50p_method=method,phase50p_condition=level,phase50p_moving=moving,run_id=f'{level}_{index}')
    # Only dynamic scenario metadata changes. Static geometry/render/Topomap and
    # all method aliases/EC/filter/plant/HMM settings remain from Phase47-C.
    c['dynamic_obstacle']=dict(id='MovingPerson',shape='cylinder',radius_m=.2,height_m=1.7,
        size_xyz_m=[.4,.4,1.7],color_rgb=[.65,.04,.65],placement={'mode':'phase50p_crossing'})
    return c

def verify():
    verify47();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
