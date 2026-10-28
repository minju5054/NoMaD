"""Redirect two factories after protected SimulationApp initialization.

Only stdlib is imported here: importing SciPy/NumPy before Kit initialization
can disturb Kit extension loading. The Phase17 script and runtime are unchanged.
"""
import ast
from pathlib import Path

source=Path(__file__).parents[1]/'nomad_phase17/simulator.py'
tree=ast.parse(source.read_text())
mapping={'nomad_phase17.config':'nomad_phase18.config',
         'nomad_phase17.execution':'nomad_phase18.execution'}
changed=[]
for node in ast.walk(tree):
    if isinstance(node,ast.ImportFrom) and node.module in mapping:
        changed.append(node.module);node.module=mapping[node.module]
assert sorted(changed)==sorted(mapping)
namespace=dict(__name__='__main__',__file__=str(source),__package__=None)
exec(compile(tree,str(source),'exec'),namespace)
