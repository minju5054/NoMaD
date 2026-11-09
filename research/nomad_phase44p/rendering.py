"""Frozen renderer plus materials after the same wall-geometry validation."""
from types import FunctionType
from nomad_phase26 import rendering as frozen
from nomad_isaac.common import write_json
from .appearance import apply


def make(base,config,out):
    def checked(stage,c,b):
        geometry=frozen.repair_and_check(stage,c,b)
        write_json(out/'appearance_check.json',apply(stage,c,b))
        return geometry
    fn=frozen.make
    return FunctionType(fn.__code__,dict(fn.__globals__,repair_and_check=checked),fn.__name__,fn.__defaults__,fn.__closure__)(base,config,out)
