"""Phase11 worker: original v6 lifecycle with adaptive progress subclass."""
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np
from nomad_phase0.graph_v4 import SignedDistanceField
from nomad_phase9.graph import FreeField
from .graph import GraphV61,progress_metadata


import os
import queue
import subprocess
import threading
from nomad_isaac.common import ROOT
from nomad_phase3_stage2.execution import SerialGraphClient

class Client(SerialGraphClient):
    def __init__(self,out):
        self.out=out;self.jobs=queue.Queue(maxsize=512);self.results=queue.Queue(maxsize=512)
        self.ready=threading.Event();self.error=None;self.busy=False
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(out/'graph_worker.log').open('x')
        self.proc=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase11.worker'],cwd=ROOT,env=env,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        self.thread=threading.Thread(target=self.run,name='graph-ipc',daemon=True);self.thread.start()
        if not self.ready.wait(30) or self.error:raise RuntimeError(f'Graph worker startup failed: {self.error}')


def main():
    p=json.loads(Path(__file__).parents[1].joinpath('nomad_phase0/graph_v4_protocol.json').read_text())
    fields={}
    print(json.dumps({'kind':'ready'}),flush=True)
    for line in sys.stdin:
        job=json.loads(line)
        if job.get('kind')=='stop': return
        start=time.monotonic_ns(); response={'job_id':job['job_id'],'id':job['id'],'worker_start_ns':start}
        response.update(progress_metadata(job['world_xy'],job['boundary']))
        try:
            assert job['public_config'].get('phase11_v61') is True
            key=json.dumps(job['public_config']['obstacles'],sort_keys=True)
            if key not in fields:
                fields[key]=SignedDistanceField(job['public_config'],p['sdf_resolution_m'],p['sdf_padding_m']) if job['public_config']['obstacles'] else FreeField()
            graph=GraphV61(job['world_xy'],job['boundary'],job['previous_command'],job['public_config'],p,
                          fields[key],job.get('previous_xy'))
            poses,solver=graph.solve()
            response.update(kind='result',poses=poses.tolist(),solver=solver,
                accepted=solver['feasible'],sdf_build_s=fields[key].build_wall_s)
        except Exception as e:
            response.update(kind='result',accepted=False,initialization_rejected=True,
                error=repr(e),traceback=traceback.format_exc())
        response.update(worker_end_ns=time.monotonic_ns())
        print(json.dumps(response),flush=True)

if __name__=='__main__':main()
