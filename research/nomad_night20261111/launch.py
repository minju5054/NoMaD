import inspect,sys
from nomad_phase53p import launch as frozen
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,SMOKE_ROOT,METHODS,SCENES,EXP,DEFS,verify,split
class Processes(frozen.Processes):Popen=bind(frozen.Processes.Popen,HERE=HERE,split=split)
def launcher_main(processes):
    source=inspect.getsource(frozen.launcher_main)
    source=source.replace("phase='53-P'","phase='NIGHT_20261111_'+EXP")
    source=source.replace("a.index==95 and a.scene=='LC_D075' and a.method=='GRAPH-HO'", "a.index==95 and a.scene==SMOKE_SCENE and a.method==SMOKE_METHOD")
    ns=dict(frozen.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify,EXP=EXP,
        SMOKE_SCENE=DEFS[EXP]['smoke']['scene'],SMOKE_METHOD=DEFS[EXP]['smoke']['method'])
    # The parser's compiled globals must include smoke names used in its assertion.
    source=source.replace('METHODS=METHODS,SCENES=SCENES,verify=verify,subprocess=processes,','METHODS=METHODS,SCENES=SCENES,verify=verify,subprocess=processes,SMOKE_SCENE=SMOKE_SCENE,SMOKE_METHOD=SMOKE_METHOD,')
    exec(compile(source,__file__,'exec'),ns);return ns['launcher_main'](processes)
def main():bind(frozen.main,HERE=HERE,RUN_ROOT=RUN_ROOT,SMOKE_ROOT=SMOKE_ROOT,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
