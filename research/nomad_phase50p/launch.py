"""Frozen launcher/process isolation; HMM worker and local scenario routing."""
import inspect,sys
from nomad_phase47c import launch as frozen
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify

class Processes(frozen.Processes):
    def __init__(self):super().__init__(hmm=True)
    def Popen(self,args,*a,**kw):
        args=['nomad_phase43p.worker' if x=='nomad_isaac.worker' else x for x in args]
        return bind(frozen.frozen.Processes.Popen,HERE=HERE)(self,args,*a,**kw)

def launcher_main(processes):
    source=inspect.getsource(frozen.launcher_main)
    source=source.replace("phase='47-C'","phase='50-P'")
    ns=dict(frozen.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify)
    exec(compile(source,str(HERE/'launch.py'),'exec'),ns)
    return ns['launcher_main'](processes)

def main():
    assert '--smoke' not in sys.argv
    bind(frozen.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()

if __name__=='__main__':main()
