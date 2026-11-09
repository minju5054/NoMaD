"""Nonblocking VN jobs; waiting commands use the frozen OURS-DETOUR stack.

Pending planners are deliberately separate from repair_pending/detour. Those
frozen attributes imply a stop in the old controller; only an installed R3
occupies detour. Controller, selection, trigger and recovery equations remain
the imported implementations.
"""
import json
import time
import numpy as np
from nomad_phase38.ec_normal import NormalEC, RotateOnly
from nomad_phase38.runtime import install as install38, run_without_oracle
from nomad_phase32.runtime import path_key
from nomad_phase20f.runtime import Execution as FrozenDetour
from nomad_phase20c.detour import select_detour
from nomad_phase20c.detour_known import radial_reference
from nomad_phase24r.trigger import PersistentNoProgress
from nomad_phase24.retention import retained_apply
from nomad_phase28.telemetry import builtin
from nomad_phase39o3.maps import policy_map
from nomad_phase39o3.solver import map_certificate
from nomad_phase20c.detour_known import KnownDetourGraph
from .schedule import application_tick, predict, disposition
from .worker import Worker
from .escape import installation_anchor,certify_escape
from nomad_phase32o.exec_cert import certify
from nomad_phase32.policy import continuation_certificate


class PlanningBase(RotateOnly):
    def apply(self,core,refresh,switch):
        self.poll_job(core,refresh,switch)
        if self.detour_active:
            return FrozenDetour.detour_control(self,core,refresh,switch)
        # This is exactly the no-detour EC alternative's decision/executor.
        super().apply(core,refresh,switch)
        if self.n_pending is not None or self.recovery.state!='NORMAL':
            return
        if self.n_after_r2:
            # A timed-out pool may still be finishing. Keep the frozen R2->R3
            # transition queued without holding the robot or losing the stage.
            if self.start_detour(core,refresh,'A',None):self.n_after_r2=False
            return
        if switch is not None and switch.get('phase16',{}).get('selection',{}).get('all_unsafe'):
            self.start_repair(core,refresh,switch)
            return
        tick=round(refresh['simulation_time_s']*72)
        u,_=radial_reference(np.asarray(self.history),tick)
        source=refresh.get('applied_command_source','')
        blocked=source in ('ALIGN_BRAKE','ALIGN_ROTATE') or self.recovery.state!='NORMAL'
        fire,progress,_=self.no_progress.check(np.asarray(self.history),tick,u,blocked)
        if fire and tick!=self.suppress_trigger_tick:
            self.start_detour(core,refresh,'B',progress)


