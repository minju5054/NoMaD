"""Frozen Kit bootstrap; no numerical imports before SimulationApp."""
from pathlib import Path
source=Path(__file__).parents[1]/'nomad_phase26/simulator.py';code=source.read_text()
for old,new in [('from nomad_phase26.config import runtime_config','from nomad_phase53p.config import runtime_config'),
                ('from nomad_phase26.execution import install,run_without_oracle','from nomad_phase53p.runtime import install,run_without_oracle')]:
    assert code.count(old)==1;code=code.replace(old,new)
exec(compile(code,str(source),'exec'),dict(__name__='__main__',__file__=str(source)))
