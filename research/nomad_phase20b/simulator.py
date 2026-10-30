"""Reuse Phase20 renderer/bootstrap, redirect only level configuration/executor."""
import ast,sys
from pathlib import Path
source=Path(__file__).parents[1]/'nomad_phase20/simulator.py'
sys.path[0]=str(source.parent)
# Remove the level from argv before the protected parser builds Kit arguments.
idx=sys.argv.index('--level');level=sys.argv[idx+1];del sys.argv[idx:idx+2]
assert level in ('L2','L3')
tree=ast.parse(source.read_text());imports=0;calls=0
for node in ast.walk(tree):
    if isinstance(node,ast.ImportFrom) and node.module in ('nomad_phase20.config','nomad_phase20.runtime'):
        node.module=node.module.replace('nomad_phase20.','nomad_phase20b.');imports+=1
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='runtime_config':
        node.keywords.append(ast.keyword(arg='level',value=ast.Constant(value=level)));calls+=1
assert imports==2 and calls==1
exec(compile(ast.fix_missing_locations(tree),str(source),'exec'),dict(__name__='__main__',__file__=str(source),__package__=None))
