"""Frozen bridges, replacing only the child module for storage-v2 loading."""
import subprocess
from types import FunctionType
from nomad_phase20d.worker import Worker as FrozenGraph
from nomad_phase21.worker import Worker as FrozenAStar

class Processes:
    def __init__(self,source,target):self.source=source;self.target=target
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,args,*a,**kw):return subprocess.Popen([self.target if x==self.source else x for x in args],*a,**kw)

def init(original,source,target):
    return FunctionType(original.__code__,dict(original.__globals__,subprocess=Processes(source,target)),
                        original.__name__,original.__defaults__,original.__closure__)

class GraphWorker(FrozenGraph):
    __init__=init(FrozenGraph.__init__,'nomad_phase20d.pool','nomad_phase35.graph_pool')

class AStarWorker(FrozenAStar):
    __init__=init(FrozenAStar.__init__,'nomad_phase21.pool','nomad_phase35.astar_pool')
