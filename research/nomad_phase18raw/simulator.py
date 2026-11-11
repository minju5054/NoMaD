"""Exact Phase18/17 renderer/bootstrap, with only RAW config/executor factories."""
import ast,sys
from pathlib import Path
source=Path(__file__).parents[1]/'nomad_phase17/simulator.py';sys.path[0]=str(source.parent)
tree=ast.parse(source.read_text());mapping={'nomad_phase17.config':'nomad_phase18raw.config','nomad_phase17.execution':'nomad_phase18raw.execution'};changed=[]
for node in ast.walk(tree):
    if isinstance(node,ast.ImportFrom) and node.module in mapping:changed.append(node.module);node.module=mapping[node.module]
assert sorted(changed)==sorted(mapping)
exec(compile(tree,str(source),'exec'),dict(__name__='__main__',__file__=str(source),__package__=None))
