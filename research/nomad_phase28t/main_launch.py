"""Campaign-only routing; same T execution, affinity, short socket and cleanup."""
import json,os,subprocess,sys
from pathlib import Path
from nomad_phase26 import launch as base
from nomad_phase28.storage import cleanup
from .main_config import HERE,verify,METHODS,SCENES,RUN_ROOT
from .affinity import plan,pin

class Processes:
    def __init__(self):self.children=[]
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,args,*a,**kw):
        args=[str(HERE/'main_simulator.py') if str(x).endswith('/nomad_phase26/simulator.py') else x for x in args]
        p=subprocess.Popen(args,*a,**kw);self.children.append(p);return p

def main():
    assert '--smoke' not in sys.argv
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve()
    assert out.is_relative_to(RUN_ROOT.resolve()/'main')
    if out.exists():raise RuntimeError('Existing run preserved')
    affinity=plan();original=set(os.sched_getaffinity(0));mask=pin(affinity['driver_cpus']) if affinity['possible'] else dict(passed=False,reason=affinity['reason'])
    if affinity.get('worker_cpu') is not None:os.environ['NOMAD_PHASE28T_WORKER_CPU']=str(affinity['worker_cpu'])
    processes=Processes();base.subprocess=processes;base.verify=verify;base.METHODS=METHODS;base.SCENES=SCENES
    writer=base.write_json
    def provenance(path,value):
        if path.name=='provenance.json':value=dict(value,phase='28-T',campaign=True,smoke_excluded=False,affinity_plan=affinity,launcher_affinity=mask)
        return writer(path,value)
    base.write_json=provenance
    try:base.main()
    finally:
        if out.exists():
            (out/'phase28t_affinity.json').write_text(json.dumps(dict(plan=affinity,launcher=mask),indent=2)+'\n')
            if all(p.poll() is not None for p in processes.children):cleanup(out,True,True)
        os.sched_setaffinity(0,original)

if __name__=='__main__':main()
