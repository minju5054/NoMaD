import copy,json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase47c.config import runtime_config as frozen_config,verify as verify47

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase51p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase51p_01'
METHODS=('OURS-DETOUR+HMM',);INDICES=(221,222);BASE_SCENES=('SLW','LC','L2','H1','H2');CONDITIONS=('L150','WIDE')
SCENES=tuple(f'{s}_{k}' for s in BASE_SCENES for k in CONDITIONS);ORDER_SEED=20261114

def protocol():return json.loads((HERE/'protocol.json').read_text())
def split(level):
    s,k=level.rsplit('_',1);assert s in BASE_SCENES and k in CONDITIONS
    return s,k

def registered_order():
    rng=random.Random(ORDER_SEED);order=[]
    for i in INDICES:
        for s in BASE_SCENES:
            conditions=list(CONDITIONS);rng.shuffle(conditions)
            order.extend(dict(scene=f'{s}_{k}',index=i,method=METHODS[0]) for k in conditions)
    return order

def runtime_config(method,index,timeout=90,level='H1_L150'):
    assert method==METHODS[0] and index in INDICES and timeout==90
    s,k=split(level);c=frozen_config(method,index,timeout,s)
    c.update(phase51p=True,phase51p_condition=k,phase51p_level=level,phase51p_delay_s=1.5 if k=='L150' else .75,run_id=f'{level}_{index}')
    if k=='WIDE' and 'dynamic_obstacle' in c:
        spec=copy.deepcopy(protocol()['wide'][s]);c['phase51p_wide']=spec
        c['dynamic_obstacle']['size_xyz_m'][spec['lateral_axis']]=spec['applied_width_m']
        c['phase38_jitter']=[dict(offset_m=0.,condition='WIDE_CENTERED') for _ in range(2 if s=='H2' else 1)]
        if s=='L2':c['blockage_center_y_m']=spec['centerline_m']
        else:
            c['phase26_spawn']['cross_axis_center_m']=spec['centerline_m']
            if s=='H2':c['phase26_spawn']['cross_axis_centers_m']=[spec['centerline_m']]*2
    return c

def verify():
    verify47();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
