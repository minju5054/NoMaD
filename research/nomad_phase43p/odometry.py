"""Capture-only metadata adapter: exact72Hz travel at the input image tick."""
import numpy as np
from nomad_phase41.stop import ExecutionThread as Phase41Thread
from nomad_isaac.async_core import AsyncClient as FrozenClient


class ExecutionThread(Phase41Thread):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.hmm_odometry=[];self.hmm_total=0.
        original=self.stage2.integrate_record
        def record(before,after):
            original(before,after)
            tick=self.stage2.plant.last_tick
            assert tick==len(self.hmm_odometry)
            self.hmm_total+=float(np.linalg.norm(np.asarray(after)[:2]-np.asarray(before)[:2]))
            self.hmm_odometry.append(self.hmm_total)
        self.stage2.integrate_record=record

    def odometry_at_tick(self,tick):
        if tick==0 and not self.hmm_odometry:return 0.
        assert 0<=tick<len(self.hmm_odometry),'Observation predates/misses recorded odometry'
        return float(self.hmm_odometry[tick])


class Client(FrozenClient):
    def submit(self,metadata,**arrays):
        # The renderer may block while execution continues. Use the captured
        # observation's tick, never the later submit-time robot state.
        engine=self.snapshot.__self__;tick=round(metadata['observation_sim_s']*72)
        metadata['hmm_odometry_total_m']=engine.odometry_at_tick(tick)
        metadata['hmm_odometry_tick']=tick
        return super().submit(metadata,**arrays)
