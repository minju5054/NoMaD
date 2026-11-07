"""A single R2 dispatch branch becomes the existing A-mode R3 dispatch."""
import ast,copy,hashlib,inspect,textwrap
from nomad_phase20e.runtime import Execution as FrozenNormal

ORIGINAL=FrozenNormal._normal_apply

def build():
    tree=ast.parse(textwrap.dedent(inspect.getsource(ORIGINAL)));original=ast.dump(tree,include_attributes=False)
    changed=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.If):continue
        if any(isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and ast.unparse(x.value.func)=='self.repair_worker.submit' for x in node.body):
            saved=copy.deepcopy(node.body);node.body=ast.parse("self._phase34_start_A(core, refresh, switch)").body;changed.append((node,'body',saved))
        if ast.unparse(node.test)=='self.repair_pending is None and self.recovery.eligible(before[0])':
            saved=copy.deepcopy(node.test);node.test=ast.BoolOp(op=ast.And(),values=[ast.parse('self.detour is None',mode='eval').body,node.test]);changed.append((node,'test',saved))
    assert len(changed)==2,'Only dispatch and the equivalent pending-planner guard may change'
    namespace=dict(ORIGINAL.__globals__);exec(compile(ast.fix_missing_locations(tree),'<phase34-R2-bypass>','exec'),namespace)
    result=namespace['_normal_apply']
    for node,name,value in changed:setattr(node,name,value)
    assert ast.dump(tree,include_attributes=False)==original
    proof=dict(original_ast_sha256=hashlib.sha256(original.encode()).hexdigest(),restored_ast_sha256=hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest(),changes=['R2 submit body -> original start_detour(trigger=A)','pending R3 blocks RECOVER on the same tick, just as pending R2 did'])
    return result,proof

BYPASS,AST_PROOF=build()
