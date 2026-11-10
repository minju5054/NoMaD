"""Reuse Phase35 four-process R2 pool/bootstrap/storage; no R3/strict map."""
import time
from types import FunctionType
from nomad_phase20d import pool as frozen
from nomad_phase33p.storage import install
from nomad_phase20d.recent import RecentSnapshot
from nomad_phase19r.evaluate import clean
from .graph import solve_sample,select

_key=None;_field=None

def initialize(q):install();frozen.initialize(q)
def solve_one(args):
    global _key,_field
    index,job=args;start=time.monotonic_ns();file=job['snapshot_file']
    if file!=_key:_field=RecentSnapshot.load(file);_key=file
    result=solve_sample(job['samples_world'][index],job['B'],_field,job['old_path'])
    return clean(dict(index=index,start_ns=start,end_ns=time.monotonic_ns(),**result))
def evaluate_job(pool,job):
    begin=time.monotonic_ns();results=list(pool.map(solve_one,[(i,job) for i in range(8)]));end=time.monotonic_ns()
    return dict(job_id=job['job_id'],kind='REC',start_ns=begin,end_ns=end,results=results,selected_sample=select(results),
        pool_wall_s=(end-begin)/1e9,dispatch_to_complete_s=(end-job['dispatch_ns'])/1e9,
        sample_solve_s=[r['attempt_wall_s'] for r in results])
def main():
    install();fn=frozen.main
    FunctionType(fn.__code__,dict(fn.__globals__,initialize=initialize,evaluate_job=evaluate_job),fn.__name__,fn.__defaults__,fn.__closure__)()
if __name__=='__main__':main()
