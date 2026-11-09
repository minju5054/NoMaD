"""Locked Topomap preparation then the frozen serial six-run campaign."""
import argparse,json,subprocess,sys
from types import FunctionType
from nomad_phase40r2 import campaign as frozen
from nomad_phase40p.campaign import capacity
from nomad_phase0.s0_batch import exclusive_batch
from .config import ROOT,RUN_ROOT,protocol,verify


class Routes:
    def __getattr__(self,key):return getattr(subprocess,key)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase44p.launch','nomad_phase26.report':'nomad_phase44p.report'}.get(x,x) for x in args]
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)


def jobs(root):
    fn=frozen.jobs
    return FunctionType(fn.__code__,dict(fn.__globals__,protocol=protocol),fn.__name__)(root)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    if a.status:
        from .topomaps import status
        print(json.dumps(dict(topomap=status(),
                              main=dict(frozen.base.status(RUN_ROOT),planned=6))));return
    p=verify();plan=jobs(RUN_ROOT)
    if a.dry_run:
        print(json.dumps(dict(planned=6,jobs=plan,topomap_scenes=['L2','H2'],render_started=0,simulations_started=0,disk=capacity(RUN_ROOT,plan))));return
    with exclusive_batch():
        assert capacity(RUN_ROOT,plan)['enough'],'Disk below30GB; no renderer or run started'
        from .topomaps import ensure
        ensure();p=verify(require_maps=True)
        from .metrics import audit
        import nomad_phase26.metrics as metrics
        metrics.audit=audit;base=frozen.base;original=base.jobs
        base.protocol=lambda:p;base.verify=lambda:verify(require_maps=True);base.capacity=capacity;base.subprocess=Routes()
        local=FunctionType(original.__code__,dict(original.__globals__,protocol=lambda:p),original.__name__)
        base.jobs=lambda root,smoke=False:local(root,False)
        # Lock already covers both preparation and driving: do not reacquire.
        base.campaign(RUN_ROOT,False)


if __name__=='__main__':main()
