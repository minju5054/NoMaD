"""Thirty locked, serial, resumable jobs; at most one technical retry."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from nomad_phase26 import campaign as base
from .config import ROOT,RUN_ROOT,protocol,verify

class Routes:
    def __getattr__(self,name):return getattr(subprocess,name)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase31p.launch','nomad_phase26.report':'nomad_phase31p.report'}.get(x,x) for x in args]
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)

def capacity(root,plan):
    p=protocol();pending=[j for j in plan if not (root/'metrics'/(j['key']+'.json')).exists()]
    sizes={(r['scene'],r['method']):r['estimated_bytes_per_run'] for r in p['storage_estimates']}
    expected=sum(sizes[(j['scene'],j['method'])] for j in pending);free=shutil.disk_usage(ROOT).free
    return dict(remaining_runs=len(pending),free_bytes=free,required_free_bytes=30_000_000_000,enough=free>=30_000_000_000,
        expected_remaining_bytes=expected,projected_free_after_remaining_bytes=free-expected,
        estimated_full_with_reserve_bytes=expected+30_000_000_000,
        estimated_full_with_reserve_enough=free>=expected+30_000_000_000,
        policy='Only the fixed30GB minimum starts/stops each run; storage estimate is descriptive')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    root=a.run_root.resolve();assert root==RUN_ROOT.resolve()
    if a.status:
        r=base.status(root);r['planned']=30;print(json.dumps(r));return
    base.protocol=protocol;base.verify=verify;base.subprocess=Routes();base.capacity=capacity
    if a.dry_run:
        p=verify();jobs=base.jobs(root);print(json.dumps(dict(planned=len(jobs),blocks=p['blocks'],navigation_started=0,disk=capacity(root,jobs))));return
    import nomad_phase26.metrics as metrics
    from .report import audit
    metrics.audit=audit
    if '--run-root' not in sys.argv:sys.argv+=['--run-root',str(root)]
    base.main()
if __name__=='__main__':main()
