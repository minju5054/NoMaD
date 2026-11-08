"""Resume/lock/retry/report envelope reused; never starts from preparation."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from nomad_phase26 import campaign as base
from .config import ROOT,RUN_ROOT,protocol,verify

class Routes:
    def __getattr__(self,name):return getattr(subprocess,name)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase37p.launch','nomad_phase26.report':'nomad_phase37p.report'}.get(x,x) for x in args]
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)

def capacity(root,plan):
    pending=[j for j in plan if not (root/'metrics'/(j['key']+'.json')).exists()];free=shutil.disk_usage(ROOT).free
    return dict(remaining_runs=len(pending),free_bytes=free,required_free_bytes=30_000_000_000,enough=free>=30_000_000_000)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args();root=a.run_root.resolve();assert root==RUN_ROOT.resolve()
    if a.status:
        result=base.status(root);result['planned']=20;print(json.dumps(result));return
    base.protocol=protocol;base.verify=verify;base.subprocess=Routes();base.capacity=capacity
    if a.dry_run:
        p=verify();jobs=base.jobs(root);print(json.dumps(dict(planned=len(jobs),order=p['main_order'],disk=capacity(root,jobs),navigation_started=0)));return
    import nomad_phase26.metrics as metrics
    from .metrics import audit
    metrics.audit=audit
    if '--run-root' not in sys.argv:sys.argv+=['--run-root',str(root)]
    base.main()
if __name__=='__main__':main()
