"""Frozen R2/R3 pool with storage-v2 loading installed in every child."""
from types import FunctionType
from nomad_phase20d import pool as frozen
from nomad_phase33p.storage import install

def initialize(q):
    install();frozen.initialize(q)

def main():
    install()
    fn=FunctionType(frozen.main.__code__,dict(frozen.main.__globals__,initialize=initialize),frozen.main.__name__,frozen.main.__defaults__,frozen.main.__closure__)
    fn()

if __name__=='__main__':main()
