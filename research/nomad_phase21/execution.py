"""Phase18 handoff rules +20F common PP/SP executor; no oracle controller input."""
import json,time
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase20.runtime import Execution as Common
from nomad_phase20.execution import SPAlignment
from nomad_phase20f.runtime import Execution as Frozen,run_without_oracle
from nomad_phase16.execution import filter_ensemble,stop_command
from nomad_phase12.methods import TransitionState


class RawExecution(Common):
    def __init__(self,out):super().__init__('M1_ROTATE',out);self.named_method='B0_NOMAD_RAW'
    def apply(self,core,refresh,switch):
        before=list(self.last_command);nominal=[core.v,core.w]
        if switch is not None:
            self.active_id=switch['id'];path=local_to_world(np.array(switch['overnight_metric_samples'][0]),switch['observation_pose'])
            try:self.new_path(path,core,refresh,switch['id'],'RAW')
            except ValueError:self.sp=self.follower=None;self.path_source_id=None
            switch['phase21_raw']=dict(sample=0,depth_used=False,recovery_enabled=False)
        source='NORMAL';diag={}
        if not refresh['valid'] or self.sp is None:command=stop_command(before[0]);source='WAYPOINT_TIMEOUT' if not refresh['valid'] else 'INVALID_PATH'
        else:
            command,diag=self.sp.control(core.pose,before[0])
            if diag['completed']:command=stop_command(before[0]);source='ENDPOINT'
            elif diag['mode'] in ('BRAKE','ROTATE'):source='ALIGN_'+diag['mode']
        core.v,core.w=command;self.last_command=list(command);self.write_command(core,refresh,switch,before,nominal,source,diag)


class TEProfile(SPAlignment):
    """Latest selected chunk supplies SP/alignment; unchanged ensemble supplies steering."""
    def control(self,pose,actual_v):
        command,diag=super().control(pose,actual_v)
        if diag['mode'] in ('BRAKE','ROTATE'):return command,diag
        te,detail=self.ensemble.control(pose,self.now_ns)
        if te is None or te['endpoint_stop']:return (0.,0.),dict(completed=True,mode='ENDPOINT',kappa=None,ensemble=detail)
        x,y=te['target_local_x_m'],te['target_local_y_m'];k=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
        s,_=self.follower.path.project(np.asarray(pose)[:2]);target=float(np.clip(np.interp(s,self.plan['s_m'],self.plan['v_m_s']),.05,.3))
        v=float(np.clip(target,max(.05,actual_v-.5/9),min(.3,actual_v+.5/9)));w=float(np.clip(v*k,-.4,.4))
        return (v,w),dict(completed=False,mode='GO',target=target,kappa=k,progress=self.follower.progress,plan_generation=self.plan_generation,ensemble=detail)


class TEExecution(Common):
    def __init__(self,out):
        super().__init__('M1_ROTATE',out);self.named_method='B1_SAFE_TE';self.transition=TransitionState('TEMPORAL-ENSEMBLE');self.fresh=None;self.now_ns=0
    def new_path(self,path,core,refresh,identifier,kind):
        super().new_path(path,core,refresh,identifier,kind)
        _,detail=self.transition.switch(np.repeat(np.asarray(path)[None],8,axis=0),core.pose,identifier,self.fresh['received_monotonic_ns'],refresh['monotonic_ns'])
        self.fresh['phase16_transition']=detail
        wrapped=object.__new__(TEProfile);wrapped.__dict__.update(self.sp.__dict__);wrapped.ensemble=self.transition.ensemble;wrapped.now_ns=self.now_ns;self.sp=wrapped
        self.transition.ensemble.chunks[-1]['sp']=self.sp
    def use_fallback(self,core,refresh):
        self.snapshot=self.depth_maps.snapshot();self.mode,detail=filter_ensemble(self.transition.ensemble,core.pose,self.snapshot,refresh['monotonic_ns'])
        if self.transition.ensemble.chunks:
            latest=self.transition.ensemble.chunks[-1];self.sp=latest['sp'];self.follower=self.sp.follower;self.path_source_id=latest['id']
        else:self.sp=self.follower=None;self.path_source_id=None
        self.repair_active=False
        self.fallback_log.write(json.dumps(dict(id=self.active_id,simulation_time_s=refresh['simulation_time_s'],mode=self.mode,path_source_id=self.path_source_id,**detail))+'\n');self.fallback_log.flush();self.recovery.decision(self.mode);return detail
    def apply(self,core,refresh,switch):
        self.fresh=switch;self.now_ns=refresh['monotonic_ns']
        if self.sp is not None:self.sp.now_ns=self.now_ns
        super().apply(core,refresh,switch)
    def write_command(self,core,refresh,switch,before,nominal,source,diag):
        super().write_command(core,refresh,switch,before,nominal,source,diag)
        if 'ensemble' in diag:
            refresh['phase16_ensemble']=diag['ensemble']
            if switch is not None:switch['phase16_ensemble']=diag['ensemble']


def make_execution(c,out):
    m=c['phase21_method']
    if m=='B0_NOMAD_RAW':return RawExecution(out)
    if m=='B1_SAFE_TE':return TEExecution(out)
    if m in ('B2_SAFE_RTC','B3_M1'):return Frozen('M1_ROTATE',out)
    if m=='M3_GRAPH':return Frozen('M3_DETOUR',out)
    if m=='B4_ASTAR':
        import nomad_phase20d.runtime as previous
        from .worker import Worker
        saved=previous.Worker;previous.Worker=Worker
        try:return Frozen('M3_DETOUR',out)
        finally:previous.Worker=saved
    raise ValueError(m)

def install():
    from nomad_phase20f.runtime import install as previous_install
    previous_install()
    import nomad_phase15b.execution as factory
    import nomad_phase8.execution as overnight
    import nomad_phase2.config as placement
    from .config import place,triggered
    old=overnight.OvernightExecution
    overnight.OvernightExecution=lambda c,out:make_execution(c,out) if c.get('phase21') else old(c,out)
    factory.make_execution=make_execution;placement.place=place;placement.triggered=triggered
