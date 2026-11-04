"""Phase24 D -> one G -> PP/graph-speed, with frozen20F exits/recovery."""
import copy,json,time
import numpy as np
from nomad_isaac.common import local_to_world,integrate_se2
from nomad_phase23.rollout import GraphFollower
from nomad_phase22.reeval import stop_reason
from nomad_phase4c.execution import AccelExecution
from nomad_phase19r.evaluate import clean
from nomad_phase17.recovery import Recovery
from .trigger import PersistentNoProgress as NewObstacleNoProgress,choose_ahead,no_new_obstacle_ahead
from .follower import ControlState
from .safety import certificate
from nomad_phase20d.recent import build_cache
from nomad_phase20c.detour_known import radial_reference
from nomad_phase20d.runtime import Execution as FrozenDetour
from .online_worker import Worker
from .online_config import protocol
POLICIES=('PATH_AT_0P5_NEXT_9HZ',)

def stop_result():
    return dict(accepted=False,output_type='STOP',poses=None,dt=None,path=None,compute_s=None)


class DecisionGraphExecution(AccelExecution):
    def __init__(self,c,out):
        super().__init__(dict(phase4c_method='CURV',plant_alpha='inf'),out)
        self.out=out;self.named_method='G';self.clock=ControlState(protocol()['application_policy']);self.worker=Worker(out)
        self.jobs=[];self.next_job=0;self.depth_maps=None;self.last_native_received_ns=None;self.last_application_ns=None;self.path_source_id=None
        self.history=[];self.native=None;self.mode='NORMAL';self.epoch=0;self.detour=None;self.suppress_trigger_tick=-1;self.no_progress=NewObstacleNoProgress(self)
        self.recovery=Recovery();self.recovery_started=None
        self.events=(out/'g_events.jsonl').open('x');self.commands=(out/'g_commands.jsonl').open('x')
        self._integrate=self.plant.integrate;self.plant.integrate=self.integrate;self.live_cache=None;self.priority_event=None;self.last_core_pose=None
    def record_event(self,event,**kw):
        self.events.write(json.dumps(clean(dict(event=event,**kw)))+'\n');self.events.flush()
    def drecord(self,event,**kw):self.record_event(event,**kw)
    def strict_cache(self,field,tick):
        key=(field.metadata['frame_id'],tick)
        if self.live_cache is None or self.live_cache[0]!=key:self.live_cache=(key,build_cache(field,tick)[0])
        return self.live_cache[1]
    def end_priority(self,tick,reason):
        self.record_event('ROTATION_PRIORITY_END',tick=tick,simulation_time_s=tick/72,duration_s=(tick-self.priority_event['tick'])/72,reason=reason,**{k:v for k,v in self.priority_event.items() if k!='tick'})
        self.priority_event=None
    def record_priority(self,tick):
        self.last_tick_seen=tick;diag=self.clock.last_diag;rotating=diag.get('rotation_priority') and diag.get('mode')=='GRAPH_ROTATION'
        identity=(self.path_source_id,diag.get('segment'))
        if self.priority_event is not None and (not rotating or tuple(self.priority_event['identity'])!=identity):self.end_priority(tick,'COMPLETED_OR_BRAKING')
        if rotating and self.priority_event is None:
            self.priority_event=dict(tick=tick,identity=identity,theta_chord_error_deg=diag['theta_chord_error_deg'],THETA_CHORD_INCONSISTENT=diag['THETA_CHORD_INCONSISTENT'])
            self.record_event('ROTATION_PRIORITY_START',simulation_time_s=tick/72,**self.priority_event)
    def integrate_record(self,before,after):
        super().integrate_record(before,after);self.history.append(np.asarray(after).copy())
    def poses(self,pose,tick):
        poses=list(self.history)
        if len(poses)==tick:poses.append(np.asarray(pose).copy())
        assert len(poses)>tick
        return np.asarray(poses)
    def direction(self,core,tick):
        poses=self.poses(core.pose,tick);chosen,info=choose_ahead(self.depth_maps.snapshot(),poses,tick,self.no_progress.direction_cache)
        if chosen is not None:return chosen['u_ref'],dict(source='20F_COMPONENT_PREAPPEARANCE',component=chosen,**info)
        u,detail=radial_reference(poses,tick);return u.tolist(),dict(source='20F_A_FALLBACK',detail=detail)
    def dispatch(self,core,tick,mode,u=None,reason='FRESH',parent=None):
        if self.native is None:return
        start=time.monotonic_ns();expiry=float('inf') if self.mode=='DETOUR' and self.detour.get('active',False) else tick+(self.last_native_received_ns+1_000_000_000-start)/1e9*72
        prediction=self.clock.predict(core.pose,tick,expiry);field=self.depth_maps.snapshot()
        old=self.clock.plan.get('path') if self.clock.plan is not None else None
        case=dict(B=core.pose.tolist(),previous_vw=list(self.last_command),tick=tick,fresh_id=self.native['id'],samples_world=self.native['samples_world'],old_path=old,U_old_withheld_ASTAR=False)
        job=dict(job_id=self.next_job,fresh_id=self.native['id'],dispatch_tick=tick,due_tick=tick+36,dispatch_ns=start,case=case,prediction=prediction,mode=mode,u_ref=u,epoch=self.epoch,reason=reason,parent=parent)
        self.next_job+=1;self.jobs.append(job);self.worker.submit(job,field)
        self.record_event('DISPATCH',job_id=job['job_id'],fresh_id=job['fresh_id'],tick=tick,simulation_time_s=tick/72,mode=mode,reason=reason,u_ref=u,predicted_pose=prediction['B_pred'],due_tick=tick+36,parent=parent,depth_snapshot=dict(field.metadata))
    def enter_detour(self,core,tick,reason,parent=None):
        self.epoch+=1;self.mode='DETOUR';self.no_progress.started();u,detail=self.direction(core,tick)
        self.detour=dict(u_ref=u,reason=reason,active=False,direction=detail,parent=parent)
        self.record_event('MODE_ENTER',mode='DETOUR',reason=reason,tick=tick,simulation_time_s=tick/72,pose=core.pose.tolist(),direction=detail)
        self.dispatch(core,tick,'DETOUR',u,reason,parent)
    def exit_detour(self,core,tick,reason,failed=False):
        self.record_event('MODE_EXIT',mode='DETOUR',reason=reason,tick=tick,simulation_time_s=tick/72,pose=core.pose.tolist(),execution_s=(tick-self.detour['apply_tick'])/72 if self.detour.get('active') else 0.)
        self.mode='NORMAL';self.epoch+=1;self.detour=None;self.no_progress.ended(tick/72);self.suppress_trigger_tick=tick
        self.clock.install(stop_result(),tick);self.path_source_id=None;self.recovery.decision('STOP_WAIT' if failed else 'NORMAL')
    def apply_due(self,core,tick):
        now=time.monotonic_ns()
        for job in list(self.jobs):
            if tick<job['due_tick']:continue
            self.jobs.remove(job)
            if job['epoch']!=self.epoch:
                self.record_event('MODE_SUPERSEDED',job_id=job['job_id'],tick=tick);continue
            packet=self.worker.result(job['job_id'],min(now,job['dispatch_ns']+500_000_000));offered=packet['result'] if packet is not None else stop_result()
            alternatives=offered.get('alternatives',[]);result=stop_result();rejected=0
            certificate_info=[]
            if alternatives:
                field=self.depth_maps.snapshot();strict=self.strict_cache(field,tick)
                for candidate in alternatives:
                    check=certificate(candidate['path'],job['prediction']['B_pred'],field,strict)
                    certificate_info.append(dict(initialization=candidate['index'],output_type=candidate['output_type'],certificate=check))
                    live=check['passed']
                    if live:
                        result=dict(offered,accepted=True,output_type=candidate['output_type'],path=candidate['path'],poses=candidate['poses'],dt=candidate['dt'],selected=candidate);break
                    rejected+=1;self.record_event('CERTIFICATE_REJECTED',stage='APPLICATION',job_id=job['job_id'],initialization=candidate['index'],tick=tick,simulation_time_s=tick/72,certificate=check)
            if rejected and result['accepted']:self.record_event('CERTIFICATE_ALTERNATIVE_USED',job_id=job['job_id'],initialization=result['selected']['index'],tick=tick,simulation_time_s=tick/72)
            if self.priority_event is not None:self.end_priority(tick,'NEW_PATH')
            self.clock.install(result,tick);self.path_source_id=job['fresh_id'];self.active_id=job['fresh_id'];self.last_application_ns=now
            measured=result.get('compute_s');first=job['parent'].get('compute_s') if job.get('parent') else None
            self.record_event('APPLY',job_id=job['job_id'],fresh_id=job['fresh_id'],tick=tick,simulation_time_s=tick/72,mode=job['mode'],reason=job['reason'],pose=core.pose.tolist(),predicted_pose=job['prediction']['B_pred'],
                prediction_error_m=float(np.linalg.norm(core.pose[:2]-np.asarray(job['prediction']['B_pred'])[:2])),application_delay_s=(tick-job['dispatch_tick'])/72,wall_delay_s=(now-job['dispatch_ns'])/1e9,
                output_type=result['output_type'],path=result.get('path'),poses=result.get('poses'),dt=result.get('dt'),available_result=packet is not None,compute_s=measured,
                combined_compute_s=None if measured is None else measured+(first or 0.),first_eligible_command_tick=self.clock.next_tick,
                certificate_rejections=offered.get('certificate_rejections',0)+rejected,candidate_certificates=certificate_info,
                alternative_initializer_used=offered.get('alternative_initializer_used',False))
            if job['mode']=='NORMAL':
                if result['accepted']:self.recovery.decision('NORMAL')
                else:self.enter_detour(core,tick,'NORMAL_NO_OUTPUT',dict(job_id=job['job_id'],compute_s=measured))
            elif result['accepted']:
                self.detour.update(active=True,path=result['path'],B=job['prediction']['B_pred'],apply_tick=tick);self.recovery.decision('NORMAL')
            else:self.exit_detour(core,tick,'NO_DETOUR_OUTPUT',failed=True)
    def command(self,core,tick):
        valid=self.mode=='DETOUR' and self.detour.get('active',False) or self.last_native_received_ns is not None and time.monotonic_ns()-self.last_native_received_ns<=1_000_000_000
        if self.recovery.state!='NORMAL':
            self.clock.last_command=list(self.recovery.interval_command());self.clock.last_diag=dict(mode=self.recovery.state)
        else:self.clock.update(core.pose,tick,valid)
        self.last_command=list(self.clock.last_command);core.v,core.w=self.last_command
        self.record_priority(tick)
        self.follower=self.clock.controller.pp if self.clock.controller is not None else None
    def integrate(self,core,tick):
        core.v,core.w=self.last_command
        rotating=self.recovery.state=='RECOVER_ROTATE'
        if self.recovery.state!='NORMAL':core.v,core.w=self.recovery.interval_command()
        before=core.pose.copy();actual=self._integrate(core,tick)
        if self.clock.last_diag.get('rotation_priority') and self.clock.last_diag.get('mode')=='GRAPH_ROTATION':
            assert actual[0]==0 and np.array_equal(before[:2],core.pose[:2]),'Priority rotation translated the circular footprint'
        if rotating:
            assert np.array_equal(before[:2],core.pose[:2])
            if self.recovery.integrated(actual[1]):self.record_event('RECOVERY_END',tick=tick,simulation_time_s=tick/72,duration_s=(tick-self.recovery_started)/72,pose=core.pose.tolist())
        if self.recovery.state=='NORMAL':self.apply_due(core,tick)
        if tick%8:self.command(core,tick)
        return actual
    def apply(self,core,refresh,switch):
        tick=round(refresh['simulation_time_s']*72)
        if switch is not None:
            self.last_native_received_ns=switch['received_monotonic_ns'];self.active_id=switch['id']
            self.native=dict(id=switch['id'],samples_world=np.asarray([local_to_world(np.asarray(x),switch['observation_pose']) for x in switch['overnight_metric_samples']]).tolist())
            if self.recovery.state=='WAIT_FRESH':self.recovery.state='NORMAL';self.record_event('RECOVERY_NEXT_FRESH',tick=tick,simulation_time_s=tick/72,fresh_id=switch['id'])
        if self.recovery.state=='NORMAL':
            if self.mode=='DETOUR' and self.detour.get('active'):
                job=self.detour;field=self.depth_maps.snapshot();reason=None
                if job['reason']=='TRIGGER_B' and no_new_obstacle_ahead(field,core.pose,tick,job['u_ref']):reason='NO_NEW_OBSTACLE_AHEAD'
                elif not certificate(job['path'],job['B'],field,self.strict_cache(field,tick))['passed']:reason='PATH_BECAME_UNSAFE'
                elif tick-job['apply_tick']>=432:reason='SIX_SECOND_LIMIT'
                elif self.clock.ended:reason='ENDPOINT'
                if reason:self.exit_detour(core,tick,reason)
            if self.mode=='NORMAL':
                if self.clock.plan and self.clock.plan.get('accepted') and not self.clock.ended:
                    field=self.depth_maps.snapshot();path=self.clock.plan['path'];boundary=self.clock.plan.get('B_pred',path[0])
                    if not certificate(path,boundary,field,self.strict_cache(field,tick))['passed']:
                        self.record_event('PATH_BECAME_UNSAFE',mode='NORMAL',tick=tick,simulation_time_s=tick/72,pose=core.pose.tolist());self.clock.install(stop_result(),tick);self.path_source_id=None
                poses=self.poses(core.pose,tick);u,_=radial_reference(poses,tick)
                fire,_,_=self.no_progress.check(poses,tick,u,blocked=self.clock.last_diag.get('mode') in ('GRAPH_ROTATION','GRAPH_ROTATION_BRAKE'))
                if fire and self.native is not None and tick!=self.suppress_trigger_tick:self.enter_detour(core,tick,'TRIGGER_B')
                elif switch is not None:self.dispatch(core,tick,'NORMAL')
            if self.mode=='NORMAL' and not any(j['epoch']==self.epoch for j in self.jobs) and self.recovery.eligible(self.last_command[0]):
                rays=self.recovery.start(self.depth_maps.snapshot(),core.pose);self.recovery_started=tick;self.epoch+=1;self.clock.install(stop_result(),tick)
                self.record_event('RECOVERY_START',tick=tick,simulation_time_s=tick/72,pose=core.pose.tolist(),count=self.recovery.count,sign=self.recovery.sign,rays_m=rays)
        self.command(core,tick)
        diag=self.clock.last_diag;row=dict(tick=tick,simulation_time_s=tick/72,monotonic_ns=time.monotonic_ns(),pose=core.pose.tolist(),command=self.last_command,path_source_id=self.path_source_id,mode=self.mode,recovery=self.recovery.state,diag=diag)
        self.commands.write(json.dumps(clean(row))+'\n');self.commands.flush()
        refresh.update(commanded_v_m_s=core.v,commanded_w_rad_s=core.w,applied_v_m_s=core.v,applied_w_rad_s=self.plant.actual_w,applied_command_source='G_'+self.mode,
            pure_pursuit=dict(active_chunk_id=self.path_source_id,path_valid=self.follower is not None,stop_reason=diag['mode'] if diag['mode'] in ('STOP','ENDPOINT','WAYPOINT_TIMEOUT') else None),
            stage2=dict(method='G',kappa_pp=diag.get('kappa_pp'),corrected_path_active=self.clock.controller is not None,graph_applied_job=None),
            phase24=dict(mode=self.mode,recovery=self.recovery.state,output_type=self.clock.plan['output_type'] if self.clock.plan else 'STOP'))
        if switch is not None:switch['phase24']=refresh['phase24']
    def close(self):
        if self.priority_event is not None:self.end_priority(self.last_tick_seen,'RUN_END')
        for job in self.jobs:self.record_event('TERMINAL_UNAPPLIED',job_id=job['job_id'])
        self.worker.close();self.events.close();self.commands.close();super().close()
