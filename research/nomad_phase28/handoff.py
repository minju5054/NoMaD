"""NORMAL SAFE handoff only; all C0 selection/trigger/R2/R3 methods inherited."""
import json,time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from nomad_phase26.execution import install as baseline_install
from nomad_phase24.retention import retained_apply,run_without_oracle
from .runtime import NAExecution
from .graph import solve,certificate
from .tracking import TimedFollower,predict

class HExecution(NAExecution):
    def __init__(self,method,out,alpha):
        super().__init__(method,out);self.alpha=alpha;self.pending_h=None;self.warm_h=None;self.h_future=None;self.h_id=0
        self.h_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='phase28-handoff')
        self.h_log=(out/'phase28_handoff.jsonl').open('x')
    def hrecord(self,event,**kw):
        self.h_log.write(json.dumps(dict(event=event,**kw))+'\n');self.h_log.flush()
    def cancel_h(self,reason):
        if self.pending_h:
            self.hrecord('DISCARDED',job_id=self.pending_h['job_id'],reason=reason)
            self.pending_h=None
    def new_path(self,path,core,refresh,source_id,kind):
        if kind!='SAFE':
            self.cancel_h('NON_NORMAL_PATH');return super().new_path(path,core,refresh,source_id,kind)
        self.cancel_h('SUPERSEDED')
        if self.h_future is not None and not self.h_future.done():
            self.hrecord('FALLBACK',reason='WORKER_BUSY',id=source_id,simulation_time_s=refresh['simulation_time_s'])
            return super().new_path(path,core,refresh,source_id,kind)
        started=time.perf_counter();tick=round(refresh['simulation_time_s']*72)
        prediction=predict(core.pose,[self.last_command[0],self.plant.actual_w],self.sp,tick,self.plant.alpha)
        field=self.snapshot
        job=dict(job_id=self.h_id,id=source_id,path=np.asarray(path).tolist(),prediction=prediction,dispatch_sim_s=refresh['simulation_time_s'],snapshot=dict(field.metadata),started=started)
        self.h_id+=1;self.pending_h=job;self.mode='NORMAL'
        self.hrecord('DISPATCH',**{k:v for k,v in job.items() if k!='started'},dispatch_wall_s=started,previous_vw=self.last_command)
        self.h_future=self.h_pool.submit(solve,prediction['pose'],prediction['vw'],job['path'],field,self.alpha,self.warm_h,started)
    def fallback_h(self,job,core,refresh,reason,result=None):
        self.hrecord('FALLBACK',job_id=job['job_id'],id=job['id'],reason=reason,simulation_time_s=refresh['simulation_time_s'],result=result)
        super().new_path(job['path'],core,refresh,job['id'],'SAFE')
    def collect_h(self,core,refresh,switch):
        job=self.pending_h
        if job is None:return
        if switch is not None or self.detour is not None or self.recovery.state!='NORMAL':self.cancel_h('SUPERSEDED_OR_OTHER_MODE');return
        tick=round(refresh['simulation_time_s']*72)
        if tick<job['prediction']['apply_tick']:return
        self.pending_h=None
        if not self.h_future.done():return self.fallback_h(job,core,refresh,'TIMEOUT')
        try:r=self.h_future.result()
        except Exception as exc:return self.fallback_h(job,core,refresh,'WORKER_EXCEPTION',dict(error=repr(exc)))
        if not r['accepted']:return self.fallback_h(job,core,refresh,r['disposition'],r)
        field=self.depth_maps.snapshot();xy=np.asarray(r['poses'])[:,:2]
        current=certificate(np.vstack([core.pose[:2],xy]),field)
        if not current['passed']:return self.fallback_h(job,core,refresh,'APPLICATION_CERTIFICATE_FAILURE',dict(result=r,certificate=current))
        try:controller=TimedFollower(r,refresh['simulation_time_s'],self.alpha)
        except (ValueError,AssertionError) as exc:return self.fallback_h(job,core,refresh,'CONTROLLER_ASSEMBLY_FAILURE',dict(error=repr(exc)))
        self.sp=controller;self.follower=self.sp.follower
        self.path_source_id=job['id'];self.path_kind='HANDOFF';self.mode='NORMAL';self.repair_active=False;self.last_application_ns=refresh['monotonic_ns'];self.warm_h=r
        self.rlog('PATH_APPLIED',kind='HANDOFF',id=job['id'],tick=tick,simulation_time_s=refresh['simulation_time_s'],pose=core.pose.tolist(),
            previous_vw=self.last_command,path_world=xy.tolist(),alignment=False,heading_error_deg=None,threshold_deg=90.,plan=self.sp.plan)
        self.hrecord('APPLIED',job_id=job['job_id'],id=job['id'],tick=tick,simulation_time_s=refresh['simulation_time_s'],prediction=job['prediction'],pose=core.pose.tolist(),
            prediction_position_error_m=float(np.linalg.norm(core.pose[:2]-np.array(job['prediction']['pose'])[:2])),result=r,latest_certificate=current)
    def apply(self,core,refresh,switch):
        self.collect_h(core,refresh,switch)
        if isinstance(self.sp,TimedFollower):self.sp.now_s=refresh['simulation_time_s'];self.sp.previous_w=self.plant.actual_w
        super().apply(core,refresh,switch)
        if self.detour is not None:self.cancel_h('DETOUR_STARTED')
    def write_command(self,core,refresh,switch,before,nominal,source,diag):
        super().write_command(core,refresh,switch,before,nominal,source,diag)
        if diag.get('phase28_timed'):
            self.hrecord('COMMAND',simulation_time_s=refresh['simulation_time_s'],command=[core.v,core.w],before_vw=before,source=source,diag=diag)
    def close(self):
        self.cancel_h('TERMINAL');self.h_pool.shutdown(wait=True,cancel_futures=True);self.h_log.close();super().close()

def install(config):
    baseline_install(config)
    import nomad_phase15b.execution as factory
    factory.make_execution=lambda c,out:retained_apply(NAExecution('M3_DETOUR',out) if c['phase28_method']=='C0-NA' else HExecution('M3_DETOUR',out,c['phase28_alpha']))
