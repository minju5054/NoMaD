"""Optional RIGID entry and ablation worker around unchanged Phase4c execution."""
import json
import os
import queue
import subprocess
import threading
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase3_stage2.execution import SerialGraphClient
from nomad_phase4c.execution import AccelExecution
from .config import protocol
from .rigid import rigid_entry


class AblationClient(SerialGraphClient):
    def __init__(self,out):
        self.out=out;self.jobs=queue.Queue(maxsize=512);self.results=queue.Queue(maxsize=512)
        self.ready=threading.Event();self.error=None;self.busy=False
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(out/'graph_worker.log').open('x')
        self.proc=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase5.worker'],cwd=ROOT,env=env,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        self.thread=threading.Thread(target=self.run,name='graph-ipc',daemon=True);self.thread.start()
        if not self.ready.wait(30) or self.error:raise RuntimeError(f'Graph worker startup failed: {self.error}')


class Phase5Execution(AccelExecution):
    def __init__(self,config,out,client=None):
        self.phase5_method=config['phase5_method'];self.phase5_flags=protocol()['graph_flags'].get(self.phase5_method)
        if self.phase5_method.startswith('GRAPH-NO-'):client=client or AblationClient(out)
        super().__init__(config,out,client)
        self.applications=(out/'phase5_applications.jsonl').open('x')

    def record(self,row):
        super().record({**row,'phase5_method':self.phase5_method,'phase5_flags':self.phase5_flags})

    def apply(self,core,refresh,switch):
        before=list(self.last_command);original_chunk=None;correction=None
        if switch is not None and self.phase5_method=='RIGID-ENTRY':
            original_chunk=switch['chunk']
            try:
                xy,detail=rigid_entry(original_chunk['world_xy_m'],core.pose)
                correction={'status':'APPLIED',**detail,'applied_world_xy':xy.tolist()}
                switch['chunk']={**original_chunk,'world_xy_m':xy.tolist()}
            except ValueError as e:
                correction={'status':'INITIALIZATION_REJECTED','error':str(e),'fallback':'RAW'}
        try:super().apply(core,refresh,switch)
        finally:
            if original_chunk is not None:switch['chunk']=original_chunk
        refresh['phase5_method']=self.phase5_method
        if correction is not None:refresh['phase5_rigid']=correction
        if switch is not None:
            switch['phase5_method']=self.phase5_method
            if correction is not None:switch['phase5_rigid']=correction
        graph_job=refresh['stage2']['graph_applied_job']
        if switch is not None or graph_job is not None:
            path=self.follower.path if self.follower is not None else None
            s,d=path.project(core.pose[:2]) if path is not None else (None,None)
            row=dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],
                monotonic_ns=refresh['monotonic_ns'],id=self.active_id,pose=core.pose.tolist(),
                kind='GRAPH' if graph_job is not None else 'RIGID' if correction and correction['status']=='APPLIED' else 'RAW',
                graph_job_id=graph_job,world_xy=None if path is None else path.points.tolist(),
                path_length_m=None if path is None else float(path.s[-1]),projected_arclength_m=s,
                staleness=None if path is None else float(s/path.s[-1]),projection_distance_m=d,
                before_vw=before,after_vw=list(self.last_command),abs_dw=abs(self.last_command[1]-before[1]))
            self.applications.write(json.dumps(row)+'\n');self.applications.flush()

    def close(self):
        self.applications.close();super().close()
