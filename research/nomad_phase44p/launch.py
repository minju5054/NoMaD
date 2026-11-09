import inspect,sys
from nomad_phase40p import launch as frozen
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify


class Processes(frozen.Processes):
    def Popen(self,args,*a,**kw):
        args=['nomad_phase43p.worker' if x=='nomad_isaac.worker' else x for x in args]
        return bind(frozen.Processes.Popen,HERE=HERE)(self,args,*a,**kw)


def launcher_main(processes):
    source=inspect.getsource(frozen.launcher_main).replace("phase='40-P'","phase='44-P'")
    ns=dict(frozen.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=lambda:verify(require_maps=True))
    exec(compile(source,str(HERE/'launch.py'),'exec'),ns)
    return ns['launcher_main'](processes)


def main():
    assert '--smoke' not in sys.argv
    bind(frozen.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()


if __name__=='__main__':main()
