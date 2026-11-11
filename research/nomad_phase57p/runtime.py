"""Switches only: no depth prefilter/recovery/alignment/slow tier; endpoint latch."""
import json,time
import numpy as np
from nomad_phase40p.launch import bind
from nomad_phase28.telemetry import builtin
from nomad_phase28.runtime import installer
from nomad_phase32.policy import CappedNA
from nomad_phase32.runtime import Execution as FrozenEC
from nomad_phase20.runtime import Execution as BaseSelection
from nomad_phase38.ec_normal import RTCWithEC
from nomad_phase53p.runtime import Execution as Handoff,path_key
from nomad_phase53p.ec_tail import certify_tail
from nomad_phase47c.runtime import install as frozen_install,run_without_oracle
from nomad_phase0.pure_pursuit import XYPath

class MinProfile(CappedNA):
    """Same PP/SP commands, with ALIGN disabled and endpoint completion latched."""
    def replace_path(self,xy,B,actual_v):
        count=self.alignment_count;super().replace_path(xy,B,actual_v)
        self.mode='GO';self.target_yaw=None;self.trigger_S=False;self.alignment_count=count
        self.endpoint_latched=False;self.speed_cap=None
    def control(self,pose,actual_v):
        assert self.speed_cap is None
        if self.endpoint_latched:command,diag=(0.,0.),dict(completed=True,mode='ENDPOINT',target=0.,kappa=None)
        else:
            command,diag=super().control(pose,actual_v)
            if diag['completed']:self.endpoint_latched=True
        return command,builtin(dict(diag,endpoint_latched=self.endpoint_latched,alignment_disabled=True))

def longest(samples,B,field):
    """No SDF query: rank all world-fixed candidates by B-projected remainder."""
    candidates=[]
    for i,p in enumerate(samples):
        try:path=XYPath(p);s,_=path.project(np.asarray(B)[:2]);length=float(path.s[-1]-s)
        except ValueError:length=0.
        # safe is only an inherited eligibility slot, NOT a depth certificate.
        candidates.append(dict(index=i,safe=True,remaining_length_m=length,clearance_m=None,depth_filter_disabled=True))
    selected=min(candidates,key=lambda x:(-x['remaining_length_m'],x['index']))['index']
    return samples[selected],dict(selected_sample=selected,all_unsafe=False,candidates=candidates,depth_filter_disabled=True,oracle_used=False)

def full_speed(primary,options,check,retained_cap=None,primary_rejected=False):
    assert retained_cap is None
    tested=set()
    for item in [primary,*options]:
        if item['key'] in tested or (primary_rejected and item['key']==primary['key']):continue
        tested.add(item['key'])
        if check(item,None)['passed']:return dict(item=item,cap=None,route='PRIMARY_FULL' if item['key']==primary['key'] else 'NEXT_CANDIDATE_FULL')
    return dict(item=None,cap=None,route='STOP_WAIT')

class NoRecovery:
    def __init__(self,base):self.base=base
    def __getattr__(self,k):return getattr(self.base,k)
    def __setattr__(self,k,v):
        if k=='base':object.__setattr__(self,k,v)
        else:setattr(self.base,k,v)
    def decision(self,mode):pass
    def eligible(self,v):return False

class SelectionBridge(BaseSelection):
    apply=bind(BaseSelection.apply,evaluate_samples=longest)

# C3 places SelectionBridge immediately before the frozen BaseSelection, so
# upper EC/HMM/phase20 wrappers still run without a process-global monkeypatch.
class Execution(Handoff,SelectionBridge):
    ec_options=bind(FrozenEC.ec_options,evaluate_samples=longest)
    ec_install=bind(Handoff.ec_install,normal_choice=full_speed)
    def __init__(self,method,out,worker=None):
        super().__init__('CUT',out);self.recovery=NoRecovery(self.recovery);self.min_method=method
        if method=='MIN+G18':
            from nomad_night20261111.worker import Client
            self.ho_method='GRAPH-HO';self.ho_worker=worker if worker is not None else Client(out)
    def ec_check(self,pose,vw,path,field,t,state,scope,cap,controller=None):
        assert cap is None
        if controller is None:
            controller=MinProfile()
            try:controller.replace_path(path,pose,vw[0])
            except ValueError as exc:
                tick=round(t*72);ident=self.ec_check_sequence;self.ec_check_sequence+=1
                r=dict(passed=False,reason='INVALID_PATH',clearance_m=None,model='MIN_BRAKING_TAIL',error=str(exc),compute_s=0.)
                self.ec_log('CHECK',check_id=ident,check_tick=tick,simulation_time_s=t,pose=np.asarray(pose).tolist(),actual_vw=vw,
                    state=state,scope=scope,speed_cap_m_s=None,snapshot=dict(field.metadata),path_sha256=path_key(path),**r)
                return dict(r,check_id=ident,check_tick=tick,check_started_ns=time.monotonic_ns())
        # Frozen tail integration receives the same no-ALIGN/latching profile
        # used by the real installer, including continuation controller state.
        r=super().ec_check(pose,vw,path,field,t,state,scope,cap,controller)
        return r
    def use_fallback(self,core,refresh):
        self.ec_stop(refresh,'NO_CANDIDATE_WAIT_NEW_CHUNK');self.recovery.decision('STOP_WAIT')
        detail=dict(reason='WAIT_NEW_CHUNK',keep_active_disabled=True)
        self.fallback_log.write(json.dumps(builtin(dict(id=self.active_id,simulation_time_s=refresh['simulation_time_s'],mode=self.mode,path_source_id=self.path_source_id,**detail)))+'\n');self.fallback_log.flush()
        return detail
    def record(self,event,**kw):
        if event=='INSTALL':kw.update(alignment_disabled=True,endpoint_latch=True,depth_filter_disabled=True)
        return super().record(event,**kw)

# Phase53's final Handoff installer uses super().commit_path. Bind its original
# installer lookup to MinProfile instead of replacing Graph/EC numerics.
from nomad_phase38.ec_normal import NormalEC
class ProfileBridge(RTCWithEC):
    commit_path=installer(MinProfile)
class MinExecution(Execution,ProfileBridge):pass

def install(config):
    frozen_install(config)
    if config['phase57p_method']!='NOMAD_RAW':
        from nomad_phase24.retention import retained_apply
        import nomad_phase15b.execution as factory
        import nomad_phase8.execution as overnight
        def make(c,out):return retained_apply(MinExecution(c['phase57p_method'],out))
        factory.make_execution=make;overnight.OvernightExecution=make
    if config.get('h1v2'):
        from nomad_h1v2.scene import install_environment
        install_environment(config)
