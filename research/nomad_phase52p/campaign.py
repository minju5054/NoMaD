import inspect,subprocess
from types import FunctionType
from nomad_phase40r2 import campaign as frozen
from .config import ROOT,RUN_ROOT,protocol,verify

class Routes:
    def __getattr__(self,key):return getattr(subprocess,key)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase52p.launch','nomad_phase26.report':'nomad_phase52p.report'}.get(x,x) for x in args]
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)

def jobs(root):
    fn=frozen.jobs
    return FunctionType(fn.__code__,dict(fn.__globals__,protocol=protocol),fn.__name__)(root)

def run_with_audit_gate(base):
    """Called only for actual resume, inside the inherited global campaign lock."""
    original=base.campaign
    def guarded(root,smoke=False):
        assert not smoke
        from .resume import audit_gate
        audit_gate(root)
        return original(root,False)
    base.campaign=guarded
    try:return base.main()
    finally:base.campaign=original

def main():
    source=inspect.getsource(frozen.main).replace('planned=20','planned=40').replace('from .metrics import audit','from nomad_phase52p.metrics import audit').replace('    base.main()','    run_with_audit_gate(base)')
    ns=dict(frozen.main.__globals__,ROOT=ROOT,RUN_ROOT=RUN_ROOT,protocol=protocol,verify=verify,jobs=jobs,Routes=Routes,run_with_audit_gate=run_with_audit_gate)
    exec(compile(source,__file__,'exec'),ns);return ns['main']()

if __name__=='__main__':main()
