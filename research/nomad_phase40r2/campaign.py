"""Reuse locked/resumable Phase40-P engine; skip smoke entirely."""
import argparse,json,subprocess,sys
from types import FunctionType
from nomad_phase26 import campaign as base
from nomad_phase40p.campaign import capacity
from .config import ROOT,RUN_ROOT,protocol,verify


class Routes:
    def __getattr__(self,key):return getattr(subprocess,key)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase40r2.launch','nomad_phase26.report':'nomad_phase40r2.report'}.get(x,x) for x in args]
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)


def jobs(root):
    fn=base.jobs
    return FunctionType(fn.__code__,dict(fn.__globals__,protocol=protocol),fn.__name__)(root,False)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(dict(base.status(RUN_ROOT),planned=20)));return
    p=verify();plan=jobs(RUN_ROOT)
    if a.dry_run:
        print(json.dumps(dict(planned=len(plan),jobs=plan,smoke=False,disk=capacity(RUN_ROOT,plan),simulations_started=0)));return
    from .metrics import audit
    import nomad_phase26.metrics as metrics
    metrics.audit=audit
    original=base.jobs
    base.protocol=lambda:p;base.verify=lambda:(verify(),p)[1];base.capacity=capacity;base.subprocess=Routes()
    local=FunctionType(original.__code__,dict(original.__globals__,protocol=lambda:p),original.__name__)
    base.jobs=lambda root,smoke=False:local(root,False)
    sys.argv=['campaign','--run-root',str(RUN_ROOT)]
    base.main()


if __name__=='__main__':main()
