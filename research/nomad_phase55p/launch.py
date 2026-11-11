"""Frozen Phase53 launch path, local protocol and output routing only."""
from nomad_phase35 import launch as base
from nomad_phase53p import launch as cut
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify,split
class Processes(cut.Processes):
    def Popen(self,args,*a,**kw):
        return bind(cut.Processes.Popen,HERE=HERE,split=split)(self,args,*a,**kw)
def launcher_main(processes):
    # The Phase53 factory closes over its module names; clone with the local
    # definitions so provenance, choices and frozen hash all name Phase55.
    fn=bind(cut.launcher_main,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify)(processes)
    original=fn.__globals__['write_json']
    def write(path,value):
        if path.name=='provenance.json':
            # Original writer is the Phase53 wrapper; override its fixed phase
            # with the low-level writer after explicitly filling our provenance.
            from nomad_isaac.common import write_json,sha256_file
            value=dict(value,phase='55-P',protocol_sha256=sha256_file(HERE/'protocol.json'),source_sha256=verify()['source_sha256'],storage_version=2,executor='C0-NA HOLD')
            return write_json(path,value)
        return original(path,value)
    return bind(fn,write_json=write)
def main():
    bind(base.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
