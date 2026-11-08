"""Frozen job timing envelope, warmed four-process pool, local scratch caches."""
import inspect,os,time
from nomad_phase20d import pool as frozen
from nomad_phase33p.storage import install
from nomad_phase20d.recent import RecentSnapshot,load_cache
from nomad_phase19r.evaluate import clean
from .solver import solve

_key=None;_base=None;_strict=None
def initialize(queue):install();queue.put(os.getpid())

def solve_one(args):
    global _key,_base,_strict
    kind,index,job,file=args;started=time.monotonic_ns();key=(kind,file,job['variant'])
    if key!=_key:
        if kind=='R3':_base,_strict=load_cache(file)
        else:_base=RecentSnapshot.load(file);_strict=None
        _key=key
    r=solve(kind,index,job,_base,_strict)
    return clean(dict(index=index,pid=os.getpid(),start_ns=started,end_ns=time.monotonic_ns(),**r))

source=inspect.getsource(frozen.evaluate_job)
old="n=7 if kind=='R3' else 8"
assert source.count(old)==1
source=source.replace(old,"n=(7+len(job['extra_initializations']) if job['variant']=='V3' else 7) if kind=='R3' else 8")
namespace=dict(frozen.evaluate_job.__globals__,solve_one=solve_one)
exec(source,namespace)
variant_job=namespace['evaluate_job']

def evaluate_job(pool,job):
    return frozen.evaluate_job(pool,job) if job['variant']=='V0' else variant_job(pool,job)
