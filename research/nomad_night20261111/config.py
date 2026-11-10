import json,os,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase40p.launch import bind
from nomad_phase53p.config import runtime_config as frozen_config,verify as verify53
HERE=Path(__file__).parent;EXP=os.environ.get('NOMAD_NIGHT_EXPERIMENT','E1')
QUEUE_ROOT=ROOT.parent/'artifacts/isaac6/night_queue_20261111_01';RESULTS=ROOT/'research/results/night20261111'
ORDER_SEED=20261117
BASE_SCENES=('SLW','LC','L2','H1','H2','H1-v2')
DEFS={
 'E1':dict(phase='E1_D075_R3',methods=['CUT','GRAPH-HO','OURS-R3'],scenes=[s+'_D075' for s in BASE_SCENES],indices=[225,226],smoke=dict(scene='LC_D075',method='OURS-R3',index=95)),
 'E2':dict(phase='Phase54-P',methods=['CUT-HOLD','GRAPH-HOLD'],scenes=[s+'_'+d for d in ('D075','D150') for s in BASE_SCENES],indices=[225,226],smoke=dict(scene='LC_D150',method='GRAPH-HOLD',index=95)),
 'E3':dict(phase='E3_D150_R3',methods=['CUT','GRAPH-HO','OURS-R3'],scenes=[s+'_D150' for s in BASE_SCENES],indices=[225,226],smoke=dict(scene='LC_D150',method='OURS-R3',index=95))}
assert EXP in DEFS
METHODS=tuple(DEFS[EXP]['methods']);SCENES=tuple(DEFS[EXP]['scenes']);RUN_ROOT=QUEUE_ROOT/EXP;SMOKE_ROOT=QUEUE_ROOT/'smoke'/EXP;OUT=RESULTS/EXP

def protocol(e=None):return json.loads((HERE/f'protocol_{e or EXP}.json').read_text())
def split(level):return level.rsplit('_',1)
def registered_order(e):
    d=DEFS[e];rng=random.Random(ORDER_SEED);rows=[]
    for index in d['indices']:
        for scene in d['scenes']:
            methods=list(d['methods']);rng.shuffle(methods);rows.extend(dict(scene=scene,index=index,method=m) for m in methods)
    return rows

def runtime_config(method,index,timeout=90,level=None):
    d=DEFS[EXP];assert timeout==90 and method in d['methods'] and level in d['scenes']
    assert index in d['indices'] or dict(scene=level,method=method,index=index)==d['smoke']
    scene,condition=split(level);base_scene='H1' if scene=='H1-v2' else scene
    underlying='GRAPH-HO' if method in ('GRAPH-HO','GRAPH-HOLD') else 'CUT'
    c=bind(frozen_config,INDICES=tuple(d['indices'])+(95,))(underlying,index,90,base_scene+'_'+condition)
    c['phase38_jitter']=protocol()['placements'].get(f'{base_scene}_{index}',[])
    if scene=='H1-v2':
        from nomad_h1v2.scene import configure
        c=configure(c)
    if method=='OURS-R3':c['phase38_method']='OURS'
    c.update(night_experiment=EXP,night_method=method,night_level=level,run_id=f'{EXP}_{level}_{index}_{method}')
    return c

def verify(e=None):
    e=e or EXP;verify53();p=protocol(e);assert p['status']=='FROZEN' and p['main_order']==registered_order(e)
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
