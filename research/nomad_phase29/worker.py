"""Phase28-T process/immutable SDF transport, frozen Phase18 solver on CPU7."""
import argparse,json,os,time
from multiprocessing.connection import Listener
from pathlib import Path

def solve(job,field):
    from nomad_phase17.graph import ClearanceGraph
    from nomad_phase19r.evaluate import clean
    start=time.monotonic_ns()
    r=dict(job_id=job['job_id'],id=job['id'],worker_start_ns=start)
    try:
        graph=ClearanceGraph(job['path'],job['boundary'],job['previous_vw'],field,job['previous_xy'])
        poses,solver=graph.solve();r.update(accepted=bool(solver['feasible']),poses=poses.tolist(),solver=solver)
    except ValueError as exc:r.update(accepted=False,initialization_rejected=True,error=repr(exc))
    r['worker_end_ns']=time.monotonic_ns();return clean(r)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--socket',required=True);ap.add_argument('--cpu',type=int,default=7);ap.add_argument('--provenance',type=Path,required=True);a=ap.parse_args()
    from nomad_phase28t.affinity import pin
    affinity=pin([a.cpu]);assert affinity['passed'] and affinity['actual']==[7]
    import sys,numpy as np,scipy
    from multiprocessing import shared_memory,resource_tracker
    from types import MappingProxyType
    from nomad_phase15b.depth import Snapshot
    from nomad_phase17.graph import ClearanceGraph
    info=dict(pid=os.getpid(),python=sys.executable,numpy=np.__version__,scipy=scipy.__version__,numpy_file=str(Path(np.__file__).resolve()),scipy_file=str(Path(scipy.__file__).resolve()),affinity=affinity)
    a.provenance.write_text(json.dumps(info,indent=2)+'\n')
    token=bytes.fromhex(os.environ.pop('NOMAD_PHASE29_AUTH'));os.umask(0o077)
    with Listener(a.socket,family='AF_UNIX',authkey=token) as listener:
        with listener.accept() as con:
            con.send_bytes(json.dumps(info).encode())
            while True:
                payload=json.loads(con.recv_bytes())
                if payload.get('shutdown'):break
                blocks=[]
                try:
                    field=object.__new__(Snapshot)
                    for name,d in payload['arrays'].items():
                        block=shared_memory.SharedMemory(name=d['name']);blocks.append(block);resource_tracker.unregister(block._name,'shared_memory')
                        array=np.ndarray(d['shape'],dtype=d['dtype'],buffer=block.buf);array.flags.writeable=False;setattr(field,name,array)
                    for name,value in payload['field'].items():setattr(field,name,value)
                    field.origin=np.asarray(field.origin);field.metadata=MappingProxyType(field.metadata)
                    result=solve(payload['job'],field)
                except Exception as exc:result=dict(technical_error=repr(exc),job_id=payload['job']['job_id'])
                finally:
                    for b in blocks:b.close()
                con.send_bytes(json.dumps(result).encode())
    Path(a.socket).unlink(missing_ok=True)
if __name__=='__main__':main()
