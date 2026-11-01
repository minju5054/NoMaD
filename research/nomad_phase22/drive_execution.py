"""Reuse frozen21 execution; P2F changes only its CPU solver backend."""
import threading
from nomad_phase21.execution import make_execution as previous_factory
from nomad_phase20f.runtime import Execution as Frozen,run_without_oracle

class AnchorBus:
    def __init__(self):self.lock=threading.Lock();self.value=None
    def publish(self,previous,tick):
        with self.lock:
            if self.value is None:self.value=dict(anchor_xy=list(previous[:2]),anchor_tick=max(0,tick-1),anchor_source='SPAWN_PREVIOUS_ODOMETRY')
    def get(self,job):
        with self.lock:return dict(self.value) if self.value else dict(anchor_xy=job['B'][:2],anchor_tick=round(job['simulation_time_s']*72),anchor_source='CURRENT_B_PRE_SPAWN')
ANCHOR=AnchorBus()

def make_execution(c,out):
    if c['phase22_method']!='P2F_ASTAR_GRAPH':return previous_factory(c,out)
    import nomad_phase20d.runtime as previous
    from .drive_backend import Worker
    saved=previous.Worker;previous.Worker=lambda out:Worker(out,ANCHOR.get)
    try:return Frozen('M3_DETOUR',out)
    finally:previous.Worker=saved

def install():
    from nomad_phase21.execution import install as previous_install
    previous_install()
    import nomad_phase15b.execution as factory
    import nomad_phase2.config as placement
    import nomad_isaac.sudden_obstacle as sudden
    from .drive_geometry import monitor
    from .drive_config import place,triggered
    factory.make_execution=make_execution;placement.place=place;placement.triggered=triggered;sudden.ObstacleMonitor=monitor
    original=sudden.SuddenObstacleMonitor
    class Monitor(original):
        def observe_tick(self,tick,previous,pose,*args,**kwargs):
            before=self.spawn;r=super().observe_tick(tick,previous,pose,*args,**kwargs)
            if before is None and self.spawn is not None:ANCHOR.publish(previous,tick)
            return r
    sudden.SuddenObstacleMonitor=Monitor
