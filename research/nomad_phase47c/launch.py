import inspect,sys
from nomad_phase40p import launch as frozen
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify


class Processes(frozen.Processes):
    def __init__(self,hmm=None):
        super().__init__()
        self.hmm=(sys.argv[sys.argv.index('--method')+1]=='OURS-DETOUR+HMM') if hmm is None else hmm
    def Popen(self,args,*a,**kw):
        if self.hmm:args=['nomad_phase43p.worker' if x=='nomad_isaac.worker' else x for x in args]
        return bind(frozen.Processes.Popen,HERE=HERE)(self,args,*a,**kw)


def launcher_main(processes):
    source=inspect.getsource(frozen.launcher_main)
    source=source.replace("phase='40-P'","phase='47-C'").replace('full_frame_seed_per_scene=217','full_frame_seed_per_scene=221').replace('index==217','index==221')
    ns=dict(frozen.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify)
    exec(compile(source,str(HERE/'launch.py'),'exec'),ns)
    return ns['launcher_main'](processes)


def main():
    assert '--smoke' not in sys.argv
    bind(frozen.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()


if __name__=='__main__':main()