class Execution(NormalEC,PlanningBase):
    def __init__(self,out):
        super().__init__(out)
        self.n_worker=Worker(out)
        self.n_pending=None;self.n_result=None;self.n_after_r2=False
        self.n_log=(out/'phase40p.jsonl').open('x')
        self.no_progress=PersistentNoProgress(self)
        self.n_escape=None;self.n_escape_jobs={};self.n_installing=None
        self.n_last_install_escape=False;self.n_preview_anchors={}

    def nrecord(self,event,**data):
        self.n_log.write(json.dumps(builtin(dict(event=event,**data)),allow_nan=False)+'\n')
        self.n_log.flush()

    def ec_check(self,pose,vw,path,field,t,state,scope,cap,controller=None):
        tick=round(t*72);started=time.monotonic_ns();anchor=None;trace=None
        if scope=='PERIODIC':
            state='R3' if self.path_kind=='DETOUR' else 'R2' if self.path_kind=='REPAIR' else 'NORMAL'
        if self.n_installing is not None and state in ('R2','R3'):
            job,candidate=self.n_installing
            if candidate['cB']<.025:
                key=(job['job_id'],path_key(path))
                anchor=self.n_escape_jobs.get(job['job_id'])
                if anchor is None:
                    anchor,trace=installation_anchor(job['job_id'],candidate['cB'],t,pose,vw,path,field,cap)
                self.n_preview_anchors[key]=anchor
        elif scope=='PERIODIC' and self.n_escape is not None:
            anchor=self.n_escape
        if anchor is not None:
            r=certify_escape(pose,vw,path,field,anchor,t,cap,controller,trace)
            # Include initial deadline determination, not only the second sweep.
            r['compute_s']=(time.monotonic_ns()-started)/1e9
        else:
            r=continuation_certificate(controller,pose,vw,field,tick) if controller is not None else certify(pose,vw,path,field,speed_cap=cap)
        if hasattr(self.depth_maps,'archive_queue') and not getattr(self.depth_maps,'full_frames',True):
            self.depth_maps.archive_queue.put_nowait((field,None,None))
        finished=time.monotonic_ns();ident=self.ec_check_sequence;self.ec_check_sequence+=1
        self.ec_log('CHECK',check_id=ident,generation=self.ec_generation,state=state,scope=scope,check_tick=tick,
                    check_started_ns=started,check_finished_ns=finished,simulation_time_s=t,pose=np.asarray(pose).tolist(),
                    actual_vw=vw,speed_cap_m_s=cap,snapshot=dict(field.metadata),path_sha256=path_key(path),**r)
        return dict(r,check_id=ident,check_tick=tick,check_started_ns=started,check_finished_ns=finished)

    def ec_install(self,path,core,refresh,source_id,kind,periodic_rejected=False,reference_sample=None):
        candidate=self.n_installing
        result=super().ec_install(path,core,refresh,source_id,kind,periodic_rejected,reference_sample)
        if result['installed']:
            escape=candidate is not None and kind in ('REPAIR','DETOUR') and candidate[1]['cB']<.025
            if escape:
                job,_=candidate;key=(job['job_id'],path_key(path))
                anchor=self.n_escape_jobs.get(job['job_id']) or self.n_preview_anchors[key]
                assert abs(anchor['installed_s']-refresh['simulation_time_s'])<1e-10 or job['job_id'] in self.n_escape_jobs
                self.n_escape_jobs.setdefault(job['job_id'],anchor);self.n_escape=anchor
                self.nrecord('ESCAPE_INSTALL',**anchor,apply_tick=round(refresh['simulation_time_s']*72),
                             actual_install_s=refresh['simulation_time_s'],consecutive=self.n_last_install_escape)
            else:self.n_escape=None
            self.n_last_install_escape=bool(escape)
        self.n_preview_anchors.clear()
        return result

    def ec_stop(self,refresh,reason):
        super().ec_stop(refresh,reason)
        self.n_escape=None

    def dispatch(self,core,refresh,payload):
        if self.n_pending is not None or self.n_worker.busy():
            self.nrecord('WORKER_BUSY',tick=round(refresh['simulation_time_s']*72),kind=payload['kind'])
            return False
        tick=round(refresh['simulation_time_s']*72)
        target=application_tick(tick)
        controller=self.sp if self.mode not in ('STOP_WAIT','REPAIR_WAIT') else None
        prediction=predict(controller,core.pose,self.last_command,tick,target)
        field=self.depth_maps.snapshot()
        job=dict(payload,job_id=self.next_repair,id=self.active_id,B=prediction['pose'],
                 previous_vw=prediction['vw'],dispatch_pose=core.pose.tolist(),
                 dispatch_vw=list(self.last_command),dispatch_tick=tick,apply_tick=target,
                 dispatch_ns=time.monotonic_ns(),simulation_time_s=tick/72,
                 evaluation_tick=tick,depth_snapshot=dict(field.metadata),prediction=prediction)
        self.next_repair+=1;self.n_pending=job;self.n_result=None
        self.n_worker.submit(job,field)
        self.nrecord('DISPATCH',**job)
        if job['kind']=='R2':self.rlog('SUBMIT',**job)
        else:
            self.no_progress.started();self.detour_count+=1
            self.drecord('TRIGGER',**job)
        return True

    def start_repair(self,core,refresh,switch):
        self.dispatch(core,refresh,dict(kind='R2',trigger='A',samples_world=self.ec_samples[switch['id']]['worlds'].tolist(),
                                      observation_pose=switch['observation_pose'],observation_sim_s=switch['observation_sim_s']))

    def start_detour(self,core,refresh,trigger,progress):
        tick=round(refresh['simulation_time_s']*72)
        component=self.no_progress.last_gate['component'] if trigger=='B' else None
        if component is not None:u=component['u_ref'];source=component['direction']
        else:u,source=radial_reference(np.asarray(self.history),tick);u=u.tolist()
        return self.dispatch(core,refresh,dict(kind='R3',trigger=trigger,u_ref=u,component=component,
                                              reference_source=source,progress_3s_m=progress))

    def poll_job(self,core,refresh,switch):
        tick=round(refresh['simulation_time_s']*72)
        while True:
            r=self.n_worker.poll()
            if r is None:break
            if self.n_pending is not None and r['job_id']==self.n_pending['job_id']:self.n_result=r
            else:self.nrecord('LATE_RESULT',job_id=r['job_id'],tick=tick)
        job=self.n_pending
        if job is None:return
        superseded=job['kind']=='R2' and switch is not None and switch['id']!=job['id']
        status=disposition(job,self.n_result,tick,refresh['monotonic_ns'],superseded)
        if status=='WAIT':return
        result=self.n_result;self.n_pending=None;self.n_result=None
        if status=='ACCEPTED' and not refresh['valid'] and job['kind']=='R2':status='WAYPOINT_TIMEOUT'
        if status=='ACCEPTED' and self.recovery.state!='NORMAL':status='RECOVERY_ACTIVE'
        chosen=None;checks=[]
        if status=='ACCEPTED':
            indices=range(len(result['results'])) if job['kind']=='R3' else [result['selected_sample']]
            for i in indices:
                candidate=result['results'][i]
                if not candidate.get('accepted'):continue
                self.n_installing=(job,candidate)
                check=self.ec_check(core.pose,self.actual_vw(),candidate['path'],self.depth_maps.snapshot(),tick/72,
                                    job['kind'],'INSTALL_CANDIDATE',self.ec_cap)
                checks.append(dict(index=i,passed=check['passed'],check_id=check['check_id']))
            allowed={x['index'] for x in checks if x['passed']}
            if job['kind']=='R3':
                chosen=select_detour([dict(x,accepted=x['accepted'] and i in allowed) for i,x in enumerate(result['results'])])
            elif allowed:chosen=result['selected_sample']
            if chosen is None:status='EXEC_CERT_REJECT'
            self.ec_log('SOLVER_FILTER',state=job['kind'],job_id=job['job_id'],simulation_time_s=tick/72,
                        original_selected=result['selected_sample'],selected=chosen,checks=checks,
                        route='SOLVER_EC_PASS' if chosen is not None else 'R2_TO_R3' if job['kind']=='R2' else 'R3_FAILURE')
        if status=='ACCEPTED':
            candidate=result['results'][chosen];path=candidate['path'];self.n_installing=(job,candidate)
            self.ec_tokens.add((tick,path_key(path)))
            outcome=self.ec_install(path,core,refresh,job['id'],'DETOUR' if job['kind']=='R3' else 'REPAIR')
            assert outcome['installed']
            self.recovery.decision('NORMAL')
            if job['kind']=='R3':
                self.detour=dict(job,path=path,apply_sim_s=tick/72,cB=candidate['cB'])
                self.detour_active=True;self.repair_active=False
                self.drecord('APPLIED',job_id=job['job_id'],simulation_time_s=tick/72,pose=core.pose.tolist(),path=path,B=job['B'])
            else:self.await_repair_fresh=True
            self.nrecord('APPLIED',job_id=job['job_id'],kind=job['kind'],tick=tick,selected=chosen,
                         prediction_error_m=float(np.linalg.norm(core.pose[:2]-np.asarray(job['B'])[:2])),
                         escape=bool(candidate['cB']<.025),cB=candidate['cB'])
        elif job['kind']=='R2' and status not in ('SUPERSEDED','RECOVERY_ACTIVE'):
            self.n_after_r2=True
        elif job['kind']=='R3':
            # Same frozen failed-detour handover/fallback, after the wait ends.
            self.detour=job;self.detour_active=False
            self.end_detour(core,refresh,status)
        self.n_installing=None
        self.nrecord('RESULT',job_id=job['job_id'],kind=job['kind'],tick=tick,apply_tick=job['apply_tick'],
                     disposition=status,checks=checks,numeric_result=result)
        record=self.drecord if job['kind']=='R3' else self.rlog
        record('RESULT',job_id=job['job_id'],disposition=status,simulation_time_s=tick/72,
               wait_s=(time.monotonic_ns()-job['dispatch_ns'])/1e9,pose_at_result=core.pose.tolist(),numeric_result=result)

    def certificate(self,field,pose,tick,xy,B):
        # Phase24-R's active recheck tests the complete installed path. Preserve
        # that scope, replacing only its map and threshold with VN's certificate.
        planning,_=policy_map(field,B,'VN')
        u=self.detour['u_ref']
        graph=KnownDetourGraph(B,u,field,planning,0)
        graph.cB=self.detour['cB']
        graph.near_threshold=min(.025,max(0.,graph.cB-.005))
        return bool(map_certificate(graph,np.asarray(xy),planning,'VN')['certificate_pass'])

    def apply(self,core,refresh,switch):
        # The shared EC wrapper handles NORMAL pending changes. Solver paths
        # retain the original R2->R3 / R3-failure routes on periodic rejection.
        pending=self.ec_pending
        if pending is not None and pending.get('state') in ('R2','R3'):
            self.ec_pending=None;tick=round(refresh['simulation_time_s']*72)
            if pending['generation']==self.ec_generation:
                if pending['state']=='R2':
                    self.ec_blocked=True;self.repair_active=False;self.n_after_r2=True
                    # Waiting for R3 uses the same latest-SAFE alternatives as
                    # OURS-DETOUR, including slow candidates before STOP_WAIT.
                    self.ec_install(pending['path'],core,refresh,pending['source_id'],'SAFE',periodic_rejected=True)
                elif self.detour is not None:
                    self.ec_blocked=True;self.end_detour(core,refresh,'EXEC_CERT_REJECT')
            self.ec_log('PERIODIC_APPLY',check_id=pending['check_id'],check_tick=pending['check_tick'],apply_tick=tick,
                        delay_ticks=tick-pending['check_tick'],delay_ms=(tick-pending['check_tick'])/72*1000,state=pending['state'],
                        delay_wall_ms=(time.monotonic_ns()-pending['check_started_ns'])/1e6,apply_monotonic_ns=time.monotonic_ns(),
                        action='R2_TO_R3' if pending['state']=='R2' else 'R3_FAILURE')
        super().apply(core,refresh,switch)
        refresh['phase40p']=builtin(dict(waiting=self.n_pending is not None,pending_kind=self.n_pending['kind'] if self.n_pending else None,
                                       apply_tick=self.n_pending['apply_tick'] if self.n_pending else None))
        if switch is not None:switch['phase40p']=refresh['phase40p']

    def integrate_record(self,before,after):
        # NormalEC performs the unchanged 36-tick inspection. ec_check replaces
        # its label/schedule only when the installed path is a planner path.
        super().integrate_record(before,after)
        if self.ec_pending is not None:
            self.ec_pending['state']='R3' if self.path_kind=='DETOUR' else 'R2' if self.path_kind=='REPAIR' else 'NORMAL'
        self.nrecord('TICK',tick=self.plant.last_tick,waiting=self.n_pending is not None,
                     physical_stop=abs(self.last_command[0])<.01,mode=self.mode,
                     recovery_state=self.recovery.state)

    def close(self):
        try:
            self.n_worker.close()
            super().close()
        finally:self.n_log.close()


def install(config):
    install38(config)
    import nomad_phase15b.execution as factory
    factory.make_execution=lambda c,out:retained_apply(Execution(out))
