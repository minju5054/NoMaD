"""Explicit nightly deltas only: common tail, frozen R2/R3 or requested HOLD."""
import json
from types import MethodType
from nomad_phase53p.runtime import Execution as Handoff,frozen_install,run_without_oracle
from nomad_phase32.runtime import Execution as OriginalEC
from nomad_phase52p.runtime import HoldCore,Execution as OldHold
from nomad_phase24.retention import retained_apply
from nomad_phase28.telemetry import builtin

class HoldExecution(Handoff):
    def __init__(self,method,out):
        super().__init__('CUT',out)
        self.hold_rejected=False;self.rec_log=(out/'hold.jsonl').open('x')
        if method=='GRAPH-HOLD':
            from .worker import Client
            self.ho_method='GRAPH-HO';self.ho_worker=Client(out)
    def record52(self,event,**kw):
        self.rec_log.write(json.dumps(builtin(dict(event=event,**kw)),allow_nan=False)+'\n');self.rec_log.flush()
    set_hold=OldHold.set_hold
    try_hold=OldHold.try_hold
    def ec_stop(self,refresh,reason):
        core,_=self.ec_context
        if self.try_hold(core,refresh,reason):return
        self.set_hold(False,refresh['simulation_time_s'],reason);super().ec_stop(refresh,reason)
    def use_fallback(self,core,refresh):
        if self.try_hold(core,refresh,'ALL_DEPTH_UNSAFE'):detail=dict(reason='ACTIVE_EC_PASS',minimum_remaining_length_removed=True)
        else:
            self.set_hold(False,refresh['simulation_time_s'],'ACTIVE_EC_REJECT_OR_NO_PATH')
            OriginalEC.ec_stop(self,refresh,'NO_ACTIVE_EC_PATH');detail=dict(reason='ACTIVE_EC_REJECT_OR_NO_PATH',minimum_remaining_length_removed=True)
            self.recovery.decision('STOP_WAIT')
        self.fallback_log.write(json.dumps(builtin(dict(id=self.active_id,simulation_time_s=refresh['simulation_time_s'],mode=self.mode,path_source_id=self.path_source_id,**detail)))+'\n');self.fallback_log.flush();return detail
    def install_certified(self,*args,**kwargs):
        result=super().install_certified(*args,**kwargs);self.set_hold(False,args[2]['simulation_time_s'],'PATH_INSTALLED');return result
    def close(self):
        try:super().close()
        finally:self.rec_log.close()

def make(c,out):
    method=c['night_method']
    if method=='OURS-R3':
        # Phase38 OURS factory is exactly the frozen Phase35 R2/R3+EC stack.
        from nomad_phase35.runtime import make_execution
        e=make_execution(c,out)
        e.ec_check=MethodType(Handoff.ec_check,e)
        return e
    if method in ('CUT-HOLD','GRAPH-HOLD'):return retained_apply(HoldExecution(method,out))
    return retained_apply(Handoff(method,out))

def install(c):
    frozen_install(c)
    import nomad_phase15b.execution as factory
    import nomad_phase8.execution as overnight
    factory.make_execution=make;overnight.OvernightExecution=make
    if c['night_experiment']=='E2':
        import nomad_isaac.async_runtime as engine
        engine.WaypointExecution=HoldCore
    if c.get('h1v2'):
        from nomad_h1v2.scene import install_environment
        install_environment(c)
