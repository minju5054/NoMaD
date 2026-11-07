"""Same Phase29 launcher, affinity and cleanup; private routing globals only."""
import subprocess
from pathlib import Path
from types import FunctionType
from nomad_phase29 import launch as base
from .config import HERE,verify,METHODS,SCENES,RUN_ROOT

class Processes(base.Processes):
    def Popen(self,args,*a,**kw):
        args=[str(HERE/'simulator.py') if str(x).endswith('/nomad_phase26/simulator.py') else x for x in args]
        p=subprocess.Popen(args,*a,**kw);self.children.append(p);return p

_main=FunctionType(base.main.__code__,dict(base.main.__globals__,HERE=HERE,verify=verify,METHODS=METHODS,SCENES=SCENES,RUN_ROOT=RUN_ROOT,Processes=Processes),base.main.__name__,base.main.__defaults__,base.main.__closure__)
def main():
    writer=base.base.write_json
    def provenance(path,value):
        if path.name=='provenance.json':value=dict(value,phase='30-R',base_phase='29',soft_clearance_target_m=.08,r2_soft_clearance_factor=False)
        return writer(path,value)
    base.base.write_json=provenance
    try:_main()
    finally:base.base.write_json=writer
if __name__=='__main__':main()
