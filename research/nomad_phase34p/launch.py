"""Frozen process launcher/cleanup; only routing and provenance differ."""
import subprocess,sys
from pathlib import Path
from types import FunctionType
from nomad_phase29 import launch as old
from .config import HERE,verify,METHODS,SCENES,RUN_ROOT

class Processes(old.Processes):
    def Popen(self,args,*a,**kw):
        args=[str(HERE/'simulator.py') if str(x).endswith('/nomad_phase26/simulator.py') else x for x in args]
        child=subprocess.Popen(args,*a,**kw);self.children.append(child);return child

_main=FunctionType(old.main.__code__,dict(old.main.__globals__,HERE=HERE,verify=verify,METHODS=METHODS,SCENES=SCENES,RUN_ROOT=RUN_ROOT,Processes=Processes),old.main.__name__,old.main.__defaults__,old.main.__closure__)

def main():
    assert '--smoke' not in sys.argv
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve();assert out.is_relative_to(RUN_ROOT.resolve()/'main')
    base=old.base;writer=base.write_json;atomic=base.atomic_json
    def provenance(path,value):
        if path.name=='provenance.json':value=dict(value,phase='34-P',storage_version=2,baseline='Phase32 C0-NA+EC',R2_bypass=value['method']==METHODS[1])
        return writer(path,value)
    def persistence(path,value,*a,**kw):
        if path.name=='storage_policy.json':value=dict(value,version='SDF_STORAGE_V2',sdf_values_stored=False,loader='nomad_storage_sdf.loader',derived_cache='frozen transient R3 transport unchanged')
        return atomic(path,value,*a,**kw)
    base.write_json=provenance;base.atomic_json=persistence
    try:return _main()
    finally:base.write_json=writer;base.atomic_json=atomic

if __name__=='__main__':main()
