"""Change only the B cell-count predicate in the Phase35 OURS instance."""
from types import FunctionType
from nomad_phase35 import runtime as frozen
from nomad_phase24r.trigger import PersistentNoProgress
from nomad_phase37b.rules import component_sets,choose_ahead
from .provenance import ProvenPublisher

run_without_oracle=frozen.run_without_oracle


class ProvenNoProgress(PersistentNoProgress):
    check=FunctionType(PersistentNoProgress.check.__code__,
        dict(PersistentNoProgress.check.__globals__,component_sets=component_sets,choose_ahead=choose_ahead),
        PersistentNoProgress.check.__name__,PersistentNoProgress.check.__defaults__,PersistentNoProgress.check.__closure__)


def make_execution(config,out):
    execution=frozen.make_execution(config,out)
    if config['phase37p_method']=='OURS+PROV':execution.no_progress=ProvenNoProgress(execution)
    return execution


def install(config):
    frozen.install(config)
    import nomad_phase15b.execution as factory
    import nomad_phase8.execution as overnight
    import nomad_phase15b.depth as depth
    factory.make_execution=make_execution
    original=overnight.OvernightExecution
    overnight.OvernightExecution=lambda c,out:make_execution(c,out) if c.get('phase37p') else original(c,out)
    if config['phase37p_method']=='OURS+PROV':depth.DepthMapThread=ProvenPublisher
