"""Frozen launcher, isolated worker core, short socket and post-run cleanup."""
import json,os,subprocess,sys
from pathlib import Path
from nomad_phase26 import launch as base
from nomad_phase28.storage import cleanup
from nomad_phase28t.affinity import plan,pin
from .config import HERE,verify,METHODS,SCENES,RUN_ROOT
class Processes:
    def __init__(self):self.children=[]
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,args,*a,**kw):
        args=[str(HERE/'simulator.py') if str(x).endswith('/nomad_phase26/simulator.py') else x for x in args]
        p=subprocess.Popen(args,*a,**kw);self.children.append(p);return p
def main():
    assert '--smoke' not in sys.argv
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve();assert out.is_relative_to(RUN_ROOT.resolve()) and not out.exists()
    affinity=plan();assert affinity['possible'] and affinity['worker_cpu']==7
    original=set(os.sched_getaffinity(0));mask=pin(affinity['driver_cpus']);assert mask['passed']
    child=Processes();base.subprocess=child;base.verify=verify;base.METHODS=METHODS;base.SCENES=SCENES;writer=base.write_json
    def provenance(p,r):
        if p.name=='provenance.json':r=dict(r,phase='29',smoke_excluded='smoke' in out.parts,affinity=mask)
        return writer(p,r)
    base.write_json=provenance
    try:base.main()
    finally:
        if out.exists() and all(p.poll() is not None for p in child.children):cleanup(out,True,True)
        os.sched_setaffinity(0,original)
if __name__=='__main__':main()
