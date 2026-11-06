"""Exactly H1/C0-H/201 once; affinity only for this process and its descendants."""
import copy,json,os,subprocess,sys
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
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve()
    if out.exists():raise RuntimeError('Existing smoke preserved; no automatic repeat/retry')
    affinity=plan();original_mask=set(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None;result=pin(affinity['driver_cpus']) if affinity['possible'] else dict(passed=False,reason=affinity['reason'])
    if affinity.get('worker_cpu') is not None:os.environ['NOMAD_PHASE28T_WORKER_CPU']=str(affinity['worker_cpu'])
    processes=Processes();base.subprocess=processes;base.METHODS=('C0-H',);base.SCENES=('H1',)
    verified={}
    def verify_for_base():
        registered=verify()  # Run every Phase28-T check before adapting anything.
        verified['protocol']=copy.deepcopy(registered)
        compatible=copy.deepcopy(registered);compatible['status']='FROZEN'
        return compatible
    base.verify=verify_for_base
    writer=base.write_json;atomic=base.atomic_json
    def provenance(path,value):
        if path.name=='provenance.json':
            value=dict(value,phase='28-T',smoke_excluded=True,campaign=False,affinity_plan=affinity,launcher_affinity=result,
                protocol=copy.deepcopy(verified['protocol']),launcher_compatibility=dict(
                    verification='nomad_phase28t.config.verify passed',original_status=verified['protocol']['status'],
                    base_launcher_status=value['protocol']['status'],adapted_fields=['status'],protocol_file_modified=False))
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
