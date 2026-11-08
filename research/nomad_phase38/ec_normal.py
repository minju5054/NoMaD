"""Phase32 NORMAL EC plumbing for methods without R2/R3 planners."""
import copy,json,time
from types import FunctionType
import numpy as np
from nomad_phase35.runtime import TENA,RTCNA
from nomad_phase21.execution import TEProfile
from nomad_phase28.telemetry import builtin
from nomad_phase28.alignment import NoAlignment
from nomad_phase32.runtime import Execution as FrozenEC,RecoveryGate
from nomad_phase32.policy import CappedNA
from nomad_phase32o.exec_cert import swept_clearance
from nomad_isaac.common import local_to_world,integrate_se2

class CappedTE(TEProfile):
    def control(self,pose,actual_v):
        (v,w),diag=super().control(pose,actual_v)
        if self.speed_cap is not None and diag.get('mode')=='GO' and not diag['completed']:
            v=max(float(actual_v)-.5/9,min(v,.1));w=float(np.clip(v*diag['kappa'],-.4,.4))
        return (float(v),float(w)),builtin(dict(diag,ec_speed_cap_m_s=self.speed_cap))

def te_trajectory(controller,pose,vw,tick,return_trace=False):
    ctl=copy.deepcopy(controller);q=np.asarray(pose,float).copy();v,w=map(float,vw);poses=[q.copy()];commands=[];done=False
    start_ns=ctl.now_ns
    for step in range(144):
        if (tick+step)%8==0:
            ctl.now_ns=start_ns+round(step/72*1e9)
            (v,w),d=ctl.control(q,v)
            if d['completed']:done=True;break
        q=integrate_se2(q,v,w,1/72);poses.append(q.copy());commands.append([v,w])
    return dict(poses=np.asarray(poses),commands=np.asarray(commands).reshape(-1,2),duration_s=len(commands)/72,endpoint_reached=done)

def installed(self,path,core,refresh,source_id,kind):return self.commit_path(path,core,refresh,source_id,kind)
_install=FunctionType(FrozenEC.ec_install.__code__,dict(FrozenEC.ec_install.__globals__,RAW_INSTALL=installed),
    FrozenEC.ec_install.__name__,FrozenEC.ec_install.__defaults__,FrozenEC.ec_install.__closure__)

class NormalEC:
    is_te=False
    def __init__(self,out):
        self.ec_blocked=False;self.ec_cap=None;self.ec_generation=0;self.ec_due=None;self.ec_pending=None;self.ec_context=None;self.ec_tokens=set();self.ec_sequence=0;self.ec_check_sequence=0;self.ec_samples={};self.ec_switch=None
        self.ec_file=(out/'exec_cert.jsonl').open('x');self.ec_ticks=(out/'exec_cert_72hz.jsonl').open('x');self.ec_candidate=None
        super().__init__(out);self.recovery=RecoveryGate(self.recovery,self)
        assert self.repair_worker is None,'This adapter must not start a planner'
    ec_log=FrozenEC.ec_log
    actual_vw=FrozenEC.actual_vw
    ec_stop=FrozenEC.ec_stop
    ec_options=FrozenEC.ec_options
    ec_install=_install
    def new_path(self,path,core,refresh,source_id,kind):
        return self.ec_install(path,core,refresh,source_id,kind)
    def commit_path(self,path,core,refresh,source_id,kind):
        from nomad_phase32.runtime import RAW_INSTALL
        RAW_INSTALL(self,path,core,refresh,source_id,kind)
    def ec_check(self,pose,vw,path,field,t,state,scope,cap,controller=None):
        return FrozenEC.ec_check(self,pose,vw,path,field,t,state,scope,cap,controller)
    def apply(self,core,refresh,switch):
        tick=round(refresh['simulation_time_s']*72);self.ec_context=(core,refresh);self.ec_switch=switch;self._ec_refresh=refresh
        if switch is not None:
            self.ec_samples[switch['id']]=dict(worlds=np.array([local_to_world(np.asarray(x),switch['observation_pose']) for x in switch['overnight_metric_samples']]),
                received_monotonic_ns=switch['received_monotonic_ns'])
            self.ec_samples={k:v for k,v in self.ec_samples.items() if k>=switch['id']-2}
        pending=self.ec_pending
        if pending is not None:
            self.ec_pending=None;delay=tick-pending['check_tick'];assert 0<=delay<=4
            if pending['generation']!=self.ec_generation:action='SUPERSEDED_PATH'
            else:
                self.ec_install(pending['path'],core,refresh,pending['source_id'],self.path_kind,periodic_rejected=True);action='NORMAL_FALLBACK'
            self.ec_log('PERIODIC_APPLY',check_id=pending['check_id'],check_tick=pending['check_tick'],apply_tick=tick,
                delay_ticks=delay,delay_ms=delay/72*1000,apply_monotonic_ns=time.monotonic_ns(),
                delay_wall_ms=(time.monotonic_ns()-pending['check_started_ns'])/1e6,action=action,state='NORMAL')
        super().apply(core,refresh,switch)
        refresh['exec_cert']=builtin(dict(speed_cap_m_s=self.ec_cap,blocked=self.ec_blocked,generation=self.ec_generation))
        if switch is not None:switch['exec_cert']=refresh['exec_cert']
        self.ec_switch=None
    def integrate_record(self,before,after):
        super().integrate_record(before,after);tick=self.plant.last_tick
        if self.ec_due is not None and tick>=self.ec_due:
            self.ec_due+=36
            if self.sp is not None and self.mode not in ('STOP_WAIT','REPAIR_WAIT') and self.recovery.state=='NORMAL' and self.ec_pending is None:
                field=self.depth_maps.snapshot();r=self.ec_check(after,self.actual_vw(),self.follower.path.points,field,tick/72,'NORMAL','PERIODIC',self.ec_cap,self.sp)
                if not r['passed']:self.ec_pending=dict(generation=self.ec_generation,path=self.follower.path.points.copy(),source_id=self.path_source_id,
                    check_tick=tick,check_id=r['check_id'],check_started_ns=r['check_started_ns'])
        self.ec_ticks.write(json.dumps(builtin(dict(tick=tick,simulation_time_s=tick/72,speed_cap_active=self.ec_cap is not None,
            ec_reject_latched=self.ec_blocked,physical_stop=abs(self.last_command[0])<.01,mode=self.mode,recovery_state=self.recovery.state,periodic_pending=self.ec_pending is not None)))+'\n')
    def close(self):
        try:super().close()
        finally:self.ec_file.close();self.ec_ticks.close()

