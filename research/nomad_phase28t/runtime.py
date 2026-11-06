"""Timing-only binding of the existing R1 H lifecycle, plus worker isolation."""
import os
from nomad_phase28.online_r1 import R1Execution,bind
from nomad_phase28.handoff import HExecution
from nomad_phase28.graph_r1 import R1Follower
from nomad_phase28.runtime import NAExecution
from nomad_phase28.handoff import install as original_install,run_without_oracle
from nomad_phase24.retention import retained_apply
from .timing import solve,predict,application_certificate
from .client import ProcessWorker

NEW_PATH=bind(HExecution.new_path,solve=solve,predict=predict)
NEW_CASE=bind(R1Execution.new_path,_new_path=NEW_PATH)
COLLECT=bind(HExecution.collect_h,TimedFollower=R1Follower,certificate=application_certificate)

class TimingExecution(R1Execution):
    new_path=NEW_CASE
    collect_h=COLLECT
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw);self.h_pool.shutdown(wait=True,cancel_futures=True)
        cpu=os.environ.get('NOMAD_PHASE28T_WORKER_CPU')
        self.h_pool=ProcessWorker(self.out,int(cpu) if cpu is not None else None)
        self.raw_record('WORKER_READY',**self.h_pool.info)
    def finalize_telemetry(self):
        # R1.close has drained the executor before this callback.
        for job,future in sorted(self.r1_futures.items()):
            if future.done():
                try:r=future.result()
                except Exception as exc:self.raw_record('TIMING_RESULT',job_id=job,error=repr(exc));continue
                self.raw_record('TIMING_RESULT',job_id=job,case_id=self.r1_job_cases.get(job),result=r)
        super().finalize_telemetry()

def install(config):
    assert config.get('phase28t') and config['phase28_method']=='C0-H'
    original_install(config)
    import nomad_phase15b.execution as factory
    factory.make_execution=lambda c,out:retained_apply(TimingExecution('M3_DETOUR',out,c['phase28_alpha']))
