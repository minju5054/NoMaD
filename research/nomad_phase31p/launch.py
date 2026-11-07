"""Reuse each method's frozen launcher policy; only route new registration/paths."""
import subprocess,sys
from pathlib import Path
from types import FunctionType
from nomad_phase29 import launch as base
from nomad_phase27r import launch as c0_launch
from nomad_phase28 import launch as na_launch
from nomad_phase28.storage import cleanup
from .config import HERE,verify,METHODS,SCENES,RUN_ROOT

class Processes(base.Processes):
    def Popen(self,args,*a,**kw):
        args=[str(HERE/'simulator.py') if str(x).endswith('/nomad_phase26/simulator.py') else x for x in args]
        child=subprocess.Popen(args,*a,**kw);self.children.append(child);return child

def routed(fn):
    return FunctionType(fn.__code__,dict(fn.__globals__,HERE=HERE,verify=verify,METHODS=METHODS,SCENES=SCENES,RUN_ROOT=RUN_ROOT,Processes=Processes),fn.__name__,fn.__defaults__,fn.__closure__)
LAUNCHERS={'G18-R':routed(base.main),'C0':routed(c0_launch.main),'C0-NA':routed(na_launch.main)}

def main():
    assert '--smoke' not in sys.argv
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve()
    method=sys.argv[sys.argv.index('--method')+1]
    assert method in METHODS and out.is_relative_to(RUN_ROOT.resolve()/'main') and not out.exists()
    processes=Processes();base.base.subprocess=processes;base.base.METHODS=METHODS;base.base.SCENES=SCENES
    writer=base.base.write_json
    def provenance(path,value):
        if path.name=='provenance.json':
            sources={'G18-R':'Phase30-R','C0':'Phase27-R','C0-NA':'Phase28'}
            value=dict(value,phase='31-P',frozen_method_source=sources[value['method']],smoke_excluded=False)
        return writer(path,value)
    base.base.write_json=provenance
    try:LAUNCHERS[method]()
    finally:
        base.base.write_json=writer
        # C0's old launcher predates this cleanup; reuse the same approved
        # cleanup function, after both children finish, without touching raw.
        if method=='C0' and out.exists() and all(p.poll() is not None for p in processes.children):cleanup(out,True,True)
if __name__=='__main__':main()
