"""Phase32 C0-NA+EC unchanged except the optional A -> R3 route."""
import json
from nomad_phase32.runtime import Execution as FrozenExecution,install as frozen_install,run_without_oracle
from nomad_phase24.retention import retained_apply
from nomad_phase28.telemetry import builtin
from nomad_phase33p.storage import install as install_storage
from .routing import ORIGINAL,BYPASS

BASE='C0-NA+EC';VARIANT='C0-NA+EC-R2'

class Execution(FrozenExecution):
    def __init__(self,method,out):
        assert method in (BASE,VARIANT);self.phase34_method=method
        super().__init__(BASE,out)
        self.phase34_log=(out/'phase34_events.jsonl').open('x')
    def record34(self,event,**kw):
        self.phase34_log.write(json.dumps(builtin(dict(event=event,method=self.phase34_method,**kw)),allow_nan=False)+'\n');self.phase34_log.flush()
    def _normal_apply(self,core,refresh,switch):
        return (BYPASS if self.phase34_method==VARIANT else ORIGINAL)(self,core,refresh,switch)
    def _phase34_start_A(self,core,refresh,switch):
        self.record34('R2_BYPASSED',id=switch['id'],simulation_time_s=refresh['simulation_time_s'],pose=core.pose.tolist())
        self.start_detour(core,refresh,'A',None)
    def start_detour(self,core,refresh,trigger,progress):
        old=self.detour
        super().start_detour(core,refresh,trigger,progress)
        if old is None and self.detour is not None and trigger=='A':
            self.record34('A_R3_STARTED',job_id=self.detour['job_id'],id=self.detour['id'],simulation_time_s=refresh['simulation_time_s'],B=self.detour['B'],u_ref=self.detour['u_ref'],r2_bypassed=self.phase34_method==VARIANT)
    def close(self):
        try:super().close()
        finally:self.phase34_log.close()

def install(config):
    frozen_install(config);install_storage()
    import nomad_phase20d.runtime as d
    import nomad_phase15b.execution as factory
    from .worker import Worker
    d.Worker=Worker
    factory.make_execution=lambda c,out:retained_apply(Execution(c['phase34_method'],out))
