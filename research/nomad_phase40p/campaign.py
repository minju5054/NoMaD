"""One smoke then20 paired blocks; no run is started by preparation/dry-run."""
import argparse
import inspect
import json
import shutil
import subprocess
import sys
from types import FunctionType
from nomad_phase26 import campaign as base
from .config import ROOT,RUN_ROOT,SMOKE_ROOT,protocol,verify


class Routes:
    def __getattr__(self,key):return getattr(subprocess,key)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase40p.launch','nomad_phase26.report':'nomad_phase40p.report'}.get(x,x) for x in args]
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)


def capacity(root,jobs):
    free=shutil.disk_usage(ROOT).free
    return dict(free_bytes=free,required_free_bytes=30_000_000_000,enough=free>=30_000_000_000,
                remaining_runs=sum(not (root/'metrics'/(j['key']+'.json')).exists() for j in jobs))


def jobs(root,smoke=False):
    p=dict(protocol())
    if smoke:p['main_order']=[dict(scene='H1',index=217,method='OURS-N')]
    fn=base.jobs
    return FunctionType(fn.__code__,dict(fn.__globals__,protocol=lambda:p),fn.__name__)(root,False)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');ap.add_argument('--with-smoke',action='store_true');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    assert not (a.smoke and a.with_smoke)
    root=SMOKE_ROOT if a.smoke else RUN_ROOT
    if a.status:
        print(json.dumps(dict(main=dict(base.status(RUN_ROOT),planned=20),smoke=dict(base.status(SMOKE_ROOT),planned=1))));return
    p=verify();plan=jobs(root,a.smoke)
    if a.dry_run:
        print(json.dumps(dict(planned=len(plan),jobs=plan,smoke_first=a.with_smoke,disk=capacity(root,plan),simulations_started=0)));return
    if a.with_smoke and not (SMOKE_ROOT/'complete.json').exists():
        # A fresh Python process keeps the inherited campaign's local bindings
        # isolated. Its one smoke attempt must finish before any main launch.
        from nomad_phase26.launch import environment
        print('[smoke] H1_217_OURS-N start before main',flush=True)
        subprocess.run(['/usr/bin/python3','-u','-m','nomad_phase40p.campaign','--smoke'],cwd=ROOT,env=environment(),check=True)
    if not a.smoke:
        assert (SMOKE_ROOT/'complete.json').exists(),'Run the single registered smoke before main'
        metrics=[json.loads(f.read_text()) for f in (SMOKE_ROOT/'metrics').glob('*.json')]
        assert len(metrics)==1 and metrics[0]['technical_validation']=='PASS'
    from .metrics import audit
    import nomad_phase26.metrics as metrics
    metrics.audit=audit
    p=dict(p,main_order=[dict(scene=j['scene'],index=j['index'],method=j['method']) for j in plan])
    original_jobs=base.jobs
    base.protocol=lambda:p;base.verify=lambda:(verify(),p)[1];base.capacity=capacity;base.subprocess=Routes()
    local=FunctionType(original_jobs.__code__,dict(original_jobs.__globals__,protocol=lambda:p),original_jobs.__name__)
    base.jobs=lambda run,smoke=False:local(run,False)
    # One smoke attempt, no automatic rerun. Main inherits one technical retry.
    source=inspect.getsource(base.run_job)
    source=source.replace('if not smoke:','if True:')
    ns=dict(base.run_job.__globals__);exec(compile(source,__file__,'exec'),ns)
    base.run_job=ns['run_job']
    if a.smoke:
        plan[0]['outputs']=plan[0]['outputs'][:1]
        base.jobs=lambda run,smoke=False:plan
    sys.argv=['campaign','--run-root',str(root),*(['--smoke-only'] if a.smoke else [])]
    base.main()


if __name__=='__main__':main()
