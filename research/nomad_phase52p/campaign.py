import ast,inspect,json,subprocess
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
    # The live Phase26 binding becomes a closure after campaign setup. Avoid
    # the older Phase40 wrapper which itself copies that binding without cells.
    from nomad_phase26.campaign import jobs as fn
    return FunctionType(fn.__code__,dict(fn.__globals__,protocol=protocol),fn.__name__,
                        fn.__defaults__,fn.__closure__)(root,False)

def run_with_audit_gate(base,dry_run=False):
    """Exercise identical setup and saved-data gate for dry-run and resume."""
    original=base.campaign
    def guarded(root,smoke=False):
        assert not smoke
        from .resume import audit_gate
        gate=audit_gate(root)
        if dry_run:
            plan=jobs(root)
            pending=[j['key'] for j in plan if not (root/'metrics'/(j['key']+'.json')).exists()]
            print(json.dumps(dict(planned=len(plan),jobs=plan,audit_gate=gate['status'],
                audited_attempt1_keys=gate['checked'],audited_attempt1_count=len(gate['checked']),
                actual_jobs_closure_cells=len(base.jobs.__closure__ or ()),remaining=len(pending),
                next_key=pending[0] if pending else None,simulations_started=0,smoke=False)))
            return
        return original(root,False)
    base.campaign=guarded
    try:return base.main()
    finally:base.campaign=original

def main():
    source=inspect.getsource(frozen.main).replace('planned=20','planned=40').replace('from .metrics import audit','from nomad_phase52p.metrics import audit').replace('    base.main()','    run_with_audit_gate(base,dry_run=a.dry_run)')
    source=source.replace('original.__name__)', 'original.__name__,original.__defaults__,original.__closure__)')
    tree=ast.parse(source)
    class FullDryRun(ast.NodeTransformer):
        count=0
        def visit_If(self,node):
            if ast.unparse(node.test)=='a.dry_run':
                self.count+=1
                return ast.copy_location(ast.Pass(),node)
            return self.generic_visit(node)
    visitor=FullDryRun();tree=visitor.visit(tree);assert visitor.count==1
    ns=dict(frozen.main.__globals__,ROOT=ROOT,RUN_ROOT=RUN_ROOT,protocol=protocol,verify=verify,jobs=jobs,Routes=Routes,run_with_audit_gate=run_with_audit_gate)
    exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),ns);return ns['main']()

if __name__=='__main__':main()
