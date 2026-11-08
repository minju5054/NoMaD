"""Frozen Phase35 launcher with paths, protocol and provenance routed locally."""
import sys
from pathlib import Path
from types import FunctionType
from nomad_phase35 import launch as frozen
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify

def bind(fn,**kw):return FunctionType(fn.__code__,dict(fn.__globals__,**kw),fn.__name__,fn.__defaults__,fn.__closure__)

class Processes(frozen.Processes):
    Popen=bind(frozen.Processes.Popen,HERE=HERE)

launcher_main=bind(frozen.launcher_main,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify)
_main=bind(frozen.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)

def main():
    assert '--smoke' not in sys.argv
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve();assert out.is_relative_to(RUN_ROOT.resolve()/'main')
    writer=frozen.base.write_json
    def metadata(path,value):
        if path.name=='provenance.json':value=dict(value,phase='37-P',provenance_cell_filter=value['method']=='OURS+PROV',
            baseline='Phase35 OURS frozen',deviation=verify()['user_decision'])
        return writer(path,value)
    frozen.base.write_json=metadata
    try:return _main()
    finally:frozen.base.write_json=writer
if __name__=='__main__':main()
