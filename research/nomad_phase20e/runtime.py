"""Phase20D executor unchanged except the extra NO_PROGRESS predicate."""
from types import FunctionType
from nomad_phase20d.runtime import Execution as Previous,run_without_oracle
from nomad_phase19r.evaluate import clean
from .trigger import ConditionalNoProgress


class Execution(Previous):
    # The inherited R2 serialization call references clean, omitted from the20D
    # module globals. Bind the existing helper locally; same function bytecode.
    _normal_apply=FunctionType(Previous._normal_apply.__code__,{**Previous._normal_apply.__globals__,'clean':clean})
    def __init__(self,method,out):
        super().__init__(method,out)
        if method=='M3_DETOUR':self.no_progress=ConditionalNoProgress(self)
    def drecord(self,event,**kw):
        if event=='TRIGGER' and kw.get('trigger')=='B':kw['obstacle_condition']=self.no_progress.last_gate
        super().drecord(event,**kw)


def install():
    from nomad_phase20d.runtime import install as previous_install
    previous_install()
    import nomad_phase15b.execution as factory
    factory.make_execution=lambda c,out:Execution(c['phase20_method'],out)
