"""Standard-library-only method registration and frozen source checks."""
import json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase35.config import runtime_config as frozen_config

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase38';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase38_01'
SMOKE_ROOT=ROOT.parent/'artifacts/isaac6/phase38_smoke_01'
METHODS=('NOMAD_RAW','TE','RTC','ASTAR+EC','OURS','TE+EC','RTC+EC','OURS-DETOUR','CARE')
SMOKE_METHODS=('TE+EC','RTC+EC','CARE','OURS-DETOUR')
SCENES=('SLW','LC','L2','H1','H2');INDICES=(217,218,219,220);ORDER_SEED=20261111
ALIASES={'NOMAD_RAW':'NOMAD_RAW','TE':'SAFE_TE','RTC':'SAFE_RTC','ASTAR+EC':'ASTAR+EC','OURS':'OURS',
         'TE+EC':'SAFE_TE','RTC+EC':'SAFE_RTC','OURS-DETOUR':'OURS','CARE':'NOMAD_RAW'}
EC_METHODS=('OURS','ASTAR+EC','TE+EC','RTC+EC','OURS-DETOUR')

def registered_order():
    rng=random.Random(ORDER_SEED);blocks=[];order=[]
    for index in INDICES:
        for scene in SCENES:
            methods=list(METHODS);rng.shuffle(methods);night=1 if index<=218 else 2
            blocks.append(dict(night=night,scene=scene,index=index,methods=methods))
            order.extend(dict(night=night,scene=scene,index=index,method=m) for m in methods)
    return blocks,order

def protocol():return json.loads((HERE/'protocol.json').read_text())

def runtime_config(method,index,timeout=90,level='H1'):
    assert method in METHODS and index in (*INDICES,95) and timeout==90 and level in SCENES
    c=frozen_config(ALIASES[method],95 if index==95 else 212,90,level)
    c.update(seed_offset=index*10000,run_id=f'{level}_{index}',phase35_index=index,phase38=True,phase38_method=method,phase38_index=index)
    if method=='CARE':
        # The nonempty sensor tag attaches a current-frame receiver, not the
        # SAFE factory: make_execution routes it to RawNA+CARE explicitly.
        c.update(phase35_method='CARE',phase26_method='CARE',phase24_method='CARE',phase24r_method='CARE',
            phase15b_method='CARE_DEPTH_FRAME',depth_camera=True)
    if method in ('TE+EC','RTC+EC'):c.update(phase32=True,phase32_method='C0-NA+EC',phase32_index=index)
    for key in ('phase29_index','phase32_index'):
        if key in c:c[key]=index
    p=protocol();c['phase38_jitter']=p['placements'].get(f'{level}_{index}',[])
    c['phase38_care']=p['care'];c['phase38_ec']=p['ec_extension']
    return c

def verify():
    from nomad_phase35.config import verify as baseline_verify
    baseline_verify();p=protocol();assert p['status']=='FROZEN';assert p['main_order']==registered_order()[1]
    for f,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    for scene in p['scenes'].values():
        assert sha256_file(ROOT/scene['scenario'])==scene['scenario_sha256']
        assert sha256_file(scene['topomap'])==scene['topomap_sha256']
    return p
