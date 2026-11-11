"""Reuse Phase55 11-start/four-process solver and RPC; pass goal_xy only."""
import inspect,subprocess
from nomad_phase55p import worker as frozen
from nomad_phase40p.launch import bind

class Processes:
    def __getattr__(self,k):return getattr(subprocess,k)
    def Popen(self,args,*a,**kw):return subprocess.Popen(['nomad_phase62p.worker' if x=='nomad_phase55p.worker' else x for x in args],*a,**kw)
class Client(frozen.Client):
    __init__=bind(frozen.Client.__init__,subprocess=Processes())

source=inspect.getsource(frozen.start_one)
old='from .graph import Graph,solve_start';assert source.count(old)==1
source=source.replace(old,'from nomad_phase62p.graph import Graph,solve_start')
old="g=Graph(job['initial'],job['omega'],job['samples_world'],FIELD,job['previous'],job['simulation_time_s'])";assert source.count(old)==1
source=source.replace(old,old[:-1]+",goal_xy=job['goal_xy'])")
ns=dict(frozen.start_one.__globals__,__name__=__name__)
exec(compile(source,__file__,'exec'),ns);start_one=ns['start_one']
solve=bind(frozen.solve,start_one=start_one)
def main():return bind(frozen.main,solve=solve)()
if __name__=='__main__':main()
