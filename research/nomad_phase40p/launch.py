"""Frozen launcher with one method, smoke217 and local entry point."""
import inspect
import sys
from pathlib import Path
from types import FunctionType
from nomad_phase35 import launch as frozen
from .config import HERE,RUN_ROOT,SMOKE_ROOT,METHODS,SCENES,verify


def bind(fn,**kw):
    return FunctionType(fn.__code__,dict(fn.__globals__,**kw),fn.__name__,fn.__defaults__,fn.__closure__)


class Processes(frozen.Processes):
    Popen=bind(frozen.Processes.Popen,HERE=HERE)


def launcher_main(processes):
    source=inspect.getsource(frozen.base.main)
    assert source.count('a.index==95')==1
    source=source.replace('a.index==95',"a.index==217 and a.scene=='H1'")
    def write(path,value):
        if path.name=='provenance.json':
            from nomad_isaac.common import sha256_file
            value=dict(value,phase='40-P',protocol_sha256=sha256_file(HERE/'protocol.json'),
                       source_sha256=verify()['source_sha256'],storage_version=2,executor='C0-NA')
        return frozen.base.write_json(path,value)
    def atomic(path,value,*a,**kw):
        if path.name=='storage_policy.json':value=dict(value,version='SDF_STORAGE_V2',sdf_values_stored=False,
            loader='nomad_storage_sdf.loader',full_frame_seed_per_scene=217)
        return frozen.base.atomic_json(path,value,*a,**kw)
    ns=dict(frozen.base.main.__globals__,METHODS=METHODS,SCENES=SCENES,verify=verify,subprocess=processes,
            write_json=write,atomic_json=atomic,retain_full_frames=lambda index,smoke:smoke or index==217)
    exec(compile(source,str(HERE/'launch.py'),'exec'),ns)
    return ns['main']


def main():
    root=SMOKE_ROOT if '--smoke' in sys.argv else RUN_ROOT
    out=Path(sys.argv[sys.argv.index('--output')+1]).resolve()
    assert out.is_relative_to(root.resolve()) and not out.exists()
    bind(frozen.main,HERE=HERE,RUN_ROOT=root,Processes=Processes,launcher_main=launcher_main)()


if __name__=='__main__':main()
