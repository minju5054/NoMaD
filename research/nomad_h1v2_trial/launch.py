"""Same frozen launcher/cleanup/HMM worker; only scene/module/provenance names."""
import inspect,sys
from nomad_phase53p import launch as frozen
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify,split

class Processes(frozen.Processes):
    Popen=bind(frozen.Processes.Popen,HERE=HERE,split=split)

def launcher_main(processes):
    source=inspect.getsource(frozen.launcher_main)
    assert source.count("phase='53-P'")==1
    source=source.replace("phase='53-P'","phase='H1-v2-trial'")
    ns=dict(frozen.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify)
    exec(compile(source,__file__,'exec'),ns);return ns['launcher_main'](processes)

def main():
    assert '--smoke' not in sys.argv,'No separate smoke is registered'
    bind(frozen.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
