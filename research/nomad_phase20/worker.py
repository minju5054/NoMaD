"""One outstanding CPU-thread repair; no oracle or navigation calls."""
import queue,threading,time
import numpy as np
from nomad_phase19r.evaluate import select_repair,clean
from .repair import solve_sample


def disposition(result,dispatch_ns,now_ns):
    if result is None:return 'TIMEOUT' if now_ns-dispatch_ns>500_000_000 else 'WAIT'
    if result['end_ns']-dispatch_ns>500_000_000:return 'TIMEOUT'
    if result.get('error'):return 'ERROR'
    return 'ACCEPTED' if result['selected_sample'] is not None else 'REJECTED'


class RepairWorker:
    def __init__(self):self.thread=None;self.results=queue.SimpleQueue()
    def busy(self):return self.thread is not None and self.thread.is_alive()
    def submit(self,job,field):
        assert not self.busy()
        samples=np.array(job['samples_world'],copy=True);B=np.array(job['B'],copy=True)
        samples.flags.writeable=False;B.flags.writeable=False
        def work():
            started=time.monotonic_ns()
            try:
                results=[solve_sample(x,B,field) for x in samples]
                result=dict(job_id=job['job_id'],start_ns=started,end_ns=time.monotonic_ns(),selected_sample=select_repair(results),results=clean(results))
            except BaseException as exc:result=dict(job_id=job['job_id'],start_ns=started,end_ns=time.monotonic_ns(),error=repr(exc),selected_sample=None,results=[])
            self.results.put(result)
        self.thread=threading.Thread(target=work,name='phase20-R2-repair',daemon=True);self.thread.start()
    def poll(self):
        try:return self.results.get_nowait()
        except queue.Empty:return None
    def close(self):
        if self.thread:self.thread.join(15)
        if self.busy():raise RuntimeError('Repair worker did not finish on shutdown')
