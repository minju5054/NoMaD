"""Phase40-R2 launcher with local method/provenance routing; no smoke."""
import inspect,sys
from nomad_phase40p import launch as frozen
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify


class Processes(frozen.Processes):
    Popen=bind(frozen.Processes.Popen,HERE=HERE)


def launcher_main(processes):
    source=inspect.getsource(frozen.launcher_main);assert source.count("phase='40-P'")==1
    source=source.replace("phase='40-P'","phase='41'")
    ns=dict(frozen.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify)
    exec(compile(source,str(HERE/'launch.py'),'exec'),ns)
    return ns['launcher_main'](processes)


def main():
    assert '--smoke' not in sys.argv
    bind(frozen.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()


if __name__=='__main__':main()
