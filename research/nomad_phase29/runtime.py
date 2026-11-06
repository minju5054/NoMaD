"""Normal SAFE path edits only; inherited C0 decisions, R2/R3, NA execution."""
import json,time
import numpy as np
from nomad_phase28.runtime import NAExecution
from nomad_phase26.execution import install as original_install,run_without_oracle
from nomad_phase20f.runtime import Execution as C0Execution
from nomad_phase24.retention import retained_apply
from nomad_phase3_stage2.execution import decision
from nomad_phase28.telemetry import builtin
from .paths import smooth
from .client import Worker

class PathExecution(NAExecution):
    def __init__(self,method,out):
        super().__init__('M3_DETOUR',out);self.path_method=method;self.path_jobs={};self.path_sequence=0;self.path_prior=None
        self.path_log=(out/'phase29_paths.jsonl').open('x');self.path_worker=Worker(out) if method=='G18' else None
        if self.path_worker:self.path_record('WORKER_READY',**self.path_worker.info)
    def path_record(self,event,**data):self.path_log.write(json.dumps(builtin(dict(event=event,**data)))+'\n');self.path_log.flush()
    def new_path(self,path,core,refresh,source_id,kind):
        if kind!='SAFE':return super().new_path(path,core,refresh,source_id,kind)
        field=self.snapshot;job_id=self.path_sequence;self.path_sequence+=1;started=time.monotonic_ns()
        self.path_record('SUBMIT',job_id=job_id,id=source_id,simulation_time_s=refresh['simulation_time_s'],method=self.path_method,
            boundary=core.pose.tolist(),previous_vw=[self.last_command[0],self.plant.actual_w],path=np.asarray(path).tolist(),snapshot=dict(field.metadata))
        if self.path_method=='SM':
            chosen,info=smooth(path,core.pose,field)
            super().new_path(chosen,core,refresh,source_id,kind)
            self.path_record('RESULT',job_id=job_id,id=source_id,simulation_time_s=refresh['simulation_time_s'],disposition=info['reason'],applied=info['applied'],wall_s=(time.monotonic_ns()-started)/1e9,**{k:v for k,v in info.items() if k not in ('reason','applied')})
            return
        super().new_path(path,core,refresh,source_id,kind)
        job=dict(job_id=job_id,id=source_id,path=np.asarray(path).tolist(),boundary=core.pose.tolist(),previous_vw=[self.last_command[0],self.plant.actual_w],previous_xy=self.path_prior)
        self.path_jobs[job_id]=(job,self.path_worker.submit(job,field),started)
    def collect_paths(self,core,refresh,switch):
        for job_id,(job,future,started) in list(self.path_jobs.items()):
            if not future.done():continue
            result=future.result()
            if result['result_received_ns']>refresh['monotonic_ns']:continue
            del self.path_jobs[job_id]
            status,stale,seconds=decision(result,core.latest['id'] if core.latest else -1,refresh['valid'])
            if status=='ACCEPTED' and (switch is not None or core.applied_id!=job['id']):status='SUPERSEDED'
            if status=='ACCEPTED' and (self.detour is not None or self.detour_active or self.repair_pending is not None or self.mode!='NORMAL' or self.recovery.state!='NORMAL'):status='NON_NORMAL_MODE'
            if status=='ACCEPTED':
                path=np.asarray(result['poses'])[:,:2];self.path_prior=path.tolist()
                # Install only XY, through the unchanged NA PP/SP path installer.
                NAExecution.new_path(self,path,core,refresh,job['id'],'GRAPH18')
            self.path_record('RESULT',**result,simulation_time_s=refresh['simulation_time_s'],disposition=status,stale_flag=stale,applied=status=='ACCEPTED',wall_s=seconds,dispatch_to_result_s=(result['result_received_ns']-started)/1e9)
    def apply(self,core,refresh,switch):
        if self.path_worker:self.collect_paths(core,refresh,switch)
        super().apply(core,refresh,switch)
        refresh.update(builtin(refresh))
        if switch is not None:switch.update(builtin(switch))
    def close(self):
        if self.path_worker:
            self.path_worker.close()
            for job_id,(_,future,started) in self.path_jobs.items():
                result=future.result();self.path_record('RESULT',**result,disposition='TERMINAL_UNAPPLIED',applied=False,wall_s=(result['worker_end_ns']-result['worker_start_ns'])/1e9)
        self.path_log.close();super().close()

def install(config):
    original_install(config)
    import nomad_phase15b.execution as factory
    def make(c,out):
        method=c['phase29_method']
        if method=='C0':obj=C0Execution('M3_DETOUR',out)
        elif method=='C0-NA':obj=NAExecution('M3_DETOUR',out)
        else:obj=PathExecution(method,out)
        return retained_apply(obj)
    factory.make_execution=make
