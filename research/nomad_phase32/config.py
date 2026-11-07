import json,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase29.config import runtime_config as frozen_config
HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase32';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase32_01'
METHODS=('C0-NA+EC','G18+EC');SCENES=('H1','H2','L2');INDICES=(201,202,203,204,205)
ORDER_SEED=20261107

def registered_order():
 rng=random.Random(ORDER_SEED);blocks=[];order=[]
 for i in INDICES:
  for s in SCENES:
   methods=list(METHODS);rng.shuffle(methods);blocks.append(dict(scene=s,index=i,methods=methods));order.extend(dict(scene=s,index=i,method=m) for m in methods)
 return blocks,order

def protocol():return json.loads((HERE/'protocol.json').read_text())
def verify():
 from nomad_phase29.config import verify as original
 original();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()[1]
 for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['historical_sources']}.items():assert sha256_file(ROOT/f)==h,f
 return p

def runtime_config(method,index,timeout=90,level='H1'):
 assert method in METHODS and index in INDICES and level in SCENES and timeout==90
 c=frozen_config(method.removesuffix('+EC'),index,timeout,level)
 c.update(phase32=True,phase32_method=method,phase32_index=index)
 return c
