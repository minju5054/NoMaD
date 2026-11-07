"""Frozen launcher with method-name/entry-point/metadata wiring only."""
import inspect,os,subprocess,sys
from pathlib import Path
from nomad_phase26 import launch as base
from nomad_phase28.storage import cleanup
from nomad_phase28t.affinity import plan,pin
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify

class Processes:
    def __init__(self):self.children=[]
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,args,*a,**kw):
        args=[str(HERE/'simulator.py') if str(x).endswith('/nomad_phase26/simulator.py') else x for x in args]
        child=subprocess.Popen(args,*a,**kw);self.children.append(child);return child

def launcher_main(processes):
    # The only semantic string substitution is the equivalent RTC method tag.
    source=inspect.getsource(base.main);assert source.count("a.method=='B2_SAFE_RTC'")==2
    source=source.replace("a.method=='B2_SAFE_RTC'","a.method=='SAFE_RTC'")
    def write(path,value):
        if path.name=='provenance.json':value=dict(value,phase='35',storage_version=2,executor='C0-NA',protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
        return base.write_json(path,value)
    def atomic(path,value,*a,**kw):
        if path.name=='storage_policy.json':value=dict(value,version='SDF_STORAGE_V2',sdf_values_stored=False,loader='nomad_storage_sdf.loader',derived_cache='frozen ephemeral R3 cache unchanged')
        return base.atomic_json(path,value,*a,**kw)
    namespace=dict(base.main.__globals__,METHODS=METHODS,SCENES=SCENES,verify=verify,
                   subprocess=processes,write_json=write,atomic_json=atomic)
    exec(compile(source,str(HERE/'launch.py'),'exec'),namespace)
    return namespace['main']

def main():
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve()
    assert out.is_relative_to(RUN_ROOT.resolve()) and not out.exists()
    affinity=plan();assert affinity['possible'];original=set(os.sched_getaffinity(0))
    result=pin(affinity['driver_cpus']);assert result['passed']
    processes=Processes()
    try:launcher_main(processes)()
    finally:
        if out.exists() and all(p.poll() is not None for p in processes.children):cleanup(out,True,True)
        os.sched_setaffinity(0,original)
if __name__=='__main__':main()
