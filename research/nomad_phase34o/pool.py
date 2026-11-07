"""Unchanged eight-sample job/selector in a persistent four-process pool."""
from types import FunctionType
from nomad_phase20d import pool as frozen
from nomad_phase33p.storage import install
from .repair import solve_sample

_clr_globals = dict(frozen.solve_one.__globals__, solve_sample=solve_sample)
_clr_one = FunctionType(frozen.solve_one.__code__, _clr_globals,
    frozen.solve_one.__name__, frozen.solve_one.__defaults__, frozen.solve_one.__closure__)


def initialize(queue):
    install()
    frozen.initialize(queue)


def solve_one(args):
    return (_clr_one if args[2]['variant'] == 'R2_CLR' else frozen.solve_one)(args)


evaluate_job = FunctionType(frozen.evaluate_job.__code__,
    dict(frozen.evaluate_job.__globals__, solve_one=solve_one),
    frozen.evaluate_job.__name__, frozen.evaluate_job.__defaults__, frozen.evaluate_job.__closure__)
