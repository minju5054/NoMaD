"""One serial night at a time, original lock/resume/retry/atomic-state engine."""
import argparse,inspect,json,shutil,subprocess,sys
from pathlib import Path
from types import FunctionType
from nomad_phase26 import campaign as base
from .config import ROOT,RUN_ROOT,SMOKE_ROOT,SMOKE_METHODS,protocol,verify

class Routes:
    def __getattr__(self,key):return getattr(subprocess,key)
    @staticmethod
    def route(args):return [{'nomad_phase26.launch':'nomad_phase38.launch','nomad_phase26.report':'nomad_phase38.report'}.get(x,x) for x in args]
    def Popen(self,args,*a,**kw):return subprocess.Popen(self.route(args),*a,**kw)
    def run(self,args,*a,**kw):return subprocess.run(self.route(args),*a,**kw)

def capacity(root,jobs):
    free=shutil.disk_usage(ROOT).free
    return dict(free_bytes=free,required_free_bytes=30_000_000_000,enough=free>=30_000_000_000,
                remaining_runs=sum(not (root/'metrics'/(j['key']+'.json')).exists() for j in jobs))

def jobs(root,night=None,smoke=False):
    p=dict(protocol());p['main_order']=([dict(scene='H1',index=95,method=m) for m in SMOKE_METHODS] if smoke else
        [r for r in p['main_order'] if night is None or r['night']==night])
    original=base.jobs
    fn=FunctionType(original.__code__,dict(original.__globals__,protocol=lambda:p),original.__name__)
    return fn(root,False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--night',type=int,choices=(1,2));ap.add_argument('--smoke',action='store_true');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    assert not (a.smoke and a.night)
    root=SMOKE_ROOT if a.smoke else RUN_ROOT/f'night{a.night}' if a.night else RUN_ROOT
    if a.status:
        if a.smoke:r=base.status(root);r['planned']=4
        else:r={f'night{n}':dict(base.status(RUN_ROOT/f'night{n}'),planned=90) for n in (1,2)}
        print(json.dumps(r));return
    p=verify();plan=jobs(root,a.night,a.smoke)
    if a.dry_run:
        print(json.dumps(dict(planned=len(plan),jobs=plan,disk=capacity(root,plan),simulation_runs=0)));return
    assert a.smoke or a.night,'Choose one registered night'
    if a.night==2:assert (RUN_ROOT/'night1/complete.json').exists(),'Finish night1 before night2'
    from .metrics import audit
    import nomad_phase26.metrics as metrics
    metrics.audit=audit
    p=dict(p,main_order=[dict(scene=j['scene'],index=j['index'],method=j['method']) for j in plan])
    base.protocol=lambda:p;base.verify=lambda:(verify(),p)[1];base.capacity=capacity;base.subprocess=Routes()
    original_jobs=base.jobs
    local=FunctionType(original_jobs.__code__,dict(original_jobs.__globals__,protocol=lambda:p),original_jobs.__name__)
    base.jobs=lambda run,smoke=False:local(run,False)
    # The user authorizes one technical retry for this phase, including its
    # smoke command. Retain two attempts, but do not inherit Phase26's manual
    # smoke-retry token; check the30GB reserve before every smoke attempt too.
    source=inspect.getsource(base.run_job)
    assert source.count('if not smoke:')==1 and source.count("read(root/'allow_smoke_retry',{}).get('key')")==1
    source=source.replace('if not smoke:','if True:').replace("read(root/'allow_smoke_retry',{}).get('key')","job['key']")
    ns=dict(base.run_job.__globals__);exec(compile(source,__file__,'exec'),ns);base.run_job=ns['run_job']
    sys.argv=['campaign','--run-root',str(root),*(['--smoke-only'] if a.smoke else [])]
    base.main()
if __name__=='__main__':main()
