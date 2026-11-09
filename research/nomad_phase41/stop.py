"""Optional terminal stop on each delivered inference, before any control.

D750 and socket release timing remain frozen. This hook never uses geometric
distance to decide whether to stop. Goal distance is evaluated in metrics only.
"""
import ast
import inspect
import json
import textwrap
import time
from nomad_isaac import async_runtime as frozen

FrozenExecutionThread=frozen.ExecutionThread


def goal_node_reached(metadata):
    topomap=metadata.get('topomap') or {}
    closest,goal=topomap.get('closest_node'),topomap.get('goal_node')
    return isinstance(closest,int) and isinstance(goal,int) and goal>=0 and closest==goal


def patched_run():
    tree=ast.parse(textwrap.dedent(inspect.getsource(FrozenExecutionThread.run)))
    class StopHook(ast.NodeTransformer):
        def __init__(self):self.geometry=0;self.delivery=0
        def visit_If(self,node):
            self.generic_visit(node)
            if ast.unparse(node.test)=="distance <= c['goal_tolerance_m']":
                node.test=ast.BoolOp(op=ast.And(),values=[ast.UnaryOp(op=ast.Not(),operand=ast.Attribute(value=ast.Name(id='self',ctx=ast.Load()),attr='nomad_goal_stop',ctx=ast.Load())),node.test])
                self.geometry+=1
            return node
        def visit_Expr(self,node):
            if isinstance(node.value,ast.Call) and ast.unparse(node.value)=='self.accept(result, sim_time)':
                self.delivery+=1
                extra=ast.parse('''
if self.declared_arrival is not None:
    append(cf, dict(simulation_time_s=sim_time, monotonic_ns=time.monotonic_ns(),
        commanded_v_m_s=0., commanded_w_rad_s=0., applied_v_m_s=0., applied_w_rad_s=0.,
        applied_command_source='DECLARED_ARRIVAL', valid=False,
        declared_arrival=self.declared_arrival))
    break
''').body
                return [node,*extra]
            return node
    visitor=StopHook();tree=visitor.visit(tree)
    assert visitor.geometry==visitor.delivery==1
    ns=dict(FrozenExecutionThread.run.__globals__)
    exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),ns)
    return ns['run']


class ExecutionThread(FrozenExecutionThread):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.nomad_goal_stop=bool(self.config.get('nomad_goal_stop',False))
        self.declared_arrival=None

    def accept(self,result,sim_time,terminal=False):
        declare=self.nomad_goal_stop and not terminal and goal_node_reached(result[0])
        super().accept(result,sim_time,terminal=terminal or declare)
        if not declare:return
        metadata=result[0];self.core.v=self.core.w=0.;self.core.command_valid=False
        if self.stage2 is not None:
            self.stage2.last_command=[0.,0.]
            self.stage2.plant.actual_w=0.
        self.reason='declared_arrival'
        self.declared_arrival=dict(id=metadata['id'],closest_node=metadata['topomap']['closest_node'],
            goal_node=metadata['topomap']['goal_node'],simulation_time_s=float(sim_time),
            tick=round(sim_time*self.config['integration_hz']),pose=self.core.pose.tolist(),
            stop_command=[0.,0.],received_monotonic_ns=metadata.get('received_monotonic_ns'),
            declared_monotonic_ns=time.monotonic_ns())
        with self.lock:
            self.state.update(command_valid=False,actual_vw=[0.,0.],declared_arrival=self.declared_arrival)
        (self.out/'declared_arrival.json').write_text(json.dumps(self.declared_arrival,indent=2)+'\n')

    run=patched_run()


def install():
    frozen.ExecutionThread=ExecutionThread
