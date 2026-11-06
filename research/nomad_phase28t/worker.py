"""Pure numerical child, same Python/NumPy/SciPy as its parent; no Kit import."""
import argparse,json,os,time
from multiprocessing.connection import Listener
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--socket',required=True);ap.add_argument('--cpu',type=int);ap.add_argument('--provenance',type=Path,required=True);a=ap.parse_args()
    from .affinity import pin
    affinity=pin([a.cpu]) if a.cpu is not None else dict(passed=False,reason='NO_ISOLATED_CORE_SELECTED',actual=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None)
    # Pin before loading numerical libraries; parent library paths are inherited.
    import sys,numpy as np,scipy
    from multiprocessing import shared_memory,resource_tracker
    from types import MappingProxyType
    from nomad_phase15b.depth import Snapshot
    from .timing import solve
    info=dict(pid=os.getpid(),python=sys.executable,numpy=np.__version__,scipy=scipy.__version__,numpy_file=str(Path(np.__file__).resolve()),scipy_file=str(Path(scipy.__file__).resolve()),affinity=affinity,ready_ns=time.perf_counter_ns())
    a.provenance.write_text(json.dumps(info,indent=2)+'\n')
    token=bytes.fromhex(os.environ.pop('NOMAD_PHASE28T_AUTH'));os.umask(0o077)
    with Listener(a.socket,family='AF_UNIX',authkey=token) as listener:
        with listener.accept() as connection:
            connection.send_bytes(json.dumps(info).encode())
            while True:
                payload=json.loads(connection.recv_bytes());receive=time.perf_counter_ns()
                if payload.get('shutdown'):break
                blocks=[];attached=time.perf_counter_ns()
                try:
                    field=object.__new__(Snapshot)
                    for name,description in payload['arrays'].items():
                        block=shared_memory.SharedMemory(name=description['name']);blocks.append(block)
                        # Only the creator(parent) owns unlinking these buffers.
                        resource_tracker.unregister(block._name,'shared_memory')
                        array=np.ndarray(description['shape'],dtype=description['dtype'],buffer=block.buf);array.flags.writeable=False;setattr(field,name,array)
                    field.origin=np.array(payload['field']['origin']);field.origin.flags.writeable=False
                    field.h=payload['field']['h'];field.radius=payload['field']['radius'];field.error_bound=payload['field']['error_bound'];field.metadata=MappingProxyType(payload['field']['metadata'])
                    attach_end=time.perf_counter_ns()
                    result=solve(payload['B'],payload['vw'],payload['path'],field,payload['alpha'],payload['warm'],payload['started'])
                    result['timing'].update(worker_receive_ns=receive,field_attach_start_ns=attached,field_attach_end_ns=attach_end,worker_pid=os.getpid(),worker_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None)
                except BaseException as exc:
                    result=dict(accepted=False,output_type='FALLBACK',disposition='WORKER_EXCEPTION',error=repr(exc),wall_s=time.perf_counter()-payload['started'],timing=dict(worker_receive_ns=receive,worker_pid=os.getpid(),worker_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None))
                finally:
                    for block in blocks:block.close()
                result['timing']['worker_send_start_ns']=time.perf_counter_ns()
                result['request_id']=payload['request_id']
                connection.send_bytes(json.dumps(result).encode())
    if Path(a.socket).exists():Path(a.socket).unlink()

if __name__=='__main__':main()
