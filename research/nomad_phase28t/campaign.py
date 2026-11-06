"""Phase26 locking/resume/disk/retry/report; only ten new C0-H jobs."""
import argparse,json,subprocess,sys
from pathlib import Path
from nomad_phase26 import campaign as base
from nomad_phase26.storage import measure_storage,HEADROOM_BYTES
from nomad_phase28.report import audit
from .main_config import protocol,verify,RUN_ROOT

class Routes:
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase28t.main_launch','nomad_phase26.report':'nomad_phase28t.drive_report'}.get(x,x) for x in args]

ORIGINAL_CAPACITY=base.capacity
def capacity(root,plan):
    # Keep the larger of the inherited estimate and observed T smoke bytes.
    result=ORIGINAL_CAPACITY(root,[dict(j,method='C0') for j in plan])
    p=protocol();measured=p['storage_estimate'];pending=[j for j in plan if not (root/'metrics'/(j['key']+'.json')).exists()]
    expected=sum(measured['bytes'] if j['index']==201 else measured['thin_projected_bytes'] for j in pending)
    result['expected_remaining_bytes']=max(result['expected_remaining_bytes'],expected)
    result['required_free_bytes']=result['expected_remaining_bytes']+HEADROOM_BYTES
    result['enough']=result['free_bytes']>=result['required_free_bytes'];result['phase28t_smoke_estimate_bytes']=expected
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    root=a.run_root.resolve();assert root==RUN_ROOT.resolve()
    if a.status:
        r=base.status(root);r['planned']=10;print(json.dumps(r));return
    base.protocol=protocol;base.verify=verify;base.subprocess=Routes();base.capacity=capacity
    if a.dry_run:
        verify();plan=base.jobs(root);print(json.dumps(dict(planned=len(plan),navigation_started=0,disk=capacity(root,plan))));return
    import nomad_phase26.metrics as metrics
    metrics.audit=audit
    if '--run-root' not in sys.argv:sys.argv+=['--run-root',str(root)]
    base.main()

if __name__=='__main__':main()
