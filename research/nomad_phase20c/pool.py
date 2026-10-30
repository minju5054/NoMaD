"""Seven fixed initializations in four CPU processes; immutable saved depth input."""
import os,time
from nomad_phase15b.depth import Snapshot
from nomad_phase19r.evaluate import clean
from .detour import ANGLES,solve_initialization,select_detour

_field=None
_file=None
def initialize(ready):ready.put(os.getpid())
def ping():return os.getpid()

def solve_one(args):
    global _field,_file
    i,B,u,file=args;t=time.monotonic_ns()
    if file!=_file:_field=Snapshot.load(file);_file=file
    r=solve_initialization(B,u,_field,ANGLES[i])
    return clean(dict(initialization=i,angle_deg=ANGLES[i],pid=os.getpid(),start_ns=t,end_ns=time.monotonic_ns(),**r))

def solve_event(pool,event):
    start=time.perf_counter();ns=time.monotonic_ns()
    results=list(pool.map(solve_one,[(i,event['B'],event['u_ref'],event['snapshot_file']) for i in range(7)]))
    assert [r['initialization'] for r in results]==list(range(7))
    return dict(results=results,selected=select_detour(results),seven_wall_s=time.perf_counter()-start,dispatch_ns=ns,end_ns=time.monotonic_ns())
