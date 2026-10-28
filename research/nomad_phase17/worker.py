"""External CPU worker: numeric graph input and one immutable depth snapshot file."""
import json
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
from nomad_isaac.common import ROOT
from nomad_phase12.gf_worker import numeric_job, solve_job as solve_gf
from nomad_phase3_stage2.execution import SerialGraphClient

class Client(SerialGraphClient):
    def __init__(self,out,depth=False):
        self.out=out;self.depth=depth;self.snapshot_file=None
        self.jobs=queue.Queue(maxsize=512);self.results=queue.Queue(maxsize=512)
        self.ready=threading.Event();self.error=None;self.busy=False
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(out/'graph_worker.log').open('x')
        self.proc=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase17.worker'],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        self.thread=threading.Thread(target=self.run,name='depth-graph-ipc',daemon=True);self.thread.start()
        if not self.ready.wait(30) or self.error:raise RuntimeError(f'Graph worker startup failed: {self.error}')
    def submit(self,job):
        job=numeric_job(job)
        if self.depth:job['depth_snapshot_file']=self.snapshot_file
        super().submit(job)

def solve_job(job):
    job=dict(job);path=job.pop('depth_snapshot_file',None)
    if path is None:return solve_gf(job)
    numeric_job(job);start=time.monotonic_ns()
    r=dict(job_id=job['job_id'],id=job['id'],worker_start_ns=start,depth_snapshot_file=path)
    try:
        from nomad_phase15b.depth import Snapshot
        from .graph import ClearanceGraph as DepthGraph
        graph=DepthGraph(job['world_xy'],job['boundary'],job['previous_command'],Snapshot.load(path),job['previous_xy'])
        poses,solver=graph.solve();r.update(kind='result',poses=poses.tolist(),solver=solver,accepted=solver['feasible'])
    except Exception as e:r.update(kind='result',accepted=False,initialization_rejected=True,error=repr(e),traceback=traceback.format_exc())
    r['worker_end_ns']=time.monotonic_ns();return r

def main():
    from .graph import ClearanceGraph as DepthGraph
    from nomad_phase15b.depth import Snapshot
    print(json.dumps(dict(kind='ready')),flush=True)
    for line in sys.stdin:
        job=json.loads(line)
        if job.get('kind')=='stop':return
        print(json.dumps(solve_job(job)),flush=True)
if __name__=='__main__':main()
