"""Phase47 serial/resumable engine: 12 runs, no preparation-time driving."""
import inspect,subprocess
from types import FunctionType
from nomad_phase40r2 import campaign as frozen
from .config import ROOT,RUN_ROOT,protocol,verify

class Routes:
    def __getattr__(self,key):return getattr(subprocess,key)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase50p.launch','nomad_phase26.report':'nomad_phase50p.report'}.get(x,x) for x in args]
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)

def jobs(root):
    fn=frozen.jobs
    return FunctionType(fn.__code__,dict(fn.__globals__,protocol=protocol),fn.__name__)(root)

def main():
    source=inspect.getsource(frozen.main).replace('planned=20','planned=12').replace('from .metrics import audit','from nomad_phase50p.metrics import audit')
    ns=dict(frozen.main.__globals__,ROOT=ROOT,RUN_ROOT=RUN_ROOT,protocol=protocol,verify=verify,jobs=jobs,Routes=Routes)
    exec(compile(source,__file__,'exec'),ns);return ns['main']()

if __name__=='__main__':main()
