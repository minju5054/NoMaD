"""Immediate CUT installation, shared EC-only hold, optional delayed R2 repair."""
import ast,inspect,json,time
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_isaac.async_core import WaypointExecution as OriginalCore
from nomad_phase38.ec_normal import RTCWithEC
from nomad_phase47c.runtime import install as frozen_install,run_without_oracle as frozen_run
from nomad_phase24.retention import retained_apply
from nomad_phase28.telemetry import builtin
from nomad_phase32.runtime import path_key
from nomad_phase16.execution import stop_command
from nomad_phase40p.schedule import application_tick,predict,disposition
from nomad_phase0.pure_pursuit import XYPath
from .graph import select


def hold_control():
    changes=0
    # inspect source is class-indented; dedent without touching the frozen file.
    import textwrap
    tree=ast.parse(textwrap.dedent(inspect.getsource(OriginalCore.control)))
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='command_valid' for t in node.targets):
            assert ast.unparse(node.value)=='age is not None and age < 1.0';node.value=ast.parse('age is not None',mode='eval').body;changes+=1
    assert changes==1;ns=dict(OriginalCore.control.__globals__);exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),ns);return ns['control']

class HoldCore(OriginalCore):
    control=hold_control()


def direction(path,pose):
    if path is None:return None
    try:
        p=XYPath(path);s,_=p.project(np.asarray(pose)[:2])
        if p.s[-1]-s<1e-9:return None
        delta=p.at(min(s+.05,p.s[-1]))-p.at(s)
        return float(np.arctan2(delta[1],delta[0]))
    except ValueError:return None

def angle_error(a,b):return float(abs((a-b+np.pi)%(2*np.pi)-np.pi))

