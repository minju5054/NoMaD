"""Process-local routing only. Frozen C0 code and all controllers are reused."""
from nomad_phase24r.online_execution import install as frozen_install
from nomad_phase24.retention import run_without_oracle,retained_apply
from nomad_phase21.execution import make_execution as original_make
from nomad_phase20f.runtime import Execution as C0Execution
from .scenes import MultiSuddenMonitor

def make_execution(c,out):
    if c['phase26_method']=='B4_ASTAR':
        import nomad_phase20d.runtime as previous
        from .astar_worker import Worker
        saved=previous.Worker;previous.Worker=Worker
        try:return retained_apply(C0Execution('M3_DETOUR',out))
        finally:previous.Worker=saved
    return retained_apply(original_make(c,out))

def install(config):
    frozen_install()
    import nomad_phase15b.execution as factory
    factory.make_execution=make_execution
    if config.get('phase26_dynamic'):
        import nomad_isaac.sudden_obstacle as sudden
        sudden.SuddenObstacleMonitor=MultiSuddenMonitor
    if config['phase16_scene']=='H1':
        # The old S1 adapter otherwise loads its straight-corridor config.
        # This is evaluation plumbing only; the controller sees the same depth.
        import nomad_phase1.s1_v2 as s1
        from nomad_isaac.clearance import MultiObstacleMonitor
        s1.CorridorOnlyMonitor=lambda ignored,out:MultiObstacleMonitor(config,out)
