"""Frozen G18 lifecycle; only route its two numerical worker entry points."""
from nomad_phase29.runtime import PathExecution as Original,original_install,run_without_oracle
from nomad_phase24.retention import retained_apply
from .client import NormalWorker,PoolWorker
from .factors import bind

class PathExecution(Original):
    __init__=bind(Original.__init__,Worker=NormalWorker)

def make(c,out):
    assert c['phase29_method']=='G18-R'
    import nomad_phase20d.runtime as detour_runtime
    saved=detour_runtime.Worker;detour_runtime.Worker=PoolWorker
    try:obj=PathExecution('G18',out)
    finally:detour_runtime.Worker=saved
    obj.path_method='G18-R'
    return retained_apply(obj)

def install(config):
    original_install(config)
    import nomad_phase15b.execution as factory
    factory.make_execution=make
