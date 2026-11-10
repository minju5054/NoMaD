"""Same Phase26/35 process lifecycle; local names, delay and HMM routing only."""
import inspect,os,sys
from pathlib import Path
from nomad_phase35 import launch as base
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,SMOKE_ROOT,METHODS,SCENES,verify,split

class Processes(base.Processes):
    def Popen(self,args,*a,**kw):
        args=['nomad_phase43p.worker' if x=='nomad_isaac.worker' else x for x in args]
        if '--level' in args and '--delay' in args:
            _,condition=split(args[args.index('--level')+1]);args[args.index('--delay')+1]='1.5' if condition=='D150' else '.75'
        return bind(base.Processes.Popen,HERE=HERE)(self,args,*a,**kw)

def launcher_main(processes):
    source=inspect.getsource(base.base.main)
    source=source.replace('a.index==95',"a.index==95 and a.scene=='LC_D075' and a.method=='GRAPH-HO'")
    def write(path,value):
        if path.name=='provenance.json':
            from nomad_isaac.common import sha256_file
            value=dict(value,phase='53-P',protocol_sha256=sha256_file(HERE/'protocol.json'),source_sha256=verify()['source_sha256'],storage_version=2,executor='C0-NA')
        return base.base.write_json(path,value)
    def atomic(path,value,*a,**kw):
        if path.name=='storage_policy.json':value=dict(value,version='SDF_STORAGE_V2',sdf_values_stored=False,loader='nomad_storage_sdf.loader',full_frame_seed_per_scene=221)
        return base.base.atomic_json(path,value,*a,**kw)
    ns=dict(base.base.main.__globals__,METHODS=METHODS,SCENES=SCENES,verify=verify,subprocess=processes,
        write_json=write,atomic_json=atomic,retain_full_frames=lambda index,smoke:smoke or index==221)
    exec(compile(source,__file__,'exec'),ns);return ns['main']

def main():
    root=SMOKE_ROOT if '--smoke' in sys.argv else RUN_ROOT
    bind(base.main,HERE=HERE,RUN_ROOT=root,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