class Execution(RTCWithEC):
    def __init__(self,method,out,worker=None):
        super().__init__(out);self.method52=method;self.rec_pending=None;self.rec_result=None;self.rec_next=0
        self.hold_rejected=False;self.current_native=None;self.last52_source='INITIAL_WAIT'
        self.rec_log=(out/'reconstruction.jsonl').open('x');self.trace_log=(out/'phase52_72hz.jsonl').open('x')
        if worker is not None:self.rec_worker=worker
        elif method=='GRAPH-REC':
            from .worker import Worker
            self.rec_worker=Worker(out)
        else:self.rec_worker=None
        assert self.repair_worker is None
    def record52(self,event,**kw):
        self.rec_log.write(json.dumps(builtin(dict(event=event,**kw)),allow_nan=False)+'\n');self.rec_log.flush()
    def set_hold(self,value,t,reason):
        if bool(value)!=self.hold_rejected:self.record52('HOLD_REJECTED_START' if value else 'HOLD_REJECTED_END',simulation_time_s=t,reason=reason,path_source_id=self.path_source_id)
        self.hold_rejected=bool(value)
    def try_hold(self,core,refresh,reason):
        if self.sp is None or self.follower is None:return False
        field=self.depth_maps.snapshot();r=self.ec_check(core.pose,self.actual_vw(),self.follower.path.points,field,
            refresh['simulation_time_s'],'NORMAL','KEEP_ACTIVE_NO_MIN_LENGTH',self.ec_cap,self.sp)
        if not r['passed']:return False
        self.mode='KEEP_ACTIVE';self.ec_blocked=False;self.ec_pending=None
        if self.ec_due is None:self.ec_due=round(refresh['simulation_time_s']*72)+36
        self.recovery.decision('KEEP_ACTIVE');self.set_hold(True,refresh['simulation_time_s'],reason)
        self.record52('KEEP_AFTER_REJECTION',simulation_time_s=refresh['simulation_time_s'],check_id=r['check_id'],reason=reason)
        return True
    def ec_stop(self,refresh,reason):
        core,_=self.ec_context
        if self.try_hold(core,refresh,reason):return
        self.set_hold(False,refresh['simulation_time_s'],reason);super().ec_stop(refresh,reason)
    def use_fallback(self,core,refresh):
        if self.try_hold(core,refresh,'ALL_DEPTH_UNSAFE'):
            detail=dict(reason='ACTIVE_EC_PASS',minimum_remaining_length_removed=True)
        else:
            self.set_hold(False,refresh['simulation_time_s'],'ACTIVE_EC_REJECT_OR_NO_PATH')
            super().ec_stop(refresh,'NO_ACTIVE_EC_PATH');detail=dict(reason='ACTIVE_EC_REJECT_OR_NO_PATH',minimum_remaining_length_removed=True)
            self.recovery.decision('STOP_WAIT')
        self.fallback_log.write(json.dumps(dict(id=self.active_id,simulation_time_s=refresh['simulation_time_s'],mode=self.mode,
            path_source_id=self.path_source_id,**detail))+'\n');self.fallback_log.flush();return detail
    def commit_path(self,path,core,refresh,source_id,kind):
        previous=self.follower.path.points.copy() if self.follower else None
        a=direction(previous,core.pose);b=direction(path,core.pose)
        self.set_hold(False,refresh['simulation_time_s'],'PATH_INSTALLED')
        super().commit_path(path,core,refresh,source_id,kind)
        bank=self.ec_samples.get(source_id,{}).get('worlds')
        if self.ec_switch is not None and self.ec_switch['id']==source_id:
            self.ec_samples[source_id]['observation_sim_s']=self.ec_switch['observation_sim_s']
        self.current_native=None if bank is None else np.asarray(bank[self.active_sample]).copy()
        self.record52('INSTALL_META',tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],
            id=source_id,kind=kind,sample=self.active_sample,heading_discontinuity_rad=angle_error(b,a) if a is not None and b is not None else None,
            old_direction_rad=a,new_direction_rad=b,original_candidate_world=self.current_native,
            observation_sim_s=self.ec_samples.get(source_id,{}).get('observation_sim_s'),path_world=self.follower.path.points)
    def poll_reconstruction(self,core,refresh,switch):
        if self.rec_worker is None:return
        tick=round(refresh['simulation_time_s']*72)
        while True:
            r=self.rec_worker.poll()
            if r is None:break
            if self.rec_pending and r['job_id']==self.rec_pending['job_id']:self.rec_result=r
            else:self.record52('LATE_RESULT',job_id=r['job_id'],simulation_time_s=tick/72,numeric_result=r)
        job=self.rec_pending
        if job is None:return
        status=disposition(job,self.rec_result,tick,refresh['monotonic_ns'],switch is not None and switch['id']!=job['id'])
        if status=='WAIT':return
        result=self.rec_result;self.rec_pending=None;self.rec_result=None
        if status=='ACCEPTED' and self.recovery.state!='NORMAL':status='RECOVERY_ACTIVE'
        error=float(np.linalg.norm(core.pose[:2]-np.asarray(job['B'])[:2]));yaw_error=angle_error(core.pose[2],job['B'][2]);chosen=None;checks=[]
        if status=='ACCEPTED':
            field=self.depth_maps.snapshot()
            for i,c in enumerate(result['results']):
                if not c.get('accepted'):continue
                r=self.ec_check(core.pose,self.actual_vw(),c['path'],field,tick/72,'NORMAL','GRAPH_REC_REPLACE',self.ec_cap)
                checks.append(dict(sample=i,check_id=r['check_id'],passed=r['passed'],objective=c['objective']))
            chosen=select(result['results'],{x['sample'] for x in checks if x['passed']})
            if chosen is None:status='EXEC_CERT_REJECT'
        if chosen is not None:
            self.active_sample=chosen;self.commit_path(result['results'][chosen]['path'],core,refresh,job['id'],'GRAPH_REC')
            self.sp.speed_cap=self.ec_cap;self.ec_generation+=1;self.ec_due=tick+36;self.ec_pending=None;self.ec_blocked=False
            self.recovery.decision('NORMAL')
            self.ec_log('INSTALL',generation=self.ec_generation,id=job['id'],kind='GRAPH_REC',state='NORMAL',apply_tick=tick,simulation_time_s=tick/72,
                route='GRAPH_REC_EC_PASS',speed_cap_m_s=self.ec_cap,fresh=False,freshest_rank=None,selected_sample=chosen,cap_released=False,cap_activated=False)
        self.record52('RESULT',job_id=job['job_id'],id=job['id'],simulation_time_s=tick/72,tick=tick,apply_tick=job['apply_tick'],
            disposition=status,applied=chosen is not None,selected_sample=chosen,prediction_error_m=error,prediction_yaw_error_rad=yaw_error,
            checks=checks,numeric_result=result,cut_path_preserved=chosen is None)
    def apply(self,core,refresh,switch):
        old_path=self.follower.path.points.copy() if self.follower is not None else None
        self.poll_reconstruction(core,refresh,switch)
        # Frozen NormalEC -> SAFE FRESHEST selection -> shared hold policy.
        super().apply(core,refresh,switch)
        if switch is not None:
            self.ec_samples[switch['id']]['observation_sim_s']=switch['observation_sim_s']
            if self.rec_worker is not None:
                tick=round(refresh['simulation_time_s']*72);target=application_tick(tick)
                ctl=self.sp if self.mode not in ('STOP_WAIT','REPAIR_WAIT') and self.recovery.state=='NORMAL' else None
                predicted=predict(ctl,core.pose,self.last_command,tick,target);field=self.depth_maps.snapshot()
                job=dict(kind='REC',job_id=self.rec_next,id=switch['id'],B=predicted['pose'],previous_vw=predicted['vw'],
                    samples_world=self.ec_samples[switch['id']]['worlds'].tolist(),old_path=old_path.tolist() if old_path is not None else None,
                    observation_sim_s=switch['observation_sim_s'],observation_pose=switch['observation_pose'],dispatch_tick=tick,apply_tick=target,
                    simulation_time_s=tick/72,dispatch_ns=time.monotonic_ns(),dispatch_pose=core.pose.tolist(),dispatch_vw=list(self.last_command),prediction=predicted,
                    depth_snapshot=dict(field.metadata))
                self.rec_next+=1;self.rec_pending=job;self.rec_result=None;self.rec_worker.submit(job,field);self.record52('DISPATCH',**job)
        if refresh.get('applied_command_source')=='ENDPOINT':self.set_hold(False,refresh['simulation_time_s'],'ENDPOINT')
        self.last52_source=refresh.get('applied_command_source','UNKNOWN')
        refresh['phase52p']=builtin(dict(method=self.method52,hold_rejected=self.hold_rejected,pending_job=self.rec_pending['job_id'] if self.rec_pending else None))
        if switch is not None:switch['phase52p']=refresh['phase52p']
    def integrate_record(self,before,after):
        super().integrate_record(before,after)
        installed=self.follower is not None and self.sp is not None
        cte=self.follower.path.project(np.asarray(after)[:2])[1] if installed else None
        native_error=XYPath(self.current_native).project(np.asarray(after)[:2])[1] if installed and self.current_native is not None and np.any(np.linalg.norm(np.diff(self.current_native,axis=0),axis=1)>1e-12) else None
        row=dict(tick=self.plant.last_tick,simulation_time_s=self.plant.last_tick/72,path_source_id=self.path_source_id if installed else None,
            kind=self.path_kind if installed else None,source=self.last52_source,hold_rejected=self.hold_rejected,installed=installed,
            cross_track_m=cte,raw_candidate_distance_m=native_error)
        self.trace_log.write(json.dumps(builtin(row),allow_nan=False)+'\n')
    def close(self):
        try:
            if self.rec_pending:self.record52('TERMINAL_UNAPPLIED',job_id=self.rec_pending['job_id'],id=self.rec_pending['id'])
            if self.rec_worker:self.rec_worker.close()
            super().close()
        finally:self.rec_log.close();self.trace_log.close()


def install(c):
    frozen_install(c)
    import nomad_isaac.async_runtime as engine
    import nomad_phase15b.execution as factory
    engine.WaypointExecution=HoldCore
    factory.make_execution=lambda config,out:retained_apply(Execution(config['phase52p_method'],out))

def run_without_oracle(*args,**kwargs):
    c=args[0];assert kwargs['uniform_delivery_delay_s']==c['phase52p_delay_s']
    if c['phase52p_delay_s']==.75:return frozen_run(*args,**kwargs)
    from nomad_phase51p.runtime import driver_tree
    from nomad_phase24.retention import full_frames
    from nomad_isaac import async_runtime as original
    tree=driver_tree(inspect.getsource(original.run_async),full_frames());ns=dict(original.__dict__,_phase24_full_frames=full_frames())
    exec(compile(tree,original.__file__,'exec'),ns);return ns['run_async'](*args,**kwargs)
