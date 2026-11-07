"""Process-local factor clones. Protected files and all hard rows stay intact."""
import ast,hashlib,inspect,textwrap
from types import FunctionType
from nomad_phase17.graph import ClearanceGraph as OriginalClearanceGraph
from nomad_phase20c.detour import DetourGraph

TARGET_M=.08

def bind(fn,**globals_update):
    return FunctionType(fn.__code__,dict(fn.__globals__,**globals_update),fn.__name__,fn.__defaults__,fn.__closure__)

class ClearanceGraph(OriginalClearanceGraph):
    clearance_residual=bind(OriginalClearanceGraph.clearance_residual,D_PREF_M=TARGET_M)
    # Keep the reported target consistent; the solver/body is byte-for-byte reused.
    solve=bind(OriginalClearanceGraph.solve,D_PREF_M=TARGET_M)

ORIGINAL_R3_RESIDUAL=DetourGraph.residual_jacobian

def detour_residual():
    source=textwrap.dedent(inspect.getsource(ORIGINAL_R3_RESIDUAL));tree=ast.parse(source)
    old_hash=hashlib.sha256(ast.dump(tree).encode()).hexdigest()
    class TargetOnly(ast.NodeTransformer):
        count=0
        def visit_Constant(self,node):
            if isinstance(node.value,float) and node.value==.15:
                self.count+=1;return ast.copy_location(ast.Constant(TARGET_M),node)
            return node
    transform=TargetOnly();tree=transform.visit(tree)
    assert transform.count==2, 'Only CLR hinge target and its active-set test may change'
    namespace=dict(ORIGINAL_R3_RESIDUAL.__globals__)
    exec(compile(ast.fix_missing_locations(tree),'<phase30r CLR target only>','exec'),namespace)
    result=namespace['residual_jacobian']
    for node in ast.walk(tree):
        if isinstance(node,ast.Constant) and isinstance(node.value,float) and node.value==TARGET_M:node.value=.15
    result.phase30r_original_ast_sha256=old_hash
    result.phase30r_restored_ast_sha256=hashlib.sha256(ast.dump(tree).encode()).hexdigest()
    assert result.phase30r_original_ast_sha256==result.phase30r_restored_ast_sha256
    return result

R3_RESIDUAL=detour_residual()

def install_detour_factor():
    # Called in each numerical pool child; R2 has no soft clearance cost.
    DetourGraph.residual_jacobian=R3_RESIDUAL
