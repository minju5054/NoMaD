"""Strict numeric-job CPU worker; never receives a scene config or SDF."""
import json
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase3_stage2.execution import SerialGraphClient

NUMERIC_SHAPES={'world_xy':(8,2),'boundary':(3,),'previous_command':(2,),
                'previous_commanded_vw':(2,),'observation_pose':(3,),'previous_xy':(8,2)}
SCALARS={'job_id','id','dispatch_ns','switch_monotonic_ns','switch_sim_s','observation_sim_s','distance_m'}
CONTROL_CONFIG={'phase4c_method':'GRAPH','plant_alpha':'inf'}

def validate_job(job):
    assert set(job)==set(NUMERIC_SHAPES)|SCALARS, 'Unknown job keys / geometry forbidden'
    for key,shape in NUMERIC_SHAPES.items():
        if key=='previous_xy' and job[key] is None:continue
        assert not isinstance(job[key],dict), 'Geometry object forbidden'
        a=np.asarray(job[key],dtype=float)
        assert a.shape==shape and np.isfinite(a).all(),key
    for key in SCALARS:assert isinstance(job[key],(int,float)) and np.isfinite(job[key]),key
    return job


def numeric_job(parent_job):
    job=dict(parent_job)
    # Parent scheduler only sees these two numerical/execution-mode constants.
    if 'public_config' in job:assert job.pop('public_config')==CONTROL_CONFIG, 'Geometry leaked into dispatch'
    return validate_job(job)


class Client(SerialGraphClient):
    def __init__(self,out):
        self.out=out;self.jobs=queue.Queue(maxsize=512);self.results=queue.Queue(maxsize=512)
        self.ready=threading.Event();self.error=None;self.busy=False
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(out/'graph_worker.log').open('x')
        self.proc=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase12.gf_worker'],cwd=ROOT,env=env,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        self.thread=threading.Thread(target=self.run,name='graph-gf-ipc',daemon=True);self.thread.start()
        if not self.ready.wait(30) or self.error:raise RuntimeError(f'Graph-GF worker startup failed: {self.error}')
    def submit(self,job):super().submit(numeric_job(job))


def solve_job(job):
    from .graph_gf import GraphGF,graph_protocol
    validate_job(job);start=time.monotonic_ns()
    response=dict(job_id=job['job_id'],id=job['id'],worker_start_ns=start,geometry_free_assert=True)
    try:
        graph=GraphGF(job['world_xy'],job['boundary'],job['previous_command'],graph_protocol(),job['previous_xy'])
        poses,solver=graph.solve()
        response.update(kind='result',poses=poses.tolist(),solver=solver,accepted=solver['feasible'])
    except Exception as e:
        response.update(kind='result',accepted=False,initialization_rejected=True,error=repr(e),traceback=traceback.format_exc())
    response['worker_end_ns']=time.monotonic_ns()
    return response


def main():
    # Load CPU numerical dependencies before READY; startup is not per-solve latency.
    from .graph_gf import GraphGF
    print(json.dumps({'kind':'ready'}),flush=True)
    for line in sys.stdin:
        job=json.loads(line)
        if job.get('kind')=='stop':return
        print(json.dumps(solve_job(job)),flush=True)

if __name__=='__main__':main()
