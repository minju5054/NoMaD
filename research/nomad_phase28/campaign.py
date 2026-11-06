"""Phase26 locks, retries, capacity checks and resume; twenty new runs only."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase26 import campaign as base
from .config import protocol,verify,RUN_ROOT

class Routes:
    def __getattr__(self,n):return getattr(subprocess,n)
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase28.launch','nomad_phase26.report':'nomad_phase28.report'}.get(x,x) for x in args]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    root=a.run_root.resolve();assert root==RUN_ROOT.resolve()
    if a.status:
        r=base.status(root);r['planned']=20;print(json.dumps(r));return
    base.protocol=protocol;base.verify=verify;base.subprocess=Routes()
    capacity=base.capacity
    base.capacity=lambda root,plan:capacity(root,[dict(j,method='C0') for j in plan])
    if a.dry_run:
        p=verify();plan=base.jobs(root);print(json.dumps(dict(planned=len(plan),navigation_started=0,disk=base.capacity(root,plan))));return
    import nomad_phase26.metrics as metrics
    from .report import audit
    metrics.audit=audit
    # base.main requires an explicit run-root; add only when the default was used.
    import sys
    if '--run-root' not in sys.argv:sys.argv+=['--run-root',str(root)]
    base.main()

if __name__=='__main__':main()
