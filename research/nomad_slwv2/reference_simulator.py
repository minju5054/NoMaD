"""Exact Phase17 reference renderer and 2s node capture, with new scene metadata."""
import ast
import sys
from pathlib import Path
source=Path(__file__).parents[1]/'nomad_phase17/simulator.py';sys.path[0]=str(source.parent)
code=source.read_text();old='from nomad_phase17.config import scene,protocol,runtime_config'
assert code.count(old)==1;code=code.replace(old,'from nomad_slwv2.config import scene,protocol,runtime_config')
old="ROOT/'research/nomad_phase17/protocol.json'"
assert code.count(old)==1;code=code.replace(old,"ROOT/'research/nomad_slwv2/protocol.json'")
exec(compile(ast.parse(code),str(source),'exec'),dict(__name__='__main__',__file__=str(source),__package__=None))
