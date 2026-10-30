import os,time
from nomad_phase15b.depth import Snapshot
from nomad_phase19r.evaluate import clean
from .detour import ANGLES,select_detour
from .shadow import strict_snapshot
from .detour_known import solve_initialization

_file=None
_base=None
_strict=None

def solve_one(args):
    global _file,_base,_strict
    i,B,u,file=args;t=time.monotonic_ns()
    if _file!=file:
        _base=Snapshot.load(file);_strict=strict_snapshot(_base);_file=file
    r=solve_initialization(B,u,_base,_strict,ANGLES[i])
    if r.get('path') is not None:
        import numpy as np
        from nomad_phase15.evaluate import sample_path
        from nomad_phase20.repair import split_arclength
        near,far=split_arclength(np.array(r['path']))
        r['near_unknown_fraction']=_base.unknown_fraction(sample_path(near)[0])
        r['far_unknown_fraction']=_base.unknown_fraction(sample_path(far)[0]) if far is not None else None
    return clean(dict(initialization=i,angle_deg=ANGLES[i],pid=os.getpid(),start_ns=t,end_ns=time.monotonic_ns(),**r))

def solve_event(pool,event):
    start=time.perf_counter();results=list(pool.map(solve_one,[(i,event['B'],event['u_ref'],event['snapshot_file']) for i in range(7)]))
    return dict(results=results,selected=select_detour(results),seven_wall_s=time.perf_counter()-start)
