"""Original launcher, new executor entry point, cleanup after both children exit."""
import json,subprocess,sys
from pathlib import Path
from nomad_phase26 import launch as base
from .config import verify,METHODS,HERE
from .storage import cleanup

class Processes:
    def __init__(self):self.children=[]
    def __getattr__(self,n):return getattr(subprocess,n)
    def Popen(self,args,*a,**kw):
        args=[str(HERE/'simulator.py') if str(x).endswith('/nomad_phase26/simulator.py') else x for x in args]
        p=subprocess.Popen(args,*a,**kw);self.children.append(p);return p

def main():
    base.verify=verify;base.METHODS=METHODS;processes=Processes();base.subprocess=processes
    write=base.write_json
    def provenance(p,r):
        if p.name=='provenance.json':r=dict(r,phase='28',base_phase='27-R',cleanup_enabled=True)
        return write(p,r)
    base.write_json=provenance
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve()
    try:base.main()
    finally:
        if out.exists():
            if all(p.poll() is not None for p in processes.children):cleanup(out,True,enabled=True)
            else:(out/'phase28_cleanup.json').write_text(json.dumps(dict(enabled=True,skipped='CHILD_STILL_RUNNING'))+'\n')

if __name__=='__main__':main()
