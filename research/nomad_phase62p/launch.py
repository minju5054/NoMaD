"""Phase61 oracle worker and process lifecycle; local experiment routing only."""
import inspect
from nomad_phase35 import launch as base
from nomad_phase57p import launch as template
from nomad_phase61p import launch as previous
from nomad_phase40p.launch import bind
from .config import HERE,RUN_ROOT,METHODS,SCENES,verify
class Processes(previous.Processes):
    Popen=bind(previous.Processes.Popen,HERE=HERE)
source=inspect.getsource(template.launcher_main).replace("phase='57-P'","phase='62-P'").replace('full_frame_seed_per_scene=227','full_frame_seed_per_scene=229').replace('index==227','index==229')
ns=dict(template.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify)
exec(compile(source,__file__,'exec'),ns);launcher_main=ns['launcher_main']
def main():
    import sys
    assert '--smoke' not in sys.argv
    bind(base.main,HERE=HERE,RUN_ROOT=RUN_ROOT,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
