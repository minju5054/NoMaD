"""Frozen process lifecycle, per-method RAW/HMM route and local provenance."""
import inspect,sys
from nomad_phase35 import launch as base
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify
class Processes(base.Processes):
    def __init__(self,hmm=None):
        super().__init__();self.hmm=(sys.argv[sys.argv.index('--method')+1]!='NOMAD_RAW') if hmm is None else hmm
    def Popen(self,args,*a,**kw):
        if self.hmm:args=['nomad_phase43p.worker' if x=='nomad_isaac.worker' else x for x in args]
        return bind(base.Processes.Popen,HERE=HERE)(self,args,*a,**kw)
def launcher_main(processes):
    source=inspect.getsource(base.base.main)
    def write(path,value):
        if path.name=='provenance.json':
            from nomad_isaac.common import sha256_file
            value=dict(value,phase='57-P',protocol_sha256=sha256_file(HERE/'protocol.json'),source_sha256=verify()['source_sha256'],storage_version=2)
        return base.base.write_json(path,value)
    def atomic(path,value,*a,**kw):
        if path.name=='storage_policy.json':value=dict(value,version='SDF_STORAGE_V2',sdf_values_stored=False,loader='nomad_storage_sdf.loader',full_frame_seed_per_scene=227)
        return base.base.atomic_json(path,value,*a,**kw)
    ns=dict(base.base.main.__globals__,METHODS=METHODS,SCENES=SCENES,verify=verify,subprocess=processes,write_json=write,
        atomic_json=atomic,retain_full_frames=lambda index,smoke:index==227)
    exec(compile(source,__file__,'exec'),ns);return ns['main']
def main():
    assert '--smoke' not in sys.argv
    bind(base.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
