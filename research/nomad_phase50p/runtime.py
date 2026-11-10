"""Frozen Phase47-C controller; only scenario monitor and passive logging differ."""
from nomad_phase47c.runtime import install as frozen_install,run_without_oracle

def install(config):
    frozen_install(config)
    from nomad_isaac import sudden_obstacle,async_runtime
    from .motion import MovingPersonMonitor
    sudden_obstacle.SuddenObstacleMonitor=MovingPersonMonitor
    Original=async_runtime.ExecutionThread
    class TelemetryThread(Original):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw)
            self.dynamic.depth_provider=lambda:self.stage2.depth_maps.snapshot()
    async_runtime.ExecutionThread=TelemetryThread
