"""Exactly H1/C0-H/201 once; affinity only for this process and its descendants."""
import json,os,subprocess,sys
from pathlib import Path
from nomad_phase26 import launch as base
from nomad_phase28.storage import cleanup
from .config import HERE,verify
from .affinity import plan,pin

class Processes:
    def __init__(self):self.children=[]
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,args,*a,**kw):
        args=[str(HERE/'simulator.py') if str(x).endswith('/nomad_phase26/simulator.py') else x for x in args]
        p=subprocess.Popen(args,*a,**kw);self.children.append(p);return p

def main():
    assert '--smoke' not in sys.argv
    for name,value in [('--scene','H1'),('--method','C0-H'),('--index','201')]:assert sys.argv[sys.argv.index(name)+1]==value
    affinity=plan();original_mask=set(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None;result=pin(affinity['driver_cpus']) if affinity['possible'] else dict(passed=False,reason=affinity['reason'])
    if affinity.get('worker_cpu') is not None:os.environ['NOMAD_PHASE28T_WORKER_CPU']=str(affinity['worker_cpu'])
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve();processes=Processes();base.subprocess=processes;base.verify=verify;base.METHODS=('C0-H',);base.SCENES=('H1',)
    writer=base.write_json;atomic=base.atomic_json
    def provenance(path,value):
        if path.name=='provenance.json':value=dict(value,phase='28-T',smoke_excluded=True,campaign=False,affinity_plan=affinity,launcher_affinity=result)
        return writer(path,value)
    def marked(path,value):
        if path.name=='launch_complete.json':value=dict(value,smoke_excluded=True,campaign=False)
        return atomic(path,value)
    base.write_json=provenance;base.atomic_json=marked
    try:base.main()
    finally:
        if out.exists():
            (out/'phase28t_affinity.json').write_text(json.dumps(dict(plan=affinity,launcher=result),indent=2)+'\n')
            if all(p.poll() is not None for p in processes.children):cleanup(out,True,True)
        try:
            if original_mask is not None:os.sched_setaffinity(0,original_mask)
        except (OSError,AttributeError):pass

if __name__=='__main__':main()
