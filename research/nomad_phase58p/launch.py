"""Reuse the Phase57 launch path; all three methods use the frozen HMM worker."""
import inspect
from nomad_phase35 import launch as base
from nomad_phase57p import launch as previous
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify
class Processes(previous.Processes):
    def __init__(self):super().__init__(hmm=True)
    Popen=bind(previous.Processes.Popen,HERE=HERE)
source=inspect.getsource(previous.launcher_main).replace("phase='57-P'","phase='58-P'")
ns=dict(previous.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify)
exec(compile(source,__file__,'exec'),ns);launcher_main=ns['launcher_main']
def main():
    import sys
    assert '--smoke' not in sys.argv
    bind(base.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
