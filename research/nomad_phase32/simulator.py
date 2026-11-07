"""Numerical EC imports occur only after the frozen SimulationApp bootstrap."""
from pathlib import Path
source=Path(__file__).parents[1]/'nomad_phase26/simulator.py';code=source.read_text()
for a,b in [('from nomad_phase26.config import runtime_config','from nomad_phase32.config import runtime_config'),('from nomad_phase26.execution import install,run_without_oracle','from nomad_phase32.runtime import install,run_without_oracle')]:
 assert code.count(a)==1;code=code.replace(a,b)
exec(compile(code,str(source),'exec'),dict(__name__='__main__',__file__=str(source)))
