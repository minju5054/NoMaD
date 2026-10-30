"""One planner at a time; independent detour actions retain incoming NoMaD logs."""
import json,time
import numpy as np
from nomad_phase20.runtime import Execution as Base,run_without_oracle
from nomad_isaac.common import local_to_world
from nomad_phase15b.depth import evaluate_samples
from nomad_phase20b.worker import disposition
from nomad_phase20.execution import SPAlignment
from nomad_phase16.execution import stop_command
from nomad_phase15.evaluate import suffix
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase20.repair import split_arclength
from nomad_phase20c.detour_known import radial_reference
from nomad_phase20c.trigger import NoProgress
from .recent import local_certificate
from .worker import Worker


class Execution(Base):
    def __init__(self,method,out):
        super().__init__('M2_REPAIR' if method=='M3_DETOUR' else 'M1_ROTATE',out)
        self.named_method=method
        if method=='M3_DETOUR':self.repair_worker=Worker(out)
        self.history=[];self.no_progress=NoProgress();self.detour=None;self.detour_active=False;self.pending_field=None;self.detour_sent=False
        self.repair_to_detour=False;self.suppress_trigger_tick=-1;self.detour_count=0;self.detour_outcome_pending=None
        self.dlog=(out/'detour.jsonl').open('x');self.dcmd=(out/'phase20d_commands.jsonl').open('x')
    def integrate_record(self,before,after):
        super().integrate_record(before,after);self.history.append(np.asarray(after).copy())
    def drecord(self,event,**kw):
        self.dlog.write(json.dumps(dict(event=event,**kw))+'\n');self.dlog.flush()
    def collect_repair(self,core,refresh,switch):
        if self.repair_worker is None or self.detour is not None:return None
        found=None
        while True:
            r=self.repair_worker.poll()
            if r is None:break
            if self.repair_pending and r['job_id']==self.repair_pending['job_id']:found=r
            else:self.rlog('LATE_RESULT',**r)
        if self.repair_pending is None:return None
        job=self.repair_pending;status=disposition(found,job['dispatch_ns'],time.monotonic_ns())
        if switch is not None:status='SUPERSEDED'
        if status=='WAIT':return None
        self.repair_pending=None
        if status=='ACCEPTED' and not refresh['valid']:status='WAYPOINT_TIMEOUT'
        if status=='ACCEPTED':
            chosen=found['results'][found['selected_sample']];self.new_path(chosen['path'],core,refresh,job['id'],'REPAIR');self.await_repair_fresh=True;self.recovery.decision('NORMAL')
        elif switch is None:self.start_detour(core,refresh,'A',None)
        self.rlog('RESULT',job_id=job['job_id'],id=job['id'],disposition=status,simulation_time_s=refresh['simulation_time_s'],
            wait_s=(time.monotonic_ns()-job['dispatch_ns'])/1e9,pose_at_dispatch=job['B'],pose_at_result=core.pose.tolist(),
            movement_m=float(np.linalg.norm(core.pose[:2]-np.array(job['B'])[:2])),numeric_result=found)
        return status
    def start_detour(self,core,refresh,trigger,progress):
        if self.detour is not None or self.repair_pending is not None:return
        tick=round(refresh['simulation_time_s']*72);assert len(self.history)>tick
        u,source=radial_reference(np.array(self.history),tick)
        self.snapshot=self.depth_maps.snapshot();self.pending_field=self.snapshot
        self.detour=dict(kind='R3',job_id=self.next_repair,id=self.active_id,B=core.pose.tolist(),u_ref=u.tolist(),evaluation_tick=tick,
            dispatch_ns=time.monotonic_ns(),simulation_time_s=refresh['simulation_time_s'],depth_snapshot=dict(self.snapshot.metadata),trigger=trigger)
        self.next_repair+=1;self.detour_count+=1;self.detour_sent=False;self.detour_active=False;self.mode='REPAIR_WAIT';self.no_progress.started()
        self.drecord('TRIGGER',**self.detour,reference_source=source,progress_3s_m=progress)
        self.submit_detour()
    def submit_detour(self):
        if self.detour and not self.detour_sent and not self.repair_worker.busy():
            self.repair_worker.submit(self.detour,self.pending_field);self.detour_sent=True
            self.drecord('SUBMIT',job_id=self.detour['job_id'],simulation_time_s=self.detour['simulation_time_s'])
    def certificate(self,field,pose,tick,xy,B):
        path=XYPath(xy);s,_=path.project(np.asarray(pose)[:2]);tail,_=suffix(path.points,pose)
        if s<.30:
            near,far=split_arclength(tail,.30-s)
            cB=float(field.query(np.asarray(B)[None,:2])[0][0])-field.error_bound
            if cB<0:return False
            if not local_certificate(field,near,tick,min(.025,max(0.,cB-.005)),False):return False
        else:far=tail
        return far is None or local_certificate(field,far,tick,.025,True)
    def end_detour(self,core,refresh,reason):
        job=self.detour;elapsed=refresh['simulation_time_s']-job.get('apply_sim_s',refresh['simulation_time_s'])
        self.drecord('END',job_id=job['job_id'],reason=reason,simulation_time_s=refresh['simulation_time_s'],pose=core.pose.tolist(),execution_s=elapsed)
        self.detour_outcome_pending=dict(job_id=job['job_id'],end_sim_s=refresh['simulation_time_s']) if self.detour_active else None
        self.detour=None;self.pending_field=None;self.detour_active=False;self.no_progress.ended(refresh['simulation_time_s'])
        self.suppress_trigger_tick=round(refresh['simulation_time_s']*72)
        self.follower=None;self.sp=None;self.path_source_id=None;self.path_kind=None;self.repair_active=False
        self.use_fallback(core,refresh)
    def detour_control(self,core,refresh,switch):
        before=list(self.last_command);nominal=[core.v,core.w];tick=round(refresh['simulation_time_s']*72)
        if switch is not None:
            self.active_id=switch['id'];switch['phase20d_selection_deferred']=True
        if not self.detour_active:
            self.submit_detour();found=None
            while True:
                r=self.repair_worker.poll()
                if r is None:break
                if r['job_id']==self.detour['job_id']:found=r
                else:self.rlog('LATE_RESULT',**r)
            status=disposition(found,self.detour['dispatch_ns'],time.monotonic_ns())
            if status!='WAIT':
                job=self.detour
                if status=='ACCEPTED':
                    path=found['results'][found['selected_sample']]['path'];field=self.depth_maps.snapshot()
                    if not self.certificate(field,core.pose,tick,path,job['B']):status='APPLICATION_UNSAFE'
                self.drecord('RESULT',job_id=job['job_id'],disposition=status,simulation_time_s=refresh['simulation_time_s'],pose_at_result=core.pose.tolist(),
                    wait_s=(time.monotonic_ns()-job['dispatch_ns'])/1e9,numeric_result=found)
                if status=='ACCEPTED':
                    self.new_path(path,core,refresh,job['id'],'DETOUR');self.repair_active=False;self.detour_active=True
                    job.update(path=path,apply_sim_s=refresh['simulation_time_s']);self.recovery.decision('NORMAL')
                    self.drecord('APPLIED',job_id=job['job_id'],simulation_time_s=refresh['simulation_time_s'],pose=core.pose.tolist(),path=path,B=job['B'],validation_frame_id=field.metadata['frame_id'],validation_tick=tick)
                else:self.end_detour(core,refresh,status)
        diag={};source='DETOUR_WAIT'
        if self.detour_active:
            field=self.depth_maps.snapshot();job=self.detour
            if not self.certificate(field,core.pose,tick,job['path'],job['B']):self.end_detour(core,refresh,'PATH_BECAME_UNSAFE')
            elif refresh['simulation_time_s']-job['apply_sim_s']>=6.-1e-12:self.end_detour(core,refresh,'SIX_SECOND_LIMIT')
            else:
                command,diag=self.sp.control(core.pose,before[0])
                if diag['completed']:self.end_detour(core,refresh,'ENDPOINT')
                else:source='ALIGN_'+diag['mode'] if diag['mode'] in ('BRAKE','ROTATE') else 'DETOUR'
        if not self.detour_active:command=stop_command(before[0]);source='DETOUR_WAIT' if self.detour is not None else 'STOP_WAIT'
        core.v,core.w=command;self.last_command=list(command)
        self.write_command(core,refresh,switch,before,nominal,source,diag)
    def apply(self,core,refresh,switch):
        if self.named_method!='M3_DETOUR':super().apply(core,refresh,switch);return
        if self.detour is not None:self.detour_control(core,refresh,switch);return
        if switch is not None and self.detour_outcome_pending:
            self.drecord('FIRST_FRESH_AFTER_DETOUR',**self.detour_outcome_pending,id=switch['id'],simulation_time_s=refresh['simulation_time_s'],pose=core.pose.tolist())
            self.detour_outcome_pending=None
        self._normal_apply(core,refresh,switch)
    def _normal_apply(self,core,refresh,switch):
        before=list(self.last_command);nominal=[core.v,core.w];state=self.recovery.state
        if state=='WAIT_FRESH' and switch is not None:self.recovery.state='NORMAL';self.mode='STOP_WAIT'
        elif state in ('RECOVER_ROTATE','WAIT_FRESH'):
            if switch is not None:self.active_id=switch['id'];switch['phase17_selection_deferred']=True
            self.override(core,refresh,switch);self.write_command(core,refresh,switch,before,nominal,state,{})
            return
        repair_status=self.collect_repair(core,refresh,switch);decision=None;detail=None
        if self.detour is not None:
            self.detour_control(core,refresh,switch);return
        if switch is not None:
            self.active_id=switch['id'];self.fresh_switch_s=refresh['simulation_time_s'];self.repair_active=False
            self.snapshot=self.depth_maps.snapshot();switch['phase16_selection_ns']=time.monotonic_ns()
            worlds=np.array([local_to_world(np.array(x),switch['observation_pose']) for x in switch['overnight_metric_samples']])
            selected,detail=evaluate_samples(worlds,core.pose,self.snapshot);self.active_sample=detail['selected_sample']
            if self.await_repair_fresh:
                self.rlog('FIRST_FRESH_AFTER_REPAIR',id=switch['id'],simulation_time_s=refresh['simulation_time_s'],safe_sample_count=sum(c['safe'] for c in detail['candidates']))
                self.await_repair_fresh=False
            if self.recovery.awaiting_outcome:
                self.recovery_record('FIRST_FRESH',id=switch['id'],simulation_time_s=refresh['simulation_time_s'],safe_sample_count=sum(c['safe'] for c in detail['candidates']))
                self.recovery.awaiting_outcome=False
            if not detail['all_unsafe']:
                self.new_path(selected,core,refresh,switch['id'],'SAFE');self.recovery.decision('NORMAL')
            elif self.repair_worker is not None and not self.repair_worker.busy():
                job=dict(job_id=self.next_repair,id=switch['id'],B=core.pose.tolist(),samples_world=worlds.tolist(),
                    previous_vw=before,observation_pose=switch['observation_pose'],observation_sim_s=switch['observation_sim_s'],
                    depth_snapshot=dict(self.snapshot.metadata),dispatch_ns=time.monotonic_ns(),simulation_time_s=refresh['simulation_time_s'])
                self.next_repair+=1;self.repair_pending=job;self.mode='REPAIR_WAIT'
                (self.jobs_dir/f"{job['job_id']:04d}.json").write_text(json.dumps(clean(job)))
                self.rlog('SUBMIT',**job);self.repair_worker.submit(job,self.snapshot)
            else:
                if self.repair_worker is not None:self.rlog('WORKER_BUSY_FALLBACK',id=switch['id'],simulation_time_s=refresh['simulation_time_s'])
                decision=self.use_fallback(core,refresh)
            switch['phase16']=dict(method=self.named_method,selection=detail,fallback_mode=self.mode,fallback=decision,path_source_id=self.path_source_id,oracle_used=False)
        if self.repair_pending is None and self.recovery.eligible(before[0]):
            self.snapshot=self.depth_maps.snapshot();rays=self.recovery.start(self.snapshot,core.pose)
            self.recovery_start=dict(simulation_time_s=refresh['simulation_time_s'],pose=core.pose.tolist())
            self.recovery_record('START',**self.recovery_start,tick=round(refresh['simulation_time_s']*72),id=self.active_id,
                sign=self.recovery.sign,rays_m=rays,snapshot=dict(self.snapshot.metadata),stop_wait_streak=self.recovery.streak,previous_actual_v_m_s=before[0])
            self.follower=None;self.sp=None;self.path_source_id=None;self.repair_active=False
            self.override(core,refresh,switch);self.write_command(core,refresh,switch,before,nominal,'RECOVER_ROTATE',{})
            return
        diag={};source=self.mode
        if not refresh['valid']:
            command=stop_command(before[0]);source='WAYPOINT_TIMEOUT'
        elif self.mode in ('REPAIR_WAIT','STOP_WAIT') or self.sp is None:
            command=stop_command(before[0])
        else:
            command,diag=self.sp.control(core.pose,before[0])
            if diag['completed']:command=stop_command(before[0]);source='ENDPOINT'
            elif diag['mode'] in ('BRAKE','ROTATE'):source='ALIGN_'+diag['mode']
            elif self.repair_active:source='REPAIR'
        tick=round(refresh['simulation_time_s']*72)
        blocked=self.recovery.state!='NORMAL' or self.repair_pending is not None or source in ('ALIGN_BRAKE','ALIGN_ROTATE','REPAIR_WAIT')
        u,_=radial_reference(np.array(self.history),tick)
        fire,progress,_=self.no_progress.check(np.array(self.history),tick,u,blocked)
        if fire and tick!=self.suppress_trigger_tick:
            self.start_detour(core,refresh,'B',progress)
            command=stop_command(before[0]);source='DETOUR_WAIT';diag={}
        core.v,core.w=command;self.last_command=list(command)
        assert abs(core.v-before[0])<=.5/9+1e-12 and abs(core.w)<=.4+1e-12
        self.write_command(core,refresh,switch,before,nominal,source,diag)
        if switch is not None or repair_status=='ACCEPTED':
            self.apps.write(json.dumps(dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],
                id=self.active_id,path_source_id=self.path_source_id,kind=self.path_kind,pose=core.pose.tolist(),selected_sample=self.active_sample,
                world_xy=self.follower.path.points.tolist() if self.follower else None,depth_snapshot=dict(self.snapshot.metadata),
                before_vw=before,after_vw=list(command),fallback_mode=self.mode))+'\n');self.apps.flush()

    def write_command(self,core,refresh,switch,before,nominal,source,diag):
        super().write_command(core,refresh,switch,before,nominal,source,diag)
        snap=self.depth_maps.snapshot();state='ACTIVE' if self.detour_active else 'WAIT' if self.detour is not None else 'NORMAL'
        extra=dict(detour_state=state,detour_job=self.detour['job_id'] if self.detour else None,depth_frame=snap.metadata['frame_id'],
            snapshot_age_s=refresh['simulation_time_s']-snap.metadata['sim_s'],snapshot_publication_ns=snap.metadata['publication_monotonic_ns'])
        refresh['phase20d']=extra
        if switch is not None:switch['phase20d']=extra
        self.dcmd.write(json.dumps(dict(tick=round(refresh['simulation_time_s']*72),time_s=refresh['simulation_time_s'],source=source,**extra))+'\n');self.dcmd.flush()
    def close(self):
        self.dlog.close();self.dcmd.close();super().close()


def install():
    from nomad_phase20.runtime import install as old_install
    old_install()
    import nomad_phase15b.execution as factory
    import nomad_phase15b.depth as depth
    import nomad_phase2.config as placement
    from nomad_phase20b.config import place
    from .depth import DepthMapThread
    factory.make_execution=lambda c,out:Execution(c['phase20_method'],out);depth.DepthMapThread=DepthMapThread;placement.place=place
