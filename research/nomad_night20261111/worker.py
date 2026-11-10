"""Same synchronous RPC, only the registered Phase54 graph subclass changes."""
import inspect,subprocess,json,sys,traceback
from nomad_phase53p import worker as frozen
from nomad_phase40p.launch import bind
class Processes:
    def __getattr__(self,k):return getattr(subprocess,k)
    def Popen(self,args,*a,**kw):return subprocess.Popen(['nomad_night20261111.worker' if x=='nomad_phase53p.worker' else x for x in args],*a,**kw)
class Client(frozen.Client):
    __init__=bind(frozen.Client.__init__,subprocess=Processes())
source=inspect.getsource(frozen.solve);old='from nomad_phase17.graph import ClearanceGraph';assert source.count(old)==1
scope=dict(frozen.solve.__globals__);exec(compile(source.replace(old,'from nomad_night20261111.graph import HoldClearanceGraph as ClearanceGraph'),__file__,'exec'),scope);solve=scope['solve']
def main():
    from .graph import HoldClearanceGraph
    print('{"kind":"ready"}',flush=True)
    for line in sys.stdin:
        job=json.loads(line)
        if job.get('kind')=='stop':return
        try:r=solve(job)
        except Exception as exc:traceback.print_exc();r=dict(kind='error',error=repr(exc))
        print(json.dumps(frozen.builtin(r),allow_nan=False),flush=True)
if __name__=='__main__':main()
