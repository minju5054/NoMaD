"""Environment delay registration only; frozen controller/HMM/EC unchanged."""
import ast,inspect
from nomad_phase47c.runtime import install as frozen_install,run_without_oracle as frozen_run

def install(c):
    frozen_install(c)
    from .geometry import install as install_geometry
    install_geometry(c)

def driver_tree(source,retain):
    tree=ast.parse(source);fn=tree.body[0];gate=0;allow=0;register=0
    # Preserve the same no-oracle gate and archival guard used by Phase47.
    for i,node in enumerate(fn.body):
        if isinstance(node,ast.If) and ast.unparse(node.test)=='s1 and engine.dynamic is not None':
            fn.body[i]=ast.Assign(targets=[ast.Name(id='oracle_gate',ctx=ast.Store())],value=ast.Constant(value=None));gate+=1
    class DelayEnvironment(ast.NodeTransformer):
        def visit_Assert(self,node):
            nonlocal allow
            if ast.unparse(node.test)=='uniform_delivery_delay_s in (0.0, 0.25, 0.5, 0.75)':
                node.test.comparators[0].elts.append(ast.Constant(value=1.5));allow+=1
            return node
        def visit_Assign(self,node):
            nonlocal register
            if any(isinstance(t,ast.Name) and t.id=='delay_protocol' for t in node.targets) and 'uniform_latency_protocol.json' in ast.unparse(node.value):
                register+=1
                return [node,*ast.parse("delay_protocol = {**delay_protocol, 'conditions_delay_s': {**delay_protocol['conditions_delay_s'], 'D1500': 1.5}}").body]
            return self.generic_visit(node)
    tree=DelayEnvironment().visit(tree);assert (gate,allow,register)==(1,1,1)
    if not retain:
        from nomad_phase24.retention import GuardRGBWrites
        guard=GuardRGBWrites();tree=guard.visit(tree);assert guard.count==4
    return ast.fix_missing_locations(tree)

def run_without_oracle(*args,**kwargs):
    c=args[0];delay=kwargs.get('uniform_delivery_delay_s');assert delay==c['phase51p_delay_s']
    if delay==.75:return frozen_run(*args,**kwargs)
    assert delay==1.5 and c['phase51p_condition']=='L150'
    from nomad_isaac import async_runtime as original
    from nomad_phase24.retention import full_frames
    tree=driver_tree(inspect.getsource(original.run_async),full_frames())
    ns=dict(original.__dict__,_phase24_full_frames=full_frames())
    exec(compile(tree,original.__file__,'exec'),ns)
    return ns['run_async'](*args,**kwargs)
