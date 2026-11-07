from types import FunctionType
from nomad_phase20d import pool as frozen
from nomad_phase33p.storage import install

def initialize(q):install();frozen.initialize(q)
def main():
    install()
    FunctionType(frozen.main.__code__,dict(frozen.main.__globals__,initialize=initialize),
        frozen.main.__name__,frozen.main.__defaults__,frozen.main.__closure__)()
if __name__=='__main__':main()
