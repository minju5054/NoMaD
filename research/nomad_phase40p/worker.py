"""Existing storage-v2 bridge, local VN pool entry point only."""
from nomad_phase20d.worker import Worker as Frozen
from nomad_phase35.worker import init


class Worker(Frozen):
    __init__ = init(Frozen.__init__, 'nomad_phase20d.pool', 'nomad_phase40p.pool')
