"""Bind frozen R1 solve/follower into the existing H lifecycle; add telemetry only."""
import time
from types import FunctionType
from . import graph_r1
from .handoff import HExecution,install as original_install,run_without_oracle
from .runtime import NAExecution
from nomad_phase24.retention import retained_apply
from nomad_phase19r.evaluate import clean

def solve_job(B,vw,path,field,alpha,warm=None,started=None):
    # Intentionally no postprocessing of the frozen numerical decision/deadline.
    return graph_r1.solve(B,vw,path,field,alpha,warm,started)

def bind(method,**changes):
    return FunctionType(method.__code__,dict(method.__globals__,**changes),method.__name__,method.__defaults__,method.__closure__)

_new_path=bind(HExecution.new_path,solve=solve_job)
_collect_h=bind(HExecution.collect_h,TimedFollower=graph_r1.R1Follower)

class R1Execution(HExecution):
    collect_h=_collect_h
    def __init__(self,*args,**kwargs):
        self.init_telemetry();super().__init__(*args,**kwargs)
    def init_telemetry(self):
        self.r1_cases={};self.r1_job_cases={};self.r1_jobs={};self.r1_futures={};self.r1_closed=set();self.r1_active=None
        self.r1_current=None;self.r1_now_s=0.;self.r1_next_case=0
    def raw_record(self,event,**kw):super().hrecord(event,**clean(kw))
    def solver_result(self,job_id,value=None):
        r=value
        if isinstance(r,dict) and 'result' in r and 'output_type' not in r:r=r['result']
        if isinstance(r,dict) and 'output_type' in r:return r
        future=self.r1_futures.get(job_id)
        if future is not None and future.done():
            try:return future.result()
            except Exception:return None
        return None
    def finish_case(self,case_id,output_type,reason,job_id=None,result=None,applied=False):
        if case_id is None or case_id in self.r1_closed:return
        c=self.r1_cases[case_id];r=self.solver_result(job_id,result);job=self.r1_jobs.get(job_id)
        compute=r.get('wall_s') if r else (0. if reason=='WORKER_BUSY' else None)
        self.r1_closed.add(case_id);c.update(output_type=output_type,reason=reason,job_id=job_id,applied=applied,solver_result=r)
        self.raw_record('CASE_OUTCOME',case_id=case_id,id=c['id'],job_id=job_id,simulation_time_s=self.r1_now_s,
            output_type=output_type,reason=reason,applied=applied,explicit_na_fallback=reason not in ('SUPERSEDED','NON_NORMAL_PATH','SUPERSEDED_OR_OTHER_MODE','DETOUR_STARTED','TERMINAL') and not applied,
            solver_output_type=r.get('output_type') if r else None,solver_reason=r.get('disposition') if r else None,
            compute_wall_s=compute,compute_known=compute is not None,wait_wall_s=time.perf_counter()-job['started'] if job else 0.,
            feedback_clip_any=None if applied else False,feedback_clip_fraction=None,feedback_status='PENDING_COMMANDS' if applied else 'NO_H_FEEDBACK')
    def hrecord(self,event,**kw):
        job_id=kw.get('job_id');case_id=self.r1_job_cases.get(job_id,self.r1_current)
        if event=='DISPATCH':
            case_id=self.r1_current;self.r1_job_cases[job_id]=case_id
            self.r1_jobs[job_id]=dict(started=kw['dispatch_wall_s']);self.r1_cases[case_id]['job_id']=job_id
        if event=='COMMAND':
            case_id=self.r1_active
            if case_id is not None:
                c=self.r1_cases[case_id];c['commands']+=1;c['clips']+=bool(kw['diag'].get('any_clipped'))
                kw.update(case_id=case_id,job_id=c.get('job_id'),output_type=c['output_type'],feedback_clip=bool(kw['diag'].get('any_clipped')))
        self.raw_record(event,**kw)
        if event=='APPLIED':
            r=kw['result'];self.finish_case(case_id,r['output_type'],r.get('optimized_failure') or r['disposition'],job_id,r,True);self.r1_active=case_id
        elif event=='FALLBACK':
            self.finish_case(case_id,'FALLBACK',kw['reason'],job_id,kw.get('result'));self.r1_active=None
        elif event=='DISCARDED':self.finish_case(case_id,'FALLBACK',kw['reason'],job_id)
    def new_path(self,path,core,refresh,source_id,kind):
        self.r1_now_s=refresh['simulation_time_s']
        if kind=='SAFE':
            case_id=self.r1_next_case;self.r1_next_case+=1;self.r1_current=case_id
            self.r1_cases[case_id]=dict(id=source_id,commands=0,clips=0,dispatch_sim_s=self.r1_now_s)
        else:self.r1_current=None;self.r1_active=None
        try:return _new_path(self,path,core,refresh,source_id,kind)
        finally:
            if self.pending_h is not None and self.h_future is not None:self.r1_futures[self.pending_h['job_id']]=self.h_future
            self.r1_current=None
    def apply(self,core,refresh,switch):
        self.r1_now_s=refresh['simulation_time_s'];super().apply(core,refresh,switch)
    def finalize_telemetry(self):
        for case_id,c in sorted(self.r1_cases.items()):
            if case_id not in self.r1_closed:self.finish_case(case_id,'FALLBACK','TERMINAL',c.get('job_id'))
            r=self.solver_result(c.get('job_id')) or c.get('solver_result');n=c['commands']
            self.raw_record('CASE_SUMMARY',case_id=case_id,id=c['id'],job_id=c.get('job_id'),output_type=c['output_type'],reason=c['reason'],applied=c['applied'],
                solver_output_type=r.get('output_type') if r else None,compute_wall_s=r.get('wall_s') if r else 0. if c['reason']=='WORKER_BUSY' else None,
                feedback_commands=n,feedback_clipped_commands=c['clips'],feedback_clip_any=bool(c['clips']),feedback_clip_fraction=c['clips']/n if n else None,
                feedback_status='MEASURED' if n else 'NO_H_FEEDBACK')
    def close(self):
        # Keep the same lifecycle, but emit final per-case clip counts before close.
        self.cancel_h('TERMINAL');self.h_pool.shutdown(wait=True,cancel_futures=True);self.finalize_telemetry()
        self.h_log.close();NAExecution.close(self)

def install(config):
    assert config.get('phase28_runtime_revision')=='R1'
    original_install(config)
    import nomad_phase15b.execution as factory
    factory.make_execution=lambda c,out:retained_apply(NAExecution('M3_DETOUR',out) if c['phase28_method']=='C0-NA' else R1Execution('M3_DETOUR',out,c['phase28_alpha']))
