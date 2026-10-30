"""B-scope new-obstacle trigger/direction/end; ALL_UNSAFE A remains20E."""
import time
import numpy as np
from nomad_phase20e.runtime import Execution as Previous,run_without_oracle
from nomad_phase20d.runtime import Execution as Phase20D
from nomad_phase20b.worker import disposition
from nomad_phase16.execution import stop_command
from .trigger import NewObstacleNoProgress,no_new_obstacle_ahead
from .history import active_components

class Execution(Previous):
    def __init__(self,method,out):
        super().__init__(method,out)
        if method=='M3_DETOUR':self.no_progress=NewObstacleNoProgress(self)
    def drecord(self,event,**kw):
        if event=='TRIGGER' and kw.get('trigger')=='B':kw['new_obstacle_condition']=self.no_progress.last_gate
        Phase20D.drecord(self,event,**kw)
    def start_detour(self,core,refresh,trigger,progress):
        if trigger!='B':return super().start_detour(core,refresh,trigger,progress)
        if self.detour is not None or self.repair_pending is not None:return
        tick=round(refresh['simulation_time_s']*72);component=self.no_progress.last_gate['component'];assert component is not None
        self.snapshot=self.depth_maps.snapshot();self.pending_field=self.snapshot
        self.detour=dict(kind='R3',job_id=self.next_repair,id=self.active_id,B=core.pose.tolist(),u_ref=component['u_ref'],evaluation_tick=tick,
            dispatch_ns=time.monotonic_ns(),simulation_time_s=refresh['simulation_time_s'],depth_snapshot=dict(self.snapshot.metadata),trigger=trigger,component=component)
        self.next_repair+=1;self.detour_count+=1;self.detour_sent=False;self.detour_active=False;self.mode='REPAIR_WAIT';self.no_progress.started()
        self.drecord('TRIGGER',**self.detour,reference_source=component['direction'],progress_3s_m=progress)
        self.submit_detour()
    def new_obstacle_gone(self,field,pose,tick,job):
        gone=no_new_obstacle_ahead(field,pose,tick,job['u_ref'])
        if gone:self.drecord('EARLY_END_CHECK',job_id=job['job_id'],simulation_time_s=tick/72,pose=np.asarray(pose).tolist(),snapshot=dict(field.metadata),
            component=job.get('component'),active_components=len(active_components(field,tick)),reason='NO_NEW_OBSTACLE_AHEAD')
        return gone
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
            if job.get('trigger')=='B' and self.new_obstacle_gone(field,core.pose,tick,job):self.end_detour(core,refresh,'NO_NEW_OBSTACLE_AHEAD')
            elif not self.certificate(field,core.pose,tick,job['path'],job['B']):self.end_detour(core,refresh,'PATH_BECAME_UNSAFE')
            elif refresh['simulation_time_s']-job['apply_sim_s']>=6.-1e-12:self.end_detour(core,refresh,'SIX_SECOND_LIMIT')
            else:
                command,diag=self.sp.control(core.pose,before[0])
                if diag['completed']:self.end_detour(core,refresh,'ENDPOINT')
                else:source='ALIGN_'+diag['mode'] if diag['mode'] in ('BRAKE','ROTATE') else 'DETOUR'
        if not self.detour_active:command=stop_command(before[0]);source='DETOUR_WAIT' if self.detour is not None else 'STOP_WAIT'
        core.v,core.w=command;self.last_command=list(command)
        self.write_command(core,refresh,switch,before,nominal,source,diag)


def install():
    from nomad_phase20e.runtime import install as previous_install
    previous_install()
    import nomad_phase15b.execution as factory
    import nomad_phase15b.depth as depth
    from .depth import DepthMapThread
    factory.make_execution=lambda c,out:Execution(c['phase20_method'],out);depth.DepthMapThread=DepthMapThread
