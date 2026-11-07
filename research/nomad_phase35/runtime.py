"""Only executor/solver routing; frozen policy, EC, controllers and evaluator."""
from types import FunctionType
from nomad_phase26.execution import install as frozen_install,run_without_oracle
from nomad_phase24.retention import retained_apply
from nomad_phase32.runtime import Execution as ECExecution
from nomad_phase21.execution import RawExecution,TEExecution
from nomad_phase20f.runtime import Execution as FrozenExecution
from nomad_phase28.runtime import installer
from nomad_phase28.alignment import NoAlignment
from nomad_phase33p.storage import install as install_storage

NA_INSTALL=installer(NoAlignment)

class RawNA(RawExecution):
    new_path=NA_INSTALL

class RTCNA(FrozenExecution):
    new_path=NA_INSTALL

class NAInstallBridge(TEExecution.__bases__[0]):
    new_path=NA_INSTALL

class TENA(TEExecution,NAInstallBridge):
    # TE.new_path's super() resolves only its installer through the bridge.
    # The original TEProfile still supplies ensemble steering/expiry/KEEP.
    pass

def make_execution(config,out):
    method=config['phase35_method']
    if method in ('OURS','ASTAR+EC'):
        import nomad_phase20d.runtime as d
        from .worker import GraphWorker,AStarWorker
        original=d.Worker;d.Worker=AStarWorker if method=='ASTAR+EC' else GraphWorker
        try:execution=ECExecution('C0-NA+EC',out)
        finally:d.Worker=original
    elif method=='NOMAD_RAW':execution=RawNA(out)
    elif method=='SAFE_TE':execution=TENA(out)
    elif method=='SAFE_RTC':execution=RTCNA('M1_ROTATE',out)
    else:raise ValueError(method)
    return retained_apply(execution)

def install(config):
    frozen_install(config);install_storage()
    import nomad_phase15b.execution as factory
    factory.make_execution=make_execution
