"""Private import routing; CPU7 pin still precedes numerical library imports."""
import ast,inspect,textwrap
from nomad_phase29 import worker as original

def route(fn,**updates):
    tree=ast.parse(textwrap.dedent(inspect.getsource(fn)));count=0
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom) and node.module=='nomad_phase17.graph':
            assert [a.name for a in node.names]==['ClearanceGraph']
            node.module='nomad_phase30r.factors';count+=1
    assert count==1
    namespace=dict(fn.__globals__,**updates)
    exec(compile(ast.fix_missing_locations(tree),'<phase30r worker import routing>','exec'),namespace)
    return namespace[fn.__name__]

solve=route(original.solve)
main=route(original.main,solve=solve)
if __name__=='__main__':main()
