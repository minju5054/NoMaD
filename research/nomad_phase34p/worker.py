"""Change only the subprocess entry point so both arms read compact maps."""
import subprocess
from types import FunctionType
from nomad_phase20d.worker import Worker as FrozenWorker

class Processes:
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,args,*a,**kw):
        args=['nomad_phase34p.pool' if x=='nomad_phase20d.pool' else x for x in args]
        return subprocess.Popen(args,*a,**kw)

class Worker(FrozenWorker):
    __init__=FunctionType(FrozenWorker.__init__.__code__,dict(FrozenWorker.__init__.__globals__,subprocess=Processes()),FrozenWorker.__init__.__name__,FrozenWorker.__init__.__defaults__,FrozenWorker.__init__.__closure__)
