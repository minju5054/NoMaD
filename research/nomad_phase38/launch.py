"""Frozen launcher with local entry point, RTC tags and registration only."""
import inspect,sys
from pathlib import Path
from types import FunctionType
from nomad_phase35 import launch as frozen
from .config import HERE,RUN_ROOT,SMOKE_ROOT,METHODS,SCENES,verify

def bind(fn,**kw):return FunctionType(fn.__code__,dict(fn.__globals__,**kw),fn.__name__,fn.__defaults__,fn.__closure__)
class Processes(frozen.Processes):
    Popen=bind(frozen.Processes.Popen,HERE=HERE)

def launcher_main(processes):
    source=inspect.getsource(frozen.base.main);assert source.count("a.method=='B2_SAFE_RTC'")==2
    source=source.replace("a.method=='B2_SAFE_RTC'","a.method in ('RTC','RTC+EC')")
    def write(path,value):
        if path.name=='provenance.json':
            from nomad_isaac.common import sha256_file
            value=dict(value,phase='38',protocol_sha256=sha256_file(HERE/'protocol.json'),storage_version=2,executor='C0-NA',
                method_source='Phase35 frozen except registered Phase38 extensions',source_sha256=verify()['source_sha256'])
        return frozen.base.write_json(path,value)
    def atomic(path,value,*args,**kw):
        if path.name=='storage_policy.json':value=dict(value,version='SDF_STORAGE_V2',sdf_values_stored=False,loader='nomad_storage_sdf.loader')
        return frozen.base.atomic_json(path,value,*args,**kw)
    namespace=dict(frozen.base.main.__globals__,METHODS=METHODS,SCENES=SCENES,verify=verify,subprocess=processes,write_json=write,atomic_json=atomic)
    exec(compile(source,str(HERE/'launch.py'),'exec'),namespace);return namespace['main']

def main():
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve();smoke='--smoke' in sys.argv
    root=SMOKE_ROOT if smoke else RUN_ROOT
    assert out.is_relative_to(root.resolve()) and not out.exists()
    return bind(frozen.main,HERE=HERE,RUN_ROOT=root,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
