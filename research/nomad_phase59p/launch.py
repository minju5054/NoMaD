"""Frozen process lifecycle; route HMM worker to the NET adapter only."""
import inspect
from nomad_phase35 import launch as base
from nomad_phase57p import launch as previous
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify
class Processes(previous.Processes):
    def __init__(self):super().__init__(hmm=True)
    def Popen(self,args,*a,**kw):
        args=['nomad_phase59p.worker' if x in ('nomad_isaac.worker','nomad_phase43p.worker') else x for x in args]
        return bind(previous.Processes.Popen,HERE=HERE)(self,args,*a,**kw)
source=inspect.getsource(previous.launcher_main).replace("phase='57-P'","phase='59-P'")
ns=dict(previous.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify)
exec(compile(source,__file__,'exec'),ns);launcher_main=ns['launcher_main']
def main():
    import sys
    assert '--smoke' not in sys.argv
    bind(base.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
