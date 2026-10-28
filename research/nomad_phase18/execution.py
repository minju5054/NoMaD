"""RTC changes generation only; all six use the unmodified Phase17 SAFE executor."""
from nomad_phase17.execution import SafeExecution,install_runtime_adapters as base_install
from .config import METHODS

def make_execution(config,out):
    assert config.get('phase18') and config['phase15b_method'] in METHODS
    return SafeExecution(config['phase15b_method'],out)

def install_runtime_adapters():
    base_install()
    import nomad_phase15b.execution as runtime
    runtime.make_execution=make_execution