class RotateOnly(RTCNA):
    def __init__(self,out):super().__init__('M1_ROTATE',out)
class RTCWithEC(NormalEC,RotateOnly):pass

class TEWithEC(NormalEC,TENA):
    is_te=True
    def use_fallback(self,core,refresh):
        detail=TENA.use_fallback(self,core,refresh)
        if self.sp is not None:
            self.sp.speed_cap=self.ec_cap;self.sp.ensemble=self.transition.ensemble
            r=self.ec_check(core.pose,self.actual_vw(),self.follower.path.points,self.depth_maps.snapshot(),
                refresh['simulation_time_s'],'NORMAL','KEEP_ACTIVE',self.ec_cap,self.sp)
            if not r['passed']:self.ec_stop(refresh,'TE_KEEP_EXEC_CERT_REJECT')
            else:self.ec_blocked=False;self.ec_due=round(refresh['simulation_time_s']*72)+36
        return detail
    def make_profile(self,path,pose,v,source_id,cap,refresh):
        base=CappedNA();base.replace_path(path,pose,v)
        ctl=object.__new__(CappedTE);ctl.__dict__.update(base.__dict__);ctl.speed_cap=cap
        ensemble=copy.deepcopy(self.transition.ensemble)
        # Periodic replacement updates the same chunk identity/receipt clock;
        # rejected previews never mutate the live ensemble.
        ensemble.chunks=[c for c in ensemble.chunks if c['id']!=source_id]
        received=self.ec_samples[source_id]['received_monotonic_ns']
        ensemble.push(path,source_id,received);ctl.ensemble=ensemble;ctl.now_ns=refresh['monotonic_ns']
        return ctl
    def commit_path(self,path,core,refresh,source_id,kind):
        # Installation log and PP/SP state are exactly the common NA installer.
        super().commit_path(path,core,refresh,source_id,kind)
        profile=self.make_profile(path,core.pose,self.last_command[0],source_id,self.ec_cap,refresh)
        self.sp=profile;self.follower=profile.follower;self.transition.ensemble=profile.ensemble
        self.transition.old_xy=np.asarray(path).copy();self.transition.old_received_ns=self.ec_samples[source_id]['received_monotonic_ns']
        profile.ensemble.chunks[-1]['sp']=profile
        if self.fresh is not None:self.fresh['phase16_transition']=dict(kind='TEMPORAL-ENSEMBLE',selected_sample=0,added=True)
    def ec_install(self,path,core,refresh,source_id,kind,periodic_rejected=False,reference_sample=None):
        self.ec_candidate_source=max(self.ec_samples) if periodic_rejected and self.ec_samples else source_id
        return _install(self,path,core,refresh,source_id,kind,periodic_rejected,reference_sample)
    def ec_check(self,pose,vw,path,field,t,state,scope,cap,controller=None):
        if getattr(self,'ec_te_mode',None)!='ENSEMBLE':
            return super().ec_check(pose,vw,path,field,t,state,scope,cap,controller)
        begin=time.perf_counter();start_ns=time.monotonic_ns();tick=round(t*72)
        ctl=copy.deepcopy(controller) if controller is not None else self.make_profile(path,pose,vw[0],self.ec_candidate_source,cap,self._ec_refresh)
        # A36tick inspection can occur four72Hz ticks after the last control.
        # Start the expiry clock at the inspection time, not that old control.
        ctl.now_ns=self._ec_refresh['monotonic_ns']+round((t-self._ec_refresh['simulation_time_s'])*1e9)
        trace=te_trajectory(ctl,pose,vw,tick);after=time.perf_counter();r=swept_clearance(field,trace['poses'],trace['commands'])
        r.update(compute_s=time.perf_counter()-begin,rollout_s=after-begin,duration_s=trace['duration_s'],endpoint_reached=trace['endpoint_reached'],model='TE_ENSEMBLE',continuation=controller is not None,rollout_start_monotonic_ns=ctl.now_ns)
        ident=self.ec_check_sequence;self.ec_check_sequence+=1;finished=time.monotonic_ns()
        if hasattr(self.depth_maps,'archive_queue') and not getattr(self.depth_maps,'full_frames',True):self.depth_maps.archive_queue.put_nowait((field,None,None))
        from nomad_phase32.runtime import path_key
        self.ec_log('CHECK',check_id=ident,generation=self.ec_generation,state=state,scope=scope,check_tick=tick,
            check_started_ns=start_ns,check_finished_ns=finished,simulation_time_s=t,pose=np.asarray(pose).tolist(),actual_vw=vw,
            speed_cap_m_s=cap,snapshot=dict(field.metadata),path_sha256=path_key(path),**r)
        return dict(r,check_id=ident,check_tick=tick,check_started_ns=start_ns,check_finished_ns=finished)
