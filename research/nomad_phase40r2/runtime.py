"""Only remove B/R3; keep the complete frozen R2, EC and waiting executor."""
from nomad_phase40p.runtime import Execution as Frozen,install as install40p,run_without_oracle
from nomad_phase24.retention import retained_apply


class DisabledTriggerB:
    def check(self,*args,**kwargs):return False,None,'TRIGGER_B_DISABLED'


class Execution(Frozen):
    def __init__(self,out):
        super().__init__(out)
        self.no_progress=DisabledTriggerB()

    def dispatch(self,core,refresh,payload):
        assert payload['kind']=='R2','R3 is disabled for OURS-R2'
        return super().dispatch(core,refresh,payload)

    def start_detour(self,*args,**kwargs):
        raise AssertionError('No trigger B or R2-to-R3 transition is allowed')

    def poll_job(self,core,refresh,switch):
        super().poll_job(core,refresh,switch)
        if self.n_after_r2:
            # Frozen PlanningBase then executes the same OURS-DETOUR alternative
            # path/EC/recovery as it did while waiting; no R3 stage is queued.
            self.n_after_r2=False
            self.nrecord('R2_FAILURE_ALTERNATIVE',tick=round(refresh['simulation_time_s']*72))

    def ec_log(self,event,**kw):
        for key in ('route','action'):
            if kw.get(key)=='R2_TO_R3':kw[key]='R2_TO_ALTERNATIVE'
        return super().ec_log(event,**kw)


def install(config):
    install40p(config)
    import nomad_phase15b.execution as factory
    factory.make_execution=lambda c,out:retained_apply(Execution(out))
