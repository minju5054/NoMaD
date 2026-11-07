"""Change only the child module name, preserving both original transports."""
import subprocess
from nomad_phase29.client import Worker as OriginalNormalWorker
from nomad_phase20d.worker import Worker as OriginalPoolWorker
from .factors import bind

class Routes:
    def __init__(self,old,new):self.old=old;self.new=new
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,args,*a,**kw):
        return subprocess.Popen([self.new if x==self.old else x for x in args],*a,**kw)

class NormalWorker(OriginalNormalWorker):
    __init__=bind(OriginalNormalWorker.__init__,subprocess=Routes('nomad_phase29.worker','nomad_phase30r.worker'))

class PoolWorker(OriginalPoolWorker):
    __init__=bind(OriginalPoolWorker.__init__,subprocess=Routes('nomad_phase20d.pool','nomad_phase30r.pool'))
