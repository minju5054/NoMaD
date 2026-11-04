"""Protected Phase21 renderer; initialize SimulationApp before numerical imports."""
import ast,sys,os
from pathlib import Path
source=Path(__file__).parents[1]/'nomad_phase21/simulator.py';tree=ast.parse(source.read_text())
for node in ast.walk(tree):
    if isinstance(node,ast.ImportFrom) and node.module in ('nomad_phase21.config','nomad_phase21.execution'):
        node.module='nomad_phase24.'+('online_config' if node.module.endswith('config') else 'online_execution')
    if isinstance(node,ast.List) and [e.value for e in node.elts if isinstance(e,ast.Constant)]==['L2','L2A']:
        node.elts=[ast.Constant(value='L2'),ast.Constant(value='SLW')]
    if isinstance(node,ast.Constant) and isinstance(node.value,str) and 'adaptive=True\n' in node.value:
        node.value=node.value.replace('adaptive=True\n',"adaptive=('dynamic_obstacle' in config)\n")
from nomad_phase24.retention import GuardRGBWrites
guard=GuardRGBWrites();tree=guard.visit(tree);assert guard.count==2
exec(compile(ast.fix_missing_locations(tree),str(source),'exec'),dict(__name__='__main__',__file__=str(source),__package__=None,_phase24_full_frames=os.environ.get('NOMAD_PHASE24_FULL_FRAMES','1')=='1'))
