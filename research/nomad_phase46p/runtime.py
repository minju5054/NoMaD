"""Remove only the ALL_UNSAFE R2 branch; B/R3 and its EC remain frozen."""
import ast,inspect,textwrap
from types import FunctionType,MethodType
from nomad_phase32.runtime import Execution as FrozenExecution
from nomad_phase20e.runtime import Execution as NormalSource
from nomad_phase35.worker import GraphWorker
from nomad_phase43p.runtime import install as install43,run_without_oracle
from nomad_phase24.retention import retained_apply
from nomad_phase24r.trigger import component_sets,PersistentNoProgress


def without_trigger_a():
    fn=NormalSource._normal_apply
    tree=ast.parse(textwrap.dedent(inspect.getsource(fn)))
    target=ast.dump(ast.parse('self.repair_worker is not None and not self.repair_worker.busy()',mode='eval').body)
    class RemoveA(ast.NodeTransformer):
        count=0
        def visit_If(self,node):
            if ast.dump(node.test)==target:
                self.count+=1
                return ast.parse("self.rlog('TRIGGER_A_DISABLED',id=switch['id'],simulation_time_s=refresh['simulation_time_s'])\ndecision=self.use_fallback(core,refresh)").body
            return self.generic_visit(node)
    change=RemoveA();tree=change.visit(tree);assert change.count==1
    scope=dict(fn.__globals__);exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),scope)
    return scope['_normal_apply']


def record_component(owner):
    """Capture the exact published field used by the frozen B predicate.

    Only depth cell coordinates are logged. No box/goal/oracle data enters
    this function or the online execution module.
    """
    trigger=owner.no_progress;assert isinstance(trigger,PersistentNoProgress)
    fn=trigger.check.__func__;choose=fn.__globals__['choose_ahead']
    def capture(field,poses,tick,cache):
        selected,info=choose(field,poses,tick,cache)
        owner.trigger_component=None;owner.trigger_component_field=None
        if selected is not None:
            owner.trigger_component_field=field
            owner.trigger_component=dict(component_id=selected['component_id'],frame_id=field.metadata['frame_id'],
                snapshot=dict(field.metadata))
        return selected,info
    trigger.check=MethodType(FunctionType(fn.__code__,dict(fn.__globals__,choose_ahead=capture),
        fn.__name__,fn.__defaults__,fn.__closure__),trigger)


class BWorker(GraphWorker):
    def submit(self,job,field):
        assert job.get('kind')=='R3' and job.get('trigger')=='B','Only trigger-B R3 jobs are enabled'
        return super().submit(job,field)


class Execution(FrozenExecution):
    _normal_apply=without_trigger_a()

    def __init__(self,method,out):
        super().__init__(method,out)
        self.trigger_component=None;self.trigger_component_field=None;record_component(self)

    def start_detour(self,core,refresh,trigger,progress):
        assert trigger=='B','Trigger A and its R2/R3 transition are disabled'
        return super().start_detour(core,refresh,trigger,progress)

    def drecord(self,event,**kw):
        if event=='TRIGGER' and kw.get('trigger')=='B':
            evidence=self.trigger_component
            assert evidence is not None and evidence['component_id']==kw['component']['component_id']
            assert evidence['frame_id']==self.no_progress.last_gate['snapshot']['frame_id']
            points=component_sets(self.trigger_component_field)[evidence['component_id']]
            kw['trigger_component_evidence']=dict(evidence,cell_centers_world=points.tolist())
        return super().drecord(event,**kw)


def install(config):
    install43(config)
    import nomad_phase15b.execution as factory
    import nomad_phase20d.runtime as original
    def make(c,out):
        saved=original.Worker;original.Worker=BWorker
        try:return retained_apply(Execution('C0-NA+EC',out))
        finally:original.Worker=saved
    factory.make_execution=make
