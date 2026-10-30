"""Phase20 executor unchanged except worker backend and the fixed 1s deadline."""
import types
import nomad_phase20.runtime as base
from .worker import RepairWorker,disposition


class Execution(base.Execution):
    def __init__(self,method,out):
        super().__init__(method,out)
        if method=='M2_REPAIR':self.repair_worker=RepairWorker(out)
    collect_repair=types.FunctionType(base.Execution.collect_repair.__code__,{**base.__dict__,'disposition':disposition},
                                     name='collect_repair',argdefs=base.Execution.collect_repair.__defaults__)


def install():
    base.install()
    import nomad_phase15b.execution as factory
    import nomad_phase2.config as placement
    from .config import place
    factory.make_execution=lambda c,out:Execution(c['phase20_method'],out)
    placement.place=place

run_without_oracle=base.run_without_oracle
