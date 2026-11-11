"""Frozen startup, local routing and truthful oracle-localization provenance."""
from pathlib import Path
source=Path(__file__).parents[1]/'nomad_phase26/simulator.py';code=source.read_text()
for old,new in [('from nomad_phase26.config import runtime_config','from nomad_phase61p.config import runtime_config'),
                ('from nomad_phase26.execution import install,run_without_oracle','from nomad_phase61p.runtime import install,run_without_oracle'),
                ('oracle_used_for_control=False','oracle_used_for_control=True,oracle_localization_only=True,oracle_obstacles_for_control=False')]:
    assert code.count(old)==1;code=code.replace(old,new)
exec(compile(code,str(source),'exec'),dict(__name__='__main__',__file__=str(source)))
