"""Reuse C0 path installation verbatim, replacing only its alignment executor."""
from types import FunctionType
from nomad_phase20.runtime import Execution as PathInstaller
from nomad_phase20f.runtime import Execution as C0Execution
from .alignment import NoAlignment

def installer(controller):
    original=PathInstaller.new_path
    # A private function-global dictionary avoids process-wide runtime patches.
    return FunctionType(original.__code__,dict(original.__globals__,SPAlignment=controller),
                        original.__name__,original.__defaults__,original.__closure__)

class NAExecution(C0Execution):
    new_path=installer(NoAlignment)
