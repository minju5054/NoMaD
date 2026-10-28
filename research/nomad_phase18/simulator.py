"""Opt-in process-local factories around the untouched Phase17 renderer/core."""
import runpy
from pathlib import Path
import nomad_phase17.config as config17
import nomad_phase17.execution as execution17
from nomad_phase18.config import scene,protocol,runtime_config
from nomad_phase18.execution import install_runtime_adapters

config17.scene=scene
config17.protocol=protocol
config17.runtime_config=runtime_config
execution17.install_runtime_adapters=install_runtime_adapters
runpy.run_path(str(Path(__file__).parents[1]/'nomad_phase17/simulator.py'),run_name='__main__')
